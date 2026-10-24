"""The API files of the Flutter app in app/test/api/. The Dart tests check the
models of app/lib/api/models.dart against them (README.md, "The API client
and the models"). SAVE_OPENAPI=1 writes openapi.json again."""

import json
import os
from pathlib import Path

from tlhelper import app as service
from tlhelper import schemas

FOLDER = Path(__file__).parents[1] / "app" / "test" / "api"
# Each saved response, and its model.
FIXTURES = {
    "answer.json": schemas.AnswerResponse,
    "audio_lesson.json": schemas.AudioLessonResponse,
    "audio_lessons.json": schemas.AudioCoursesResponse,
    "classify.json": schemas.ClassifyResponse,
    "decks.json": schemas.DecksResponse,
    "explain.json": schemas.ExplainResponse,
    "languages.json": schemas.LanguagesResponse,
    "locales.json": schemas.LocalesResponse,
    "next.json": schemas.NextCard,
    "next_done.json": schemas.NoCard,
    "questions.json": schemas.QuestionsResponse,
    "rating.json": schemas.RatingResponse,
    "speech.json": schemas.SpeechInfoResponse,
    "stats.json": schemas.StatsResponse,
    "status.json": schemas.StatusResponse,
    "users.json": schemas.UsersResponse,
}


def test_the_saved_schema_is_the_schema_of_the_app():
    path = FOLDER / "openapi.json"
    schema = json.loads(json.dumps(service.app.openapi()))
    if os.environ.get("SAVE_OPENAPI") == "1":
        path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == schema, "run SAVE_OPENAPI=1 uv run pytest tests/test_dart_api.py"


def test_each_fixture_fits_its_model():
    folder = FOLDER / "fixtures"
    assert sorted(path.name for path in folder.glob("*.json")) == sorted(FIXTURES)
    for name, model in FIXTURES.items():
        body = json.loads((folder / name).read_text(encoding="utf-8"))
        # No key that the model does not have, and none that it changes.
        shape = model.model_validate(body).model_dump(mode="json", exclude_unset=True)
        assert shape == body, name
