import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langhelper_app/api/client.dart';
import 'package:langhelper_app/i18n/i18n.dart';
import 'package:langhelper_app/main.dart';
import 'package:langhelper_app/providers.dart';

import 'api/fixtures.dart';

http.Response json(Object body, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

/// A server that answers with the saved responses of test/api/fixtures/.
class FakeServer {
  FakeServer({
    Future<http.Response> Function(http.Request request)? classify,
    this.languagesReady,
  }) : classify = classify ?? ((_) async => json(fixture('classify.json')));

  /// The answer of POST /api/v1/classify.
  Future<http.Response> Function(http.Request request) classify;

  /// The list of languages waits for this.
  Future<void>? languagesReady;

  /// The bodies of the classify requests, in order.
  final classified = <Map<String, dynamic>>[];

  Future<http.Response> _answer(http.Request request) async {
    switch (request.url.path) {
      case '/api/v1/languages':
        await languagesReady;
        return json(fixture('languages.json'));
      case '/api/v1/status':
        return json(fixture('status.json'));
      case '/api/v1/classify':
        classified.add(jsonDecode(request.body) as Map<String, dynamic>);
        return classify(request);
    }
    return json({'detail': 'Not Found'}, 404);
  }

  late final api = Api(
    base: Uri.parse('https://example.fly.dev/'),
    newClient: () => MockClient(_answer),
    onUnauthorized: () => fail('no 401 here'),
  );
}

I18n english() => I18n(
  locale: 'en',
  catalogs: [Catalog('en', File(bundledCatalog).readAsStringSync())],
);

/// The app on [server], in [i18n] (English by default).
Widget appOn(FakeServer server, {I18n? i18n}) => ProviderScope(
  overrides: [apiProvider.overrideWithValue(server.api)],
  child: LanghelperApp(i18n: i18n ?? english()),
);

/// An answer that never comes, for the Cancel button.
Future<http.Response> never(http.Request request) =>
    Completer<http.Response>().future;
