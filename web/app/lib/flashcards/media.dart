import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../listen/listen_panel.dart' show PlayerBar;
import '../listen/player.dart';
import '../providers.dart';

/// The pictures and the sound clips of one side of a card. With [autoplay],
/// the first clip starts at once. The clips stop when the widget goes, so a
/// new card gives it a new key.
class MediaView extends ConsumerStatefulWidget {
  const MediaView({super.key, required this.media, this.autoplay = false});

  final List<Media> media;
  final bool autoplay;

  @override
  ConsumerState<MediaView> createState() => _MediaViewState();
}

class _MediaViewState extends ConsumerState<MediaView> {
  /// The player of each clip, in the order of [MediaView.media].
  final _players = <Media, Player>{};
  final _durations = <Media, Duration?>{};

  @override
  void initState() {
    super.initState();
    final api = ref.read(apiProvider);
    final newPlayer = ref.read(newPlayerProvider);
    var first = widget.autoplay;
    for (final each in widget.media) {
      if (each.kind != MediaKind.audio) continue;
      final player = _players[each] = newPlayer();
      unawaited(_load(player, each, api.resolve(each.url), play: first));
      first = false;
    }
  }

  Future<void> _load(
    Player player,
    Media media,
    Uri uri, {
    required bool play,
  }) async {
    Duration? duration;
    try {
      duration = await player.loadUri(uri);
    } on Object catch (error) {
      debugPrint('media: no clip ${media.url}: $error');
    }
    if (!mounted) return;
    setState(() => _durations[media] = duration);
    // A browser can refuse a clip that no click started. The buttons stay.
    if (play) player.play();
  }

  @override
  void dispose() {
    for (final player in _players.values) {
      unawaited(player.dispose());
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.media.isEmpty) return const SizedBox.shrink();
    final api = ref.read(apiProvider);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          for (final each in widget.media)
            switch (_players[each]) {
              final player? => ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 360),
                child: PlayerBar(player: player, duration: _durations[each]),
              ),
              null => ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 260),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    api.resolve(each.url).toString(),
                    // The picture is the prompt, so it has no text of its
                    // own.
                    excludeFromSemantics: true,
                    errorBuilder: (context, error, stack) =>
                        const Icon(Icons.broken_image_outlined, size: 48),
                  ),
                ),
              ),
            },
        ],
      ),
    );
  }
}
