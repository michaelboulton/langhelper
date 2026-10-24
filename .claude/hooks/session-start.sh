#!/bin/bash
# SessionStart hook for Claude Code cloud sessions of langhelper, registered in
# .claude/settings.json. It installs fd, rg, the Flutter SDK of
# web/Dockerfile, the LFS files, the uv workspace, prek, and a Playwright
# Chromium under the name that uv.lock wants.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO="${CLAUDE_PROJECT_DIR:-$(pwd)}"
BIN=/usr/local/bin
FLUTTER_HOME="${FLUTTER_HOME:-/opt/flutter}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FD_VERSION=10.3.0
RG_VERSION=15.1.0

persist() {
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "$1" >> "$CLAUDE_ENV_FILE"
  fi
}

# fd and rg: static musl builds from the GitHub releases.
if ! command -v fd >/dev/null; then
  curl -fsSL "https://github.com/sharkdp/fd/releases/download/v${FD_VERSION}/fd-v${FD_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C "$TMP"
  install -m 755 "$TMP/fd-v${FD_VERSION}-x86_64-unknown-linux-musl/fd" "$BIN/fd"
fi
if ! command -v rg >/dev/null; then
  curl -fsSL "https://github.com/BurntSushi/ripgrep/releases/download/${RG_VERSION}/ripgrep-${RG_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C "$TMP"
  install -m 755 "$TMP/ripgrep-${RG_VERSION}-x86_64-unknown-linux-musl/rg" "$BIN/rg"
fi

# Flutter: the version and the SHA-256 of web/Dockerfile, so the session
# builds with the same SDK as the image.
FLUTTER_VERSION="$(sed -n 's/^ARG FLUTTER_VERSION=//p' "$REPO/web/Dockerfile")"
FLUTTER_SHA256="$(sed -n 's/^ARG FLUTTER_SHA256=//p' "$REPO/web/Dockerfile")"
if [ -n "$FLUTTER_VERSION" ]; then
  if ! grep -qx "$FLUTTER_VERSION" "$FLUTTER_HOME/.hook-version" 2>/dev/null; then
    curl -fsSL -o "$TMP/flutter.tar.xz" \
      "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
    echo "${FLUTTER_SHA256}  $TMP/flutter.tar.xz" | sha256sum -c -
    rm -rf "$FLUTTER_HOME"
    mkdir -p "$(dirname "$FLUTTER_HOME")"
    tar -xJf "$TMP/flutter.tar.xz" -C "$TMP"
    mv "$TMP/flutter" "$FLUTTER_HOME"
    rm "$TMP/flutter.tar.xz"
    echo "$FLUTTER_VERSION" > "$FLUTTER_HOME/.hook-version"
  fi
  git config --global --get-all safe.directory | grep -qx "$FLUTTER_HOME" \
    || git config --global --add safe.directory "$FLUTTER_HOME"
  export PATH="$FLUTTER_HOME/bin:$PATH"
  persist "export PATH=\"$FLUTTER_HOME/bin:\$PATH\""
  # The proxy refuses Google Analytics.
  flutter config --no-analytics >/dev/null
  dart --disable-analytics >/dev/null
  flutter precache --web
  if [ -f "$REPO/web/app/pubspec.yaml" ]; then
    flutter pub get --directory "$REPO/web/app"
  fi
fi

# The data files of the web tests, and the uv workspace (AGENTS.md).
# --all-groups: the dev groups of web/ and tts/ too, so `uv run` in a member
# folder installs nothing more.
git -C "$REPO" lfs pull
uv sync --all-packages --all-groups --directory "$REPO"
uv tool install prek >/dev/null

# Playwright: link the Chromium of /opt/pw-browsers under the revision that
# the locked playwright wants (AGENTS.md, "Commands").
BROWSERS_JSON="$(ls "$REPO"/.venv/lib/python3*/site-packages/playwright/driver/package/browsers.json 2>/dev/null | head -n 1)"
if [ -n "$BROWSERS_JSON" ] && [ -d /opt/pw-browsers ]; then
  LINKS="$HOME/.cache/pw-browsers"
  mkdir -p "$LINKS"
  for name in chromium chromium-headless-shell; do
    want="$(jq -r --arg n "$name" '.browsers[] | select(.name == $n) | .revision' "$BROWSERS_JSON")"
    folder="${name//-/_}"
    have="$(ls -d /opt/pw-browsers/"${folder}"-[0-9]* 2>/dev/null | sort -V | tail -n 1)"
    if [ -n "$want" ] && [ -n "$have" ]; then
      ln -sfn "$have" "$LINKS/${folder}-${want}"
    fi
  done
  persist "export PLAYWRIGHT_BROWSERS_PATH=\"$LINKS\""
fi
