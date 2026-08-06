"""In-process mock of POST /api/v1/llm/agent?type=translation.

Simulates just enough real-endpoint behavior for the chunking tests to be
meaningful:
  - requires a `Session-Token` header (401 if absent)
  - only understands `type=translation` (400 otherwise)
  - rejects an unsupported `target_language` (400)
  - enforces TOKEN_LIMIT on the request payload, mirroring the real
    endpoint's context-window limit (413 if exceeded) -- this is the
    behavior the chunking logic under test exists to work around
  - returns the real target-language translation for each input text, in
    `{"translations": [...]}` shape, so tests can verify ordering and
    chunk-recombination against genuine translated text

sentence_bank.SENTENCES is a parallel corpus: SENTENCES[lang][i] is the same
sentence in every language, so looking up which sentence a text is (by
source language + exact text match) lets the mock return the real
translation in the target language, rather than a fake placeholder. Text
that isn't in the corpus (i.e. not one of the fixture sentences) can't be
translated by the mock and returns 422.
"""

import json
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from sentence_bank import SENTENCES, sentence_index
from token_utils import count_tokens

HERE = Path(__file__).parent
TOKEN_LIMIT = 400

_SUPPORTED_LANGUAGES = json.loads(
    (HERE / "languages.json").read_text(encoding="utf-8")
)["supported_languages"]


class TranslationText(BaseModel):
    messages: str
    source: str


class TranslationRequest(BaseModel):
    target_language: str
    texts: list[TranslationText] = Field(default_factory=list)


class TranslationResponse(BaseModel):
    translations: list[str]


app = FastAPI()


def _require_session_token(session_token: str | None) -> None:
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing Session-Token header")


@app.post("/api/v1/llm/agent", response_model=TranslationResponse)
def llm_agent(
    body: TranslationRequest,
    type: str = Query(...),
    session_token: str | None = Header(default=None, alias="Session-Token"),
):
    _require_session_token(session_token)

    if type != "translation":
        raise HTTPException(status_code=400, detail=f"Unsupported type: {type!r}")

    if body.target_language not in _SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target_language: {body.target_language!r}",
        )

    request_tokens = count_tokens(json.dumps(body.model_dump(), ensure_ascii=False))
    if request_tokens > TOKEN_LIMIT:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Request exceeds token limit: {request_tokens} > {TOKEN_LIMIT}. "
                "Split texts into smaller chunks."
            ),
        )

    translations = []
    for t in body.texts:
        try:
            idx = sentence_index(t.source, t.messages)
        except (KeyError, ValueError):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Mock cannot translate unrecognized text "
                    f"(source={t.source!r}): {t.messages!r}"
                ),
            )
        translations.append(SENTENCES[body.target_language][idx])

    return TranslationResponse(translations=translations)
