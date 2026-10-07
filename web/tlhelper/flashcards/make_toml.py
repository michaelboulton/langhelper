"""Write the .toml file of a deck package, from a look at its notes:

    uv run python -m tlhelper.flashcards.make_toml decks/basics.apkg --language hr

The result is decks/basics.toml. The guesses are the two fields with the most
text, which of them is English (the one with fewer letters outside ASCII), and
the note types that have both fields. Read the result, and correct it by hand
or with the options.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from ..languages import LANGUAGES
from . import apkg, decks

# A note type with a smaller share of the notes is not part of the guess.
# These are mostly the few notes that the author made for something else.
MIN_SHARE = 0.01


def foreign_share(texts: list[str]) -> float:
    letters = [char for text in texts for char in text if char.isalpha()]
    return sum(not char.isascii() for char in letters) / max(len(letters), 1)


def guess(notes: list[apkg.Note]) -> dict:
    """{"english_field", "answer_field", "notetype"} for the largest group of
    notes with the same two fields."""
    # A picture counts: it can be the whole English side of a note.
    filled = Counter(
        (note.notetype, name)
        for note in notes
        for name, value in note.fields.items()
        if value or note.media.get(name)
    )
    sizes = Counter(note.notetype for note in notes)
    largest = sizes.most_common(1)[0][0]
    names = sorted(
        (name for notetype, name in filled if notetype == largest),
        key=lambda name: -filled[largest, name],
    )[:2]
    if len(names) < 2:
        raise SystemExit(f"the note type {largest!r} has no two fields with text")
    texts = {
        name: [n.fields[name] for n in notes if n.notetype == largest] for name in names
    }
    english, answer = sorted(names, key=lambda name: foreign_share(texts[name]))
    notetypes = [
        notetype
        for notetype, size in sizes.most_common()
        if size >= MIN_SHARE * len(notes)
        and filled[notetype, english]
        and filled[notetype, answer]
    ]
    return {"english_field": english, "answer_field": answer, "notetype": notetypes}


def render(config: dict) -> str:
    # A JSON string or list of strings is also valid TOML.
    lines = [
        f"{key} = {json.dumps(value, ensure_ascii=False)}"
        for key, value in config.items()
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", type=Path)
    parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
    parser.add_argument("--name", help="the default is the file name")
    parser.add_argument("--english-field")
    parser.add_argument("--answer-field")
    parser.add_argument("--notetype", action="append", help="can repeat")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument(
        "--subdecks", action="store_true", help="one deck for each Anki deck"
    )
    parser.add_argument(
        "--to-english-notetype",
        action="append",
        help="a note type that only asks for the English. Can repeat",
    )
    parser.add_argument(
        "--lines", action="store_true", help="each line of a field is one answer"
    )
    parser.add_argument("--new-per-day", type=int, default=10)
    parser.add_argument("--reviews-per-day", type=int, default=100)
    parser.add_argument("--force", action="store_true", help="replace the file")
    args = parser.parse_args()

    target = args.package.with_suffix(".toml")
    if target.exists() and not args.force:
        raise SystemExit(f"{target} is there already (--force replaces it)")
    try:
        notes = apkg.read_notes(args.package)
    except apkg.BadDeck as exc:
        raise SystemExit(str(exc)) from exc
    if not notes:
        raise SystemExit(f"{args.package} has no notes")

    config = {
        "name": args.name or args.package.stem.replace("-", " ").replace("_", " "),
        "language": args.language,
        **guess(notes),
        "reverse": args.reverse,
        "new_per_day": args.new_per_day,
        "reviews_per_day": args.reviews_per_day,
    }
    for key in ("english_field", "answer_field", "notetype"):
        if getattr(args, key):
            config[key] = getattr(args, key)
    if args.subdecks:
        config["subdecks"] = True
    if args.to_english_notetype:
        config["to_english_notetypes"] = args.to_english_notetype
    if args.lines:
        config["separators"] = ["\n"]
    target.write_text(render(config), encoding="utf-8")

    sizes = Counter(note.notetype for note in notes)
    print(f"{len(notes)} notes:")
    for notetype, size in sizes.most_common():
        fields = next(list(n.fields) for n in notes if n.notetype == notetype)
        print(f"  {size:6} {notetype!r}: {', '.join(fields)}")
    anki_decks = Counter(note.deck for note in notes if note.deck)
    if len(anki_decks) > 1:
        print("Anki decks (--subdecks makes one deck of each):")
        for name, size in sorted(anki_decks.items()):
            print(f"  {size:6} {' :: '.join(name)}")
    cards = decks.cards_of(notes, decks.read_config(target))
    with_media = sum(bool(c["prompt_media"] or c["answer_media"]) for c in cards)
    print(f"{target}: {len(cards)} cards, {with_media} with media, for example")
    for card in cards[:: max(len(cards) // 5, 1)][:5]:
        prompt = card["prompt"] or card["prompt_media"]
        print(f"  {prompt!r} -> {card['answers']}")


if __name__ == "__main__":
    main()
