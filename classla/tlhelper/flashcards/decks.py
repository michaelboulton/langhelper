"""Import the decks of the admin into the flashcard database.

A deck is two files with the same stem, for example basics.apkg (an export
from Anki) and basics.toml:

    name = "Croatian basics"
    language = "hr"              # a code from LANGUAGES
    english_field = "Front"      # the field names of the Anki note type
    answer_field = "Back"
    notetype = "Basic"           # optional: only these note types (one, or a list)
    reverse = true               # optional: also ask for the English
    separators = [" / ", ";"]    # optional: they split the accepted answers
    media_fields = ["Audio"]     # optional: more fields with images or sound
    new_per_day = 10             # optional
    reviews_per_day = 100        # optional
    subdecks = true              # optional: one deck for each Anki deck with cards
    to_english_notetypes = ["Read"]  # optional: these notes ask for the English

A line break of a field is "\\n" in separators, for a deck with each accepted
answer on its own line. In all other decks it is a space.

With subdecks, a package with the Anki decks "Croatian::Read::2" and
"Croatian::Speak::2" gives the two decks "Read, 2" and "Speak, 2" under the
name of the package. The page shows them as a tree, and each one has its own
queue and its own limits for a day.

A card shows the images and the sound clips of its two fields: those of the
prompt with the prompt, and those of the answer (and of media_fields) after
the user answered. A note with only a picture as its English is a card too.

The folders are decks/ next to the code (in the image) and decks/ under
DATA_ROOT (the volume). For the same stem, the volume wins.
"""

import logging
import re
from pathlib import Path

import tomllib

from ..languages import LANGUAGES
from ..languages.base import DATA_FILES
from ..settings import DATA_ROOT
from . import apkg, store

DECK_DIRS = [DATA_FILES / "decks", DATA_ROOT / "decks"]
# Part of the stamp of a deck. A larger number makes every deck import again,
# for a change to what the import reads.
IMPORT_VERSION = 4
# Common English words that are not also a word of a study language: no "a",
# "i", "to", "on" or "do" (Croatian), and no "in", "am", "was", "so" or
# "will" (German). "no" is a rare Croatian word, and a common English answer.
ENGLISH_WORDS = frozenset(
    [
        "the",
        "is",
        "are",
        "you",
        "your",
        "of",
        "and",
        "with",
        "this",
        "that",
        "what",
        "how",
        "where",
        "who",
        "why",
        "which",
        "when",
        "there",
        "from",
        "for",
        "not",
        "have",
        "has",
        "does",
        "did",
        "they",
        "she",
        "we",
        "it",
        "its",
        "my",
        "our",
        "thank",
        "thanks",
        "please",
        "yes",
        "hello",
        "hi",
        "good",
        "goodbye",
        "bye",
        "very",
        "much",
        "some",
        "any",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "sorry",
        "excuse",
        "welcome",
        "morning",
        "evening",
        "night",
        "day",
        "today",
        "tomorrow",
        "yesterday",
        "no",
        "can",
        "should",
        "would",
        "could",
        "like",
        "want",
        "need",
        "here",
        "just",
        "everything",
        "later",
        "nice",
        "only",
        "love",
        "take",
        "something",
        "someone",
        "mister",
        "madam",
        "boy",
        "girl",
        "friend",
        "child",
        "husband",
        "wife",
        "woman",
        "young",
        "old",
    ]
)
# Not a part of a word with a hyphen: "is-" is a Croatian prefix.
WORD = re.compile(r"(?<![\w-])[^\W\d_]+(?![\w-])")
DEFAULTS = {
    "notetype": None,
    "reverse": False,
    "separators": [" / ", ";"],
    "media_fields": [],
    "new_per_day": 10,
    "reviews_per_day": 100,
    "subdecks": False,
    "to_english_notetypes": [],
}
REQUIRED = ("name", "language", "english_field", "answer_field")

logger = logging.getLogger("uvicorn.error")


def split(text: str, separators: list[str]) -> list[str]:
    parts = [text]
    for separator in separators:
        parts = [piece for part in parts for piece in part.split(separator)]
    # A line break that is not a separator is only a space.
    return [" ".join(part.split()) for part in parts if part.strip()]


def english_words(text: str) -> int:
    return sum(word in ENGLISH_WORDS for word in WORD.findall(text.lower()))


def wrong_way_round(english: str, answer: str) -> bool:
    """A shared deck can have some notes with the two fields the other way
    round. Only a clear case counts: English words in the answer field, and
    none in the English field. A note with English on both sides (a grammar
    question) stays as the configuration says."""
    return english_words(answer) > 0 and english_words(english) == 0


def read_config(path: Path) -> dict:
    config = DEFAULTS | tomllib.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED if key not in config]
    if missing:
        raise apkg.BadDeck(f"{path.name} has no {', '.join(missing)}")
    if config["language"] not in LANGUAGES:
        raise apkg.BadDeck(f"{path.name}: no language {config['language']!r}")
    if isinstance(config["to_english_notetypes"], str):
        config["to_english_notetypes"] = [config["to_english_notetypes"]]
    return config


def cards_of(notes: list[apkg.Note], config: dict) -> list[dict]:
    cards = []
    notetypes = config["notetype"]
    if isinstance(notetypes, str):
        notetypes = [notetypes]
    for note in notes:
        if notetypes and note.notetype not in notetypes:
            continue
        english_field, answer_field = config["english_field"], config["answer_field"]
        if wrong_way_round(
            note.fields.get(english_field, ""), note.fields.get(answer_field, "")
        ):
            english_field, answer_field = answer_field, english_field
        english = " ".join(note.fields.get(english_field, "").split())
        answers = split(note.fields.get(answer_field, ""), config["separators"])
        english_media = note.media.get(english_field, [])
        answer_media = note.media.get(answer_field, [])
        more_media = [
            name
            for field in config["media_fields"]
            for name in note.media.get(field, [])
        ]
        # A picture can be the whole English side.
        if not (english or english_media) or not answers:
            continue
        # A note type for reading only asks for the English.
        only_english = note.notetype in config["to_english_notetypes"]
        if not only_english:
            cards.append(
                {
                    "guid": note.guid,
                    "deck": note.deck,
                    "direction": store.TO_STUDY,
                    # The whole field: "hi / hello" tells the user that both count.
                    "prompt": english,
                    "answers": answers,
                    "prompt_media": english_media,
                    "answer_media": unique(answer_media + more_media),
                }
            )
        english_answers = split(
            note.fields.get(english_field, ""), config["separators"]
        )
        # The user types the English, so a picture is not enough here.
        if (config["reverse"] or only_english) and english_answers:
            cards.append(
                {
                    "guid": note.guid,
                    "deck": note.deck,
                    "direction": store.TO_ENGLISH,
                    "prompt": " / ".join(answers),
                    "answers": english_answers,
                    "prompt_media": answer_media,
                    "answer_media": unique(english_media + more_media),
                }
            )
    return cards


def unique(names: list[str]) -> list[str]:
    return list(dict.fromkeys(names))


def subdecks_of(stem: str, config: dict, cards: list[dict]) -> list[tuple[dict, list]]:
    """(the configuration of a deck, its cards) for each Anki deck with cards,
    in the order of the package. The parts that all the names start with are
    not in the path: the name of the package stands for them."""
    groups: dict[tuple[str, ...], list[dict]] = {}
    for card in cards:
        groups.setdefault(card["deck"], []).append(card)
    shared = 0
    names = list(groups)
    while all(len(name) > shared + 1 for name in names) and (
        len({name[shared] for name in names}) == 1
    ):
        shared += 1
    return [
        (
            config
            | {
                # The whole Anki name: the key of the deck must stay the same
                # when another export has other decks next to this one.
                "stem": "::".join((stem, *name)),
                "name": ", ".join(name[shared:]) or config["name"],
                "path": [config["name"], *name[shared:]],
            },
            group,
        )
        for name, group in groups.items()
    ]


def deck_path(stem: str) -> Path | None:
    """The package of a deck. As in the import, the last folder wins."""
    # A subdeck has the parts of its Anki name after the file name.
    stem = stem.split("::")[0]
    for folder in reversed(DECK_DIRS):
        if (folder / f"{stem}.toml").exists():
            package = folder / f"{stem}.apkg"
            return package if package.exists() else None
    return None


def import_decks() -> None:
    """Never raises: a bad deck must not stop the start of the service."""
    try:
        found = {
            path.stem: path
            for folder in DECK_DIRS
            if folder.is_dir()
            for path in sorted(folder.glob("*.toml"))
        }
        stamps = store.deck_stamps()
    except Exception:
        logger.exception("no deck import")
        return
    for stem, toml in found.items():
        package = toml.with_suffix(".apkg")
        try:
            if not package.exists():
                raise apkg.BadDeck(f"{toml.name} has no {package.name} next to it")
            stamp = f"v{IMPORT_VERSION} " + " ".join(
                f"{stat.st_size}:{stat.st_mtime_ns}"
                for stat in (toml.stat(), package.stat())
            )
            # All the decks of a package have its stamp.
            if stamp in (
                old
                for name, old in stamps.items()
                if name == stem or name.startswith(stem + "::")
            ):
                continue
            config = read_config(toml)
            cards = cards_of(apkg.read_notes(package), config)
            if not cards:
                raise apkg.BadDeck(
                    f"{toml.name}: no note has the fields"
                    f" {config['english_field']!r} and {config['answer_field']!r}"
                )
            if config["subdecks"]:
                decks = subdecks_of(stem, config, cards)
            else:
                decks = [(config | {"stem": stem}, cards)]
            for deck, group in decks:
                store.save_deck(deck, stamp, group)
                logger.info("deck %s: %d cards", deck["stem"], len(group))
            store.retire_decks(stem, [deck["stem"] for deck, _ in decks])
        except (apkg.BadDeck, tomllib.TOMLDecodeError, OSError) as exc:
            logger.warning("deck %s not imported: %s", stem, exc)
    # A package whose files are gone: its decks leave the page. The rows stay
    # for the review log, and the cards come back with the files.
    for package in {name.split("::")[0] for name in stamps} - found.keys():
        store.retire_decks(package, [])
        logger.info("deck %s: files gone, cards removed", package)
