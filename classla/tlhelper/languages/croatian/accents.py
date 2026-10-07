"""Pitch accent lookup for Croatian words.

The data comes from the Serbo-Croatian entries of English Wiktionary, through
kaikki.org (CC BY-SA). build_glosses.py turns that export into accents.db, a
read-only SQLite file with three tables:

    lemmas(key, form)                         'kuća|NOUN', 'kȕća'
    forms(key, surface, form, gcase, number)  'kuća|NOUN', 'kuće', 'kȕćē', 'gen', 'sg'
    glosses(key, word)                        'kuća|NOUN', 'house'

Some nouns have every case form with its accent. Verbs and adjectives mostly
have the accent only on the dictionary form, so for them the lookup falls back
to the accented lemma and says so with exact=False. The glosses are the English
translations of the word, which align.py uses.
"""

import logging
import sqlite3
import threading

from pathlib import Path

from ..glosses import GLOSSES_SCHEMA, entry_key, plain

# The data of a language is in the folder of the language.
ACCENTS_PATH = Path(__file__).with_name("accents.db")

SCHEMA = (
    """
CREATE TABLE lemmas (
    key TEXT NOT NULL, seq INTEGER NOT NULL, form TEXT NOT NULL,
    PRIMARY KEY (key, seq)) WITHOUT ROWID;
CREATE TABLE forms (
    key TEXT NOT NULL, surface TEXT NOT NULL, seq INTEGER NOT NULL,
    form TEXT NOT NULL, gcase TEXT NOT NULL, number TEXT NOT NULL,
    PRIMARY KEY (key, surface, seq)) WITHOUT ROWID;
"""
    + GLOSSES_SCHEMA
)
# seq keeps the order of Wiktionary, so the first reading of a homograph is the
# first one that Wiktionary lists. WITHOUT ROWID: the primary key is the only
# index, which halves the file.

CASES = {
    "Nom": "nom",
    "Gen": "gen",
    "Dat": "dat",
    "Acc": "acc",
    "Voc": "voc",
    "Loc": "loc",
    "Ins": "ins",
}
NUMBERS = {"Sing": "sg", "Plur": "pl"}
NO_ACCENT_UPOS = {"PUNCT", "SYM", "NUM"}
# Clitics (short unstressed words that lean on the word next to them) carry no
# accent of their own. The short forms of biti and htjeti, and the question
# word li:
VERB_CLITICS = {
    "sam",
    "si",
    "je",
    "smo",
    "ste",
    "su",
    "ću",
    "ćeš",
    "će",
    "ćemo",
    "ćete",
    "bih",
    "bi",
    "bismo",
    "biste",
}
# The short pronoun forms. "mi" and "ti" are also the stressed nominative
# forms mȋ and tȋ, so a nominative is never a clitic.
PRONOUN_CLITICS = {
    "me",
    "te",
    "se",
    "ga",
    "je",
    "ju",
    "ih",
    "nas",
    "vas",
    "mi",
    "ti",
    "mu",
    "joj",
    "im",
    "nam",
    "vam",
    "si",
}

logger = logging.getLogger("uvicorn.error")

_conn: sqlite3.Connection | None = None
_missing = False
_lock = threading.Lock()


def connect() -> sqlite3.Connection | None:
    """Open accents.db read-only. The caller must hold _lock."""
    global _conn, _missing
    if _conn is None and not _missing:
        try:
            _conn = sqlite3.connect(
                f"file:{ACCENTS_PATH}?mode=ro&immutable=1",
                uri=True,
                check_same_thread=False,
            )
        except sqlite3.OperationalError as exc:
            logger.warning("no accent data in %s: %r", ACCENTS_PATH, exc)
            _missing = True
    return _conn


def is_clitic(surface: str, upos: str, feats: dict) -> bool:
    if upos == "AUX":
        return surface in VERB_CLITICS
    if upos == "PRON":
        return surface in PRONOUN_CLITICS and feats.get("Case") != "Nom"
    return upos == "PART" and surface == "li"


def join(forms: list[str], text: str, exact: bool) -> dict:
    forms = list(dict.fromkeys(forms))
    if text[:1].isupper():
        forms = [form[:1].upper() + form[1:] for form in forms]
    result = {"form": " / ".join(forms), "exact": exact}
    if len(forms) > 1:
        result["ambiguous"] = True
    return result


def glosses_for(text: str, lemma: str, upos: str) -> dict[str, int]:
    """The English words for this word, each with its rank: 0 for the first
    word of the first sense in Wiktionary, which is the main meaning. classla
    says that the lemma of "ona" is "on" (he), so this also reads the entry of
    the word itself (she)."""
    keys = {entry_key(lemma, upos), entry_key(text, upos)}
    with _lock:
        conn = connect()
        if conn is None:
            return {}
        marks = ",".join("?" * len(keys))
        try:
            rows = conn.execute(
                f"SELECT word, min(rank) FROM glosses WHERE key IN ({marks})"
                " GROUP BY word",
                tuple(keys),
            ).fetchall()
        except sqlite3.OperationalError:
            # An accents.db from before the glosses table.
            return {}
    return dict(rows)


def noun_can_be(text: str, case: str) -> bool | None:
    """True if Wiktionary has this form of a noun with that case (a key of
    CASES). None if it has no case form of this noun at all: only some nouns
    have their table. For the light models, which have no lexicon of their
    own (grammar.Lexicon). The table has no index on the surface, so this
    reads all of it: about 20 ms, and only for a noun with a wrong case."""
    surface = plain(text)
    with _lock:
        conn = connect()
        if conn is None:
            return None
        rows = conn.execute(
            "SELECT DISTINCT gcase FROM forms WHERE surface IN (?, ?)"
            " AND gcase != '' AND (key LIKE '%|NOUN' OR key LIKE '%|PROPN')",
            (surface, surface.lower()),
        ).fetchall()
    return (CASES[case],) in rows if rows else None


def accent_for(text: str, lemma: str, upos: str, feats: dict) -> dict | None:
    if upos in NO_ACCENT_UPOS:
        return None
    key = entry_key(lemma, upos)
    surface = plain(text) if upos == "PROPN" else plain(text).lower()
    if is_clitic(surface, upos, feats):
        return {"form": text, "exact": True, "clitic": True}
    with _lock:
        conn = connect()
        if conn is None:
            return None
        candidates = conn.execute(
            "SELECT form, gcase, number FROM forms WHERE key = ? AND surface = ?"
            " ORDER BY seq",
            (key, surface),
        ).fetchall()
        lemmas = [
            row[0]
            for row in conn.execute(
                "SELECT form FROM lemmas WHERE key = ? ORDER BY seq", (key,)
            )
        ]

    if candidates:
        case = CASES.get(feats.get("Case"), "")
        number = NUMBERS.get(feats.get("Number"), "")
        matches = [
            form
            for form, form_case, form_number in candidates
            if form_case in ("", case) and form_number in ("", number)
        ]
        return join(matches or [form for form, _, _ in candidates], text, True)

    if not lemmas:
        return None
    # Only the dictionary form has an accent in the data. It is exact if the
    # word is in that form, and a hint if not: ráditi, but rȃdīm.
    exact = surface.lower() in {plain(form).lower() for form in lemmas}
    return join(lemmas, text if exact else "", exact)
