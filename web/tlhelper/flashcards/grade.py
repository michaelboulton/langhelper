"""Grade a typed answer against the accepted answers of a card.

The ratings are those of Anki and FSRS: 1 Again, 2 Hard, 3 Good, 4 Easy. The
automatic grade never gives Easy: only the user knows that a card was easy.
"""

import difflib
import unicodedata

from ..languages.base import Grading

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
# The rules of a language with no rules of its own. A slip is one wrong
# letter: a wrong ending is two ("s prijatelj" for "s prijateljem"), and the
# endings are what the user learns.
DEFAULT = Grading()


def normalize(text: str, rules: Grading = DEFAULT) -> str:
    """Case, punctuation and the amount of space never count."""
    # lower() and not casefold(), which makes "ss" from "ß".
    text = unicodedata.normalize("NFC", text).lower()
    if rules.marks == "ignore":
        text = no_marks(text)
    # In a script with no spaces, a comma must not become a space.
    gap = " " if rules.spaces else ""
    kept = (
        gap if unicodedata.category(char)[0] in "PZ" else char
        for char in text
        if unicodedata.category(char)[0] != "C" and char not in rules.ignored
    )
    return " ".join("".join(kept).split())


def no_marks(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )


def folds(text: str, rules: Grading = DEFAULT) -> set[str]:
    """The ways to write a normalized text with no diacritics."""
    results = {text}
    for letter, plain in rules.plain_letters:
        results = {r.replace(letter, p) for r in results for p in plain}
    if rules.marks == "keep":
        return results
    return {no_marks(r) for r in results}


def grade(typed: str, answers: list[str], rules: Grading = DEFAULT) -> dict:
    """{"rating", "answer": the closest accepted answer, "diff"}. The diff is
    a list of [op, text] over the answer as typed and that answer, where op is
    "equal", "delete" (typed, and wrong) or "insert" (missing). The rules are
    those of the language of the answers."""
    want = normalize(typed, rules)
    best, best_ratio = answers[0], -1.0
    for answer in answers:
        # No autojunk: in a long answer it ignores the most frequent letters.
        ratio = difflib.SequenceMatcher(
            None, want, normalize(answer, rules), autojunk=False
        ).ratio()
        if ratio > best_ratio:
            best, best_ratio = answer, ratio
    folded = [
        a for a in answers if folds(want, rules) & folds(normalize(a, rules), rules)
    ]
    if best_ratio == 1.0:
        rating = GOOD
    elif folded:
        rating, best = HARD, folded[0]
    elif wrong_letters(want, normalize(best, rules)) <= rules.slip_letters:
        rating = HARD
    else:
        rating = AGAIN
    return {"rating": rating, "answer": best, "diff": diff(typed.strip(), best, rules)}


def wrong_letters(typed: str, answer: str) -> int:
    opcodes = difflib.SequenceMatcher(None, typed, answer, autojunk=False).get_opcodes()
    return sum(max(a1 - a0, b1 - b0) for op, a0, a1, b0, b1 in opcodes if op != "equal")


def counts(text: str, rules: Grading = DEFAULT) -> bool:
    """Has a character that normalize() keeps."""
    return bool(normalize(text, rules))


def no_end_signs(text: str) -> str:
    """The text with no punctuation and no space at its end."""
    while text and unicodedata.category(text[-1])[0] in "PZ":
        text = text[:-1]
    return text


def diff(typed: str, answer: str, rules: Grading = DEFAULT) -> list[list[str]]:
    # Case-blind, like the grade, but the result keeps the letters as they are.
    # lower() and not casefold(): the indexes must fit the original text, and
    # casefold() makes "ss" from "ß".
    low_typed, low_answer = typed.lower(), answer.lower()
    if (len(low_typed), len(low_answer)) != (len(typed), len(answer)):
        low_typed, low_answer = typed, answer
    matcher = difflib.SequenceMatcher(None, low_typed, low_answer)
    parts = []
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        # Punctuation never counts in the grade, so it is not an error here:
        # a missing full stop shows as plain text of the answer. The same for
        # the marks of a language that ignores them.
        wrong, missing = typed[a0:a1], answer[b0:b1]
        if op == "equal" or not (counts(wrong, rules) or counts(missing, rules)):
            if parts and parts[-1][0] == "equal":
                parts[-1][1] += answer[b0:b1]
            elif b1 > b0:
                parts.append(["equal", answer[b0:b1]])
            continue
        # The same for the punctuation at the end of a wrong part: "a." for "e".
        wrong = no_end_signs(typed[a0:a1])
        missing = no_end_signs(answer[b0:b1])
        if wrong:
            parts.append(["delete", wrong])
        if missing:
            parts.append(["insert", missing])
        if len(missing) < b1 - b0:
            parts.append(["equal", answer[b0 + len(missing) : b1]])
    return parts
