"""Tests for the basic checks of an English text. They use the real spaCy
model, because the checks read its tags and its parse."""

import pytest
from tlhelper.languages import ENGLISH

CORRECT = [
    "I am not happy.",
    "My hovercraft is full of eels.",
    "He goes to the shop, and they go home.",
    "She has gone home.",
    "We were there when it happened.",
    "A lot of people are here.",
    "The police are outside.",
    "Tom and Ana are here.",
    "If he were here, I would go.",
    "He can go, and she must stay.",
    "Does he like it? I don't know, but he can't say.",
    "She said that that was wrong, because she had had enough.",
    "You are late, and I was early.",
    "I wanna go home, and I'm gonna sleep.",
    "The boats that we saw are full.",
    "To view this page correctly, you must have the program installed.",
]


def flagged(text):
    return {
        word["text"]: word["problems"]
        for sentence in ENGLISH.analyze(text, check=True)
        for word in sentence["words"]
        if word["problems"]
    }


@pytest.mark.parametrize("text", CORRECT)
def test_a_correct_sentence_is_clean(text):
    assert flagged(text) == {}


@pytest.mark.parametrize(
    "text, verb, correct",
    [
        ("i is not happy", "is", "'am'"),
        ("You is late.", "is", "'are'"),
        ("They was at home.", "was", "'were'"),
        ("She have gone home.", "have", "'has'"),
        ("he don't like it", "do", "'does'"),
        ("The boats is full.", "is", "'are'"),
        ("Tom and Ana is here.", "is", "'are'"),
        ("He go to the shop.", "go", "needs the ending -s"),
        ("We were there and they goes home.", "goes", "no ending -s"),
    ],
)
def test_a_verb_that_does_not_agree(text, verb, correct):
    problems = flagged(text)
    assert list(problems) == [verb]
    [problem] = problems[verb]
    assert "does not agree" in problem and correct in problem


def test_spelling_with_a_suggestion():
    problems = flagged("I recieve the mesage tomorow in Zagreb.")
    assert list(problems) == ["recieve", "mesage", "tomorow"]
    assert problems["recieve"] == [
        "The English word list does not have this word. Did you mean 'receive'?"
    ]
    # A long word gets no suggestion, because the search is slow.
    [problem] = flagged("The plan is unquestionablyy wrong.")["unquestionablyy"]
    assert problem == "The English word list does not have this word."


def test_repeats():
    problems = flagged("My boat is is full of of the the eels.")
    assert problems == {
        "is": ["'is' repeats."],
        "of": ["'of' repeats."],
        "the": ["'the' repeats."],
    }
    assert flagged("I went to I went to the shop.") == {
        "I": ["'I went to' repeats."],
        "went": ["'I went to' repeats."],
        "to": ["'I went to' repeats."],
    }
