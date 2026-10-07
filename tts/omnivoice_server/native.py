"""The C library of omnivoice.cpp through ctypes. README.md has the build, the
pinned commit and how to bump it."""

import ctypes
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger("omnivoice.cpp")

# The structs below mirror src/omnivoice.h at the pinned commit (README.md),
# field for field. The library rejects a higher abi_version.
ABI_VERSION = 3

OK = 0
INSTRUCT_INVALID = -2


class InitParams(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_int),
        ("model_path", ctypes.c_char_p),
        ("codec_path", ctypes.c_char_p),
        ("use_fa", ctypes.c_bool),
        ("clamp_fp16", ctypes.c_bool),
    ]


CancelCallback = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p)
ChunkCallback = ctypes.CFUNCTYPE(
    ctypes.c_bool, ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.c_void_p
)


class TtsParams(ctypes.Structure):
    _fields_ = [
        ("abi_version", ctypes.c_int),
        ("text", ctypes.c_char_p),
        ("lang", ctypes.c_char_p),
        ("instruct", ctypes.c_char_p),
        ("T_override", ctypes.c_int),
        ("chunk_duration_sec", ctypes.c_float),
        ("chunk_threshold_sec", ctypes.c_float),
        ("denoise", ctypes.c_bool),
        ("preprocess_prompt", ctypes.c_bool),
        ("mg_num_step", ctypes.c_int),
        ("mg_guidance_scale", ctypes.c_float),
        ("mg_t_shift", ctypes.c_float),
        ("mg_layer_penalty_factor", ctypes.c_float),
        ("mg_position_temperature", ctypes.c_float),
        ("mg_class_temperature", ctypes.c_float),
        ("mg_seed", ctypes.c_uint64),
        ("ref_audio_tokens", ctypes.POINTER(ctypes.c_int32)),
        ("ref_T", ctypes.c_int),
        ("ref_audio_24k", ctypes.POINTER(ctypes.c_float)),
        ("ref_n_samples", ctypes.c_int),
        ("ref_text", ctypes.c_char_p),
        ("dump_dir", ctypes.c_char_p),
        ("cancel", CancelCallback),
        ("cancel_user_data", ctypes.c_void_p),
        ("on_chunk", ChunkCallback),
        ("on_chunk_user_data", ctypes.c_void_p),
        ("postproc", ctypes.c_bool),
    ]


class Audio(ctypes.Structure):
    _fields_ = [
        ("samples", ctypes.POINTER(ctypes.c_float)),
        ("n_samples", ctypes.c_int),
        ("sample_rate", ctypes.c_int),
        ("channels", ctypes.c_int),
    ]


class VoiceRef(ctypes.Structure):
    _fields_ = [
        ("ref_codes", ctypes.POINTER(ctypes.c_int32)),
        ("ref_T", ctypes.c_int),
        ("num_codebooks", ctypes.c_int),
    ]


@dataclass(frozen=True)
class Reference:
    """The codes of a reference clip, [num_codebooks, frames] flattened, and
    what the clip says."""

    codes: np.ndarray
    frames: int
    text: str


LogCallback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)

# The levels of the library (ov_log_level) to the levels of logging. Only
# the lines that it sends through ov_log come here (README.md, "Notes").
LOG_LEVELS = {0: logging.DEBUG, 1: logging.DEBUG, 2: logging.WARNING, 3: logging.ERROR}


@LogCallback
def _log(level: int, message: bytes, user_data) -> None:
    logger.log(
        LOG_LEVELS.get(level, logging.WARNING), "%s", message.decode(errors="replace")
    )


def library_path() -> Path:
    return Path(os.environ.get("OMNIVOICE_LIB", "/opt/omnivoice/lib/libomnivoice.so"))


_library: ctypes.CDLL | None = None


def library() -> ctypes.CDLL:
    """libomnivoice.so, loaded once. Its ggml libraries sit next to it."""
    global _library
    if _library is None:
        path = library_path()
        if not path.is_file():
            raise RuntimeError(
                f"no omnivoice.cpp library at {path}: build it and set OMNIVOICE_LIB "
                "(see README.md)"
            )
        lib = ctypes.CDLL(str(path))
        lib.ov_version.restype = ctypes.c_char_p
        lib.ov_last_error.restype = ctypes.c_char_p
        lib.ov_init_default_params.argtypes = [ctypes.POINTER(InitParams)]
        lib.ov_init.argtypes = [ctypes.POINTER(InitParams)]
        lib.ov_init.restype = ctypes.c_void_p
        lib.ov_free.argtypes = [ctypes.c_void_p]
        lib.ov_tts_default_params.argtypes = [ctypes.POINTER(TtsParams)]
        lib.ov_synthesize.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(TtsParams),
            ctypes.POINTER(Audio),
        ]
        lib.ov_synthesize.restype = ctypes.c_int
        lib.ov_audio_free.argtypes = [ctypes.POINTER(Audio)]
        lib.ov_extract_voice_ref.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.POINTER(VoiceRef),
        ]
        lib.ov_extract_voice_ref.restype = ctypes.c_int
        lib.ov_voice_ref_free.argtypes = [ctypes.POINTER(VoiceRef)]
        lib.ov_n_languages.restype = ctypes.c_int
        lib.ov_language_id.argtypes = [ctypes.c_int]
        lib.ov_language_id.restype = ctypes.c_char_p
        lib.ov_log_set.argtypes = [LogCallback, ctypes.c_void_p]
        # _log is a module global, so the pointer that the library keeps
        # stays valid.
        lib.ov_log_set(_log, None)
        _library = lib
    return _library


def version() -> str:
    return library().ov_version().decode()


def languages() -> list[str]:
    """The ids that the library accepts as `lang`."""
    lib = library()
    return [lib.ov_language_id(i).decode() for i in range(lib.ov_n_languages())]


def _error(lib: ctypes.CDLL) -> str:
    return (lib.ov_last_error() or b"").decode()


class Model:
    """One loaded pair of GGUFs: the language model and the codec. One call
    of generate at a time (Synth holds the lock)."""

    def __init__(self, model_path: str, codec_path: str):
        lib = library()
        params = InitParams()
        lib.ov_init_default_params(ctypes.byref(params))
        # The bytes stay referenced by the struct while ov_init reads them.
        params.model_path = str(model_path).encode()
        params.codec_path = str(codec_path).encode()
        self.context = lib.ov_init(ctypes.byref(params))
        if not self.context:
            raise RuntimeError(f"omnivoice.cpp did not load the model: {_error(lib)}")
        self.sampling_rate = 24000

    def __del__(self):
        context = getattr(self, "context", None)
        if context:
            library().ov_free(context)

    def reference(self, samples: np.ndarray, text: str) -> Reference:
        """The codes of a clip of 24 kHz mono float samples, for generate."""
        lib = library()
        samples = np.ascontiguousarray(samples, dtype=np.float32)
        ref = VoiceRef()
        status = lib.ov_extract_voice_ref(
            self.context,
            samples.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            len(samples),
            ctypes.byref(ref),
        )
        if status != OK:
            raise RuntimeError(f"omnivoice.cpp failed ({status}): {_error(lib)}")
        try:
            size = ref.num_codebooks * ref.ref_T
            codes = np.ctypeslib.as_array(ref.ref_codes, shape=(size,)).copy()
            return Reference(codes, ref.ref_T, text)
        finally:
            lib.ov_voice_ref_free(ctypes.byref(ref))

    def generate(
        self,
        text: str,
        language: str | None,
        instruct: str | None,
        num_step: int,
        reference: Reference | None = None,
    ) -> np.ndarray:
        """The mono float samples of the text, in the voice of the reference
        when there is one. ValueError when the library refuses an instruct
        item, with its message naming the item."""
        lib = library()
        params = TtsParams()
        lib.ov_tts_default_params(ctypes.byref(params))
        params.text = text.encode()
        params.lang = (language or "none").encode()
        params.instruct = instruct.encode() if instruct else None
        params.mg_num_step = num_step
        if reference is not None:
            # reference.codes outlives the call, so the pointer stays valid.
            params.ref_audio_tokens = reference.codes.ctypes.data_as(
                ctypes.POINTER(ctypes.c_int32)
            )
            params.ref_T = reference.frames
            params.ref_text = reference.text.encode()
        audio = Audio()
        status = lib.ov_synthesize(
            self.context, ctypes.byref(params), ctypes.byref(audio)
        )
        if status == INSTRUCT_INVALID:
            raise ValueError(_error(lib))
        if status != OK:
            raise RuntimeError(f"omnivoice.cpp failed ({status}): {_error(lib)}")
        try:
            samples = np.ctypeslib.as_array(audio.samples, shape=(audio.n_samples,))
            self.sampling_rate = audio.sample_rate
            return samples.astype(np.float32, copy=True)
        finally:
            lib.ov_audio_free(ctypes.byref(audio))
