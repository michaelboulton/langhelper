# langhelper

A web page that helps you learn a language. You enter a sentence in Croatian,
German, French or Italian. The page shows each word with its part of speech,
its base form and its grammar, and it marks grammar errors. It can also do
these things:

- Translate the sentence to English or from English, with a line from each
  word to its English word.
- Ask you flashcards from Anki decks, grade your typed answer, and schedule
  the next review.
- Explain a sentence or an answer with an AI model.
- Read a sentence aloud.

![A Croatian sentence with a color for each part of speech, its English
translation under it, and a line from each Croatian word to its English
word. The wrong form "malog" has a red wavy line, and its card gives the
three grammar problems](docs/breakdown.png)

## Folders

| Folder or file | Contents |
| -------------- | -------- |
| `web/` | The FastAPI app (`tlhelper`) and the page. See [web/README.md](web/README.md) |
| `tts/` | The text-to-speech service for the "Listen" buttons, with OmniVoice. See [tts/README.md](tts/README.md) |
| `pyproject.toml`, `uv.lock` | The uv workspace of the two folders, with one set of locked versions |
| `docker-compose.yml` | A local run of `web`, `tts` and a llama.cpp server for the AI buttons |
| `.data/` | The downloaded models and the databases of a local run. Not in git |
| `docs/` | The pictures of this README |

## How the parts connect

```text
browser ──> web ──> DeepL                 (translation)
             ├────> llama.cpp or an API   (explain with AI)
             └────> tts                   (Listen)
```

Fly.io runs only `web`, with a Pocket ID login. On Fly, the page has no
"Listen" buttons, and it has AI buttons only with an API key. The compose file
runs all three services on one machine and needs no login.

## Quick start

You need [uv](https://docs.astral.sh/uv/). For the containers, you need podman
and podman-compose.

1. Install the dependencies of both folders into one `.venv` at the root:

   ```bash
   uv sync --all-packages
   ```

2. Run the tests. Run them in each folder:

   ```bash
   (cd web && uv run pytest)
   (cd tts && uv run pytest)
   ```

3. Start the page at <http://localhost:8000/>, with no login:

   ```bash
   (cd web && DATA_ROOT=../.data uv run uvicorn tlhelper.app:app --port 8000 --no-access-log)
   ```

4. Or start all the services from the root. Read "Running locally" in
   `web/README.md` first, for the DeepL secret:

   ```bash
   podman-compose up --build --force-recreate
   ```

5. Lint and format with [prek](https://github.com/j178/prek):

   ```bash
   prek run --all-files
   ```

The two Dockerfiles use the root as the build context, because they need the
root `pyproject.toml` and `uv.lock`. To deploy `web` to Fly.io, run this from
the root:

```bash
fly deploy . --config web/fly.toml --dockerfile web/Dockerfile --ha=false
```

After a change to a `pyproject.toml`, run `uv lock` at the root.
