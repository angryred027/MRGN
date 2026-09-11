"""Validates POST /api/v1/llm/agent?type=translation response shape, and
that the number of translations returned matches the number of texts sent.

Parametrized across all 15 fixtures/{lang}.json target languages (via the
fixture_case fixture in conftest.py). Only a small sample of each fixture's
42 texts is sent per call, since the real endpoint's token limit is unknown.
"""

import json

import requests

SAMPLE_SIZE = 3


def test_translation_response_schema_and_count_match(
    fixture_case, translation_url, auth_headers, artifacts_output_dir
):
    target_language = fixture_case["target_language"]
    sample_texts = fixture_case["texts"][:SAMPLE_SIZE]

    response = requests.post(
        translation_url,
        params={"type": "translation"},
        headers=auth_headers,
        json={"target_language": target_language, "texts": sample_texts},
    )
    assert response.status_code == 200, response.text

    body = response.json()

    output_path = artifacts_output_dir / f"{target_language}.json"
    output_path.write_text(
        json.dumps(
            {
                "target_language": target_language,
                "request_texts": sample_texts,
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

    assert len(body["translations"]) == len(sample_texts), (
        f"sent {len(sample_texts)} texts but got "
        f"{len(body['translations'])} translations back"
    )
