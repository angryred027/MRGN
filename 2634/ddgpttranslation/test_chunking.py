"""Offline tests for chunking.py, using a fake token counter (1 token per
word) instead of the real /api/v1/count-tokens endpoint, so these run
without network access or a live server.
"""

from chunking import (
    build_batches,
    reassemble_translations,
    split_into_sentences,
    translate_long_message,
)


def word_count(text: str) -> int:
    return len(text.split())


def test_split_into_sentences_basic():
    text = "Hello there. How are you? I am fine!"
    assert split_into_sentences(text) == [
        "Hello there.",
        "How are you?",
        "I am fine!",
    ]


def test_split_into_sentences_ignores_abbreviation_periods():
    text = "Dr. Smith arrived at 3 p.m. and left an hour later."
    assert split_into_sentences(text) == [text]


def test_short_message_is_not_split():
    texts = ["Hi.", "Short message here."]
    batches = build_batches(texts, max_tokens_per_batch=100, count_tokens_fn=word_count)

    assert len(batches) == 1
    assert [item.text for item in batches[0]] == texts
    assert [item.message_index for item in batches[0]] == [0, 1]
    assert all(item.part_index == 0 for item in batches[0])


def test_long_message_is_split_into_sentence_packed_chunks():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    batches = build_batches([text], max_tokens_per_batch=6, count_tokens_fn=word_count)

    chunks = [item.text for batch in batches for item in batch]
    assert chunks == [
        "One two three. Four five six.",
        "Seven eight nine. Ten eleven twelve.",
    ]
    assert all(word_count(c) <= 6 for c in chunks)


def test_batches_never_exceed_token_budget_across_messages():
    texts = ["one two three", "four five six", "seven eight nine"]
    batches = build_batches(texts, max_tokens_per_batch=6, count_tokens_fn=word_count)

    assert all(sum(word_count(item.text) for item in batch) <= 6 for batch in batches)
    # every message made it into exactly one chunk (none needed splitting)
    all_items = [item for batch in batches for item in batch]
    assert sorted(item.message_index for item in all_items) == [0, 1, 2]


def test_oversized_single_sentence_is_kept_intact():
    text = "one two three four five six seven eight nine ten"  # one sentence, no punctuation
    batches = build_batches([text], max_tokens_per_batch=3, count_tokens_fn=word_count)

    chunks = [item.text for batch in batches for item in batch]
    assert chunks == [text]  # can't split further without punctuation boundaries


def test_reassemble_roundtrips_split_message():
    texts = ["Short one.", "One two three. Four five six. Seven eight nine."]
    batches = build_batches(texts, max_tokens_per_batch=6, count_tokens_fn=word_count)

    # fake translation: uppercase each chunk, batch by batch
    batch_translations = [[item.text.upper() for item in batch] for batch in batches]

    result = reassemble_translations(batches, batch_translations, message_count=len(texts))

    assert result == [
        "SHORT ONE.",
        "ONE TWO THREE. FOUR FIVE SIX. SEVEN EIGHT NINE.",
    ]
    assert len(result) == len(texts)  # contract: one output per input message


def test_reassemble_rejects_mismatched_batch_count():
    texts = ["hello"]
    batches = build_batches(texts, max_tokens_per_batch=10, count_tokens_fn=word_count)

    try:
        reassemble_translations(batches, batch_translations=[], message_count=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for mismatched batch count")


def test_translate_long_message_short_text_is_single_call():
    calls = []

    def fake_translate(texts):
        calls.append(texts)
        return [t.upper() for t in texts]

    result = translate_long_message(
        "Short message.", max_tokens=100, count_tokens_fn=word_count, translate_fn=fake_translate
    )

    assert result == "SHORT MESSAGE."
    assert calls == [["Short message."]]  # one call, whole message, untouched


def test_translate_long_message_splits_and_rejoins():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    calls = []

    def fake_translate(texts):
        calls.append(texts)
        return [t.upper() for t in texts]

    result = translate_long_message(
        text, max_tokens=6, count_tokens_fn=word_count, translate_fn=fake_translate
    )

    assert result == (
        "ONE TWO THREE. FOUR FIVE SIX. SEVEN EIGHT NINE. TEN ELEVEN TWELVE."
    )
    # each chunk is already packed to the 6-token budget, so they can't
    # share a batch -- two chunks means two translate_fn calls here
    assert calls == [
        ["One two three. Four five six."],
        ["Seven eight nine. Ten eleven twelve."],
    ]
