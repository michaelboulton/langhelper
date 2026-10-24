import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/breakdown/form.dart';
import 'package:langhelper_app/breakdown/state.dart';
import 'package:langhelper_app/explain/explain_panel.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';
import '../flashcards/flashcards_test.dart' show answer, openDeck;

Finder button(String text) => find.widgetWithText(OutlinedButton, text);

bool enabled(WidgetTester tester, String text) =>
    tester.widget<OutlinedButton>(button(text)).onPressed != null;

/// The questions of a server with a key for an AI service.
Map<String, dynamic> available() => {
  ...fixture('questions.json'),
  'available': true,
  'model': 'local-model',
};

/// Show the app and break down a sentence.
Future<void> breakDown(WidgetTester tester, FakeServer server) async {
  await tester.binding.setSurfaceSize(const Size(900, 1400));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(appOn(server));
  await tester.pumpAndSettle();
  // The text of the saved breakdown.
  await tester.enterText(find.byKey(textFieldKey), 'Ona je je bila kod kuće.');
  await tester.pump(debounceTime);
  await tester.pumpAndSettle();
}

Future<void> ask(WidgetTester tester, String question) async {
  await tester.ensureVisible(button(question));
  await tester.tap(button(question));
  await tester.pump();
}

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('no key on the server: no panel', (tester) async {
    final server = FakeServer();
    await breakDown(tester, server);
    expect(find.bySemanticsLabel('chip: Ona PRON'), findsOneWidget);
    expect(find.text('Ask the AI:'), findsNothing);
  });

  testWidgets('the questions about a sentence, and an answer', (tester) async {
    final server = FakeServer(questions: available());
    await breakDown(tester, server);
    expect(find.text('Ask the AI:'), findsOneWidget);
    expect(button('What does this mean?'), findsOneWidget);
    expect(button('Explain the grammar'), findsOneWidget);
    expect(button('Is this colloquial?'), findsOneWidget);
    // The questions about an answer are only on a card.
    expect(button('Why is my answer wrong?'), findsNothing);
    // No request before a click.
    expect(server.explained, isEmpty);

    await tester.enterText(find.byType(TextField).last, ' why kod? ');
    await ask(tester, 'Explain the grammar');
    await tester.pumpAndSettle();
    final (path, body) = server.explained.single;
    expect(path, '/api/v1/explain');
    expect(body, {
      'question': 'grammar',
      'user_context': 'why kod?',
      'locale': 'en',
      'text': 'Ona je je bila kod kuće.',
      'language': 'hr',
    });
    expect(find.textContaining('"Kod" takes the genitive'), findsOneWidget);
    expect(find.text('local-model wrote this. It can be wrong.'), findsOne);
    expect(enabled(tester, 'What does this mean?'), isTrue);
  });

  testWidgets('no answer after the time limit', (tester) async {
    final server = FakeServer(questions: available(), explain: never);
    await breakDown(tester, server);
    await ask(tester, 'What does this mean?');
    expect(find.text('The AI writes an answer.'), findsOneWidget);
    expect(enabled(tester, 'What does this mean?'), isFalse);
    expect(enabled(tester, 'Explain the grammar'), isFalse);

    await tester.pump(explainTimeout - const Duration(seconds: 1));
    expect(find.text('The AI writes an answer.'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('No answer after 60 s. Try again.'), findsOneWidget);
    expect(find.text('The AI writes an answer.'), findsNothing);
    // The user can ask again.
    expect(enabled(tester, 'What does this mean?'), isTrue);
  });

  testWidgets('an error of the AI service', (tester) async {
    final server = FakeServer(
      questions: available(),
      explain: (_) async => json({'detail': 'The AI service failed.'}, 502),
    );
    await breakDown(tester, server);
    await ask(tester, 'What does this mean?');
    await tester.pumpAndSettle();
    expect(
      find.text('The server returned 502. The AI service failed.'),
      findsOneWidget,
    );
  });

  testWidgets('an answered card: the questions about the answer', (
    tester,
  ) async {
    final server = FakeServer(questions: available());
    await openDeck(tester, server);
    expect(find.text('Ask the AI:'), findsNothing);
    await answer(tester, 'Pijem kafu.');
    expect(find.text('Ask the AI:'), findsOneWidget);
    expect(button('Why is my answer wrong?'), findsOneWidget);
    expect(button('What does this mean?'), findsOneWidget);

    await ask(tester, 'Why is my answer wrong?');
    await tester.pumpAndSettle();
    final (path, body) = server.explained.single;
    expect(path, '/api/v1/reviews/1/explain');
    expect(body, {'question': 'why_wrong', 'user_context': '', 'locale': 'en'});
    expect(find.textContaining('"Kod" takes the genitive'), findsOneWidget);
  });
}
