"""Sentence-level string utilities for the LLM translation pipeline.

A single message can exceed the model's input token limit on its own when
it is several grammatical sentences long. `split_sentences` cuts such a
message on sentence boundaries so `chunk_texts` can pack the pieces into
requests that fit, and `join_sentences` puts the translated pieces back
together as one message in the original order.

Backends
--------
pySBD (rule-based, no model download) handles the languages it ships
rules for. For the rest we fall back to a blank spaCy pipeline with the
`sentencizer` component -- also rule-based, no trained model needed --
using the language's own tokenizer when it loads cleanly and spaCy's
multi-language tokenizer ("xx") otherwise.

Of this project's supported languages (tests/translation/languages.json)::

    pySBD : ar de en es fr hi ja pl ru zh
    spaCy : ht pt tl   (the language's own tokenizer)
            ko vi      (via the "xx" multi-language tokenizer)

Both backends are non-destructive: ``"".join(split_sentences(t, lang)) == t``
for every language. Whitespace between sentences stays attached to the
piece that precedes it, which is what lets `join_sentences` rebuild the
message with its original spacing.

Requires: pip install pysbd spacy
"""

from __future__ import annotations

import re
import threading
from typing import Callable

import pysbd
import spacy
from pysbd.languages import LANGUAGE_CODES

__all__ = [
    "normalize_language",
    "split_sentences",
    "join_sentences",
    "pack_sentences",
]

# Codes pySBD ships segmentation rules for. Read from the library rather
# than hardcoded so it can't drift when pysbd adds a language.
PYSBD_LANGUAGES = frozenset(LANGUAGE_CODES)

# spaCy's multi-language tokenizer: punctuation rules only, no language
# model, and it splits terminators in every script we care about.
_MULTI_LANGUAGE = "xx"

# Languages whose own spaCy tokenizer we deliberately skip:
#   ko - requires mecab-ko + mecab-ko-dic + natto-py, none of which are
#        install-time guaranteed on Windows.
#   vi - requires pyvi; with `use_pyvi=False` the tokenizer degrades to a
#        whitespace splitter that never separates a trailing "." from its
#        word, so the sentencizer finds no boundaries at all.
# The "xx" tokenizer segments both correctly, so use it directly.
_FORCE_MULTI_LANGUAGE = frozenset({"ko", "vi"})

# Legacy / macrolanguage tags that BCP 47 still allows in the wild.
_LANGUAGE_ALIASES = {
    "iw": "he",   # deprecated Hebrew
    "in": "id",   # deprecated Indonesian
    "ji": "yi",   # deprecated Yiddish
    "mo": "ro",   # deprecated Moldavian
    "fil": "tl",  # Filipino -> Tagalog
    "cmn": "zh",  # Mandarin -> Chinese
    "yue": "zh",  # Cantonese -> Chinese
    "nan": "zh",
}

# Last-resort splitter for text in a language neither backend can load.
# Breaks after a run of terminators, keeping trailing whitespace attached.
_FALLBACK_BOUNDARY = re.compile(
    "(?<=[.!?。！？۔؟।])\\s"
)

# Both backends over-split on a name's initials ("Doktè J. | R. | Alvarez",
# "الدكتور ج. | ر. | ..."): a lone letter before a period looks
# like the end of a sentence to a rule-based segmenter. A piece ending
# that way is not finished, so the next piece belongs to it.
_TRAILING_INITIAL = re.compile(r"(?:^|[\s(\[{【（])\w\.[\"'»”’)\]]?\s*$")

# ...and they leave a closing quote or bracket stranded at the head of the
# next piece when the terminator sits inside the quote ("...jaahiz؟ | » wa
# hiya...", "...好了吗？ | "其实..."). That opener belongs to the
# sentence before it.
_LEADING_CLOSER = re.compile(r"^[\s]*[\"'»›”’)\]}】）」』“》]")

# A piece ending in a colon or comma is not a finished sentence either
# (pySBD's Arabic rules break after "سألت:").
_TRAILING_UNFINISHED = re.compile(r"[:;,：；，،؛、]\s*$")


def _merge_fragments(pieces: list[str]) -> list[str]:
    """Glue back pieces that a rule-based segmenter cut in the wrong place.

    Concatenating adjacent pieces, so the non-destructive guarantee holds.
    """
    if len(pieces) <= 1:
        return pieces

    merged = [pieces[0]]
    for piece in pieces[1:]:
        previous = merged[-1]
        if (
            not piece.strip()  # whitespace-only sliver
            or _TRAILING_INITIAL.search(previous)
            or _TRAILING_UNFINISHED.search(previous)
            or _LEADING_CLOSER.match(piece)
        ):
            merged[-1] = previous + piece
        else:
            merged.append(piece)
    return merged

# pySBD's Segmenter stores the text it is working on as instance state
# (`self.original_text`), and a spaCy pipeline is not documented as
# thread-safe either. FastAPI runs sync endpoints in a threadpool, so give
# each thread its own cached instances instead of sharing one.
_local = threading.local()

CountTokensFn = Callable[[str], int]


def normalize_language(tag: str | None) -> str:
    """Reduce a BCP 47 language tag to its lowercase primary subtag.

    ``"pt-BR"`` -> ``"pt"``, ``"zh-Hant-TW"`` -> ``"zh"``, ``"fil"`` ->
    ``"tl"``. Returns ``""`` for a missing or unusable tag.
    """
    if not tag:
        return ""
    primary = re.split(r"[-_]", tag.strip(), maxsplit=1)[0].lower()
    if not primary.isalpha():
        return ""
    return _LANGUAGE_ALIASES.get(primary, primary)


def _cache(name: str) -> dict:
    cache = getattr(_local, name, None)
    if cache is None:
        cache = {}
        setattr(_local, name, cache)
    return cache


def _segmenter(language: str) -> pysbd.Segmenter:
    cache = _cache("segmenters")
    segmenter = cache.get(language)
    if segmenter is None:
        # clean=False keeps the text byte-identical; char_span=True gives
        # offsets into the original so we can slice it ourselves.
        segmenter = pysbd.Segmenter(language=language, clean=False, char_span=True)
        cache[language] = segmenter
    return segmenter


def _spacy_pipeline(language: str):
    cache = _cache("pipelines")
    nlp = cache.get(language)
    if nlp is None:
        code = _MULTI_LANGUAGE if language in _FORCE_MULTI_LANGUAGE else language
        try:
            nlp = spacy.blank(code)
        except (ImportError, OSError):
            # Language class needs an optional dependency we don't have.
            nlp = spacy.blank(_MULTI_LANGUAGE)
        nlp.add_pipe("sentencizer")
        cache[language] = nlp
    return nlp


def _offsets_to_pieces(text: str, starts) -> list[str]:
    """Slice `text` at the given sentence-start offsets.

    Slicing between consecutive starts -- rather than using each backend's
    own end offset -- is what guarantees the pieces rejoin to exactly the
    input: no character can be dropped or duplicated.
    """
    bounds = [0]
    bounds.extend(s for s in sorted(set(starts)) if 0 < s < len(text))
    bounds.append(len(text))
    pieces = [text[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]
    return _merge_fragments(pieces)


def _split_pysbd(text: str, language: str) -> list[str]:
    spans = _segmenter(language).segment(text)
    return _offsets_to_pieces(text, [span.start for span in spans])


def _split_spacy(text: str, language: str) -> list[str]:
    doc = _spacy_pipeline(language)(text)
    if doc.text != text:
        # A tokenizer that rewrites the text would make our offsets lie.
        raise ValueError(f"spaCy tokenizer for {language!r} is destructive")
    return _offsets_to_pieces(text, [sent.start_char for sent in doc.sents])


def _split_regex(text: str) -> list[str]:
    return _offsets_to_pieces(
        text, [match.end() for match in _FALLBACK_BOUNDARY.finditer(text)]
    )


def split_sentences(text: str, language: str = "en") -> list[str]:
    """Split `text` into sentences for a BCP 47 `language` tag.

    Non-destructive: ``"".join(split_sentences(text, lang)) == text``.
    Whitespace following a sentence stays attached to that sentence, so
    the original spacing survives the round trip.

    Falls back through pySBD -> spaCy -> a punctuation regex, and returns
    ``[text]`` unchanged if the text holds no sentence boundary at all.
    """
    if not text or not text.strip():
        return [text] if text else []

    code = normalize_language(language)

    try:
        if code in PYSBD_LANGUAGES:
            return _split_pysbd(text, code)
        return _split_spacy(text, code)
    except Exception:
        # A backend failing is not a reason to lose the message; the regex
        # split is worse but always non-destructive.
        return _split_regex(text)


def join_sentences(sources: list[str], translations: list[str]) -> str:
    """Rebuild one message from its translated sentence pieces.

    `sources` are the pieces `split_sentences` produced, `translations`
    the model's output for them in the same order. Each translated piece
    inherits the trailing whitespace of the source piece it replaces, so
    the rebuilt message is spaced like the original even though the model
    is free to strip or add whitespace of its own.
    """
    if len(sources) != len(translations):
        raise ValueError(
            f"got {len(translations)} translations for {len(sources)} sentence pieces"
        )
    rebuilt = []
    for source, translation in zip(sources, translations):
        trailing = source[len(source.rstrip()):]
        rebuilt.append(translation.rstrip() + trailing)
    return "".join(rebuilt)


def pack_sentences(
    text: str,
    token_limit: int,
    count_tokens_fn: CountTokensFn,
    language: str = "en",
) -> list[str]:
    """Split `text` into the fewest pieces that each fit `token_limit`.

    Sentences are packed greedily in order, so every piece is a run of
    whole consecutive sentences and ``"".join(pieces) == text`` still
    holds. `count_tokens_fn` takes a string and returns its token count
    under the target model.

    A single sentence that exceeds `token_limit` on its own is returned
    intact -- there is no safe boundary inside it -- so the caller must
    still decide what to do with an oversized piece.
    """
    sentences = split_sentences(text, language)
    if len(sentences) <= 1:
        return sentences

    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = current + sentence
        if current and count_tokens_fn(candidate) > token_limit:
            pieces.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        pieces.append(current)

    return pieces
