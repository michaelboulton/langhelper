"""Build the data file of one language from the kaikki.org export of Wiktionary.

Croatian, with the accents and the glosses (languages/croatian/accents.db):

    curl -LO https://kaikki.org/dictionary/Serbo-Croatian/kaikki.org-dictionary-SerboCroatian.jsonl
    uv run python -m tlhelper.build_glosses kaikki.org-dictionary-SerboCroatian.jsonl

German, with the glosses only (languages/german/glosses.db):

    curl -LO https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl
    uv run python -m tlhelper.build_glosses --language de kaikki.org-dictionary-German.jsonl

French, with the glosses only (languages/french/glosses.db):

    curl -LO https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl
    uv run python -m tlhelper.build_glosses --language fr kaikki.org-dictionary-French.jsonl

Italian, with the glosses only (languages/italian/glosses.db):

    curl -LO https://kaikki.org/dictionary/Italian/kaikki.org-dictionary-Italian.jsonl
    uv run python -m tlhelper.build_glosses --language it kaikki.org-dictionary-Italian.jsonl

The full raw dump from https://kaikki.org/dictionary/rawdata.html works too,
because the script only reads the lines of one language. Run this by hand
when you want newer data, then commit the file. See languages/glosses.py and
languages/croatian/accents.py for the tables.
"""

import argparse
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from .languages.croatian.accents import ACCENTS_PATH, SCHEMA
from .languages.french import GLOSSES_PATH as FRENCH_GLOSSES_PATH
from .languages.german import GLOSSES_PATH as GERMAN_GLOSSES_PATH
from .languages.glosses import GLOSSES_SCHEMA, entry_key, plain
from .languages.italian import GLOSSES_PATH as ITALIAN_GLOSSES_PATH

# Our language code: (the lang_code of Wiktionary, the file, its schema). Only
# Wiktionary has one code for Croatian and Serbian. A file with no accent
# tables stays small, because the forms are most of accents.db.
LANGUAGES = {
    "hr": ("sh", ACCENTS_PATH, SCHEMA),
    "de": ("de", GERMAN_GLOSSES_PATH, GLOSSES_SCHEMA),
    "fr": ("fr", FRENCH_GLOSSES_PATH, GLOSSES_SCHEMA),
    "it": ("it", ITALIAN_GLOSSES_PATH, GLOSSES_SCHEMA),
}

# One Wiktionary part of speech can be several UPOS tags in classla.
UPOS = {
    "noun": ["NOUN"],
    "name": ["PROPN"],
    "verb": ["VERB", "AUX"],
    "adj": ["ADJ"],
    "adv": ["ADV"],
    "pron": ["PRON", "DET"],
    "det": ["DET"],
    "article": ["DET"],
    # French "du" and "au": spaCy tags them ADP.
    "contraction": ["ADP"],
    "num": ["NUM"],
    "prep": ["ADP"],
    "conj": ["CCONJ", "SCONJ"],
    "particle": ["PART"],
    "intj": ["INTJ"],
}
CASES = {
    "nominative": "nom",
    "genitive": "gen",
    "dative": "dat",
    "accusative": "acc",
    "vocative": "voc",
    "locative": "loc",
    "instrumental": "ins",
}
NUMBERS = {"singular": "sg", "plural": "pl"}
# Not a form of this word: table headers, other scripts, derived words.
SKIP_TAGS = {
    "table-tags",
    "inflection-template",
    "romanization",
    "Cyrillic",
    "diminutive",
    "augmentative",
    "relational",
    "noun-from-verb",
    "demonym",
}
# Not part of a translation: "a house", "somebody's".
GLOSS_STOPWORDS = {
    "a",
    "an",
    "the",
    "s",
    "of",
    "or",
    "etc",
    "something",
    "somebody",
    "someone",
}
MAX_GLOSS_WORDS = 3


def is_latin(text: str) -> bool:
    return not any("CYRILLIC" in unicodedata.name(char, "") for char in text)


def has_accent(text: str) -> bool:
    return plain(text) != unicodedata.normalize("NFC", text)


def gloss_words(entry: dict) -> list[str]:
    """The English words that translate this entry: 'to drink (to consume
    liquid)' gives drink, and 'full, filled' gives full and filled. A long
    gloss is a description and not a translation, so it gives nothing."""
    words = []
    for sense in entry.get("senses", []):
        if sense.get("form_of") or sense.get("alt_of"):
            continue
        for gloss in sense.get("glosses", []):
            for part in re.split(r"[,;/]", re.sub(r"\([^)]*\)", " ", gloss)):
                tokens = re.findall(r"[a-z]+", part.lower())
                # "to drink" is the verb drink, but "to" alone is the
                # preposition: u means "to, into".
                if len(tokens) > 1 and tokens[0] == "to":
                    tokens = tokens[1:]
                tokens = [t for t in tokens if t not in GLOSS_STOPWORDS]
                if len(tokens) <= MAX_GLOSS_WORDS:
                    words.extend(tokens)
    return words


def rows(entry: dict):
    """Yield ('lemma', key, form), ('form', key, surface, form, case, number),
    and ('gloss', key, word, rank)."""
    for upos in UPOS.get(entry.get("pos"), []):
        key = entry_key(entry["word"], upos)
        for rank, word in enumerate(dict.fromkeys(gloss_words(entry))):
            yield ("gloss", key, word, rank)
        for item in entry.get("forms", []):
            form = unicodedata.normalize("NFC", item["form"])
            tags = set(item.get("tags", []))
            if tags & SKIP_TAGS or not is_latin(form) or not has_accent(form):
                continue
            if "canonical" in tags:
                yield ("lemma", key, form)
                continue
            surface = plain(form) if upos == "PROPN" else plain(form).lower()
            case = next((CASES[t] for t in tags if t in CASES), "")
            number = next((NUMBERS[t] for t in tags if t in NUMBERS), "")
            yield ("form", key, surface, form, case, number)


def build(source: Path, target: Path, language: str = "hr") -> tuple[int, int, int]:
    lang_code, _, schema = LANGUAGES[language]
    accents = schema is SCHEMA
    target.unlink(missing_ok=True)
    conn = sqlite3.connect(target)
    conn.executescript(schema)
    # Wiktionary has several entries for one word (grad: city, hail), and one
    # UPOS list can name a row twice. dict keys keep the first-seen order.
    seen = {}
    # (key, word) -> the lowest rank over the entries of a homograph.
    glosses = {}
    with open(source, encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)
            if entry.get("lang_code") != lang_code:
                continue
            for row in rows(entry):
                if row[0] == "gloss":
                    _, key, word, rank = row
                    glosses[key, word] = min(rank, glosses.get((key, word), rank))
                elif accents:
                    seen[row] = None
    conn.executemany(
        "INSERT INTO glosses VALUES (?, ?, ?)",
        [(key, word, rank) for (key, word), rank in glosses.items()],
    )
    for seq, (kind, key, *rest) in enumerate(seen):
        if kind == "lemma":
            conn.execute("INSERT INTO lemmas VALUES (?, ?, ?)", (key, seq, *rest))
        else:
            surface, form, case, number = rest
            conn.execute(
                "INSERT INTO forms VALUES (?, ?, ?, ?, ?, ?)",
                (key, surface, seq, form, case, number),
            )
    conn.commit()
    counts = (
        conn.execute("SELECT count(*) FROM lemmas").fetchone()[0] if accents else 0,
        conn.execute("SELECT count(*) FROM forms").fetchone()[0] if accents else 0,
        conn.execute("SELECT count(*) FROM glosses").fetchone()[0],
    )
    conn.execute("VACUUM")
    conn.close()
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="the kaikki.org JSONL file")
    parser.add_argument("--language", choices=sorted(LANGUAGES), default="hr")
    args = parser.parse_args()
    path = LANGUAGES[args.language][1]
    lemmas, forms, glosses = build(args.source, path, args.language)
    size = path.stat().st_size / 1e6
    print(
        f"{path.name}: {lemmas} lemmas, {forms} forms, {glosses} glosses, {size:.1f} MB"
    )
