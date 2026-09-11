import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FIXTURES_DIR = HERE / "fixtures"
ARTIFACTS_OUTPUT_DIR = HERE.parent / "artifacts" / "translation" / "output"

BASE_URL = "http://localhost:5005"
API_VERSION = "/api/v1"
TRANSLATION_PATH = "/api/v1/llm/agent"
COUNT_TOKENS_PATH = f"{API_VERSION}/count-tokens"


@pytest.fixture(scope="session")
def translation_url() -> str:
    return f"{BASE_URL}{TRANSLATION_PATH}"


@pytest.fixture(scope="session")
def count_tokens_url() -> str:
    return f"{BASE_URL}{COUNT_TOKENS_PATH}"


@pytest.fixture(scope="session")
def session_token() -> str | None:
    """Real auth token, supplied at runtime: SESSION_TOKEN=xxx pytest ...

    Never hardcoded. Tests that need a valid token skip (not fail) when
    it's unset, via the `auth_headers` fixture below.
    """
    return os.environ.get("SESSION_TOKEN")


@pytest.fixture()
def auth_headers(session_token: str | None) -> dict[str, str]:
    if not session_token:
        pytest.skip("SESSION_TOKEN env var not set; skipping authenticated test")
    return {"Session-Token": session_token}


def load_fixture(target_language: str) -> dict:
    path = FIXTURES_DIR / f"{target_language}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def pytest_generate_tests(metafunc):
    if "fixture_language" in metafunc.fixturenames:
        languages = sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))
        metafunc.parametrize("fixture_language", languages)


@pytest.fixture()
def fixture_case(fixture_language: str) -> dict:
    return load_fixture(fixture_language)


@pytest.fixture(scope="session")
def artifacts_output_dir() -> Path:
    ARTIFACTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_OUTPUT_DIR


@pytest.fixture(scope="session")
def supported_languages() -> list[str]:
    data = json.loads((HERE / "languages.json").read_text(encoding="utf-8"))
    return data["supported_languages"]
