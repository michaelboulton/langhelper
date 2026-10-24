import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'login.dart' if (dart.library.js_interop) 'login_web.dart';
import 'models.dart';

/// Formats the message [id] of the catalogs, or gives null if no catalog has
/// it.
typedef Messages = String? Function(String id, Map<String, Object?> params);

/// The message "error-[code]" of the catalogs, else [fallback]: the English
/// text of the server. For an ApiException and for Translation.error.
String codedMessage(
  Messages messages,
  String code,
  Map<String, Object?> params,
  String fallback,
) => code.isEmpty ? fallback : messages('error-$code', params) ?? fallback;

/// A response with an error status. The body is {detail, code?, params?}.
class ApiException implements Exception {
  const ApiException(
    this.status, {
    this.detail = '',
    this.code = '',
    this.params = const {},
  });

  factory ApiException.fromResponse(http.Response response) {
    Object? body;
    try {
      body = jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      body = null;
    }
    if (body is! Map<String, dynamic>) return ApiException(response.statusCode);
    final detail = body['detail'];
    final code = body['code'];
    final params = body['params'];
    return ApiException(
      response.statusCode,
      // A 422 of FastAPI has a list here.
      detail: detail is String ? detail : '',
      code: code is String ? code : '',
      params: params is Map<String, dynamic> ? params : const {},
    );
  }

  final int status;
  final String detail;
  final String code;
  final Map<String, Object?> params;

  /// "The server returned 503." and the text of the error, as on the page
  /// of static/.
  String message(Messages messages) {
    final server =
        messages('error-server', {'status': status}) ??
        'The server returned $status.';
    final text = codedMessage(messages, code, params, detail);
    return text.isEmpty ? server : '$server $text';
  }

  @override
  String toString() => 'ApiException($status, $detail)';
}

enum CancelReason { cancel, superseded, timeout }

/// The request stopped before its answer came.
class ApiCanceled implements Exception {
  const ApiCanceled(this.reason);

  final CancelReason reason;

  @override
  String toString() => 'ApiCanceled(${reason.name})';
}

/// One request, with its own http.Client: close() of the client cancels
/// the request.
class Call {
  Call._(this._client);

  final http.Client _client;
  final _stopped = Completer<Never>();
  CancelReason? _reason;
  bool _done = false;

  /// Close the client. The request fails with ApiCanceled(reason).
  void stop(CancelReason reason) {
    if (_done || _reason != null) return;
    _reason = reason;
    _stopped.completeError(ApiCanceled(reason));
    _client.close();
  }

  void _finish() {
    _done = true;
    _client.close();
  }
}

/// The API of the server, on the origin of the page. A 401 loads the login
/// page.
class Api {
  Api({
    Uri? base,
    http.Client Function()? newClient,
    void Function()? onUnauthorized,
  }) : base = base ?? Uri.base,
       _newClient = newClient ?? http.Client.new,
       _onUnauthorized = onUnauthorized ?? goToLogin;

  /// The address of the page.
  final Uri base;
  final http.Client Function() _newClient;
  final void Function() _onUnauthorized;

  late final breakdown = BreakdownApi._(this);
  late final flashcards = FlashcardsApi._(this);
  late final explain = ExplainApi._(this);
  late final speech = SpeechApi._(this);
  late final audioLessons = AudioLessonsApi._(this);

  /// An address of the server, such as the `url` of a Media.
  Uri resolve(String path) => base.resolve(path);

  Uri _uri(String path, Map<String, String>? query) {
    final uri = resolve('/api/v1$path');
    return query == null || query.isEmpty
        ? uri
        : uri.replace(queryParameters: query);
  }

  Call _call() => Call._(_newClient());

  Future<http.Response> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
    Duration? timeout,
    Call? call,
  }) async {
    call ??= _call();
    final timer = timeout == null
        ? null
        : Timer(timeout, () => call!.stop(CancelReason.timeout));
    final request = http.Request(method, _uri(path, query));
    if (body != null) {
      request.headers['content-type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    try {
      final response = await Future.any([
        call._client.send(request).then(http.Response.fromStream),
        call._stopped.future,
      ]);
      if (call._reason case final reason?) throw ApiCanceled(reason);
      if (response.statusCode == 401) _onUnauthorized();
      if (response.statusCode >= 300) {
        throw ApiException.fromResponse(response);
      }
      return response;
    } on Object catch (error) {
      // The close() of stop() can fail the request first.
      if (call._reason case final reason? when error is! ApiCanceled) {
        throw ApiCanceled(reason);
      }
      rethrow;
    } finally {
      timer?.cancel();
      call._finish();
    }
  }

  Future<Map<String, dynamic>> _json(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
    Duration? timeout,
    Call? call,
  }) async {
    final response = await _send(
      method,
      path,
      query: query,
      body: body,
      timeout: timeout,
      call: call,
    );
    // The server sends no charset, and http reads such a body as Latin-1.
    return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }
}

/// The breakdown tab, the languages and the text of the page.
class BreakdownApi {
  BreakdownApi._(this._api);

  final Api _api;
  Call? _classify;

  Future<LanguagesResponse> languages() async =>
      LanguagesResponse.fromJson(await _api._json('GET', '/languages'));

  Future<LocalesResponse> locales() async =>
      LocalesResponse.fromJson(await _api._json('GET', '/locales'));

  /// The Fluent file of the page text in one locale.
  Future<String> catalog(String code) async {
    final path = '/locales/${Uri.encodeComponent(code)}/ui.ftl';
    final response = await _api._send('GET', path);
    return utf8.decode(response.bodyBytes);
  }

  Future<StatusResponse> status() async =>
      StatusResponse.fromJson(await _api._json('GET', '/status'));

  /// A newer classify cancels this one (CancelReason.superseded).
  Future<ClassifyResponse> classify(
    ClassifyRequest request, {
    required Duration timeout,
  }) async {
    _classify?.stop(CancelReason.superseded);
    final call = _classify = _api._call();
    try {
      return ClassifyResponse.fromJson(
        await _api._json(
          'POST',
          '/classify',
          body: request.toJson(),
          timeout: timeout,
          call: call,
        ),
      );
    } finally {
      if (identical(_classify, call)) _classify = null;
    }
  }

  /// The classify in flight fails with ApiCanceled(CancelReason.cancel).
  void cancelClassify() => _classify?.stop(CancelReason.cancel);
}

class FlashcardsApi {
  FlashcardsApi._(this._api);

  final Api _api;

  Future<DecksResponse> decks() async =>
      DecksResponse.fromJson(await _api._json('GET', '/decks'));

  Future<NextResult> next(int deckId, {bool heavy = false}) async =>
      NextResult.fromJson(
        await _api._json(
          'GET',
          '/decks/$deckId/next',
          query: {'heavy': '$heavy'},
        ),
      );

  Future<AnswerResponse> answer(int cardId, AnswerRequest request) async =>
      AnswerResponse.fromJson(
        await _api._json(
          'POST',
          '/cards/$cardId/answer',
          body: request.toJson(),
        ),
      );

  Future<RatingResponse> rating(int reviewId, int rating) async =>
      RatingResponse.fromJson(
        await _api._json(
          'POST',
          '/reviews/$reviewId/rating',
          body: RatingRequest(rating: rating).toJson(),
        ),
      );

  Future<UsersResponse> users() async =>
      UsersResponse.fromJson(await _api._json('GET', '/flashcards/users'));

  /// [of]: the `id` of another user, for an admin.
  Future<StatsResponse> stats({int? deck, String? of}) async =>
      StatsResponse.fromJson(
        await _api._json(
          'GET',
          '/flashcards/stats',
          query: {'deck': ?deck?.toString(), 'of': ?of},
        ),
      );
}

class ExplainApi {
  ExplainApi._(this._api);

  final Api _api;

  Future<QuestionsResponse> questions() async =>
      QuestionsResponse.fromJson(await _api._json('GET', '/explain/questions'));

  Future<ExplainResponse> sentence(
    ExplainSentenceRequest request, {
    Duration? timeout,
  }) async => ExplainResponse.fromJson(
    await _api._json(
      'POST',
      '/explain',
      body: request.toJson(),
      timeout: timeout,
    ),
  );

  Future<ExplainResponse> review(
    int reviewId,
    ExplainRequest request, {
    Duration? timeout,
  }) async => ExplainResponse.fromJson(
    await _api._json(
      'POST',
      '/reviews/$reviewId/explain',
      body: request.toJson(),
      timeout: timeout,
    ),
  );
}

/// The mp3 of a text, and the model that read it.
class SpeechAudio {
  const SpeechAudio(this.bytes, this.model);

  final Uint8List bytes;

  /// The x-voice-model header. Null without it: then the model of info().
  final String? model;
}

class SpeechApi {
  SpeechApi._(this._api);

  final Api _api;

  Future<SpeechInfoResponse> info() async =>
      SpeechInfoResponse.fromJson(await _api._json('GET', '/speech'));

  /// A GET, so the browser cache answers a repeat.
  Future<SpeechAudio> audio(
    String text,
    String language, {
    Duration? timeout,
  }) async {
    final response = await _api._send(
      'GET',
      '/speech/audio',
      query: {'text': text, 'language': language},
      timeout: timeout,
    );
    return SpeechAudio(response.bodyBytes, response.headers['x-voice-model']);
  }
}

class AudioLessonsApi {
  AudioLessonsApi._(this._api);

  final Api _api;

  Future<AudioCoursesResponse> courses() async =>
      AudioCoursesResponse.fromJson(await _api._json('GET', '/audio-lessons'));

  Future<AudioLessonResponse> lesson(String course, int number) async =>
      AudioLessonResponse.fromJson(
        await _api._json(
          'GET',
          '/audio-lessons/${Uri.encodeComponent(course)}/$number',
        ),
      );

  /// The mp3 of a lesson, for the player. The route answers a Range request.
  Uri audio(String course, int number) => _api._uri(
    '/audio-lessons/${Uri.encodeComponent(course)}/$number.mp3',
    null,
  );
}
