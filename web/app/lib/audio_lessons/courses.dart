import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/models.dart';
import '../i18n/i18n.dart';
import 'state.dart';

/// The title of the tab. It is also the title of the browser tab.
class AudioTitle extends StatelessWidget {
  const AudioTitle({super.key});

  @override
  Widget build(BuildContext context) {
    final title = I18n.of(context).t('audio-title');
    return Title(
      title: title,
      color: Theme.of(context).primaryColor,
      child: Text(title),
    );
  }
}

/// The side margin of the tab in a window [width] wide: a column of at most
/// 860 px in the middle, with margins of 16 px. index.html has the same
/// column for the script of a lesson in a browser.
double pageSide(double width) => max(0.0, (width - 860) / 2) + 16;

/// The width and the margins of the tab, as on the other tabs.
class AudioPage extends StatelessWidget {
  const AudioPage({super.key, required this.children, this.sliver});

  final List<Widget> children;

  /// After the [children]. A long list goes here, so that only the part on
  /// the screen is built.
  final Widget? sliver;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = pageSide(box.maxWidth);
        return CustomScrollView(
          slivers: [
            SliverPadding(
              padding: EdgeInsets.fromLTRB(side, 16, side, 64),
              sliver: SliverMainAxisGroup(
                slivers: [
                  SliverToBoxAdapter(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: children,
                    ),
                  ),
                  ?sliver,
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

/// A note of the tab, such as an error.
class AudioNote extends StatelessWidget {
  const AudioNote({super.key, required this.text, this.error = false});

  final String text;
  final bool error;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Semantics(
        liveRegion: error,
        child: Text(
          text,
          style: TextStyle(
            color: error
                ? const Color(0xFFC0392B)
                : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}

/// The courses, each with its lessons in order. A lesson opens at
/// `/#/audio/<course>/<lesson>`.
class CoursesView extends ConsumerWidget {
  const CoursesView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final courses = ref.watch(audioCoursesProvider);
    return AudioPage(
      children: [
        Text(
          i18n.t('audio-intro'),
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        switch (courses) {
          AsyncData(value: final list) when list.isEmpty => AudioNote(
            text: i18n.t('audio-no-courses'),
          ),
          AsyncData(value: final list) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [for (final course in list) _Course(course: course)],
          ),
          AsyncError(:final error) => AudioNote(
            text: i18n.errorText(error),
            error: true,
          ),
          _ => const SizedBox.shrink(),
        },
      ],
    );
  }
}

class _Course extends StatelessWidget {
  const _Course({required this.course});

  final AudioCourse course;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final i18n = I18n.of(context);
    final lessons = [...course.lessons]
      ..sort((a, b) => a.number.compareTo(b.number));
    final next = nextLesson(lessons);
    return Padding(
      padding: const EdgeInsets.only(top: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 16,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Semantics(
                header: true,
                child: Text(course.name, style: theme.textTheme.titleLarge),
              ),
              if (next != null)
                FilledButton.tonalIcon(
                  onPressed: () =>
                      context.go(lessonPath(course.id, next.number)),
                  icon: const Icon(Icons.play_arrow),
                  label: Text(i18n.t('audio-continue')),
                ),
            ],
          ),
          const SizedBox(height: 4),
          for (final lesson in lessons)
            Row(
              children: [
                SizedBox(
                  width: 32,
                  child: Text(
                    '${lesson.number}.',
                    textAlign: TextAlign.end,
                    style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
                  ),
                ),
                Flexible(
                  child: TextButton(
                    onPressed: () =>
                        context.go(lessonPath(course.id, lesson.number)),
                    child: Text(lesson.title),
                  ),
                ),
                _LessonProgress(lesson: lesson),
              ],
            ),
        ],
      ),
    );
  }
}

/// A check mark for a finished lesson, and a bar with the percentage for a
/// lesson that the user started. Nothing for a lesson that the user never
/// played.
class _LessonProgress extends StatelessWidget {
  const _LessonProgress({required this.lesson});

  final AudioLesson lesson;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    if (lesson.finished) {
      // An icon: the bundled fonts have no ✓, and the browser would fetch
      // a font from Google for it.
      return Semantics(
        label: i18n.t('audio-finished'),
        child: const ExcludeSemantics(
          child: Icon(Icons.check, color: Color(0xFF2E7D32), size: 20),
        ),
      );
    }
    if (lesson.position <= 0 || lesson.duration <= 0) {
      return const SizedBox.shrink();
    }
    final fraction = (lesson.position / lesson.duration).clamp(0.0, 1.0);
    // A started lesson shows at least 1 %, and 100 % only when finished.
    final percent = (fraction * 100).floor().clamp(1, 99);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        ExcludeSemantics(
          child: SizedBox(
            width: 64,
            child: LinearProgressIndicator(
              value: fraction,
              minHeight: 4,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          i18n.t('audio-percent', {'percent': '$percent'}),
          style: TextStyle(color: muted),
        ),
      ],
    );
  }
}
