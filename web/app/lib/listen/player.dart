import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';

/// Plays one mp3 at a time. The widget tests use a fake.
abstract class Player {
  /// Replaces the sound, and gives its length if the player knows it.
  Future<Duration?> load(Uint8List mp3);

  /// The same for a sound on the server, such as a clip of a card.
  Future<Duration?> loadUri(Uri uri);

  /// After the end, from the start again. A browser can refuse to play.
  void play();

  void pause();

  void seek(Duration position);

  /// 1 is the normal speed.
  void setSpeed(double speed);

  /// False at the end of the sound.
  Stream<bool> get playing;

  Stream<Duration> get position;

  /// The place in the sound now.
  Duration get currentPosition;

  Future<void> dispose();
}

/// Makes the player of a Listen panel or of a clip.
final newPlayerProvider = Provider<Player Function()>(
  (ref) => JustAudioPlayer.new,
);

class JustAudioPlayer implements Player {
  final _player = AudioPlayer();

  @override
  Future<Duration?> load(Uint8List mp3) => _player.setAudioSource(
    AudioSource.uri(Uri.dataFromBytes(mp3, mimeType: 'audio/mpeg')),
  );

  @override
  Future<Duration?> loadUri(Uri uri) =>
      _player.setAudioSource(AudioSource.uri(uri));

  @override
  void play() => unawaited(_play());

  Future<void> _play() async {
    try {
      if (_player.processingState == ProcessingState.completed) {
        await _player.seek(Duration.zero);
      }
      // play() completes when the sound stops.
      await _player.play();
    } on Object catch (error) {
      debugPrint('listen: no play: $error');
    }
  }

  @override
  void pause() => unawaited(_player.pause());

  @override
  void seek(Duration position) => unawaited(_player.seek(position));

  @override
  void setSpeed(double speed) => unawaited(_player.setSpeed(speed));

  @override
  late final Stream<bool> playing = _player.playerStateStream
      .map(
        (state) =>
            state.playing && state.processingState != ProcessingState.completed,
      )
      .distinct();

  @override
  late final Stream<Duration> position = _player.positionStream;

  @override
  Duration get currentPosition => _player.position;

  @override
  Future<void> dispose() => _player.dispose();
}
