"""The heavy Italian models: Stanza, the combined UD treebanks. About 330 MB
on disk, downloaded on first use from Hugging Face."""

import logging

import stanza

from ...settings import DATA_ROOT, DOWNLOAD_MODELS
from ..base import STUDY, ModelsMissing, parse_feats
from . import checks

MODEL_DIR = DATA_ROOT / "stanza_resources"

LANG = "it"
# mwt splits "sul" into "su il", so the checks see the article.
PROCESSORS = "tokenize,mwt,pos,lemma,depparse"

logger = logging.getLogger("uvicorn.error")


def get_pipeline() -> stanza.Pipeline:
    try:
        return load_pipeline()
    except Exception as exc:
        if not DOWNLOAD_MODELS:
            raise ModelsMissing(
                f"The Stanza models did not load from {MODEL_DIR}"
                f" and DOWNLOAD_MODELS is off: {exc!r}"
            ) from exc
        logger.warning(
            "the Stanza models did not load from %s (%r), downloading",
            MODEL_DIR,
            exc,
        )
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        stanza.download(LANG, model_dir=str(MODEL_DIR), processors=PROCESSORS)
        return load_pipeline()


def load_pipeline() -> stanza.Pipeline:
    # download_method=None: no network access, so a missing model raises.
    return stanza.Pipeline(
        LANG,
        processors=PROCESSORS,
        dir=str(MODEL_DIR),
        download_method=None,
        use_gpu=False,
    )


def words(text: str, check: bool) -> list[dict]:
    with STUDY.use((LANG, "heavy"), get_pipeline) as pipeline:
        doc = pipeline(text)
    sentences = []
    for sentence in doc.sentences:
        # The words of "sul" share the span of their token.
        found = [
            {
                "id": word.id,
                "text": word.text,
                "lemma": word.lemma or word.text,
                "upos": word.upos,
                "xpos": word.xpos or "",
                "feats": parse_feats(word.feats),
                "head": word.head,
                "deprel": word.deprel,
                "start_char": word.parent.start_char,
                "end_char": word.parent.end_char,
            }
            for word in sentence.words
        ]
        if check:
            checks.check_words(found)
        sentences.append({"text": sentence.text, "words": found})
    return sentences
