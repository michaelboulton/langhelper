"""The flashcard API, with the real light models (they are dependencies)."""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from tlhelper import app as service
from tlhelper.flashcards import decks, routes, store

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
reverse = true
"""


@pytest.fixture
def client(deck_dir, make_apkg, clock):
    make_apkg(
        deck_dir / "basics.apkg", [("guid-coffee", "I drink coffee.", "Pijem kavu.")]
    )
    (deck_dir / "basics.toml").write_text(TOML)
    decks.import_decks()
    # No `with`: the lifespan (and so the model warm-up) does not run.
    return TestClient(service.app)


def texts(sentences):
    return [word["text"] for sentence in sentences for word in sentence["words"]]


def test_the_flow_of_a_card(client, clock):
    [deck] = client.get("/api/v1/decks").json()["decks"]
    assert deck["counts"] == {"total": 2, "new": 2, "learning": 0, "due": 0}

    card = client.get(f"/api/v1/decks/{deck['id']}/next").json()
    assert (card["direction"], card["prompt"]) == ("to_study", "I drink coffee.")
    assert texts(card["prompt_sentences"]) == ["I", "drink", "coffee", "."]
    assert "answers" not in card

    result = client.post(
        f"/api/v1/cards/{card['card_id']}/answer",
        json={"typed": "Pijem kava", "elapsed_ms": 4000},
    ).json()
    assert result["rating"] == 2
    assert result["answers"] == ["Pijem kavu."]
    assert ["delete", "a"] in result["diff"]
    assert texts(result["typed"]["sentences"]) == ["Pijem", "kava"]
    assert texts(result["correct"]["sentences"]) == ["Pijem", "kavu", "."]
    # [Croatian word, English word]: kavu and coffee.
    assert [1, 2] in result["correct"]["links"]
    # Only the text of the user gets the grammar checks.
    assert "problems" in result["typed"]["sentences"][0]["words"][0]
    assert "problems" not in result["correct"]["sentences"][0]["words"][0]

    changed = client.post(
        f"/api/v1/reviews/{result['review_id']}/rating", json={"rating": 4}
    )
    assert changed.json()["rating"] == 4
    assert changed.json()["next_due"] > result["next_due"]

    stats = client.get("/api/v1/flashcards/stats", params={"deck": deck["id"]}).json()
    assert (stats["reviews"], stats["success_rate"], stats["streak_days"]) == (
        1,
        1.0,
        1,
    )
    assert store.stats(routes.LOCAL_USER)["reviews"] == 1
    # The other direction of the note waits for tomorrow.
    assert client.get(f"/api/v1/decks/{deck['id']}/next").json()["done"]


def test_a_card_that_asks_for_the_english(client, clock):
    [deck] = client.get("/api/v1/decks").json()["decks"]
    first = client.get(f"/api/v1/decks/{deck['id']}/next").json()
    review = client.post(
        f"/api/v1/cards/{first['card_id']}/answer", json={"typed": "Pijem kavu"}
    ).json()
    # Easy: the card leaves the learning steps, so it is not due tomorrow.
    client.post(f"/api/v1/reviews/{review['review_id']}/rating", json={"rating": 4})
    clock.add(days=1)
    card = client.get(f"/api/v1/decks/{deck['id']}/next").json()
    assert (card["direction"], card["prompt"]) == ("to_english", "Pijem kavu.")
    assert card["prompt_sentences"][0]["words"][1]["lemma"] == "kava"
    result = client.post(
        f"/api/v1/cards/{card['card_id']}/answer", json={"typed": "i drink coffee"}
    ).json()
    assert result["rating"] == 3
    # Still [Croatian word, English word].
    assert [1, 2] in result["typed"]["links"]


def test_a_card_with_a_picture_and_a_clip(deck_dir, make_apkg, clock):
    notes = [("guid-house", '<img src="my house.jpg">', "kuća[sound:kuća.mp3]")]
    media = {"my house.jpg": b"a picture", "kuća.mp3": b"a clip", "spare.jpg": b"x"}
    make_apkg(deck_dir / "pictures.apkg", notes, new_format=True, media=media)
    (deck_dir / "pictures.toml").write_text(TOML)
    decks.import_decks()
    client = TestClient(service.app)
    [deck] = client.get("/api/v1/decks").json()["decks"]

    card = client.get(f"/api/v1/decks/{deck['id']}/next").json()
    assert (card["prompt"], card["prompt_sentences"]) == ("", [])
    # The clip of the answer is not there yet.
    [picture] = card["media"]
    assert picture == {
        "kind": "image",
        "url": f"/api/v1/decks/{deck['id']}/media/my%20house.jpg",
    }
    response = client.get(picture["url"])
    assert response.content == b"a picture"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"

    result = client.post(
        f"/api/v1/cards/{card['card_id']}/answer", json={"typed": "kuća"}
    ).json()
    assert result["rating"] == 3
    [clip] = result["media"]
    assert clip["kind"] == "audio"
    assert client.get(clip["url"]).content == b"a clip"

    # In the package, but of no card. And a file of another deck.
    assert client.get(f"/api/v1/decks/{deck['id']}/media/spare.jpg").status_code == 404
    assert client.get("/api/v1/decks/99/media/my%20house.jpg").status_code == 404
    # The package left the folder.
    (deck_dir / "pictures.apkg").unlink()
    assert client.get(picture["url"]).status_code == 404


def test_an_empty_answer_is_again(client):
    result = client.post("/api/v1/cards/1/answer", json={"typed": ""}).json()
    assert result["rating"] == 1
    assert result["typed"] == {"sentences": [], "links": [], "guesses": []}


def test_errors(client):
    assert client.get("/api/v1/decks/99/next").status_code == 404
    assert (
        client.post("/api/v1/cards/99/answer", json={"typed": "x"}).status_code == 404
    )
    assert (
        client.post("/api/v1/reviews/99/rating", json={"rating": 3}).status_code == 404
    )
    assert (
        client.post("/api/v1/reviews/1/rating", json={"rating": 5}).status_code == 422
    )


@pytest.fixture
def admin():
    service.app.dependency_overrides[routes.is_admin] = lambda: True
    yield
    service.app.dependency_overrides.pop(routes.is_admin)


def answer_as(user, rating):
    card = store.next_card(user, 1)["card"]
    store.answer(user, card["id"], rating, "", None)


def test_a_user_sees_only_the_own_numbers(client):
    answer_as("user-2", 3)
    assert client.get("/api/v1/flashcards/users").json() == {
        "me": "local",
        "admin": False,
        "users": [{"id": "local", "name": "My cards"}],
    }
    response = client.get("/api/v1/flashcards/stats", params={"of": "user-2"})
    assert response.status_code == 403
    assert "Only an admin" in response.json()["detail"]
    own = client.get("/api/v1/flashcards/stats", params={"of": "local"})
    assert own.json()["reviews"] == 0


def test_an_admin_sees_the_numbers_of_each_user(client, admin):
    answer_as("user-2", 3)
    answer_as("local", 1)
    store.save_user("user-2", "Ana")
    users = client.get("/api/v1/flashcards/users").json()
    assert users["admin"]
    assert users["users"] == [
        {"id": "local", "name": "My cards"},
        {"id": "user-2", "name": "Ana"},
    ]
    other = client.get("/api/v1/flashcards/stats", params={"of": "user-2"}).json()
    assert (other["reviews"], other["success_rate"]) == (1, 1.0)
    assert client.get("/api/v1/flashcards/stats").json()["success_rate"] == 0.0


def test_the_admin_is_the_group_of_the_login():
    def admin_of(scope):
        return routes.is_admin(Request({"type": "http", **scope}))

    assert admin_of({"session": {"user": {"sub": "user-1", "group": "admin"}}})
    assert not admin_of({"session": {"user": {"sub": "user-1", "group": "family"}}})
    # A session from before the group was there.
    assert not admin_of({"session": {"user": {"sub": "user-1"}}})
    assert not admin_of({})


def test_the_user_is_the_sub_of_the_login():
    session = {"user": {"sub": "user-1", "name": "michael"}}
    assert (
        routes.current_user(Request({"type": "http", "session": session})) == "user-1"
    )
    assert routes.current_user(Request({"type": "http", "session": {}})) == "local"
    assert routes.current_user(Request({"type": "http"})) == "local"
