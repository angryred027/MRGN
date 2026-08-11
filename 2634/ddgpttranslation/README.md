# Translation Endpoint Tests

Pytest suite for the `/api/v1/llm/agent?type=translation` and `/api/v1/count-tokens` endpoints.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
```

## Configuration

- **Server**: hardcoded in `tests/translation/conftest.py` as `http://localhost:5005`. Edit `BASE_URL` there if it changes.
- **Auth**: tests need a real token, passed via env var (never hardcoded):

```bash
export SESSION_TOKEN=your-real-token
```

Tests that need auth skip automatically if `SESSION_TOKEN` isn't set.

## Structure

```
tests/translation/
  languages.json          # supported language codes
  response.json            # reference response shape
  fixtures/{lang}.json      # test data per target language (42 texts each)
  conftest.py               # shared config/fixtures
  test_auth.py               # missing/valid token -> 401 / 200
  test_translation_response.py  # response schema + input/output count match (3-text sample)
  test_token_count.py        # /count-tokens schema check
  test.py                    # full fixture (all texts) sent per language

tests/artifacts/translation/output/   # saved request/response JSON per language (gitignored)
```

## Running

```bash
# everything test_*.py / *_test.py picks up
SESSION_TOKEN=your-real-token pytest tests/translation -v

# test.py isn't auto-discovered (pytest only collects test_*.py / *_test.py by
# default) - run it explicitly:
SESSION_TOKEN=your-real-token pytest tests/translation/test.py -v
```

Run one language only:

```bash
SESSION_TOKEN=your-real-token pytest tests/translation -k es -v
```
