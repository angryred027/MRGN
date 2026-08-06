"""Materializes tests/translation/fixtures/{lang}.json from sentence_bank.SENTENCES.

For each supported target language, builds a request-shaped fixture containing
3 sentences from every *other* supported language as source text (14 sources
x 3 sentences = 42 texts per fixture). Deliberately large enough to exceed the
endpoint's per-request token limit, so the fixtures double as chunking-logic
test input.

Run directly to (re)generate all fixture files:
    python generate_fixtures.py
"""

import json
from pathlib import Path

from sentence_bank import SENTENCES

HERE = Path(__file__).parent
LANGUAGES_FILE = HERE / "languages.json"
FIXTURES_DIR = HERE / "fixtures"


def load_supported_languages() -> list[str]:
    data = json.loads(LANGUAGES_FILE.read_text(encoding="utf-8"))
    return data["supported_languages"]


def build_fixture(target_language: str, languages: list[str]) -> dict:
    texts = []
    for source in languages:
        if source == target_language:
            continue
        for sentence in SENTENCES[source]:
            texts.append({"messages": sentence, "source": source})
    return {"target_language": target_language, "texts": texts}


def main() -> None:
    languages = load_supported_languages()
    missing = [lang for lang in languages if lang not in SENTENCES]
    if missing:
        raise ValueError(f"sentence_bank.SENTENCES is missing languages: {missing}")

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for target_language in languages:
        fixture = build_fixture(target_language, languages)
        out_path = FIXTURES_DIR / f"{target_language}.json"
        out_path.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {out_path} ({len(fixture['texts'])} texts)")


if __name__ == "__main__":
    main()
