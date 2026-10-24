import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langhelper_app/api/client.dart';
import 'package:langhelper_app/api/models.dart';

import 'fixtures.dart';

/// A MockClient that knows if it was closed.
class Tracked extends http.BaseClient {
  Tracked(this.inner);

  final http.Client inner;
  bool closed = false;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) =>
      inner.send(request);

  @override
  void close() => closed = true;
}

/// A JSON response with no charset, as the server sends it.
http.Response jsonResponse(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json'},
);

/// The messages of a catalog with two of the error messages.
String? messages(String id, Map<String, Object?> params) => switch (id) {
  'error-server' => 'Server: ${params['status']}.',
  'error-not-admin' => 'Not an admin.',
  _ => null,
};

const request = ClassifyRequest(
  text: 'Ona je je bila kod kuće.',
  language: 'hr',
);
const long = Duration(seconds: 30);

void main() {
  final page = Uri.parse('https://example.fly.dev/?locale=hr#/cards');

  /// An Api whose server is [handler]. Each new client goes into [clients].
  Api api(MockClientHandler handler, {List<Tracked>? clients}) => Api(
    base: page,
    newClient: () {
      final client = Tracked(MockClient(handler));
      clients?.add(client);
      return client;
    },
    onUnauthorized: () => fail('no 401 here'),
  );

  test('a request goes to the origin of the page, and reads UTF-8', () async {
    final requests = <http.Request>[];
    final result = await api((request) async {
      requests.add(request);
      return http.Response.bytes(
        utf8.encode(jsonEncode(fixture('classify.json'))),
        200,
        headers: {'content-type': 'application/json'},
      );
    }).breakdown.classify(request, timeout: long);
    expect(result.sentences.single.words[4].text, 'kod');
    expect(result.sentences.single.words.first.accent?.form, 'Òna');
    final sent = requests.single;
    expect(sent.method, 'POST');
    expect(sent.url.toString(), 'https://example.fly.dev/api/v1/classify');
    expect(sent.headers['content-type'], startsWith('application/json'));
    expect(jsonDecode(sent.body), request.toJson());
  });

  test('the query and the path of a request', () async {
    final urls = <String>[];
    final server = api((request) async {
      urls.add(request.url.toString());
      if (request.url.path.endsWith('/stats')) {
        return jsonResponse(fixture('stats.json'));
      }
      return jsonResponse(fixture('audio_lesson.json'));
    });
    await server.flashcards.stats(of: 'user 2');
    await server.audioLessons.lesson('it course', 3);
    expect(urls, [
      'https://example.fly.dev/api/v1/flashcards/stats?of=user+2',
      'https://example.fly.dev/api/v1/audio-lessons/it%20course/3',
    ]);
    expect(
      server.audioLessons.audio('it course', 3).toString(),
      'https://example.fly.dev/api/v1/audio-lessons/it%20course/3.mp3',
    );
    expect(
      server.resolve('/api/v1/decks/1/media/a.png').toString(),
      'https://example.fly.dev/api/v1/decks/1/media/a.png',
    );
  });

  test('the sound of a text, and the model of the header', () async {
    final server = api(
      (request) async => http.Response.bytes(
        [1, 2, 3],
        200,
        headers: {'content-type': 'audio/mpeg', 'x-voice-model': 'omni'},
      ),
    );
    final audio = await server.speech.audio('Bok', 'hr');
    expect(audio.bytes, [1, 2, 3]);
    expect(audio.model, 'omni');
  });

  group('errors', () {
    Future<ApiException> failure(http.Response response) async {
      try {
        await api((request) async => response).flashcards.users();
      } on ApiException catch (error) {
        return error;
      }
      throw StateError('no error');
    }

    test('a code is the message error-{code}', () async {
      final error = await failure(
        jsonResponse({
          'detail': 'Only an admin can see the cards of another user.',
          'code': 'not-admin',
          'params': <String, Object>{},
        }, 403),
      );
      expect(error.status, 403);
      expect(error.code, 'not-admin');
      expect(error.message(messages), 'Server: 403. Not an admin.');
    });

    test('with no message for the code, the detail', () async {
      final error = await failure(
        jsonResponse({
          'detail': 'the voice service did not answer in time',
          'code': 'voice-timeout',
          'params': <String, Object>{},
        }, 502),
      );
      expect(
        error.message(messages),
        'Server: 502. the voice service did not answer in time',
      );
      expect(
        error.message((id, params) => null),
        'The server returned 502. the voice service did not answer in time',
      );
    });

    test('a validation error or a body that is not JSON', () async {
      final invalid = await failure(
        jsonResponse({
          'detail': [
            {'type': 'string_too_short', 'loc': [], 'msg': '', 'input': ''},
          ],
        }, 422),
      );
      expect(invalid.message(messages), 'Server: 422.');
      final html = await failure(http.Response('<h1>Bad gateway</h1>', 502));
      expect(html.message(messages), 'Server: 502.');
    });

    test('the error of a translation', () {
      expect(
        codedMessage(messages, 'not-admin', {}, 'English'),
        'Not an admin.',
      );
      expect(codedMessage(messages, '', {}, 'English'), 'English');
      expect(
        codedMessage(messages, 'translator-busy', {}, 'English'),
        'English',
      );
    });

    test('a 401 loads the login page', () async {
      var logins = 0;
      final server = Api(
        base: page,
        newClient: () => MockClient(
          (request) async => jsonResponse({
            'detail': 'The login expired. Load the page again.',
          }, 401),
        ),
        onUnauthorized: () => logins++,
      );
      await expectLater(
        server.flashcards.decks(),
        throwsA(isA<ApiException>()),
      );
      expect(logins, 1);
    });
  });

  group('cancel', () {
    /// A server that answers only when [answer] completes.
    MockClientHandler waiting(Completer<void> answer) => (request) async {
      await answer.future;
      return jsonResponse(fixture('classify.json'));
    };

    Matcher canceled(CancelReason reason) => throwsA(
      isA<ApiCanceled>().having((error) => error.reason, 'reason', reason),
    );

    test('a newer classify cancels the one before', () async {
      final answer = Completer<void>();
      final clients = <Tracked>[];
      final server = api(waiting(answer), clients: clients);
      final first = server.breakdown.classify(request, timeout: long);
      final second = server.breakdown.classify(request, timeout: long);
      await expectLater(first, canceled(CancelReason.superseded));
      expect(clients.first.closed, isTrue);
      answer.complete();
      expect((await second).language, 'hr');
      expect(clients, hasLength(2));
      expect(clients.last.closed, isTrue);
    });

    test('the cancel button', () async {
      final clients = <Tracked>[];
      final server = api(waiting(Completer()), clients: clients);
      final call = server.breakdown.classify(request, timeout: long);
      server.breakdown.cancelClassify();
      await expectLater(call, canceled(CancelReason.cancel));
      expect(clients.single.closed, isTrue);
    });

    test('a timeout', () async {
      final clients = <Tracked>[];
      final server = api(waiting(Completer()), clients: clients);
      await expectLater(
        server.breakdown.classify(
          request,
          timeout: const Duration(milliseconds: 10),
        ),
        canceled(CancelReason.timeout),
      );
      expect(clients.single.closed, isTrue);
    });

    test('a timeout of another request', () async {
      final server = api(waiting(Completer()));
      await expectLater(
        server.explain.sentence(
          const ExplainSentenceRequest(
            question: 'meaning',
            locale: 'en',
            text: 'Bok',
            language: 'hr',
          ),
          timeout: const Duration(milliseconds: 10),
        ),
        canceled(CancelReason.timeout),
      );
    });

    test('a client that fails on close() still gives the reason', () async {
      final requests = StreamController<void>();
      final server = Api(
        base: page,
        newClient: () => ClosingClient(requests),
        onUnauthorized: () => fail('no 401 here'),
      );
      final call = server.breakdown.classify(request, timeout: long);
      await requests.stream.first;
      server.breakdown.cancelClassify();
      await expectLater(call, canceled(CancelReason.cancel));
    });
  });
}

/// A client whose close() fails the request at once, as the browser does.
class ClosingClient extends http.BaseClient {
  ClosingClient(this.requests);

  final StreamController<void> requests;
  final _closed = Completer<http.StreamedResponse>();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    requests.add(null);
    return _closed.future;
  }

  @override
  void close() {
    if (!_closed.isCompleted) {
      _closed.completeError(http.ClientException('aborted'));
    }
  }
}
