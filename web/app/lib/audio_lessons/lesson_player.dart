import 'dart:async';

import 'package:audio_video_progress_bar/audio_video_progress_bar.dart';
import 'package:flutter/material.dart';

import '../flashcards/browser.dart'
    if (dart.library.js_interop) '../flashcards/browser_web.dart';
import '../i18n/i18n.dart';
import '../listen/player.dart';

/// The step of the back and forward buttons and keys.
const skipStep = Duration(seconds: 10);

/// The speeds of the speed buttons.
const speeds = [0.75, 1.0, 1.25];

/// The time between two saves of the position while a lesson plays.
const saveEvery = Duration(seconds: 10);

/// A saved position this near the end starts the lesson again. The same as
/// `FINISHED_WITHIN` in `tlhelper/flashcards/store.py`.
const finishedWithin = Duration(seconds: 5);

/// What the buttons and the keys of a lesson do to its [player], and the
/// saves of its position.
class LessonAudio {
  LessonAudio(this.player, {this.save}) {
    _playing = player.playing.listen(_onPlaying);
  }

  final Player player;

  /// Saves the position in the lesson and the length of the mp3.
  final void Function(Duration position, Duration duration)? save;

  /// The length of the mp3. Null until it loads.
  Duration? duration;
  bool isPlaying = false;
  double speed = 1;
  late final StreamSubscription<bool> _playing;
  Timer? _timer;

  /// The position of the last save, or of the start.
  Duration? _saved;

  /// Saves every 10 s while the lesson plays, and on pause and at the end.
  void _onPlaying(bool playing) {
    final was = isPlaying;
    isPlaying = playing;
    if (playing) {
      _timer ??= Timer.periodic(saveEvery, (_) => saveNow());
    } else {
      _timer?.cancel();
      _timer = null;
      if (was) saveNow();
    }
  }

  /// Saves the position, if the mp3 has loaded and the position changed
  /// after the last save.
  void saveNow() {
    final duration = this.duration;
    if (duration == null || duration <= Duration.zero) return;
    final position = player.currentPosition;
    if (position == _saved) return;
    _saved = position;
    save?.call(position, duration);
  }

  /// Starts the lesson at the saved [position], after the mp3 loads. A
  /// position at the end starts the lesson again from the start.
  void start(Duration position) {
    final end = duration;
    if (position <= Duration.zero ||
        (end != null && position >= end - finishedWithin)) {
      _saved = Duration.zero;
      return;
    }
    _saved = position;
    player.seek(position);
  }

  void playPause() => isPlaying ? player.pause() : player.play();

  /// Back 10 s stops at the start, and forward 10 s stops at the end.
  void skip(Duration delta) {
    var to = player.currentPosition + delta;
    if (to < Duration.zero) to = Duration.zero;
    if (duration case final end? when to > end) to = end;
    player.seek(to);
  }

  void setSpeed(double value) {
    speed = value;
    player.setSpeed(value);
  }

  /// Saves the position, then stops the player.
  Future<void> dispose() async {
    _timer?.cancel();
    saveNow();
    // The cancel stops the events at once, before the player stops.
    final cancel = _playing.cancel();
    await Future.wait([player.dispose(), cancel]);
  }
}

/// The player of a lesson: back 10 s, play or pause, forward 10 s, the
/// speeds, and the seek bar.
class LessonPlayer extends StatefulWidget {
  const LessonPlayer({super.key, required this.audio});

  final LessonAudio audio;

  @override
  State<LessonPlayer> createState() => _LessonPlayerState();
}

class _LessonPlayerState extends State<LessonPlayer> {
  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final audio = widget.audio;
    final player = audio.player;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.replay_10),
                tooltip: i18n.t('audio-back'),
                onPressed: () => audio.skip(-skipStep),
              ),
              StreamBuilder<bool>(
                stream: player.playing,
                builder: (context, snapshot) {
                  final playing = snapshot.data ?? false;
                  return IconButton.filled(
                    icon: Icon(playing ? Icons.pause : Icons.play_arrow),
                    tooltip: playing
                        ? i18n.t('listen-pause')
                        : i18n.t('listen-play'),
                    onPressed: playing ? player.pause : player.play,
                  );
                },
              ),
              IconButton(
                icon: const Icon(Icons.forward_10),
                tooltip: i18n.t('audio-forward'),
                onPressed: () => audio.skip(skipStep),
              ),
              // The label wraps with its buttons on a narrow screen.
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(i18n.t('audio-speed'), style: TextStyle(color: muted)),
                  const SizedBox(width: 8),
                  SegmentedButton<double>(
                    showSelectedIcon: false,
                    segments: [
                      for (final each in speeds)
                        ButtonSegment(
                          value: each,
                          label: Text('${decimal(i18n.locale, each)}×'),
                        ),
                    ],
                    selected: {audio.speed},
                    onSelectionChanged: (chosen) =>
                        setState(() => audio.setSpeed(chosen.single)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          StreamBuilder<Duration>(
            stream: player.position,
            builder: (context, snapshot) => ProgressBar(
              progress: snapshot.data ?? Duration.zero,
              total: audio.duration ?? Duration.zero,
              onSeek: player.seek,
              timeLabelLocation: TimeLabelLocation.below,
            ),
          ),
        ],
      ),
    );
  }
}
