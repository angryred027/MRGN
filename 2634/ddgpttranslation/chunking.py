"""Sentence-level chunking for the LLM translation token limit.

A single message in `texts` (see prompt.py) can be long enough to blow the
model's per-request token budget on its own. This module splits such a
message into sentences and repacks them into chunks that fit the budget,
then bin-packs chunks from any number of messages into batches so a single
`texts` payload sent to the translation endpoint never exceeds it. After
translation, `reassemble_translations` joins the pieces back into exactly
one translated string per original message -- the split is invisible to
the caller.

Token counting is delegated to the caller (`count_tokens_fn`) rather than
estimated here, since the real limit and tokenizer live behind the
`/api/v1/count-tokens` endpoint (see tests/translation/test_token_count.py)
and differ per model/language.

Only content_type="text" is handled. For "html", sentence-split the
extracted text nodes only and leave markup untouched -- splitting raw HTML
on sentence boundaries will cut tags in half.

Requires: pip install pysbd
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pysbd

CountTokensFn = Callable[[str], int]


@dataclass(frozen=True)
class ChunkItem:
    message_index: int  # index into the original `texts` list
    part_index: int  # order of this chunk within its message's pieces
    text: str


Batch = list[ChunkItem]

_segmenters: dict[str, "pysbd.Segmenter"] = {}


def _segmenter(language: str) -> "pysbd.Segmenter":
    segmenter = _segmenters.get(language)
    if segmenter is None:
        segmenter = pysbd.Segmenter(language=language, clean=False)
        _segmenters[language] = segmenter
    return segmenter


def split_into_sentences(text: str, language: str = "en") -> list[str]:
    """Split `text` into sentences using language-aware boundary rules.

    `language` is an ISO 639-1 code (pysbd supports ~30 languages; falls
    back to its "en" rules for codes it doesn't recognize).
    """
    if not text.strip():
        return [text]
    # clean=False preserves the original text exactly (no silent rewriting
    # of quotes/whitespace); pysbd leaves boundary whitespace attached to
    # each segment in that mode, so strip it since we rejoin with our own
    # joiner.
    return [sentence.strip() for sentence in _segmenter(language).segment(text)]


def _split_message(
    text: str,
    max_tokens: int,
    count_tokens_fn: CountTokensFn,
    language: str,
) -> list[str]:
    """Split one message into pieces that each fit max_tokens.

    Tries the whole message first; only falls back to sentence-packing if
    it doesn't fit, so short messages are never touched. A single sentence
    that alone exceeds max_tokens is kept intact -- there's no safe way to
    split it further without corrupting meaning -- and is sent oversized.
    """
    if count_tokens_fn(text) <= max_tokens:
        return [text]

    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in split_into_sentences(text, language):
        sentence_tokens = count_tokens_fn(sentence)

        if current and current_tokens + sentence_tokens > max_tokens:
            pieces.append(" ".join(current))
            current, current_tokens = [], 0

        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        pieces.append(" ".join(current))

    return pieces


def build_batches(
    texts: list[str],
    max_tokens_per_batch: int,
    count_tokens_fn: CountTokensFn,
    language: str = "en",
) -> list[Batch]:
    """Split and pack `texts` into batches, each within max_tokens_per_batch.

    Each message is first split into sentence-packed chunks if it alone
    exceeds the budget, then all chunks (from any message) are bin-packed
    greedily, in original order, into batches -- one LLM call per batch.
    """
    batches: list[Batch] = []
    current: Batch = []
    current_tokens = 0

    for message_index, text in enumerate(texts):
        message_chunks = _split_message(text, max_tokens_per_batch, count_tokens_fn, language)
        for part_index, chunk_text in enumerate(message_chunks):
            chunk_tokens = count_tokens_fn(chunk_text)

            if current and current_tokens + chunk_tokens > max_tokens_per_batch:
                batches.append(current)
                current, current_tokens = [], 0

            current.append(ChunkItem(message_index, part_index, chunk_text))
            current_tokens += chunk_tokens

    if current:
        batches.append(current)

    return batches


def reassemble_translations(
    batches: list[Batch],
    batch_translations: list[list[str]],
    message_count: int,
    joiner: str = " ",
) -> list[str]:
    """Rejoin translated chunks into one translated string per original
    message, in the same order and count as the input `texts`.

    `batch_translations[i]` must be the `translations` list returned for
    `batches[i]` (same length, same order).
    """
    if len(batches) != len(batch_translations):
        raise ValueError(
            f"got {len(batch_translations)} batch responses for {len(batches)} batches"
        )

    parts: dict[int, dict[int, str]] = {i: {} for i in range(message_count)}

    for batch, translations in zip(batches, batch_translations):
        if len(translations) != len(batch):
            raise ValueError(
                f"batch had {len(batch)} chunks but got {len(translations)} translations back"
            )
        for item, translated in zip(batch, translations):
            parts[item.message_index][item.part_index] = translated

    return [
        joiner.join(parts[message_index][part] for part in sorted(parts[message_index]))
        for message_index in range(message_count)
    ]


def translate_long_message(
    text: str,
    max_tokens: int,
    count_tokens_fn: CountTokensFn,
    translate_fn: Callable[[list[str]], list[str]],
    language: str = "en",
) -> str:
    """Translate one message that may exceed max_tokens on its own.

    If `text` already fits, this is a single translate_fn([text]) call.
    Otherwise it's split into sentence-packed chunks (see _split_message)
    and bin-packed into batches the same way build_batches packs multiple
    messages; each batch is sent through `translate_fn` -- since each
    chunk is already packed close to max_tokens, that's usually one call
    per chunk (rather than all chunks sharing a single call) -- and the
    translated pieces are rejoined into one string in original order.

    `translate_fn` wraps one call to the translation endpoint and returns
    its `translations` list for the `texts` it was given, e.g.:

        def translate_fn(texts: list[str]) -> list[str]:
            resp = requests.post(
                translation_url,
                params={"type": "translation"},
                headers=auth_headers,
                json={"target_language": target_language, "texts": texts},
            )
            return resp.json()["translations"]
    """
    batches = build_batches([text], max_tokens, count_tokens_fn, language)
    batch_translations = [translate_fn([item.text for item in batch]) for batch in batches]
    return reassemble_translations(batches, batch_translations, message_count=1)[0]
