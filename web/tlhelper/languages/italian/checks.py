"""Basic grammar checks over the words of one Italian sentence, from the light
model (spaCy) or the heavy one (Stanza).

    spelling    "maccina"            not in the Italian word list
    repeat      "io io"              a word or a phrase directly after itself
    agreement   "una piccolo gatto"  feminine article, masculine noun

The parse is Universal Dependencies: the article of a noun has the label det,
and an adjective before or after it has the label amod. The light model keeps
a preposition with an article (sul, della) as one word with the label case, so
it is not checked. The heavy model splits it into "su il", so the article is
checked.

The tagger reads the gender of a noun from its article, so the check misses an
article with the wrong gender and no other word to show it: "il casa" reads
as a masculine noun, and "il gatti" loses the number of the noun. An adjective
after essere (la casa è grande) is not checked.
"""

from ...messages import Problem
from .. import base
from ..base import NO_SPELLING_UPOS

VALID_REPEATS: frozenset[str] = frozenset()

FEAT_NAMES = {"Gender": "gender", "Number": "number"}
VALUE_NAMES = {
    "Masc": "masculine",
    "Fem": "feminine",
    "Sing": "singular",
    "Plur": "plural",
}
MODIFIERS = {"det": ("DET", "ADP"), "amod": ("ADJ",)}


def check_spelling(words: list[dict]) -> None:
    # isalpha is False for "l'", "un'" and "c'".
    for word in words:
        if word["upos"] in NO_SPELLING_UPOS or not word["text"].isalpha():
            continue
        problem = base.spelling_problem(word["text"].lower(), "it", "Italian")
        if problem:
            word["problems"].append(problem)


def check_repeats(words: list[dict]) -> None:
    base.check_repeats(words, VALID_REPEATS)


def modifiers(noun: dict, words: list[dict]) -> list[dict]:
    """The articles and the adjectives of a noun, on either side of it."""
    return [
        word
        for word in words
        if word["head"] == noun["id"]
        and word["upos"] in MODIFIERS.get(word["deprel"], ())
    ]


def check_agreement(words: list[dict]) -> None:
    """An article or an adjective must have the gender and the number of its
    noun."""
    for noun in words:
        if noun["upos"] != "NOUN":
            continue
        theirs = noun["feats"]
        for word in modifiers(noun, words):
            if word["problems"]:
                continue
            mine = word["feats"]
            for feat, name in FEAT_NAMES.items():
                if mine.get(feat) and theirs.get(feat) and mine[feat] != theirs[feat]:
                    word["problems"].append(
                        Problem(
                            "problem-agreement",
                            f"Does not agree with '{noun['text']}': this form is"
                            f" {VALUE_NAMES.get(mine[feat], mine[feat])}, but the"
                            f" noun is {VALUE_NAMES.get(theirs[feat], theirs[feat])}"
                            f" ({name}).",
                            noun=noun["text"],
                            mine=mine[feat],
                            theirs=theirs[feat],
                            feat=feat,
                        )
                    )


def check_words(words: list[dict]) -> None:
    """words: one sentence, with head and deprel. Gives each word its
    "problems" list."""
    for word in words:
        word["problems"] = []
    check_spelling(words)
    check_repeats(words)
    check_agreement(words)


def check(tokens: list, words: list[dict]) -> None:
    """The callback of SpacyTagger. The words already have all that the checks
    need."""
    check_words(words)
