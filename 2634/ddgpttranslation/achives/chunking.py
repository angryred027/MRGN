"""Token-limit chunking for the LLM translation endpoint.

`chunk_texts` packs a request's messages into batches that each fit the
model's input token limit. A single message can blow the limit on its own
when it is several grammatical sentences long; those are split on sentence
boundaries (see string_utils) into parts that are packed like any other
message, and `ChunkPlan.reassemble` joins the translated parts back into
one string per original message, in the original order.

Only content_type="text" is handled. For "html", sentence-split the
extracted text nodes only and leave markup untouched -- splitting raw HTML
on sentence boundaries will cut tags in half.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from string_utils import join_sentences, pack_sentences

# --- Request models ---------------------------------------------------------
# Replace these with an import from your app's schema module; they are here
# so this file is runnable on its own.


class MessageSource(BaseModel):
    message: str
    source: str  # source language, BCP 47 tag


class TokenizeRequest(BaseModel):
    model: str
    texts: list[MessageSource]


class TokenizeResponse(BaseModel):
    token_count: int


def count_tokens(payload: TokenizeRequest) -> TokenizeResponse:  # pragma: no cover
    """Stand-in for your /api/v1/count-tokens implementation."""
    raise NotImplementedError


# --- Chunking ---------------------------------------------------------------


@dataclass
class ChunkPlan:
    """Batches to send, plus what it takes to undo the split afterwards."""

    chunks: list[list[MessageSource]] = field(default_factory=list)
    # parts[i] holds the source text of every part message i was split
    # into -- a single-element list for a message that was left whole.
    parts: list[list[str]] = field(default_factory=list)

    @property
    def was_split(self) -> bool:
        return any(len(p) > 1 for p in self.parts)

    def reassemble(self, chunk_translations: list[list[str]]) -> list[str]:
        """Rebuild one translated string per original message.

        `chunk_translations[i]` is the `translations` list the endpoint
        returned for `chunks[i]` -- same length, same order. Because
        chunks and the messages inside them are both emitted in order,
        flattening the translations reproduces the exact part sequence.
        """
        if len(chunk_translations) != len(self.chunks):
            raise ValueError(
                f"got {len(chunk_translations)} chunk responses "
                f"for {len(self.chunks)} chunks"
            )
        for index, (chunk, translations) in enumerate(zip(self.chunks, chunk_translations)):
            if len(translations) != len(chunk):
                raise ValueError(
                    f"chunk {index} had {len(chunk)} messages "
                    f"but came back with {len(translations)} translations"
                )

        flat = [text for translations in chunk_translations for text in translations]
        expected = sum(len(p) for p in self.parts)
        if len(flat) != expected:
            raise ValueError(f"expected {expected} translated parts, got {len(flat)}")

        rebuilt, cursor = [], 0
        for sources in self.parts:
            rebuilt.append(join_sentences(sources, flat[cursor : cursor + len(sources)]))
            cursor += len(sources)
        return rebuilt


def build_chunk_plan(payload: TokenizeRequest, token_limit: int) -> ChunkPlan:
    """Pack `payload.texts` into batches that each fit `token_limit`.

    Messages keep their original order. A message that exceeds the limit
    on its own is split into sentence-packed parts first; the parts are
    then packed like any other message, so a long message's tail can
    share a batch with the message that follows it.

    Raises ValueError if a single sentence exceeds the limit -- there is
    no boundary left to split on without corrupting the text.
    """
    model = payload.model
    plan = ChunkPlan()

    current: list[MessageSource] = []

    def fits(candidate: list[MessageSource]) -> bool:
        request = TokenizeRequest(model=model, texts=candidate)
        return count_tokens(request).token_count <= token_limit

    def flush() -> None:
        nonlocal current
        if current:
            plan.chunks.append(current)
            current = []

    def add(part: MessageSource, message_index: int) -> None:
        nonlocal current
        if fits(current + [part]):
            current.append(part)
            return
        flush()
        if not fits([part]):
            raise ValueError(
                f"texts[{message_index}]: a single sentence exceeds the "
                f"{token_limit}-token limit and cannot be split further"
            )
        current = [part]

    for message_index, text in enumerate(payload.texts):
        if fits([text]):
            pieces = [text.message]
        else:
            # Too long on its own -- cut it on sentence boundaries and
            # pack the sentences up to the limit.
            pieces = pack_sentences(
                text.message,
                token_limit,
                lambda piece: count_tokens(
                    TokenizeRequest(
                        model=model,
                        texts=[MessageSource(message=piece, source=text.source)],
                    )
                ).token_count,
                text.source,
            )

        plan.parts.append(pieces)
        for piece in pieces:
            add(MessageSource(message=piece, source=text.source), message_index)

    flush()
    return plan


def chunk_texts(payload: TokenizeRequest, token_limit: int) -> list[list[MessageSource]]:
    """Batches of messages that each fit `token_limit`.

    Use `build_chunk_plan` instead when any message may need splitting:
    the plan carries what `reassemble` needs to put the parts back into
    one translated string per input message.
    """
    return build_chunk_plan(payload, token_limit).chunks
