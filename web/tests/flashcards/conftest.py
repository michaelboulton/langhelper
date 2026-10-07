"""Builds small Anki deck packages, and points the flashcard code at tmp_path."""

import json
import sqlite3
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
import zstandard
from tlhelper import explain
from tlhelper.flashcards import decks, store

MID = 1700000000000
NOTES = [
    ("guid-house", "house", "kuća"),
    ("guid-hello", "hello / hi", "bok; zdravo"),
    ("guid-coffee", "I drink coffee.", "Pijem kavu."),
]
TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""


def media_entries(media):
    """The protobuf list of the media files of a new package. Each entry has
    its name (field 1) and its size (field 2). All lengths here are under 128,
    so each is one byte."""
    entries = b""
    for name, data in media.items():
        encoded = name.encode()
        entry = bytes([0x0A, len(encoded)]) + encoded + bytes([0x10, len(data)])
        entries += bytes([0x0A, len(entry)]) + entry
    return entries


def write_apkg(
    path,
    notes=NOTES,
    *,
    new_format=False,
    fields=("Front", "Back"),
    media=None,
    anki_decks=None,
):
    """notes: (guid, front, back). new_format: schema 18 with zstd, as Anki
    2.1.50 and later write it, else schema 11. media: {file name: bytes}.
    anki_decks: {deck id: "Parent::Child"}, and then each note ends with the id
    of its deck. Without it, the package has no cards table."""
    media = media or {}
    if anki_decks:
        deck_ids = [note[-1] for note in notes]
        notes = [note[:-1] for note in notes]
    collection = path.with_suffix(".sqlite")
    collection.unlink(missing_ok=True)
    conn = sqlite3.connect(collection)
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, guid, mid, flds)")
    if new_format:
        conn.execute("CREATE TABLE notetypes (id INTEGER PRIMARY KEY, name)")
        conn.execute("CREATE TABLE fields (ntid, ord, name)")
        conn.execute("INSERT INTO notetypes VALUES (?, 'Basic')", (MID,))
        # Out of order, like a table with no ORDER BY can be.
        for ord_, name in reversed(list(enumerate(fields))):
            conn.execute("INSERT INTO fields VALUES (?, ?, ?)", (MID, ord_, name))
    else:
        flds = [{"name": name, "ord": ord_} for ord_, name in enumerate(fields)]
        models = {str(MID): {"name": "Basic", "flds": flds}}
        named = {str(did): {"name": name} for did, name in (anki_decks or {}).items()}
        conn.execute("CREATE TABLE col (models, decks)")
        conn.execute(
            "INSERT INTO col VALUES (?, ?)", (json.dumps(models), json.dumps(named))
        )
    if anki_decks:
        conn.execute("CREATE TABLE cards (id INTEGER PRIMARY KEY, nid, did, ord)")
        for number, did in enumerate(deck_ids):
            conn.execute(
                "INSERT INTO cards VALUES (?, ?, ?, 0)", (number + 1,) * 2 + (did,)
            )
        if new_format:
            # Anki 2.1.50 and later: its own collation, and \x1f in the names.
            conn.create_collation("unicase", lambda a, b: (a > b) - (a < b))
            conn.execute(
                "CREATE TABLE decks (id INTEGER PRIMARY KEY, name TEXT COLLATE unicase)"
            )
            for did, name in anki_decks.items():
                conn.execute(
                    "INSERT INTO decks VALUES (?, ?)", (did, name.replace("::", "\x1f"))
                )
    for number, (guid, *values) in enumerate(notes):
        conn.execute(
            "INSERT INTO notes VALUES (?, ?, ?, ?)",
            (number + 1, guid, MID, "\x1f".join(values)),
        )
    conn.commit()
    conn.close()
    data = collection.read_bytes()
    collection.unlink()
    with zipfile.ZipFile(path, "w") as package:
        if new_format:
            package.writestr("collection.anki21b", zstandard.compress(data))
            # The dummy for an old Anki. Not a database here: nobody reads it.
            package.writestr("collection.anki2", b"Please update Anki")
            package.writestr("media", zstandard.compress(media_entries(media)))
        else:
            package.writestr("collection.anki21", data)
            package.writestr("media", json.dumps(dict(enumerate(media))))
        for number, content in enumerate(media.values()):
            package.writestr(
                str(number), zstandard.compress(content) if new_format else content
            )
    return path


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 20, 9, 0, tzinfo=UTC)

    def __call__(self):
        return self.now

    def add(self, **delta):
        self.now += timedelta(**delta)


class FakeBackend:
    """An AI service (tlhelper/explain) that keeps each prompt."""

    name = "fake"

    def __init__(self):
        self.key = True
        self.prompts = []
        self.error = None
        # The system text that the next request must have.
        self.system = explain.SYSTEM

    def available(self):
        return self.key

    def model(self):
        return "fake-model"

    def complete(self, system, prompt, **kwargs):
        assert system == self.system
        if self.error:
            raise explain.ExplainError(self.error, "ai-busy")
        self.prompts.append(prompt)
        return f"Answer {len(self.prompts)}."


@pytest.fixture
def backend(monkeypatch):
    fake = FakeBackend()
    monkeypatch.setitem(explain.BACKENDS, "fake", fake)
    monkeypatch.setenv("TLHELPER_AI_BACKEND", "fake")
    return fake


@pytest.fixture
def make_apkg():
    """The tests have no package to import write_apkg from."""
    return write_apkg


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(store, "now", clock)
    return clock


@pytest.fixture
def basics(deck_dir):
    """The id of an imported deck with the three NOTES."""
    write_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML, encoding="utf-8")
    decks.import_decks()
    [deck] = store.decks("anyone")
    return deck["id"]
