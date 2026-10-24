import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langhelper_app/api/client.dart';
import 'package:langhelper_app/flashcards/voices.dart';
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
    Map<String, dynamic>? decks,
    List<Map<String, dynamic>>? next,
    Future<http.Response> Function(http.Request request)? answer,
    Map<String, dynamic>? questions,
    Future<http.Response> Function(http.Request request)? explain,
    Map<String, dynamic>? users,
    Future<http.Response> Function(http.Request request)? stats,
    Future<http.Response> Function(http.Request request)? audioCourses,
    Future<http.Response> Function(http.Request request)? audioLesson,
  }) : audioCourses =
           audioCourses ?? ((_) async => json(fixture('audio_lessons.json'))),
       audioLesson =
           audioLesson ?? ((_) async => json(fixture('audio_lesson.json'))),
       classify = classify ?? ((_) async => json(fixture('classify.json'))),
       questions = questions ?? fixture('questions.json'),
       explain = explain ?? ((_) async => json(fixture('explain.json'))),
       users = users ?? fixture('users.json'),
       stats = stats ?? ((_) async => json(fixture('stats.json'))),
       speech =
           speech ?? {'available': false, 'model': '', 'languages': <String>[]},
       speechAudio =
           speechAudio ??
           ((_) async => http.Response.bytes(
             mp3,
             200,
             headers: {'x-voice-model': 'k2-fsa/OmniVoice'},
           )),
       decks = decks ?? fixture('decks.json'),
       next = next ?? [fixture('next.json'), fixture('next_done.json')],
       answer = answer ?? ((_) async => json(fixture('answer.json')));

  /// The answer of POST /api/v1/classify.
  Future<http.Response> Function(http.Request request) classify;

  /// The list of languages waits for this.
  Future<void>? languagesReady;

  /// The body of GET /api/v1/speech: no voice service by default.
  Map<String, dynamic> speech;

  /// The answer of GET /api/v1/speech/audio.
  Future<http.Response> Function(http.Request request) speechAudio;

  /// The body of GET /api/v1/decks.
  Map<String, dynamic> decks;

  /// The answers of GET /api/v1/decks/{id}/next, in order. The last one
  /// stays.
  List<Map<String, dynamic>> next;

  /// The answer of POST /api/v1/cards/{id}/answer.
  Future<http.Response> Function(http.Request request) answer;

  /// The body of GET /api/v1/explain/questions: no AI service by default.
  Map<String, dynamic> questions;

  /// The answer of both explain routes.
  Future<http.Response> Function(http.Request request) explain;

  /// The body of GET /api/v1/flashcards/users.
  Map<String, dynamic> users;

  /// The answer of GET /api/v1/flashcards/stats.
  Future<http.Response> Function(http.Request request) stats;

  /// The answer of GET /api/v1/audio-lessons.
  Future<http.Response> Function(http.Request request) audioCourses;

  /// The answer of GET /api/v1/audio-lessons/{course}/{lesson}.
  Future<http.Response> Function(http.Request request) audioLesson;

  /// The path of each request for a lesson, in order.
  final lessons = <String>[];

  /// The path and the body of each question to the AI, in order.
  final explained = <(String, Map<String, dynamic>)>[];

  /// The query of each request for the numbers, in order.
  final statsQueries = <Map<String, String>>[];

  /// The bodies of the answers and of the ratings, in order.
  final answers = <Map<String, dynamic>>[];
  final ratings = <Map<String, dynamic>>[];

  /// The query of each request for a card, in order.
  final nextQueries = <Map<String, String>>[];

  /// The voices of the browser.
  final voices = FakeVoices();

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
      case '/api/v1/decks':
        return json(decks);
      case '/api/v1/decks/1/next':
        nextQueries.add(request.url.queryParameters);
        final index = min(nextQueries.length, next.length) - 1;
        return json(next[index]);
      case '/api/v1/cards/1/answer':
        answers.add(jsonDecode(request.body) as Map<String, dynamic>);
        return answer(request);
      case '/api/v1/reviews/1/rating':
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        ratings.add(body);
        return json({
          'rating': body['rating'],
          'next_due': '2026-10-26T09:00:00+00:00',
        });
      case '/api/v1/explain/questions':
        return json(questions);
      case '/api/v1/explain' || '/api/v1/reviews/1/explain':
        explained.add((
          request.url.path,
          jsonDecode(request.body) as Map<String, dynamic>,
        ));
        return explain(request);
      case '/api/v1/flashcards/users':
        return json(users);
      case '/api/v1/flashcards/stats':
        statsQueries.add(request.url.queryParameters);
        return stats(request);
      case '/api/v1/audio-lessons':
        return audioCourses(request);
      case final path when path.startsWith('/api/v1/audio-lessons/'):
        lessons.add(path);
        return audioLesson(request);
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

  /// The sounds on the server, in order.
  final uris = <Uri>[];
  final _playing = StreamController<bool>.broadcast();
  final _position = StreamController<Duration>.broadcast();
  bool _isPlaying = false;
  int plays = 0;
  bool disposed = false;

  /// The length of each sound.
  Duration length = const Duration(seconds: 2);

  /// The places of each seek, and the speeds, in order.
  final seeks = <Duration>[];
  final speeds = <double>[];

  @override
  Duration currentPosition = Duration.zero;

  @override
  Future<Duration?> load(Uint8List mp3) async {
    loaded.add(mp3);
    return length;
  }

  @override
  Future<Duration?> loadUri(Uri uri) async {
    uris.add(uri);
    return length;
  }

  @override
  void play() {
    plays++;
    _playing.add(_isPlaying = true);
  }

  @override
  void pause() => _playing.add(_isPlaying = false);

  @override
  void seek(Duration position) {
    seeks.add(position);
    _position.add(currentPosition = position);
  }

  @override
  void setSpeed(double speed) => speeds.add(speed);

  /// The state now, then each change, as the stream of just_audio.
  @override
  Stream<bool> get playing async* {
    yield _isPlaying;
    yield* _playing.stream;
  }

  @override
  Stream<Duration> get position async* {
    yield currentPosition;
    yield* _position.stream;
  }

  @override
  Future<void> dispose() async {
    disposed = true;
    await _playing.close();
    await _position.close();
  }
}

/// Voices of a browser that keep what the app asks of them.
class FakeVoices implements BrowserVoices {
  @override
  bool available = true;

  /// What the voices say before the start, if not null.
  SpeakFailure? failure;

  /// The texts and their tags, in order.
  final spoken = <(String, String)>[];

  @override
  Future<void> speak(
    String text, {
    required String language,
    required String tag,
    required void Function(SpeakFailure failure) onError,
  }) async {
    if (failure case final failure?) throw failure;
    spoken.add((text, tag));
  }
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
    browserVoicesProvider.overrideWithValue(server.voices),
  ],
  child: LanghelperApp(i18n: i18n ?? english()),
);

/// An answer that never comes, for the Cancel button.
Future<http.Response> never(http.Request request) =>
    Completer<http.Response>().future;
