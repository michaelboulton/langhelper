"""Fill the template of a question with the values of one request."""

from string import Formatter

from .base import Question

# Each name that a template can use.
VARIABLES = frozenset(
    {
        # The name of the study language, and of the language of the sentence.
        "language",
        "sentence_language",
        # The name of the language that the learner reads: the language of
        # the page, and of the answer.
        "learner_language",
        # The text of a question about a sentence.
        "sentence",
        # What the flashcard showed, what the user entered, and the answers.
        "flashcard_input",
        "user_input",
        "correct_answer",
        "accepted_answers",
        # The name of the grade: "Again", "Hard", "Good", or "Easy".
        "grade",
        # The lemma and the grammar of each word, from notes().
        "tagger_notes",
        # What the user added to the question.
        "user_context",
    }
)


def names(line: str) -> list[str]:
    """The variables of a part of a template."""
    return [name for _, name, _, _ in Formatter().parse(line) if name]


def build(question: Question, values: dict[str, str]) -> str:
    """The prompt. A value is the data of a deck or of a user: str.format does
    not expand a value again, so braces in it do nothing."""
    missing = set(question.variables) - set(values)
    if missing:
        raise KeyError(f"{question.id} needs: {', '.join(sorted(missing))}")
    lines = []
    for line in question.template.splitlines():
        used = names(line)
        # One line for each value, so a line break in a value adds no line.
        clean = {name: " ".join(values[name].split()) for name in used}
        if used and not any(clean.values()):
            continue
        lines.append(line.format(**clean))
    return "\n".join(lines)


def relation(word: dict, texts: dict[int, str]) -> str:
    """'object of Pijem'. Empty for a tagger with no parser."""
    label = word.get("deprel", "")
    if not label:
        return ""
    if label.lower() == "root" or not word.get("head"):
        return "root of the sentence"
    # The glossary of spaCy has the labels of each of its models, and those of
    # Universal Dependencies: "oa" is "accusative object".
    import spacy

    return f"{spacy.explain(label) or label} of {texts.get(word['head'], '?')}"


def notes(sentences: list[dict]) -> str:
    """The words of a breakdown, as facts for the model: the lemma, the part
    of speech, the features with their names, and the relation to the head.
    "kavu (kava: NOUN Case=Acc Number=Sing; object of Pijem)"."""
    words = []
    for sentence in sentences:
        texts = {word["id"]: word["text"] for word in sentence["words"]}
        for word in sentence["words"]:
            if word["upos"] == "PUNCT":
                continue
            feats = [f"{name}={value}" for name, value in word.get("feats", {}).items()]
            facts = " ".join([word["upos"], *feats])
            role = relation(word, texts)
            if role:
                facts = f"{facts}; {role}"
            words.append(f"{word['text']} ({word['lemma']}: {facts})")
    return ", ".join(words)
