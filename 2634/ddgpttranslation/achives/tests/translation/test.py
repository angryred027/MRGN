"""Full-coverage test of POST /api/v1/llm/agent?type=translation.

Unlike test_translation_response.py (which samples 3 texts per language as
a lightweight schema check), this sends every text in each fixture -- the
whole 42-entry set -- for every supported target language, in a single
request per language. If the real endpoint enforces a token limit smaller
than a full fixture, these requests may be rejected; that's a genuine
finding about the endpoint, not a bug in the test.
"""

import json

import requests


def test_fixtures_cover_all_supported_languages(supported_languages, fixture_language):
    assert fixture_language in supported_languages


def test_translation_full_fixture_schema_and_count_match(
    fixture_case, translation_url, auth_headers, artifacts_output_dir
):
    target_language = fixture_case["target_language"]
    texts = fixture_case["texts"]

    response = requests.post(
        translation_url,
        params={"type": "translation"},
        headers=auth_headers,
        json={"target_language": target_language, "texts": texts},
    )
    assert response.status_code == 200, response.text

    body = response.json()

    output_path = artifacts_output_dir / f"{target_language}.full.json"
    output_path.write_text(
        json.dumps(
            {
                "target_language": target_language,
                "request_texts": texts,
                "response": body,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert isinstance(body, dict)
    assert "translations" in body
    assert isinstance(body["translations"], list)
    assert all(isinstance(t, str) for t in body["translations"])

    assert len(body["translations"]) == len(texts), (
        f"sent {len(texts)} texts but got "
        f"{len(body['translations'])} translations back"
    )
