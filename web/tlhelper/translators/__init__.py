"""The machine translators: the services that translate a text for the app.

app.translate() calls the translator that the environment variable TRANSLATOR
names (default "deepl"), and keeps each result in SQLite. The translator is a
part of the cache key, so a new service does not show the texts of the old one.

DeepL (deepl.py), the only translator now
    1. Make an API account at https://www.deepl.com/pro-api and copy the key.
       The README ("Translation") has the limits of the free plan.
    2. Set DEEPL_API_KEY. With docker compose, put it in .env (see
       example.env). On Fly: fly secrets set DEEPL_API_KEY=...
    3. With a paid key, set DEEPL_URL=https://api.deepl.com/v2/translate.

To add a translator
    1. Write a module here with a class that fits base.Translator: a name,
       and translate(text, source, target), which makes one request.
    2. Map the codes of the app ("hr", "de", "en") to the codes of the
       service in that module. A language knows nothing about a translator.
    3. Raise base.TranslationError for every failure, with a message that
       the page can show: no credentials, no answer in base.TIMEOUT seconds,
       a used-up quota, too many requests.
    4. Read the credentials from the environment. Import the SDK and make
       its client in the class, on the first call, and not at the import of
       the module: the app must start with no SDK and no credentials of a
       translator that it does not use.
    5. Add an instance to TRANSLATORS below, the SDK to an optional
       dependency group of pyproject.toml, and the set-up to this docstring.

Notes for the two likely ones. Both take the codes of the app as they are.
    Amazon Translate (boto3)
        client = boto3.client("translate", config=botocore.config.Config(
            connect_timeout=TIMEOUT, read_timeout=TIMEOUT,
            retries={"max_attempts": 1}))
        client.translate_text(Text=text, SourceLanguageCode=source,
            TargetLanguageCode=target)["TranslatedText"]
        The credentials and the region come from the usual AWS chain
        (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION). A text has a
        limit of 10,000 bytes. The errors are botocore.exceptions.ClientError
        (the code is in exc.response["Error"]["Code"]:
        TooManyRequestsException, TextSizeLimitExceededException,
        UnsupportedLanguagePairException) and BotoCoreError (no credentials,
        no connection, a timeout).
    Google Cloud Translation v3 (google-cloud-translate)
        client = translate_v3.TranslationServiceClient()
        client.translate_text(request={
            "parent": f"projects/{project}/locations/global",
            "contents": [text], "mime_type": "text/plain",
            "source_language_code": source, "target_language_code": target,
        }, timeout=TIMEOUT).translations[0].translated_text
        The default mime_type is HTML, which escapes characters, so
        "text/plain" is necessary. "model" selects the Translation LLM
        ("projects/{project}/locations/us-central1/models/general/
        translation-llm", with the same location in "parent"). The
        credentials are the Application Default Credentials
        (GOOGLE_APPLICATION_CREDENTIALS) and the project comes from
        GOOGLE_CLOUD_PROJECT. The errors are
        google.api_core.exceptions.GoogleAPICallError (ResourceExhausted,
        DeadlineExceeded) and google.auth.exceptions.DefaultCredentialsError.
"""

import os

from .base import TIMEOUT, TranslationError, Translator
from .deepl import DeepL

__all__ = ["TIMEOUT", "TRANSLATORS", "TranslationError", "Translator", "current"]

TRANSLATORS: dict[str, Translator] = {each.name: each for each in (DeepL(),)}
DEFAULT = "deepl"


def current() -> Translator:
    """The translator that TRANSLATOR names."""
    name = os.environ.get("TRANSLATOR", DEFAULT)
    if name not in TRANSLATORS:
        known = ", ".join(sorted(TRANSLATORS))
        raise TranslationError(f"TRANSLATOR is {name!r}, and must be one of: {known}")
    return TRANSLATORS[name]
