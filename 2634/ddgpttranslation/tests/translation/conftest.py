import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mock_server import TOKEN_LIMIT, app

HERE = Path(__file__).parent
FIXTURES_DIR = HERE / "fixtures"
ARTIFACTS_OUTPUT_DIR = HERE.parent / "artifacts" / "translation" / "output"

MOCK_SESSION_TOKEN = "test-mock-session-token"


@pytest.fixture(scope="session")
def token_limit() -> int:
    return TOKEN_LIMIT


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    return {"Session-Token": MOCK_SESSION_TOKEN}


@pytest.fixture(scope="session")
def supported_languages() -> list[str]:
    data = json.loads((HERE / "languages.json").read_text(encoding="utf-8"))
    return data["supported_languages"]


@pytest.fixture(scope="session")
def artifacts_output_dir() -> Path:
    ARTIFACTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_OUTPUT_DIR


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
