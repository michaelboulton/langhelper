# scripts/

Local tools for the admin. Nothing here runs in the web app or in its image.
Run each one from the folder of the project, as a module, so that it imports
`tlhelper` without an install of the project.

## lessons.py: flashcards from lessons

A language model writes 10 to 20 flashcards for each lesson of a course. The
result is one deck package with a subdeck for each lesson, which the app
imports like any other deck (README.md, "Flashcards"). The script keeps a
memory of the earlier lessons, so the cards of a lesson use the grammar of that
lesson with the words of the lessons before it: the verb "to wander" from
lesson 1 and the past tense from lesson 10 give "We wandered." in the deck of
lesson 10.

### Set-up

The HTML step needs two packages that the image does not have. They are the
dependency group `lessons`:

```bash
uv sync --group lessons
```

The AI service is the one of the app: set `TLHELPER_AI_API_KEY`,
`TLHELPER_AI_MODEL` and, for a service that is not OpenAI,
`TLHELPER_AI_API_BASE` (README.md, "Set up the AI service"). A lesson costs
about 6 to 10 thousand input tokens and 1 to 2 thousand output tokens.

With the `llamacpp` service of docker-compose.yml up, the three variables are
those of the `classla` service there, with the port of the host:

```bash
export TLHELPER_AI_API_BASE=http://localhost:9931/v1 TLHELPER_AI_API_KEY=local TLHELPER_AI_MODEL=gemma-4-12b
```

For a paid service, the key of the podman secret `tlhelper_ai_api_key` goes
straight into the variable, and never into a file:

```bash
export TLHELPER_AI_API_KEY=$(podman secret inspect --showsecret --format '{{.SecretData}}' tlhelper_ai_api_key)
```

With Claude Code installed and logged in, `--backend claude` (or
`TLHELPER_AI_BACKEND=claude`) sends each request through one `claude -p`
process instead, so no key variable is needed. That is the Claude Code
backend of the app (`tlhelper/explain/claude_cli.py`; README.md, "Set up the
AI service"). `TLHELPER_AI_MODEL`, if set, goes to `claude --model` (an alias
such as `sonnet`, or a full name) and is the model in the memory file;
without it, the CLI uses its default and the memory file says `claude`.

### A course, one run at a time

The first run makes the scaffolding: the memory file `<course>.json`, the
package `<course>.apkg` and its `<course>.toml`. It needs the language and the
name of the deck:

```bash
uv run --group lessons python -m scripts.lessons \
    --language hr --name "Croatian course" --course decks/croatian-course \
    lessons/01.md
```

Each later run appends the lessons it gets, in the order given, and builds the
deck again. The language and the name come from the memory file:

```bash
uv run --group lessons python -m scripts.lessons \
    --course decks/croatian-course https://www.easy-croatian.com/2014/11/16.html
```

A lesson is a markdown file or the address of a web page. Its key is the stem
of the path (`03` for `lessons/03.md` and for `https://site/2014/03.html`), so
a lesson that is in the course already is skipped: a run can repeat the whole
list, or give only the new lesson. Its number is its position in the course.
Its title is the first heading of the text, else the title of the page, else
the key; `--title KEY=TITLE` sets it.

The app sees the new files at its next start and imports them again. A card
keeps its guid between two runs (it comes from the key of the lesson and the
English text), so the progress of every user stays, and the new lesson is one
more subdeck.

Other options:

- `--redo KEY`: make the cards of that lesson again. It keeps its number and
  its title. The new cards have new English texts, so they have new guids: the
  progress on that lesson is lost. The same happens with `--title`, because the
  title is part of the key of the subdeck in the app.
- `--dry-run`: print the prompt of the first new lesson, with a rough count of
  its tokens, and write nothing.
- `--build-only`: write the package and the toml from the memory file, with no
  AI call. For after a hand edit of the memory file.
- `--new-per-day`, `--reviews-per-day`: the limits in the toml (10 and 100).

### The memory file

`<course>.json` holds the language, the name, and for each lesson: its key,
number, source, title, the model that answered, a one-sentence summary, the
lemmas that the lesson brought in (`{"VERB": [...], "NOUN": [...]}`), and its
cards. The pydantic models in `lessons.py` (`Course`, `Lesson`, `Card`)
define it, and a key that they do not know is an error, so a typo in a hand
edit does not lose a field silently.

The lemmas come from the tagger of the app (the light model of the language)
run on the answers of the new cards and on the vocabulary that the model
lists. The lesson text itself is not tagged: it mixes English with the study
language, and the tagger would record the English words as lemmas of the
study language.

The file is written after each lesson, complete or not at all, so a run over
many lessons that dies loses at most the lesson it was on.

### The prompt

The system text says that the model is a teacher of the language, that the
answer is JSON only, and that the lesson text is data. The user message has:

1. the numbered summaries of the earlier lessons;
2. the lemmas the learner has seen, by part of speech: all of the last 10
   lessons, then an even sample of the older ones with the verbs first, up to
   400 in all;
3. `Lesson N: title` and the markdown of the lesson, cut at a paragraph after
   20 000 characters;
4. the task: 10 to 20 cards, each with a full English sentence (a bare word
   could make the app swap the sides of the card), an answer in the language
   with " / " between alternatives and no ";", the vocabulary of the lesson,
   and the summary.

The answer is parsed with the `Answer` model. After an answer that is not
valid, the script asks once more with "Answer with JSON only" appended, and
then stops with the answer in the message. A busy service is asked again after
a pause, up to three times.

### The deck

The package has the fields `Front` and `Back` and the Anki deck
`<name>::<NNN> <title>` for each lesson, with three digits so that lesson 100
sorts after lesson 99. The toml sets `subdecks = true` and splits an answer on
" / " only. `tlhelper/flashcards/make_deck.py` has the writer.

### A web page

The page is fetched with `requests`, and the content is the first of
`<article>`, `<main>` and `<body>`, without the navigation, header, footer,
aside, scripts and styles, and without each element whose id or class has
"comment" in it. `markdownify` turns the rest into markdown with the headings,
bold, italic, lists and tables, and without the links and the images. The
markdown is not cached: `--redo` fetches the page again.

## transcribe.py: what a model hears in a voice clip

A quick check that a clip is speech: the mp3 of the voice service
(`tts/` at the repository root), or a reference clip before it goes into
`tts/omnivoice_server/voices/`. The script sends each `.wav` or `.mp3` to a model
that hears audio and prints its transcript. It needs no extra dependency
group.

By default it asks the `llamacpp` service of docker-compose.yml, at
`http://localhost:9931/v1` with the model `gemma-4-12b`. That service hears
audio because its command loads the audio encoder of Gemma (`--mmproj`);
`GET /props` of the server then says `"audio": true`. To ask another service,
set the `TLHELPER_AI_*` variables above: each one that is set replaces its
default.

```bash
uv run python -m scripts.transcribe hr.wav
uv run python -m scripts.transcribe --language Croatian --tries 3 out/*.mp3
```

- A clip in another format: `ffmpeg -i clip.m4a clip.wav` first.
- `--language` names the language in the prompt. Gemma 4 12B knows little
  Croatian: without the name, it often writes Croatian speech as Ukrainian or
  Russian in Cyrillic; with it, the transcript is Croatian but can gain words
  that were not said. So the check is "speech or not" and "about these
  words", not a word-for-word test.
- `--tries N` asks N times per clip: the answers differ, and one odd answer
  says little.
- An answer such as "no audio was provided" means the model heard no speech:
  silence, or noise.
- Temperature 0.3 and a repeat penalty of 1.3 (a parameter of llama-server):
  at temperature 0 with no penalty, Gemma sometimes repeats the empty
  thinking block of its chat template until the token limit.
