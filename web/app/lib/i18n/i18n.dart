import 'package:fluent/fluent.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/client.dart';
import '../api/models.dart' show LanguageInfo, LocalesResponse, ScriptDirection;

/// The shared_preferences key of the locale that the user chose.
const localeKey = 'langhelper.locale';

/// The complete catalog. A message that another catalog does not have comes
/// from this one.
const defaultLocale = 'en';

/// A copy of tlhelper/languages/english/ui.ftl, for an app that gets no
/// English catalog from the server (README.md, "The text of the app").
const bundledCatalog = 'assets/i18n/ui.ftl';

/// The messages of one locale: one ui.ftl file.
class Catalog {
  Catalog(this.code, String source) : _bundle = FluentBundle(code) {
    for (final error in _bundle.addMessages(source)) {
      debugPrint('i18n: $code: $error');
    }
  }

  final String code;
  final FluentBundle _bundle;

  bool has(String id) => _bundle.messages[id]?.value != null;

  String format(String id, Map<String, Object?> args) {
    final errors = <Error>[];
    final text = _bundle.format(id, args: args, errors: errors);
    for (final error in errors) {
      debugPrint('i18n: $id: $error');
    }
    return text ?? id;
  }
}

/// The text of the app in one locale.
class I18n {
  I18n({
    required this.locale,
    required this.catalogs,
    this.direction = TextDirection.ltr,
  });

  /// The code of the locale, such as "hr".
  final String locale;

  /// The catalogs to look in: the one of [locale], then the English one.
  final List<Catalog> catalogs;
  final TextDirection direction;
  final _missing = <String>{};

  /// The message [id] of the first catalog that has it. Without one: the
  /// [fallback], else the id, and the log names the id one time.
  String tOr(
    String id, {
    Map<String, Object?> args = const {},
    String? fallback,
  }) {
    if (message(id, args) case final text?) return text;
    if (fallback != null) return fallback;
    if (_missing.add(id)) debugPrint('i18n: no message $id');
    return id;
  }

  String t(String id, [Map<String, Object?> args = const {}]) =>
      tOr(id, args: args);

  /// The name of a language of /api/v1/languages.
  String languageName(LanguageInfo info) =>
      tOr('language-name-${info.code}', fallback: info.name);

  /// The message [id], or null if no catalog has it. It fits [Messages] of
  /// the API client.
  String? message(String id, Map<String, Object?> args) {
    for (final catalog in catalogs) {
      if (catalog.has(id)) return catalog.format(id, args);
    }
    return null;
  }

  /// The text of a failed request.
  String errorText(Object error) =>
      error is ApiException ? error.message(message) : '$error';

  static I18n of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<I18nScope>()!.i18n;
}

/// Gives [i18n] to the widgets under it, through I18n.of.
class I18nScope extends InheritedWidget {
  const I18nScope({super.key, required this.i18n, required super.child});

  final I18n i18n;

  @override
  bool updateShouldNotify(I18nScope oldWidget) =>
      !identical(i18n, oldWidget.i18n);
}

/// The first tag of [wanted] that has a catalog in [available], else
/// [fallback]. "de-AT" gets "de".
String pickLocale(
  Iterable<String?> wanted,
  List<String> available,
  String fallback,
) {
  for (final tag in wanted) {
    if (tag == null || tag.isEmpty) continue;
    for (final code in [tag, tag.split('-').first]) {
      if (available.contains(code)) return code;
    }
  }
  return fallback;
}

/// The catalogs of the first locale of [wanted] that the server has, and of
/// English. If the server gives no English catalog, [bundled] gives it.
Future<I18n> loadI18n(
  BreakdownApi api, {
  required Iterable<String?> wanted,
  required Future<String> Function() bundled,
}) async {
  LocalesResponse? list;
  try {
    list = await api.locales();
  } on Object catch (error) {
    debugPrint('i18n: no list of locales: $error');
  }
  final catalogs = <Catalog>[];
  if (list != null) {
    final fallback = list.defaultCode;
    final code = pickLocale(wanted, [
      for (final each in list.locales) each.code,
    ], fallback);
    final codes = {code, fallback};
    final sources = await Future.wait(
      codes.map((each) async {
        try {
          return await api.catalog(each);
        } on Object catch (error) {
          debugPrint('i18n: no catalog $each: $error');
          return null;
        }
      }),
    );
    for (final (index, each) in codes.indexed) {
      if (sources[index] case final source?) {
        catalogs.add(Catalog(each, source));
      }
    }
  }
  if (!catalogs.any((each) => each.code == defaultLocale)) {
    catalogs.add(Catalog(defaultLocale, await bundled()));
  }
  final locale = catalogs.first.code;
  final shown = list?.locales.where((each) => each.code == locale).firstOrNull;
  return I18n(
    locale: locale,
    catalogs: catalogs,
    direction: shown?.direction == ScriptDirection.rtl
        ? TextDirection.rtl
        : TextDirection.ltr,
  );
}

/// The text of the app in the locale of the user: `?locale=` of the address,
/// then the choice under [localeKey], then the languages of the browser.
Future<I18n> startI18n(Api api) async {
  String? saved;
  try {
    saved = await SharedPreferencesAsync().getString(localeKey);
  } on Object catch (error) {
    debugPrint('i18n: no saved locale: $error');
  }
  return loadI18n(
    api.breakdown,
    wanted: [
      api.base.queryParameters['locale'],
      saved,
      for (final each in PlatformDispatcher.instance.locales)
        each.toLanguageTag(),
    ],
    bundled: () => rootBundle.loadString(bundledCatalog),
  );
}
