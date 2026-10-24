# Build from the repository root, which holds the uv workspace:
#   docker build -f web/Dockerfile -t langhelper-web .

# The Flutter app (app/). The version must equal the local `flutter --version`.
# The SHA-256 is that of the archive in
# https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json
FROM debian:trixie-slim AS app
ARG FLUTTER_VERSION=3.47.5
ARG FLUTTER_SHA256=2132e990f236f8d22e7c6314b29a191a95b10d7cbcfec9b4e2e303d996652cbb
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git unzip xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/flutter.tar.xz \
        "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz" \
    && echo "${FLUTTER_SHA256}  /tmp/flutter.tar.xz" | sha256sum -c - \
    && tar -xJf /tmp/flutter.tar.xz -C /opt \
    && rm /tmp/flutter.tar.xz \
    && git config --global --add safe.directory /opt/flutter
ENV PATH=/opt/flutter/bin:$PATH
RUN flutter config --no-analytics && flutter precache --web
WORKDIR /src/app
COPY web/app/pubspec.yaml web/app/pubspec.lock /src/app/
RUN flutter pub get
COPY web/app/ /src/app/
RUN flutter build web --wasm --no-web-resources-cdn --base-href /static/

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first, so a change to tlhelper/ or static/ does not reinstall
# torch. The root pyproject.toml pins torch to the CPU-only wheel index. uv
# reads the pyproject.toml of each workspace member, so tts/ needs its file too.
COPY pyproject.toml uv.lock /app/
COPY web/pyproject.toml /app/web/
COPY tts/pyproject.toml /app/tts/
RUN UV_COMPILE_BYTECODE=1 uv sync --frozen --no-dev --package langhelper-web --no-install-workspace --no-cache

# The flashcard decks of the image. More decks can go in /data/decks.
COPY web/decks/ /app/decks/
COPY web/entrypoint.sh /app/
# With the data files of the languages (accents.db, glosses.db).
COPY web/tlhelper/ /app/tlhelper/
# STATIC_DIR chooses the page: /app/static (the JS page) or /app/flutter
# (README.md, "The Flutter app").
COPY web/static/ /app/static/
COPY --from=app /src/app/build/web /app/flutter/
RUN chmod +x /app/entrypoint.sh

# Non-root. Fly mounts the volume with the uid/gid of USER, so /data is writable.
RUN useradd --create-home --uid 1000 web \
    && mkdir -p /data && chown web:web /data
USER web

ENV HOME=/home/web \
    PATH=/app/.venv/bin:$PATH \
    DATA_ROOT=/data \
    STATIC_DIR=/app/static \
    PORT=8000

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
