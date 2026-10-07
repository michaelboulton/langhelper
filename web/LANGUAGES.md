# More languages

This file lists the work for a study language with a script that is not the Latin script. It has a section for each of Japanese, Thai, Arabic, and Hebrew. The README section "Add a language" has the steps that each new language needs. The work in this file comes on top of those steps.

The app has no code for one of these languages. It only has the parts that are the same for each such language.

## What the app already has

- A word position (`start_char`, `end_char`) is a character position. It does not depend on spaces.
- `Grading` in `tlhelper/languages/base.py` has the rules for a typed flashcard answer, and each language sets them in `info.grading`.
    - `spaces=False` makes punctuation count as nothing, not as a space.
    - `marks="keep"` keeps a combining mark, for example a tone mark or a voicing mark.
    - `marks="ignore"` makes the combining marks count as nothing, in the grade and in the diff. This is for the vowel marks of Arabic and Hebrew, which almost nobody types.
    - `ignored` is a set of other characters that count as nothing, for example the Arabic tatweel "ـ".
    - `slip_letters=0` makes one wrong sign a wrong answer.
    - `plain_letters` has the letters that people type in another way, for example "ss" for "ß".
- A word can have the key `reading`, which says how to say the word. The page shows it under the word and in the detail panel. `Word` in `tlhelper/schemas.py` has the key.
- The page sets `lang` on each line of words and on the answer diff, so the browser selects the font of the language.
- `LanguageInfo.direction` is `"ltr"` or `"rtl"`, and it is in `/api/v1/languages`. The page sets it as `dir` on each text in the language.
    - A line of words is a flex row, so the first word of a right-to-left sentence is on the right. The link lines use the measured positions, so they stay correct.
    - The entry field follows the side that the user enters.
    - A text in the middle of an English line goes into a `<bdi>` element (`bdi()` in `static/js/breakdown.js`). The punctuation around the text then stays in its place.
    - A right-to-left lemma is not italic.
- One written token can be several words. The words then share `start_char` and `end_char`. The page does not use the positions, so each word gets its own chip.
- The page does not send a text while an input method (IME) makes a word. An IME is the tool that makes kanji from Latin letters. The Enter key that accepts a word does not send a flashcard answer.
- A long text with no spaces breaks at the edge of its box.
- The key of a lemma count uses the NFKC form, so half-width and full-width katakana get one row.
- A language can have no grammar checks. Its `check()` only sets `word["problems"] = []`.
- The lemma of a word must never be empty. If the tagger gives no dictionary form, use the text of the word.

## Work for each language with such a script

1. Word links (`tlhelper/align.py`). The rules come from European grammar.
    - `match_rank()` links a name or a number because the text is the same on both sides. That never occurs across two scripts. A possible fix is a romanization of the name before the comparison.
    - The rules for `PART`, `AUX`, `ADP`, and `DET` do not fit a language with particles.
    - `MAX_DISTANCE` and `MAX_SHIFT` assume a similar number of words on both sides. These languages give more tokens than English.
    - Arabic and Hebrew write "and", "in", and "the" onto the next word, and the tagger makes a word of each. That also gives more words on the study side.
    - Move these rules into a record on `LanguageInfo`, as `Grading` does for the answers. Tune them with real sentences.
2. The gloss build (`tlhelper/build_glosses.py`).
    - Add the language to `LANGUAGES`.
    - Add the Wiktionary word classes that the `UPOS` map does not have, for example "counter", "suffix", and "prefix".
3. The text of the page and of the API names Croatian in some places. The text of the page is in the catalogs, `tlhelper/languages/*/ui.ftl`.
    - The message `accents-legend` is a fixed legend of the Croatian accent marks.
    - The message `option-nonstandard` (the "casual text" checkbox) is about Croatian.
    - The summary of the app in `tlhelper/app.py` names the two languages.
4. The names of the grammar features in the catalogs (`feat-*`, `featval-*`) are for Slavic and Germanic languages. The page shows a tag with no message as it is.
5. A page in the language itself. The README section "The language of the page" has the steps. The plural forms and the formats of numbers and times come from the browser.
    - For Arabic and Hebrew, `direction="rtl"` also becomes the `dir` of the page. `static/css/breakdown.css` then needs logical properties, for example `margin-inline-start` in place of `margin-left`.
    - `i18n.js` turns off the isolation marks of Fluent (`useIsolating`), because the page has `<bdi>` elements for a text in another language. Look at the sentences that have a name or a number in them.
6. The page shows a sentence only as separate words. For a script with no spaces, add one line with the sentence as the user wrote it.
7. The default deck `separators` are `" / "` and `";"`. A deck in these scripts needs its own list in its TOML file.
8. Browser tests use `fill()`, which does not use an IME. The guard has a test with a synthetic `keydown` event. A test with a real composition needs the `Input.imeSetComposition` command of the Chrome DevTools Protocol.

## Japanese

The tagger and the translator exist, so Japanese is the smaller task.

1. The tagger.
    - Use `ja_core_news_md` 3.8.0. It fits the spaCy version and the Python version of the project.
    - Pin the wheel in `pyproject.toml`, together with `sudachipy` and `sudachidict_core`. The dictionary adds about 70 MB to the image.
    - spaCy has no Japanese transformer model, so `variants` is only `("light",)`.
    - Make `tlhelper/languages/japanese/` after the German example, with `SpacyTagger` and a `slot_key`.
    - Measure the memory and the load time for the model table of the README.
2. The grading rules: `Grading(spaces=False, slip_letters=0, marks="keep")`. The tests in `tests/flashcards/test_grade.py` already have rows for these rules.
3. The reading of a word.
    - Sudachi gives the katakana reading of each token (`token.morph.get("Reading")`). Put it into `word["reading"]`, as hiragana, and only for a word with kanji.
4. Kana and kanji in a flashcard answer.
    - The answer わたし for a card with 私 is "Again" now.
    - At the import, add the reading of an answer as one more accepted answer. If the deck has a reading field, take the reading from that field. If it has none, take the reading from the tagger.
5. The deck import (`tlhelper/flashcards/apkg.py`). Each change needs a higher `IMPORT_VERSION` in `decks.py`.
    - `clean()` removes the `<ruby>` and `<rt>` tags and keeps their text, so an answer becomes "漢字かんじ". Remove the text of `<rt>` and `<rp>` first.
    - The "Japanese Support" add-on of Anki writes `漢字[かんじ]`. `clean()` keeps this as it is. Remove the brackets, and keep their text as the reading.
6. The translator. DeepL has Japanese with the code `JA`, and `tlhelper/translators/deepl.py` already sends that.
7. Grammar checks: none at first. `check_repeats` in `base.py` must not run, because a repeat is normal in Japanese.
8. The gloss file. Build it from `https://kaikki.org/dictionary/Japanese/`. One word has entries under its kanji form and under its kana form, so make sure that `entry_key` finds the lemma that Sudachi gives.
9. `dictionary_links`: Jisho (`https://jisho.org/search/{lemma}`) is a good first link.
10. `speech="ja-JP"`.

## Thai

Thai needs all of the work for Japanese that is not about kanji, and also a tagger and possibly a translator.

1. The tagger. spaCy has no Thai model.
    - `pythainlp` splits a text into words and gives part-of-speech tags. It has no lemmas, and Thai has no inflection, so the lemma is the text.
    - `SpacyTagger` does not fit. Write `analyze()` directly on `pythainlp`, and compute `start_char` and `end_char` from the word lengths.
    - Map the tags of `pythainlp` to Universal POS tags. `feats` stays empty.
    - Another choice is `spacy-thai`, which gives a parse. Compare its size and its quality first.
2. Sentences. Thai has no full stop, and a space divides clauses, not words.
    - Decide on a sentence split. `pythainlp.sent_tokenize` is one choice.
    - If both sides have the same number of sentences, the word links work per sentence. If the numbers are different, all words are one block, and the position limits are too strict for that.
3. The translator. Make sure that DeepL accepts `TH` with the key of this app. If it does not, write a translator for Amazon Translate or for Google. `tlhelper/translators/__init__.py` has a sketch of both.
4. The grading rules: `Grading(spaces=False, marks="keep")`. A missing tone mark can be a slip, so `slip_letters=1` is a possible value. Thai users also type the vowel and the tone mark in the two possible orders, so normalize that order before the comparison.
5. The reading of a word: `pythainlp.transliterate.romanize` gives a romanization. Put it into `word["reading"]`.
6. The font. The size of 16px with a line height of 1.5 cuts the stacked marks of Thai. Give `:lang(th)` a larger font size and line height in `static/css/breakdown.css`.
7. The gloss file. Build it from `https://kaikki.org/dictionary/Thai/`. The tagger splits compound words in its own way, so measure how many words get a gloss.
8. `speech="th-TH"`. Some browsers have no Thai voice. The page already shows a message for a language with no voice.
9. Thai text can have the zero-width space (U+200B) as a soft break. The grading removes it. Make sure that the tagger input does too.

## Arabic and Hebrew: the common work

The two languages go from right to left, and both have spaces. An input method is not necessary, because a keyboard layout types the letters directly. The direction is the smaller part of the work, and the app already has it. The larger parts are below.

1. The tagger. spaCy has only a tokenizer for `ar` and for `he`, and no trained model.
    - `stanza` has models for both languages. `classla` is a fork of `stanza`, but `stanza` itself is not a dependency of the project. It uses the `torch` that the image already has.
    - Put its models on the volume, as `croatian/heavy.py` does for the classla models, and give the pipeline a `slot_key`.
    - The README says that the first of `variants` is `"light"`, a model that loads in a second or two. No such model exists. Measure a pipeline with only `tokenize`, `mwt`, `pos`, and `lemma`. If it is too slow for "light", change that rule of the README and the test in `tests/languages/test_protocol.py`.
    - Read `sentence.words`, and not the tokens, as `croatian/heavy.py` does. One token such as وبالكتاب gives the four words "and", "in", "the", and "book".
2. The key of a gloss. `plain()` in `tlhelper/languages/glosses.py` removes only the five Croatian accent marks. Make the key function a part of the language, so that a language can remove its vowel marks.
3. The grading rules: `Grading(marks="ignore")`. The tests in `tests/flashcards/test_grade.py` already have rows for these rules, for the two scripts.
4. The font. Give `:lang(ar)` and `:lang(he)` a larger font size in `static/css/breakdown.css`. Never give Arabic text a letter spacing, because it breaks the joined letters.
5. The answer diff marks single letters with a `<span>`. A current browser joins Arabic letters across the edge of a span. Look at the result in the browsers that you use.
6. A deck can have the direction marks U+200E and U+200F in its fields. The grading removes them. Make sure that the tagger input does too.

## Arabic

1. The tagger: the `stanza` model for Arabic (the PADT treebank). It knows Modern Standard Arabic. A deck with a dialect, for example Egyptian or Levantine, gets poor tags.
2. The grading rules: `Grading(marks="ignore", ignored="ـ", plain_letters=(("ة", ("ه",)), ("ى", ("ي",))))`.
    - For Unicode, the hamza of أ, إ, and ؤ is a combining mark. `marks="ignore"` therefore also accepts ا for أ. This is the usual practice, and the tests have a row for it.
3. The gloss file. Build it from `https://kaikki.org/dictionary/Arabic/`.
    - The lemmas of the tagger have vowel marks. The Wiktionary headwords have none, and give the form with marks as the canonical form. The key function must remove the marks on both sides.
    - Many words then share one key, for example كتب as "he wrote" and as "books". The part of speech in the key divides some of them.
4. The reading of a word: the form with all vowel marks.
    - Follow the pattern of `croatian/accents.py`, which maps a form to the same form with accent marks from the Wiktionary form tables. The Arabic tables have the forms with vowel marks.
    - A romanization is a second choice. Wiktionary has one for each entry, and `SKIP_TAGS` in `build_glosses.py` drops it now.
5. The spelling check. pyspellchecker has an Arabic word list, so `base.spelling_problem(text, "ar", "Arabic")` can work. Remove the vowel marks first.
6. The translator. DeepL has Arabic with the code `AR`.
7. `direction="rtl"` and `speech="ar-SA"`.
8. `dictionary_links`: Almaany (`https://www.almaany.com/en/dict/ar-en/{lemma}/`) and Wiktionary are good first links.

## Hebrew

1. The tagger: a `stanza` model for Hebrew (the HTB or the IAHLTwiki treebank). Compare the two.
    - Hebrew with no vowel marks is very ambiguous: one written word can be a noun, a verb, or a word with a prefix. The tags and the lemmas are therefore less exact than those of the other languages. Say so in `light_note`.
2. The grading rules: `Grading(marks="ignore")`. Hebrew has no letter that people type in another way.
    - A text with no vowel marks often has one more י or ו than the same text with marks ("full spelling"). A deck with vowel marks then does not accept the usual typed form. Add the full spelling as one more accepted answer at the import, or make the deck accept both.
3. The gloss file. Build it from `https://kaikki.org/dictionary/Hebrew/`. The lemmas of the tagger have no vowel marks, and the headwords of Wiktionary have none, so the keys fit.
4. The reading of a word. A form with vowel marks for each word of a sentence needs a separate large model, for example Dicta Nakdan. The cheap first step is the form with marks of the lemma, from Wiktionary.
5. No spelling check: pyspellchecker has no Hebrew word list.
6. The translator. Make sure that DeepL accepts `HE` with the key of this app. If it does not, use the same answer as for Thai.
7. `direction="rtl"` and `speech="he-IL"`.
8. `dictionary_links`: Morfix (`https://www.morfix.co.il/en/{lemma}`) and Pealim for verbs are good first links.
