"""The models in memory, the reference clips, and the mp3 of a text."""

import threading
import wave
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import lameenc
import numpy as np

from . import native, settings

# A code of a caller that differs from the id of the model. The ids are ISO
# 639-1 where one exists, else ISO 639-3 (omnivoice.utils.lang_map).
LANGUAGE_CODES: dict[str, str] = {}

# The bit rate of the mp3, in kbit/s. Speech at 24 kHz mono is clear at 64.
BIT_RATE = 64

# The clip for a language that has none of its own (README.md, "Voice").
DEFAULT_CLIP = "default"
CLIP_RATE = 24000


def load_model(model_id: str) -> Any:
    """The two GGUFs of the model (README.md, "Models") in omnivoice.cpp. The
    first call downloads them into the Hugging Face cache."""
    from huggingface_hub import hf_hub_download

    quant = settings.quant()
    base = hf_hub_download(model_id, f"omnivoice-base-{quant}.gguf")
    codec = hf_hub_download(model_id, f"omnivoice-tokenizer-{quant}.gguf")
    return native.Model(base, codec)


def read_clip(path: Path) -> np.ndarray:
    """The float samples of a 24 kHz mono 16-bit WAV."""
    try:
        with wave.open(str(path)) as clip:
            shape = (clip.getframerate(), clip.getnchannels(), clip.getsampwidth())
            frames = clip.readframes(clip.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError(
            f'{path} is not a WAV ({exc}): see README.md, "Voice"'
        ) from exc
    if shape != (CLIP_RATE, 1, 2):
        raise ValueError(
            f"{path} is {shape[0]} Hz, {shape[1]} channels, {8 * shape[2]} bits: "
            'it must be 24000 Hz, mono, 16 bits (README.md, "Voice")'
        )
    return np.frombuffer(frames, "<i2").astype(np.float32) / 32768


def read_voices(folder: Path | None) -> dict[str, tuple[np.ndarray, str]]:
    """Each <name>.wav of the folder, with what it says from <name>.txt."""
    voices = {}
    for path in sorted(folder.glob("*.wav")) if folder else []:
        script = path.with_suffix(".txt")
        text = script.read_text().strip() if script.is_file() else ""
        if not text:
            raise ValueError(f"{path} needs its transcript in {script.name}")
        voices[path.stem] = (read_clip(path), text)
    return voices


def mp3(audio: np.ndarray, rate: int) -> bytes:
    """The mp3 of a mono float signal in -1..1."""
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(BIT_RATE)
    encoder.set_in_sample_rate(rate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    encoder.silence()
    return bytes(encoder.encode(pcm.tobytes())) + bytes(encoder.flush())


Key = tuple[str, str, str, str, int]


class Synth:
    """The models by id. One lock covers a load and a generation: one CPU
    runs one of them at a time, and a request that arrives during the load
    at the start waits for it.

    A request with no instruct clones the reference clip of its language, or
    the default clip, else it gets OMNIVOICE_INSTRUCT (README.md, "Voice").
    The clips are read once, and each model encodes them once, at its load.

    The last mp3s (settings.cache_size()) stay in memory, by model, text,
    language, voice and steps, so a repeat of a text costs nothing. A request
    with an empty instruct lets the model pick the voice, and never comes
    from the cache."""

    def __init__(self, loader: Callable[[str], Any] = load_model):
        self.loader = loader
        self.models: dict[str, Any] = {}
        self.references: dict[str, dict[str, native.Reference]] = {}
        self._voices: dict[str, tuple[np.ndarray, str]] | None = None
        self.lock = threading.Lock()
        self.cache: OrderedDict[Key, bytes] = OrderedDict()

    def voices(self) -> dict[str, tuple[np.ndarray, str]]:
        """The clips of settings.voices_dir(), read on the first call."""
        if self._voices is None:
            self._voices = read_voices(settings.voices_dir())
        return self._voices

    def loaded(self) -> list[str]:
        return sorted(self.models)

    def load(self, model_id: str) -> None:
        with self.lock:
            self._model(model_id)

    def _model(self, model_id: str) -> Any:
        # Under the lock.
        if model_id not in self.models:
            model = self.loader(model_id)
            self.references[model_id] = {
                name: model.reference(samples, text)
                for name, (samples, text) in self.voices().items()
            }
            self.models[model_id] = model
        return self.models[model_id]

    def clip(self, language: str) -> str | None:
        """The name of the clip for a request in the language with no
        instruct, or None for OMNIVOICE_INSTRUCT."""
        voices = self.voices()
        if language in voices:
            return language
        return DEFAULT_CLIP if DEFAULT_CLIP in voices else None

    def speak(
        self, text: str, language: str, instruct: str | None, model_id: str
    ) -> tuple[bytes, bool]:
        """The mp3, and whether it came from the cache. instruct None is the
        default voice."""
        num_step = settings.num_step()
        clip = self.clip(language) if instruct is None else None
        if instruct is None and clip is None:
            instruct = settings.instruct()
        voice = (f"clip:{clip}" if clip else instruct) or ""
        key = (model_id, text, language, voice, num_step)
        # A hit does not wait for a generation that is under way.
        if voice and key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key], True
        with self.lock:
            model = self._model(model_id)
            audio = model.generate(
                text=text,
                language=LANGUAGE_CODES.get(language, language),
                instruct=instruct or None,
                num_step=num_step,
                reference=self.references[model_id][clip] if clip else None,
            )
            rate = model.sampling_rate
        data = mp3(np.asarray(audio, dtype=np.float32), rate)
        if voice:
            self.cache[key] = data
            while len(self.cache) > settings.cache_size():
                self.cache.popitem(last=False)
        return data, False
