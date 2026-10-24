import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:langhelper_app/audio_lessons/lesson_player.dart';
import 'package:langhelper_app/main.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';
import '../flashcards/flashcards_test.dart' show tap;

/// The saved course, with the audio state [audio] for lesson 1, and the
/// keys of [first] and [second] in lessons 1 and 2.
Future<http.Response> Function(http.Request) courses(
  String audio, {
  Map<String, dynamic> first = const {},
  Map<String, dynamic> second = const {},
}) {
  final body = fixture('audio_lessons.json');
  final course = (body['courses'] as List).single as Map<String, dynamic>;
  final lessons = (course['lessons'] as List).cast<Map<String, dynamic>>();
  lessons.first
    ..['audio'] = audio
    ..addAll(first);
  lessons.last.addAll(second);
  return (_) async => json(body);
}

/// Lesson 1 with its sound, started at 30.5 s of 120 s.
final started = courses(
  'ready',
  first: {'position': 30.5, 'duration': 120.0, 'finished': false},
);

GoRouter router(WidgetTester tester) =>
    tester.widget<LanghelperApp>(find.byType(LanghelperApp)).router;

String path(WidgetTester tester) =>
    router(tester).routerDelegate.currentConfiguration.uri.path;

/// Show the app and open the Audio lessons tab.
Future<void> openTab(WidgetTester tester, FakeServer server) async {
  await tester.binding.setSurfaceSize(const Size(900, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(appOn(server));
  await tester.pumpAndSettle();
  await tap(tester, find.widgetWithText(Tab, 'Audio lessons'));
}

/// Open lesson 1 of the course.
Future<void> openLesson(WidgetTester tester, FakeServer server) async {
  await openTab(tester, server);
  await tap(tester, find.text('Is there meat in this dish?'));
}

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('the courses and their lessons in order', (tester) async {
    final server = FakeServer();
    await openTab(tester, server);
    expect(path(tester), '/audio');
    expect(
      find.byWidgetPredicate(
        (widget) => widget is Title && widget.title == 'Audio lessons',
      ),
      findsOne,
    );
    expect(find.text('Italian'), findsOne);
    final first = tester.getRect(find.text('Is there meat in this dish?'));
    final second = tester.getRect(find.text('Where is the station?'));
    expect(first.top, lessThan(second.top));
    expect(find.text('1.'), findsOne);
    expect(find.text('2.'), findsOne);
  });

  testWidgets('no courses', (tester) async {
    final server = FakeServer(
      audioCourses: (_) async => json({'courses': <Object>[]}),
    );
    await openTab(tester, server);
    expect(find.text('No audio lessons yet.'), findsOne);
  });

  testWidgets('an error of the list', (tester) async {
    final server = FakeServer(
      audioCourses: (_) async => json({'detail': 'Broken.'}, 500),
    );
    await openTab(tester, server);
    expect(find.text('The server returned 500. Broken.'), findsOne);
    expect(find.text('Italian'), findsNothing);
  });

  testWidgets('a lesson with no sound: the script and no player', (
    tester,
  ) async {
    final server = FakeServer();
    await openLesson(tester, server);
    expect(path(tester), '/audio/it-course/1');
    expect(server.lessons, ['/api/v1/audio-lessons/it-course/1']);
    expect(find.text('Is there meat in this dish?'), findsOne);
    expect(find.text('"there is / there isn\'t" (c\'è, non c\'è).'), findsOne);
    expect(find.text('This lesson has no sound yet.'), findsOne);
    expect(server.players, isEmpty);
    expect(find.byTooltip('Play'), findsNothing);

    expect(find.text('Narrator:'), findsOne);
    expect(find.text('(pause, 3 s)'), findsOne);
    expect(find.text('You:'), findsOne);
    expect(find.text('Other person:'), findsOne);
    // The narrator speaks English, and the actors Italian.
    final narrator = tester.widget<Text>(
      find.text('How do you say "is there"?'),
    );
    expect(narrator.locale, const Locale('en'));
    final actor = tester.widget<Text>(find.text('No, non c\'è carne.'));
    expect(actor.locale, const Locale('it'));
    expect(actor.textDirection, TextDirection.ltr);

    await tap(tester, find.text('All lessons'));
    expect(path(tester), '/audio');
    expect(find.text('Where is the station?'), findsOne);
  });

  testWidgets('a lesson at its address', (tester) async {
    final server = FakeServer(audioCourses: courses('ready'));
    await openTab(tester, server);
    router(tester).go('/audio/it-course/1');
    await tester.pumpAndSettle();
    expect(find.text('"there is / there isn\'t" (c\'è, non c\'è).'), findsOne);
    expect(server.players.single.uris, [
      Uri.parse('https://example.fly.dev/api/v1/audio-lessons/it-course/1.mp3'),
    ]);
  });

  testWidgets('a lesson number that is not a number', (tester) async {
    final server = FakeServer();
    await openTab(tester, server);
    router(tester).go('/audio/it-course/x');
    await tester.pumpAndSettle();
    expect(path(tester), '/audio');
    expect(server.lessons, isEmpty);
  });

  testWidgets('a lesson whose script is newer than its sound', (tester) async {
    final server = FakeServer(audioCourses: courses('stale'));
    await openLesson(tester, server);
    expect(find.byTooltip('Play'), findsOne);
    expect(
      find.text(
        'The script changed after the sound was made, so the sound can '
        'differ from the text.',
      ),
      findsOne,
    );
  });

  testWidgets('the buttons of the player', (tester) async {
    final server = FakeServer(audioCourses: courses('ready'));
    await openLesson(tester, server);
    final player = server.players.single;
    expect(find.text('This lesson has no sound yet.'), findsNothing);

    await tap(tester, find.byTooltip('Play'));
    expect(player.plays, 1);
    await tap(tester, find.byTooltip('Pause'));
    expect(find.byTooltip('Play'), findsOne);

    // Back 10 s at 4 s goes to the start.
    player.currentPosition = const Duration(seconds: 4);
    await tap(tester, find.byTooltip('Back 10 s'));
    expect(player.seeks.last, Duration.zero);

    // Forward 10 s near the end stops at the end: the fake sound is 2 s.
    player.currentPosition = const Duration(milliseconds: 1500);
    await tap(tester, find.byTooltip('Forward 10 s'));
    expect(player.seeks.last, const Duration(seconds: 2));

    await tap(tester, find.text('0.75×'));
    await tap(tester, find.text('1.25×'));
    await tap(tester, find.text('1×'));
    expect(player.speeds, [0.75, 1.25, 1.0]);
  });

  testWidgets('the keys of the player', (tester) async {
    final server = FakeServer(audioCourses: courses('ready'));
    await openLesson(tester, server);
    final player = server.players.single;

    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    await tester.pumpAndSettle();
    expect(player.plays, 1);
    expect(find.byTooltip('Pause'), findsOne);
    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    await tester.pumpAndSettle();
    expect(find.byTooltip('Play'), findsOne);

    player.currentPosition = const Duration(milliseconds: 500);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    expect(player.seeks.last, const Duration(seconds: 2));
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
    expect(player.seeks.last, Duration.zero);
  });

  testWidgets('leaving the lesson stops its player', (tester) async {
    final server = FakeServer(audioCourses: courses('ready'));
    await openLesson(tester, server);
    await tap(tester, find.byTooltip('Play'));
    await tap(tester, find.text('All lessons'));
    expect(server.players.single.disposed, isTrue);
  });

  testWidgets('the progress of each lesson in the list', (tester) async {
    final server = FakeServer(
      audioCourses: courses(
        'none',
        second: {'position': 30.0, 'duration': 120.0, 'finished': false},
      ),
    );
    await openTab(tester, server);
    // Lesson 1 is finished, and the user is a quarter through lesson 2.
    expect(find.byIcon(Icons.check), findsOne);
    expect(find.bySemanticsLabel('Finished'), findsOne);
    expect(find.text('25%'), findsOne);
    final bar = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(bar.value, 0.25);
    final second = tester.getRect(find.text('Where is the station?'));
    expect(tester.getRect(find.text('25%')).center.dy, second.center.dy);

    await tap(tester, find.text('Continue'));
    expect(path(tester), '/audio/it-course/2');
  });

  testWidgets('a lesson that the user never played has no bar', (tester) async {
    final server = FakeServer(
      audioCourses: courses(
        'none',
        first: {'position': 0.0, 'duration': 0.0, 'finished': false},
      ),
    );
    await openTab(tester, server);
    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(find.byIcon(Icons.check), findsNothing);
    await tap(tester, find.text('Continue'));
    expect(path(tester), '/audio/it-course/1');
  });

  testWidgets('no Continue when all the lessons are finished', (tester) async {
    final server = FakeServer(
      audioCourses: courses('none', second: {'finished': true}),
    );
    await openTab(tester, server);
    expect(find.byIcon(Icons.check), findsNWidgets(2));
    expect(find.text('Continue'), findsNothing);
  });

  testWidgets('the player starts at the saved position and saves it', (
    tester,
  ) async {
    final server = FakeServer(audioCourses: started)
      ..soundLength = const Duration(minutes: 2);
    await openTab(tester, server);
    expect(find.text('25%'), findsOne);
    await tap(tester, find.text('Continue'));
    expect(path(tester), '/audio/it-course/1');
    final player = server.players.single;
    expect(player.seeks, [const Duration(milliseconds: 30500)]);
    expect(server.saves, isEmpty);

    // Every 10 s while it plays.
    await tap(tester, find.byTooltip('Play'));
    player.currentPosition = const Duration(seconds: 40);
    await tester.pump(saveEvery);
    expect(
      server.saves.single.$1,
      '/api/v1/audio-lessons/it-course/1/progress',
    );
    expect(server.saves.single.$2, {'position': 40.0, 'duration': 120.0});
    // The same position again is not saved again.
    await tester.pump(saveEvery);
    expect(server.saves, hasLength(1));

    // On pause.
    player.currentPosition = const Duration(seconds: 45);
    await tap(tester, find.byTooltip('Pause'));
    expect(server.saves.last.$2, {'position': 45.0, 'duration': 120.0});
    expect(server.saves, hasLength(2));
    // Ten seconds after the pause, no save.
    await tester.pump(saveEvery);
    expect(server.saves, hasLength(2));

    // When the user leaves the lesson, and the list shows the new position.
    player.currentPosition = const Duration(seconds: 60);
    await tap(tester, find.text('All lessons'));
    expect(server.saves.last.$2, {'position': 60.0, 'duration': 120.0});
    expect(server.saves, hasLength(3));
    expect(find.text('50%'), findsOne);
  });

  testWidgets('the end of a lesson marks it finished', (tester) async {
    final server = FakeServer(audioCourses: started)
      ..soundLength = const Duration(minutes: 2);
    await openLesson(tester, server);
    final player = server.players.single;
    await tap(tester, find.byTooltip('Play'));
    // At the end, the player stops as on a pause.
    player.currentPosition = const Duration(minutes: 2);
    player.pause();
    await tester.pumpAndSettle();
    expect(server.saves.single.$2, {'position': 120.0, 'duration': 120.0});
    await tap(tester, find.text('All lessons'));
    expect(server.saves, hasLength(1));
    expect(find.byIcon(Icons.check), findsOne);
    expect(find.byType(LinearProgressIndicator), findsNothing);
  });

  testWidgets('a lesson with no sound saves nothing', (tester) async {
    final server = FakeServer();
    await openLesson(tester, server);
    await tap(tester, find.text('All lessons'));
    expect(server.saves, isEmpty);
  });

  test('a saved position at the end starts the lesson again', () async {
    final player = FakePlayer();
    final saves = <Duration>[];
    final audio = LessonAudio(
      player,
      save: (position, _) => saves.add(position),
    )..duration = const Duration(minutes: 1);
    audio.start(const Duration(seconds: 57));
    expect(player.seeks, isEmpty);
    await audio.dispose();
    // The start is at 0, so the leave saves nothing.
    expect(saves, isEmpty);
  });

  test('back and forward 10 s in the middle of a lesson', () async {
    final player = FakePlayer();
    final audio = LessonAudio(player)..duration = const Duration(minutes: 1);
    player.currentPosition = const Duration(seconds: 30);
    audio.skip(skipStep);
    audio.skip(-skipStep);
    audio.skip(-skipStep);
    expect(player.seeks, const [
      Duration(seconds: 40),
      Duration(seconds: 30),
      Duration(seconds: 20),
    ]);
    await audio.dispose();
  });
}
