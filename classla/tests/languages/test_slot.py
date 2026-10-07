"""Tests for base.StudySlot: the one model of a study language in memory."""

import pytest

from tlhelper.languages import ENGLISH
from tlhelper.languages.base import StudySlot


def test_the_same_key_loads_once_and_another_key_replaces_it():
    slot, loads = StudySlot(), []

    def load(name):
        loads.append(name)
        return name

    for name in ("hr heavy", "hr heavy", "de light"):
        code, model_type = name.split()
        with slot.use((code, model_type), lambda name=name: load(name)) as model:
            assert model == name
    assert loads == ["hr heavy", "de light"]
    assert slot.status("de") == {"loading": None, "loaded": ["light"]}
    assert slot.status("hr") == {"loading": None, "loaded": []}


def test_the_old_model_is_gone_before_the_new_one_loads():
    slot, during = StudySlot(), []
    with slot.use(("hr", "heavy"), lambda: "old"):
        pass

    def load():
        during.append((slot.key, slot._model, slot.status("de"), slot.status("hr")))
        return "new"

    with slot.use(("de", "heavy"), load):
        pass
    assert during == [
        (
            None,
            None,
            {"loading": "heavy", "loaded": []},
            {"loading": None, "loaded": []},
        )
    ]


def test_a_failed_load_leaves_the_slot_empty():
    slot = StudySlot()

    def load():
        raise OSError("no model")

    with pytest.raises(OSError), slot.use(("de", "heavy"), load):
        pass
    assert (slot.key, slot.loading) == (None, None)
    # The lock is free again.
    with slot.use(("de", "light"), lambda: "model") as model:
        assert model == "model"


def test_english_is_not_in_the_slot():
    from tlhelper.languages.base import STUDY

    with STUDY.use(("hr", "heavy"), lambda: "pipeline"):
        pass
    ENGLISH.analyze("This is good.")
    assert STUDY.key == ("hr", "heavy")
    assert ENGLISH.status()["loaded"] == ["light"]
    STUDY.drop()
    assert ENGLISH.status()["loaded"] == ["light"]
