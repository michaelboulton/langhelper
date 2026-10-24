import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:langhelper_app/api/client.dart';
import 'package:langhelper_app/i18n/i18n.dart';

import '../api/fixtures.dart';

const english = '''
tab-cards = Flashcards
tab-audio = Audio lessons
status-timeout = No answer after { \$seconds } s.
''';
const croatian = '''
tab-cards = Kartice
''';

/// A server with the locales of fixtures/locales.json. [catalogs] are the
/// ui.ftl files by code, and [locales] replaces the list.
BreakdownApi server(
  Map<String, String> catalogs, {
  Object? locales,
  List<String>? asked,
}) => Api(
  base: Uri.parse('https://example.fly.dev/'),
  newClient: () => MockClient((request) async {
    asked?.add(request.url.path);
    if (request.url.path == '/api/v1/locales') {
      final list = jsonEncode(locales ?? fixture('locales.json'));
      return http.Response.bytes(utf8.encode(list), 200);
    }
    final code = RegExp(r'^/api/v1/locales/(\w+)/ui\.ftl$')
        .firstMatch(request.url.path)?[1];
    final source = catalogs[code];
    return source == null
        ? http.Response('{"detail": "Not Found"}', 404)
        : http.Response.bytes(utf8.encode(source), 200);
  }),
  onUnauthorized: () => fail('no 401 here'),
).breakdown;

Future<String> bundled() async => File(bundledCatalog).readAsStringSync();

void main() {
  group('pickLocale', () {
    const available = ['en', 'hr', 'de'];

    test('the first tag with a catalog wins', () {
      expect(pickLocale(['hr', 'de'], available, 'en'), 'hr');
      expect(pickLocale([null, '', 'xx', 'de'], available, 'en'), 'de');
    });

    test('a region falls back to its language', () {
      expect(pickLocale(['de-AT'], available, 'en'), 'de');
    });

    test('with no tag that has a catalog, the fallback', () {
      expect(pickLocale(['ja-JP', null], available, 'en'), 'en');
    });
  });

  group('I18n', () {
    final i18n = I18n(
      locale: 'hr',
      catalogs: [Catalog('hr', croatian), Catalog('en', english)],
    );

    test('a message comes from the first catalog that has it', () {
      expect(i18n.t('tab-cards'), 'Kartice');
      expect(i18n.t('tab-audio'), 'Audio lessons');
    });

    test('a parameter, with the number in the format of the locale', () {
      expect(
        i18n.t('status-timeout', {'seconds': 1.5}),
        'No answer after 1.5 s.',
      );
    });

    test('a missing message gives the fallback, else the id', () {
      expect(i18n.tOr('nothing', fallback: 'Croatian'), 'Croatian');
      expect(i18n.t('nothing'), 'nothing');
      expect(i18n.message('nothing', const {}), isNull);
    });
  });

  group('loadI18n', () {
    test('the wanted locale and English', () async {
      final asked = <String>[];
      final i18n = await loadI18n(
        server({'en': english, 'hr': croatian}, asked: asked),
        wanted: ['hr-HR', 'de'],
        bundled: bundled,
      );
      expect(i18n.locale, 'hr');
      expect(i18n.direction, TextDirection.ltr);
      expect([for (final each in i18n.catalogs) each.code], ['hr', 'en']);
      expect(i18n.t('tab-cards'), 'Kartice');
      expect(
        asked,
        unorderedEquals([
          '/api/v1/locales',
          '/api/v1/locales/hr/ui.ftl',
          '/api/v1/locales/en/ui.ftl',
        ]),
      );
    });

    test('a right-to-left locale turns the text direction', () async {
      final i18n = await loadI18n(
        server(
          {'en': english, 'he': 'tab-cards = כרטיסיות\n'},
          locales: {
            'default': 'en',
            'locales': [
              {'code': 'en', 'name': 'English', 'direction': 'ltr'},
              {'code': 'he', 'name': 'עברית', 'direction': 'rtl'},
            ],
          },
        ),
        wanted: ['he'],
        bundled: bundled,
      );
      expect(i18n.locale, 'he');
      expect(i18n.direction, TextDirection.rtl);
      expect(i18n.t('tab-cards'), 'כרטיסיות');
    });

    test('with no list of locales, the bundled English catalog', () async {
      final api = Api(
        base: Uri.parse('https://example.fly.dev/'),
        newClient: () => MockClient((request) async => http.Response('', 503)),
        onUnauthorized: () => fail('no 401 here'),
      ).breakdown;
      final i18n = await loadI18n(api, wanted: ['hr'], bundled: bundled);
      expect(i18n.locale, 'en');
      expect(i18n.t('tab-cards'), 'Flashcards');
    });

    test('without the English catalog, the bundled one fills in', () async {
      final i18n = await loadI18n(
        server({'hr': croatian}),
        wanted: ['hr'],
        bundled: bundled,
      );
      expect([for (final each in i18n.catalogs) each.code], ['hr', 'en']);
      expect(i18n.t('tab-progress'), 'Progress');
    });

    test('without the catalog of the locale, English', () async {
      final i18n = await loadI18n(
        server({'en': english}),
        wanted: ['hr'],
        bundled: bundled,
      );
      expect(i18n.locale, 'en');
      expect(i18n.t('tab-cards'), 'Flashcards');
    });
  });
}
