import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';

import 'browser.dart' if (dart.library.js_interop) 'browser_web.dart';

/// Why the voices of the browser do not read a text.
sealed class SpeakFailure implements Exception {
  const SpeakFailure();
}

/// The browser has no voice at all.
class NoVoices extends SpeakFailure {
  const NoVoices();
}

/// The browser has voices, but none for the language.
class NoVoice extends SpeakFailure {
  const NoVoice();
}

/// The voice stopped with the code of the browser, such as
/// "synthesis-failed".
class SpeakError extends SpeakFailure {
  const SpeakError(this.code);

  final String code;
}

/// Reads a text aloud with the voices of the browser. The widget tests use a
/// fake.
abstract class BrowserVoices {
  /// The browser can read a text aloud at all.
  bool get available;

  /// Read [text] with a voice of [language], a code such as "hr". [tag] is
  /// the tag with the region, such as "hr-HR". Fails with a SpeakFailure
  /// before the start. A failure after the start goes to [onError].
  Future<void> speak(
    String text, {
    required String language,
    required String tag,
    required void Function(SpeakFailure failure) onError,
  });
}

final browserVoicesProvider = Provider<BrowserVoices>((ref) => TtsVoices());

class TtsVoices implements BrowserVoices {
  TtsVoices() {
    _tts.setErrorHandler((code) {
      // A new text stops the one before it.
      if (code == 'canceled' || code == 'interrupted') return;
      _onError?.call(SpeakError('$code'));
    });
  }

  final _tts = FlutterTts();
  void Function(SpeakFailure failure)? _onError;

  @override
  bool get available => canSpeak();

  /// The browser loads its voices in the background, so the first list can
  /// be empty. A second look after a second, because some browsers have no
  /// voice at all.
  Future<List<Map<Object?, Object?>>> _voices() async {
    for (final wait in [Duration.zero, const Duration(seconds: 1)]) {
      await Future<void>.delayed(wait);
      final voices = await _tts.getVoices;
      if (voices is List && voices.isNotEmpty) {
        return [for (final each in voices) each as Map<Object?, Object?>];
      }
    }
    return const [];
  }

  @override
  Future<void> speak(
    String text, {
    required String language,
    required String tag,
    required void Function(SpeakFailure failure) onError,
  }) async {
    final voices = await _voices();
    // On Linux the voices come from Speech Dispatcher, and a browser in a
    // Flatpak often cannot reach it.
    if (voices.isEmpty) throw const NoVoices();
    final voice = voices
        .where(
          (each) =>
              '${each['locale']}'.replaceAll('_', '-').startsWith(language),
        )
        .firstOrNull;
    if (voice == null) throw const NoVoice();
    _onError = onError;
    await _tts.stop();
    await _tts.setLanguage(tag);
    await _tts.setVoice({
      'name': '${voice['name']}',
      'locale': '${voice['locale']}',
    });
    await _tts.speak(text);
  }
}
