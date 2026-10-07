import pytest
from tlhelper.flashcards import decks, store
from tlhelper.flashcards.grade import AGAIN, EASY, GOOD

TOML = """
name = "Basics"
language = "hr"
english_field = "Front"
answer_field = "Back"
"""


def prompt(user, deck):
    result = store.next_card(user, deck)
    return None if result.get("done") else result["card"]["prompt"]


def answer_next(user, deck, rating=GOOD):
    card = store.next_card(user, deck)["card"]
    return store.answer(user, card["id"], rating, "typed", 1500)


def test_new_cards_come_in_deck_order_then_the_learning_steps(basics, clock):
    assert prompt("me", basics) == "house"
    answer_next("me", basics)
    # After Good, "house" is in its second learning step: 10 minutes.
    assert prompt("me", basics) == "hello / hi"
    clock.add(minutes=11)
    assert prompt("me", basics) == "house"


def test_done_gives_the_next_due_time(basics, clock):
    for _ in range(3):
        answer_next("me", basics)
    result = store.next_card("me", basics)
    assert result["done"]
    assert result["next_due"] == "2026-09-20T09:10:00+00:00"
    assert result["counts"] == {"total": 3, "new": 0, "learning": 3, "due": 0}


def test_the_limit_of_new_cards_a_day(deck_dir, make_apkg, clock):
    make_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML + "new_per_day = 2\n")
    decks.import_decks()
    [deck] = store.decks("me")
    for _ in range(2):
        answer_next("me", deck["id"], EASY)
    result = store.next_card("me", deck["id"])
    # Easy ends the learning steps, so nothing is due before the next day.
    assert (result["done"], result["next_due"]) == (True, "2026-09-21T00:00:00+00:00")
    clock.add(days=1)
    assert prompt("me", deck["id"]) == "I drink coffee."


def test_the_limit_of_reviews_a_day(deck_dir, make_apkg, clock):
    make_apkg(deck_dir / "basics.apkg")
    (deck_dir / "basics.toml").write_text(TOML + "reviews_per_day = 1\n")
    decks.import_decks()
    [deck] = store.decks("me")
    for _ in range(3):
        answer_next("me", deck["id"], EASY)
    clock.add(days=60)
    assert store.decks("me")[0]["counts"]["due"] == 3
    answer_next("me", deck["id"], EASY)
    assert store.next_card("me", deck["id"])["done"]


def test_the_other_direction_waits_for_the_next_day(deck_dir, make_apkg, clock):
    make_apkg(deck_dir / "basics.apkg", [("guid-house", "house", "kuća")])
    (deck_dir / "basics.toml").write_text(TOML + "reverse = true\n")
    decks.import_decks()
    [deck] = store.decks("me")
    assert prompt("me", deck["id"]) == "house"
    answer_next("me", deck["id"], EASY)
    assert store.next_card("me", deck["id"])["done"]
    clock.add(days=1)
    assert prompt("me", deck["id"]) == "kuća"


def test_a_changed_rating_starts_from_the_card_before(basics, clock):
    review_id, due_good = answer_next("me", basics, GOOD)
    assert due_good == "2026-09-20T09:10:00+00:00"
    clock.add(seconds=30)
    assert store.change_rating("me", review_id, AGAIN) == "2026-09-20T09:01:00+00:00"
    # Not from the result of Good: the same as Again on a new card.
    assert store.change_rating("me", review_id, GOOD) == due_good
    assert store.stats("me")["reviews"] == 1


def test_only_the_last_review_of_the_own_cards_can_change(basics, clock):
    first, _ = answer_next("me", basics)
    with pytest.raises(store.NotFound):
        store.change_rating("you", first, AGAIN)
    clock.add(minutes=11)
    second, _ = answer_next("me", basics)  # "house" again
    with pytest.raises(store.NotFound):
        store.change_rating("me", first, AGAIN)
    store.change_rating("me", second, AGAIN)


def test_each_user_has_their_own_progress(basics, clock):
    answer_next("me", basics)
    assert prompt("me", basics) == "hello / hi"
    assert prompt("you", basics) == "house"
    assert store.stats("you")["reviews"] == 0


def test_the_users_and_their_names(basics, clock):
    answer_next("sub-2", basics)
    answer_next("sub-1", basics)
    store.save_user("sub-1", "Zoe")
    store.save_user("sub-3", "ana")
    # By name, and a user with no login yet has the sub as the name.
    assert store.users() == [
        {"id": "sub-3", "name": "ana"},
        {"id": "sub-2", "name": "sub-2"},
        {"id": "sub-1", "name": "Zoe"},
    ]
    store.save_user("sub-1", "Ben")
    assert store.users()[1] == {"id": "sub-1", "name": "Ben"}


def test_unknown_ids(basics):
    with pytest.raises(store.NotFound):
        store.next_card("me", basics + 1)
    with pytest.raises(store.NotFound):
        store.get_card(999)


def test_stats(basics, clock):
    answer_next("me", basics, GOOD)
    clock.add(days=1)
    answer_next("me", basics, AGAIN)
    answer_next("me", basics, GOOD)
    stats = store.stats("me", basics)
    assert stats["reviews"] == 3
    assert stats["success_rate"] == pytest.approx(2 / 3)
    assert stats["streak_days"] == 2
    assert len(stats["days"]) == 90
    assert stats["days"][-2:] == [
        {"date": "2026-09-20", "reviews": 1, "passed": 1},
        {"date": "2026-09-21", "reviews": 2, "passed": 1},
    ]
    # The next day with no review yet: the streak still holds.
    clock.add(days=1)
    assert store.stats("me")["streak_days"] == 2
    clock.add(days=1)
    assert store.stats("me")["streak_days"] == 0
    assert store.stats("me", basics + 1)["counts"] == {}
