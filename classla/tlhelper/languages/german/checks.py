"""Basic grammar checks over the spaCy tokens of one German sentence.

    spelling      "Hungr"             not in the German word list
    repeat        "habe habe"         a word or a phrase directly after itself
    agreement     "der Haus"          feminine or masculine article, neuter noun
    ending        "ein kleine Hund"   after ein, a masculine nominative takes -er
    preposition   "mit den Hund"      mit takes the dative, den is accusative

The tagger reads the case of a word from its context, and a German noun mostly
has the same form in each case. So the case checks only trust the words that
show their case: an article, an adjective, and a pronoun. The parse is the
TIGER scheme: the noun of a preposition, and the article and the adjectives of
a noun, all have the label nk (noun kernel).

The checks miss an error that is a valid form in that place: "Ich wohne in die
Stadt" reads as in + accusative, and "Ich sehe der Mann" reads as a subject.
"""

from .. import base
from ...messages import Problem
from ..base import NO_SPELLING_UPOS

# "Die Frau, die die Katze hat": a relative pronoun before an article.
# check_repeats compares in lower case, so "sie" is also "Sie".
VALID_REPEATS = frozenset({"der", "die", "das", "sie"})

CASE_NAMES = {
    "Nom": "nominative",
    "Gen": "genitive",
    "Dat": "dative",
    "Acc": "accusative",
}
# The case is not here: see the module text.
FEAT_NAMES = {"Gender": "gender", "Number": "number"}
VALUE_NAMES = {
    "Masc": "masculine",
    "Fem": "feminine",
    "Neut": "neuter",
    "Sing": "singular",
    "Plur": "plural",
}

# Preposition lemma: the cases that it can take. A contraction has the lemma
# of its preposition: "zum" is "zu". Everyday speech uses the dative after the
# genitive prepositions, so that passes.
ACCUSATIVE = {"Acc"}
DATIVE = {"Dat"}
TWO_WAY = {"Acc", "Dat"}
GENITIVE = {"Gen", "Dat"}
PREPOSITIONS = {
    "bis": ACCUSATIVE,
    "durch": ACCUSATIVE,
    "für": ACCUSATIVE,
    "gegen": ACCUSATIVE,
    "ohne": ACCUSATIVE,
    "um": ACCUSATIVE,
    "aus": DATIVE,
    "außer": DATIVE,
    "bei": DATIVE,
    "gegenüber": DATIVE,
    "mit": DATIVE,
    "nach": DATIVE,
    "seit": DATIVE,
    "von": DATIVE,
    "zu": DATIVE,
    "an": TWO_WAY,
    "auf": TWO_WAY,
    "hinter": TWO_WAY,
    "in": TWO_WAY,
    "neben": TWO_WAY,
    "über": TWO_WAY,
    "unter": TWO_WAY,
    "vor": TWO_WAY,
    "zwischen": TWO_WAY,
    "statt": GENITIVE,
    "trotz": GENITIVE,
    "während": GENITIVE,
    "wegen": GENITIVE,
}

# The ending of an adjective before a noun depends on the word before it.
# After a der-word the adjective is weak, after an ein-word it is mixed, and
# with no article it is strong and has the ending of the der-word itself.
DER_WORDS = {"der", "dieser", "jeder", "jener", "welcher", "mancher", "solcher"}
DER_WORDS |= {"alle", "aller"}
EIN_WORDS = {"ein", "kein", "mein", "dein", "sein", "ihr", "unser", "euer"}
STRONG = {
    "Masc": {"Nom": "er", "Acc": "en", "Dat": "em", "Gen": "en"},
    "Neut": {"Nom": "es", "Acc": "es", "Dat": "em", "Gen": "en"},
    "Fem": {"Nom": "e", "Acc": "e", "Dat": "er", "Gen": "er"},
    "Plur": {"Nom": "e", "Acc": "e", "Dat": "en", "Gen": "er"},
}
# For is_compound: the shortest part of a compound word, and what can stand
# between two parts. A short part gives false splits ("Hun" + "gr").
MIN_COMPOUND_PART = 4
LINKS = ("", "s", "n", "es", "en")
# The longest first: "kleinen" ends in -en, not in -n.
ENDINGS = ("en", "em", "er", "es", "e")
KIND_NAMES = {
    "weak": "after a word like der",
    "mixed": "after a word like ein",
    "strong": "with no article",
}


def is_compound(text: str, parts: int = 3) -> bool:
    """German joins words, and no word list has every result:
    "Luftkissenfahrzeug" is Luft + Kissen + Fahrzeug. True if the text splits
    into known words, with a linking -s- or -n- between them ("Arbeitszimmer")."""
    checker = base.speller("de")
    if text in checker:
        return True
    if parts == 1:
        return False
    for cut in range(MIN_COMPOUND_PART, len(text) - MIN_COMPOUND_PART + 1):
        head, rest = text[:cut], text[cut:]
        if head not in checker:
            continue
        if any(
            rest.startswith(link)
            and len(rest) - len(link) >= MIN_COMPOUND_PART
            and is_compound(rest[len(link) :], parts - 1)
            for link in LINKS
        ):
            return True
    return False


def check_spelling(tokens: list, words: list[dict]) -> None:
    for token, word in zip(tokens, words):
        if word["upos"] in NO_SPELLING_UPOS or not token.is_alpha:
            continue
        # A noun has a capital letter, and the word list has "Hund" as "hund".
        text = token.text.lower()
        problem = base.spelling_problem(text, "de", "German")
        if problem and not is_compound(text):
            word["problems"].append(problem)


def check_repeats(words: list[dict]) -> None:
    base.check_repeats(words, VALID_REPEATS)


def kernel(noun) -> list:
    """The article, the pronouns and the adjectives of a noun."""
    return [
        child
        for child in noun.children
        if child.dep_ == "nk" and child.pos_ in ("DET", "ADJ") and child.i < noun.i
    ]


def check_agreement(tokens: list, words: list[dict]) -> None:
    """An article or an adjective must have the gender and the number of its
    noun."""
    by_token = {token.i: word for token, word in zip(tokens, words)}
    for noun in tokens:
        if noun.pos_ != "NOUN":
            continue
        theirs = noun.morph.to_dict()
        for token in kernel(noun):
            # "mit der Hund": the heavy model says that "der" is a nominative,
            # and then takes the gender of the noun from the article. One
            # reason is enough, and that gender is not a fact about the noun.
            if by_token[token.i]["problems"]:
                continue
            mine = token.morph.to_dict()
            for feat, name in FEAT_NAMES.items():
                # A plural form has no gender.
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


def declension(noun) -> str:
    lemmas = {t.lemma_.lower() for t in kernel(noun) if t.pos_ == "DET"}
    # "im" is "in dem", so it counts as a der-word.
    contraction = noun.dep_ == "nk" and noun.head.tag_ == "APPRART"
    if lemmas & DER_WORDS or contraction:
        return "weak"
    if lemmas & EIN_WORDS:
        return "mixed"
    return "strong"


def expected_ending(kind: str, case: str, gender: str, number: str) -> str | None:
    if case not in CASE_NAMES:
        return None
    if number == "Plur":
        return STRONG["Plur"][case] if kind == "strong" else "en"
    if gender not in STRONG:
        return None
    if kind == "weak":
        return "e" if case == "Nom" or (case == "Acc" and gender != "Masc") else "en"
    if kind == "mixed" and case in ("Dat", "Gen"):
        return "en"
    return STRONG[gender][case]


def check_adjective_endings(tokens: list, words: list[dict]) -> None:
    by_token = {token.i: word for token, word in zip(tokens, words)}
    for noun in tokens:
        if noun.pos_ != "NOUN":
            continue
        feats = noun.morph.to_dict()
        kind = declension(noun)
        expected = expected_ending(
            kind, feats.get("Case"), feats.get("Gender"), feats.get("Number")
        )
        if expected is None:
            continue
        for token in kernel(noun):
            word = by_token[token.i]
            # A word with another error already has its reason.
            if token.pos_ != "ADJ" or word["problems"]:
                continue
            text = token.text.lower()
            ending = next((e for e in ENDINGS if text.endswith(e)), None)
            # No ending: "lila", "rosa", "Berliner" do not change.
            if ending is None or ending == expected:
                continue
            plural = feats.get("Number") == "Plur"
            form = "plural" if plural else VALUE_NAMES[feats["Gender"]]
            word["problems"].append(
                Problem(
                    "problem-de-adjective-ending",
                    f"The ending -{ending} does not fit '{noun.text}' ({form}"
                    f" {CASE_NAMES[feats['Case']]}). {KIND_NAMES[kind].capitalize()},"
                    f" the ending is -{expected}.",
                    ending=ending,
                    noun=noun.text,
                    # The gender of a singular noun, or "Plur".
                    form="Plur" if plural else feats["Gender"],
                    case=feats["Case"],
                    kind=kind,
                    expected=expected,
                )
            )


def check_prepositions(tokens: list, words: list[dict]) -> None:
    by_token = {token.i: word for token, word in zip(tokens, words)}
    for prep in tokens:
        cases = PREPOSITIONS.get(prep.lemma_.lower())
        if prep.pos_ != "ADP" or cases is None:
            continue
        # "im" and "zum" hold their article, so they show their case.
        marked = [prep] if prep.tag_ == "APPRART" else []
        for child in prep.children:
            if child.dep_ != "nk" or child.i < prep.i:
                continue
            if child.pos_ == "PRON":
                marked.append(child)
            elif child.pos_ in ("NOUN", "PROPN"):
                marked += kernel(child)
        for token in marked:
            case = token.morph.get("Case")
            if not case or case[0] in cases or case[0] not in CASE_NAMES:
                continue
            wanted = sorted(cases, reverse=True)
            needs = " or the ".join(CASE_NAMES[c] for c in wanted)
            by_token[token.i]["problems"].append(
                Problem(
                    "problem-preposition-cases",
                    f"The preposition '{prep.text}' takes the {needs}, but this"
                    f" form is {CASE_NAMES[case[0]]}.",
                    word=prep.text,
                    # A list: the page joins it with the "or" of its language.
                    want=wanted,
                    got=case[0],
                )
            )


def check(tokens: list, words: list[dict]) -> None:
    """tokens: the spaCy tokens of one sentence. words: the word of each
    token, in the same order. Gives each word its "problems" list."""
    for word in words:
        word["problems"] = []
    check_spelling(tokens, words)
    check_repeats(words)
    check_prepositions(tokens, words)
    check_agreement(tokens, words)
    check_adjective_endings(tokens, words)
