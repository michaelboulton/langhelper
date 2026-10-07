"""Croatian: tagged by spaCy (light.py) or by classla (heavy.py), with grammar
checks (grammar.py) and the pitch accent of each word (accents.py)."""

import logging
from typing import ClassVar

from ..base import STUDY, Grading, LanguageInfo, ModelsMissing
from . import accents, heavy, light

logger = logging.getLogger("uvicorn.error")


class Croatian:
    info = LanguageInfo(
        code="hr",
        name="Croatian",
        tag_name="MULTEXT-East tag",
        placeholder="Ona je bila kod kuće.",
        # "nonstandard" is also heavy: the classla models for casual text.
        variants=("light", "heavy", "nonstandard"),
        light_note=(
            "The small Croatian model has no spelling check, and it misses some"
            " errors of case (Pijem kava). The large models find more."
        ),
        has_accents=True,
        speech="hr-HR",
        # dict.cc searches from the address. HJP only searches from its own
        # POST form, so that link opens the front page and you enter the lemma
        # there.
        dictionary_links=(
            ("dict.cc: {lemma}", "https://enhr.dict.cc/?s={lemma}"),
            ("HJP", "https://hjp.znanje.hr/"),
        ),
        ui_locale="hr",
        native_name="Hrvatski",
        grading=Grading(plain_letters=(("đ", ("d", "dj")),)),
    )
    # "svoj" is the possessive of the subject, so English has a different word
    # for each person.
    extra_glosses: ClassVar[dict[str, list[str]]] = {
        "i": ["and", "also", "too"],
        "ili": ["or"],
        "kad": ["when"],
        "kada": ["when"],
        "svoj": ["my", "your", "his", "her", "its", "our", "their", "own"],
    }

    def warm_up(self) -> None:
        try:
            light.TAGGER.warm_up()
        except ModelsMissing as exc:
            logger.error("%s", exc)

    def status(self) -> dict:
        return STUDY.status(self.info.code)

    def analyze(
        self, text: str, *, variant: str = "light", check: bool = True
    ) -> list[dict]:
        if variant == "light":
            sentences = light.TAGGER.words(text, check)
        else:
            sentences = heavy.words(text, variant, check)
        for sentence in sentences:
            for word in sentence["words"]:
                word["accent"] = accents.accent_for(
                    word["text"], word["lemma"], word["upos"], word["feats"]
                )
        return sentences

    def glosses(self, text: str, lemma: str, upos: str) -> dict[str, int]:
        return accents.glosses_for(text, lemma, upos)
