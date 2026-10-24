import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';
import 'package:langhelper_app/breakdown/form.dart';
import 'package:langhelper_app/breakdown/state.dart';
import 'package:langhelper_app/breakdown/tags.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';

/// The Text of the word on a chip.
Finder wordText(String word) => find.descendant(
  of: find.bySemanticsLabel('chip: $word'),
  matching: find.text(word.split(' ').first),
);

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  group('tags', () {
    final words = [
      for (final sentence in ClassifyResponse.fromJson(
        fixture('classify.json'),
      ).sentences)
        ...sentence.words,
    ];

    test('the feature note', () {
      expect(featNote(words[0]), 'N/F/S'); // Ona: a pronoun
      expect(featNote(words[1]), 'F/3/S'); // je: a finite verb
      expect(featNote(words[3]), 'P/F/S'); // bila: a participle
      expect(featNote(words[4]), ''); // kod: a preposition
      expect(featNote(words[5]), 'G/F/S'); // kuće
    });

    test('the id of a tag', () {
      expect(tagId('feat', 'Number[psor]'), 'feat-Number-psor');
      expect(tagId('upos', 'NOUN'), 'upos-NOUN');
    });

    test('a problem with a list of cases', () {
      const word = Word(
        id: 1,
        text: 'u',
        lemma: 'u',
        upos: 'ADP',
        xpos: 'Sl',
        feats: {},
        startChar: 0,
        endChar: 1,
        problems: ['English'],
        problemMessages: [
          ProblemMessage(
            key: 'problem-preposition-cases',
            params: {
              'word': 'u',
              'want': ['Acc', 'Loc'],
              'got': 'Nom',
            },
          ),
        ],
      );
      expect(
        problemText(english(), word, 0, (_) => null),
        "The preposition 'u' takes the accusative or the locative, "
        'but this form is nominative.',
      );
    });
  });

  testWidgets('a change sends the form after 500 ms', (tester) async {
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(textFieldKey), 'Ona');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.enterText(
      find.byKey(textFieldKey),
      'Ona je je bila kod kuće.',
    );
    await tester.pump(const Duration(milliseconds: 400));
    expect(server.classified, isEmpty);
    await tester.pump(const Duration(milliseconds: 100));
    expect(server.classified, hasLength(1));
    expect(server.classified.single, {
      'text': 'Ona je je bila kod kuće.',
      'language': 'hr',
      'heavy': false,
      'nonstandard': false,
      // A send of the debounce does not count the lemmas.
      'track': false,
      'translate': false,
      'source': 'study',
    });
    await tester.pumpAndSettle();
    expect(find.bySemanticsLabel('chip: Ona PRON'), findsOneWidget);
    expect(find.text('Models: Croatian light.'), findsOneWidget);
    // The same form again sends nothing.
    await tester.enterText(
      find.byKey(textFieldKey),
      'Ona je je bila kod kuće. ',
    );
    await tester.pump(debounceTime);
    expect(server.classified, hasLength(1));
  });

  testWidgets('Ctrl+Enter sends at once and counts the lemmas', (tester) async {
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(textFieldKey), 'Ona je bila kod kuće.');
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pump();
    expect(server.classified, hasLength(1));
    expect(server.classified.single['track'], isTrue);
    // The debounce of the typed text does not send again.
    await tester.pumpAndSettle();
    expect(server.classified, hasLength(1));
  });

  testWidgets('Cancel stops the request', (tester) async {
    final server = FakeServer(classify: never);
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(textFieldKey), 'Ona je bila kod kuće.');
    await tester.pump(debounceTime);
    expect(server.classified, hasLength(1));
    await tester.pump();
    expect(find.text('Working.'), findsOneWidget);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
    await tester.pumpAndSettle();
    expect(find.text('Canceled.'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsNothing);
  });

  testWidgets('the time limit stops the request', (tester) async {
    final server = FakeServer(classify: never);
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(textFieldKey), 'Ona je bila kod kuće.');
    await tester.pump(debounceTime);
    await tester.pump(const Duration(seconds: 5));
    expect(find.textContaining('No answer after 5 s.'), findsOneWidget);
  });

  testWidgets('a chip row with a problem, and the table of a word', (
    tester,
  ) async {
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(textFieldKey),
      'Ona je je bila kod kuće.',
    );
    await tester.pump(debounceTime);
    await tester.pumpAndSettle();
    final chips = find.bySemanticsLabel(RegExp('^chip: '));
    // The Croatian words, and the English words of the translation.
    expect(chips, findsNWidgets(7 + 5));
    // Only the second "je" fails a check. Each chip has "je" as the word and
    // as the accent.
    final underlined = [
      for (final element in find.text('je').evaluate())
        (element.widget as Text).style?.decoration == TextDecoration.underline,
    ];
    expect(underlined, [false, false, true, false]);
    final style = tester.widget<Text>(find.text('je').at(2)).style!;
    expect(style.decorationStyle, TextDecorationStyle.wavy);
    expect(style.decorationColor, problemRed);
    // The colour of the part of speech, and the feature note.
    final chip = tester.widget<Material>(
      find
          .ancestor(of: find.text('kuće'), matching: find.byType(Material))
          .first,
    );
    expect(chip.color, uposColors['NOUN']);
    expect(find.text('NOUN (G/F/S)'), findsOneWidget);
    // The accent line: the dictionary form in parentheses, a dash with no
    // data.
    expect(find.text('(bȉti)'), findsOneWidget);
    expect(find.text('–'), findsOneWidget);

    await tester.ensureVisible(find.text('je').at(2));
    await tester.tap(find.text('je').at(2));
    await tester.pumpAndSettle();
    expect(find.text("• 'je' repeats."), findsOneWidget);
    Color border(int index) {
      final chip = tester.widget<Material>(
        find
            .ancestor(
              of: find.text('je').at(index),
              matching: find.byType(Material),
            )
            .first,
      );
      return (chip.shape! as RoundedRectangleBorder).side.color;
    }

    // The selected chip has a border.
    expect(border(0), Colors.transparent);
    expect(border(2), isNot(Colors.transparent));
    expect(find.text('Base form (lemma)'), findsOneWidget);
    expect(find.text('dict.cc: biti'), findsOneWidget);
    final links = find.byWidgetPredicate(
      (widget) => widget is Semantics && widget.properties.link == true,
    );
    expect(
      [
        for (final element in links.evaluate())
          (element.widget as Semantics).properties.linkUrl,
      ],
      [
        Uri.parse('https://enhr.dict.cc/?s=biti'),
        Uri.parse('https://hjp.znanje.hr/'),
      ],
    );
  });

  testWidgets('the translation goes under its sentence', (tester) async {
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Translate to English'));
    await tester.enterText(
      find.byKey(textFieldKey),
      'Ona je je bila kod kuće.',
    );
    await tester.pump(debounceTime);
    await tester.pumpAndSettle();
    expect(server.classified.single['translate'], isTrue);
    final study = tester.getRect(wordText('Ona PRON'));
    final english = tester.getRect(wordText('She PRON'));
    expect(english.top, greaterThan(study.bottom + 56));
    expect(find.text('English: She was at home.'), findsOneWidget);
  });

  testWidgets('the form comes back from shared_preferences', (tester) async {
    final preferences = SharedPreferencesAsync();
    await preferences.setString(
      entryKey,
      jsonEncode({
        'source': 'en',
        'language': 'de',
        'text': 'She was at home.',
        'nonstandard': false,
        'translate': true,
      }),
    );
    await preferences.setBool(heavyKey, true);
    final server = FakeServer();
    await tester.pumpWidget(appOn(server));
    await tester.pumpAndSettle();
    expect(find.text('German sentence breakdown'), findsOneWidget);
    final field = tester.widget<TextField>(find.byKey(textFieldKey));
    expect(field.controller!.text, 'She was at home.');
    expect(server.classified.single, {
      'text': 'She was at home.',
      'language': 'de',
      'heavy': true,
      'nonstandard': false,
      'track': false,
      'translate': true,
      'source': 'en',
    });
    // The light note is for Croatian, and the accents too.
    expect(find.textContaining('The small Croatian model'), findsNothing);
    expect(find.textContaining('Accent marks'), findsNothing);

    await tester.tap(
      find.text(
        'Large models (more exact, and the first request waits for their load)',
      ),
    );
    await tester.pumpAndSettle();
    expect(await preferences.getBool(heavyKey), isFalse);
  });

  testWidgets('a text typed before the list loads stays', (tester) async {
    await SharedPreferencesAsync().setString(
      entryKey,
      jsonEncode({'text': 'She was at home.'}),
    );
    final ready = Completer<void>();
    final server = FakeServer(languagesReady: ready.future);
    await tester.pumpWidget(appOn(server));
    await tester.enterText(find.byKey(textFieldKey), 'Ona je bila kod kuće.');
    await tester.pump(debounceTime);
    // No language yet: the form sends nothing.
    expect(server.classified, isEmpty);
    ready.complete();
    await tester.pumpAndSettle();
    final field = tester.widget<TextField>(find.byKey(textFieldKey));
    expect(field.controller!.text, 'Ona je bila kod kuće.');
    expect(server.classified.single['text'], 'Ona je bila kod kuće.');
  });

  testWidgets('the legend has each part of speech', (tester) async {
    await tester.pumpWidget(appOn(FakeServer()));
    await tester.pumpAndSettle();
    expect(find.text('NOUN noun'), findsOneWidget);
    expect(find.text('X other'), findsOneWidget);
    // Croatian has accent data.
    expect(find.textContaining('Accent marks:'), findsOneWidget);
  });
}
