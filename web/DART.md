# Moving the page to Flutter

A plan for replacing `static/` with a Flutter web app in `app/`, as the first
step towards an Android/iOS app. Nothing here is built yet.

## Why Flutter, and what it changes

`static/` is about 1,760 lines of plain JS with no build step: the Breakdown,
Flashcards and Progress tabs, the "explain with AI" panel, Fluent catalogs that
the backend serves, and a web app manifest. Flutter (3.47 stable, September
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
  (about 440 lines) is rewritten. Playwright stays as the browser driver,
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
    pubspec.yaml           http, fluent, shared_preferences, audioplayers, flutter_tts, go_router
    lib/
      main.dart            ensureSemantics(), theme, router (/, /cards, /progress), locale bootstrap
      api/client.dart      one class per endpoint group; same-origin http; 401 -> reload to /auth/login
      api/models.dart      Word, Sentence, Classification, Translation, Deck, NextCard, Answer, Stats, LanguageInfo
      i18n/                Fluent bundle loading (/api/v1/locales, ui.ftl), t()/tOr(), bundled English fallback
      breakdown/           form, debounce, cancel, chips, detail table, dictionary links
      links/link_layer.dart Stack + CustomPaint that draws the curves
      flashcards/          deck tree, card view, answer and diff, ratings, media, speak
      explain/             questions panel
      progress/            stats table and the two bar charts
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
```

Serving keeps its shape. `GET /` returns `build/web/index.html` (`app.py:326`)
and `/static` mounts `build/web` (`app.py:228`). The app is built with
`--base-href /static/`, so `flutter_bootstrap.js`, `main.dart.wasm`,
`canvaskit/`, `manifest.json` and the icons resolve under `/static/`.
`OPEN_PATHS` in `auth.py:37-50` stays as it is because the icon and manifest
names stay, and Chrome on Android installs the page as before.

## Steps

### 1. Scaffold and serve an empty app

- `flutter create app --platforms web --project-name langhelper_app` inside
  `web/`. Move `manifest.json` and the icons from `static/` to `app/web/`.
  Write `app/web/index.html` with the theme colour, the viewport and the
  manifest link.
- Add Noto Sans to `assets/fonts/` and make it the theme font.
- `app.py`: default `STATIC_DIR` to `app/build/web`. Add a middleware that
  sets `Cross-Origin-Opener-Policy: same-origin` and
  `Cross-Origin-Embedder-Policy: credentialless` on HTML responses.
  Multithreaded skwasm needs them; without them Flutter runs single-threaded.
- Dockerfile: a stage `FROM ghcr.io/cirruslabs/flutter:3.47.5 AS web` that
  runs `flutter build web --wasm --no-web-resources-cdn --base-href /static/`,
  then `COPY --from=web /src/app/build/web /app/static`. The tag must equal
  the local `flutter --version`.
- Build, run uvicorn, and confirm the blank app loads at `/` with no request
  outside the origin (Playwright `page.on("request")` in a smoke test).

### 2. API client and models

Port the response shapes from `tlhelper/schemas.py` (`Word` at 42-97,
`LanguageInfo` at 142-192) and the request bodies from `app.py:298`
(classify), `flashcards/routes.py` and `explain/`. Errors are
`{detail, code?, params?}`; map `code` to the Fluent message `error-{code}` as
`breakdown.js` does. Cancel: one `http.Client` per classify request, and
`close()` on cancel, supersede or timeout.

### 3. i18n

Load `/api/v1/locales` and `/api/v1/locales/{code}/ui.ftl`. Choose the locale
as `i18n.js:91-160` does: `?locale=`, then the `shared_preferences` key
`classla.locale`, then the browser locale. Set `Directionality` from
`direction`. Bundle `tlhelper/languages/english/ui.ftl` as an asset for the
fallback. A unit test formats every message id of the three catalogs with
`package:fluent`, to catch syntax it does not support.

### 4. Breakdown tab

The form: language dropdown, source radios, text field with a 500 ms debounce
and Ctrl/Cmd+Enter through `CallbackShortcuts`, heavy, nonstandard, translate,
time limit, cancel. The models banner polls `/api/v1/status`. Chips use the
UPOS palette from `breakdown.js:6-24` and the feature note from lines 99-127.
A problem gets `TextDecoration.underline` with `TextDecorationStyle.wavy`.
Selection opens the detail table (lines 150-209). The legend and the accents
legend. Form state in `shared_preferences` (`classla.entry`, `classla.heavy`).
The result sits in a `SelectionArea`.

### 5. Link layer: the curves

`LinkLayer` is a `Stack`: the sentences (a `Column` of `Wrap`s of chips, each
chip with a `GlobalKey`) and a
`Positioned.fill(IgnorePointer(CustomPaint(painter: LinkPainter)))`. After
each frame (`addPostFrameCallback`) it reads the `RenderBox` offset of every
linked chip relative to the layer. The painter draws `Path.cubicTo` from the
bottom centre of the upper chip to the top centre of the lower one with
`bend = max(24, (y2 - y1) / 2)`, as in `breakdown.js:265-276`. Guesses are
dashed and the links of the selected chip are thick. A `LayoutBuilder` around
the stack repaints on resize. The breakdown and the card view both use it
(`flashcards.js:194, 296`).

### 6. Flashcards tab

The deck tree with counts, the card view, `Image.network` for pictures,
`audioplayers` for clips (the first one autoplays), the typed answer, the diff
(equal, delete and insert spans), the other answers, ratings 1-4 with the
keys 1-4, the next due time, `flutter_tts` for "Read it aloud" (hidden when
the language has no `speech`), next card. `go_router` keeps the tab in the
address.

### 7. Explain panel and Progress tab

Explain: `/api/v1/explain/questions`, one button per question, the context
field, a 60 s timeout, under the breakdown and under an answered card.
Progress: the user selector (admin), the stats table and the two 90-day bar
charts.

### 8. Tests and screenshots

- Golden tests in `app/test/`: the link layer with a fixed fake classification
  (two sentences, links and guesses, one selected chip), a chip row, the diff,
  the bar charts. `flutter test` compares with `test/goldens/*.png`;
  `flutter test --update-goldens` rewrites them. The goldens are plain PNGs.
- Playwright in pytest: keep the server, error-collecting and `--screenshots`
  fixtures of `conftest.py`, remove the CDN fixture, and add a session fixture
  that skips when `app/build/web/index.html` is missing. Rewrite the browser
  tests with `get_by_role` and `get_by_label`. Give the key widgets an
  explicit `Semantics(label:)`, so the tests and screen readers use the same
  names: `chip: <word> <upos>`, `links: N`.
- Keep `tests/test_auth.py` and `tests/test_locales.py`. Update the paths in
  `test_auth.py:121-126` if a built file name differs.

### 9. Remove `static/`, update README

Delete `static/`, the file table (README 43-49), the PWA section (833-860:
Chrome now installs from `app/web/manifest.json`, same address) and "Running
locally" (1011-1038) for the new commands. Note the tab address change.

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
- `podman-compose up --build`, then the three tabs by hand: translation
  curves, a picture card with audio, dark mode, `?locale=hr`, a right-to-left
  language.
- `fly deploy --ha=false`: the login redirect works, the manifest and icons
  open without a session, Chrome on Android offers to install.

## Later: a native app

The API only has the cookie session that the redirect login sets
(`auth.py:86-112`). For Android and iOS: `flutter create --platforms
android,ios`, log in through the system browser with `flutter_appauth`
against Pocket ID (already a public PKCE client), and add a bearer token path
in `auth.py` next to the cookie. The API client takes its base address from
`--dart-define=API_BASE`, and the backend allows CORS for that origin. The UI
code does not change.

Local toolchain today: Flutter 3.47.5, Dart 3.13.4. `flutter doctor` lacks
the Android SDK, Chrome and the Linux desktop libraries; none of them is
needed for `flutter build web`. `CHROME_EXECUTABLE` can point at Playwright's
Chromium for `flutter run -d chrome`.
