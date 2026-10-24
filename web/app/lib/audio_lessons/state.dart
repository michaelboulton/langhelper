import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../providers.dart';

/// An error shows at once: a missing course does not come back on a retry.
Duration? _noRetry(int count, Object error) => null;

/// The courses of DATA_ROOT/audio/, read one time.
final audioCoursesProvider = FutureProvider<List<AudioCourse>>(
  (ref) async => (await ref.watch(apiProvider).audioLessons.courses()).courses,
  retry: _noRetry,
);

/// A lesson of a course: the name of its folder and its number.
typedef LessonId = ({String course, int number});

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
