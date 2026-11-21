"""Look inside a deck package, before and after you write its .toml:

\b
    uv run python -m tlhelper.flashcards.inspect_deck notes decks/x.apkg
    uv run python -m tlhelper.flashcards.inspect_deck cards decks/x.apkg
"""

import re
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

import click

from . import apkg, decks, store

PACKAGE = click.argument(
    "package", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
LIMIT = click.option(
    "--limit", default=5, show_default=True, help="examples to print, 0 for all"
)
GREP = click.option("--grep", help="only the ones with text that matches this regex")


def spread(items: list, limit: int) -> list:
    """`limit` items from the whole list, not only from its start."""
    if not limit:
        return items
    return items[:: max(len(items) // limit, 1)][:limit]


def read(package: Path) -> list[apkg.Note]:
    try:
        return apkg.read_notes(package)
    except apkg.BadDeck as exc:
        raise SystemExit(str(exc)) from exc


@click.group(help=__doc__)
def main() -> None:
    pass


@main.command()
@PACKAGE
@click.option("--notetype", multiple=True, help="can repeat")
@GREP
@LIMIT
@click.option(
    "--width", default=70, show_default=True, help="characters of a field, 0 for all"
)
def notes(
    package: Path, notetype: tuple[str, ...], grep: str | None, limit: int, width: int
) -> None:
    """The Anki decks, the note types, how many notes fill each field, and
    example notes."""
    found = read(package)
    if notetype:
        found = [note for note in found if note.notetype in notetype]
    if grep:
        pattern = re.compile(grep)
        found = [
            note
            for note in found
            if any(pattern.search(value) for value in note.fields.values())
        ]
    print(f"{len(found)} notes")
    anki_decks = Counter(note.deck for note in found if note.deck)
    if len(anki_decks) > 1:
        for deck, size in sorted(anki_decks.items()):
            print(f"  {size:6} {' :: '.join(deck)}")
    groups = defaultdict(list)
    for note in found:
        groups[note.notetype].append(note)
    for kind, group in sorted(groups.items(), key=lambda item: -len(item[1])):
        print(f"{kind!r}: {len(group)} notes, filled fields:")
        for name in group[0].fields:
            filled = sum(
                bool(note.fields.get(name, "").strip() or note.media.get(name))
                for note in group
            )
            print(f"  {filled:6} {name}")
        for note in spread(group, limit):
            print(f"  {note.guid}")
            for name, value in note.fields.items():
                media = note.media.get(name, [])
                if value or media:
                    text = value[:width] if width else value
                    print(f"    {name}: {text!r}{' ' + str(media) if media else ''}")


@main.command()
@PACKAGE
@click.option(
    "--direction",
    type=click.Choice(
        [store.TO_STUDY, store.TO_ENGLISH, store.LISTEN, store.DICTATION]
    ),
)
@click.option(
    "--prompt-media",
    type=click.Choice(["audio", "image", "none"]),
    help="only the cards with this kind of media in the prompt",
)
@GREP
@LIMIT
def cards(
    package: Path,
    direction: str | None,
    prompt_media: str | None,
    grep: str | None,
    limit: int,
) -> None:
    """The cards that the import makes from the package with the .toml next
    to it."""
    try:
        config = decks.read_config(package.with_suffix(".toml"))
    except (OSError, apkg.BadDeck, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    made = decks.cards_of(read(package), config)
    print(f"{len(made)} cards:", dict(Counter(card["direction"] for card in made)))
    if config["subdecks"]:
        for deck, group in decks.subdecks_of(package.stem, config, made):
            print(f"  {len(group):6} {' / '.join(deck['path'])}")

    def kinds(card: dict) -> set[str]:
        return {apkg.kind(name)[0] for name in card["prompt_media"]} or {"none"}

    shown = [
        card
        for card in made
        if (not direction or card["direction"] == direction)
        and (not prompt_media or prompt_media in kinds(card))
        and (
            not grep
            or any(re.search(grep, text) for text in [card["prompt"], *card["answers"]])
        )
    ]
    if len(shown) != len(made):
        print(f"{len(shown)} cards match")
    for card in spread(shown, limit):
        print(
            f"  {card['direction']}: {card['prompt']!r} {card['prompt_media']}"
            f" -> {card['answers']} {card['answer_media']}"
        )


if __name__ == "__main__":
    main()
