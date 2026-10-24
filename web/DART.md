# A native app

The page is a Flutter web app in `app/` (README.md, "The Flutter app"). This
is the plan for an Android and iOS app from the same code.

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
