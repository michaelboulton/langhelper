import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart' hide Locale;
import '../breakdown/form.dart' show textDirection;
import '../breakdown/state.dart';
import '../flashcards/browser.dart'
    if (dart.library.js_interop) '../flashcards/browser_web.dart';
import '../i18n/i18n.dart';
import '../listen/player.dart';
import '../providers.dart';
import 'courses.dart';
import 'lesson_player.dart';
import 'state.dart';

/// One lesson: its title, its grammar step, the player and the script.
/// Space plays and pauses, and ← and → go back and forward 10 s.
class LessonView extends ConsumerStatefulWidget {
  const LessonView({super.key, required this.course, required this.number});

  /// The name of the folder of the course.
  final String course;
  final int number;

  @override
  ConsumerState<LessonView> createState() => _LessonViewState();
}

class _LessonViewState extends ConsumerState<LessonView> {
  /// Null for a lesson with no mp3, and until the list of courses loads.
  LessonAudio? _audio;

  @override
  void initState() {
    super.initState();
    // The list of courses has the audio state of the lesson.
    ref.listenManual(audioCoursesProvider, (_, next) {
      if (next.value case final courses?) _start(_lesson(courses));
    }, fireImmediately: true);
  }

  @override
  void dispose() {
    unawaited(_audio?.dispose());
    super.dispose();
  }

  (AudioCourse, AudioLesson)? _lesson(List<AudioCourse> courses) {
    for (final course in courses) {
      if (course.id != widget.course) continue;
      for (final lesson in course.lessons) {
        if (lesson.number == widget.number) return (course, lesson);
      }
    }
    return null;
  }

  void _start((AudioCourse, AudioLesson)? found) {
    if (_audio != null || found == null) return;
    if (found.$2.audio == AudioState.none) return;
    final audio = _audio = LessonAudio(ref.read(newPlayerProvider)());
    unawaited(_load(audio));
  }

  Future<void> _load(LessonAudio audio) async {
    final uri = ref
        .read(apiProvider)
        .audioLessons
        .audio(widget.course, widget.number);
    Duration? duration;
    try {
      duration = await audio.player.loadUri(uri);
    } on Object catch (error) {
      debugPrint('audio: no mp3 $uri: $error');
    }
    if (!mounted) return;
    setState(() => audio.duration = duration);
  }

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final courses = ref.watch(audioCoursesProvider);
    final script = ref.watch(
      audioLessonProvider((course: widget.course, number: widget.number)),
    );
    final found = switch (courses.value) {
      final list? => _lesson(list),
      null => null,
    };
    final error = courses.error ?? script.error;
    final lesson = script.value;
    final audio = _audio;
    final state = found?.$2.audio ?? AudioState.none;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    final page = AudioPage(
      children: [
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: TextButton.icon(
            onPressed: () => context.go('/audio'),
            icon: const Icon(Icons.arrow_back),
            label: Text(i18n.t('audio-all-lessons')),
          ),
        ),
        if (error != null)
          AudioNote(text: i18n.errorText(error), error: true)
        else if (lesson != null && courses.hasValue) ...[
          Semantics(
            header: true,
            child: Text(
              lesson.title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          const SizedBox(height: 4),
          Text(lesson.grammar, style: TextStyle(color: muted)),
          if (audio != null) LessonPlayer(audio: audio),
          if (state != AudioState.ready)
            AudioNote(text: i18n.t('audio-state-${state.name}')),
          const SizedBox(height: 12),
          SelectionArea(
            child: _Script(
              lines: lesson.lines,
              language: found?.$1.language ?? '',
            ),
          ),
        ],
      ],
    );
    if (audio == null) return page;
    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.space): audio.playPause,
        const SingleActivator(LogicalKeyboardKey.arrowLeft): () =>
            audio.skip(-skipStep),
        const SingleActivator(LogicalKeyboardKey.arrowRight): () =>
            audio.skip(skipStep),
      },
      child: Focus(autofocus: true, child: page),
    );
  }
}

/// The lines of a lesson: the name of each speaker, and a line for each
/// pause. The narrator speaks English, and the actors the study language.
class _Script extends ConsumerWidget {
  const _Script({required this.lines, required this.language});

  final List<AudioLine> lines;

  /// The code of the study language of the course.
  final String language;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final english = languages?.english;
    final study = languages?.study[language];
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final line in lines)
          // One node for each line: else the SelectionArea merges the lines
          // into one label, out of order.
          Semantics(
            container: true,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: switch (line.speaker) {
                Speaker.pause => Text(
                  i18n.t('audio-pause', {
                    'seconds': decimal(i18n.locale, line.seconds),
                  }),
                  style: TextStyle(color: muted, fontStyle: FontStyle.italic),
                ),
                final speaker => _Line(
                  speaker: i18n.t(switch (speaker) {
                    Speaker.actor1 => 'audio-speaker-actor-1',
                    Speaker.actor2 => 'audio-speaker-actor-2',
                    _ => 'audio-speaker-narrator',
                  }),
                  text: line.text,
                  code: speaker == Speaker.narrator
                      ? english?.code ?? 'en'
                      : language,
                  info: speaker == Speaker.narrator ? english : study,
                ),
              },
            ),
          ),
      ],
    );
  }
}

/// The speaker in the language of the page, then the text in its own
/// language and direction.
class _Line extends StatelessWidget {
  const _Line({
    required this.speaker,
    required this.text,
    required this.code,
    required this.info,
  });

  final String speaker;
  final String text;
  final String code;
  final LanguageInfo? info;

  @override
  Widget build(BuildContext context) {
    final info = this.info;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Text(speaker, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            text,
            locale: Locale(code),
            textDirection: info == null ? null : textDirection(info),
          ),
        ),
      ],
    );
  }
}
