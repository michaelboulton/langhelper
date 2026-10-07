# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

The repository holds two separate uv projects. Each project has its own `pyproject.toml`, `uv.lock`, `Dockerfile` and `tests/`:

- `classla/`: the language-learning web app. The Python package is `tlhelper`, a FastAPI service. The page is plain JS in `static/`, with no build step.
- `voice/`: the text-to-speech service. The Python package is `omnivoice_server`, a ctypes binding to `libomnivoice.so` behind an OpenAI-shaped speech API.

`classla/README.md` and `voice/README.md` are the full reference: the API, the environment variables, the data files and the deploy steps. Read the relevant section before a change. `classla/CLAUDE.md` has notes for a local run with a real DeepL key.

Other documents in `classla/`:

- `LANGUAGES.md`: the extra work for a study language with a non-Latin script or no spaces.
- `DART.md`: a plan to move `static/` to Flutter. Nothing in it exists yet.
- `scripts/README.md`: admin tools that are not in the image.

### Path drift after a move

The two projects came from a layout with the folders `classla/`, `omnivoice/` and `pocket-id/`. Some files still expect that layout:

- `docker-compose.yml` is at the repository root. It has `build: .` for the classla service and `build: ../omnivoice` for the voice service. The root has no `Dockerfile`, and `omnivoice/` does not exist.
- The root `.dockerignore` lists `omnivoice_server`, so it belongs to `voice/`.
- The READMEs refer to `../omnivoice/` (now `voice/`) and `../pocket-id/` (not in this repository).
- The models of the compose file and of the local run are in `.data/` at the repository root. The READMEs say `./.data` relative to `classla/`.

Ask the user before you fix these paths, because the intended layout is not known.

## Commands

Run each command from the project folder (`classla/` or `voice/`). The projects are not installed, so pytest finds the package through `pythonpath = ["."]`.

```bash
uv run pytest                                          # all tests of the project
uv run pytest tests/flashcards/test_store.py           # one file
uv run pytest tests/flashcards/test_store.py::test_x   # one test
uv run pytest -k grade                                 # tests whose name matches
```

Lint and format from the repository root with [prek](https://github.com/j178/prek). It runs `ruff check --fix` and `ruff format`:

```bash
prek run --all-files
```

Commands for `classla/`:

```bash
DATA_ROOT=../.data uv run uvicorn tlhelper.app:app --port 8000 --no-access-log   # local run, no login
uv run playwright install --only-shell chromium        # one time, for the browser tests
uv run pytest tests/test_browser_breakdown.py --screenshots=shots   # save a PNG of each browser test
uv run pytest tests/test_locales.py                    # check the Fluent catalogs
uv run python -m tlhelper.build_glosses --language de kaikki.org-dictionary-German.jsonl   # rebuild a glosses.db
uv run python -m tlhelper.flashcards.make_toml decks/x.apkg --language hr --name "X"      # write the .toml of a deck
fly deploy --ha=false                                  # deploy to Fly.io
```

Tests that need resources skip when the resources are missing:

- `test_real_models` needs the classla models in the data folder.
- The browser tests need the Playwright Chromium.
- DeepL and the AI service are fakes in the tests, so the tests need no key.
- The `voice/` tests use a fake model and need no build of `libomnivoice.so`.

## classla architecture

### Languages and the model slot

Each study language is a class in `tlhelper/languages/<name>/` that implements the `Language` protocol of `languages/base.py`. `LANGUAGES` in `languages/__init__.py` is the registry. The page builds its language list from `GET /api/v1/languages`, so a new language needs no change to the JS. `classla/README.md`, section "Add a language", has the steps.

A language has a `"light"` variant (a spaCy model) and an optional `"heavy"` variant (classla for Croatian, a transformer for German). `StudySlot` in `languages/base.py` holds only one study model in memory at a time. A request for another language or variant drops the loaded model first. The English model stays outside the slot and is always loaded. Code that needs tags of a study language must go through the slot.

The grammar checks are in `checks.py` or `grammar.py` of each language. They only see the tags, so each check documents its limits in the README. A check adds an English sentence to `problems` and a Fluent key with its parameters to `problem_messages`.

### Pluggable backends

Three packages have the same shape: an interface in `base.py`, an implementation, a `routes.py` (except `translators/`), and a package docstring with the steps to add a backend.

| Package | Interface | Selected by |
| ------- | --------- | ----------- |
| `tlhelper/translators/` | `Translator` (DeepL) | `TRANSLATOR` |
| `tlhelper/explain/` | `Backend` (OpenAI SDK, `claude -p`) | `TLHELPER_AI_BACKEND` |
| `tlhelper/speech/` | `Synthesizer` (OpenAI speech API) | `TLHELPER_VOICE_BACKEND` |

The page hides the AI buttons when no AI key is set, and it hides the Listen buttons when `TLHELPER_VOICE_URL` is not set. The explain prompts are templates in `explain/questions.py`. The page sends only the id of a question and the text of the user, and the server fills in the rest from the review or the card.

### API schemas

`tlhelper/schemas.py` has a Pydantic model for each response, and the routes use it as `response_model`. FastAPI drops a key that the model does not have. When a route returns a new key, add the key to its model.

### Storage

All persistent state is under `DATA_ROOT` (`/data` on Fly):

- `lemmas.db`: the lemma counts and the translation cache (`translator_cache`).
- `flashcards.db`: the imported decks and cards, the FSRS state of each user, the review log, and the cache of AI answers (`explanation`).
- `classla_resources/`: the heavy Croatian models, downloaded on first use.
- `decks/`: more flashcard decks. A deck in this folder wins over a deck with the same stem in `classla/decks/`.

The app migrates rows from older table names at startup and leaves the old tables unchanged. The deck import runs at startup and skips an unchanged deck. Increase `IMPORT_VERSION` in `flashcards/decks.py` when a change to the import must read every deck again.

`accents.db` and the `glosses.db` files in `tlhelper/languages/*/` are generated from Wiktionary by `build_glosses.py`. The image includes them.

### Login

`auth.py` turns on the OIDC login only for a hostname that ends in `AUTH_HOST_SUFFIX` (default `.fly.dev`). A local run has no login, and all flashcard progress belongs to the user `local`. A static file that the browser fetches with no cookie (the manifest, the icons) must be in `OPEN_PATHS` in `auth.py`.

### Text of the page

The UI text is in a Fluent file `ui.ftl` in each language folder. `english/ui.ftl` is the complete catalog. `static/js/i18n.js` has a fallback formatter for a failed load of `@fluent/bundle`, so the catalogs must not use Fluent attributes or functions. `tests/test_locales.py` checks this.

## voice architecture

`native.py` mirrors the structs of `omnivoice.h` at the commit that `voice/Dockerfile` pins (`OMNIVOICE_CPP_COMMIT`). When you change that commit, compare the structs and update `ABI_VERSION`. The reference clips in `omnivoice_server/voices/` are in git LFS. Without `git lfs pull`, the server does not start. `languages.py` is generated and is not for manual edits.

## Documentation style

The READMEs use a controlled, simplified English: short sentences, active voice, simple tenses and one topic for each paragraph. Keep that style in documentation changes. Put explanations in the README of the project, not in long code comments. Each environment variable is listed in the README of its project, so a new variable needs an entry there.
