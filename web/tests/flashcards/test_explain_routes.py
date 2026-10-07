"""The routes of the "explain with AI" buttons, with a fake backend and the
real light models."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from tlhelper import app as service
from tlhelper import explain
from tlhelper.explain import routes as explain_routes
from tlhelper.flashcards import decks, routes

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""


class Loaded:
    """A language that records the model types that analyze() gets."""

    info = SimpleNamespace(variants=("light", "heavy"))

    def __init__(self, loaded):
        self.loaded, self.asked = loaded, []

    def status(self):
        return {"loading": None, "loaded": self.loaded}

    def analyze(self, text, *, variant, check):
        self.asked.append(variant)
        return []


@pytest.mark.parametrize(
    "loaded, variant", [(["heavy"], "heavy"), (["light"], "light"), ([], "light")]
)
def test_a_question_loads_no_other_model(loaded, variant):
    language = Loaded(loaded)
    explain_routes.tagged(language, "Pijem kavu")
    # One call, and with the model that is in memory.
    assert language.asked == [variant]


@pytest.fixture
def client(deck_dir, make_apkg, clock):
    make_apkg(
        deck_dir / "basics.apkg", [("guid-coffee", "I drink coffee.", "Pijem kavu.")]
    )
    (deck_dir / "basics.toml").write_text(TOML)
    decks.import_decks()
    return TestClient(service.app)


@pytest.fixture
def review_id(client):
    [deck] = client.get("/api/v1/decks").json()["decks"]
    card = client.get(f"/api/v1/decks/{deck['id']}/next").json()
    result = client.post(
        f"/api/v1/cards/{card['card_id']}/answer", json={"typed": "Pijem kava"}
    )
    return result.json()["review_id"]


def test_the_questions(client, backend):
    data = client.get("/api/v1/explain/questions").json()
    assert (data["available"], data["model"]) == (True, "fake-model")
    assert {"id": "why_wrong", "label": "Why is my answer wrong?", "where": "card"} in (
        data["questions"]
    )
    backend.key = False
    assert client.get("/api/v1/explain/questions").json()["available"] is False


def test_a_question_about_an_answer(client, backend, review_id):
    body = {"question": "why_wrong", "user_context": "why not kava?"}
    response = client.post(f"/api/v1/reviews/{review_id}/explain", json=body)
    assert response.json() == {
        "text": "Answer 1.",
        "model": "fake-model",
        "cached": False,
    }
    [prompt] = backend.prompts
    # The server read these from the review and the card, not from the page.
    assert "The learner studies Croatian" in prompt
    assert "The flashcard showed: I drink coffee." in prompt
    assert "The learner entered: Pijem kava" in prompt
    assert "The correct answer: Pijem kavu." in prompt
    assert 'graded the answer "Hard"' in prompt
    assert "kavu (kava: NOUN" in prompt
    assert prompt.endswith("More context from the learner: why not kava?")

    # The same request again: from the cache, with no request to the service.
    again = client.post(f"/api/v1/reviews/{review_id}/explain", json=body).json()
    assert (again["text"], again["cached"]) == ("Answer 1.", True)
    assert len(backend.prompts) == 1


def test_a_question_about_the_sentence_of_a_card(client, backend, review_id):
    body = {"question": "meaning"}
    assert (
        client.post(f"/api/v1/reviews/{review_id}/explain", json=body).status_code
        == 200
    )
    # The side in the study language, and nothing of the answer of the user.
    assert "The sentence (Croatian): Pijem kavu." in backend.prompts[0]
    assert "kava" not in backend.prompts[0].replace("(kava:", "")


def test_the_review_of_another_user(client, backend, review_id):
    service.app.dependency_overrides[routes.current_user] = lambda: "user-2"
    try:
        response = client.post(
            f"/api/v1/reviews/{review_id}/explain", json={"question": "why_wrong"}
        )
    finally:
        service.app.dependency_overrides.pop(routes.current_user)
    assert response.status_code == 404
    assert backend.prompts == []


def test_a_question_about_a_text(client, backend):
    body = {"text": "Idemo na kavu.", "language": "hr", "question": "register"}
    assert client.post("/api/v1/explain", json=body).json()["text"] == "Answer 1."
    assert "The sentence (Croatian): Idemo na kavu." in backend.prompts[0]
    assert "colloquial" in backend.prompts[0]


def test_the_answer_is_in_the_language_of_the_page(client, backend):
    body = {"text": "Idemo na kavu.", "language": "hr", "question": "meaning"}
    assert client.post("/api/v1/explain", json=body).json()["cached"] is False
    assert "knows English." in backend.prompts[0]
    backend.system = explain.system("German")
    assert "Answer in German" in backend.system
    german = client.post("/api/v1/explain", json=body | {"locale": "de"}).json()
    # The cache has one answer for each language.
    assert german == {"text": "Answer 2.", "model": "fake-model", "cached": False}
    assert "The learner studies Croatian and knows German." in backend.prompts[1]
    assert client.post("/api/v1/explain", json=body | {"locale": "de"}).json()["cached"]
    assert (
        client.post("/api/v1/explain", json=body | {"locale": "xx"}).status_code == 422
    )


def test_the_bad_requests(client, backend):
    text = {"text": "Idemo.", "language": "hr"}
    bad = [
        # A question about a card needs a review.
        text | {"question": "why_wrong"},
        text | {"question": "no such question"},
        text | {"question": "meaning", "language": "xx"},
        text | {"question": "meaning", "user_context": "a" * 301},
        # No text.
        {"question": "meaning", "language": "hr", "text": ""},
    ]
    for body in bad:
        assert client.post("/api/v1/explain", json=body).status_code == 422
    assert backend.prompts == []


def test_no_key_and_an_error_of_the_service(client, backend):
    body = {"text": "Idemo.", "language": "hr", "question": "meaning"}
    backend.error = "the AI service has too many requests, or no credit"
    response = client.post("/api/v1/explain", json=body)
    assert response.status_code == 502
    # The English text, and the message of the catalogs for it.
    assert response.json() == {"detail": backend.error, "code": "ai-busy", "params": {}}
    # A failure is not in the cache.
    backend.error = None
    assert client.post("/api/v1/explain", json=body).json()["cached"] is False
    backend.key = False
    other = body | {"question": "grammar"}
    assert client.post("/api/v1/explain", json=other).status_code == 503


def test_the_limit_of_a_day(client, backend, clock, monkeypatch):
    monkeypatch.setattr(explain, "PER_DAY", 2)
    body = {"language": "hr", "question": "meaning"}
    for text in ("Idemo.", "Pijem."):
        assert (
            client.post("/api/v1/explain", json=body | {"text": text}).status_code
            == 200
        )
    third = client.post("/api/v1/explain", json=body | {"text": "Spavam."})
    assert third.status_code == 429
    assert (third.json()["code"], third.json()["params"]) == ("ai-limit", {"limit": 2})
    # The cache does not count.
    assert (
        client.post("/api/v1/explain", json=body | {"text": "Idemo."}).status_code
        == 200
    )
    # Another user has another limit, and so has the next day.
    service.app.dependency_overrides[routes.current_user] = lambda: "user-2"
    try:
        other = client.post("/api/v1/explain", json=body | {"text": "Spavam."})
    finally:
        service.app.dependency_overrides.pop(routes.current_user)
    assert other.status_code == 200
    clock.add(days=1)
    assert (
        client.post("/api/v1/explain", json=body | {"text": "Radim."}).status_code
        == 200
    )
