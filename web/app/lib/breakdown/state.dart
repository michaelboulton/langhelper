import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../providers.dart';

/// The wait after the last change of the form before a classify.
const debounceTime = Duration(milliseconds: 500);

/// The wait between two reads of /api/v1/status while the server loads
/// models.
const modelsPollTime = Duration(seconds: 1);

/// The shared_preferences key of the form: source, language, text,
/// nonstandard and translate, as JSON.
const entryKey = 'langhelper.entry';

/// The shared_preferences key of the "Large models" choice. With no choice,
/// the server decides (`large_by_default`).
const heavyKey = 'langhelper.heavy';

/// The languages of /api/v1/languages.
class Languages {
  Languages(LanguagesResponse response)
    : study = {for (final each in response.languages) each.code: each},
      english = response.english,
      largeByDefault = response.largeByDefault;

  /// The study languages by code, in the order of the server.
  final Map<String, LanguageInfo> study;
  final LanguageInfo english;
  final bool largeByDefault;

  /// A study language or English.
  LanguageInfo? info(String code) =>
      study[code] ?? (code == english.code ? english : null);
}

/// The line under the form.
sealed class Status {
  const Status();
}

class Idle extends Status {
  const Idle();
}

class Working extends Status {
  const Working({required this.heavy});

  final bool heavy;
}

/// The answer came, from the models of [variant] for [language].
class Done extends Status {
  const Done(this.language, this.variant);

  final String language;
  final String variant;
}

class Canceled extends Status {
  const Canceled();
}

class TimedOut extends Status {
  const TimedOut(this.seconds);

  final int seconds;
}

class Failed extends Status {
  const Failed(this.error);

  final Object error;
}

/// The list of languages did not load, so the form does nothing.
class NoLanguages extends Status {
  const NoLanguages(this.error);

  final Object error;
}

/// A selected word, with its language.
typedef Selected = ({Word word, LanguageInfo info});

const _keep = Object();

@immutable
class BreakdownState {
  const BreakdownState({
    this.languages,
    this.language = '',
    this.source = Source.study,
    this.text = '',
    this.heavy = false,
    this.nonstandard = false,
    this.translate = false,
    this.timeout = 5,
    this.sending = false,
    this.status = const Idle(),
    this.result,
    this.selected,
  });

  /// Null until the list loads.
  final Languages? languages;

  /// The code of the study language.
  final String language;
  final Source source;
  final String text;
  final bool heavy;
  final bool nonstandard;
  final bool translate;

  /// The time limit of a classify, in seconds.
  final int timeout;

  /// A classify is in flight, so the Cancel button shows.
  final bool sending;
  final Status status;
  final ClassifyResponse? result;
  final Selected? selected;

  LanguageInfo? get info => languages?.study[language];

  /// [name]: a model type, "heavy" or "nonstandard".
  bool hasVariant(String name) => info?.variants.contains(name) ?? false;

  bool get useHeavy => heavy && hasVariant('heavy');

  /// The nonstandard models are heavy ones, so they need that choice too.
  bool get useNonstandard =>
      useHeavy && nonstandard && hasVariant('nonstandard');

  BreakdownState copyWith({
    Languages? languages,
    String? language,
    Source? source,
    String? text,
    bool? heavy,
    bool? nonstandard,
    bool? translate,
    int? timeout,
    bool? sending,
    Status? status,
    Object? result = _keep,
    Object? selected = _keep,
  }) => BreakdownState(
    languages: languages ?? this.languages,
    language: language ?? this.language,
    source: source ?? this.source,
    text: text ?? this.text,
    heavy: heavy ?? this.heavy,
    nonstandard: nonstandard ?? this.nonstandard,
    translate: translate ?? this.translate,
    timeout: timeout ?? this.timeout,
    sending: sending ?? this.sending,
    status: status ?? this.status,
    result: identical(result, _keep)
        ? this.result
        : result as ClassifyResponse?,
    selected: identical(selected, _keep)
        ? this.selected
        : selected as Selected?,
  );
}

final breakdownProvider = NotifierProvider<Breakdown, BreakdownState>(
  Breakdown.new,
);

/// The form, the classify requests and the result of the Breakdown tab.
class Breakdown extends Notifier<BreakdownState> {
  late Api _api;
  Timer? _debounce;

  /// The request of the last classify, as JSON. A change of the form that
  /// gives the same request sends nothing.
  String? _lastSent;

  @override
  BreakdownState build() {
    _api = ref.watch(apiProvider);
    ref.onDispose(() {
      _debounce?.cancel();
      _api.breakdown.cancelClassify();
    });
    unawaited(_start(ref.watch(preferencesProvider)));
    return const BreakdownState();
  }

  /// Load the languages and the saved form, then show the breakdown of the
  /// saved text again. Its lemmas do not count.
  Future<void> _start(SharedPreferencesAsync preferences) async {
    // Read before the first change of the form saves it.
    final reading = _readSaved(preferences);
    final Languages languages;
    try {
      languages = Languages(await _api.breakdown.languages());
    } on Object catch (error) {
      if (ref.mounted) state = state.copyWith(status: NoLanguages(error));
      return;
    }
    final (heavy, saved) = await reading;
    if (!ref.mounted) return;
    final language = saved['language'];
    final text = saved['text'];
    state = state.copyWith(
      languages: languages,
      language: languages.study.containsKey(language)
          ? language as String
          : languages.study.keys.firstOrNull ?? '',
      source: saved['source'] == Source.en.name ? Source.en : Source.study,
      // The user can type before the list loads.
      text: state.text.isEmpty && text is String ? text : null,
      heavy: heavy ?? languages.largeByDefault,
      nonstandard: saved['nonstandard'] == true,
      translate: saved['translate'] == true,
    );
    await _send(track: false);
  }

  Future<(bool?, Map<String, dynamic>)> _readSaved(
    SharedPreferencesAsync preferences,
  ) async {
    try {
      final entry = jsonDecode(await preferences.getString(entryKey) ?? '{}');
      return (
        await preferences.getBool(heavyKey),
        entry is Map<String, dynamic> ? entry : const <String, dynamic>{},
      );
    } on Object catch (error) {
      debugPrint('breakdown: no saved form: $error');
      return (null, const <String, dynamic>{});
    }
  }

  void setText(String text) {
    state = state.copyWith(text: text);
    _sendSoon();
  }

  void setLanguage(String code) {
    state = state.copyWith(language: code);
    _sendSoon();
  }

  void setSource(Source source) {
    state = state.copyWith(source: source);
    _sendSoon();
  }

  /// One choice for each tab that tags words.
  void setHeavy(bool heavy) {
    state = state.copyWith(heavy: heavy);
    unawaited(_write((store) => store.setBool(heavyKey, heavy)));
    _sendSoon();
  }

  void setNonstandard(bool nonstandard) {
    state = state.copyWith(nonstandard: nonstandard);
    _sendSoon();
  }

  void setTranslate(bool translate) {
    state = state.copyWith(translate: translate);
    _sendSoon();
  }

  void setTimeout(int seconds) => state = state.copyWith(timeout: seconds);

  void select(Selected? selected) => state = state.copyWith(selected: selected);

  /// An explicit submit: it counts the lemmas, and it sends again an
  /// unchanged form.
  Future<void> submit() => _send(track: true);

  void cancel() => _api.breakdown.cancelClassify();

  Future<void> _write(
    Future<void> Function(SharedPreferencesAsync store) write,
  ) async {
    try {
      await write(ref.read(preferencesProvider));
    } on Object catch (error) {
      debugPrint('breakdown: the form is not saved: $error');
    }
  }

  void _sendSoon() {
    final form = state;
    unawaited(
      _write(
        (store) => store.setString(
          entryKey,
          jsonEncode({
            'source': form.source.name,
            'language': form.language,
            'text': form.text,
            'nonstandard': form.nonstandard,
            'translate': form.translate,
          }),
        ),
      ),
    );
    _debounce?.cancel();
    _debounce = Timer(debounceTime, () => unawaited(_send(track: false)));
  }

  /// [track]: count the lemmas. Only an explicit submit counts them, so the
  /// half-typed words of an automatic send do not end up in the counts.
  Future<void> _send({required bool track}) async {
    _debounce?.cancel();
    final form = state;
    final text = form.text.trim();
    // No language: the list did not load.
    if (text.isEmpty || form.info == null) return;
    final request = ClassifyRequest(
      text: text,
      language: form.language,
      heavy: form.useHeavy,
      nonstandard: form.useNonstandard,
      track: track,
      translate: form.translate,
      source: form.source,
    );
    final key = jsonEncode({...request.toJson(), 'track': null});
    if (!track && key == _lastSent) return;
    _lastSent = key;
    state = form.copyWith(sending: true, status: Working(heavy: request.heavy));
    final models = ref.read(modelsProvider.notifier);
    // The server starts the load a moment after it gets the request.
    if (request.heavy) models.pollSoon();
    final seconds = max(1, form.timeout);
    try {
      final result = await _api.breakdown.classify(
        request,
        timeout: Duration(seconds: seconds),
      );
      if (!ref.mounted) return;
      state = state.copyWith(
        sending: false,
        status: Done(result.language, result.type),
        result: result,
        selected: null,
      );
    } on ApiCanceled catch (canceled) {
      // A newer request owns the state.
      if (!ref.mounted || canceled.reason == CancelReason.superseded) return;
      _lastSent = null;
      final timeout = canceled.reason == CancelReason.timeout;
      state = state.copyWith(
        sending: false,
        status: timeout ? TimedOut(seconds) : const Canceled(),
      );
      if (timeout) unawaited(models.poll());
    } on Object catch (error) {
      if (!ref.mounted) return;
      _lastSent = null;
      state = state.copyWith(sending: false, status: Failed(error));
    }
  }
}

final modelsProvider = NotifierProvider<Models, StatusResponse?>(Models.new);

bool loadingModels(StatusResponse status) =>
    status.loadingModel != null || status.loading != null;

/// The models that the server loads, from /api/v1/status. It reads the
/// status again each second while the server loads models or does not
/// answer, then stops.
class Models extends Notifier<StatusResponse?> {
  late Api _api;
  Timer? _timer;

  @override
  StatusResponse? build() {
    _api = ref.watch(apiProvider);
    ref.onDispose(() => _timer?.cancel());
    unawaited(poll());
    return null;
  }

  void pollSoon() {
    _timer?.cancel();
    _timer = Timer(modelsPollTime, () => unawaited(poll()));
  }

  Future<void> poll() async {
    _timer?.cancel();
    StatusResponse? status;
    try {
      status = await _api.breakdown.status();
    } on Object catch (error) {
      // For example in the middle of a restart of the server.
      debugPrint('breakdown: no status: $error');
    }
    if (!ref.mounted) return;
    state = status;
    if (status == null || loadingModels(status)) pollSoon();
  }
}
