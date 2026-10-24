import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../i18n/i18n.dart';
import '../listen/listen_panel.dart' show listenTimeout, speechInfoProvider;
import '../listen/player.dart';
import '../providers.dart';
import 'state.dart';
import 'voices.dart';

/// The "Read it aloud" button of an answered card. It uses the voice service
/// of the server when the service reads the language, else the voices of
/// the browser for a language with a `speech` tag. With neither, there is no
/// button. The notes go to the status line of the tab.
class ReadAloud extends ConsumerStatefulWidget {
  const ReadAloud({super.key, required this.text, required this.info});

  /// The text in the study language.
  final String text;
  final LanguageInfo info;

  @override
  ConsumerState<ReadAloud> createState() => _ReadAloudState();
}

class _ReadAloudState extends ConsumerState<ReadAloud> {
  /// The sound of the voice service, after the first click.
  Player? _player;
  bool _working = false;

  @override
  void dispose() {
    unawaited(_player?.dispose());
    super.dispose();
  }

  void _note(CardsStatus status) {
    if (mounted) ref.read(cardsProvider.notifier).note(status);
  }

  Future<void> _fromServer(SpeechInfoResponse voice) async {
    // The same text again: the sound is there.
    if (_player case final player?) {
      player.play();
      return;
    }
    setState(() => _working = true);
    _note(const CardsNote('listen-working'));
    try {
      final audio = await ref
          .read(apiProvider)
          .speech
          .audio(widget.text, widget.info.code, timeout: listenTimeout);
      if (!mounted) return;
      final player = ref.read(newPlayerProvider)();
      await player.load(audio.bytes);
      if (!mounted) {
        unawaited(player.dispose());
        return;
      }
      _player = player;
      player.play();
      _note(
        CardsNote(
          'listen-made-by',
          args: {'model': audio.model ?? voice.model},
        ),
      );
    } on Object catch (error) {
      final timeout =
          error is ApiCanceled && error.reason == CancelReason.timeout;
      _note(
        timeout
            ? CardsNote(
                'listen-timeout',
                args: {'seconds': listenTimeout.inSeconds},
                error: true,
              )
            : CardsFailed(error),
      );
    }
    if (mounted) setState(() => _working = false);
  }

  Future<void> _fromBrowser(BrowserVoices voices) async {
    final i18n = I18n.of(context);
    final name = {'language': i18n.languageName(widget.info)};
    void failed(SpeakFailure failure) => _note(switch (failure) {
      NoVoices() => const CardsNote('speech-no-voices', error: true),
      NoVoice() => CardsNote('speech-no-voice', args: name, error: true),
      SpeakError(:final code) => CardsNote(
        'speech-error',
        args: {'error': code},
        error: true,
      ),
    });
    try {
      await voices.speak(
        widget.text,
        language: widget.info.code,
        tag: widget.info.speech,
        onError: failed,
      );
    } on SpeakFailure catch (failure) {
      failed(failure);
    }
  }

  @override
  Widget build(BuildContext context) {
    final voice = ref.watch(speechInfoProvider).value;
    final browser = ref.watch(browserVoicesProvider);
    final server =
        voice != null &&
        voice.available &&
        voice.languages.contains(widget.info.code);
    if (!server && (widget.info.speech.isEmpty || !browser.available)) {
      return const SizedBox.shrink();
    }
    return OutlinedButton(
      onPressed: _working
          ? null
          : () =>
                unawaited(server ? _fromServer(voice) : _fromBrowser(browser)),
      child: Text(I18n.of(context).t('cards-speak')),
    );
  }
}
