import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';
import 'package:langhelper_app/breakdown/links.dart';
import 'package:langhelper_app/flashcards/card_view.dart';
import 'package:langhelper_app/flashcards/decks.dart';
import 'package:langhelper_app/flashcards/diff.dart';
import 'package:langhelper_app/flashcards/time.dart';
import 'package:langhelper_app/flashcards/voices.dart';
import 'package:langhelper_app/main.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';

Finder button(String text) => find.ancestor(
  of: find.text(text),
  matching: find.byWidgetPredicate((widget) => widget is ButtonStyleButton),
);

bool filled(WidgetTester tester, String text) =>
    tester.widget(button(text)) is FilledButton;

/// The address of the app.
String address(WidgetTester tester) => tester
    .widget<LanghelperApp>(find.byType(LanghelperApp))
    .router
    .routerDelegate
    .currentConfiguration
    .uri
    .path;

Future<void> tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Show the app, open the Flashcards tab and the deck "Basics".
Future<void> openDeck(WidgetTester tester, FakeServer server) async {
  await tester.binding.setSurfaceSize(const Size(900, 1400));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(appOn(server));
  await tester.pumpAndSettle();
  await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
  await tap(tester, find.text('Basics'));
}

/// Type [text] and press Enter.
Future<void> answer(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(answerFieldKey), text);
  await tester.testTextInput.receiveAction(TextInputAction.done);
  await tester.pumpAndSettle();
}

Map<String, dynamic> deck(int id, List<String> path, int newCards) => {
  'id': id,
  'name': path.join('::'),
  'language': 'hr',
  'path': path,
  'counts': {'total': newCards, 'new': newCards, 'learning': 0, 'due': 0},
};

/// The next card, with [media].
Map<String, dynamic> withMedia(List<Map<String, String>> media) => {
  ...fixture('next.json'),
  'media': media,
};

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  group('the tree of decks', () {
    final decks = DecksResponse.fromJson({
      'decks': [
        deck(1, ['Neri', 'Read', '2'], 2),
        deck(2, ['Neri', 'Read', '3'], 3),
        deck(3, ['Neri', 'Speak', '2'], 4),
        deck(4, [], 1),
      ],
    }).decks;

    test('each part of a path is a group, in the order of the server', () {
      final root = deckTree(decks);
      final [neri as DeckGroup, plain as Deck] = root.items;
      expect(neri.name, 'Neri');
      expect(neri.decks.map((each) => each.id), [1, 2, 3]);
      final [read as DeckGroup, speak as DeckGroup] = neri.items;
      expect((read.name, read.depth), ('Read', 1));
      expect(read.items, [decks[0], decks[1]]);
      expect(speak.items, [decks[2]]);
      expect(plain.id, 4);
    });

    test('the counts of a group are the sums of its decks', () {
      final sum = sumCounts(decks.take(3));
      expect((sum.total, sum.newCards, sum.learning, sum.due), (9, 9, 0, 0));
    });

    testWidgets('a heading with a summary for each group', (tester) async {
      final server = FakeServer(decks: {'decks': decks});
      await tester.pumpWidget(appOn(server));
      await tester.pumpAndSettle();
      await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
      expect(find.text('3 decks · 9 new · 0 in learning · 0 due'), findsOne);
      expect(find.text('2 decks · 5 new · 0 in learning · 0 due'), findsOne);
      // A deck in a group shows the last part of its path.
      expect(find.text('3'), findsOne);
      expect(find.text('Croatian · 3 cards'), findsOne);
    });
  });

  group('the relative time', () {
    final now = DateTime.utc(2026, 10, 24, 9);

    test('rounds to the nearest unit', () {
      Duration? at(Duration offset) =>
          switch (relativeParts(now.add(offset), now)) {
            null => null,
            (final amount, 'minute') => Duration(minutes: amount),
            (final amount, 'hour') => Duration(hours: amount),
            (final amount, _) => Duration(days: amount),
          };
      expect(at(const Duration(seconds: 20)), isNull);
      expect(at(const Duration(minutes: 5)), const Duration(minutes: 5));
      expect(at(const Duration(minutes: 89)), const Duration(minutes: 89));
      expect(at(const Duration(minutes: 100)), const Duration(hours: 2));
      expect(at(const Duration(hours: 35)), const Duration(hours: 35));
      expect(at(const Duration(hours: 40)), const Duration(days: 2));
    });

    test('now, and the English outside a browser', () {
      final i18n = english();
      expect(when(i18n, '2026-10-24T09:00:10Z', now: now), 'now');
      expect(when(i18n, '2026-10-24T09:01:00Z', now: now), 'in 1 minute');
      expect(when(i18n, '2026-10-27T09:00:00Z', now: now), 'in 3 days');
    });
  });

  testWidgets('the tab is in the address', (tester) async {
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    expect(address(tester), '/');
    await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
    expect(address(tester), '/cards');
    // The title of the app bar and of the browser tab.
    expect(
      find.byWidgetPredicate(
        (widget) => widget is Title && widget.title == 'Flashcards',
      ),
      findsOne,
    );
    expect(find.text('Basics'), findsOne);
    expect(find.text('Croatian · 2 cards'), findsOne);
    expect(find.text('2 new · 0 in learning · 0 due'), findsOne);
    await tap(tester, find.widgetWithText(Tab, 'Breakdown'));
    expect(address(tester), '/');
    expect(find.text('Croatian sentence breakdown'), findsOne);
  });

  testWidgets('no decks: a note', (tester) async {
    final server = FakeServer(decks: {'decks': <Object>[]});
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tap(tester, find.widgetWithText(Tab, 'Flashcards'));
    expect(find.textContaining('No decks.'), findsOne);
  });

  testWidgets('a card, the answer, the diff and the links', (tester) async {
    final server = FakeServer();
    await openDeck(tester, server);
    expect(server.nextQueries.single, {'heavy': 'false'});
    expect(find.text('Basics'), findsOne);
    expect(find.text('Enter this in Croatian.'), findsOne);
    expect(find.bySemanticsLabel('chip: coffee NOUN'), findsOne);
    expect(button('Check'), findsOne);
    expect(button('Next card'), findsNothing);

    await answer(tester, 'Pijem kafu.');
    expect(server.answers.single['typed'], 'Pijem kafu.');
    expect(server.answers.single['heavy'], isFalse);
    expect(server.answers.single['elapsed_ms'], isA<int>());
    expect(find.byKey(answerFieldKey), findsNothing);
    expect(find.text('Your answer'), findsOne);
    expect(find.text('The correct answer'), findsOne);
    expect(find.bySemanticsLabel('chip: kafu NOUN'), findsOne);
    expect(find.bySemanticsLabel('chip: kavu NOUN'), findsOne);
    final diff = tester.widget<DiffText>(find.byType(DiffText));
    expect(diff.diff.map((span) => span.op), [
      DiffOp.equal,
      DiffOp.delete,
      DiffOp.insert,
      DiffOp.equal,
    ]);
    // One answer: no list of the accepted answers.
    expect(find.text('All accepted answers:'), findsNothing);

    // "kafu" over "coffee", and "coffee" over "kavu".
    final painter =
        tester
                .widget<CustomPaint>(
                  find.byWidgetPredicate(
                    (widget) =>
                        widget is CustomPaint && widget.painter is LinkPainter,
                  ),
                )
                .painter!
            as LinkPainter;
    expect(painter.lines, hasLength(2));
    final top = tester.getRect(find.bySemanticsLabel('chip: kafu NOUN'));
    final middle = tester.getRect(find.bySemanticsLabel('chip: coffee NOUN'));
    final bottom = tester.getRect(find.bySemanticsLabel('chip: kavu NOUN'));
    expect(top.bottom, lessThan(middle.top));
    expect(middle.bottom, lessThan(bottom.top));

    // The rating of the server, and the time of the next review.
    expect(filled(tester, '2 Hard'), isTrue);
    expect(filled(tester, '3 Good'), isFalse);
    expect(find.textContaining('Hard: this card comes back '), findsOne);

    // A tap on a chip shows its table.
    await tap(tester, find.bySemanticsLabel('chip: kavu NOUN'));
    expect(find.text('kava'), findsWidgets);
    expect(find.text('Base form (lemma)'), findsOne);
  });

  testWidgets('the keys 1 to 4 change the rating', (tester) async {
    final server = FakeServer();
    await openDeck(tester, server);
    await answer(tester, 'Pijem kafu.');
    await tester.sendKeyEvent(LogicalKeyboardKey.digit3);
    await tester.pumpAndSettle();
    expect(server.ratings, [
      {'rating': 3},
    ]);
    expect(filled(tester, '3 Good'), isTrue);
    expect(filled(tester, '2 Hard'), isFalse);
    expect(find.textContaining('Good: this card comes back '), findsOne);

    await tap(tester, button('4 Easy'));
    expect(server.ratings.last, {'rating': 4});
    expect(filled(tester, '4 Easy'), isTrue);
  });

  testWidgets('a digit in the answer is text, not a rating', (tester) async {
    final server = FakeServer();
    await openDeck(tester, server);
    await tester.showKeyboard(find.byKey(answerFieldKey));
    await tester.sendKeyEvent(LogicalKeyboardKey.digit1);
    await tester.pumpAndSettle();
    expect(server.ratings, isEmpty);
  });

  testWidgets('Enter in an input method does not send the answer', (
    tester,
  ) async {
    final server = FakeServer();
    await openDeck(tester, server);
    await tester.showKeyboard(find.byKey(answerFieldKey));
    // An input method makes "kavu" of many keys. Its Enter accepts the word.
    tester.testTextInput.updateEditingValue(
      const TextEditingValue(
        text: 'Pijem kavu',
        selection: TextSelection.collapsed(offset: 10),
        composing: TextRange(start: 6, end: 10),
      ),
    );
    await tester.pump();
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(server.answers, isEmpty);
    expect(find.byKey(answerFieldKey), findsOne);

    // The word is done: Enter sends.
    tester.testTextInput.updateEditingValue(
      const TextEditingValue(
        text: 'Pijem kavu',
        selection: TextSelection.collapsed(offset: 10),
      ),
    );
    await tester.pump();
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(server.answers.single['typed'], 'Pijem kavu');
  });

  testWidgets('"I do not know", then Enter is the next card', (tester) async {
    final server = FakeServer();
    await openDeck(tester, server);
    await tap(tester, button('I do not know'));
    expect(server.answers.single['typed'], '');
    expect(find.text('No answer'), findsOne);

    // "Next card" has the focus.
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pumpAndSettle();
    expect(server.nextQueries, hasLength(2));
    expect(
      find.textContaining('No more cards for now. The next one is due '),
      findsOne,
    );
    expect(find.text('0 new · 2 in learning · 0 due'), findsOne);

    await tap(tester, button('All decks'));
    expect(find.text('Croatian · 2 cards'), findsOne);
  });

  testWidgets('the other accepted answers', (tester) async {
    final server = FakeServer(
      answer: (_) async => json({
        ...fixture('answer.json'),
        'answers': ['Pijem kavu.', 'Ja pijem kavu.'],
      }),
    );
    await openDeck(tester, server);
    await answer(tester, 'Pijem kafu.');
    expect(find.text('All accepted answers:'), findsOne);
    expect(find.text('Ja pijem kavu.'), findsOne);
  });

  testWidgets('a picture, and the first clip plays on its own', (tester) async {
    final server = FakeServer(
      next: [
        withMedia([
          {'kind': 'image', 'url': '/api/v1/decks/1/media/house.png'},
          {'kind': 'audio', 'url': '/api/v1/decks/1/media/a.mp3'},
          {'kind': 'audio', 'url': '/api/v1/decks/1/media/b.mp3'},
        ]),
        fixture('next_done.json'),
      ],
    );
    await openDeck(tester, server);
    final image = tester.widget<Image>(find.byType(Image));
    expect(
      (image.image as NetworkImage).url,
      'https://example.fly.dev/api/v1/decks/1/media/house.png',
    );
    final [first, second] = server.players;
    expect(first.uris.single.path, '/api/v1/decks/1/media/a.mp3');
    expect(first.plays, 1);
    expect(second.uris.single.path, '/api/v1/decks/1/media/b.mp3');
    expect(second.plays, 0);
    expect(find.byTooltip('Pause'), findsOne);
    expect(find.byTooltip('Play'), findsOne);

    // A clip must not play on.
    await answer(tester, 'kuća');
    await tap(tester, button('Next card'));
    expect(first.disposed, isTrue);
    expect(second.disposed, isTrue);
  });

  group('read it aloud', () {
    testWidgets('with no voice service, the voices of the browser', (
      tester,
    ) async {
      final server = FakeServer();
      await openDeck(tester, server);
      await answer(tester, 'Pijem kafu.');
      await tap(tester, button('Read it aloud'));
      // The correct answer: the card asks for the study language.
      expect(server.voices.spoken, [('Pijem kavu.', 'hr-HR')]);
      expect(server.spoken, isEmpty);
    });

    testWidgets('a browser with no voices says so', (tester) async {
      final server = FakeServer()..voices.failure = const NoVoices();
      await openDeck(tester, server);
      await answer(tester, 'Pijem kafu.');
      await tap(tester, button('Read it aloud'));
      expect(find.textContaining('This browser has no voices'), findsOne);
    });

    testWidgets('a browser with no voice of the language says so', (
      tester,
    ) async {
      final server = FakeServer()..voices.failure = const NoVoice();
      await openDeck(tester, server);
      await answer(tester, 'Pijem kafu.');
      await tap(tester, button('Read it aloud'));
      expect(find.text('This browser has no Croatian voice.'), findsOne);
    });

    testWidgets('the voice service, when it reads the language', (
      tester,
    ) async {
      final server = FakeServer(speech: fixture('speech.json'));
      await openDeck(tester, server);
      await answer(tester, 'Pijem kafu.');
      await tap(tester, button('Read it aloud'));
      expect(server.spoken.single, {'text': 'Pijem kavu.', 'language': 'hr'});
      expect(server.voices.spoken, isEmpty);
      final player = server.players.single;
      expect(player.loaded, [mp3]);
      expect(player.plays, 1);
      expect(find.text('k2-fsa/OmniVoice read this.'), findsOne);

      // Again: the sound is there.
      await tap(tester, button('Read it aloud'));
      expect(server.spoken, hasLength(1));
      expect(player.plays, 2);
    });

    testWidgets('neither: no button', (tester) async {
      final server = FakeServer()..voices.available = false;
      await openDeck(tester, server);
      await answer(tester, 'Pijem kafu.');
      expect(button('Next card'), findsOne);
      expect(button('Read it aloud'), findsNothing);
    });
  });

  testWidgets('the diff', (tester) async {
    final languages = LanguagesResponse.fromJson(fixture('languages.json'));
    final croatian = languages.languages.first;
    final answered = AnswerResponse.fromJson(fixture('answer.json'));
    // The letters, not the boxes of the test font: the line through a
    // wrong letter shows.
    final font = FontLoader('NotoSans')
      ..addFont(rootBundle.load('assets/fonts/NotoSans-Regular.ttf'));
    await tester.runAsync(font.load);
    await tester.binding.setSurfaceSize(const Size(320, 60));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: theme(Brightness.light),
        home: Scaffold(
          body: Padding(
            padding: const EdgeInsets.all(8),
            child: DiffText(diff: answered.diff, info: croatian),
          ),
        ),
      ),
    );
    await expectLater(
      find.byType(DiffText),
      matchesGoldenFile('goldens/diff.png'),
    );
  });
}
