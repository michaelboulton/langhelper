# Build from the repository root, which holds the uv workspace:
#   docker build -f tts/Dockerfile -t omnivoice .
#
# Stage 1: omnivoice.cpp as a shared library, from the pinned commit
# (README.md, "Notes"). The same base as the final stage, so the library
# links against the libc and libstdc++ that it runs on.
FROM python:3.12-slim AS build

ARG OMNIVOICE_CPP_COMMIT=8ab42195a05a9d48a3942b17568c1f3a876e133a

# glslc, the Vulkan headers and the SPIR-V headers: the ggml Vulkan backend
# compiles its shaders at build time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates \
        libvulkan-dev glslc spirv-headers \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git init --quiet . \
    && git remote add origin https://github.com/ServeurpersoCom/omnivoice.cpp.git \
    && git fetch --quiet --depth 1 origin "$OMNIVOICE_CPP_COMMIT" \
    && git checkout --quiet FETCH_HEAD \
    && git submodule update --init --depth 1

# $ORIGIN in the RUNPATH: the ggml libraries resolve from the folder of
# libomnivoice.so after the copy below. Vulkan and CPU backends both go in;
# the library picks the GPU when the container has one (README.md, "GPU").
# omnivoice-tts sits next to the libraries for the same $ORIGIN, and bin/ has
# a link to it.
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
        -DOMNIVOICE_SHARED=ON -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DGGML_VULKAN=ON \
    && cmake --build build --config Release -j "$(nproc)" --target omnivoice omnivoice-tts \
    && mkdir -p /opt/omnivoice/lib /opt/omnivoice/bin \
    && cp -a build/*.so* build/omnivoice-tts /opt/omnivoice/lib/ \
    && ln -s ../lib/omnivoice-tts /opt/omnivoice/bin/omnivoice-tts

# Stage 2: the server.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
COPY --from=build /opt/omnivoice /opt/omnivoice

# OpenMP for the ggml CPU backend; the Vulkan loader and the Mesa drivers
# (RADV for AMD, ANV for Intel) for the GPU.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libvulkan1 mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so a change to omnivoice_server/ does not reinstall
# them. uv reads the pyproject.toml of each workspace member, so web/ needs
# its file too.
COPY pyproject.toml uv.lock /app/
COPY web/pyproject.toml /app/web/
COPY tts/pyproject.toml /app/tts/
RUN UV_COMPILE_BYTECODE=1 uv sync --frozen --no-dev --package omnivoice-server --no-install-workspace --no-cache

COPY tts/omnivoice_server/ /app/omnivoice_server/

# Non-root. /hf is the Hugging Face cache: the GGUFs land there on the first
# request, or a volume brings them (docker-compose.yml at the repository root).
RUN useradd --create-home --uid 1000 omnivoice \
    && mkdir -p /hf && chown omnivoice:omnivoice /hf
USER omnivoice

ENV HOME=/home/omnivoice \
    PATH=/opt/omnivoice/bin:/app/.venv/bin:$PATH \
    HF_HOME=/hf \
    OMNIVOICE_LIB=/opt/omnivoice/lib/libomnivoice.so

EXPOSE 8002
CMD ["uvicorn", "omnivoice_server.app:app", "--host", "0.0.0.0", "--port", "8002"]
