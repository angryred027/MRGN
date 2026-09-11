"""Auth enforcement on POST /api/v1/llm/agent?type=translation:
rejects requests with no Session-Token, accepts requests with a valid one.
"""

import requests

MINIMAL_BODY = {
    "target_language": "es",
    "texts": [{"messages": "Hello world!", "source": "en"}],
}


def test_translation_without_session_token_is_unauthorized(translation_url):
    response = requests.post(
        translation_url, params={"type": "translation"}, json=MINIMAL_BODY
    )
    assert response.status_code == 401


def test_translation_with_valid_session_token_is_authorized(
    translation_url, auth_headers
):
    response = requests.post(
        translation_url,
        params={"type": "translation"},
        headers=auth_headers,
        json=MINIMAL_BODY,
    )
    assert response.status_code == 200
