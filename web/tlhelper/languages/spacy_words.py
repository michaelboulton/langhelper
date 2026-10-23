"""Tag a text with a spaCy model. English, German, French, Italian and the
light Croatian models use this.

The English model is small (about 50 MB loaded), so it stays in memory with
its own lock. The model of a study language is in the one slot of
base.STUDY.
"""

import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager

import spacy

from .base import STUDY, ModelsMissing


class SpacyTagger:
    def __init__(
        self,
        model: str,
        check: Callable[[list, list[dict]], None],
        upos: Callable[[object], str] = lambda token: token.pos_,
        slot_key: tuple[str, str] | None = None,
    ):
        """check(tokens, words): gives each word of one sentence its "problems"
        list. upos(token): for a model whose tags need a correction.
        slot_key: (language code, model type) for a model of a study language,
        see base.StudySlot. None: the model stays loaded."""
        self.model = model
        self.check = check
        self.upos = upos
        self.slot_key = slot_key
        self.loading = False
        self._nlp = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        if self.slot_key:
            return self.slot_key == STUDY.key
        return self._nlp is not None

    def load(self):
        try:
            return spacy.load(self.model, exclude=["ner"])
        except OSError as exc:
            raise ModelsMissing(
                f"The spaCy model {self.model} is not installed: {exc}"
            ) from exc

    @contextmanager
    def nlp(self) -> Generator:
        if self.slot_key:
            with STUDY.use(self.slot_key, self.load) as nlp:
                yield nlp
            return
        with self._lock:
            if self._nlp is None:
                self.loading = True
                try:
                    self._nlp = self.load()
                finally:
                    self.loading = False
            yield self._nlp

    def warm_up(self) -> None:
        with self.nlp():
            pass

    def words(self, text: str, check: bool) -> list[dict]:
        with self.nlp() as nlp:
            doc = nlp(text)
        sentences = []
        for sent in doc.sents:
            tokens = [t for t in sent if not t.is_space]
            ids = {token.i: id for id, token in enumerate(tokens, start=1)}
            words = [
                {
                    "id": id,
                    "text": token.text,
                    "lemma": token.lemma_,
                    "upos": self.upos(token),
                    # The French model has no tag set, and repeats the UPOS.
                    "xpos": token.tag_ if token.tag_ != token.pos_ else "",
                    "feats": token.morph.to_dict(),
                    # The root of the sentence is its own head in spaCy.
                    "head": (
                        0 if token.head.i == token.i else ids.get(token.head.i, 0)
                    ),
                    "deprel": token.dep_,
                    "start_char": token.idx,
                    "end_char": token.idx + len(token.text),
                }
                for id, token in enumerate(tokens, start=1)
            ]
            if check:
                self.check(tokens, words)
            sentences.append({"text": sent.text.strip(), "words": words})
        return sentences
