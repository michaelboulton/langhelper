/// "in 5 minutes". Outside a browser (flutter test) there is no
/// Intl.RelativeTimeFormat, so the text is English.
String relativeTime(String locale, int amount, String unit) =>
    'in $amount $unit${amount == 1 ? '' : 's'}';

/// flutter_tts can read a text aloud. Outside a browser it uses the voices of
/// the system.
bool canSpeak() => true;
