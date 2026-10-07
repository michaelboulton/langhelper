"""Read the notes of an Anki deck package (.apkg), with no Anki code.

An .apkg is a zip with one SQLite file of the collection:

  collection.anki21b  Anki 2.1.50 and later. Compressed with zstd, schema 18:
                      the field names are in the table `fields`.
  collection.anki21   The export option "Support older Anki versions".
  collection.anki2    Schema 11: the field names are in the JSON of col.models.
                      Next to one of the newer files, this one is a dummy with
                      one note ("Please update Anki"), so it is the last choice.

In every schema, notes.flds holds the fields of a note, joined by \\x1f, and
notes.guid stays the same between two exports.

A field refers to a media file as <img src="name"> or [sound:name]. The zip
holds each media file under a number, and the member `media` has the names:

  old packages  JSON, {"0": "house.jpg"}.
  new packages  zstd-compressed protobuf: a list of entries (field 1), each
                with its name (field 1). The position in the list is the
                number, and each media file is zstd-compressed too.
"""

import functools
import html
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

import zstandard

# The first one that the zip has.
COLLECTIONS = ("collection.anki21b", "collection.anki21", "collection.anki2")
# Far over any real deck. A zstd stream gives no size before the end.
MAX_COLLECTION_BYTES = 512 * 1024 * 1024

MAX_MEDIA_BYTES = 20 * 1024 * 1024

# {file suffix: (what the page makes of it, content type)}. No svg: it can
# hold a script. A file with another suffix is not part of a card.
KINDS = {
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".png": ("image", "image/png"),
    ".gif": ("image", "image/gif"),
    ".webp": ("image", "image/webp"),
    ".mp3": ("audio", "audio/mpeg"),
    ".ogg": ("audio", "audio/ogg"),
    ".wav": ("audio", "audio/wav"),
    ".m4a": ("audio", "audio/mp4"),
}

MEDIA = re.compile(
    r"\[sound:(?P<sound>[^\]]+)\]"
    r"|<img\b[^>]*?\bsrc\s*=\s*(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'"
    r"|(?P<bare>[^\s>]+))",
    re.IGNORECASE,
)
SOUND = re.compile(r"\[sound:[^\]]*\]")
# These end a line on a card, so they must not join two words.
BREAK = re.compile(r"<\s*(br|/div|/p|/li)\b[^>]*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]*>")


class BadDeck(Exception):
    pass


@dataclass(frozen=True)
class Note:
    guid: str
    notetype: str
    fields: dict[str, str]
    # {field name: the media files of the field, in order}, only for a field
    # that has some.
    media: dict[str, list[str]] = field(default_factory=dict)
    # The path of the Anki deck of the first card of the note: ("Croatian",
    # "Read Training", "2"). Empty for a package with no cards table.
    deck: tuple[str, ...] = ()


def kind(name: str) -> tuple[str, str] | None:
    return KINDS.get(Path(name).suffix.lower())


def media_of(value: str) -> list[str]:
    """The names of the images and sound clips of a field that a card can show."""
    names = []
    for match in MEDIA.finditer(value):
        if match["sound"] is not None:
            name = html.unescape(match["sound"])
        else:
            # Anki writes the src as a URL: "my%20house.jpg".
            source = match["double"] or match["single"] or match["bare"] or ""
            name = unquote(html.unescape(source))
        if kind(name) and name not in names:
            names.append(name)
    return names


def clean(field: str) -> str:
    """The plain text of a field: no HTML, no [sound:...] and no images. A
    line break of the card stays as "\\n", because some decks put each
    accepted answer on its own line."""
    text = SOUND.sub(" ", field)
    text = BREAK.sub("\n", text)
    text = TAG.sub("", text)
    lines = (" ".join(line.split()) for line in html.unescape(text).split("\n"))
    return "\n".join(line for line in lines if line)


def read_notes(path: Path) -> list[Note]:
    """The notes in the order of the deck (the note id is the creation time)."""
    try:
        with zipfile.ZipFile(path) as package:
            name = next((n for n in COLLECTIONS if n in package.namelist()), None)
            if name is None:
                raise BadDeck(f"{path.name} has no collection file")
            data = package.read(name)
    except (OSError, zipfile.BadZipFile) as exc:
        raise BadDeck(f"{path.name} is not a deck package: {exc}") from exc
    if name.endswith("b"):
        try:
            reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data))
            data = reader.read(MAX_COLLECTION_BYTES + 1)
        except zstandard.ZstdError as exc:
            raise BadDeck(f"{path.name}: {exc}") from exc
    if len(data) > MAX_COLLECTION_BYTES:
        raise BadDeck(f"{path.name} is too large")
    # sqlite3 only opens a file.
    with tempfile.NamedTemporaryFile(suffix=".anki2") as file:
        file.write(data)
        file.flush()
        conn = sqlite3.connect(f"file:{file.name}?mode=ro", uri=True)
        # Anki declares this collation on the names in schema 18, and SQLite
        # refuses a query on such a table without it.
        conn.create_collation(
            "unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())
        )
        try:
            return notes_of(conn)
        except (sqlite3.Error, ValueError, KeyError) as exc:
            raise BadDeck(f"{path.name}: {exc}") from exc
        finally:
            conn.close()


def notes_of(conn: sqlite3.Connection) -> list[Note]:
    notetypes = notetypes_of(conn)
    note_decks = note_decks_of(conn)
    notes = []
    for note_id, guid, mid, flds in conn.execute(
        "SELECT id, guid, mid, flds FROM notes ORDER BY id"
    ):
        name, field_names = notetypes[mid]
        raw = dict(zip(field_names, flds.split("\x1f"), strict=False))
        fields = {key: clean(value) for key, value in raw.items()}
        media = {key: media_of(value) for key, value in raw.items()}
        media = {key: names for key, names in media.items() if names}
        notes.append(Note(guid, name, fields, media, note_decks.get(note_id, ())))
    return notes


def tables_of(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}


def decks_of(conn: sqlite3.Connection) -> dict[int, tuple[str, ...]]:
    """{Anki deck id: the parts of its name}. "Croatian::Read Training" is the
    deck "Read Training" under the deck "Croatian"."""
    if "decks" in tables_of(conn):
        # Schema 18 has \\x1f between the parts.
        return {
            did: tuple(name.split("\x1f"))
            for did, name in conn.execute("SELECT id, name FROM decks")
        }
    [[decks]] = conn.execute("SELECT decks FROM col")
    return {
        int(did): tuple(deck["name"].split("::"))
        for did, deck in json.loads(decks).items()
    }


def note_decks_of(conn: sqlite3.Connection) -> dict[int, tuple[str, ...]]:
    """{note id: the deck of its first card}."""
    if "cards" not in tables_of(conn):
        return {}
    decks = decks_of(conn)
    found = {}
    for note_id, did in conn.execute("SELECT nid, did FROM cards ORDER BY ord DESC"):
        found[note_id] = decks.get(did, ())
    return found


def notetypes_of(conn: sqlite3.Connection) -> dict[int, tuple[str, list[str]]]:
    """{note type id: (its name, its field names in order)}."""
    if "notetypes" in tables_of(conn):
        notetypes = {
            mid: (name, [])
            for mid, name in conn.execute("SELECT id, name FROM notetypes")
        }
        for mid, name in conn.execute(
            "SELECT ntid, name FROM fields ORDER BY ntid, ord"
        ):
            notetypes[mid][1].append(name)
        return notetypes
    [[models]] = conn.execute("SELECT models FROM col")
    return {
        int(mid): (
            model["name"],
            [f["name"] for f in sorted(model["flds"], key=lambda f: f["ord"])],
        )
        for mid, model in json.loads(models).items()
    }


# The media files


def decompress(data: bytes, limit: int) -> bytes:
    """At most limit + 1 bytes, so the caller can see that it is too large."""
    reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data))
    return reader.read(limit + 1)


def varint(data: bytes, at: int) -> tuple[int, int]:
    """(the protobuf number at `at`, the position after it)."""
    value = shift = 0
    while True:
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return value, at


def protobuf_fields(data: bytes) -> list[tuple[int, bytes]]:
    """(field number, bytes) for each length-delimited field of a message."""
    found = []
    at = 0
    while at < len(data):
        key, at = varint(data, at)
        number, wire_type = key >> 3, key & 7
        if wire_type == 0:
            _, at = varint(data, at)
        elif wire_type == 1:
            at += 8
        elif wire_type == 5:
            at += 4
        elif wire_type == 2:
            size, at = varint(data, at)
            if at + size > len(data):
                raise ValueError("a protobuf field ends after the data")
            found.append((number, data[at : at + size]))
            at += size
        else:
            raise ValueError(f"protobuf wire type {wire_type}")
    return found


@functools.lru_cache(maxsize=8)
def _media_names(path: Path, _stamp: int) -> tuple[dict[str, str], bool]:
    # _stamp is only part of the cache key: a new export has a new one.
    try:
        with zipfile.ZipFile(path) as package:
            members = set(package.namelist())
            data = package.read("media") if "media" in members else b"{}"
        try:
            names = {name: number for number, name in json.loads(data).items()}
            compressed = False
        except ValueError:
            entries = protobuf_fields(decompress(data, MAX_COLLECTION_BYTES))
            names = {
                dict(protobuf_fields(entry))[1].decode(): str(number)
                for number, (_, entry) in enumerate(e for e in entries if e[0] == 1)
            }
            compressed = True
    except (
        OSError,
        zipfile.BadZipFile,
        zstandard.ZstdError,
        ValueError,
        KeyError,
        IndexError,
        AttributeError,
    ) as exc:
        raise BadDeck(f"{path.name}: no list of the media files: {exc}") from exc
    return {n: m for n, m in names.items() if m in members}, compressed


def media_names(path: Path) -> tuple[dict[str, str], bool]:
    """({file name: its zip member}, the members are zstd-compressed)."""
    try:
        stamp = path.stat().st_mtime_ns
    except OSError as exc:
        raise BadDeck(f"{path.name}: {exc}") from exc
    return _media_names(path, stamp)


def read_media(path: Path, name: str) -> bytes:
    """The bytes of a media file. KeyError for a name that the package does
    not have: the name is only a key, never a path."""
    names, compressed = media_names(path)
    member = names[name]
    try:
        with zipfile.ZipFile(path) as package:
            if package.getinfo(member).file_size > MAX_MEDIA_BYTES:
                raise BadDeck(f"{name} is too large")
            data = package.read(member)
        if compressed:
            data = decompress(data, MAX_MEDIA_BYTES)
    except (OSError, zipfile.BadZipFile, zstandard.ZstdError) as exc:
        raise BadDeck(f"{path.name}: {name}: {exc}") from exc
    if len(data) > MAX_MEDIA_BYTES:
        raise BadDeck(f"{name} is too large")
    return data
