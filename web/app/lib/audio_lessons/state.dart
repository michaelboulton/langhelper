import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../providers.dart';

/// An error shows at once: a missing course does not come back on a retry.
Duration? _noRetry(int count, Object error) => null;

/// A lesson of a course: the name of its folder and its number.
typedef LessonId = ({String course, int number});

final audioCoursesProvider =
    AsyncNotifierProvider<AudioCourses, List<AudioCourse>>(
      AudioCourses.new,
      retry: _noRetry,
    );

/// The courses of DATA_ROOT/audio/, read one time. A saved position
/// changes its lesson in the list, so the list needs no new read.
class AudioCourses extends AsyncNotifier<List<AudioCourse>> {
  @override
  Future<List<AudioCourse>> build() async =>
      (await ref.watch(apiProvider).audioLessons.courses()).courses;

  /// Saves where the user is in the lesson [id].
  Future<void> save(LessonId id, Duration position, Duration duration) async {
    final AudioProgressResponse saved;
    try {
      saved = await ref
          .read(apiProvider)
          .audioLessons
          .saveProgress(
            id.course,
            id.number,
            AudioProgressRequest(
              position: seconds(position),
              duration: seconds(duration),
            ),
          );
    } on Object catch (error) {
      debugPrint('audio: no save of $id: $error');
      return;
    }
    if (!ref.mounted) return;
    final courses = state.value;
    if (courses == null) return;
    state = AsyncData([
      for (final course in courses)
        if (course.id != id.course)
          course
        else
          AudioCourse(
            id: course.id,
            name: course.name,
            language: course.language,
            lessons: [
              for (final lesson in course.lessons)
                if (lesson.number != id.number)
                  lesson
                else
                  AudioLesson(
                    number: lesson.number,
                    title: lesson.title,
                    audio: lesson.audio,
                    position: saved.position,
                    duration: saved.duration,
                    finished: saved.finished,
                  ),
            ],
          ),
    ]);
  }
}

/// The script of one lesson.
final audioLessonProvider = FutureProvider.autoDispose
    .family<AudioLessonResponse, LessonId>(
      (ref, id) =>
          ref.watch(apiProvider).audioLessons.lesson(id.course, id.number),
      retry: _noRetry,
    );

/// The address of a lesson in the app.
String lessonPath(String course, int number) =>
    '/audio/${Uri.encodeComponent(course)}/$number';

double seconds(Duration time) => time.inMilliseconds / 1000;

Duration fromSeconds(double seconds) =>
    Duration(milliseconds: (seconds * 1000).round());

/// The lesson of [lessons] that the Continue button opens: the first one,
/// in order, that is not finished. Null when all are finished.
AudioLesson? nextLesson(List<AudioLesson> lessons) {
  final sorted = [...lessons]..sort((a, b) => a.number.compareTo(b.number));
  for (final lesson in sorted) {
    if (!lesson.finished) return lesson;
  }
  return null;
}
