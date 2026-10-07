"""Basic grammar checks over the spaCy tokens of one French sentence.

    spelling    "maizon"            not in the French word list
    repeat      "je je"             a word or a phrase directly after itself
    agreement   "une petit chat"    feminine article, masculine adjective

The parse is Universal Dependencies: the article of a noun has the label det,
and an adjective before or after it has the label amod.

The tagger reads the gender of a noun from its article, so the check misses an
article with the wrong gender and no other word to show it: "le maison" reads
as a masculine noun. An adjective after être (la maison est grand) is not
checked.
"""

from ...messages import Problem
from .. import base
from ..base import NO_SPELLING_UPOS

# "Nous nous levons": a subject and its reflexive pronoun.
VALID_REPEATS = frozenset({"nous", "vous"})

FEAT_NAMES = {"Gender": "gender", "Number": "number"}
VALUE_NAMES = {
    "Masc": "masculine",
    "Fem": "feminine",
    "Sing": "singular",
    "Plur": "plural",
}
# "du" and "des" are ADP, with the label det.
MODIFIERS = {"det": ("DET", "ADP"), "amod": ("ADJ",)}


def check_spelling(tokens: list, words: list[dict]) -> None:
    # is_alpha is False for "l'", "qu'" and "peut-être".
    for token, word in zip(tokens, words):
        if word["upos"] in NO_SPELLING_UPOS or not token.is_alpha:
            continue
        problem = base.spelling_problem(token.text.lower(), "fr", "French")
        if problem:
            word["problems"].append(problem)


def check_repeats(words: list[dict]) -> None:
    base.check_repeats(words, VALID_REPEATS)


def modifiers(noun) -> list:
    """The articles and the adjectives of a noun, on either side of it."""
    return [
        child for child in noun.children if child.pos_ in MODIFIERS.get(child.dep_, ())
    ]


def check_agreement(tokens: list, words: list[dict]) -> None:
    """An article or an adjective must have the gender and the number of its
    noun."""
    by_token = {token.i: word for token, word in zip(tokens, words)}
    for noun in tokens:
        if noun.pos_ != "NOUN":
            continue
        theirs = noun.morph.to_dict()
        for token in modifiers(noun):
            if by_token[token.i]["problems"]:
                continue
            mine = token.morph.to_dict()
            for feat, name in FEAT_NAMES.items():
                # A plural form has no gender: "les" is both.
                if feat == "Gender" and "Plur" in (
                    mine.get("Number"),
                    theirs.get("Number"),
                ):
                    continue
                if mine.get(feat) and theirs.get(feat) and mine[feat] != theirs[feat]:
                    by_token[token.i]["problems"].append(
                        Problem(
                            "problem-agreement",
                            f"Does not agree with '{noun.text}': this form is"
                            f" {VALUE_NAMES.get(mine[feat], mine[feat])}, but the"
                            f" noun is {VALUE_NAMES.get(theirs[feat], theirs[feat])}"
                            f" ({name}).",
                            noun=noun.text,
                            mine=mine[feat],
                            theirs=theirs[feat],
                            feat=feat,
                        )
                    )


def check(tokens: list, words: list[dict]) -> None:
    """tokens: the spaCy tokens of one sentence. words: the word of each
    token, in the same order. Gives each word its "problems" list."""
    for word in words:
        word["problems"] = []
    check_spelling(tokens, words)
    check_repeats(words)
    check_agreement(tokens, words)
