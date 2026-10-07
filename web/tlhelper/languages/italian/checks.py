"""Basic grammar checks over the spaCy tokens of one Italian sentence.

    spelling    "maccina"            not in the Italian word list
    repeat      "io io"              a word or a phrase directly after itself
    agreement   "una piccolo gatto"  feminine article, masculine noun

The parse is Universal Dependencies: the article of a noun has the label det,
and an adjective before or after it has the label amod. A preposition with an
article (sul, della) is one token with the label case, so it is not checked.

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


def check_spelling(tokens: list, words: list[dict]) -> None:
    # is_alpha is False for "l'", "un'" and "c'".
    for token, word in zip(tokens, words):
        if word["upos"] in NO_SPELLING_UPOS or not token.is_alpha:
            continue
        problem = base.spelling_problem(token.text.lower(), "it", "Italian")
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
