# Moving the page to Flutter

A plan for replacing `static/` with a Flutter web app in `app/`, as the first
step towards an Android/iOS app. Step 1 is done: `app/` is a blank app.

## Why Flutter, and what it changes

`static/` is about 1,620 lines of plain JS in seven files, plus about 200
lines of HTML and 200 of CSS, with no build step: the Breakdown, Flashcards,
Progress and Audio lessons tabs, the "explain with AI" panel, the Listen panel
(the voice service of the server reads a text), Fluent catalogs that the
backend serves, and a web app manifest. Flutter (3.47 stable, September
2026, `flutter build web --wasm`) gives one Dart codebase for the web page and
for a native app. Jaspr renders real HTML from Dart and would keep the CSS and
the Playwright tests, but its UI code cannot become the mobile app; wrapping
the PWA (Capacitor, TWA) gives a store listing with no Dart at all. The choice
is Flutter, replacing `static/` outright, and the login stays as it is: the
Flutter page is on the same origin, so the cookie session keeps working.

Flutter web draws on a canvas. There is no DOM of chips, no `<svg>` for the
curves and no CSS. That decides most of the plan:

- Every Playwright assertion on selectors and attributes in
  `tests/test_browser_breakdown.py` and `tests/flashcards/test_browser.py`
  (about 560 lines) is rewritten. Playwright stays as the browser driver,
  because it is already in pytest and takes screenshots. It finds widgets
  through the semantics tree: after `SemanticsBinding.instance.ensureSemantics()`
  at startup, Flutter mirrors the tree into `flt-semantics` DOM nodes with
  roles and `aria-label`, so `get_by_role` and `get_by_label` work. `get_by_text`
  and CSS selectors do not.
- The curves get a golden widget test (`matchesGoldenFile`), the pixel-exact
  check, and Playwright screenshots for eyes.
- Dark mode is `ThemeMode.system` instead of `prefers-color-scheme`; Playwright
  tests it with `color_scheme="dark"`.
- Flutter web fetches glyphs from fonts.gstatic.com and CanvasKit from Google
  at run time. The tests forbid the network, and the page shows the accent
  letters ȁ ȃ and right-to-left scripts, so the app bundles Noto Sans and is
  built with `--no-web-resources-cdn`.
- The address of a tab becomes `/#/cards` (the hash strategy of Flutter)
  instead of `#cards`. `?locale=hr` stays.
- `@fluent/bundle` from jsDelivr goes away. `package:fluent` (pub.dev, a Dart
  Fluent runtime) formats the same `.ftl` files the backend already serves.

Trade-offs to accept: text needs an explicit `SelectionArea` to be copyable;
the first paint is heavier (CanvasKit is about 1.5 MB) than the current page;
a wasm build takes about a minute per iteration.

## Layout

```
web/
  app/                     new Flutter project (flutter create --platforms web --project-name langhelper_app)
    pubspec.yaml           the packages of "Libraries" below
    lib/
      main.dart            ensureSemantics(), theme, router (/, /cards, /progress, /audio, /audio/:course/:lesson), locale bootstrap
      api/client.dart      one class per endpoint group; same-origin http; 401 -> reload to /auth/login
      api/models.dart      the response models of schemas.py that the page reads: Word, Sentence, ClassifyResponse,
                           LanguageInfo, Deck, NextCard, AnswerResponse, StatsResponse, FlashcardUser,
                           ExplainQuestion, SpeechInfoResponse, AudioCourse, AudioLesson, AudioLine
      i18n/                Fluent bundle loading (/api/v1/locales, ui.ftl), t()/tOr(), bundled English fallback
      breakdown/           form, debounce, cancel, chips, detail table, dictionary links
      links/link_layer.dart Stack + CustomPaint that draws the curves
      listen/              the Listen panel: one button per readable text, plays the mp3 of the server
      flashcards/          deck tree, card view, answer and diff, ratings, media, read aloud
      explain/             questions panel
      progress/            stats table and the two bar charts
      audio_lessons/       course list with progress, lesson view, player, script
    web/
      index.html, manifest.json, icon*.{svg,png}   from static/, same file names so OPEN_PATHS holds
    assets/fonts/NotoSans-*.ttf
    test/                  widget and golden tests (flutter test)
    test/goldens/*.png
  static/                  deleted
  tlhelper/app.py          STATIC_DIR default -> ../app/build/web; COOP/COEP headers; routes unchanged
  tests/conftest.py        no CDN route; browser tests skip when app/build/web is missing
  tests/*browser*.py       rewritten against the semantics tree
  tests/shot.py            one ad-hoc screenshot
  Dockerfile               multi-stage: flutter build, then the python image copies app/build/web
  README.md                building the app, screenshots, tab addresses
.dockerignore              lets web/app in, but not its build/ and .dart_tool/
.github/workflows/tests.yml  a Flutter job: analyze, test, build; the browser tests use its build
```

Serving keeps its shape. `GET /` returns `build/web/index.html` (`app.py:355-357`)
and `/static` mounts `build/web` (`app.py:253`). The app is built with
`--base-href /static/`, so `flutter_bootstrap.js`, `main.dart.wasm`,
`canvaskit/`, `manifest.json` and the icons resolve under `/static/`.
`OPEN_PATHS` in `auth.py:39-50` stays as it is because the icon and manifest
names stay, and Chrome on Android installs the page as before.

## Libraries

Each package is a common choice for its job, and most are from the Flutter
or Dart team.

| Job | Package | Why |
| --- | --- | --- |
| Routing | `go_router` | From the Flutter team. Hash addresses and deep links. |
| HTTP | `http` | From the Dart team. `close()` on a client cancels its request. |
| JSON models | `json_serializable`, `json_annotation` | The standard code generator for JSON. |
| State | `flutter_riverpod` | `AsyncValue` holds the load, error and cancel states of the many requests. |
| Settings | `shared_preferences` | From the Flutter team. |
| Links | `url_launcher` | From the Flutter team. Opens the dictionary links in a new tab, and in the browser of a native app. |
| UI text | `fluent` | A Dart runtime of Project Fluent, for the `.ftl` files of the backend. `fluent_flutter` is newer (0.1), and is the fallback. |
| Sound | `just_audio` | A Flutter Favorite. Seek, speed and a position stream, on the web too. |
| Seek bar | `audio_video_progress_bar` | A ready bar with the position, the buffer and seek. |
| Read aloud with no server voice | `flutter_tts` | Uses `speechSynthesis` of the browser on the web. |
| Bar charts | `fl_chart` | The two 90-day charts of the Progress tab. |
| Golden tests | `flutter_test` (`matchesGoldenFile`) | Built in. Fonts draw a little differently on each OS, so the goldens are made and checked on Linux only. |
| Lints | `flutter_lints` | The default set of `flutter create`. |
| Native app (later) | `flutter_appauth`, `flutter_secure_storage`, `audio_service` | The login through the system browser, the tokens, and a lesson that plays with the screen off. |

## Steps

### 1. Scaffold and serve an empty app

Done (#26). README, "The Flutter app", has the commands.

- `flutter create app --platforms web --project-name langhelper_app` inside
  `web/`. Copy `manifest.json` and the icons from `static/` to `app/web/`.
  Write `app/web/index.html` with the theme colour, the viewport and the
  manifest link.
- Add Noto Sans, Noto Sans Arabic and Noto Sans Hebrew to `assets/fonts/`.
  Noto Sans is the theme font, and the other two are its fallbacks.
- `app.py`: a middleware sets `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: credentialless` on HTML responses.
  Multithreaded skwasm needs them; without them Flutter runs single-threaded.
  The default `STATIC_DIR` stays `static/` until step 13.
- Dockerfile: the build context is the repository root. A stage `app` from
  `debian:trixie-slim` downloads the Flutter archive of `FLUTTER_VERSION`,
  checks its SHA-256, copies `web/app/` to `/src/app` and runs
  `flutter build web --wasm --no-web-resources-cdn --base-href /static/`.
  `ghcr.io/cirruslabs/flutter` has no tag after 3.44.0. The python stage
  copies the build to `/app/flutter`, next to `static/` in `/app/static`.
  `STATIC_DIR` chooses, and the image sets `/app/static`. The version must
  equal the local `flutter --version`.
- The root `.dockerignore` lets `web/app` in, but not `web/app/build`,
  `web/app/.dart_tool` or `web/app/test/goldens`.
- `tests/test_browser_app.py`: with `STATIC_DIR` at the build, the blank app
  loads at `/`, the page is cross-origin isolated, and there is no request
  outside the origin (Playwright `page.on("request")`).

### 2. CI

Done. The `dart` job of `.github/workflows/tests.yml` runs `flutter test`
and the web build with `subosito/flutter-action` at `FLUTTER_VERSION` of the
Dockerfile, and uploads `app/build/web`. prek runs `dart format` and
`flutter analyze` (`app/.pre-commit-config.yaml`). The `tests` job downloads
the build and installs the Playwright Chromium. It runs the web tests, then
`tests/test_browser_app.py` with `STATIC_DIR` at the build, so no browser
test skips.

### 3. API client and models

Done (#28). README, "The API client and the models", has the commands.

Port the response shapes from `tlhelper/schemas.py` (`Word` at 42-98,
`LanguageInfo` at 142-166, the audio lesson models at 396-433) and the request
bodies from `app.py:327-352` (`ClassifyRequest`), `flashcards/routes.py`,
`explain/` and `audio_lessons/routes.py`. Errors are
`{detail, code?, params?}`; map `code` to the Fluent message `error-{code}` as
`breakdown.js` does. Cancel: one `http.Client` per classify request, and
`close()` on cancel, supersede or timeout.

A test reads `/openapi.json` and checks that each Dart model has the fields of
its schema, so a new key in `schemas.py` with no Dart field fails CI.

### 4. i18n

Done (#29). README, "The text of the app", has the details.

Load `/api/v1/locales` and `/api/v1/locales/{code}/ui.ftl`. Choose the locale
as `i18n.js:91-160` does: `?locale=`, then the `shared_preferences` key
`langhelper.locale`, then the browser locale. Set `Directionality` from
`direction`. Bundle `tlhelper/languages/english/ui.ftl` as an asset for the
fallback. A unit test formats every message id of the three catalogs with
`package:fluent`, to catch syntax it does not support.

### 5. Breakdown tab

Done (#30). README, "The Breakdown tab", has the details.

The form: language dropdown, source radios, text field with a 500 ms debounce
and Ctrl/Cmd+Enter through `CallbackShortcuts`, heavy, nonstandard, translate,
time limit, cancel. The models banner polls `/api/v1/status`. Chips use the
UPOS palette from `breakdown.js:6-24` and the feature note from lines 99-127.
A problem gets `TextDecoration.underline` with `TextDecorationStyle.wavy`.
Selection opens the detail table (lines 150-209). The legend and the accents
legend. Form state in `shared_preferences` (`langhelper.entry`, `langhelper.heavy`).
The result sits in a `SelectionArea`.

The page keeps these settings under the keys `classla.*` in localStorage. On
the web, `shared_preferences` adds the prefix `flutter.` to each key, so it
cannot read the old keys. The saved settings reset one time.

### 6. Link layer: the curves

Done (#31). README, "The link layer", has the details.

`LinkLayer` is a `Stack`: the sentences (a `Column` of `Wrap`s of chips, each
chip with a `GlobalKey`) and a
`Positioned.fill(IgnorePointer(CustomPaint(painter: LinkPainter)))`. After
each frame (`addPostFrameCallback`) it reads the `RenderBox` offset of every
linked chip relative to the layer. The painter draws `Path.cubicTo` from the
bottom centre of the upper chip to the top centre of the lower one with
`bend = max(24, (y2 - y1) / 2)`, as in `breakdown.js:255-280`. Guesses are
dashed and the links of the selected chip are thick. A `LayoutBuilder` around
the stack repaints on resize. The breakdown and the card view both use it
(`flashcards.js:210, 317`).

### 7. Listen panel

Done (#32). README, "The Listen panel", has the details.

It replaces `listen.js`. Read `/api/v1/speech` one time. With no voice
service, or no text that the service can read, the panel does not show. Each
readable text (the entry, its translation) gets a button with the name of its
language. A click gets `/api/v1/speech/audio?text=…&language=…` and plays it
with `just_audio`. It is a GET, so the browser cache answers a repeat. The
buttons are disabled while the request runs, and the timeout is 190 s, a
little more than `TLHELPER_VOICE_TIMEOUT`. The note shows the model from the
`x-voice-model` header. The same texts again keep the sound on the panel. The
text goes to the voice service, so a request goes out only on a click.

### 8. Flashcards tab

The deck tree with counts, the card view, `Image.network` for pictures,
`just_audio` for clips (the first one autoplays), the typed answer, the diff
(equal, delete and insert spans), the other answers, ratings 1-4 with the
keys 1-4, the next due time, "Read it aloud", next card. `go_router` keeps
the tab in the address.

"Read it aloud" uses the voice service of the server, as the Listen panel
does, when `/api/v1/speech` has the language. Otherwise it uses `flutter_tts`,
which uses the voices of the browser, and only for a language with `speech`.
With neither, the button does not show.

### 9. Explain panel and Progress tab

Explain: `/api/v1/explain/questions`, one button per question, the context
field, a 60 s timeout, under the breakdown and under an answered card.
Progress: the user selector (admin), the stats table and the two 90-day bar
charts with `fl_chart`.

### 10. Audio lessons tab

It replaces `audio_lessons.js`. `/#/audio` lists the courses of
`/api/v1/audio-lessons` and their lessons in order.
`/#/audio/<course>/<lesson>` shows the title, the grammar note, the player and
the script. The script has the name of each speaker and a line for each
pause. The narrator lines are English, and the others are in the study
language. A lesson with `audio: "none"` has no player. A lesson with `"stale"`
or `"none"` shows the note of its state.

The player is `just_audio` with the mp3 of
`/api/v1/audio-lessons/<course>/<lesson>.mp3` and a seek bar from
`audio_video_progress_bar`. The route answers a Range request, so seek works.
The buttons are play/pause, back 10 s, forward 10 s, and the speeds 0.75×, 1×
and 1.25×. Space plays and pauses, and ← and → go back and forward 10 s.
Each button has a `Semantics` label.

### 11. Audio lesson progress

The server keeps how far each user is through each lesson, so the progress
follows the user to another device and to a native app. A local run keeps it
for the user `local`, as the flashcards do. This part of the backend needs no
Flutter, and can come first.

- `flashcards.db` gets the table
  `audio_progress(user, course, lesson, position, duration, finished_at)`,
  with the key `(user, course, lesson)`. Positions are in seconds.
- `PUT /api/v1/audio-lessons/{course}/{lesson}/progress` takes
  `{position, duration}` for `current_user`. It sets `finished_at` the first
  time that the position is near the end, and keeps it after that.
- `GET /api/v1/audio-lessons` adds `position`, `duration` and `finished` to
  each lesson (`AudioLesson` in `schemas.py`).

The tab shows a thin progress bar and the percentage for each lesson that the
user started, and a ✓ for a finished one. Each course has a "Continue" button
for the first lesson that is not finished. The player starts at the saved
position, and saves the position every 10 s while it plays, on pause, at the
end, and when the user leaves the lesson.

### 12. Tests and screenshots

- Golden tests in `app/test/`: the link layer with a fixed fake classification
  (two sentences, links and guesses, one selected chip), a chip row, the diff,
  the bar charts. `flutter test` compares with `test/goldens/*.png`;
  `flutter test --update-goldens` rewrites them. The goldens are plain PNGs.
- Playwright in pytest: keep the server, error-collecting and `--screenshots`
  fixtures of `conftest.py`, remove the CDN fixture, and add a session fixture
  that skips when `app/build/web/index.html` is missing. Rewrite the browser
  tests with `get_by_role` and `get_by_label`, and add tests for the Audio
  lessons tab and the Listen panel. Give the key widgets an explicit
  `Semantics(label:)`, so the tests and screen readers use the same names:
  `chip: <word> <upos>`, `links: N`, the player buttons.
- Keep `tests/test_auth.py` and `tests/test_locales.py`. `test_auth.py:120-125`
  checks that `/static/js/breakdown.js` needs a login. That file goes away, so
  the check uses a file of the Flutter build.

### 13. Remove `static/`, update README

Delete `static/` and its lines in the root `.dockerignore`. The Dockerfile
copies the Flutter build to `/app/static` in place of `/app/flutter`, and the
default `STATIC_DIR` of `app.py` becomes `app/build/web`. In the README,
update the `static/` rows of "Files", "Install on Android" (Chrome now
installs from `app/web/manifest.json`, same address) and "Running locally"
for the new commands. Note the tab address change. `AGENTS.md` and the root
`README.md` say that the page is plain JS with no build step; change that too.

## Pictures of the page, for a coding loop

These are the commands for checking a drawing, such as the curves, without a
person looking at a browser. They go into README under "Running locally" when
the app exists.

1. Build: `cd web/app` and
   `flutter build web --wasm --no-web-resources-cdn --base-href /static/`.
   About a minute. `flutter build web` without `--wasm` is faster for a check.
2. Pictures of every browser test:
   `uv run pytest tests/test_browser_breakdown.py --screenshots=shots` writes
   one full-page PNG per test to `shots/`. Open them with the Read tool and
   compare the curves with `app/test/goldens/link_layer.png`.
3. One picture, no test: `uv run python tests/shot.py "Ovo je rečenica." --translate --out shot.png`
   starts the server as `conftest.py` does, opens the page, types the text,
   waits for the chips and saves the picture. `--deck NAME` does the same for
   a card. `--dark` for the dark theme.
4. Pixel-exact: `flutter test`. On a failure the diff images land in
   `app/test/failures/`.

## Verification of the whole change

- `flutter analyze` and `flutter test` clean in `web/app`.
- `uv run pytest` green, with Chromium and with the network blocked.
- `docker compose up --build`, then the four tabs by hand: translation
  curves, Listen, a picture card with audio, an audio lesson (seek, back
  10 s, resume after a reload), dark mode, `?locale=hr`, a right-to-left
  language.
- `fly deploy . --config web/fly.toml --dockerfile web/Dockerfile --ha=false`
  from the repository root: the login redirect works, the manifest and icons
  open without a session, Chrome on Android offers to install.

## Later: a native app

The API only has the cookie session that the redirect login sets
(`auth.py:86-112`). For Android and iOS: `flutter create --platforms
android,ios`, log in through the system browser with `flutter_appauth`
against Pocket ID (already a public PKCE client), and add a bearer token path
in `auth.py` next to the cookie. The API client takes its base address from
`--dart-define=API_BASE`, and the backend allows CORS for that origin. The
tokens stay in `flutter_secure_storage`. An audio lesson plays with the screen
off through `audio_service`, with lock-screen controls. The UI code does not
change.

Local toolchain today: Flutter 3.47.5, Dart 3.13.4. `flutter doctor` lacks
the Android SDK, Chrome and the Linux desktop libraries; none of them is
needed for `flutter build web`. `CHROME_EXECUTABLE` can point at Playwright's
Chromium for `flutter run -d chrome`.
