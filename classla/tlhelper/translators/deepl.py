"""DeepL, through its REST API. The set-up is in the docstring of the package."""

import os

import requests

from .base import TIMEOUT, TranslationError

# Without a key, a request with translate set gets an error in place of the
# translation. A paid key needs https://api.deepl.com/v2/translate.
API_KEY = os.environ.get("DEEPL_API_KEY", "")
URL = os.environ.get("DEEPL_URL", "https://api-free.deepl.com/v2/translate")

# DeepL has target codes that are not source codes. Every other code is the
# code of the app in capital letters.
TARGET_CODES = {"en": "EN-US"}


class DeepL:
    name = "deepl"

    def translate(self, text: str, source: str, target: str) -> str:
        if not API_KEY:
            raise TranslationError("DEEPL_API_KEY is not set")
        try:
            response = requests.post(
                URL,
                headers={"Authorization": f"DeepL-Auth-Key {API_KEY}"},
                json={
                    "text": [text],
                    "source_lang": source.upper(),
                    "target_lang": TARGET_CODES.get(target, target.upper()),
                },
                timeout=TIMEOUT,
            )
        except requests.Timeout as exc:
            raise TranslationError(
                "DeepL did not answer in time", "translator-timeout", service="DeepL"
            ) from exc
        except requests.RequestException as exc:
            raise TranslationError(f"DeepL is not reachable: {exc!r}") from exc
        if response.status_code == 456:
            raise TranslationError(
                "the DeepL quota for this month is used up",
                "translator-quota",
                service="DeepL",
            )
        if response.status_code == 429:
            raise TranslationError(
                "DeepL has too many requests, try again",
                "translator-busy",
                service="DeepL",
            )
        if response.status_code != 200:
            raise TranslationError(
                f"DeepL returned HTTP {response.status_code}",
                "translator-http",
                service="DeepL",
                status=response.status_code,
            )
        return response.json()["translations"][0]["text"]
