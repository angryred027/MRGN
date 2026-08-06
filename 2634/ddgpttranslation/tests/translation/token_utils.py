"""Token counting and request chunking for the translation endpoint.

Mirrors the frontend's `tokenx`-based token counting with `tiktoken`
(cl100k_base) so tests reason about the same limit the real client enforces.

Token count is taken over the *full wire payload* (`json.dumps` of the
request body), not just the concatenated message text, since that is what
the endpoint's context window actually has to hold.
"""

import json

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def build_payload(target_language: str, texts: list[dict]) -> dict:
    return {"target_language": target_language, "texts": texts}


def count_request_tokens(target_language: str, texts: list[dict]) -> int:
    payload = build_payload(target_language, texts)
    return count_tokens(json.dumps(payload, ensure_ascii=False))


def chunk_texts(
    target_language: str, texts: list[dict], token_limit: int
) -> list[list[dict]]:
    """Greedily splits `texts` into ordered chunks that each fit `token_limit`.

    Order is preserved within and across chunks so that concatenating the
    endpoint's per-chunk `translations` responses reproduces the original
    text order.

    Raises ValueError if a single text cannot fit within the limit on its own.
    """
    chunks: list[list[dict]] = []
    current: list[dict] = []

    for entry in texts:
        candidate = current + [entry]
        if count_request_tokens(target_language, candidate) <= token_limit:
            current = candidate
            continue

        if not current:
            raise ValueError(
                f"Single text exceeds token_limit={token_limit} on its own "
                f"(source={entry.get('source')!r}): {entry.get('messages')!r}"
            )

        chunks.append(current)
        current = [entry]
        if count_request_tokens(target_language, current) > token_limit:
            raise ValueError(
                f"Single text exceeds token_limit={token_limit} on its own "
                f"(source={entry.get('source')!r}): {entry.get('messages')!r}"
            )

    if current:
        chunks.append(current)

    return chunks
