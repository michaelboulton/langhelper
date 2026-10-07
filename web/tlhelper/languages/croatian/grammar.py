"""Basic grammar checks over the tagged words of one Croatian sentence.

classla tags a wrong word by its form, not by what the sentence needs: in
"Pijem kava" it says that kava is nominative. So an error shows as two tags
that do not fit together. These checks use that:

    preposition   "s prijatelj"    s takes the instrumental, prijatelj is nominative
    agreement     "lijepa kuću"    nominative adjective, accusative noun
    genitive      "pun je kava"    pun takes a genitive noun
    object        "Pijem kava"     the verb already holds the subject (ja)

Two more checks need no tags: a word form that the lexicon of classla does not
have ("lebdići"), and a word that repeats ("je je").

The checks only see tags, so they miss an error that is a valid form in that
place ("Živim u Zagreb" reads as u + accusative, and "pun kava" reads as full
of coffees, a genitive plural). They can also flag a correct sentence, for
example an adjective with its own object that GENITIVE_ADJECTIVES does not list.
"""

from ...messages import Problem
from ..base import NO_SPELLING_UPOS, check_repeats

CASE_NAMES = {
    "Nom": "nominative",
    "Gen": "genitive",
    "Dat": "dative",
    "Acc": "accusative",
    "Voc": "vocative",
    "Loc": "locative",
    "Ins": "instrumental",
}
FEAT_NAMES = {"Case": "case", "Gender": "gender", "Number": "number"}
VALUE_NAMES = CASE_NAMES | {
    "Masc": "masculine",
    "Fem": "feminine",
    "Neut": "neuter",
    "Sing": "singular",
    "Plur": "plural",
}

NOMINALS = {"NOUN", "PROPN", "PRON"}
MODIFIERS = {"ADJ", "DET"}
# These verbs take a second nominative: "Postao sam učitelj."
NOMINATIVE_VERBS = {"biti", "postati", "ostati", "zvati"}
# A nominative follows these words: "Radim kao učitelj."
COMPARISONS = {"kao", "nego"}
# These adjectives take a genitive noun: "puna vode", "željan znanja".
GENITIVE_ADJECTIVES = {
    "pun",
    "sit",
    "željan",
    "gladan",
    "žedan",
    "svjestan",
    "vrijedan",
}


class Lexicon:
    """The two dictionaries of the classla lemma model, from the hrLex lexicon:
    forms {'kavu': 'kava'} and tagged {('kavu', 'Ncfsa'): 'kava'}. The tag is a
    MULTEXT-East tag, and the fifth letter of a noun tag is the case."""

    CASE_LETTERS = {
        "Nom": "n",
        "Gen": "g",
        "Dat": "d",
        "Acc": "a",
        "Voc": "v",
        "Loc": "l",
        "Ins": "i",
    }

    # False for a lexicon that is too small to say that a word is wrong.
    spelling = True

    def __init__(self, forms: dict, tagged: dict):
        self.forms = forms
        self.tagged = tagged

    def knows(self, text: str) -> bool:
        return text in self.forms or text.lower() in self.forms

    def noun_can_be(self, text: str, case: str) -> bool:
        """The tagger picks one reading of a form that has several: "jegulja"
        is the nominative singular and also the genitive plural."""
        letter = self.CASE_LETTERS[case]
        return any(
            (text.lower(), f"N{kind}{gender}{number}{letter}{animacy}") in self.tagged
            for kind in "cp"
            for gender in "mfn"
            for number in "sp"
            for animacy in ("", "n", "y")
        )


def fits(lexicon: Lexicon | None, word: dict, case: str) -> bool:
    """True if this noun form can have that case in another reading."""
    return (
        lexicon is not None
        and word["upos"] in ("NOUN", "PROPN")
        and lexicon.noun_can_be(word["text"], case)
    )


def agrees(word: dict, noun: dict) -> list[tuple[str, str, str, str]]:
    """The features where the two words differ: (feature, name, mine, theirs)."""
    return [
        (feat, name, word["feats"][feat], noun["feats"][feat])
        for feat, name in FEAT_NAMES.items()
        if word["feats"].get(feat)
        and noun["feats"].get(feat)
        and word["feats"][feat] != noun["feats"][feat]
    ]


def check_spelling(words: list[dict], lexicon: Lexicon | None) -> None:
    """A word form that the lexicon of classla does not have."""
    if lexicon is None or not lexicon.spelling:
        return
    for word in words:
        if word["upos"] in NO_SPELLING_UPOS or not word["text"].isalpha():
            continue
        if not lexicon.knows(word["text"]):
            word["problems"].append(
                Problem(
                    "problem-hr-lexicon",
                    "The lexicon (hrLex) does not have this word. It can be a"
                    " spelling error, a rare word, or a name.",
                )
            )


def check_genitive_adjectives(words: list[dict], lexicon: Lexicon | None) -> None:
    """ "Čaša je puna vode": the noun after pun is genitive. "Pun čamac" and
    "Pun je čamac" are also correct, because there pun agrees with the noun."""
    for index, word in enumerate(words):
        if word["upos"] != "ADJ" or word["lemma"] not in GENITIVE_ADJECTIVES:
            continue
        rest = [w for w in words[index + 1 :] if w["upos"] != "AUX"]
        noun = next((w for w in rest if w["upos"] not in MODIFIERS), None)
        if noun is None or noun["upos"] != "NOUN":
            continue
        case = noun["feats"].get("Case")
        if not case or case == "Gen" or not agrees(word, noun):
            continue
        # "pun jegulja": the tagger says nominative singular, but the form is
        # also the genitive plural.
        if not fits(lexicon, noun, "Gen"):
            noun["problems"].append(
                Problem(
                    "problem-hr-genitive-adjective",
                    f"'{word['text']}' takes a genitive noun (puna vode), but this"
                    f" form is {CASE_NAMES[case]}.",
                    word=word["text"],
                    got=case,
                )
            )


def check_prepositions(words: list[dict], lexicon: Lexicon | None) -> None:
    """The words from a preposition to its noun must have the case that the
    preposition takes."""
    for index, word in enumerate(words):
        case = word["feats"].get("Case")
        if word["upos"] != "ADP" or not case:
            continue
        for other in words[index + 1 :]:
            other_case = other["feats"].get("Case")
            # A number or a quantity word changes the case of the noun
            # ("s dva prijatelja"), so the check stops there.
            if other["upos"] not in NOMINALS | MODIFIERS or not other_case:
                break
            if other_case != case and not fits(lexicon, other, case):
                other["problems"].append(
                    Problem(
                        "problem-preposition-case",
                        f"The preposition '{word['text']}' takes the"
                        f" {CASE_NAMES[case]} here, but this form is"
                        f" {CASE_NAMES[other_case]}.",
                        word=word["text"],
                        want=case,
                        got=other_case,
                    )
                )
            if other["upos"] in NOMINALS:
                break


def check_agreement(words: list[dict]) -> None:
    """An adjective or a determiner directly before a noun must have the case,
    the gender, and the number of the noun."""
    for index, word in enumerate(words):
        # check_genitive_adjectives has the rule for pun and the like.
        if word["upos"] not in MODIFIERS or word["lemma"] in GENITIVE_ADJECTIVES:
            continue
        noun = next((w for w in words[index + 1 :] if w["upos"] not in MODIFIERS), None)
        if noun is None or noun["upos"] != "NOUN":
            continue
        for feat, name, mine, theirs in agrees(word, noun):
            word["problems"].append(
                Problem(
                    "problem-agreement",
                    f"Does not agree with '{noun['text']}': this form is"
                    f" {VALUE_NAMES.get(mine, mine)}, but the noun is"
                    f" {VALUE_NAMES.get(theirs, theirs)} ({name}).",
                    noun=noun["text"],
                    mine=mine,
                    theirs=theirs,
                    feat=feat,
                )
            )


def check_object(words: list[dict], lexicon: Lexicon | None) -> None:
    """A verb in the first or the second person holds its subject (ja, ti, mi,
    vi), so a nominative noun next to it is most likely an object in the wrong
    case. Tags do not show the clauses, so this only checks a sentence with one
    finite verb."""
    finite = [w for w in words if w["feats"].get("VerbForm") == "Fin"]
    if len(finite) != 1 or finite[0]["feats"].get("Person") not in ("1", "2"):
        return
    verbs = [w for w in words if w["upos"] == "VERB"]
    if not verbs or any(w["lemma"] in NOMINATIVE_VERBS for w in verbs):
        return
    if any(w["text"].lower() in COMPARISONS for w in words):
        return
    for word in words:
        # A noun with a wrong case already has its reason ("s prijatelj").
        if any("this form is" in problem for problem in word["problems"]):
            continue
        if word["upos"] != "NOUN" or word["feats"].get("Case") != "Nom":
            continue
        if not fits(lexicon, word, "Acc"):
            word["problems"].append(
                Problem(
                    "problem-hr-object",
                    f"The subject is already in the verb '{verbs[-1]['text']}', so"
                    " this noun is not the subject. An object is usually"
                    " accusative, but this form is nominative.",
                    verb=verbs[-1]["text"],
                )
            )


def check(words: list[dict], lexicon: Lexicon | None = None) -> None:
    """Give each word a 'problems' list: one sentence for each failed check.
    With no lexicon there is no spelling check, and the case checks trust the
    tagger on a form that has several readings."""
    for word in words:
        word["problems"] = []
    check_spelling(words, lexicon)
    check_repeats(words)
    check_prepositions(words, lexicon)
    check_agreement(words)
    check_genitive_adjectives(words, lexicon)
    check_object(words, lexicon)
