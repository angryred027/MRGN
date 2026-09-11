"""Offline tests for chunking.py.

Token counting is faked as one token per whitespace-separated word, so
these run without a live /api/v1/count-tokens endpoint.
"""

import pytest

import chunking
from chunking import (
    MessageSource,
    TokenizeRequest,
    TokenizeResponse,
    build_chunk_plan,
    chunk_texts,
)


@pytest.fixture(autouse=True)
def fake_count_tokens(monkeypatch):
    """One token per word, summed over the batch."""

    def count(payload: TokenizeRequest) -> TokenizeResponse:
        return TokenizeResponse(
            token_count=sum(len(t.message.split()) for t in payload.texts)
        )

    monkeypatch.setattr(chunking, "count_tokens", count)
    return count


def request_of(*messages: str, source: str = "en") -> TokenizeRequest:
    return TokenizeRequest(
        model="gemma-12b",
        texts=[MessageSource(message=m, source=source) for m in messages],
    )


def messages_of(chunks) -> list[list[str]]:
    return [[t.message for t in chunk] for chunk in chunks]


# --- packing ----------------------------------------------------------------


def test_short_messages_share_one_chunk():
    payload = request_of("Hi there.", "Short message here.")
    assert messages_of(chunk_texts(payload, 100)) == [
        ["Hi there.", "Short message here."]
    ]


def test_messages_are_packed_up_to_the_limit_in_order():
    payload = request_of("one two three", "four five six", "seven eight nine")
    chunks = chunk_texts(payload, 6)

    assert messages_of(chunks) == [
        ["one two three", "four five six"],
        ["seven eight nine"],
    ]


def test_no_chunk_exceeds_the_limit():
    payload = request_of(*[f"word{i} word word" for i in range(20)])
    for chunk in chunk_texts(payload, 7):
        assert sum(len(t.message.split()) for t in chunk) <= 7


def test_source_language_is_carried_onto_every_part():
    payload = request_of(
        "One two three. Four five six. Seven eight nine.", source="pt-BR"
    )
    chunks = chunk_texts(payload, 6)

    assert all(t.source == "pt-BR" for chunk in chunks for t in chunk)


def test_empty_request_produces_no_chunks():
    assert chunk_texts(request_of(), 10) == []


# --- splitting an oversized message -----------------------------------------


def test_oversized_message_is_split_on_sentence_boundaries():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    plan = build_chunk_plan(request_of(text), 6)

    assert plan.was_split
    assert plan.parts == [
        ["One two three. Four five six. ", "Seven eight nine. Ten eleven twelve."]
    ]
    assert "".join(plan.parts[0]) == text


def test_split_parts_still_respect_the_limit():
    text = " ".join(f"sentence {i} here." for i in range(30))
    for chunk in chunk_texts(request_of(text), 9):
        assert sum(len(t.message.split()) for t in chunk) <= 9


def test_a_long_message_tail_can_share_a_chunk_with_the_next_message():
    payload = request_of("One two. Three four. Five six.", "seven")
    chunks = chunk_texts(payload, 5)

    assert chunks[-1][-1].message == "seven"
    assert len(chunks[-1]) > 1, "the tail part and the next message should share a chunk"


def test_unsplittable_sentence_raises():
    payload = request_of("one two three four five six seven")
    with pytest.raises(ValueError, match="single sentence exceeds"):
        chunk_texts(payload, 3)


def test_error_names_the_offending_message():
    payload = request_of("fine", "one two three four five six seven")
    with pytest.raises(ValueError, match=r"texts\[1\]"):
        chunk_texts(payload, 3)


# --- reassembly -------------------------------------------------------------


def translate_chunks(plan, transform=str.upper) -> list[list[str]]:
    """Stand in for the endpoint: one translation per message, in order."""
    return [[transform(t.message) for t in chunk] for chunk in plan.chunks]


def test_reassembly_returns_one_string_per_input_message():
    payload = request_of("Short one.", "One two three. Four five six. Seven eight nine.")
    plan = build_chunk_plan(payload, 6)

    result = plan.reassemble(translate_chunks(plan))

    assert result == [
        "SHORT ONE.",
        "ONE TWO THREE. FOUR FIVE SIX. SEVEN EIGHT NINE.",
    ]
    assert len(result) == len(payload.texts)


def test_reassembly_preserves_order_across_many_split_messages():
    payload = request_of(
        "Aa one. Aa two. Aa three.",
        "Bb one. Bb two. Bb three.",
        "Cc one. Cc two. Cc three.",
    )
    plan = build_chunk_plan(payload, 4)

    assert plan.was_split
    assert plan.reassemble(translate_chunks(plan)) == [
        "AA ONE. AA TWO. AA THREE.",
        "BB ONE. BB TWO. BB THREE.",
        "CC ONE. CC TWO. CC THREE.",
    ]


def test_reassembly_roundtrips_an_identity_translation():
    messages = [
        "Short one.",
        "One two three. Four five six. Seven eight nine. Ten eleven twelve.",
        "Another short.",
    ]
    plan = build_chunk_plan(request_of(*messages), 6)

    assert plan.reassemble(translate_chunks(plan, transform=lambda s: s)) == messages


def test_reassembly_tolerates_a_model_that_restrips_whitespace():
    text = "One two three. Four five six. Seven eight nine."
    plan = build_chunk_plan(request_of(text), 6)

    result = plan.reassemble(translate_chunks(plan, transform=lambda s: s.strip()))

    assert result == [text]


def test_unsplit_request_reassembles_untouched():
    payload = request_of("Hi there.", "Short message here.")
    plan = build_chunk_plan(payload, 100)

    assert not plan.was_split
    assert plan.reassemble(translate_chunks(plan, transform=lambda s: s)) == [
        "Hi there.",
        "Short message here.",
    ]


def test_reassembly_rejects_a_wrong_chunk_count():
    plan = build_chunk_plan(request_of("hello"), 10)
    with pytest.raises(ValueError, match="chunk responses"):
        plan.reassemble([])


def test_reassembly_rejects_a_short_chunk_response():
    plan = build_chunk_plan(request_of("one", "two"), 10)
    with pytest.raises(ValueError, match="translations"):
        plan.reassemble([["ONE"]])
