"""Validates POST /api/v1/count-tokens: request/response schema and that it
returns a usable token count.

Request shape: {"model": "deep", "texts": [{"message": "...", "source": "..."}]}
Response shape: {"tokens": <int>}
"""

import requests

SAMPLE_SIZE = 3


def test_count_tokens_response_schema(fixture_case, count_tokens_url, auth_headers):
    sample_texts = [
        {"message": t["messages"], "source": t["source"]}
        for t in fixture_case["texts"][:SAMPLE_SIZE]
    ]

    response = requests.post(
        count_tokens_url,
        headers=auth_headers,
        json={"model": "deep", "texts": sample_texts},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert isinstance(body, dict)
    assert "tokens" in body
    assert isinstance(body["tokens"], int)
    assert body["tokens"] > 0
