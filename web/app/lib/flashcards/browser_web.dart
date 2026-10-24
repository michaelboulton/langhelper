import 'dart:js_interop';
import 'dart:js_interop_unsafe';

@JS('Intl.RelativeTimeFormat')
extension type _RelativeTimeFormat._(JSObject _) implements JSObject {
  external _RelativeTimeFormat(String locale);

  external String format(int value, String unit);
}

/// "in 5 minutes", in the words of [locale]. [unit]: "minute", "hour" or
/// "day".
String relativeTime(String locale, int amount, String unit) =>
    _RelativeTimeFormat(locale).format(amount, unit);

@JS('Intl.NumberFormat')
extension type _NumberFormat._(JSObject _) implements JSObject {
  external _NumberFormat(String locale, JSAny options);

  external String format(double value);
}

/// A [share] from 0 to 1, as [locale] writes a percentage: "100 %", "100%".
String percent(String locale, double share) => _NumberFormat(
  locale,
  {'style': 'percent', 'maximumFractionDigits': 0}.jsify()!,
).format(share);

/// A number as [locale] writes it: "0,75", "0.75". A whole number has no
/// decimals.
String decimal(String locale, double value) =>
    _NumberFormat(locale, <String, Object?>{}.jsify()!).format(value);

/// The browser has speechSynthesis, which flutter_tts uses.
bool canSpeak() => globalContext.has('speechSynthesis');
