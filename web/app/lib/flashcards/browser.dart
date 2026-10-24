/// "in 5 minutes". Outside a browser (flutter test) there is no
/// Intl.RelativeTimeFormat, so the text is English.
String relativeTime(String locale, int amount, String unit) =>
    'in $amount $unit${amount == 1 ? '' : 's'}';

/// "100%" for a [share] of 1. Outside a browser there is no
/// Intl.NumberFormat, so the format is the English one.
String percent(String locale, double share) => '${(share * 100).round()}%';

/// flutter_tts can read a text aloud. Outside a browser it uses the voices of
/// the system.
bool canSpeak() => true;
