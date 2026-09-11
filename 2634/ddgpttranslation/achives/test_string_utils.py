"""Offline tests for string_utils.py -- no network, no trained models."""

import json
from pathlib import Path

import pytest

from string_utils import (
    PYSBD_LANGUAGES,
    join_sentences,
    normalize_language,
    pack_sentences,
    split_sentences,
)

FIXTURES_DIR = Path(__file__).parent / "tests" / "translation" / "fixtures"
SUPPORTED = json.loads(
    (FIXTURES_DIR.parent / "languages.json").read_text(encoding="utf-8")
)["supported_languages"]


def fixture_messages():
    """Every (source_language, message) pair in the fixtures, deduped."""
    seen = {}
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        for text in json.loads(path.read_text(encoding="utf-8"))["texts"]:
            seen[(text["source"], text["messages"])] = None
    return list(seen)


def word_count(text: str) -> int:
    return len(text.split())


# --- normalize_language -----------------------------------------------------


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("en", "en"),
        ("pt-BR", "pt"),
        ("zh-Hant-TW", "zh"),
        ("ZH-HANS", "zh"),
        ("ht_HT", "ht"),
        ("fil", "tl"),
        ("iw", "he"),
        (" fr ", "fr"),
        ("", ""),
        (None, ""),
        ("123", ""),
    ],
)
def test_normalize_language(tag, expected):
    assert normalize_language(tag) == expected


# --- split_sentences --------------------------------------------------------


def test_splits_english_sentences():
    assert split_sentences("Hello there. How are you? I am fine!", "en") == [
        "Hello there. ",
        "How are you? ",
        "I am fine!",
    ]


def test_does_not_split_on_abbreviation_periods():
    text = "Dr. Smith arrived at 3 p.m. and left an hour later."
    assert split_sentences(text, "en") == [text]


def test_does_not_split_on_name_initials():
    text = "Doktè J. R. Alvarez te rive. Li pa t pare."
    assert split_sentences(text, "ht") == ["Doktè J. R. Alvarez te rive. ", "Li pa t pare."]


def test_keeps_closing_quote_with_its_sentence():
    pieces = split_sentences('她看着陈先生问道:"报告准备好了吗?"其实还没有。', "zh")
    assert not any(piece.lstrip().startswith('"') for piece in pieces)


@pytest.mark.parametrize("language", SUPPORTED)
def test_every_supported_language_splits_multi_sentence_text(language):
    """No supported language may silently refuse to split."""
    messages = [m for source, m in fixture_messages() if source == language]
    assert messages, f"no fixture text for {language}"
    assert any(len(split_sentences(m, language)) > 1 for m in messages)


@pytest.mark.parametrize("source,message", fixture_messages())
def test_split_is_non_destructive(source, message):
    assert "".join(split_sentences(message, source)) == message


def test_split_is_non_destructive_for_a_bcp47_subtag():
    text = "O Dr. Silva chegou. Ele perguntou algo. Não estava pronto."
    assert "".join(split_sentences(text, "pt-BR")) == text
    assert len(split_sentences(text, "pt-BR")) == 3


def test_unknown_language_still_splits_and_is_non_destructive():
    text = "First one here. Second one here. Third one here."
    pieces = split_sentences(text, "qq-ZZ")
    assert "".join(pieces) == text
    assert len(pieces) == 3


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_blank_text_is_passed_through(text):
    assert "".join(split_sentences(text, "en")) == text


def test_single_sentence_is_untouched():
    assert split_sentences("Just the one sentence here", "en") == [
        "Just the one sentence here"
    ]


def test_language_routing_covers_every_supported_language():
    """Documents which backend each supported language lands on."""
    via_pysbd = {lang for lang in SUPPORTED if normalize_language(lang) in PYSBD_LANGUAGES}
    assert via_pysbd == {"ar", "de", "en", "es", "fr", "hi", "ja", "pl", "ru", "zh"}
    assert set(SUPPORTED) - via_pysbd == {"ht", "ko", "pt", "tl", "vi"}


# --- join_sentences ---------------------------------------------------------


def test_join_restores_original_spacing():
    text = "Hello there. How are you? I am fine!"
    sources = split_sentences(text, "en")
    # the model is free to strip or add whitespace of its own
    translations = [piece.strip() + "  " for piece in sources]
    assert join_sentences(sources, translations) == text


def test_join_roundtrips_an_identity_translation():
    for source, message in fixture_messages():
        pieces = split_sentences(message, source)
        assert join_sentences(pieces, pieces) == message


def test_join_rejects_a_length_mismatch():
    with pytest.raises(ValueError):
        join_sentences(["a. ", "b."], ["A."])


# --- pack_sentences ---------------------------------------------------------


def test_packing_fills_up_to_the_limit():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    pieces = pack_sentences(text, 6, word_count, "en")

    assert pieces == [
        "One two three. Four five six. ",
        "Seven eight nine. Ten eleven twelve.",
    ]
    assert all(word_count(piece) <= 6 for piece in pieces)
    assert "".join(pieces) == text


def test_packing_leaves_a_fitting_message_whole():
    text = "One two three. Four five six."
    assert pack_sentences(text, 100, word_count, "en") == [text]


def test_oversized_single_sentence_is_returned_intact():
    text = "one two three four five six seven eight nine ten"
    assert pack_sentences(text, 3, word_count, "en") == [text]


def test_packing_is_non_destructive_across_fixtures():
    for source, message in fixture_messages():
        assert "".join(pack_sentences(message, 8, word_count, source)) == message
