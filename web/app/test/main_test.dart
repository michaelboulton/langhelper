import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/i18n/i18n.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

import 'fake_server.dart';

void main() {
  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  testWidgets('the app shows its title in Noto Sans', (tester) async {
    await tester.pumpWidget(appOn(FakeServer()));
    await tester.pumpAndSettle();
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
    await tester.pumpWidget(appOn(FakeServer(), i18n: i18n));
    await tester.pumpAndSettle();
    expect(find.text('Raščlamba rečenice: hrvatski'), findsOneWidget);
  });

  testWidgets('a right-to-left locale turns the layout', (tester) async {
    final i18n = I18n(
      locale: 'he',
      catalogs: english().catalogs,
      direction: TextDirection.rtl,
    );
    await tester.pumpWidget(appOn(FakeServer(), i18n: i18n));
    await tester.pumpAndSettle();
    final title = find.text('Croatian sentence breakdown');
    expect(Directionality.of(tester.element(title)), TextDirection.rtl);
    // The title of the app bar starts on the right.
    final bar = tester.getRect(find.byType(AppBar));
    expect(tester.getRect(title).right, greaterThan(bar.center.dx));
  });
}
