# Sentence breakdown for Croatian, German, French and Italian on Fly.io

A small FastAPI service around two taggers. The first is
[classla](https://github.com/clarinsi/classla), the CLARIN.SI language pipeline
for Croatian. The second is [spaCy](https://spacy.io/). It starts with small spaCy models, and loads the large models (classla for
Croatian) only on request. You enter a sentence. The page
shows each word with a color for its part of speech and its base form (lemma).
Select a word to see its MULTEXT-East tag and its grammar features, for example
case, gender, number, tense and person.

The service started with Croatian, and most of this document describes
Croatian. The page has a list of study languages: Croatian, German, French and
Italian. English is always the other side of a translation. The section "Languages"
describes the differences and how to add a language.

On the fly.dev deployment, the page and the API need a login through Pocket
ID. The section "3. Turn on the login" below describes it. A local run has no
login. The API refuses texts over `MAX_TEXT_CHARS`.

## Files

| File             | Purpose                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `tlhelper/app.py` | The FastAPI app: routes, the translation cache, the SQLite lemma counts |
| `tlhelper/translators/` | The machine translators: the `Translator` interface and DeepL. Its docstring says how to add one |
| `tlhelper/explain/` | The "explain with AI" buttons: the `Backend` interface, the OpenAI SDK backend, the Claude Code CLI backend, the questions as prompt templates, and the routes. Its docstring says how to add a backend or a question |
| `tlhelper/speech/` | The "Listen" buttons: the `Synthesizer` interface, the OpenAI-shaped speech API backend (the `tts/` service of this repo), and the routes. Its docstring says how to add a synthesizer |
| `tlhelper/auth.py` | The OIDC login with Authlib. Only active on a fly.dev hostname        |
| `tlhelper/settings.py` | `DATA_ROOT` and `MAX_TEXT_CHARS`, which more than one module reads |
| `tlhelper/schemas.py` | The shapes of the API responses, for the OpenAPI schema |
| `tlhelper/align.py` | Links each word of the study language to its English word in the translation |
| `tlhelper/languages/__init__.py` | The list of languages                                   |
| `tlhelper/languages/base.py` | The `Language` interface, the slot for the one study model in memory, and the checks that all languages share (repeats, spelling) |
| `tlhelper/languages/spacy_words.py` | Tags a text with a spaCy model, for English, German, French, Italian and light Croatian |
| `tlhelper/languages/glosses.py` | Reads the English glosses from a data file               |
| `tlhelper/languages/croatian/` | `light.py` (the spaCy model), `heavy.py` (the classla pipelines), `grammar.py` (grammar checks) and `accents.py` (pitch accent lookup in `accents.db`) |
| `tlhelper/languages/english/` | `checks.py`: the basic checks of an English text that the user enters |
| `tlhelper/languages/german/` | `checks.py`: the grammar checks of a German text            |
| `tlhelper/languages/french/` | `checks.py`: the grammar checks of a French text            |
| `tlhelper/languages/italian/` | `checks.py`: the grammar checks of an Italian text          |
| `tlhelper/flashcards/` | The flashcards. `apkg.py` reads an Anki deck, and `decks.py` imports the decks. `store.py` keeps the progress of each user and the schedule. `grade.py` grades a typed answer, and `routes.py` is the API. `make_deck.py` makes a deck from a text file, and `make_toml.py` writes the `.toml` of a deck |
| `decks/`         | The decks that go in the image. The section "Flashcards" describes the files |
| `scripts/`       | Local tools for the admin, not in the image. `lessons.py` makes a deck of flashcards from the lessons of a course with the AI service. See `scripts/README.md` |
| `tlhelper/build_glosses.py` | Builds the data files below from the kaikki.org export. Not in the image |
| `tlhelper/languages/croatian/accents.db` | Generated SQLite file with the accented word forms and the English glosses from Wiktionary |
| `tlhelper/languages/german/glosses.db` | Generated SQLite file with the English glosses of the German words from Wiktionary |
| `tlhelper/languages/french/glosses.db` | Generated SQLite file with the English glosses of the French words from Wiktionary |
| `tlhelper/languages/italian/glosses.db` | Generated SQLite file with the English glosses of the Italian words from Wiktionary |
| `static/index.html` | The single page. The app serves it at `/`                            |
| `static/js/breakdown.js` | The script of the page, with the fixed color palette. Served under `/static` |
| `static/js/flashcards.js` | The script of the flashcard tab, and the tabs. It uses the functions of `breakdown.js` |
| `static/js/explain.js` | The script of the "explain with AI" buttons on the two tabs. It uses the functions of `breakdown.js` and `flashcards.js` |
| `static/js/listen.js` | The script of the "Listen" buttons on the breakdown tab. It uses the functions of `breakdown.js` and `flashcards.js` |
| `static/js/progress.js` | The script of the progress tab: the numbers and the bar charts of a user. It uses the functions of `breakdown.js` and `flashcards.js` |
| `static/css/breakdown.css` | The style sheet of the page. Served under `/static`           |
| `static/manifest.json`, `static/icon*.svg`, `static/icon*.png` | The web app manifest and the icons, for the install on a phone. See "Install on Android" |
| `pyproject.toml` | Dependencies. Pins `torch` to the CPU-only wheel index of the root `pyproject.toml` |
| `../uv.lock`     | Locked versions of the whole uv workspace. Update with `uv lock --upgrade` |
| `Dockerfile`     | `python:3.12-slim` plus `uv sync --frozen`, runs as uid 1000. Its build context is the repository root |
| `entrypoint.sh`  | Makes sure that `/data` is writable, then execs uvicorn                 |
| `../docker-compose.yml` | Local run with podman-compose and the models in `.data/` at the repository root, with a llama.cpp service for the AI buttons and the `tts/` service for the "Listen" buttons |
| `tests/`         | The tests, one file for each module, with the languages in `tests/languages/` and the flashcards in `tests/flashcards/`. Run them with `uv run pytest` |
| `fly.toml`       | Fly app configuration: one shared-cpu-2x 4 GB machine that stops at idle, and a 2 GB volume |

## API

`POST /api/v1/classify` with a JSON body:

| Field         | Default  | Meaning                                                          |
| ------------- | -------- | ---------------------------------------------------------------- |
| `text`        | required | The text, 1 to `MAX_TEXT_CHARS` characters                       |
| `language`    | `"hr"`   | The study language: `"hr"`, `"de"`, `"fr"` or `"it"`. Another value gets 422 |
| `heavy`       | `false`  | Use the large models of the study language. They are more exact, and the first request waits for their load. The section "Light and heavy models" describes them |
| `nonstandard` | `false`  | Use the models for casual text (slang, missing diacritics). Only Croatian has them, and they are large models |
| `track`       | `true`   | Add the lemmas of this text to the counts                        |
| `translate`   | `false`  | Add an English translation, with the same breakdown              |
| `source`      | `"study"` | The side that the text is in. `"en"` is for an English text     |

```bash
curl -s https://boultonxyz-classla.fly.dev/api/v1/classify \
  -H 'content-type: application/json' \
  -d '{"text": "Ona je bila kod kuće."}'
```

```json
{"type": "light", "language": "hr", "source": "study", "text": "Ona je bila kod kuće.",
 "sentences": [{"text": "Ona je bila kod kuće.",
   "words": [{"id": 1, "text": "Ona", "lemma": "on", "upos": "PRON", "xpos": "Pp3fsn",
              "feats": {"Case": "Nom", "Gender": "Fem", "Number": "Sing", "Person": "3", "PronType": "Prs"},
              "start_char": 0, "end_char": 3, "seen": 1}]}]}
```

Each Croatian word also has an `accent` key, which the example leaves out. The
"Accents" section describes it. Each Croatian word also has a `problems` list,
which is empty for most words. The "Grammar checks" section describes it.

`seen` is the number of times that lemma was counted, this request included. It
is `null` for punctuation, symbols and numerals, which the service does not
count.

If `translate` is set, the response has one more key:

```json
{"translation": {"text": "She was at home.",
   "sentences": [{"text": "She was at home.",
     "words": [{"id": 1, "text": "She", "lemma": "she", "upos": "PRON", "xpos": "PRP",
                "feats": {"Case": "Nom", "Gender": "Fem", "Number": "Sing", "Person": "3", "PronType": "Prs"},
                "start_char": 0, "end_char": 3}]}]}}
```

The English words have no `seen` key, because the service does not count them.
If the translation fails, the Croatian result still returns, and the key holds
the reason: `{"translation": {"error": "DEEPL_API_KEY is not set"}}`.

If `source` is `"en"`, the text is English, and the service translates it to
the study language. The response has the same shape. `text` and `sentences` are
the translation and its breakdown. `translation` is the English text that
you entered, and each of its words has a `problems` list. The section "English
to Croatian" describes it. `translate` and `nonstandard` have no effect. If the
translation fails, `sentences` is empty, and `translation` has the English
breakdown and an `error` key.

`GET /api/v1/lemmas?limit=50&language=hr` returns the most-seen lemmas of one
language. `GET /api/v1/languages` returns the study languages and English, each
with its name, its tag set name, its placeholder text and its dictionary links.
The page builds its list of languages from that. `GET /api/v1/status` returns
the models that are in memory and the model that loads now, as
`{"loading": "Croatian heavy", "loaded": ["English light"]}`. The page asks for
it while it shows the note about the load.

`GET /openapi.json` returns the OpenAPI schema of the API, and `GET /docs`
shows it as a page. The schema has the shape of each request and each response,
with a description of each attribute. The models are in `tlhelper/schemas.py`,
and the docstring under an attribute is its description. If a route returns a
new key, add the key to its model. The app refuses a response that does not fit
the model, and it drops a key that the model does not have.

On the fly.dev deployment, an API call without the login cookie gets 401. The
section "3. Turn on the login" below describes the login. The `curl` examples
work against a local run.

## The volume

The volume at `/data` holds these things:

- `classla_resources/`, the downloaded classla models, which are the heavy
  models of Croatian. The standard models download on the first request that
  sets `heavy`. The nonstandard models download on the first request that sets
  `nonstandard`. The spaCy models are in the image and not on the volume.
- `lemmas.db`, a SQLite file with one row for each language, lemma and part of
  speech: `language_lemma_counts(language, lemma, upos, count, last_seen)`. A
  file from before German has the table `lemma_counts`. The app copies its rows
  one time, as Croatian, and does not change the old table.
- `decks/`, the flashcard decks that the admin adds after the deploy.
- `flashcards.db`, a SQLite file with the imported cards and the flashcard
  progress of each user. The section "Flashcards" describes both.

The two sets of models take 1.1 GB on disk:

| File                       | Size   |
| -------------------------- | ------ |
| `hr/lemma/standard.pt`     | 402 MB |
| `hr/lemma/nonstandard.pt`  | 403 MB |
| `hr/pos/standard.pt`       | 77 MB  |
| `hr/pos/nonstandard.pt`    | 81 MB  |
| `hr/pretrain/standard.pt`  | 151 MB |

One loaded pipeline uses about 2.5 GB of memory, mostly for the lemma
dictionary. The section "Light and heavy models" describes how the app keeps
one model in memory at a time.

## Accents

Croatian has a pitch accent: one syllable of a word has the stress, with a
rising or a falling tone, and vowels are short or long. Normal text does not
show this. The service adds it from a dictionary, as the HJP dictionary shows
it:

| Mark | Meaning                     |
| ---- | --------------------------- |
| `ȁ`  | Short falling accent        |
| `ȃ`  | Long falling accent         |
| `à`  | Short rising accent         |
| `á`  | Long rising accent          |
| `ā`  | Long vowel with no stress   |

The data comes from the Serbo-Croatian entries of the English Wiktionary,
through the [kaikki.org](https://kaikki.org/dictionary/Serbo-Croatian/) export.
The text of Wiktionary has the CC BY-SA 4.0 license, and `accents.db` has the
same license. HJP has no download, and its text is not free, so the service
cannot use it.

The detail card of a word has two links. The first one searches the
English-Croatian dictionary [dict.cc](https://enhr.dict.cc/) for the lemma, for
example `https://enhr.dict.cc/?s=zvati`. The second one opens the front page of
[HJP](https://hjp.znanje.hr/). HJP ignores a word in the address, so you enter
the lemma there.

The accent of a word can change with its form. `kuće` is `kȕćē` as the genitive
singular and `kȕće` as the nominative plural. The lookup uses the lemma, the
case and the number from classla to select the form. The `accent` key of a word
has one of these values:

| Value                                              | Meaning                                                     |
| -------------------------------------------------- | ----------------------------------------------------------- |
| `{"form": "kȕćē", "exact": true}`                  | Wiktionary has this form of the word with its accent        |
| `{"form": "grȃd / grȁd", "exact": true, "ambiguous": true}` | Several readings, and the grammar does not decide  |
| `{"form": "ráditi", "exact": false}`               | Only the dictionary form has an accent in the data          |
| `{"form": "je", "exact": true, "clitic": true}`    | A clitic, a short word with no accent of its own            |
| `null`                                             | No data, or punctuation, a symbol or a numeral              |

Wiktionary gives the accent of each case form for some nouns, for example
`kuća`. For many other nouns, for example `knjiga`, it gives only a few. For most verbs and adjectives it
gives the accent of the dictionary form only. In five test sentences, 14 words
got their exact form, 15 got the dictionary form, 5 were clitics, and 5 had no
data. The page shows a dictionary form in parentheses, because the accent can move: the dictionary form is
`ráditi`, but "I work" is `rȃdīm`.

The lookup does not know two things. It does not move the accent onto a
preposition (`ȕ grād`). It does not select between two words with the same
spelling, for example `grȃd` (city) and `grȁd` (hail).

`accents.db` has 36,551 accented dictionary forms and 242,415 accented word
forms, in 15 MB. To build it again from newer data:

```bash
curl -LO https://kaikki.org/dictionary/Serbo-Croatian/kaikki.org-dictionary-SerboCroatian.jsonl
uv run python -m tlhelper.build_glosses kaikki.org-dictionary-SerboCroatian.jsonl
```

kaikki.org marks that file as deprecated. The script also accepts the full raw
dump from <https://kaikki.org/dictionary/rawdata.html>, because it reads only
the lines with `"lang_code": "sh"`. You can query the file directly:

```bash
sqlite3 tlhelper/languages/croatian/accents.db "SELECT form, gcase, number FROM forms WHERE key = 'kuća|NOUN'"
```

## Grammar checks

classla tags a wrong word by its form, not by what the sentence needs. In
"Pijem kava." it says that `kava` is nominative. An error then shows as two tags
that do not fit together. `languages/croatian/grammar.py` has these checks:

| Check       | Example                   | Rule                                                        |
| ----------- | ------------------------- | ----------------------------------------------------------- |
| Spelling    | `lebdići čamac`           | The lexicon of classla (hrLex, 1.7 million forms) does not have the word |
| Repeat      | `pun je pun je`           | A word or a phrase of up to four words, directly after itself |
| Preposition | `Razgovaram s prijatelj.` | The words after a preposition must have the case it takes    |
| Agreement   | `Vidim lijepa kuću.`      | An adjective must have the case, gender, and number of its noun |
| Genitive    | `Čamac je pun kavu.`      | `pun`, `sit`, `željan`, `gladan`, `žedan`, `svjestan`, and `vrijedan` take a genitive noun |
| Object      | `Pijem kava.`             | A verb in the first or second person holds its subject, so a nominative noun is wrong |

The lexicon is inside the lemma model, so it costs no more memory. The spelling
check skips names, numbers, and foreign words. Many forms have more than one
reading, and the tagger picks one. `jegulja` is the nominative singular and also
the genitive plural. So before a case check flags a noun, it asks the lexicon
about the other readings of the form. If one reading has the correct case, the
noun passes.

A word that fails a check has a reason in its `problems` list:

```json
{"text": "kava", "problems": ["The subject is already in the verb 'Pijem', so this noun is not the subject. An object is usually accusative, but this form is nominative."]}
```

The page shows a red wavy line under that word, and the detail card shows the
reasons.

The checks only see tags, so they have limits:

- They miss an error that is a valid form in that place. "Živim u Zagreb." reads
  as `u` plus the accusative, which is correct grammar with a verb of motion.
- The object check only runs on a sentence with one finite verb, because tags do
  not show the clauses. It skips a third person verb ("Ana pije kava.").
- The object check skips `biti`, `postati`, `ostati`, `zvati`, `kao`, and
  `nego`, which take a nominative.
- "Čamac je pun kava." passes, because `kava` is also the genitive plural: full
  of coffees.
- The agreement check can flag a correct adjective that has its own object, if
  the adjective is not in the genitive list.
- The models learned from correct text, so they sometimes bend a tag to fit. In
  "Imam dva brat." classla says that `brat` is accusative.

## Translation

[DeepL](https://www.deepl.com/pro-api) supplies the English text through its API.

Since July 2026, the free "Developer" plan gives 1 million characters one time.
DeepL does not renew them. The older "API Free" plan, with 500,000
characters each month, is closed to new customers. After the characters are
used up, DeepL refuses the request, and the page shows the reason.

1. Create a DeepL API "Developer" account and copy the key from the account page.
2. Set the key as a secret: `fly secrets set DEEPL_API_KEY=...`

The app keeps each translation in the `translator_cache` table of `lemmas.db`,
with the name of the translator and the codes of the two languages. It sends a
text to DeepL one time only, because the page sends the same text again after
each pause in the typing. An older file has the tables `translation_cache`,
`translations` and `croatian_translations`. The app copies their rows one time
and does not change the old tables.

DeepL is the only machine translator now. The code of each translator is in
`tlhelper/translators/`, behind the `Translator` interface of `base.py`. The
variable `TRANSLATOR` selects one by its name. The docstring of
`tlhelper/translators/__init__.py` gives the steps to add a translator, with
notes for Amazon Translate and Google Cloud Translation.

[spaCy](https://spacy.io/) breaks down the English text with its
`en_core_web_sm` model. The model is a 12 MB Python package in the image, so it
needs no download and no space on the volume. It uses about 50 MB of memory
and stays loaded next to the classla pipeline. Its `xpos` values are Penn
Treebank tags, not MULTEXT-East tags.

### English to Croatian

The page has a selector for the language of the text. If you select English,
DeepL translates the text to Croatian. The page shows the English words first
and the breakdown of the Croatian translation under them. An explicit submit
counts the Croatian lemmas of the translation. German works the same way.

The Croatian grammar checks also run on the translation.
`languages/english/checks.py` checks the English text before the translation. It assumes that you are fluent in
English, so it only looks for a slip that can give a bad translation:

| Check     | Example                  | What it does                                          |
| --------- | ------------------------ | ----------------------------------------------------- |
| Spelling  | `I recieve the mesage.`  | The word list of [pyspellchecker](https://github.com/barrust/pyspellchecker) does not have the word. The reason has a suggestion |
| Repeat    | `My boat is is full.`    | A word or a phrase of up to 4 words directly after itself. "that that" and "had had" pass |
| Agreement | `i is not happy`         | The verb does not agree with its subject, from the parse of spaCy |

The agreement check knows the pronouns, "this", "that", "these", "those", and
common nouns. Two subjects with "and" are plural. It does not check a name, a
noun before "of" ("a lot of people are"), or a noun such as "police" or "team".
A singular subject with "were" passes, because "if he were" is correct.

The spelling check does not look at a name, a number, or the parts of a word
such as `can't` and `gonna`. A long word with no entry gets no suggestion,
because the search for one is slow.

### Links between the words

The page draws a curve from each Croatian word to the English word with the
same meaning. DeepL does not say which word became which, so `align.py` finds
the pairs. The `translation` key has two more lists for them:

```json
{"links": [[0, 0], [2, 2]], "guesses": [[1, 1]]}
```

Each pair is a Croatian word index and an English word index. The indexes count
over the words of all sentences in order, from 0.

- `links` come from the dictionary. The `glosses` table of `accents.db` has the
  English words of each Croatian lemma, from the same Wiktionary export as the
  accents. `kuća` links to the English word whose lemma is `house`. If a word
  matches in several places, the closest place in the sentence wins.
- `guesses` fill a gap. Wiktionary has no entry for `plutajući`. But `moj` links
  to "My", so the English word for `plutajući` is about one word after "My". A
  free English word with the same part of speech near that place is a pair. The
  page draws a guess as a dashed line.

A word with no counterpart gets no curve. That is correct for a word that only
exists for the grammar of one language: `se`, or the English "the", "do", and
the "to" of an infinitive. An English preposition only links to a Croatian
preposition, because a Croatian case often does its work (`vlakom`, by train).

Two words can want the same English word. `morati` is "must" and also "have
to", so in `morate imati` both words match "have". The matching then gives
"must" to `morate`, so that `imati` gets "have".

If both sides have the same number of sentences, a word only links inside its
own sentence. The page then puts each English sentence under its Croatian
sentence. The curves are behind the word chips. Select a word to make its curve
thick.

German has the same links. Its glosses are in
`tlhelper/languages/german/glosses.db`.

## Flashcards

The page has a second tab, "Flashcards". A card shows an English text with its
breakdown, and you enter the text in the study language. The page then shows
three rows. Your answer is on top, with its grammar problems. The English text
is in the middle. The correct answer is at the bottom. Curves link the words of
both answers to the English words. No DeepL call is necessary, because the deck
has both texts.

### Decks

The admin supplies the decks. A deck is two files with the same stem: an Anki
export (`.apkg`) and a `.toml` file that describes it. The app reads two
folders:

- `decks/` in the repository, which goes in the image as `/app/decks`.
- `/data/decks` on the volume. For the same stem, the volume wins.

To add a deck on the volume, copy both files there and restart the machine:

```bash
fly ssh sftp shell
put mydeck.apkg /data/decks/mydeck.apkg
put mydeck.toml /data/decks/mydeck.toml
```

The app imports the decks at the start. If the size and the time of both files
of a deck are the same as before, the app does not read that deck again. A
release that changes the import has a larger `IMPORT_VERSION` in `decks.py`.
The app then reads each deck again one time, and the progress stays.

To remove a deck, delete both files from both folders and restart the app. The
deck leaves the page at the next start. Its rows stay in the database for the
review log. If the files come back, the progress comes back with them.

| Key in the `.toml` | Default        | Meaning                                         |
| ------------------ | -------------- | ----------------------------------------------- |
| `name`             | required       | The name on the page                            |
| `language`         | required       | The study language: `"hr"` or `"de"`            |
| `english_field`    | required       | The name of the note field with the English     |
| `answer_field`     | required       | The name of the note field with the answer      |
| `notetype`         | all note types | Only read these Anki note types (one, or a list) |
| `reverse`          | `false`        | Also make a card that asks for the English      |
| `separators`       | `[" / ", ";"]` | They split a field into several accepted answers |
| `media_fields`     | `[]`           | More note fields with images or sound clips     |
| `new_per_day`      | `10`           | The most new cards for one user in one day      |
| `reviews_per_day`  | `100`          | The most cards that come back in one day        |
| `subdecks`         | `false`        | Make one deck for each Anki deck of the package that has cards |
| `to_english_notetypes` | `[]`       | A note of these note types only gets a card that asks for the English |

An Anki package can hold a tree of decks. Two examples are
`Sentences::Read Training::2` and `Sentences::Speak Training::2`. With `subdecks`, each Anki
deck that has cards becomes its own deck, with its own queue and its own
limits for a day. The page shows these decks as a tree under the `name` of the
package, and you select one of them. The page leaves out the parts that all the
Anki names start with. If a later export has other decks next to a subdeck, the
subdeck keeps its progress.

Some packages put each accepted answer on its own line of the card. For such a
package, set `separators = ["\n"]`. In all other packages, a line break of a
field is a space.

A shared package can have some notes with the two fields the other way round.
The import looks for common English words in the two fields of each note. If
only the answer field has such words, the import swaps the two fields.

To write the `.toml` of a package, use this script:

```bash
uv run python -m tlhelper.flashcards.make_toml decks/mydeck.apkg --language hr --name "My deck"
```

The script prints the note types and the fields of the package, and some of the
cards. It guesses the two fields and the note types from the text of the notes.
If a guess is wrong, give `--english-field`, `--answer-field` or `--notetype`.
If the `.toml` is there already, the script stops, and `--force` replaces it.
If the package has more than one Anki deck, the script also prints the tree.
`--subdecks`, `--to-english-notetype` and `--lines` set the keys for such a
package.

In Anki, the field names are under "Browse", then "Fields". The export type is
"Anki Deck Package (.apkg)". The app reads the new format of Anki (compressed
with zstd) and the format of the option "Support older Anki versions". Select
"Include media" in the export. The app removes the HTML of a field, and it does
not read the schedule of Anki.

A card shows the images and plays the sound clips of its two fields. The media
of the prompt come with the prompt. The media of the answer, and of each field
in `media_fields`, come after the answer. If the English field of a note is
only a picture, the picture is the prompt. Such a note gets no card that asks
for the English. The file types are jpg, png, gif, webp, mp3, ogg, wav and m4a.
The app does not copy the files. For each request of the page, it reads the
file from the package, so the package must stay in the folder.

A note keeps its `guid` in each Anki export. The app uses it as the key of a
card, so a new export keeps the progress of all users. A note that is not in
the new export leaves the queue, and its answers stay in the log.

With no Anki at hand, make a deck from a text file with one
"English, tab, answer" pair on each line:

```bash
uv run python -m tlhelper.flashcards.make_deck decks/mydeck.tsv
```

To make a deck from the lessons of a course, with the AI service writing 10 to
20 cards for each lesson and a subdeck for each lesson, see `scripts/README.md`.

### Grades and the schedule

The app grades the answer by itself. Case, punctuation and extra spaces never
count.

| Answer                                                        | Rating |
| ------------------------------------------------------------- | ------ |
| The same as one accepted answer                               | Good   |
| Only the diacritics are missing (`kuca`, `strasse`, `Maedchen`) | Hard |
| One wrong letter (a slip of the finger)                       | Hard   |
| All other answers, and "I do not know"                        | Again  |

The language of the answer sets the details, in `info.grading` of its class
(`Grading` in `languages/base.py`). The first detail is the letters that people type in another way. `dj` for `đ`
is only Croatian, and `ss` for `ß` is only German. The second detail is how
many wrong letters are a slip. A script with no spaces can also make
punctuation count as nothing, and keep its combining marks. A script with
vowel marks that nobody types can make those marks count as nothing.

A translation can be right in a way that the deck does not know. For that, the
four buttons under the answer change the rating. The keys 1 to 4 do the same.
"Easy" is only available this way. After a change, the app calculates the
schedule again from the card as it was before the answer.

The schedule is FSRS, the default of Anki, from the
[fsrs](https://github.com/open-spaced-repetition/py-fsrs) package with its
default parameters. A new card comes back after 1 minute and after 10 minutes.
After that, the interval grows with each right answer. The queue of a deck has
this order:

1. A card in the learning steps that is due.
2. A card that is due for review, up to `reviews_per_day`.
3. A new card in the order of the deck, up to `new_per_day`.

The app does not show both directions of a note on the same day. A day starts
at 00:00 UTC.

### The progress of each user

`flashcards.db` on the volume has five tables. `deck` and `card` hold the
imported decks. `user_card` holds the FSRS state and the due time of one card
for one user. `review` is the log: one row for each answer, with the typed text,
both ratings and the time that the user needed. Anki has the same split, in
its tables `cards` and `revlog`. `user` holds the name of each login.

The user is the `sub` claim of the Pocket ID login, which never changes. A
local run has no login, so all progress belongs to the user `local`.

The "Progress" tab shows the numbers of the user: the answers, the share that
was not "Again", and the days in a row. One bar chart shows the answers of each
of the last 90 days. A second bar chart shows the share that was not "Again" on
each of these days.

An admin can select another user in the "Progress" tab. An admin is a user
whose login has the custom claim `pocketid_user_group` with the value `admin`.
To set it, open the user in the admin pages of Pocket ID and add the custom
claim there. The claim goes into the session at the login, so log out
(`/auth/logout`) and log in again after a change. The list shows the `name`
claim of each user, saved at each login. A user with no login since this
feature shows as the `sub`. All other users see only the entry "My cards".

"Read it aloud" uses the speech synthesis of the browser. The quality depends
on the device, and some devices have no Croatian voice.

### Flashcard API

| Route | Purpose |
| ----- | ------- |
| `GET /api/v1/decks` | The decks, each with the card counts of the user. A subdeck has a `path`: the name of its package, then the parts of its Anki name |
| `GET /api/v1/decks/{id}/next?heavy=false` | The next card with the breakdown of its prompt, or `{"done": true, "next_due": ...}`. The accepted answers are not in it |
| `POST /api/v1/cards/{id}/answer` | The body is `{"typed": "...", "heavy": false, "elapsed_ms": 4000}`. Grades the answer and schedules the card. Returns `rating`, `diff`, `answers`, `next_due`, `review_id`, and the breakdowns `typed` and `correct` with their links |
| `POST /api/v1/reviews/{id}/rating` | The body is `{"rating": 1}` to `{"rating": 4}`. Changes the rating of the last answer to a card |
| `GET /api/v1/flashcards/stats?deck=1&of=sub` | The numbers of the user, for one deck or for all. `of` is the `sub` of another user. If the user is not an admin, `of` gives 403 |
| `GET /api/v1/flashcards/users` | The users whose numbers the user can see, as `{"me": ..., "admin": false, "users": [{"id": ..., "name": ...}]}`. The first entry is the user |
| `GET /api/v1/decks/{id}/media/{name}` | An image or a sound clip of a card of the deck. `next` and `answer` give these addresses in `media`, as `{"kind": "image", "url": ...}` |

Not done yet: a hint, "skip", "suspend this card", and the automatic suspend of
a card that fails often. A `TODO` in `store.py` describes where they go.

## Explain with AI

A translation does not say how people use a sentence, or why an answer to a
flashcard is wrong. If the server has a key for an AI service, the page shows
a row of questions for that. The breakdown tab has the questions about a
sentence. A flashcard has them after the answer, together with the questions
about the answer.

| Question | About | What the AI does |
| -------- | ----- | ---------------- |
| What does this mean? | a sentence | Gives the rough meaning of the sentence and its usual use |
| Explain the grammar | a sentence | Says why the important words have their form |
| Is this colloquial? | a sentence | Gives the register of the sentence: formal, neutral, colloquial, or an idiom |
| Why is my answer wrong? | an answer | Gives the rule behind the correct answer |
| Is my answer also correct? | an answer | Starts with Yes or No. You can then change the rating |
| What is the difference? | an answer | Compares the words of the two answers |

The user can add a short text to the question, for example "why this verb?".

The server writes the prompt. A question is a template in
`tlhelper/explain/questions.py` with names such as `{flashcard_input}`,
`{user_input}`, `{correct_answer}`, and `{user_context}`. For a flashcard, the
server reads the values from the review and its card. The page sends only the
id of the question and the text of the user. Nobody can thus use the route as
a free door to the AI service. A review exists only after an answer, so the
route cannot show the answer of a card early.

The prompt also has the notes of the tagger, which help a small model. For each
word, the notes give the lemma, the part of speech, and each feature with its
name. They also give the relation to another word, for example
`kavu (kava: NOUN Case=Acc Gender=Fem Number=Sing; object of Pijem)`. The
system text tells the model that a tagger can be wrong.

The notes come from the model of the language that is in memory, light or
heavy. The server holds only one model of a study language, so a question never
asks for another one. If no model of the language is in memory, the light model
loads. classla has no parser, so the notes of a heavy Croatian model have no
relations.

The text goes to the AI service, so the page makes a request only after a
click. The page shows the answer as plain text, with the name of the model and
a note that it can be wrong.

### Set up the AI service

The backend is the OpenAI SDK, which can call each service that has the chat
completions API of OpenAI. A Claude or a Gemini subscription gives no API
access. The key must be an API key with credit.

Each variable has the prefix `TLHELPER_AI_`. The app gives the key and the
address to the SDK, and does not use the `OPENAI_API_KEY` of another tool.

1. Set the key as a secret: `fly secrets set TLHELPER_AI_API_KEY=...`
2. Set `TLHELPER_AI_MODEL` to a model of the service. A small model is enough.
3. If the service is not OpenAI, set `TLHELPER_AI_API_BASE`.

| Service | `TLHELPER_AI_API_BASE` |
| ------- | ------------- |
| OpenAI | empty |
| Anthropic | `https://api.anthropic.com/v1/` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| Ollama | `http://localhost:11434/v1`, and the key can be any text |
| llama.cpp | `http://localhost:8080/v1`, and the key can be any text |

`docker-compose.yml` at the repository root has a `llamacpp` service on port
9931, and the `web` service there uses it. The local run therefore needs no key and sends no text to a third
party.

The second backend is Claude Code: `TLHELPER_AI_BACKEND=claude` runs one
`claude -p` process for each request, with no tools and no session file. The
login of the CLI is the credential, so it needs no key. It is for a local run
and for `scripts/` (the image has no CLI). `TLHELPER_AI_MODEL` then goes to
`claude --model`, as an alias such as `sonnet` or a full model name.

Three things limit the cost. `TLHELPER_AI_MAX_TOKENS` limits one answer.
`TLHELPER_AI_PER_DAY`
limits the requests of one user in a day. The table `explanation` in
`flashcards.db` keeps each answer, so the same question about the same text
makes no second request.

### Explain API

| Route | Purpose |
| ----- | ------- |
| `GET /api/v1/explain/questions` | The questions, and `available`. With no key on the server, `available` is false |
| `POST /api/v1/explain` | The body is `{"text": "...", "language": "hr", "question": "meaning", "user_context": ""}`. Only a question about a sentence |
| `POST /api/v1/reviews/{id}/explain` | The body is `{"question": "why_wrong", "user_context": ""}`. Each question, about a review of the user |

Both `POST` routes return `{"text": ..., "model": ..., "cached": false}`. The
errors are 503 for no key, 502 for a failure of the AI service, and 429 for
the limit of a day.

## Listen

A learner wants to hear a sentence, and the voices of a browser are of mixed
quality (see "Read it aloud" above). If the server has the address of a voice
service, the breakdown tab shows a row "Listen:" under the breakdown, with
one button for each side: the text in the study language, and its English
translation when there is one. A click sends that text to the service, and
the page plays the mp3 in an audio element. The row names the voice model.

The voice service is [`tts/`](../tts/) in this repo: a small
server around omnivoice.cpp, the ggml port of OmniVoice, a text-to-speech
model for 600 languages that runs on the CPU. `docker-compose.yml` runs it as the `voice` service next to the
page. The Fly app has no voice service, so the page there has no such row,
as it has no AI buttons without a key.

The text goes to the voice service, so the page makes a request only after a
click. The server keeps no sound. The mp3 is a `GET` with the text and the
language in the address, and the answer has `Cache-Control: private,
max-age=86400`, so the browser keeps it for a day: a click on the same text
plays the kept mp3, and no request goes out. A `POST` could not do that,
because browsers do not keep the answer of a `POST`. The `omnivoice` service
keeps its last mp3s too, so another browser that asks for the same text gets
it without a new generation.

### Set up the voice service

The backend talks to each service with the speech API of OpenAI:
`GET /v1/models` and `POST /v1/audio/speech`. A model entry of the list with
a `languages` field limits the buttons to those languages; the `omnivoice`
service sends one. An entry with no such field (OpenAI itself) is taken to
read every language of the page.

1. Set `TLHELPER_VOICE_URL` to the address of the service, with no path.
   The compose file sets `http://10.89.231.11:8002`, the fixed address of the
   `voice` service on its network.
2. `TLHELPER_VOICE_MODEL` names the model. Default: the first one in the
   list of the service.
3. `TLHELPER_VOICE_API_KEY` goes in the `Authorization` header, for a paid
   service. The `omnivoice` service wants none.
4. `TLHELPER_VOICE_TIMEOUT` (default 180) is the most seconds for one
   request. A CPU reads a long text slowly.

### Speech API

| Route | Purpose |
| ----- | ------- |
| `GET /api/v1/speech` | `{"available": true, "model": "Serveurperso/OmniVoice-GGUF", "languages": ["hr", "en"]}`. With no service on the server, `available` is false |
| `GET /api/v1/speech/audio?text=Dobar%20dan.&language=hr` | `language` is a study language or `en`. Returns the mp3 as `audio/mpeg`, with the model in the `X-Voice-Model` header, and `Cache-Control: private, max-age=86400` |

The errors are 503 for no service, 422 with the code `voice-language` for a
language that the service does not read, and 502 for a failure of the
service.

## Languages

The page has a list of study languages. English is always the other side, so
each language only needs glosses to English.

| Language | Light model             | Heavy models                              | Tag set       | Extras                       |
| -------- | ----------------------- | ----------------------------------------- | ------------- | ---------------------------- |
| Croatian | spaCy `hr_core_news_md` | classla, standard and nonstandard         | MULTEXT-East  | Pitch accents, `accents.db`  |
| German   | spaCy `de_core_news_md` | spaCy `de_dep_news_trf`                   | STTS          | `glosses.db`                 |
| French   | spaCy `fr_core_news_md` | None                                      | None          | `glosses.db`                 |
| Italian  | spaCy `it_core_news_md` | None                                      | ISDT          | `glosses.db`                 |
| English  | spaCy `en_core_web_sm`  | None                                      | Penn Treebank | Only as the other side       |

classla only has models for South Slavic languages, so German, French and
Italian use spaCy.

### Light and heavy models

The app starts with the light models, so it answers a few seconds after a
boot. A request with `heavy` (the "Large models" checkbox on the page) loads
the heavy models of that language, and waits for that load.

The breakdown tab and the flashcard tab share one "Large models" checkbox
value, which the browser keeps in localStorage. If the user did not make a
choice, the page ticks the box only when `TLHELPER_ALWAYS_LARGE` is `1`. The
compose file sets it. The `large_by_default` key of `GET /api/v1/languages`
gives the value to the page.

| Model                 | In the image | On the volume | Memory  | Load   |
| --------------------- | ------------ | ------------- | ------- | ------ |
| Croatian light        | 64 MB        | None          | 80 MB   | 0.3 s  |
| Croatian heavy        | None         | 630 MB        | 2.2 GB  | 9 s    |
| Croatian nonstandard  | None         | 484 MB more   | 2.2 GB  | 9 s    |
| German light          | 42 MB        | None          | 350 MB  | 1.5 s  |
| German heavy          | 391 MB       | None          | 550 MB  | 1.5 s  |
| French light          | 44 MB        | None          | 400 MB  | 2.7 s  |
| Italian light         | 52 MB        | None          | 250 MB  | 0.7 s  |
| English               | 12 MB        | None          | 70 MB   | 0.5 s  |

The memory and the load times are from a laptop, and the Fly machine has
slower CPUs. The whole process uses about 410 MB with Croatian light and
English, and about 2.6 GB with Croatian heavy. The load of German heavy needs
about 1.6 GB more than the table says for a moment.

`StudySlot` in `languages/base.py` holds the one model of a study language that
is in memory. A request for another model (another language, or the other
weight) drops the loaded one first and then loads the new one. The English
model is not in the slot and always stays loaded. After a drop, the app calls
`malloc_trim`, so glibc gives the freed memory back to the system.

The light Croatian model comes from the same corpus as the classla models
(hr500k), so its tags are the same. It is less exact. spaCy reports about 92
correct lemmas and cases of 100 for it. It reads the case of a wrong word from
the context more than classla does. So it misses "Pijem kava" and "Vidim
lijepa kuću", and the heavy models flag both. It has no spelling check, because
that check uses the lexicon inside the classla lemma model. For a noun form
with several readings, it asks the noun forms of `accents.db` in place of that
lexicon. A noun that has no forms there passes.

The heavy German model is a BERT model. spaCy reports 97 correct cases and
genders of 100 for it, and 92 for the light one. Both have the same tags and
parse labels, so the checks are the same. It needs torch, which classla
already brings.

`languages/german/checks.py` has these checks:

| Check       | Example              | What it does                                              |
| ----------- | -------------------- | --------------------------------------------------------- |
| Spelling    | `Ich habe Hungr.`    | The German word list of pyspellchecker does not have the word. A compound of known words passes (`Luftkissenfahrzeug`) |
| Repeat      | `Ich habe habe Zeit.` | The same check as for the other languages. "die die" and "der der" pass, because a relative pronoun can stand before an article |
| Agreement   | `mit der Hund`       | An article or an adjective does not have the gender or the number of its noun |
| Ending      | `ein kleine Hund`    | The adjective ending does not fit the article type, the case, the gender and the number |
| Preposition | `mit den Hund`       | The article, the adjective or the pronoun does not have a case that the preposition takes |

spaCy reads the case of a word from its context, and a German noun mostly has
the same form in each case. So the case checks only trust an article, an
adjective and a pronoun. They miss an error that is a valid form in that place:
"Ich wohne in die Stadt" reads as `in` with the accusative.

To build `glosses.db` again from newer data (the download is 1 GB):

```bash
curl -LO https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl
uv run python -m tlhelper.build_glosses --language de kaikki.org-dictionary-German.jsonl
```

French has only a light model. It has no tag set of its own: its tag is the
UPOS, so the page shows no tag row. Its parse labels are Universal
Dependencies.

`languages/french/checks.py` has these checks:

| Check     | Example                | What it does                                              |
| --------- | ---------------------- | --------------------------------------------------------- |
| Spelling  | `La maizon est belle.` | The French word list of pyspellchecker does not have the word. A word with an apostrophe or a hyphen (`l'`, `peut-être`) is not checked |
| Repeat    | `Je je mange.`         | The same check as for the other languages. "nous nous" and "vous vous" pass, because a subject can stand before its reflexive pronoun |
| Agreement | `une petit chat`       | An article (`det`) or an adjective (`amod`), before or after the noun, does not have the gender or the number of the noun |

spaCy reads the gender of a noun from its article. So "le maison" passes: the
model reads `maison` as masculine. The check finds the error when another word
shows the gender ("la grand maison", "une petit chat"). An adjective after
`être` ("la maison est grand") is not checked.

The French glosses come from Wiktionary in the same way:

```bash
curl -LO https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl
uv run python -m tlhelper.build_glosses --language fr kaikki.org-dictionary-French.jsonl
```

The gloss keys have no grave or acute accent (`glosses.py`), so `à` and `a` are
one key. The part of speech in the key keeps most of those words apart
(`a|ADP` for `à`, `avoir|AUX` for `a`).

Italian has only a light model. Its tags are the ISDT set of the Italian
Stanford Dependency Treebank (`S` noun, `A` adjective, `RD` definite article,
`E_RD` preposition with an article, `PC` clitic pronoun), and its parse labels
are Universal Dependencies. A preposition with an article (`sul`, `della`) is
one word with a lemma of two words (`su il`, `di il`), and an elision (`l'`,
`un'`, `c'`) is a word of its own. The model reads a capitalized verb at the
start of a sentence badly: "Sto mangiando" makes `Sto` a name, and "Io sto
mangiando" does not.

`languages/italian/checks.py` has these checks:

| Check     | Example                  | What it does                                              |
| --------- | ------------------------ | --------------------------------------------------------- |
| Spelling  | `Vedo la maccina.`       | The Italian word list of pyspellchecker does not have the word. A word with an apostrophe (`l'`, `un'`) is not checked. The list has 120,000 words and misses some loan words (`hovercraft`, `weekend`) |
| Repeat    | `Io io mangio.`          | The same check as for the other languages                 |
| Agreement | `una piccolo gatto`      | An article (`det`) or an adjective (`amod`), before or after the noun, does not have the gender or the number of the noun |

As in French, spaCy reads the gender of a noun from its article, so "il casa"
passes, and "il gatti" passes because the model then drops the number of the
noun. The check finds the error when another word shows the gender or the
number ("la piccolo casa", "una macchina rosse"). An adjective after `essere`
("la casa è grande") is not checked.

The Italian glosses come from Wiktionary in the same way:

```bash
curl -LO https://kaikki.org/dictionary/Italian/kaikki.org-dictionary-Italian.jsonl
uv run python -m tlhelper.build_glosses --language it kaikki.org-dictionary-Italian.jsonl
```

The file is 15 MB, twice the French one, because Italian Wiktionary has an
entry for each verb form. Wiktionary glosses the articles with "the" and "a",
which the build drops as stopwords, so the Italian class has them as
`extra_glosses`, with the two-word lemmas of the prepositions with an article.

### Add a language

The machine translator must support the language, and a tagger must exist that
gives Universal POS tags, lemmas and features. If DeepL has another code for the
language than its ISO 639-1 code in capital letters, add the code to
`tlhelper/translators/deepl.py`.

1. Make a folder `tlhelper/languages/<name>/` with a class that implements
   `Language` from `languages/base.py`: `info`, `extra_glosses`, `warm_up`,
   `status`, `analyze` and `glosses`. For a spaCy model, `SpacyTagger` in
   `spacy_words.py` does the tagging, and the German class is a short example.
   Give each tagger a `slot_key` of the language code and the model type, so
   its model goes in the slot. The first of `info.variants` must be `"light"`,
   a model that loads in a second or two. A `"heavy"` one is optional. If
   people type some letters of the language in another way, set
   `info.grading` for the flashcard answers.
2. Put the grammar checks in the same folder. `base.py` has the repeat check
   and the spelling check for a language that pyspellchecker has.
3. Add the class to `LANGUAGES` in `languages/__init__.py`. The page reads its
   list from the API, so it needs no change.
4. Add the language to `LANGUAGES` in `build_glosses.py`, and build its gloss
   file in the folder of the language. The image gets the file with the code.
5. For a spaCy model, pin its wheel in `pyproject.toml`.

These steps are enough for a language with the Latin script and with spaces
between its words. [LANGUAGES.md](LANGUAGES.md) lists the extra work for
another script, with sections for Japanese, Thai, Arabic, and Hebrew. For a
script that goes from right to left, set `direction="rtl"` in `info`.

### The language of the page

The page has its text in English, Croatian, German, French and Italian. The
study language and the language of the page are separate: a person who reads
German can study Croatian. The page uses the first language of the browser that it has, and
English for another one. The list "Language of the page" changes it. The
choice stays in `localStorage` and in the address (`?locale=hr`).

The text of each language is one Fluent file, `ui.ftl`, in the folder of the
language. [Fluent](https://projectfluent.org/) is a format for messages that
lets a translator select a text by a number or by a grammar value.

| File                                 | Use                                   |
| ------------------------------------ | ------------------------------------- |
| `tlhelper/languages/english/ui.ftl`  | The complete catalog, with the notes on each message |
| `tlhelper/languages/croatian/ui.ftl` | The Croatian text                     |
| `tlhelper/languages/german/ui.ftl`   | The German text                       |
| `tlhelper/languages/french/ui.ftl`   | The French text                       |
| `tlhelper/languages/italian/ui.ftl`  | The Italian text                      |
| `tlhelper/locales.py`                | Finds the files and serves them       |
| `tlhelper/messages.py`               | `Problem` and the errors with a code  |
| `static/js/i18n.js`                  | Loads the catalogs, and has `t()`     |

`GET /api/v1/locales` lists the languages, and
`GET /api/v1/locales/{code}/ui.ftl` gives one file. The page gets the English
file and the file of the user. A message that a file does not have shows in
English. A machine wrote the first Croatian, German, French and Italian files,
so a person who speaks the language must read them.

Python does not format the text of the page. A grammar check gives the English
sentence as before, and also the id and the parameters of a message:

```json
{"problems": ["The preposition 'u' takes the locative here, but this form is accusative."],
 "problem_messages": [{"key": "problem-preposition-case",
                       "params": {"word": "u", "want": "Loc", "got": "Acc"}}]}
```

An error with a message has `code` and `params` next to `detail`, and the
message is `error-{code}`. A failed translation has `error_code` and
`error_params` next to `error`. `/api/v1/status` has `loading_model` next to
`loading`. Another client of the API can ignore these keys.

The answers of the AI are in the language of the page. The page sends `locale`
with a question, and the prompt then says "The learner knows German. Answer in
German". The instructions of the prompt stay in English, because a small model
follows English instructions best. The cache has one answer for each language.
If the study language is also the language of the page, the app still works,
but the AI then explains German in German.

The page loads the Fluent runtime (`@fluent/bundle`) from jsDelivr, with an
exact version and an `integrity` hash in `static/index.html`. For another
version, change the address and compute the hash again:

```bash
curl -s https://cdn.jsdelivr.net/npm/@fluent/bundle@0.19.1/index.js \
  | openssl dgst -sha384 -binary | openssl base64 -A
```

If the script does not load, the page shows English with a small formatter of
its own, and the list of languages is hidden. That formatter has no attributes
and no functions, so the catalogs do not use them (`tests/test_locales.py`).
If the app gets a `Content-Security-Policy` header, `script-src` must allow
`cdn.jsdelivr.net`.

To add a language of the page:

1. Set `ui_locale` (a BCP 47 tag) and `native_name` in the `info` of the
   language. For a language that is not a study language, the class still
   needs a folder in `tlhelper/languages/`, and `locales.catalogs()` must
   list it.
2. Copy `english/ui.ftl` to the folder of the language and translate the text
   after each `=`. Keep each `{ $name }` as it is. Use the plural forms of the
   language in each selector, for example `[one]`, `[few]` and `*[other]` for
   Croatian.
3. Add the message `language-name-<code>` to each catalog.
4. Run `uv run pytest tests/test_locales.py`. It makes sure that each file
   parses and that a translation uses only the variables of the English
   message. It gives a warning for each message with no translation.

### Install on Android

Chrome on Android can install the page as an app, with its own icon on the
home screen. Open the page, open the Chrome menu, and select "Add to home
screen" or "Install app". The installed app opens `/` with no address bar.

The page links `static/manifest.json`, a web app manifest (a JSON file that
gives the name, the start address and the icon of the app). The icon is
`static/icon.svg`: a circle in the blue, white and red of the Croatian flag.
`static/icon-maskable.svg` is the same design on the full square, with no
circle. Android cuts it to the icon shape of the phone, so the icon fills that
shape and has no white border.

The PNG files are the same icons at fixed sizes, because Android makes the
installed app from a PNG icon of 192 or 512 pixels. If you change an SVG file,
render the PNG files again at the same sizes, for example:

```bash
rsvg-convert -w 512 -h 512 static/icon.svg -o static/icon-512.png
```

Chrome fetches the manifest and the icons with no cookie. On the fly.dev host,
`OPEN_PATHS` in `tlhelper/auth.py` lists these files, so they need no login.
A new icon file must also go in that list. Otherwise Chrome gets the redirect
to the login page, and says that the app cannot be installed.

Chrome installs the page only from an HTTPS address or from `localhost`. A
local run on a LAN address over HTTP gets only a bookmark on the home screen.

## If the model download is slow

classla downloads every model from one host, `www.clarin.si`. The
`resources_2.2.json` file in
[clarinsi/classla-resources](https://github.com/clarinsi/classla-resources)
lists no other URL, and Hugging Face has no copy. The speed of that host
changes a lot. On 2026-09-18 it sent about 5 kB/s. On 2026-09-19 it sent
44 MB/s, and the full download took 30 seconds.

If the host is slow on the day of the first deploy, use one of these:

- Copy a local download to the volume. Run the app locally one time, then send
  each file in `.data/classla_resources/hr/` to the same path under
  `/data/classla_resources/hr/` with `fly ssh sftp shell`. classla compares
  each file with the MD5 hash from `resources.json`, and it keeps a file that
  matches.
- Set `MODEL_URL` to a mirror that you control. The mirror must serve the same
  paths as clarin.si, for example `<MODEL_URL>/11356/1829/baseline_lemma_lemmatizer.zip`.
  The `link` values in `resources_2.2.json` list the paths. classla asks for
  the path with `.zip` added first, then for the plain path.

## 1. Create the app and the volume

From the repository root, because the image builds from the uv workspace
there:

```bash
fly apps create boultonxyz-classla             # first time only; change the name in fly.toml if taken
fly volumes create classla_data -r lhr -s 2 --config web/fly.toml   # first time only; the models take 1.1 GB
```

## 2. Deploy

```bash
fly deploy . --config web/fly.toml --dockerfile web/Dockerfile --ha=false   # --ha=false: one machine, not Fly's default of two
fly logs --config web/fly.toml                     # shows "Application startup complete."
curl https://boultonxyz-classla.fly.dev/healthz   # -> ok
```

The app opens its port first and loads the light models in a background
thread. A classify request that arrives early waits until they are ready.

The first request with `heavy` for Croatian downloads the classla models from
clarin.si to the volume. If that takes more than a few minutes, read "If the
model download is slow" above. Later requests only load the models from the
volume.

## 3. Turn on the login

On a hostname that ends in `.fly.dev`, every route except `/healthz` needs a
login through [Pocket ID](https://pocket-id.org/), the OIDC provider at
`https://boultonxyz-pocket-id.fly.dev` (`OIDC_ISSUER` in `fly.toml`). A local
run has no login. `auth.py` uses Authlib and the authorization code flow
with PKCE. The client is a public client, so there is no client secret.

1. Add an OIDC client in the admin pages of Pocket ID, with these values:
   - Name: `classla`
   - Callback URL: `https://boultonxyz-classla.fly.dev/auth/callback`
   - Public Client: on
2. Put the client ID into `OIDC_CLIENT_ID` under `[env]` in `fly.toml`. A
   public client has no secret, so the client ID is safe to commit.
3. Create the secret that signs the session cookie:
   `fly secrets set SESSION_SECRET="$(openssl rand -base64 32)"`
4. Deploy again and open the page. Pocket ID asks for the passkey, then sends
   you back to the page.

A session lasts 7 days (`SESSION_MAX_AGE`, in seconds). Open `/auth/logout` to
drop it. If `OIDC_CLIENT_ID` or `SESSION_SECRET` is missing on a fly.dev
hostname, the app answers 503 on every route except `/healthz`. It never falls
back to public.

The browser sends the login cookie with the API calls of the page. A script
cannot log in with a passkey, so point scripts at a local run.

## Cost

When there are no requests, Fly stops the machine (`auto_stop_machines =
'stop'`, `min_machines_running = 0`). The Fly proxy starts it on the next
request. While the machine is idle, you only pay for the rootfs and the 2 GB
volume. The first request after idle waits while the container boots and loads
the light models. On a laptop the app answers 4 seconds after its start. The
time on Fly is not measured yet.

The machine has 4 GB of memory because one classla pipeline uses about 2.5 GB.
The peak during the switches between the heavy models was under 3.5 GB. A
service with only the light models needs about 450 MB.

## Optional environment variables

Set under `[env]` in `fly.toml`:

- `MAX_TEXT_CHARS`: the longest text that the API accepts. Default `1000`.
- `DATA_ROOT`: where the models and `lemmas.db` live. Default `/data`.
- `STATIC_DIR`: the folder with the page, its script, and its style sheet.
  Default: `static/` next to `tlhelper/`. The image sets `/app/static`.
- `MODEL_URL`: a mirror for the model files. Default: clarin.si.
- `DOWNLOAD_MODELS`: set to `0` to never download the models. Default `1`. The
  app always tries the models on disk first, with no network access.
- `OIDC_ISSUER`: the address of the OIDC provider. Set to the Pocket ID app in
  this repo.
- `OIDC_CLIENT_ID`: the client ID from Pocket ID. See "3. Turn on the login".
- `AUTH_HOST_SUFFIX`: the login applies to a hostname with this ending.
  Default `.fly.dev`. Set to an empty string to turn the login off everywhere.
- `SESSION_MAX_AGE`: how long a login lasts, in seconds. Default `604800`
  (7 days).
- `TRANSLATOR`: the name of the machine translator. Default `deepl`, which is
  the only one now.
- `TLHELPER_AI_MODEL`: the model for the "explain with AI" buttons. Default:
  none, and then the page has no such buttons.
- `TLHELPER_AI_API_BASE`: the address of the AI service. Default: that of
  OpenAI. See "Set up the AI service".
- `TLHELPER_AI_MAX_TOKENS`: the most tokens of one answer of the AI. Default
  `500`. A model that thinks before it answers needs more.
- `TLHELPER_AI_PER_DAY`: the most requests of one user to the AI service in a
  day. Default `50`.
- `TLHELPER_AI_BACKEND`: the name of the AI backend. Default `openai`, which is
  the only one now.
- `TLHELPER_ALWAYS_LARGE`: set to `1` to tick "Large models" on the page until
  the user makes a choice. Default: not set. The compose file sets it.
- `TLHELPER_VOICE_URL`: the address of the voice service for the "Listen"
  buttons. Default: none, and then the page has no such buttons. The compose
  file sets it. See "Set up the voice service".
- `TLHELPER_VOICE_MODEL`: the model of the voice service. Default: the first
  one that the service lists.
- `TLHELPER_VOICE_TIMEOUT`: the most seconds for one request to the voice
  service. Default `180`.
- `TLHELPER_VOICE_BACKEND`: the name of the speech backend. Default `openai`,
  which is the only one now.

Set as a secret:

- `TLHELPER_AI_API_KEY`: the key for the AI service. Default: none, and then
  the page has no "explain with AI" buttons.
- `TLHELPER_VOICE_API_KEY`: the key for a paid voice service. Default: none.
  The `omnivoice` service wants none.
- `DEEPL_API_KEY`: the key for the translation. Default: none, and then a
  request with `translate` gets an error in place of the English text.
- `DEEPL_URL`: default `https://api-free.deepl.com/v2/translate`. A paid DeepL
  key needs `https://api.deepl.com/v2/translate`.
- `SESSION_SECRET`: signs the login cookies. See "3. Turn on the login".

## Running locally

With [uv](https://docs.astral.sh/uv/), from this folder (`web/`). The models
are in `.data/` at the repository root:

```bash
DATA_ROOT=../.data uv run uvicorn tlhelper.app:app --port 8000 --no-access-log
```

The app writes one line for each request, in the Apache common log format with
the latency at the end. `--no-access-log` turns off the uvicorn line, which has
no latency:

```text
1.2.3.4 - - [19/Sep/2026:09:30:00 +0000] "POST /api/v1/classify HTTP/1.1" 200 512 41.7ms
```

The third field is the name of the user from the login. It is `-` on a local
run. On Fly, the address is the value of the `Fly-Client-IP` header. A request
for `/healthz` gets no line: the health checks of Fly and of
`docker-compose.yml` call it every few seconds.

Run the tests:

```bash
uv run pytest
```

Most tests use a fake pipeline and need no models. `test_real_models` loads the
real models from `.data/` at the repository root. If the models are not there,
pytest skips that test.

`tests/flashcards/test_browser.py` and `tests/test_browser_breakdown.py` open
the page in a headless Chromium, with Playwright. The breakdown tests use the
real light models and a fake translator. Download that browser one time:

```bash
uv run playwright install --only-shell chromium
```

If the browser is not there, pytest skips these tests. The browser fixtures are
in `tests/conftest.py`.

To see the page of each browser test, give a folder for the pictures:

```bash
uv run pytest tests/test_browser_breakdown.py --screenshots=shots
```

At the end of each test, each page saves a full-page PNG with the name of the
test to that folder. Without the option, the tests save nothing.

With podman-compose, from the repository root. The compose file mounts the
models that are already in `.data/` there:

```bash
podman-compose up --build --force-recreate
```

`--build` builds a new image from the current code. `--force-recreate` replaces
the container. Without it, podman-compose starts the existing container again,
and that container still uses the old image.

The compose file sets `DOWNLOAD_MODELS=0`, so the container never downloads. If
the models are not in `.data/`, `/api/v1/classify` returns 503 with the reason.

The compose file sets the log driver `passthrough-tty`, which only podman has.
It writes the log lines of the container directly to the terminal. With Docker
Compose, remove the `logging` block.

The compose file turns off the DNS server of podman (aardvark-dns) on its
network, with `x-podman.disable_dns`. That server resolves no names on a host
that has rootless podman and a local resolver (`nameserver 127.0.0.1`). The
translation then fails with "Temporary failure in name resolution". An existing
network keeps its old setting. If the network is older than the setting, remove
it one time:

```bash
podman-compose down
podman network rm langhelper_default
```

The compose file gives the DeepL key to the container as a secret with the name
`deepl_api_key`. A secret is a value that podman or Docker stores outside the
image and mounts as the file `/run/secrets/deepl_api_key`. `entrypoint.sh` reads
that file into `DEEPL_API_KEY`. Create the secret one time, before the first
`podman-compose up`:

```bash
printf '%s' 'your-deepl-key' | podman secret create deepl_api_key -
podman secret ls                     # shows the name, never the value
podman secret rm deepl_api_key       # to replace the key, remove it and create it again
```

To keep the key out of the shell history, read it from a file:
`podman secret create deepl_api_key ./deepl.key`. If you have no key, remove the
two `secrets` blocks from `docker-compose.yml`.

Docker has `docker secret create` only in swarm mode. With Docker Compose,
change the last block of `docker-compose.yml` so that the secret comes from a
variable, and then run `DEEPL_API_KEY=... docker compose up --build`:

```yaml
secrets:
  deepl_api_key:
    environment: DEEPL_API_KEY
```

With plain `podman run` or `docker run`, the flag is `--secret deepl_api_key`
for podman, and `-e DEEPL_API_KEY=...` for Docker.

With Docker, from the repository root:

```bash
docker build -f web/Dockerfile -t langhelper-web .
docker run --rm -p 8000:8000 -v classla_data:/data langhelper-web
```
