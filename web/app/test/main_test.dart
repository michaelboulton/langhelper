import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/main.dart';

void main() {
  testWidgets('the app shows its title in Noto Sans', (tester) async {
    await tester.pumpWidget(LanghelperApp());
    expect(find.text('Sentence breakdown'), findsOneWidget);
    final context = tester.element(find.text('Sentence breakdown'));
    expect(Theme.of(context).textTheme.bodyMedium?.fontFamily, 'NotoSans');
  });
}
