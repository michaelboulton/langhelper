"""Write the .toml file of a deck package, from a look at its notes:

\b
    uv run python -m scripts.make_toml ../web/decks/basics.apkg --language hr

The result is ../web/decks/basics.toml. The guesses are the two fields with the most
text, which of them is English (the one with fewer letters outside ASCII), and
the note types that have both fields. Read the result, and correct it by hand
or with the options.
"""

import json
from collections import Counter
from pathlib import Path

import click
from tlhelper.flashcards import apkg, decks
from tlhelper.languages import LANGUAGES

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


@click.command(help=__doc__)
@click.argument("package", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--language", required=True, type=click.Choice(sorted(LANGUAGES)))
@click.option("--name", help="the default is the file name")
@click.option("--english-field")
@click.option("--answer-field")
@click.option("--notetype", multiple=True, help="can repeat")
@click.option("--reverse", is_flag=True)
@click.option("--subdecks", is_flag=True, help="one deck for each Anki deck")
@click.option(
    "--to-english-notetype",
    multiple=True,
    help="a note type that only asks for the English. Can repeat",
)
@click.option("--lines", is_flag=True, help="each line of a field is one answer")
@click.option("--new-per-day", type=int, default=10, show_default=True)
@click.option("--reviews-per-day", type=int, default=100, show_default=True)
@click.option("--force", is_flag=True, help="replace the file")
def main(
    package: Path,
    language: str,
    name: str | None,
    english_field: str | None,
    answer_field: str | None,
    notetype: tuple[str, ...],
    reverse: bool,
    subdecks: bool,
    to_english_notetype: tuple[str, ...],
    lines: bool,
    new_per_day: int,
    reviews_per_day: int,
    force: bool,
) -> None:
    target = package.with_suffix(".toml")
    if target.exists() and not force:
        raise SystemExit(f"{target} is there already (--force replaces it)")
    try:
        notes = apkg.read_notes(package)
    except apkg.BadDeck as exc:
        raise SystemExit(str(exc)) from exc
    if not notes:
        raise SystemExit(f"{package} has no notes")

    config = {
        "name": name or package.stem.replace("-", " ").replace("_", " "),
        "language": language,
        **guess(notes),
        "reverse": reverse,
        "new_per_day": new_per_day,
        "reviews_per_day": reviews_per_day,
    }
    given = {
        "english_field": english_field,
        "answer_field": answer_field,
        "notetype": list(notetype),
    }
    config |= {key: value for key, value in given.items() if value}
    if subdecks:
        config["subdecks"] = True
    if to_english_notetype:
        config["to_english_notetypes"] = list(to_english_notetype)
    if lines:
        config["separators"] = ["\n"]
    target.write_text(render(config), encoding="utf-8")

    sizes = Counter(note.notetype for note in notes)
    print(f"{len(notes)} notes:")
    for kind, size in sizes.most_common():
        fields = next(list(n.fields) for n in notes if n.notetype == kind)
        print(f"  {size:6} {kind!r}: {', '.join(fields)}")
    anki_decks = Counter(note.deck for note in notes if note.deck)
    if len(anki_decks) > 1:
        print("Anki decks (--subdecks makes one deck of each):")
        for deck, size in sorted(anki_decks.items()):
            print(f"  {size:6} {' :: '.join(deck)}")
    cards = decks.cards_of(notes, decks.read_config(target))
    with_media = sum(bool(c["prompt_media"] or c["answer_media"]) for c in cards)
    print(f"{target}: {len(cards)} cards, {with_media} with media, for example")
    for card in cards[:: max(len(cards) // 5, 1)][:5]:
        prompt = card["prompt"] or card["prompt_media"]
        print(f"  {prompt!r} -> {card['answers']}")


if __name__ == "__main__":
    main()
