import 'dart:io';

import 'package:fluent/fluent.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/i18n/i18n.dart';

/// The folders of tlhelper/languages/ with a ui.ftl, and their locales.
const locales = {
  'english': 'en',
  'croatian': 'hr',
  'german': 'de',
  'french': 'fr',
  'italian': 'it',
};

/// The start of each message and term, as the parser of package:fluent
/// finds it.
final entryStart = RegExp(r'^(-?[a-zA-Z][\w-]*) *=', multiLine: true);
final variable = RegExp(r'\$([a-zA-Z][\w-]*)');

/// flutter test runs in the package folder.
final languages = Directory('../tlhelper/languages');

String catalog(String folder) =>
    File('${languages.path}/$folder/ui.ftl').readAsStringSync();

void main() {
  test('each catalog of the server has its locale here', () {
    final folders = [
      for (final each in languages.listSync().whereType<Directory>())
        if (File('${each.path}/ui.ftl').existsSync())
          each.uri.pathSegments.lastWhere((part) => part.isNotEmpty),
    ];
    expect(folders, unorderedEquals(locales.keys));
  });

  test('the bundled catalog is a copy of the English catalog', () {
    expect(
      File(bundledCatalog).readAsStringSync(),
      catalog('english'),
      reason: 'cp ../tlhelper/languages/english/ui.ftl $bundledCatalog',
    );
  });

  for (final MapEntry(key: folder, value: code) in locales.entries) {
    test('package:fluent formats each message of $folder/ui.ftl', () {
      final source = catalog(folder);
      final starts = entryStart.allMatches(source).toList();
      final bundle = FluentBundle(code);
      expect(bundle.addMessages(source, allowOverrides: false), isEmpty);
      // The parser skips an entry that it cannot read, with no error.
      final parsed = {...bundle.messages.keys, ...bundle.terms.keys};
      expect(
        [
          for (final start in starts)
            if (!parsed.contains(start[1])) start[1],
        ],
        isEmpty,
        reason: '$folder: package:fluent cannot read these',
      );
      for (final (index, start) in starts.indexed) {
        final id = start[1]!;
        if (id.startsWith('-')) continue;
        final end = index + 1 < starts.length
            ? starts[index + 1].start
            : source.length;
        final names = {
          for (final match in variable.allMatches(source, start.start))
            if (match.start < end) match[1]!,
        };
        // A selector can want a number or a text.
        for (final value in <Object>[3, 'x']) {
          final errors = <Error>[];
          final text = bundle.format(
            id,
            args: {for (final name in names) name: value},
            errors: errors,
          );
          expect(errors, isEmpty, reason: '$folder: $id');
          expect(text, isNotNull, reason: '$folder: $id');
        }
      }
    });
  }
}
