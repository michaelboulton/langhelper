import '../i18n/i18n.dart';
import 'browser.dart' if (dart.library.js_interop) 'browser_web.dart';

/// The amount and the unit of the time from [now] to [due], rounded. Null for
/// less than a minute.
(int, String)? relativeParts(DateTime due, DateTime now) {
  final minutes = (due.difference(now).inMilliseconds / 60000).round();
  if (minutes < 1) return null;
  if (minutes < 90) return (minutes, 'minute');
  if (minutes < 36 * 60) return ((minutes / 60).round(), 'hour');
  return ((minutes / 1440).round(), 'day');
}

/// "in 5 minutes", in the words of the locale, for an ISO 8601 time.
String when(I18n i18n, String isoTime, {DateTime? now}) {
  final parts = relativeParts(DateTime.parse(isoTime), now ?? DateTime.now());
  if (parts == null) return i18n.t('time-now');
  final (amount, unit) = parts;
  return relativeTime(i18n.locale, amount, unit);
}
