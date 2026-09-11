"""Translation agent prompt + response schema for Gemma-12b.

Provider-agnostic: the schema is a plain JSON Schema dict you can hand to
whatever structured/guided-output mechanism your backend exposes (Ollama's
`format` field, an OpenAI-compatible server's `response_format.json_schema`,
Vertex AI's `response_schema`, etc.). If your backend has no native schema
enforcement, the system prompt alone still constrains the output shape.
"""

import json

from pydantic import BaseModel

SYSTEM_PROMPT = """You are a translation engine.

You receive a JSON object with:
- target_lang: target language code (e.g. "es")
- content_type: "text" or "html"
- texts: an array of strings to translate

Rules:
- Translate every string in "texts" into target_lang. Preserve meaning and tone.
- Return exactly one translated string per input atring, in the same order. Never add, drop, merge, or reorder items.
- If content_type is "html": keep all tags, attributes, and attribute values unchanged; translate only the visible text.
- If content_type is "text": return plain text with no markup.
- Keep placeholders exactly as-is and in place (e.g. {name}, {{var}}, %s, {0}).
- Keep numbers, URLs, emails, and code literals unchanged.
- If a string is empty, or already in target_lang, return it unchanged.
- Output must be a single valid JSON object matching the given schema, and nothing else: no markdown, no commentary, no explanation.
"""


def build_user_prompt(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    content_type: str = "text",
) -> str:
    """Build the user-turn message for one translation batch.

    content_type is "text" or "html" and tells the model whether `texts`
    contains plain strings or HTML fragments (tags/attributes must survive
    untouched).
    """
    payload = {
        "source_lang": source_lang,
        "target_lang": target_lang,
        "content_type": content_type,
        "texts": texts,
    }
    return json.dumps(payload, ensure_ascii=False)


# --- Response schema --------------------------------------------------------

# Plain JSON Schema: pass this directly to your backend's structured-output
# parameter.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


class TranslationResponse(BaseModel):
    """Pydantic mirror of RESPONSE_SCHEMA, for validating the model's output
    once you've parsed it: TranslationResponse.model_validate_json(raw_output)
    """

    translations: list[str]


# No JSON Schema can express "len(translations) == len(texts)" since that
# depends on the request, not the schema. Always check it after parsing:
#   parsed = TranslationResponse.model_validate_json(raw_output)
#   assert len(parsed.translations) == len(texts)
