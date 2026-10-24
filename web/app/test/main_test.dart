import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/i18n/i18n.dart';
import 'package:langhelper_app/main.dart';

I18n english() => I18n(
  locale: 'en',
  catalogs: [Catalog('en', File(bundledCatalog).readAsStringSync())],
);

void main() {
  testWidgets('the app shows its title in Noto Sans', (tester) async {
    await tester.pumpWidget(LanghelperApp(i18n: english()));
    final title = find.text('Croatian sentence breakdown');
    expect(title, findsOneWidget);
    final context = tester.element(title);
    expect(Theme.of(context).textTheme.bodyMedium?.fontFamily, 'NotoSans');
    expect(Directionality.of(context), TextDirection.ltr);
  });

  testWidgets('the app shows the text of its locale', (tester) async {
    final croatian = File('../tlhelper/languages/croatian/ui.ftl');
    final i18n = I18n(
      locale: 'hr',
      catalogs: [
        Catalog('hr', croatian.readAsStringSync()),
        ...english().catalogs,
      ],
    );
    await tester.pumpWidget(LanghelperApp(i18n: i18n));
    expect(find.text('Raščlamba rečenice: hrvatski'), findsOneWidget);
  });

  testWidgets('a right-to-left locale turns the layout', (tester) async {
    final i18n = I18n(
      locale: 'he',
      catalogs: english().catalogs,
      direction: TextDirection.rtl,
    );
    await tester.pumpWidget(LanghelperApp(i18n: i18n));
    final title = find.text('Croatian sentence breakdown');
    expect(Directionality.of(tester.element(title)), TextDirection.rtl);
    // The title of the app bar starts on the right.
    final bar = tester.getRect(find.byType(AppBar));
    expect(tester.getRect(title).right, greaterThan(bar.center.dx));
  });
}
