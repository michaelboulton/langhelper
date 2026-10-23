---
name: audio-course
description: Write the plan of an audio course, as a shell script of the scripts.audio_lessons and scripts.lessons commands that make it. Use when a user asks for a course of N spoken lessons of a language, with or without flashcards, such as "Write the plan of a course of 20 lessons of Italian, with flashcards."
---

# Write the plan of an audio course

The output is one shell script, `.data/audio/<course>/plan.sh` at the
repository root. Write it, but never run it. The user reads it, edits it, and
runs it.

The commands are in `web/scripts/README.md`, sections "audio_lessons.py" and
"Flashcards from the scripts". Read them before you write the plan.

## The input

- The study language. It must be a key of `LANGUAGES` in
  `web/tlhelper/languages/__init__.py`, such as `it` or `hr`.
- The number of lessons.
- The start level, such as "a beginner" or "knows the present tense".
- Optional: the interests of the user, such as cooking or football.

Ask for the language and the number of lessons if the request does not give
them. Take "a beginner" as the default level.

`<course>` is a short slug of the language and the subject, such as
`it-course` or `hr-football`. If `.data/audio/<course>/` has scripts already,
pick another slug, or ask the user whether the plan extends that course.

## The syllabus

Plan the syllabus first: one topic and one grammar step for each lesson, in an
order that gets harder.

- Start on something simple, and end on something hard. Work out the order
  from the grammar of the study language, because the hard parts differ by
  language. Finnish has many cases. Croatian has fewer, but a case also
  changes the words before the noun.
- Two examples, one of each end. They are examples, not a fixed sequence:
  - Simple: two people talk in the present tense about a thing in front of
    them.
  - Hard: a question about what an absent third person will do, or a
    construction particular to the language. For example, Croatian has two
    verb pairs for "to marry". `udavati se ~ udati se` is for a woman as the
    subject, and `ženiti se ~ oženiti se` is for a man. A couple takes the
    male form: `Oženit će se.` ("They will get married.")
- Each lesson adds one step. Split a large point over several lessons, such
  as one case in the singular, then in the plural.
- Start from the level of the user: skip the steps that the user knows.
- The topics are situations that a visitor meets in the country of the
  language, such as food, transport and the local football team. Each topic
  suits its grammar step: a past tense suits "what you did yesterday", and
  a future suits "the plan for the weekend". Use the interests of the user.
- Each topic is different. `scripts.audio_lessons` skips a topic that is in
  the course already.

## The plan script

Use this shape. Replace the values in `<>`, and write one `--topic` command
for each lesson, in the order of the syllabus:

```bash
#!/usr/bin/env bash
# The plan of <name>, <N> lessons of <language>. Read it, edit it, then run
# `bash plan.sh`. A re-run after an error skips the work that is done.
#
# Syllabus (lesson: topic | grammar step):
#  1. <topic> | <grammar step>
#  2. <topic> | <grammar step>
set -euo pipefail
: "${TLHELPER_VOICE_URL:?set it to the voice service, such as http://localhost:8002}"
cd "$(dirname "$0")/../../../web"
COURSE=../.data/audio/<course>
DECKS=../.data/decks/<course>

uv run python -m scripts.audio_lessons --course "$COURSE" --language <code> --name "<name>" \
    --topic "<topic 1>" --grammar "<grammar step 1>"
uv run python -m scripts.audio_lessons --course "$COURSE" --language <code> --name "<name>" \
    --topic "<topic 2>" --grammar "<grammar step 2>"

uv run python -m scripts.audio_lessons --course "$COURSE" --voice

mkdir -p "$(dirname "$DECKS")"
uv run python -m scripts.lessons --language <code> --name "<name>" \
    --course "$DECKS" --voice "$COURSE"/*.txt
```

- `--grammar` is allowed with exactly one `--topic`, so each lesson is its
  own command.
- The scripts are `01.txt`, `02.txt` and so on, so the glob `*.txt` gives
  them to `scripts.lessons` in the order of the course. Each audio lesson
  gets a flashcard subdeck with the same number and title.
- The cards of a lesson use the verbs and nouns of its script and of the
  earlier scripts. So the `scripts.lessons` command comes after every
  `--topic` command, and it gets all the scripts.
- Leave out the `scripts.lessons` command, and the `mkdir` before it, when
  the user wants no flashcards.
- When the course has its scripts already and the user wants only the
  flashcards, the plan has no `scripts.audio_lessons` command and no
  `TLHELPER_VOICE_URL` check, unless the user wants clips of the answers. Keep
  the `mkdir` and the `scripts.lessons` command. Leave out `--voice` when
  the voice service is not wanted.
- When the user has no `TLHELPER_AI_*` variables and uses Claude Code, add
  `--backend claude` to each `scripts.audio_lessons --topic` command and to
  the `scripts.lessons` command.
- Quote each topic and grammar step for bash. Write a grammar step in a few
  words, with an example in the study language, as the `grammar:` line of a
  script has.

## The end

Do not run `plan.sh`. Tell the user where it is, and tell them to read it, to
edit it if needed, and then to run `bash .data/audio/<course>/plan.sh`. Say
that it needs the voice service (`docker compose up voice` at the repository
root) and ffmpeg.

When the plan makes flashcards, also tell the user that the run prints
`verbs and nouns in no lesson: ...` for a card that uses a word of no script,
and that `--redo NN` on the `scripts.lessons` command writes the cards of
lesson NN again.
