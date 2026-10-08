"""The flashcard database: the decks, and for each user which cards they saw
and when each card is due again.

Like Anki, there is the state of a card now (user_card, Anki: cards) and a log
of every answer that only grows (review, Anki: revlog). The scheduler is FSRS,
the default of Anki: https://github.com/open-spaced-repetition/py-fsrs

All times are seconds since the epoch, in UTC. A day starts at 00:00 UTC.
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime

from fsrs import Card, Rating, Scheduler, State

from ..settings import DATA_ROOT

DB_PATH = DATA_ROOT / "flashcards.db"
DAY = 86400
STATS_DAYS = 90

TO_STUDY, TO_ENGLISH = "to_study", "to_english"

SCHEMA = """
CREATE TABLE IF NOT EXISTS deck (
    id INTEGER PRIMARY KEY,
    -- The file name without its suffix. For a subdeck of a package, the
    -- parts of its Anki name follow: "sentences::Read Training::2".
    stem TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    new_per_day INTEGER NOT NULL,
    reviews_per_day INTEGER NOT NULL,
    -- Size and mtime of the two files: the import only runs after a change.
    source_stamp TEXT NOT NULL,
    -- JSON list for the tree on the page: the name of the package, then the
    -- parts of the Anki name. Empty for a deck that is the whole package.
    path TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS card (
    id INTEGER PRIMARY KEY,
    deck_id INTEGER NOT NULL REFERENCES deck(id),
    -- Of the Anki note. The same in each export, so the progress survives.
    guid TEXT NOT NULL,
    direction TEXT NOT NULL,
    position INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    -- JSON list of the accepted answers.
    answers TEXT NOT NULL,
    -- The note left the deck. The row stays for the review log.
    removed INTEGER NOT NULL DEFAULT 0,
    -- JSON lists of the media file names (images, sound clips) of the package.
    -- The page gets answer_media only after the user answered.
    prompt_media TEXT NOT NULL DEFAULT '[]',
    answer_media TEXT NOT NULL DEFAULT '[]',
    UNIQUE (deck_id, guid, direction)
);
-- TODO: a first-letter hint, "skip", "suspend this card", and the automatic
-- suspend of a leech (Anki: a card with 8 lapses). These need a `suspended`
-- column here, and next_card() must leave such a card out.
CREATE TABLE IF NOT EXISTS user_card (
    user_id TEXT NOT NULL,
    card_id INTEGER NOT NULL REFERENCES card(id),
    -- Copies of the values in fsrs, for the queries. state: fsrs.State.
    state INTEGER NOT NULL,
    due REAL NOT NULL,
    -- fsrs.Card.to_dict()
    fsrs TEXT NOT NULL,
    first_seen REAL NOT NULL,
    PRIMARY KEY (user_id, card_id)
);
CREATE INDEX IF NOT EXISTS user_card_due ON user_card (user_id, due);
CREATE TABLE IF NOT EXISTS review (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    card_id INTEGER NOT NULL REFERENCES card(id),
    reviewed_at REAL NOT NULL,
    -- 1 Again, 2 Hard, 3 Good, 4 Easy. rating is what counts, and differs
    -- from auto_rating after the user changed the grade.
    rating INTEGER NOT NULL,
    auto_rating INTEGER NOT NULL,
    typed TEXT NOT NULL,
    elapsed_ms INTEGER,
    -- The fsrs card before this review, or NULL for a new card.
    before TEXT
);
CREATE INDEX IF NOT EXISTS review_user ON review (user_id, reviewed_at);
-- The name of each login, for the user list of an admin. The other tables
-- hold only the sub, because the name can change.
CREATE TABLE IF NOT EXISTS user (
    sub TEXT PRIMARY KEY,
    name TEXT,
    seen_at REAL NOT NULL
);
-- The answers of the AI (tlhelper/explain). key is a hash of the model and of
-- the full prompt, so the same question costs nothing the second time. A row
-- is one request to the service: the rows of a day are the limit of a user.
CREATE TABLE IF NOT EXISTS explanation (
    key TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    model TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS explanation_user ON explanation (user_id, created_at);
"""

SCHEDULER = Scheduler()
_lock = threading.Lock()


class NotFound(Exception):
    pass


def now() -> datetime:
    return datetime.now(UTC)


def day_start(when: datetime) -> float:
    return when.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    # A database from before the media columns.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(card)")}
    for column in ("prompt_media", "answer_media"):
        if column not in columns:
            conn.execute(
                f"ALTER TABLE card ADD COLUMN {column} TEXT NOT NULL DEFAULT '[]'"
            )
    # A database from before the subdecks.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(deck)")}
    if "path" not in columns:
        conn.execute("ALTER TABLE deck ADD COLUMN path TEXT NOT NULL DEFAULT '[]'")
    return conn


# The import (decks.py)


def deck_stamps() -> dict[str, str]:
    with _lock, db() as conn:
        return {
            r["stem"]: r["source_stamp"] for r in conn.execute("SELECT * FROM deck")
        }


def save_deck(config: dict, stamp: str, cards: list[dict]) -> None:
    """config: stem, name, language, new_per_day, reviews_per_day, and path for
    a subdeck. cards: guid, direction, prompt, answers, in the order of the
    deck. A card that is not in the list any more becomes `removed`."""
    path = json.dumps(config.get("path", []), ensure_ascii=False)
    with _lock, db() as conn:
        conn.execute(
            "INSERT INTO deck (stem, name, language, new_per_day, reviews_per_day,"
            " source_stamp, path) VALUES (:stem, :name, :language, :new_per_day,"
            " :reviews_per_day, :stamp, :path) ON CONFLICT (stem) DO UPDATE SET"
            " name = excluded.name, language = excluded.language,"
            " new_per_day = excluded.new_per_day,"
            " reviews_per_day = excluded.reviews_per_day,"
            " source_stamp = excluded.source_stamp, path = excluded.path",
            config | {"stamp": stamp, "path": path},
        )
        [[deck_id]] = conn.execute(
            "SELECT id FROM deck WHERE stem = ?", (config["stem"],)
        )
        conn.execute("UPDATE card SET removed = 1 WHERE deck_id = ?", (deck_id,))
        conn.executemany(
            "INSERT INTO card (deck_id, guid, direction, position, prompt, answers,"
            " prompt_media, answer_media) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (deck_id, guid, direction)"
            " DO UPDATE SET position = excluded.position, prompt = excluded.prompt,"
            " answers = excluded.answers, prompt_media = excluded.prompt_media,"
            " answer_media = excluded.answer_media, removed = 0",
            [
                (
                    deck_id,
                    card["guid"],
                    card["direction"],
                    position,
                    card["prompt"],
                    json.dumps(card["answers"], ensure_ascii=False),
                    json.dumps(card.get("prompt_media", []), ensure_ascii=False),
                    json.dumps(card.get("answer_media", []), ensure_ascii=False),
                )
                for position, card in enumerate(cards)
            ],
        )


def of_package(package: str) -> tuple[str, str]:
    """The arguments for "stem = ? OR substr(stem, 1, ?) = ?"."""
    return package, package + "::"


def retire_decks(package: str, keep: list[str]) -> None:
    """Remove the cards of each deck of the package that the new import does
    not have. The rows stay for the review log."""
    stem, prefix = of_package(package)
    with _lock, db() as conn:
        rows = conn.execute(
            "SELECT id, stem FROM deck WHERE stem = ? OR substr(stem, 1, ?) = ?",
            (stem, len(prefix), prefix),
        ).fetchall()
        for row in rows:
            if row["stem"] not in keep:
                conn.execute(
                    "UPDATE card SET removed = 1 WHERE deck_id = ?", (row["id"],)
                )


# The queue


def counts(conn: sqlite3.Connection, user: str, deck_id: int, when: datetime) -> dict:
    row = conn.execute(
        "SELECT COUNT(*) AS total,"
        " COALESCE(SUM(u.card_id IS NULL), 0) AS new,"
        " COALESCE(SUM(u.state IN (:learning, :relearning)), 0) AS learning,"
        " COALESCE(SUM(u.state = :review AND u.due <= :now), 0) AS due"
        " FROM card c LEFT JOIN user_card u ON u.card_id = c.id AND u.user_id = :user"
        " WHERE c.deck_id = :deck AND NOT c.removed",
        {
            "user": user,
            "deck": deck_id,
            "now": when.timestamp(),
            "learning": State.Learning,
            "relearning": State.Relearning,
            "review": State.Review,
        },
    ).fetchone()
    return dict(row)


def decks(user: str) -> list[dict]:
    """In the order of the tree: a subdeck sorts by its path. A deck with no
    card any more (a subdeck that left its package) is not in the list."""
    when = now()
    with _lock, db() as conn:
        found = [
            {
                "id": deck["id"],
                "name": deck["name"],
                "language": deck["language"],
                "path": json.loads(deck["path"]),
                "counts": counts(conn, user, deck["id"], when),
            }
            for deck in conn.execute("SELECT * FROM deck").fetchall()
        ]
    found = [deck for deck in found if deck["counts"]["total"]]
    return sorted(found, key=lambda deck: (deck["path"] or [deck["name"]], deck["id"]))


def card_dict(row: sqlite3.Row) -> dict:
    lists = ("answers", "prompt_media", "answer_media")
    return dict(row) | {key: json.loads(row[key]) for key in lists}


def get_card(card_id: int) -> dict:
    """The card with the language of its deck."""
    with _lock, db() as conn:
        row = conn.execute(
            "SELECT c.*, d.language FROM card c JOIN deck d ON d.id = c.deck_id"
            " WHERE c.id = ? AND NOT c.removed",
            (card_id,),
        ).fetchone()
    if row is None:
        raise NotFound(f"no card {card_id}")
    return card_dict(row)


def media_deck(deck_id: int, name: str) -> str:
    """The stem of the deck, if one of its cards has the media file `name`."""
    with _lock, db() as conn:
        row = conn.execute(
            "SELECT d.stem FROM deck d WHERE d.id = :deck AND EXISTS ("
            " SELECT 1 FROM card c WHERE c.deck_id = d.id AND NOT c.removed AND ("
            " EXISTS (SELECT 1 FROM json_each(c.prompt_media) WHERE value = :name)"
            " OR EXISTS (SELECT 1 FROM json_each(c.answer_media) WHERE value = :name)"
            "))",
            {"deck": deck_id, "name": name},
        ).fetchone()
    if row is None:
        raise NotFound(f"no media file {name!r} in deck {deck_id}")
    return row["stem"]


# Not the other direction of a note that the user answered today (Anki: "bury
# siblings"): its answer is still in their head.
NO_SIBLING_TODAY = (
    " AND NOT EXISTS (SELECT 1 FROM card s JOIN review r ON r.card_id = s.id"
    " WHERE s.deck_id = c.deck_id AND s.guid = c.guid AND s.id != c.id"
    " AND r.user_id = :user AND r.reviewed_at >= :today)"
)


def next_card(user: str, deck_id: int) -> dict:
    """{"card": ..., "counts": ...}, or {"done": True, "next_due": ...} when the
    user is through for now. The order:
    1. a card in the learning steps that is due,
    2. a review card that is due, up to reviews_per_day cards a day,
    3. a new card, up to new_per_day cards a day."""
    when = now()
    args = {
        "user": user,
        "deck": deck_id,
        "now": when.timestamp(),
        "today": day_start(when),
        "review": State.Review,
    }
    select = (
        "SELECT c.*, d.language FROM card c JOIN deck d ON d.id = c.deck_id"
        " LEFT JOIN user_card u ON u.card_id = c.id AND u.user_id = :user"
        " WHERE c.deck_id = :deck AND NOT c.removed"
    )
    with _lock, db() as conn:
        deck = conn.execute("SELECT * FROM deck WHERE id = ?", (deck_id,)).fetchone()
        if deck is None:
            raise NotFound(f"no deck {deck_id}")
        # Cards of this deck that the user answered today: the new ones, and
        # the ones that came back.
        new_today, old_today = conn.execute(
            "SELECT COALESCE(SUM(u.first_seen >= :today), 0),"
            " COALESCE(SUM(u.first_seen < :today), 0) FROM user_card u"
            " JOIN card c ON c.id = u.card_id WHERE u.user_id = :user"
            " AND c.deck_id = :deck AND EXISTS (SELECT 1 FROM review r"
            " WHERE r.card_id = u.card_id AND r.user_id = :user"
            " AND r.reviewed_at >= :today)",
            args,
        ).fetchone()
        row = conn.execute(
            select + " AND u.state != :review AND u.due <= :now ORDER BY u.due", args
        ).fetchone()
        if row is None and old_today < deck["reviews_per_day"]:
            row = conn.execute(
                select
                + " AND u.state = :review AND u.due <= :now"
                + NO_SIBLING_TODAY
                + " ORDER BY u.due",
                args,
            ).fetchone()
        if row is None and new_today < deck["new_per_day"]:
            row = conn.execute(
                select
                + " AND u.card_id IS NULL"
                + NO_SIBLING_TODAY
                + " ORDER BY c.position",
                args,
            ).fetchone()
        totals = counts(conn, user, deck_id, when)
        if row is not None:
            return {"card": card_dict(row), "counts": totals}
        [[next_due]] = conn.execute(
            "SELECT MIN(u.due) FROM user_card u JOIN card c ON c.id = u.card_id"
            " WHERE u.user_id = :user AND c.deck_id = :deck AND NOT c.removed",
            args,
        )
    # Cards wait for tomorrow: a limit, or a sibling of today.
    if totals["new"] or totals["due"]:
        tomorrow = args["today"] + DAY
        next_due = min(next_due or tomorrow, tomorrow)
    return {
        "done": True,
        "next_due": None if next_due is None else iso(next_due),
        "counts": totals,
    }


# The answers


def schedule(conn, user: str, card_id: int, before: Card | None, rating: int, when):
    """Apply a rating to the card as it was before, and store the result."""
    card = before or Card(due=when)
    card, _ = SCHEDULER.review_card(card, Rating(rating), review_datetime=when)
    conn.execute(
        "INSERT INTO user_card (user_id, card_id, state, due, fsrs, first_seen)"
        " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (user_id, card_id) DO UPDATE SET"
        " state = excluded.state, due = excluded.due, fsrs = excluded.fsrs",
        (
            user,
            card_id,
            card.state,
            card.due.timestamp(),
            json.dumps(card.to_dict()),
            when.timestamp(),
        ),
    )
    return card


def answer(user: str, card_id: int, rating: int, typed: str, elapsed_ms: int | None):
    """Store the automatic rating of an answer. Returns (review id, next due)."""
    when = now()
    with _lock, db() as conn:
        row = conn.execute(
            "SELECT fsrs FROM user_card WHERE user_id = ? AND card_id = ?",
            (user, card_id),
        ).fetchone()
        before = row and row["fsrs"]
        card = schedule(
            conn,
            user,
            card_id,
            before and Card.from_dict(json.loads(before)),
            rating,
            when,
        )
        cursor = conn.execute(
            "INSERT INTO review (user_id, card_id, reviewed_at, rating, auto_rating,"
            " typed, elapsed_ms, before) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user,
                card_id,
                when.timestamp(),
                rating,
                rating,
                typed,
                elapsed_ms,
                before,
            ),
        )
        return cursor.lastrowid, iso(card.due.timestamp())


def change_rating(user: str, review_id: int, rating: int) -> str:
    """The user does not agree with the automatic rating. Only for the last
    review of a card: a later review was scheduled from this one. Returns the
    new due time."""
    with _lock, db() as conn:
        review = conn.execute(
            "SELECT * FROM review r WHERE id = ? AND user_id = ? AND id ="
            " (SELECT MAX(id) FROM review WHERE card_id = r.card_id AND user_id = r.user_id)",
            (review_id, user),
        ).fetchone()
        if review is None:
            raise NotFound(f"no review {review_id} that can change")
        before = review["before"] and Card.from_dict(json.loads(review["before"]))
        when = datetime.fromtimestamp(review["reviewed_at"], UTC)
        card = schedule(conn, user, review["card_id"], before, rating, when)
        conn.execute("UPDATE review SET rating = ? WHERE id = ?", (rating, review_id))
        return iso(card.due.timestamp())


def get_review(user: str, review_id: int) -> dict:
    """A review of the user: the review of another user is not there."""
    with _lock, db() as conn:
        row = conn.execute(
            "SELECT * FROM review WHERE id = ? AND user_id = ?", (review_id, user)
        ).fetchone()
    if row is None:
        raise NotFound(f"no review {review_id}")
    return dict(row)


# The answers of the AI (tlhelper/explain)


def explanation(key: str) -> str | None:
    with _lock, db() as conn:
        row = conn.execute(
            "SELECT text FROM explanation WHERE key = ?", (key,)
        ).fetchone()
    return row and row["text"]


def explanations_today(user: str) -> int:
    with _lock, db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM explanation WHERE user_id = ? AND created_at >= ?",
            (user, day_start(now())),
        ).fetchone()[0]


def save_explanation(key: str, user: str, model: str, text: str) -> None:
    with _lock, db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO explanation (key, user_id, model, text,"
            " created_at) VALUES (?, ?, ?, ?, ?)",
            (key, user, model, text, now().timestamp()),
        )


# The users


def save_user(sub: str, name: str | None) -> None:
    """Keep the name of a login. A later login replaces a changed name."""
    with _lock, db() as conn:
        conn.execute(
            "INSERT INTO user (sub, name, seen_at) VALUES (?, ?, ?)"
            " ON CONFLICT (sub) DO UPDATE SET name = excluded.name,"
            " seen_at = excluded.seen_at",
            (sub, name, now().timestamp()),
        )


def users() -> list[dict]:
    """Each user with a card or a login. The name is the sub where no login
    saved a name."""
    with _lock, db() as conn:
        rows = conn.execute(
            "SELECT ids.id, COALESCE(u.name, ids.id) AS name FROM ("
            " SELECT user_id AS id FROM user_card UNION SELECT user_id FROM review"
            " UNION SELECT sub FROM user) ids LEFT JOIN user u ON u.sub = ids.id"
            " ORDER BY name COLLATE NOCASE, ids.id"
        ).fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


# The numbers


def stats(user: str, deck_id: int | None = None) -> dict:
    when = now()
    today = day_start(when)
    args = {"user": user, "deck": deck_id, "since": today - (STATS_DAYS - 1) * DAY}
    with _lock, db() as conn:
        rows = conn.execute(
            # The day number, counted from the epoch.
            "SELECT CAST(r.reviewed_at / 86400 AS INTEGER) AS day, COUNT(*) AS reviews,"
            " SUM(r.rating > 1) AS passed FROM review r JOIN card c ON c.id = r.card_id"
            " WHERE r.user_id = :user AND (:deck IS NULL OR c.deck_id = :deck)"
            " GROUP BY day ORDER BY day",
            args,
        ).fetchall()
        lapses = conn.execute(
            "SELECT COUNT(*) FROM review r JOIN card c ON c.id = r.card_id"
            " WHERE r.user_id = :user AND (:deck IS NULL OR c.deck_id = :deck)"
            " AND r.rating = 1 AND json_extract(r.before, '$.state') = 2",
            args,
        ).fetchone()[0]
        deck_ids = [
            row["id"]
            for row in conn.execute("SELECT id FROM deck ORDER BY name")
            if deck_id in (None, row["id"])
        ]
        totals = [counts(conn, user, each, when) for each in deck_ids]
    by_day = {row["day"]: row for row in rows}
    reviews = sum(row["reviews"] for row in rows)
    passed = sum(row["passed"] for row in rows)
    # A day with no review yet does not end the streak before it is over.
    day = int(today // DAY)
    if day not in by_day:
        day -= 1
    streak = 0
    while day - streak in by_day:
        streak += 1
    first = int(args["since"] // DAY)
    return {
        "counts": {key: sum(each[key] for each in totals) for key in totals[0]}
        if totals
        else {},
        "reviews": reviews,
        "success_rate": passed / reviews if reviews else None,
        "lapses": lapses,
        "streak_days": streak,
        "days": [
            {
                "date": (datetime.fromtimestamp(number * DAY, UTC)).date().isoformat(),
                "reviews": by_day[number]["reviews"] if number in by_day else 0,
                "passed": by_day[number]["passed"] if number in by_day else 0,
            }
            for number in range(first, first + STATS_DAYS)
        ],
    }
