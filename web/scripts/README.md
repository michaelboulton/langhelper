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
those of the `web` service there, with the port of the host:

```bash
export TLHELPER_AI_API_BASE=http://localhost:9931/v1 TLHELPER_AI_API_KEY=local TLHELPER_AI_MODEL=gemma-4-12b
```

For a paid service, the key is `TLHELPER_AI_API_KEY` in `.env` at the
repository root (README.md, "Running locally"). Export the variables of that
file, from `web/`:

```bash
set -a; . ../.env; set +a
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
- `--voice`: put a sound clip of each answer in the package, and add listen
  and dictation cards (see "Clips" below). It also builds the package again.
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

### Clips

With `--voice`, the voice service reads the first form of each answer (the
text before the first " / "). The service is the one of the app:
`TLHELPER_VOICE_URL` and the other `TLHELPER_VOICE_*` variables of
`tlhelper/speech/__init__.py`. Start it with `docker compose up voice`, or run
the whole stack. The answer field gets a `[sound:...]` tag, the package holds
the mp3 files, and the toml sets `listen = true` and `dictation = true`. The
app then shows two more cards for each note: one plays the clip and asks for
the English, and one plays the clip and asks for the answer.

The clips stay in the folder `<course>.clips/` next to the memory file. The
name of a clip comes from the language and the text, so a later run asks the
service only for a new or a changed answer. An error of the service stops the
run, and the clips that are in the folder stay.

To add clips to a course that has none, build it again:

```bash
TLHELPER_VOICE_URL=http://localhost:8002 uv run --group lessons \
    python -m scripts.lessons --course decks/croatian-course --build-only --voice
```

A run without `--voice` that builds the package again writes it with no clips,
and the toml with no listen or dictation cards. Give `--voice` on each run of a
course with clips.

### A web page

The page is fetched with `requests`, and the content is the first of
`<article>`, `<main>` and `<body>`, without the navigation, header, footer,
aside, scripts and styles, and without each element whose id or class has
"comment" in it. `markdownify` turns the rest into markdown with the headings,
bold, italic, lists and tables, and without the links and the images. The
markdown is not cached: `--redo` fetches the page again.

## audio_lessons.py: scripts of spoken lessons

A language model writes the script of a spoken lesson for each topic. In a
lesson, two actors have a short dialogue in the study language. Then a
narrator teaches its words in English: the narrator asks for a phrase, a pause
gives the learner time to say it aloud, and an actor says the answer. The
script keeps a memory of the earlier lessons, so each lesson can be a little
harder than the one before it, and it brings back their words. With
`--voice`, the voice service reads each line, and ffmpeg joins the lines of a
lesson into one mp3.

The AI service is the one of `lessons.py` (see "Set-up" above), with
`--backend claude` too. The script needs no extra dependency group. A lesson
costs about 1 to 3 thousand input tokens (a later lesson has more memory) and
about 1 thousand output tokens. `--voice` also needs ffmpeg on the machine
that runs the script (see "Clips and the mp3" below).

### The course folder

```
audio/<course>/
  course.toml   # language, name, and the voice of each speaker
  01.txt        # the script of lesson 1
  01/           # the clips of lesson 1, e.g. 1.05-3fa2c1.mp3
  01.mp3        # lesson 1 as one file
  02.txt
```

`course.toml` has `language` and `name`. The first run writes it. An optional
table `[voices]` gives a speaker a named clip of the voice service
(`../tts/README.md`, "Voice"), such as `"actor 2" = "it-2"`.
`tlhelper/audio_lessons/script.py` reads both kinds of file.

### The script format

One line for each thing that the learner hears:

```
# Is there meat in this dish?
topic: asking whether a dish has meat in it
summary: Asking a waiter whether a dish has meat in it.
grammar: "there is / there isn't" (c'è, non c'è); yes/no questions.

narrator: You are in a restaurant in Rome. Listen to the conversation.
actor 1: Scusi, c'è carne in questo piatto?
actor 2: No, non c'è carne.
narrator: How do you say "is there"?
pause: 3
actor 1: c'è
```

- The first line is `# <title>`.
- `summary:` and `grammar:` are required, before the first spoken line. They
  are the memory of the later lessons. `topic:` is the `--topic` that made the
  lesson, and a script by hand can leave it out.
- The speakers are `narrator` (English), `actor 1` (the role of the learner)
  and `actor 2` (the other person). Both actors speak the study language.
- `pause: N` is N seconds of silence, up to 30.
- Blank lines are ignored. The case of a speaker is ignored, and spaces are
  joined.

An error names the file and the line, such as `01.txt:7: 'actor 3' is not
one of narrator, actor 1, actor 2 or pause`.

### A course, one run at a time

From `web/`:

```bash
uv run python -m scripts.audio_lessons --course ../.data/audio/it-course \
    --language it --name "Italian" \
    --topic "asking whether a dish has meat in it" --topic "the local football team"
```

Each topic becomes the next lesson, in the order given. The number of a new
lesson is the lowest number with no script, so a deleted lesson gets its place
back. A topic that a script has already (the same words, in any case) is
skipped, so a run can repeat the whole list. A later run needs no
`--language` or `--name`.

Other options:

- `--grammar "..."`: the grammar step of the lesson. It is allowed only with
  exactly one `--topic`. With no `--grammar`, the model picks one small step
  harder than the steps of the earlier lessons, and writes it in the
  `grammar:` line.
- `--redo N`: write lesson N again, with the topic and the grammar step of
  its script. To change them, edit the `topic:` and `grammar:` lines first.
- `--dry-run`: print the prompt of the first lesson to write, with a rough
  count of its tokens, and write nothing. With `--voice`, it voices nothing.
- `--voice`: after the scripts, make the clips and the mp3 of each lesson of
  the course (see "Clips and the mp3" below).

A script is written complete or not at all, so a run over many topics that
dies loses at most the lesson it was on.

### The memory and the prompt

The memory is in the scripts, with no other file. For lesson N, the prompt
has:

1. the summary and the grammar step of each lesson before N;
2. the lemmas of the actor lines of those lessons, as in the prompt of
   `lessons.py` (see "The prompt" above);
3. the number, the topic and the grammar step of the lesson;
4. the format, and the rules: about 80 lines; only the grammar of this lesson
   and of the earlier lessons; a dialogue first; each new phrase taught with a
   prompt, a pause and the answer; a long word built up from its end; old and
   new words asked again at growing intervals; the dialogue again at the end.

The answer starts at its first `# ` line, so a code fence or a sentence before
the script does no harm. After an answer that is not a valid script, the
script asks once more and then stops with the answer in the message.

### Clips and the mp3

With `--voice`, the voice service reads each spoken line of each lesson into
one clip, and ffmpeg joins the clips of a lesson into `NN.mp3`. The voice
service is the one of the app: `TLHELPER_VOICE_URL` and the other
`TLHELPER_VOICE_*` variables of `tlhelper/speech/__init__.py`. Start it with
`docker compose up voice` at the repository root. From `web/`:

```bash
TLHELPER_VOICE_URL=http://localhost:8002 uv run python -m scripts.audio_lessons \
    --course ../.data/audio/it-course --voice
```

ffmpeg is a requirement of this script only, on the machine that runs it. No
image needs it. Install it with `apt install ffmpeg` or `brew install ffmpeg`.
Without ffmpeg or without `TLHELPER_VOICE_URL`, the run stops before its
first request.

The voice of each speaker:

- The narrator reads English (`en`) in the default voice of English.
- Actor 1 reads the study language in the default voice of that language.
- Actor 2 reads the study language in the voice that `[voices]` in
  `course.toml` names, such as `"actor 2" = "it-2"`. A voice is a named clip
  of the service (`../tts/README.md`, "Voice"). `check_voices.py` (below)
  writes a sample of it. Without that entry, both actors have the same voice,
  and the run says so.

`[voices]` can name a voice for each of the three speakers.

The clips of lesson N are in the folder `NN/`. The name of a clip is
`<lesson>.<line>-<hash>.mp3`, such as `1.05-3fa2c1.mp3`:

- `<line>` is the number of the spoken line in the lesson. A pause has no
  number. It has two digits, or more for a lesson with more than 99 spoken
  lines, so the names sort by line.
- `<hash>` comes from the language, the voice and the text. A changed line or
  a changed voice gets a new name.

A later run asks the voice service only for the new lines. A line with the
hash of a clip in the folder, such as a line that moved or a line said twice,
gets a copy of that clip. After a good run, the run deletes the clips that no
line uses. An error of the service stops the run, and every clip stays. The
hash does not change when a reference clip of the service changes: to read
a lesson again in the new voice, delete its folder `NN/`.

The mp3 of a lesson has:

- the clips, in the order of the script;
- each `pause: N` as N seconds of silence;
- 0.5 seconds of silence between two spoken lines;
- 64 kbit/s, 24 kHz, mono, as the clips of the voice service.

ffmpeg writes `NN.mp3.tmp`, and the script then renames it, so `NN.mp3` is
complete or not there. A run joins a lesson again only when `NN.mp3` is not
newer than its script and each of its clips.

### Flashcards from the scripts

`lessons.py` reads a script as a lesson: the key is the number of the file,
and the title is the first line. So a course of flashcards with the same
lessons is:

```bash
uv run python -m scripts.lessons --language it --name "Italian" \
    --course ../.data/decks/it-course ../.data/audio/it-course/*.txt
```

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

## check_voices.py: hear each named voice

A check by ear that the voice service has two distinct voices for one
language, such as the two actors of a dialogue. The service clones a named
clip for each `voice` of a request (`../tts/README.md`, "Voice"). The script
asks for the same sentence in each voice that `--voice` names, and writes one
mp3 for each. It needs no extra dependency group.

1. Put each clip and its transcript in `tts/omnivoice_server/voices/`, such
   as `it.mp3` with `it.txt` and `it-2.mp3` with `it-2.txt`. A clip is a WAV
   or an mp3 (`../tts/README.md`, "Voice").
2. Start the service again, so it reads the clips: `docker compose up --build voice`
   at the repository root.
3. Run the script from `web/`:

```bash
TLHELPER_VOICE_URL=http://localhost:8002 uv run python -m scripts.check_voices \
    --language it --voice it --voice it-2
```

It writes `voice-check/it-it.mp3` and `voice-check/it-it-2.mp3`. Each file
must be the sample sentence, and each in its own voice: the voice of its
clip. `--text` reads another text, and `--out` names another folder. The
script has a sample sentence for each language of the app. For another
language, `--text` is needed.

The script stops before a request when the service lists no such voice, and
prints the voices that it has. `scripts.transcribe` on the mp3s checks that
they are speech.
