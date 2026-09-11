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

string_utils.py           # sentence splitting / rejoining (pySBD + spaCy)
chunking.py               # chunk_texts: pack messages into token-limit batches
prompt.py                 # system prompt + response schema
test_string_utils.py      # offline, no network
test_chunking.py          # offline, fake token counter
```

## Sentence chunking

A single message can exceed the model's input token limit on its own.
`chunking.build_chunk_plan` splits those on sentence boundaries, packs the
parts into batches that fit, and `ChunkPlan.reassemble` puts the translated
parts back together as one string per input message:

```python
plan = build_chunk_plan(payload, token_limit)
chunk_translations = [translate(chunk) for chunk in plan.chunks]
messages = plan.reassemble(chunk_translations)   # one per payload.texts entry
```

Splitting is language-aware and non-destructive -- `"".join(split_sentences(t, lang)) == t`
for every language in `languages.json`. Backends:

| Backend | Languages |
| --- | --- |
| pySBD | `ar de en es fr hi ja pl ru zh` |
| spaCy `sentencizer`, native tokenizer | `ht pt tl` |
| spaCy `sentencizer`, `xx` multi-language tokenizer | `ko vi` |

`ko` and `vi` use the multi-language tokenizer on purpose: spaCy's own
Korean tokenizer needs mecab-ko/natto-py, and its Vietnamese one needs pyvi
(without it, the tokenizer never separates a trailing `.` from its word, so
no boundary is ever found). No trained spaCy models are needed -- the
`sentencizer` is rule-based, so there is nothing to download.

## Running

```bash
# offline suites -- no server, no token
pytest test_string_utils.py test_chunking.py -v

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
