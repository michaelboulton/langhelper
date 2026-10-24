import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';
import 'package:langhelper_app/breakdown/links.dart';
import 'package:langhelper_app/breakdown/result.dart';
import 'package:langhelper_app/breakdown/state.dart';
import 'package:langhelper_app/i18n/i18n.dart';

import '../api/fixtures.dart';
import '../fake_server.dart';

/// A breakdown with a fixed state and no requests.
class FixedBreakdown extends Breakdown {
  FixedBreakdown(this.fixed);

  final BreakdownState fixed;

  @override
  BreakdownState build() => fixed;
}

/// The fixture twice: two sentences on each side, with the links and the
/// guesses of both.
ClassifyResponse twoSentences() {
  final data = fixture('classify.json');
  final translation = data['translation'] as Map<String, dynamic>;
  final studyWords = [
    for (final sentence in data['sentences'] as List) ...sentence['words'],
  ].length;
  final englishWords = [
    for (final sentence in translation['sentences'] as List)
      ...sentence['words'],
  ].length;
  List<Object> twice(List<dynamic> pairs) => [
    ...pairs,
    for (final [study as int, english as int] in pairs)
      [study + studyWords, english + englishWords],
  ];
  data['sentences'] = [...data['sentences'], ...data['sentences']];
  translation['sentences'] = [
    ...translation['sentences'],
    ...translation['sentences'],
  ];
  translation['links'] = twice(translation['links']);
  translation['guesses'] = twice(translation['guesses']);
  return ClassifyResponse.fromJson(data);
}

void main() {
  testWidgets('the curves of two translated sentences', (tester) async {
    final languages = Languages(
      LanguagesResponse.fromJson(fixture('languages.json')),
    );
    final result = twoSentences();
    // "je" of the second sentence, linked to "was".
    final selected = result.sentences[1].words[1];
    await tester.binding.setSurfaceSize(const Size(900, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          breakdownProvider.overrideWith(
            () => FixedBreakdown(
              BreakdownState(
                languages: languages,
                language: 'hr',
                result: result,
                selected: (word: selected, info: languages.study['hr']!),
              ),
            ),
          ),
        ],
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          home: I18nScope(
            i18n: english(),
            child: const Scaffold(
              body: Padding(
                padding: EdgeInsets.all(16),
                child: BreakdownResult(),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
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
    // Three links and one guess for each sentence.
    expect(painter.lines, hasLength(8));
    expect(painter.lines.where((line) => line.guess), hasLength(2));
    final thick = painter.lines.where((line) => line.selected).single;
    final je = tester
        .getRect(find.byKey(chipKey(selected)))
        .shift(-tester.getTopLeft(find.byType(LinkLayer)));
    expect(thick.from, je.bottomCenter);
    for (final line in painter.lines) {
      expect(line.to.dy, greaterThan(line.from.dy));
    }
    await expectLater(
      find.byType(BreakdownResult),
      matchesGoldenFile('goldens/links.png'),
    );
  });
}
