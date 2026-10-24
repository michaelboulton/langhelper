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

/// The browser has speechSynthesis, which flutter_tts uses.
bool canSpeak() => globalContext.has('speechSynthesis');
