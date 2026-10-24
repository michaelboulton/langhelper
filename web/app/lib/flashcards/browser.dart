/// "in 5 minutes". Outside a browser (flutter test) there is no
/// Intl.RelativeTimeFormat, so the text is English.
String relativeTime(String locale, int amount, String unit) =>
    'in $amount $unit${amount == 1 ? '' : 's'}';

/// "100%" for a [share] of 1. Outside a browser there is no
/// Intl.NumberFormat, so the format is the English one.
String percent(String locale, double share) => '${(share * 100).round()}%';

/// "0.75" for 0.75 and "3" for 3.0. Outside a browser the format is the
/// English one.
String decimal(String locale, double value) =>
    value == value.roundToDouble() ? '${value.toInt()}' : '$value';

/// flutter_tts can read a text aloud. Outside a browser it uses the voices of
/// the system.
bool canSpeak() => true;
