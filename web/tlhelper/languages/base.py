"""What each language gives to the app, and the checks that need no grammar.

A study language (Croatian, German, French, Italian) and English all implement
Language. The app (app.py) and the word links (align.py) only use this
interface, so a new language is one subfolder and one line in
languages/__init__.py.

analyze() returns a list of sentences: {"text": ..., "words": [...]}. A word
is a dict with these keys:

    id, text, lemma, upos, xpos, feats, start_char, end_char
    problems    one English sentence for each failed check, only with
                check=True. Each one is a messages.Problem, so the page can
                show it in the language of the user.
    accent      only for a language with has_accents
    reading     optional: how to say the word, for a script that does not
                show it. The page shows it under the word.

One written token can be several words: Arabic and Hebrew write "and", "in"
and "the" onto the next word. Those words then have the same start_char and
end_char, and their texts do not add up to the token.

A word with no dictionary form has its text as the lemma, and never "": the
lemma is the key of the glosses, of the lemma counts and of the word links.
"""

import ctypes
import gc
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

from spellchecker import SpellChecker

from ..messages import Problem

# The folder of the data that is not for one language (decks/): next to the
# package and not in it.
DATA_FILES = Path(__file__).parents[2]
# The longest phrase that check_repeats looks for.
MAX_REPEAT = 4
# No spelling check: names, numbers, and what the tagger marks as foreign.
NO_SPELLING_UPOS = {"PUNCT", "SYM", "NUM", "PROPN", "X"}
# correction() tries every change of two letters, and that is slow for a long
# word. A long word with no entry gets the message with no suggestion.
MAX_CORRECTION_CHARS = 12


class ModelsMissing(Exception):
    pass


def release_memory() -> None:
    """Python frees a dropped model, but glibc keeps most of those pages for
    the process. malloc_trim gives them back. Measured after a switch from a
    heavy model to a light one: 530 MB in place of 790 MB. Another libc has
    no such call, and then this does nothing."""
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


class StudySlot:
    """The one model of a study language that is in memory. A heavy model
    needs about 2.5 GB, and its load has a peak above that, so the 4 GB
    machine has room for one. A request for another model drops this one
    first, and the new one loads with a delay. English is not here: its model
    is small and stays loaded (spacy_words.py)."""

    def __init__(self):
        # One lock for load and inference. torch already uses every core for a
        # single call, and the machine has shared CPUs, so parallel calls gain
        # nothing.
        self._lock = threading.Lock()
        self._model = None
        # (language code, model type). Plain values, so Language.status can
        # read them with no wait on the lock.
        self.key: tuple[str, str] | None = None
        self.loading: tuple[str, str] | None = None

    @contextmanager
    def use(self, key: tuple[str, str], load: Callable[[], object]) -> Iterator:
        """Hold the lock and give the model of this key. load() makes it."""
        with self._lock:
            if self.key != key:
                self.loading = key
                try:
                    self.key = self._model = None
                    release_memory()
                    self._model = load()
                    self.key = key
                finally:
                    self.loading = None
            yield self._model

    def drop(self) -> None:
        with self._lock:
            self.key = self._model = None
            release_memory()

    def status(self, code: str) -> dict:
        """The Language.status of the language with this code."""
        loading, key = self.loading, self.key
        return {
            "loading": loading[1] if loading and loading[0] == code else None,
            "loaded": [key[1]] if key and key[0] == code else [],
        }


STUDY = StudySlot()


@dataclass(frozen=True)
class Grading:
    """How the flashcards compare a typed answer in this language with an
    accepted answer (flashcards/grade.py). The default is a language with the
    Latin script and no letters of its own, such as English."""

    # The script has spaces between its words. False: punctuation and space
    # are nothing, so a comma that is not there does not make a space error.
    spaces: bool = True
    # This many wrong letters are a slip of the finger, and more is a miss. 0
    # for a script where one sign is a word or changes the word.
    slip_letters: int = 1
    # What a combining mark is in an answer.
    # "hard":   an answer with no marks is right, but hard: "kuca" for "kuća".
    # "keep":   a mark makes another word (a tone mark, a voicing mark).
    # "ignore": nobody types the marks, so they never count (the vowel marks
    #           of Arabic and Hebrew).
    marks: Literal["hard", "keep", "ignore"] = "hard"
    # (letter, what people type on a keyboard without it). Only the letters
    # with no separate accent need an entry: marks takes care of "č".
    plain_letters: tuple[tuple[str, tuple[str, ...]], ...] = ()
    # Characters that count as nothing, and that are not punctuation: the
    # tatweel "ـ" only makes an Arabic word longer.
    ignored: str = ""


@dataclass(frozen=True)
class LanguageInfo:
    # ISO 639-1. A machine translator (translators/) gets this code.
    code: str
    name: str
    # The name of the xpos tag set.
    tag_name: str
    placeholder: str
    # The model types. The first one is the default: "light" loads in a
    # second. "heavy" is more exact and loads with a delay.
    variants: tuple[str, ...] = ("light",)
    # For the page: what the light model cannot do, if the heavy one can.
    light_note: str = ""
    has_accents: bool = False
    # "rtl" for a script that goes from right to left. The page sets it as
    # the dir of each text in this language.
    direction: Literal["ltr", "rtl"] = "ltr"
    # The BCP 47 tag for the speech synthesis of the browser.
    speech: str = ""
    # (label, address). "{lemma}" in either one becomes the lemma of the word.
    dictionary_links: tuple[tuple[str, str], ...] = ()
    # The BCP 47 tag of the page text in this language: the folder of the
    # language then has a ui.ftl (locales.py). Empty: no such text.
    ui_locale: str = ""
    # The name of the language in the language, for the list of the locales.
    native_name: str = ""
    # Not in the API: only the flashcards use it.
    grading: Grading = Grading()


class Language(Protocol):
    info: LanguageInfo
    # Common words where the glosses of Wiktionary have a gap: lemma to
    # English words, the main meaning first.
    extra_glosses: dict[str, list[str]]

    def warm_up(self) -> None:
        """Load the default models. Runs in a thread at the start of the app."""

    def status(self) -> dict:
        """{"loading": a model type or None, "loaded": [model types]}. Must
        not wait on a model load."""

    def analyze(
        self, text: str, *, variant: str = "light", check: bool = True
    ) -> list[dict]:
        """Tag a text. Raises ModelsMissing if the models are not there."""

    def glosses(self, text: str, lemma: str, upos: str) -> dict[str, int]:
        """The English words for this word, each with its rank. 0 is the main
        meaning."""


def check_repeats(words: list[dict], allowed: frozenset[str] = frozenset()) -> None:
    """A word or a phrase of up to MAX_REPEAT words, directly after itself:
    "je je", "pun je pun je". Punctuation between the two copies stops it, so
    "Da, da" passes. allowed: single words that can repeat ("had had")."""
    texts = [w["text"].lower() if w["text"].isalpha() else None for w in words]
    for size in range(1, MAX_REPEAT + 1):
        start = size
        while start + size <= len(words):
            phrase = texts[start : start + size]
            if None in phrase or phrase != texts[start - size : start]:
                start += 1
                continue
            # Jump over the copy, so "pun je pun je pun je" does not also
            # match as "je pun" two times.
            copy = words[start : start + size]
            start += size
            if size == 1 and phrase[0] in allowed:
                continue
            shown = " ".join(w["text"] for w in copy)
            for word in copy:
                # "je je je je" is also "je je" two times: one reason is enough.
                if not any("repeats" in problem for problem in word["problems"]):
                    word["problems"].append(
                        Problem("problem-repeat", f"'{shown}' repeats.", words=shown)
                    )


_spellers: dict[str, SpellChecker] = {}
_speller_lock = threading.Lock()


def speller(language: str) -> SpellChecker:
    """language: a code of pyspellchecker, "en", "de" or "fr"."""
    with _speller_lock:
        if language not in _spellers:
            _spellers[language] = SpellChecker(language=language)
        return _spellers[language]


@lru_cache(maxsize=4096)
def spelling_problem(text: str, language: str, name: str) -> Problem | None:
    """name: the language name for the message, "English"."""
    checker = speller(language)
    if text in checker:
        return None
    message = f"The {name} word list does not have this word."
    if len(text) <= MAX_CORRECTION_CHARS:
        better = checker.correction(text)
        if better and better != text:
            return Problem(
                "problem-spelling-suggestion",
                f"{message} Did you mean '{better}'?",
                language=language,
                better=better,
            )
    return Problem("problem-spelling", message, language=language)
