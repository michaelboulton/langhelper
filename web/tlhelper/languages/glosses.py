"""The English glosses of Wiktionary for the words of one language.

build_glosses.py writes a read-only SQLite file for each language, with the
table that align.py needs:

    glosses(key, word, rank)    'haus|NOUN', 'house', 0

The file of Croatian (accents.db) also has the accent tables, see
croatian/accents.py.
"""

import logging
import sqlite3
import threading
import unicodedata
from pathlib import Path

GLOSSES_SCHEMA = """
CREATE TABLE glosses (
    key TEXT NOT NULL, word TEXT NOT NULL, rank INTEGER NOT NULL,
    PRIMARY KEY (key, word)) WITHOUT ROWID;
"""

# The accent marks of Serbo-Croatian: grave, acute, double grave, inverted
# breve, and the macron for a long vowel. The umlaut of German is not one.
ACCENT_MARKS = {"̀", "́", "̏", "̑", "̄"}
# The accent sits on a vowel or on a syllabic r. The acute of ć is on a c, so
# it stays.
ACCENT_BASES = set("aeiouAEIOUrR")

logger = logging.getLogger("uvicorn.error")


def plain(text: str) -> str:
    """Remove the accent marks: 'kȗćā' -> 'kuća'. č, ć, š, ž and đ stay."""
    out = []
    base = ""
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.combining(char):
            if char in ACCENT_MARKS and base in ACCENT_BASES:
                continue
        else:
            base = char
        out.append(char)
    return unicodedata.normalize("NFC", "".join(out))


def entry_key(lemma: str, upos: str) -> str:
    lemma = plain(lemma)
    return (lemma if upos == "PROPN" else lemma.lower()) + "|" + upos


class GlossFile:
    def __init__(self, path: Path):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        self._missing = False
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection | None:
        """Open the file read-only. The caller must hold _lock."""
        if self._conn is None and not self._missing:
            try:
                self._conn = sqlite3.connect(
                    f"file:{self.path}?mode=ro&immutable=1",
                    uri=True,
                    check_same_thread=False,
                )
            except sqlite3.OperationalError as exc:
                logger.warning("no gloss data in %s: %r", self.path, exc)
                self._missing = True
        return self._conn

    def glosses_for(self, text: str, lemma: str, upos: str) -> dict[str, int]:
        """The English words for this word, each with its rank: 0 for the
        first word of the first sense in Wiktionary, which is the main
        meaning. The tagger can give a lemma with another meaning, so this
        also reads the entry of the word itself."""
        keys = {entry_key(lemma, upos), entry_key(text, upos)}
        with self._lock:
            conn = self.connect()
            if conn is None:
                return {}
            marks = ",".join("?" * len(keys))
            rows = conn.execute(
                f"SELECT word, min(rank) FROM glosses WHERE key IN ({marks})"
                " GROUP BY word",
                tuple(keys),
            ).fetchall()
        return dict(rows)
