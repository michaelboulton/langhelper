"""The OpenAPI schema must be enough to use the API with no look at the code."""

from tlhelper import app as service

SCHEMA = service.app.openapi()
# The names say it all.
PLAIN = {"text", "name", "language", "id", "lemma", "upos", "count", "detail"}
PLAIN |= {"sentences", "words", "decks", "counts", "source", "kind", "url"}
PLAIN |= {"card_id", "prompt", "rating", "next_due", "me", "admin", "date", "reviews"}
PLAIN |= {"has_accents", "streak_days", "done", "loc", "msg", "type", "input", "ctx"}
PLAIN |= {"available"}


def operations():
    for path, methods in SCHEMA["paths"].items():
        for method, operation in methods.items():
            yield f"{method.upper()} {path}", operation


def test_each_route_has_a_description_and_a_response_shape():
    assert len(list(operations())) == 18
    for name, operation in operations():
        assert operation.get("description"), name
        assert operation.get("tags"), name
        content = operation["responses"]["200"]["content"]
        shape = content.get("application/json", {}).get("schema")
        # A picture of a card, the Fluent file of a locale, and a text read
        # aloud.
        plain = {"image/*", "text/plain", "audio/mpeg"}
        assert shape or plain & set(content), name
        for parameter in operation.get("parameters", []):
            if parameter["in"] == "query":
                assert parameter.get("description"), f"{name}: {parameter['name']}"


def test_each_attribute_of_a_model_has_a_description():
    missing = [
        f"{model}.{name}"
        for model, shape in SCHEMA["components"]["schemas"].items()
        for name, attribute in shape.get("properties", {}).items()
        if name not in PLAIN and not attribute.get("description")
    ]
    assert missing == []


def test_the_request_of_classify():
    attributes = SCHEMA["components"]["schemas"]["ClassifyRequest"]["properties"]
    assert all(attribute.get("description") for attribute in attributes.values())
    assert attributes["source"]["enum"] == ["study", "en"]
