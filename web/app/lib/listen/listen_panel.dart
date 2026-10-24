import 'dart:async';

import 'package:audio_video_progress_bar/audio_video_progress_bar.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../i18n/i18n.dart';
import '../providers.dart';
import 'player.dart';

/// The voice service of the server, read one time. Null when the server does
/// not answer: then no panel shows.
final speechInfoProvider = FutureProvider<SpeechInfoResponse?>((ref) async {
  try {
    return await ref.watch(apiProvider).speech.info();
  } on Object catch (error) {
    debugPrint('listen: no voice service: $error');
    return null;
  }
});

/// The server stops the voice service after TLHELPER_VOICE_TIMEOUT seconds
/// (180 by default), so a little more than that.
const listenTimeout = Duration(seconds: 190);

/// A text for the voice service, in the language of [info].
typedef ListenTarget = ({String text, LanguageInfo info});

typedef _Note = ({String text, bool error});

/// The Listen panel: one button for each text that the voice service can
/// read. The text goes to the service, so a request goes out only on a
/// click.
class ListenPanel extends ConsumerStatefulWidget {
  const ListenPanel({super.key, required this.targets});

  final List<ListenTarget> targets;

  @override
  ConsumerState<ListenPanel> createState() => _ListenPanelState();
}

class _ListenPanelState extends ConsumerState<ListenPanel> {
  Player? _player;

  /// The length of the sound on the panel. Null with no sound.
  Duration? _duration;
  bool _loaded = false;
  bool _working = false;
  _Note? _note;

  /// Changes with the texts, so the answer for an older text is dropped.
  int _texts = 0;

  static List<(String, String)> _key(List<ListenTarget> targets) => [
    for (final each in targets) (each.text, each.info.code),
  ];

  @override
  void didUpdateWidget(ListenPanel old) {
    super.didUpdateWidget(old);
    // The same texts again (an automatic send) keep the sound on the panel.
    if (listEquals(_key(old.targets), _key(widget.targets))) return;
    _texts++;
    _player?.pause();
    _loaded = false;
    _duration = null;
    _working = false;
    _note = null;
  }

  @override
  void dispose() {
    unawaited(_player?.dispose());
    super.dispose();
  }

  Future<void> _listen(ListenTarget target, SpeechInfoResponse info) async {
    final texts = _texts;
    final i18n = I18n.of(context);
    setState(() {
      _working = true;
      _note = (text: i18n.t('listen-working'), error: false);
    });
    _Note note;
    try {
      final audio = await ref
          .read(apiProvider)
          .speech
          .audio(target.text, target.info.code, timeout: listenTimeout);
      if (!mounted || texts != _texts) return;
      final player = _player ??= ref.read(newPlayerProvider)();
      final duration = await player.load(audio.bytes);
      if (!mounted || texts != _texts) return;
      // After a click, so the browser allows it.
      player.play();
      _loaded = true;
      _duration = duration;
      note = (
        text: i18n.t('listen-made-by', {'model': audio.model ?? info.model}),
        error: false,
      );
    } on Object catch (error) {
      final timeout =
          error is ApiCanceled && error.reason == CancelReason.timeout;
      note = (
        text: timeout
            ? i18n.t('listen-timeout', {'seconds': listenTimeout.inSeconds})
            : i18n.errorText(error),
        error: true,
      );
    }
    if (!mounted || texts != _texts) return;
    setState(() {
      _working = false;
      _note = note;
    });
  }

  @override
  Widget build(BuildContext context) {
    final info = ref.watch(speechInfoProvider).value;
    if (info == null || !info.available) return const SizedBox.shrink();
    final readable = [
      for (final target in widget.targets)
        if (target.text.isNotEmpty && info.languages.contains(target.info.code))
          target,
    ];
    if (readable.isEmpty) return const SizedBox.shrink();
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.only(top: 12),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(i18n.t('listen-label'), style: TextStyle(color: muted)),
              for (final target in readable)
                OutlinedButton(
                  onPressed: _working
                      ? null
                      : () => unawaited(_listen(target, info)),
                  child: Text(i18n.languageName(target.info)),
                ),
            ],
          ),
          if (_player case final player? when _loaded)
            PlayerBar(player: player, duration: _duration),
          if (_note case final note?)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  note.text,
                  style: TextStyle(
                    color: note.error ? const Color(0xFFC0392B) : muted,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Play or pause, and the place in the sound.
class PlayerBar extends StatelessWidget {
  const PlayerBar({super.key, required this.player, required this.duration});

  final Player player;
  final Duration? duration;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final length = duration;
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 480),
      child: Row(
        children: [
          StreamBuilder<bool>(
            stream: player.playing,
            builder: (context, snapshot) {
              final playing = snapshot.data ?? false;
              return IconButton(
                icon: Icon(playing ? Icons.pause : Icons.play_arrow),
                tooltip: playing
                    ? i18n.t('listen-pause')
                    : i18n.t('listen-play'),
                onPressed: playing ? player.pause : player.play,
              );
            },
          ),
          if (length != null && length > Duration.zero)
            Expanded(
              child: StreamBuilder<Duration>(
                stream: player.position,
                builder: (context, snapshot) => ProgressBar(
                  progress: snapshot.data ?? Duration.zero,
                  total: length,
                  onSeek: player.seek,
                  timeLabelLocation: TimeLabelLocation.sides,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
