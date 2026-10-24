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
import 'script.dart' if (dart.library.js_interop) 'script_web.dart';
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

  /// Read here, because the last save comes after the dispose.
  late final AudioCourses _courses;

  /// Saves the position when the browser tab hides or closes.
  late final AppLifecycleListener _lifecycle;

  LessonId get _id => (course: widget.course, number: widget.number);

  @override
  void initState() {
    super.initState();
    _courses = ref.read(audioCoursesProvider.notifier);
    _lifecycle = AppLifecycleListener(onHide: () => _audio?.saveNow());
    // The list of courses has the audio state and the progress of the lesson.
    ref.listenManual(audioCoursesProvider, (_, next) {
      if (next.value case final courses?) _start(_lesson(courses));
    }, fireImmediately: true);
  }

  @override
  void dispose() {
    _lifecycle.dispose();
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
    final lesson = found.$2;
    if (lesson.audio == AudioState.none) return;
    final courses = _courses;
    final id = _id;
    final audio = _audio = LessonAudio(
      ref.read(newPlayerProvider)(),
      save: (position, duration) =>
          unawaited(courses.save(id, position, duration)),
    );
    unawaited(_load(audio, fromSeconds(lesson.position)));
  }

  Future<void> _load(LessonAudio audio, Duration start) async {
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
    audio.start(start);
  }

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final courses = ref.watch(audioCoursesProvider);
    final script = ref.watch(audioLessonProvider(_id));
    final found = switch (courses.value) {
      final list? => _lesson(list),
      null => null,
    };
    final error = courses.error ?? script.error;
    final lesson = script.value;
    final audio = _audio;
    final state = found?.$2.audio ?? AudioState.none;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final ready = error == null && lesson != null && courses.hasValue;
    final page = LessonScript(
      header: [
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
        else if (ready) ...[
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
        ],
      ],
      lines: ready
          ? _script(i18n, lesson.lines, found?.$1.language ?? '', languages)
          : const [],
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
/// pause. The narrator speaks English, and the actors the study language,
/// whose code is [language].
List<ScriptLine> _script(
  I18n i18n,
  List<AudioLine> lines,
  String language,
  Languages? languages,
) {
  final english = languages?.english;
  final study = languages?.study[language];
  return [
    for (final line in lines)
      switch (line.speaker) {
        Speaker.pause => (
          speaker: null,
          text: i18n.t('audio-pause', {
            'seconds': decimal(i18n.locale, line.seconds),
          }),
          locale: null,
          direction: null,
        ),
        final speaker => (
          speaker: i18n.t(switch (speaker) {
            Speaker.actor1 => 'audio-speaker-actor-1',
            Speaker.actor2 => 'audio-speaker-actor-2',
            _ => 'audio-speaker-narrator',
          }),
          text: line.text,
          locale: speaker == Speaker.narrator
              ? english?.code ?? 'en'
              : language,
          direction: switch (speaker == Speaker.narrator ? english : study) {
            final info? => textDirection(info),
            null => null,
          },
        ),
      },
  ];
}
