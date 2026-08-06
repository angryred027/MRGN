"""Tests for POST /api/v1/llm/agent?type=translation against the mock server.

Fixtures in fixtures/{lang}.json are intentionally oversized (42 sentences)
so that a single request exceeds the endpoint's token limit; the core of
this suite is verifying that chunk_texts() splits each fixture into
requests that fit, that the mock endpoint accepts every chunk, and that
recombining the per-chunk responses reproduces the original text order.
"""

import json

from sentence_bank import SENTENCES, sentence_index
from token_utils import chunk_texts, count_request_tokens

ENDPOINT = "/api/v1/llm/agent"


def post_chunk(client, auth_headers, target_language: str, chunk: list[dict]):
    return client.post(
        ENDPOINT,
        params={"type": "translation"},
        headers=auth_headers,
        json={"target_language": target_language, "texts": chunk},
    )


def test_fixture_exceeds_single_request_token_limit(fixture_case, token_limit):
    """Sanity check: confirms the generated fixtures actually need chunking."""
    total_tokens = count_request_tokens(
        fixture_case["target_language"], fixture_case["texts"]
    )
    assert total_tokens > token_limit, (
        f"fixture for {fixture_case['target_language']!r} is only "
        f"{total_tokens} tokens (limit {token_limit}); it no longer "
        "exercises chunking -- add more/longer sentences to sentence_bank.py"
    )


def test_chunks_each_fit_within_token_limit(fixture_case, token_limit):
    target_language = fixture_case["target_language"]
    chunks = chunk_texts(target_language, fixture_case["texts"], token_limit)

    assert len(chunks) > 1, "expected fixture to require multiple chunks"
    for chunk in chunks:
        assert count_request_tokens(target_language, chunk) <= token_limit


def test_chunking_preserves_full_text_set_and_order(fixture_case, token_limit):
    target_language = fixture_case["target_language"]
    chunks = chunk_texts(target_language, fixture_case["texts"], token_limit)

    flattened = [text for chunk in chunks for text in chunk]
    assert flattened == fixture_case["texts"]


def test_translation_endpoint_chunked_roundtrip(
    fixture_case, client, auth_headers, token_limit, artifacts_output_dir
):
    """End-to-end: chunk -> POST each chunk -> recombine -> verify against source."""
    target_language = fixture_case["target_language"]
    texts = fixture_case["texts"]
    chunks = chunk_texts(target_language, texts, token_limit)

    combined_translations: list[str] = []
    for chunk in chunks:
        response = post_chunk(client, auth_headers, target_language, chunk)
        assert response.status_code == 200, response.text

        body = response.json()
        assert set(body.keys()) == {"translations"}
        assert isinstance(body["translations"], list)
        assert len(body["translations"]) == len(chunk)
        assert all(isinstance(t, str) for t in body["translations"])

        combined_translations.extend(body["translations"])

    assert len(combined_translations) == len(texts)

    results = []
    for original, translation in zip(texts, combined_translations):
        expected = SENTENCES[target_language][
            sentence_index(original["source"], original["messages"])
        ]
        assert translation == expected
        results.append(
            {
                "source": original["source"],
                "messages": original["messages"],
                "translation": translation,
            }
        )

    artifact = {
        "target_language": target_language,
        "chunk_count": len(chunks),
        "text_count": len(texts),
        "results": results,
    }
    output_path = artifacts_output_dir / f"{target_language}.json"
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_unchunked_full_fixture_hits_token_limit(fixture_case, client, auth_headers):
    """Without chunking, the oversized fixture is rejected -- this is *why*
    chunking is required, not just an implementation detail."""
    response = post_chunk(
        client, auth_headers, fixture_case["target_language"], fixture_case["texts"]
    )
    assert response.status_code == 413
    assert "token limit" in response.json()["detail"].lower()


def test_missing_session_token_header_is_rejected(client):
    response = client.post(
        ENDPOINT,
        params={"type": "translation"},
        json={
            "target_language": "es",
            "texts": [{"messages": "Hello world!", "source": "en"}],
        },
    )
    assert response.status_code == 401


def test_unsupported_target_language_is_rejected(client, auth_headers):
    response = post_chunk(
        client,
        auth_headers,
        "xx",
        [{"messages": "Hello world!", "source": "en"}],
    )
    assert response.status_code == 400


def test_unsupported_type_query_param_is_rejected(client, auth_headers):
    response = client.post(
        ENDPOINT,
        params={"type": "summarization"},
        headers=auth_headers,
        json={
            "target_language": "es",
            "texts": [{"messages": "Hello world!", "source": "en"}],
        },
    )
    assert response.status_code == 400
