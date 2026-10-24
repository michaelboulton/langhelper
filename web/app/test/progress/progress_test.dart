import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';
import 'package:langhelper_app/i18n/i18n.dart';
import 'package:langhelper_app/main.dart';
import 'package:langhelper_app/progress/charts.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';
import '../flashcards/flashcards_test.dart' show tap;

/// Show the app and open the Progress tab.
Future<void> openProgress(WidgetTester tester, FakeServer server) async {
  await tester.binding.setSurfaceSize(const Size(900, 1000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(appOn(server));
  await tester.pumpAndSettle();
  await tap(tester, find.widgetWithText(Tab, 'Progress'));
}

/// 90 days with a fixed pattern: days with no answer, days with only
/// "Again", and days where all passed.
List<StatsDay> fixedDays() => [
  for (var index = 0; index < 90; index++)
    if (index % 9 == 4 ? 0 : (index * 7) % 13 + 1 case final reviews)
      StatsDay(
        date: DateTime.utc(
          2026,
          7,
          27 + index,
        ).toIso8601String().substring(0, 10),
        reviews: reviews,
        passed: switch (index % 5) {
          0 => 0,
          1 => reviews,
          _ => reviews ~/ 2,
        },
      ),
];

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('the tab, its address and the numbers', (tester) async {
    final server = FakeServer();
    await openProgress(tester, server);
    final router = tester
        .widget<LanghelperApp>(find.byType(LanghelperApp))
        .router;
    expect(router.routerDelegate.currentConfiguration.uri.path, '/progress');
    expect(
      find.byWidgetPredicate(
        (widget) => widget is Title && widget.title == 'Progress',
      ),
      findsOne,
    );
    // The user is no admin, and the own numbers need no `of`.
    expect(find.text('Cards of'), findsNothing);
    expect(server.statsQueries.single, isEmpty);
    expect(find.text('Answers'), findsOne);
    expect(find.text('Not "Again"'), findsOne);
    expect(find.text('100%'), findsOne);
    expect(find.text('Days in a row'), findsOne);
    expect(find.text('2 (0 new · 2 in learning · 0 due)'), findsOne);
    expect(find.byType(DayBars), findsNWidgets(2));
  });

  testWidgets('each opening of the tab loads the numbers again', (
    tester,
  ) async {
    final server = FakeServer();
    await openProgress(tester, server);
    await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
    await tap(tester, find.widgetWithText(Tab, 'Progress'));
    expect(server.statsQueries, hasLength(2));
  });

  testWidgets('no answers yet: a note and no charts', (tester) async {
    final server = FakeServer(
      stats: (_) async =>
          json({...fixture('stats.json'), 'reviews': 0, 'success_rate': null}),
    );
    await openProgress(tester, server);
    expect(find.text('No answers yet.'), findsOne);
    expect(find.text('Answers'), findsNothing);
    expect(find.byType(DayBars), findsNothing);
  });

  testWidgets('an error: the text and no numbers', (tester) async {
    final server = FakeServer(
      stats: (_) async => json({'detail': 'Database locked.'}, 500),
    );
    await openProgress(tester, server);
    expect(find.text('The server returned 500. Database locked.'), findsOne);
    expect(find.text('Answers'), findsNothing);
  });

  testWidgets('an admin selects another user', (tester) async {
    final server = FakeServer(
      users: {
        'me': 'local',
        'admin': true,
        'users': [
          {'id': 'local', 'name': 'My cards'},
          {'id': 'sub-2', 'name': 'Ana'},
        ],
      },
    );
    await openProgress(tester, server);
    expect(find.text('Cards of'), findsOne);
    await tap(tester, find.byType(DropdownButton<String>));
    await tap(tester, find.text('Ana').last);
    expect(server.statsQueries.last, {'of': 'sub-2'});
    // The choice stays when the tab opens again.
    await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
    await tap(tester, find.widgetWithText(Tab, 'Progress'));
    expect(server.statsQueries.last, {'of': 'sub-2'});
    await tap(tester, find.byType(DropdownButton<String>));
    await tap(tester, find.text('My cards').last);
    expect(server.statsQueries.last, isEmpty);
  });

  testWidgets('the bar charts', (tester) async {
    // The letters, not the boxes of the test font.
    final font = FontLoader('NotoSans')
      ..addFont(rootBundle.load('assets/fonts/NotoSans-Regular.ttf'));
    await tester.runAsync(font.load);
    await tester.binding.setSurfaceSize(const Size(480, 320));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      I18nScope(
        i18n: english(),
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: theme(Brightness.light),
          home: Scaffold(
            body: Padding(
              padding: const EdgeInsets.all(8),
              child: ProgressCharts(days: fixedDays()),
            ),
          ),
        ),
      ),
    );
    await expectLater(
      find.byType(ProgressCharts),
      matchesGoldenFile('goldens/charts.png'),
    );
  });
}
