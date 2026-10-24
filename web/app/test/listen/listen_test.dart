import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:langhelper_app/breakdown/form.dart';
import 'package:langhelper_app/breakdown/state.dart';
import 'package:langhelper_app/listen/listen_panel.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';

Finder button(String language) =>
    find.widgetWithText(OutlinedButton, language);

bool enabled(WidgetTester tester, String language) =>
    tester.widget<OutlinedButton>(button(language)).onPressed != null;

/// The saved breakdown, with the text of the request.
Future<http.Response> echo(http.Request request) async => json({
  ...fixture('classify.json'),
  'text': (jsonDecode(request.body) as Map<String, dynamic>)['text'],
});

/// Show the app and break down [text].
Future<void> breakDown(
  WidgetTester tester,
  FakeServer server, [
  String text = 'Ona je je bila kod kuće.',
]) async {
  await tester.pumpWidget(appOn(server));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(textFieldKey), text);
  await tester.pump(debounceTime);
  await tester.pumpAndSettle();
}

Future<void> tapListen(WidgetTester tester, String language) async {
  await tester.ensureVisible(button(language));
  await tester.tap(button(language));
  await tester.pump();
}

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('no voice service: no panel', (tester) async {
    final server = FakeServer();
    await breakDown(tester, server);
    expect(find.bySemanticsLabel('chip: Ona PRON'), findsOneWidget);
    expect(find.text('Listen:'), findsNothing);
  });

  testWidgets('no text that the service reads: no panel', (tester) async {
    final server = FakeServer(
      speech: {'available': true, 'model': 'm', 'languages': ['fr']},
    );
    await breakDown(tester, server);
    expect(find.text('Listen:'), findsNothing);
  });

  testWidgets('a button for each text that the service reads', (tester) async {
    final server = FakeServer(speech: fixture('speech.json'));
    await breakDown(tester, server);
    expect(find.text('Listen:'), findsOneWidget);
    expect(button('Croatian'), findsOneWidget);
    expect(button('English'), findsOneWidget);
    // The text goes to the service only on a click.
    expect(server.spoken, isEmpty);
  });

  testWidgets('only the languages of the service', (tester) async {
    final server = FakeServer(
      speech: {'available': true, 'model': 'm', 'languages': ['en']},
    );
    await breakDown(tester, server);
    expect(button('Croatian'), findsNothing);
    expect(button('English'), findsOneWidget);
  });

  testWidgets('a click plays the sound and names the model', (tester) async {
    final answer = Completer<http.Response>();
    final server = FakeServer(
      speech: fixture('speech.json'),
      speechAudio: (_) => answer.future,
    );
    await breakDown(tester, server);
    await tapListen(tester, 'English');
    expect(server.spoken, [
      {'text': 'She was at home.', 'language': 'en'},
    ]);
    expect(find.text('The voice service reads the text.'), findsOneWidget);
    expect(enabled(tester, 'Croatian'), isFalse);
    expect(enabled(tester, 'English'), isFalse);

    answer.complete(
      http.Response.bytes(mp3, 200, headers: {'x-voice-model': 'voice-x'}),
    );
    await tester.pumpAndSettle();
    final player = server.players.single;
    expect(player.loaded, [mp3]);
    expect(player.plays, 1);
    expect(find.text('voice-x read this.'), findsOneWidget);
    expect(find.byTooltip('Pause'), findsOneWidget);
    expect(enabled(tester, 'Croatian'), isTrue);

    await tester.tap(find.byTooltip('Pause'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Play'), findsOneWidget);
  });

  testWidgets('with no header, the note names the model of the service', (
    tester,
  ) async {
    final server = FakeServer(
      speech: fixture('speech.json'),
      speechAudio: (_) async => http.Response.bytes(mp3, 200),
    );
    await breakDown(tester, server);
    await tapListen(tester, 'Croatian');
    await tester.pumpAndSettle();
    expect(server.spoken.single, {
      'text': 'Ona je je bila kod kuće.',
      'language': 'hr',
    });
    expect(find.text('k2-fsa/OmniVoice read this.'), findsOneWidget);
  });

  testWidgets('the same texts keep the sound, and new texts drop it', (
    tester,
  ) async {
    final server = FakeServer(speech: fixture('speech.json'), classify: echo);
    await breakDown(tester, server);
    await tapListen(tester, 'Croatian');
    await tester.pumpAndSettle();
    expect(find.text('k2-fsa/OmniVoice read this.'), findsOneWidget);

    // The Break down button sends the same text again.
    await tester.ensureVisible(find.text('Break down'));
    await tester.tap(find.text('Break down'));
    await tester.pumpAndSettle();
    expect(server.classified, hasLength(2));
    expect(find.text('k2-fsa/OmniVoice read this.'), findsOneWidget);
    expect(find.byTooltip('Pause'), findsOneWidget);

    await tester.enterText(find.byKey(textFieldKey), 'Ona je bila kod kuće.');
    await tester.pump(debounceTime);
    await tester.pumpAndSettle();
    expect(server.classified, hasLength(3));
    expect(button('Croatian'), findsOneWidget);
    expect(find.text('k2-fsa/OmniVoice read this.'), findsNothing);
    expect(find.byTooltip('Pause'), findsNothing);
    expect(find.byTooltip('Play'), findsNothing);
  });

  testWidgets('no sound after the time limit', (tester) async {
    final server = FakeServer(
      speech: fixture('speech.json'),
      speechAudio: never,
    );
    await breakDown(tester, server);
    await tapListen(tester, 'Croatian');
    await tester.pump(listenTimeout - const Duration(seconds: 1));
    expect(find.text('The voice service reads the text.'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('No sound after 190 s. Try again.'), findsOneWidget);
    expect(enabled(tester, 'Croatian'), isTrue);
    expect(server.players, isEmpty);
  });

  testWidgets('an error of the voice service', (tester) async {
    final server = FakeServer(
      speech: fixture('speech.json'),
      speechAudio: (_) async =>
          json({'detail': 'The voice service failed.'}, 502),
    );
    await breakDown(tester, server);
    await tapListen(tester, 'Croatian');
    await tester.pumpAndSettle();
    expect(
      find.text('The server returned 502. The voice service failed.'),
      findsOneWidget,
    );
    expect(enabled(tester, 'Croatian'), isTrue);
  });
}
