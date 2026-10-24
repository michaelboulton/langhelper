import 'package:web/web.dart' as web;

/// Load the login page. After the login, the server sends the browser back
/// to this address.
void goToLogin() {
  final location = web.window.location;
  final next = '${location.pathname}${location.search}${location.hash}';
  location.assign('/auth/login?next=${Uri.encodeQueryComponent(next)}');
}
