import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langhelper_app/api/client.dart';
import 'package:langhelper_app/i18n/i18n.dart';
import 'package:langhelper_app/listen/player.dart';
import 'package:langhelper_app/main.dart';
import 'package:langhelper_app/providers.dart';

import 'api/fixtures.dart';

http.Response json(Object body, [int status = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

/// The mp3 of the fake voice service.
final mp3 = Uint8List.fromList([0x49, 0x44, 0x33]);

/// A server that answers with the saved responses of test/api/fixtures/.
class FakeServer {
  FakeServer({
    Future<http.Response> Function(http.Request request)? classify,
    this.languagesReady,
    Map<String, dynamic>? speech,
    Future<http.Response> Function(http.Request request)? speechAudio,
  }) : classify = classify ?? ((_) async => json(fixture('classify.json'))),
       speech =
           speech ?? {'available': false, 'model': '', 'languages': <String>[]},
       speechAudio =
           speechAudio ??
           ((_) async => http.Response.bytes(
             mp3,
             200,
             headers: {'x-voice-model': 'k2-fsa/OmniVoice'},
           ));

  /// The answer of POST /api/v1/classify.
  Future<http.Response> Function(http.Request request) classify;

  /// The list of languages waits for this.
  Future<void>? languagesReady;

  /// The body of GET /api/v1/speech: no voice service by default.
  Map<String, dynamic> speech;

  /// The answer of GET /api/v1/speech/audio.
  Future<http.Response> Function(http.Request request) speechAudio;

  /// The bodies of the classify requests, in order.
  final classified = <Map<String, dynamic>>[];

  /// The query of each request for a sound, in order.
  final spoken = <Map<String, String>>[];

  /// The players that the app made, in order.
  final players = <FakePlayer>[];

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
      case '/api/v1/speech':
        return json(speech);
      case '/api/v1/speech/audio':
        spoken.add(request.url.queryParameters);
        return speechAudio(request);
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

/// A player that keeps what the app asks of it.
class FakePlayer implements Player {
  /// The sounds, in order.
  final loaded = <Uint8List>[];
  final _playing = StreamController<bool>.broadcast();
  bool _isPlaying = false;
  int plays = 0;

  @override
  Future<Duration?> load(Uint8List mp3) async {
    loaded.add(mp3);
    return const Duration(seconds: 2);
  }

  @override
  void play() {
    plays++;
    _playing.add(_isPlaying = true);
  }

  @override
  void pause() => _playing.add(_isPlaying = false);

  @override
  void seek(Duration position) {}

  /// The state now, then each change, as the stream of just_audio.
  @override
  Stream<bool> get playing async* {
    yield _isPlaying;
    yield* _playing.stream;
  }

  @override
  Stream<Duration> get position => const Stream.empty();

  @override
  Future<void> dispose() => _playing.close();
}

/// The app on [server], in [i18n] (English by default).
Widget appOn(FakeServer server, {I18n? i18n}) => ProviderScope(
  overrides: [
    apiProvider.overrideWithValue(server.api),
    newPlayerProvider.overrideWithValue(() {
      final player = FakePlayer();
      server.players.add(player);
      return player;
    }),
  ],
  child: LanghelperApp(i18n: i18n ?? english()),
);

/// An answer that never comes, for the Cancel button.
Future<http.Response> never(http.Request request) =>
    Completer<http.Response>().future;
