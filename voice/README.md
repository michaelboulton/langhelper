# OmniVoice text to speech

A small FastAPI server around [omnivoice.cpp](https://github.com/ServeurpersoCom/omnivoice.cpp),
the C++/ggml port of [OmniVoice](https://github.com/k2-fsa/OmniVoice), a
zero-shot text-to-speech model for 646 languages. It has the shape of the
speech API of OpenAI, so a client that knows `GET /v1/models` and
`POST /v1/audio/speech` can use it. The "Listen" buttons of the
[classla](../classla/) page use it, and `classla/docker-compose.yml` runs it
next to the page.

The model is two GGUF files from one Hugging Face repo
(`Serveurperso/OmniVoice-GGUF`): the language model (`omnivoice-base-*`, a
Qwen3 with 0.6 B parameters) and the codec (`omnivoice-tokenizer-*`). The
default variant `Q8_0` is 945 MB for both. One model covers every language:
there are no per-language models. It runs on the GPU through Vulkan when
the container has one (see "GPU"): a short sentence takes about 1.5 s at 16
steps on the Radeon of a Strix Halo laptop. On the CPU it takes about 6 s at
16 steps and 12 s at 32 (24 threads). One request runs at a time.

## Files

| File | Purpose |
| ---- | ------- |
| `omnivoice_server/app.py` | The routes |
| `omnivoice_server/synth.py` | The models in memory, one lock for a load and a generation, the cache of the last mp3s, and the mp3 encoder (`lameenc`) |
| `omnivoice_server/native.py` | `libomnivoice.so` through ctypes: the structs of `omnivoice.h`, the load, one `generate`, the log callback |
| `omnivoice_server/languages.py` | The 646 language ids, generated (see "Notes") |
| `omnivoice_server/voices/` | The reference clips, `<language>.wav` in git lfs with the transcript in `<language>.txt` (see "Voice") |
| `omnivoice_server/settings.py` | The environment variables, read when they are used |
| `tests/` | The routes with a fake model, and the encoder with a real signal. Run with `uv run pytest`; no library and no model needed |
| `Dockerfile` | Two stages: a build of omnivoice.cpp at a pinned commit with the Vulkan and CPU backends, then `python:3.12-slim` plus the Mesa Vulkan drivers and `uv sync --frozen`, uid 1000, the Hugging Face cache at `/hf` |
| `pyproject.toml` | Dependencies: fastapi, uvicorn, numpy, lameenc, huggingface-hub |

## Routes

`GET /v1/models` lists the models, each with the language codes that it
reads. `languages` is not in the API of OpenAI; a client that does not know
it ignores it.

```bash
curl http://localhost:8002/v1/models
```

```json
{"object": "list", "data": [{"id": "Serveurperso/OmniVoice-GGUF", "object": "model",
  "owned_by": "Serveurperso", "languages": ["de", "en", "fr", "hr", "it"]}]}
```

`POST /v1/audio/speech` returns the mp3 of a text. `model` and `instruct`
are optional. `response_format` can only be `mp3`.

```bash
curl http://localhost:8002/v1/audio/speech \
  -H 'content-type: application/json' \
  -d '{"input": "Dobar dan. Kako ste?", "language": "hr"}' -o out.mp3
```

The server keeps the last mp3s in memory (`OMNIVOICE_CACHE`, default 16), by
model, text, language, voice (the clip or the instruct) and steps. The
`Cache-Status` header of the answer ([RFC 9211](https://www.rfc-editor.org/rfc/rfc9211))
is `omnivoice; hit` or `omnivoice; fwd=miss`. A hit answers at once, also
while another request is being read. A request with an empty `instruct`
never comes from the cache.

The answer has no `Cache-Control`: it is the answer of a `POST`, which no
browser or proxy keeps. The page of classla serves the mp3 to the browser
with a `GET` that the browser keeps (`../classla/README.md`, "Listen").

An error is JSON with `detail` and `code`: `unknown-model` (404),
`unknown-language` (422), `empty-text` (422), `bad-instruct` (422, and
`detail` names the instruct; the log of the server lists the valid items). A
text has at most 4000 characters.

## Voice

A request with no `instruct` clones a reference clip: `voices/<language>.wav`
when the language has one, else `voices/default.wav`, else it gets
`OMNIVOICE_INSTRUCT`. A request with an `instruct` never uses a clip.

The clips are there because a description alone fails on short texts. The
OmniVoice README says that voice design "is trained on Chinese and English
data only", and its tips say that "the model may not reliably generate short
audio clips (e.g., 1–2 seconds) without reference audio". In Croatian, a
sentence of two seconds with the default instruct came out as clicks or
silence for half of the seeds, and the library always uses the same seed (42),
so a text that fails, fails each time. The same sentence cloned from a clip
was speech for every seed. Longer texts (five seconds and up) were speech in
every mode.

The model copies the accent of the clip: "In cross-lingual voice cloning …
the generated speech will carry an accent from the reference audio's
language." So a clip is per language, spoken in that language.
`voices/hr.wav` is a Croatian speaker and `voices/it.wav` an Italian one; a
language with no clip of its own gets the accent of `default.wav`. The Italian
clip is 17 seconds, over the 10 below, so each Italian request encodes more
and may clone a little worse.

A clip is a 24 kHz mono 16-bit WAV of 3 to 10 seconds (longer ones slow down
each request and, upstream says, clone worse), with its exact transcript in
the `.txt` of the same name. The server encodes each clip once, when it loads
a model, and a clip that is not such a WAV or has no transcript stops the
start. To make one from a recording, cut one sentence and convert it:

```bash
ffmpeg -i recording.m4a -ss 0.7 -to 11.45 -ac 1 -ar 24000 -sample_fmt s16 \
  -map_metadata -1 -bitexact omnivoice_server/voices/hr.wav
```

`ffmpeg -i recording.m4a -af silencedetect=noise=-35dB:d=0.35 -f null -`
lists the pauses, to find where the sentence ends. The WAVs are in git lfs
(`.gitattributes`): a clone without `git lfs pull` has small text pointers in
their place, and the server refuses to start with them.

`instruct` describes the voice, and the model only takes its own items, with
`, ` between them. The English items are: `female`, `male`; `child`,
`teenager`, `young adult`, `middle-aged`, `elderly`; `very low pitch`,
`low pitch`, `moderate pitch`, `high pitch`, `very high pitch`; `whisper`;
and the accents `american`, `australian`, `british`, `canadian`, `chinese`,
`indian`, `japanese`, `korean`, `portuguese`, `russian`, each with ` accent`.
There is a Chinese list too, with a full-width comma between the items. In a
language with no clip, the default is `OMNIVOICE_INSTRUCT`. With an empty
`instruct`, the model picks a voice itself; the seed is always 42, so it
picks the same one for the same text.

`GET /healthz` answers at once, also during the load of the model, with the
models that are in memory: `{"status": "ok", "loaded": ["Serveurperso/OmniVoice-GGUF"]}`.
It gets no access line in the log: the health check of compose calls it
every few seconds.

## GPU

The library loads every ggml backend in the image and takes the best device:
`Vulkan0` when the container sees a GPU, else the CPU. The log of the start
names it: `[Load] LM backend: Vulkan0`. The compose file passes `/dev/dri`
to the container, as it does for the llamacpp service; the image runs as uid
1000 and `keep-id` maps that to your user, whose logind ACL opens the
device. The Mesa drivers in the image cover AMD (RADV) and Intel (ANV).
`GGML_BACKEND=CPU` in the environment forces the CPU.

## Language codes

A code is the id of OmniVoice: ISO 639-1 where the language has one (`hr`,
`de`, `fr`, `en`, `zh`, `fa`), else ISO 639-3. `docs/languages.md` in the
OmniVoice repo has the list, and `omnivoice_server/languages.py` has it in
code. A language name in English also works in the library, but this server
only accepts the codes from its list.

## Environment variables

- `OMNIVOICE_MODELS`: the Hugging Face repos of GGUFs that the server may
  download and load, with commas between them. Default
  `Serveurperso/OmniVoice-GGUF`. The first one is the default model, and it
  loads at the start. Another one loads on its first request. A request for
  an id outside the list gets 404. A repo must hold the two files
  `omnivoice-base-<quant>.gguf` and `omnivoice-tokenizer-<quant>.gguf`.
- `OMNIVOICE_QUANT`: the variant of the two files. Default `Q8_0` (656 MB +
  289 MB, the one omnivoice.cpp recommends). Also `Q4_K_M` (407 + 252 MB),
  `BF16` (1.23 GB + 373 MB) and `F32`.
- `OMNIVOICE_LIB`: the path of `libomnivoice.so`. Default
  `/opt/omnivoice/lib/libomnivoice.so`, where the image puts it. The ggml
  libraries must sit next to it.
- `OMNIVOICE_LANGUAGES`: the codes that `/v1/models` advertises and a request
  can use, with commas between them. Default: every code that the model
  knows. The compose file sets `hr,de,fr,it,en`. A code that the model does not
  know stops the start.
- `OMNIVOICE_VOICES`: the folder of the reference clips (see "Voice").
  Default `voices/` next to the code. Empty: no clips, so every request with
  no `instruct` gets `OMNIVOICE_INSTRUCT`.
- `OMNIVOICE_INSTRUCT`: the description of the voice for a request with no
  `instruct` in a language with no clip, from the items under "Voice", such
  as `female, low pitch, british accent`. Default
  `female, young adult, moderate pitch`.
- `OMNIVOICE_NUM_STEP`: the decoding steps of the model. Default `16`, the
  fast setting of the OmniVoice docs. Their quality default is `32`, which
  takes twice as long.
- `OMNIVOICE_CACHE`: how many of the last mp3s stay in memory. Default `16`,
  about 1 MB for short sentences. `0` keeps none.
- `OMNIVOICE_PRELOAD`: `1` (the default) loads the default model at the
  start, in a thread that holds the lock, so a request that comes early
  waits for the load. `0` loads it on the first request.
- `HF_HOME`: the Hugging Face cache. The image sets `/hf`. The download of
  the GGUFs goes there, so give it a volume.
- `GGML_BACKEND`: a device name of ggml (`Vulkan0`, `CPU`) instead of the
  best one, see "GPU".

## Running

With the classla page: `podman-compose up --build` in `../classla/`. The
`voice` service there binds `~/.cache/huggingface` of the host to `/hf`, so
the GGUFs download once and stay. The first build compiles omnivoice.cpp,
which takes a few minutes.

The image alone:

```bash
podman build -t omnivoice .
podman run --rm -p 8002:8002 -v ~/.cache/huggingface:/hf --userns=keep-id --device /dev/dri omnivoice
```

The image also has the `omnivoice-tts` CLI of omnivoice.cpp, for a check
without the server:

```bash
podman run --rm -it -v ~/.cache/huggingface:/hf --userns=keep-id omnivoice bash
echo "Dobar dan." | omnivoice-tts --model /hf/hub/models--Serveurperso--OmniVoice-GGUF/snapshots/*/omnivoice-base-Q8_0.gguf \
  --codec /hf/hub/models--Serveurperso--OmniVoice-GGUF/snapshots/*/omnivoice-tokenizer-Q8_0.gguf --lang hr -o /tmp/out.wav \
  --ref-wav omnivoice_server/voices/hr.wav --ref-text omnivoice_server/voices/hr.txt
```

`--ref-text` takes the path of the transcript, not the text. Without the two
`--ref-*` options it is voice design, with `--instruct`. `--seed` fixes the
seed; the CLI picks a random one, the server always has 42.

Alone, without the image, the server needs a local build of the library
(add `-DGGML_VULKAN=ON` for the GPU, with `glslc` and the Vulkan headers
installed):

```bash
git clone --recurse-submodules https://github.com/ServeurpersoCom/omnivoice.cpp.git
cmake -S omnivoice.cpp -B omnivoice.cpp/build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON -DOMNIVOICE_SHARED=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON
cmake --build omnivoice.cpp/build -j --target omnivoice
OMNIVOICE_LIB=$PWD/omnivoice.cpp/build/libomnivoice.so uv run uvicorn omnivoice_server.app:app --port 8002
```

The first request, or the start with the default `OMNIVOICE_PRELOAD`,
downloads the GGUFs into `~/.cache/huggingface/hub`.

The tests never load the library or a model:

```bash
uv run pytest
```

## Notes

- The GGUFs are the weights of omnivoice.cpp, which has its own ggml graph
  for the OmniVoice architecture. llama.cpp has no such architecture, so
  `llama-cpp-python` cannot load them. omnivoice.cpp exports a C99 API
  (`src/omnivoice.h`) for ctypes, and `native.py` is that binding.
- `native.py` mirrors the structs of `omnivoice.h` at the commit that the
  `Dockerfile` pins (`OMNIVOICE_CPP_COMMIT`), and `ABI_VERSION` is
  `OV_ABI_VERSION` of that header. To move to a newer commit: change the
  hash in the `Dockerfile`, compare `ov_init_params`, `ov_tts_params` and
  `ov_audio` with the classes in `native.py` (the header only grows fields at
  the end and then bumps `OV_ABI_VERSION`), and update `ABI_VERSION`. The
  library refuses a struct with a higher version than its own.
- The build uses `-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON`, so `libomnivoice.so`
  finds `libggml*.so` in its own folder after the copy into
  `/opt/omnivoice/lib`, and `native.py` loads one file.
- ggml compiles its CPU backend for the CPU of the build machine
  (`-march=native`). The image is for the machine that builds it;
  `-DGGML_NATIVE=OFF` in the `Dockerfile` makes a slower image that runs
  anywhere. The Vulkan shaders are SPIR-V and run on any GPU.
- The library uses half of the hardware threads. Most of its lines (the
  load, one line per decoding step, the timings) go straight to stderr, so
  they show in the log of the container. The lines that go through its log
  callback (`ov_log`) land in the `omnivoice.cpp` logger: INFO at DEBUG,
  warnings and errors as they are.
- `languages.py` is generated from `omnivoice.utils.lang_map.LANG_IDS` of the
  `omnivoice` Python package, the same table that the library carries
  (`ov_n_languages`). A static copy keeps `/v1/models` and the check at the
  start free of the library, so the tests need no build. To regenerate it,
  install `omnivoice` in a scratch venv and write the sorted `LANG_IDS`.
- The model returns float samples at 24 kHz, and `lameenc` encodes them to a
  64 kbit/s mono mp3 in the process, so the image needs no ffmpeg.
- The port shares the duration rule of the Python model (one estimate from
  the letters of the text, scaled by the speed of the reference clip when
  there is one), so it sounds the same as torch did, the failures of short
  texts without a clip included (see "Voice").
