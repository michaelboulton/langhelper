import 'package:flutter/painting.dart';

import '../api/models.dart';
import '../i18n/i18n.dart';

/// One colour for each Universal POS tag, as in static/js/breakdown.js. The
/// name of a tag is the message "upos-NOUN".
const uposColors = <String, Color>{
  'NOUN': Color(0xFF9ECBFF),
  'PROPN': Color(0xFF6FA8FF),
  'VERB': Color(0xFFFF9E9E),
  'AUX': Color(0xFFFFC3A0),
  'ADJ': Color(0xFFA8E6A1),
  'ADV': Color(0xFFD4F0A0),
  'PRON': Color(0xFFD9B3FF),
  'DET': Color(0xFFF0B8E8),
  'ADP': Color(0xFFFFE08A),
  'CCONJ': Color(0xFFFFD0B0),
  'SCONJ': Color(0xFFF5C28A),
  'PART': Color(0xFFA0E8E0),
  'NUM': Color(0xFFB8D8D0),
  'INTJ': Color(0xFFFFB0D0),
  'PUNCT': Color(0xFFD8D8D2),
  'SYM': Color(0xFFC8C8C0),
  'X': Color(0xFFBDBDB5),
};

/// The text on a chip and on the legend. The colours are light in both
/// themes.
const chipText = Color(0xFF1D1D1B);

/// The wavy line under a word that fails a grammar check, and the list of
/// the problems.
const problemRed = Color(0xFFD00000);

Color uposColor(String upos) => uposColors[upos] ?? uposColors['X']!;

String uposName(I18n i18n, String upos) =>
    i18n.t(tagId('upos', uposColors.containsKey(upos) ? upos : 'X'));

/// The id of the message for a tag of a tagger: "feat-Number-psor" for
/// ("feat", "Number[psor]"). A Fluent id has only letters, digits, "_", "-".
String tagId(String prefix, String tag) {
  final id = '$prefix-${tag.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '-')}';
  return id.endsWith('-') ? id.substring(0, id.length - 1) : id;
}

/// The name of a feature, such as "Case". A tag with no message shows as it
/// is.
String featName(I18n i18n, String name) =>
    i18n.tOr(tagId('feat', name), fallback: name);

/// The word for a value of a feature. A message with the feature name
/// ("featval-Definite-Ind") wins over the plain value ("featval-Ind").
String featValue(I18n i18n, String name, String value) => i18n.tOr(
  tagId('featval', '$name-$value'),
  fallback: i18n.tOr(tagId('featval', value), fallback: value),
);

const _nominalUpos = ['NOUN', 'PROPN', 'ADJ', 'DET', 'PRON'];
const _nominalFeats = ['Case', 'Gender', 'Number'];
const _verbFormFeats = {
  'Fin': ['Person', 'Number'],
  'Part': ['Gender', 'Number'],
};

List<String> _noteFeats(Word word) {
  if (_nominalUpos.contains(word.upos)) return _nominalFeats;
  final form = word.feats['VerbForm'];
  if ((word.upos == 'VERB' || word.upos == 'AUX') && form != null) {
    return ['VerbForm', ...?_verbFormFeats[form]];
  }
  return const [];
}

/// The short note after the tag: the first letter of each feature value,
/// such as "A/F/S" for Acc, Fem, Sing. A missing feature is "–". A word with
/// none of the features has no note. A noun, an adjective, a pronoun or a
/// determiner: case/gender/number. A verb: the verb form, then
/// person/number for a finite verb or gender/number for a participle.
String featNote(Word word) {
  final names = _noteFeats(word);
  if (!names.any(word.feats.containsKey)) return '';
  return [
    for (final name in names)
      switch (word.feats[name]) {
        final value? => value.split(',').map((each) => each[0]).join(','),
        null => '–',
      },
  ].join('/');
}

/// The note in words, such as "Case: accusative, Gender: feminine".
String featNoteTitle(I18n i18n, Word word) => [
  for (final name in _noteFeats(word))
    if (word.feats[name] case final value?)
      '${featName(i18n, name)}: ${featValue(i18n, name, value)}',
].join(', ');

/// A problem that a check found, in the language of the page. The server
/// gives the English sentence, and the id and the parameters of the message.
/// A parameter is a raw value, so this adds the words: "gotName" for "got",
/// "languageName" for "language", and a list of tags as "the accusative or
/// the dative".
String problemText(
  I18n i18n,
  Word word,
  int index,
  LanguageInfo? Function(String code) language,
) {
  final message = index < word.problemMessages.length
      ? word.problemMessages[index]
      : null;
  if (message == null) return word.problems[index];
  String named(Object tag) => i18n.tOr(tagId('featval', '$tag'), fallback: '');
  final args = <String, Object?>{};
  for (final MapEntry(key: name, :value) in message.params.entries) {
    if (value is List) {
      args[name] = orList(i18n, [
        for (final tag in value)
          i18n.t('problem-case-in-list', {'case': tag, 'caseName': named(tag)}),
      ]);
      continue;
    }
    args[name] = value;
    if (named(value).isNotEmpty) args['${name}Name'] = named(value);
    if (name == 'language') {
      final info = language('$value');
      args['languageName'] = info == null ? value : i18n.languageName(info);
    }
  }
  return i18n.tOr(message.key, args: args, fallback: word.problems[index]);
}

/// "a, b or c" in the language of the page.
String orList(I18n i18n, List<String> items) => items.length < 2
    ? items.join()
    : i18n.t('list-or', {
        'items': items.sublist(0, items.length - 1).join(', '),
        'last': items.last,
      });
