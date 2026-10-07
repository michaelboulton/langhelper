"""Basic checks of an English text, before DeepL translates it to Croatian.

The user is fluent in English, so this only looks for a slip that can give a
bad translation: a word with a spelling error, a word or a phrase that
repeats, and a verb that does not agree with its subject ("i is not").

The checks read the tags and the parse of spaCy. A word that fails a check
gets a reason in its "problems" list, like the words of the other languages.
"""

from ...messages import Problem
from .. import base
from ..base import NO_SPELLING_UPOS

# "He said that that was wrong" and "she had had enough" are correct.
VALID_REPEATS = frozenset({"that", "had"})

FINITE_TAGS = {"VBZ", "VBP", "VBD"}
SUBJECT_DEPS = {"nsubj", "nsubjpass"}
PRONOUNS = {
    "i": "first",
    "he": "singular",
    "she": "singular",
    "it": "singular",
    "we": "plural",
    "you": "plural",
    "they": "plural",
}
DEMONSTRATIVES = {
    "this": "singular",
    "that": "singular",
    "these": "plural",
    "those": "plural",
}
# A singular form that often takes a plural verb: "the police are", "the team
# are" (British), "the fish are".
PLURAL_SENSE = {
    "couple",
    "data",
    "deer",
    "family",
    "fish",
    "majority",
    "media",
    "pair",
    "people",
    "police",
    "rest",
    "sheep",
    "staff",
    "team",
}
SUBJECT_NAMES = {
    "first": "'I'",
    "singular": "a singular subject",
    "plural": "a plural subject",
}
# lemma: the present forms and the past forms for first, singular, plural.
IRREGULAR = {
    "be": {
        "present": {"first": "am", "singular": "is", "plural": "are"},
        "past": {"first": "was", "singular": "was", "plural": "were"},
    },
    "have": {"present": {"first": "have", "singular": "has", "plural": "have"}},
    "do": {"present": {"first": "do", "singular": "does", "plural": "do"}},
}


def spelling_problem(text: str) -> str | None:
    return base.spelling_problem(text, "en", "English")


def glued(tokens: list, index: int) -> bool:
    """No space between this token and the next one, and the next one is not
    punctuation."""
    if tokens[index].whitespace_ or index + 1 >= len(tokens):
        return False
    return not tokens[index + 1].is_punct


def check_spelling(tokens: list, words: list[dict]) -> None:
    for index, (token, word) in enumerate(zip(tokens, words)):
        if word["upos"] in NO_SPELLING_UPOS or not token.is_alpha:
            continue
        # spaCy splits "can't" into "ca" and "n't", and "gonna" into "gon" and
        # "na". The parts are not words.
        if glued(tokens, index) or (index and glued(tokens, index - 1)):
            continue
        problem = spelling_problem(token.text.lower())
        if problem:
            word["problems"].append(problem)


def subject_kind(token) -> str | None:
    """'first', 'singular' or 'plural' for a subject. None if the word is not
    a subject, or if its number is not sure."""
    if token.dep_ not in SUBJECT_DEPS:
        return None
    # "Tom and Ana": two singular subjects take a plural verb.
    if any(child.dep_ == "conj" for child in token.children):
        return "plural"
    text = token.text.lower()
    if token.tag_ == "PRP":
        return PRONOUNS.get(text)
    if token.tag_ == "DT":
        return DEMONSTRATIVES.get(text)
    if token.tag_ == "NNS":
        return "plural"
    if token.tag_ == "NN" and text not in PLURAL_SENSE:
        # "A lot of people are here": the verb agrees with "people".
        if any(child.dep_ == "prep" for child in token.children):
            return None
        return "singular"
    return None


def finite_verb(subject):
    """The verb that agrees with the subject: the first helper verb, or the
    main verb. None after a modal ("he can go"), because a modal has one form."""
    head = subject.head
    helpers = [c for c in head.children if c.dep_ in ("aux", "auxpass")]
    verb = min([*helpers, head], key=lambda token: token.i)
    return verb if verb.tag_ in FINITE_TAGS else None


def agreement_problem(kind: str, verb) -> str | None:
    text, lemma = verb.text.lower(), verb.lemma_.lower()
    if verb.tag_ == "VBD":
        # Only "be" has two past forms. "If he were" is correct, so a singular
        # subject with "were" passes.
        wrong = text == "was" and kind == "plural"
    elif kind == "first":
        wrong = verb.tag_ == "VBZ" or text == "are"
    elif kind == "singular":
        wrong = verb.tag_ == "VBP"
    else:
        wrong = verb.tag_ == "VBZ" or text == "am"
    if not wrong:
        return None
    message = f"'{verb.text}' does not agree with {SUBJECT_NAMES[kind]}."
    tense = "past" if verb.tag_ == "VBD" else "present"
    correct = IRREGULAR.get(lemma, {}).get(tense, {}).get(kind)
    # fix: what the second sentence says.
    if correct:
        fix = "form"
        message += f" The correct form is '{correct}'."
    elif kind == "singular":
        fix = "add-s"
        message += " The verb needs the ending -s."
    else:
        fix = "no-s"
        message += " The verb has no ending -s here."
    return Problem(
        "problem-en-agreement",
        message,
        verb=verb.text,
        subject=kind,
        fix=fix,
        correct=correct or "",
    )


def check_agreement(tokens: list, words: list[dict]) -> None:
    by_token = {token.i: word for token, word in zip(tokens, words)}
    for token in tokens:
        kind = subject_kind(token)
        verb = finite_verb(token) if kind else None
        if verb is None or verb.i not in by_token:
            continue
        problem = agreement_problem(kind, verb)
        if problem and problem not in by_token[verb.i]["problems"]:
            by_token[verb.i]["problems"].append(problem)


def check_repeats(words: list[dict]) -> None:
    base.check_repeats(words, VALID_REPEATS)


def check(tokens: list, words: list[dict]) -> None:
    """tokens: the spaCy tokens of one sentence. words: the word of each
    token, in the same order. Gives each word its "problems" list."""
    for word in words:
        word["problems"] = []
    check_spelling(tokens, words)
    check_repeats(words)
    check_agreement(tokens, words)
