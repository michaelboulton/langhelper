"""Make a deck package from a text file, for an admin with no Anki at hand:

    uv run python -m tlhelper.flashcards.make_deck decks/basics.tsv

Each line of the text file is "English<TAB>answer". The result is
decks/basics.apkg, with the fields Front and Back. It holds only what apkg.py
reads (the notes, the field names and the Anki decks), so Anki itself cannot
import it. write_package() is the writer for a caller that has its own notes
and wants an Anki deck for each group of them (scripts/lessons.py).
"""

import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import NamedTuple

MID = 1
MODELS = {
    str(MID): {
        "name": "Basic",
        "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
    }
}


class PackageNote(NamedTuple):
    guid: str
    english: str
    answer: str
    # The Anki deck of the note, "Course::001 Greetings". The reader splits
    # the name on "::".
    deck: str


def write_package(target: Path, notes: list[PackageNote]) -> Path:
    """The notes go in the package in this order, one card each. Each distinct
    deck name is one Anki deck."""
    deck_ids = {
        name: did
        for did, name in enumerate(dict.fromkeys(n.deck for n in notes), start=1)
    }
    with tempfile.TemporaryDirectory() as folder:
        collection = Path(folder) / "collection.anki21"
        conn = sqlite3.connect(collection)
        conn.execute("CREATE TABLE col (models TEXT, decks TEXT)")
        named = {str(did): {"name": name} for name, did in deck_ids.items()}
        conn.execute(
            "INSERT INTO col VALUES (?, ?)", (json.dumps(MODELS), json.dumps(named))
        )
        conn.execute(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, guid TEXT, mid INTEGER, flds TEXT)"
        )
        conn.execute(
            "CREATE TABLE cards (id INTEGER PRIMARY KEY, nid INTEGER, did INTEGER, ord INTEGER)"
        )
        for number, note in enumerate(notes, start=1):
            flds = f"{note.english}\x1f{note.answer}"
            conn.execute(
                "INSERT INTO notes VALUES (?, ?, ?, ?)", (number, note.guid, MID, flds)
            )
            conn.execute(
                "INSERT INTO cards VALUES (?, ?, ?, 0)",
                (number, number, deck_ids[note.deck]),
            )
        conn.commit()
        conn.close()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
            package.write(collection, collection.name)
            package.writestr("media", "{}")
    return target


def make_deck(source: Path) -> Path:
    rows = [
        line.split("\t")
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    bad = [row for row in rows if len(row) != 2]
    if bad:
        raise SystemExit(f"not 'English<TAB>answer': {bad[0]!r}")
    notes = [
        PackageNote(
            # From the English text, so a changed answer keeps the progress.
            hashlib.sha1(english.strip().encode()).hexdigest()[:10],
            english.strip(),
            answer.strip(),
            source.stem,
        )
        for english, answer in rows
    ]
    return write_package(source.with_suffix(".apkg"), notes)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(make_deck(Path(sys.argv[1])))
