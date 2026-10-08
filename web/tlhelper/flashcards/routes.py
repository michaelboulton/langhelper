"""The flashcard API. The progress belongs to the user of the OIDC login.

GET  /api/v1/decks                the decks, with the counts of the user
GET  /api/v1/decks/{id}/next      the next card and the breakdown of its prompt
POST /api/v1/cards/{id}/answer    grade a typed answer, schedule the card, and
                                  break down the typed and the correct answer
POST /api/v1/reviews/{id}/rating  the user changes the automatic rating
GET  /api/v1/flashcards/stats     the numbers of the user, or for an admin
                                  the numbers of the user in `of`
GET  /api/v1/flashcards/users     the users whose numbers the user can see
GET  /api/v1/decks/{id}/media/{name}  an image or a sound clip of a card
"""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import Field

from .. import align, schemas
from ..languages import ENGLISH, LANGUAGES, ModelsMissing, model_type
from ..messages import CodedHTTPException
from . import apkg, decks, grade, store

# Where there is no login (localhost), everything belongs to this user.
LOCAL_USER = "local"

router = APIRouter(prefix="/api/v1", tags=["flashcards"])
# A response is the dict of the code: no key that the code did not set.
UNSET: schemas.RouteOptions = {"response_model_exclude_unset": True}
HEAVY = "Use the heavy models of the study language for the breakdown."


def current_user(request: Request) -> str:
    """The `sub` claim of the login: it never changes, unlike the name."""
    user = request.session.get("user") if "session" in request.scope else None
    return (user or {}).get("sub") or LOCAL_USER


User = Annotated[str, Depends(current_user)]

# The value of the custom claim `pocketid_user_group` that makes an admin.
ADMIN_GROUP = "admin"
# The name of the own entry in the user list.
OWN_NAME = "My cards"


def is_admin(request: Request) -> bool:
    """An admin can see the numbers of each user. Never without a login."""
    user = request.session.get("user") if "session" in request.scope else None
    return (user or {}).get("group") == ADMIN_GROUP


Admin = Annotated[bool, Depends(is_admin)]


class AnswerRequest(schemas.Model):
    typed: str = Field(max_length=1000)
    """What the user entered. Empty for "I do not know"."""
    heavy: bool = False
    """Use the heavy models of the study language for the breakdown."""
    elapsed_ms: int | None = Field(default=None, ge=0)
    """How long the user looked at the card, in milliseconds."""


class RatingRequest(schemas.Model):
    rating: int = Field(ge=grade.AGAIN, le=grade.EASY)
    """1 Again, 2 Hard, 3 Good, 4 Easy."""


def side(
    card: dict, text: str, heavy: bool, *, prompt: bool, check: bool
) -> list[dict]:
    """Break down the prompt of a card, or an answer to it. The prompt of a
    "to_study" card is English, and so is an answer to a "to_english" card."""
    if not text.strip():
        return []
    if prompt == (card["direction"] == store.TO_STUDY):
        return ENGLISH.analyze(text, check=check)
    language = LANGUAGES[card["language"]]
    return language.analyze(text, variant=model_type(language, heavy), check=check)


def linked(card: dict, prompt: list[dict], answer: list[dict]) -> dict:
    """An answer with its links to the prompt. As in /api/v1/classify, a link
    is [word of the study language, English word], whatever the direction."""
    if card["direction"] == store.TO_STUDY:
        study, english = answer, prompt
    else:
        study, english = prompt, answer
    return {
        "sentences": answer,
        **align.align(LANGUAGES[card["language"]], study, english),
    }


def media(card: dict, names: list[str]) -> list[dict]:
    """What the page needs to show the media files of one side of a card."""
    return [
        {
            "kind": apkg.kind(name)[0],
            "url": f"/api/v1/decks/{card['deck_id']}/media/{quote(name, safe='')}",
        }
        for name in names
    ]


@router.get("/decks", response_model=schemas.DecksResponse, **UNSET)
def deck_list(user: User) -> dict:
    """The decks, each with the card counts of the user."""
    return {"decks": store.decks(user)}


@router.get(
    "/decks/{deck_id}/next",
    response_model=schemas.NextCard | schemas.NoCard,
    responses=schemas.NOT_FOUND | schemas.MODELS_MISSING,
    **UNSET,
)
def next_card(
    deck_id: int, user: User, heavy: bool = Query(False, description=HEAVY)
) -> dict:
    """The next card of the queue, with the breakdown of its prompt and with
    no answers. `done` if the user is through for now."""
    try:
        result = store.next_card(user, deck_id)
        if "card" not in result:
            return result
        card = result["card"]
        return {
            "card_id": card["id"],
            "direction": card["direction"],
            "language": card["language"],
            "prompt": card["prompt"],
            "media": media(card, card["prompt_media"]),
            # No answers: the page must not have them before the user answers.
            "prompt_sentences": side(
                card, card["prompt"], heavy, prompt=True, check=False
            ),
            "counts": result["counts"],
        }
    except store.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/cards/{card_id}/answer",
    response_model=schemas.AnswerResponse,
    responses=schemas.NOT_FOUND | schemas.MODELS_MISSING,
    **UNSET,
)
def answer(card_id: int, req: AnswerRequest, user: User) -> dict:
    """Grade a typed answer, schedule the card, and break down the typed and
    the correct answer."""
    try:
        card = store.get_card(card_id)
        # The answers of a "to_english" card are English.
        study = card["direction"] == store.TO_STUDY
        answers_in = LANGUAGES[card["language"]] if study else ENGLISH
        result = grade.grade(req.typed, card["answers"], answers_in.info.grading)
        # The models first: a failure must not leave a review behind.
        prompt = side(card, card["prompt"], req.heavy, prompt=True, check=False)
        typed = side(card, req.typed, req.heavy, prompt=False, check=True)
        correct = side(card, result["answer"], req.heavy, prompt=False, check=False)
    except store.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelsMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    review_id, next_due = store.answer(
        user, card_id, result["rating"], req.typed, req.elapsed_ms
    )
    return {
        "review_id": review_id,
        "rating": result["rating"],
        "next_due": next_due,
        "diff": result["diff"],
        "answers": card["answers"],
        "media": media(card, card["answer_media"]),
        "typed": linked(card, prompt, typed),
        "correct": linked(card, prompt, correct),
    }


@router.post(
    "/reviews/{review_id}/rating",
    response_model=schemas.RatingResponse,
    responses=schemas.NOT_FOUND,
    **UNSET,
)
def change_rating(review_id: int, req: RatingRequest, user: User) -> dict:
    """Replace the automatic rating of an answer, and schedule the card again."""
    try:
        return {
            "rating": req.rating,
            "next_due": store.change_rating(user, review_id, req.rating),
        }
    except store.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/decks/{deck_id}/media/{name}",
    response_class=Response,
    responses={
        200: {
            "description": "The file",
            "content": {"image/*": {}, "audio/*": {}},
        },
        **schemas.NOT_FOUND,
    },
)
def media_file(deck_id: int, name: str) -> Response:
    """An image or a sound clip of a card. The `url` of a media entry is the
    address of this route."""
    try:
        # Only a file of a card: the package can hold more than that.
        package = decks.deck_path(store.media_deck(deck_id, name))
        if package is None:
            raise store.NotFound(f"deck {deck_id} has no package any more")
        data = apkg.read_media(package, name)
        media_type = apkg.kind(name)[1]
    except (store.NotFound, KeyError, apkg.BadDeck) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        data,
        media_type=media_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            # Of a user with a login, so not for a shared cache.
            "Cache-Control": "private, max-age=86400",
        },
    )


@router.get("/flashcards/users", response_model=schemas.UsersResponse, **UNSET)
def users(user: User, admin: Admin) -> dict:
    """The users whose numbers this user can see. The own entry comes first."""
    others = [each for each in store.users() if each["id"] != user] if admin else []
    return {
        "me": user,
        "admin": admin,
        "users": [{"id": user, "name": OWN_NAME}, *others],
    }


@router.get(
    "/flashcards/stats",
    response_model=schemas.StatsResponse,
    responses={403: {"model": schemas.ErrorResponse, "description": "Not an admin"}},
    **UNSET,
)
def stats(
    user: User,
    admin: Admin,
    deck: int | None = Query(None, description="Only this deck. Default: all."),
    of: str | None = Query(
        None, description="The `id` of another user. Only for an admin."
    ),
) -> dict:
    """The numbers of the user: the counts, the success rate, and the reviews
    of each of the last days."""
    if of not in (None, user) and not admin:
        raise CodedHTTPException(
            403, "not-admin", "Only an admin can see the cards of another user."
        )
    return store.stats(of or user, deck)
