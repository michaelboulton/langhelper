import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/client.dart';

/// The API of the server. main() and the tests set it.
final apiProvider = Provider<Api>((ref) => Api());

/// The settings of the user. On the web they are in localStorage, which can
/// be blocked, so each read and write can fail.
final preferencesProvider = Provider<SharedPreferencesAsync>(
  (ref) => SharedPreferencesAsync(),
);
