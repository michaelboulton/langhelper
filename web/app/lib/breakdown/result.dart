import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/client.dart' show codedMessage;
import '../api/models.dart' hide Locale;
import '../i18n/i18n.dart';
import 'form.dart' show textDirection;
import 'links.dart';
import 'state.dart';
import 'tags.dart';

/// The text of a word in its language: the font chooses the letter shapes
/// from the locale. Without it, Japanese text can get the Chinese shapes.
Locale languageLocale(LanguageInfo info) => Locale(info.code);

/// One word: the colour of its part of speech, the word, the accent, the
/// reading, the lemma, the tag and the feature note. A word that fails a
/// grammar check has a red wavy line.
class WordChip extends StatelessWidget {
  const WordChip({
    super.key,
    required this.word,
    required this.info,
    required this.selected,
    required this.onTap,
  });

  final Word word;

  /// The language of the word.
  final LanguageInfo info;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final rtl = info.direction == ScriptDirection.rtl;
    final locale = languageLocale(info);
    final base = DefaultTextStyle.of(context).style
        .copyWith(color: chipText, height: 1.25);
    final small = base.copyWith(fontSize: 12.8);
    final note = featNote(word);
    final accent = word.accent;
    final tag = Text.rich(
      TextSpan(
        text: word.upos,
        children: [
          if (note.isNotEmpty)
            TextSpan(
              text: ' ($note)',
              style: TextStyle(color: chipText.withValues(alpha: 0.75)),
            ),
        ],
      ),
      // The tag is English, also under a right-to-left word.
      textDirection: TextDirection.ltr,
      style: base.copyWith(fontSize: 10.4, letterSpacing: 0.5),
    );
    return Semantics(
      label: 'chip: ${word.text} ${word.upos}',
      button: true,
      selected: selected,
      onTap: onTap,
      excludeSemantics: true,
      child: Material(
        color: uposColor(word.upos),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(
            width: 2,
            color: selected
                ? Theme.of(context).colorScheme.onSurface
                : Colors.transparent,
          ),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  word.text,
                  locale: locale,
                  style: base.copyWith(
                    fontSize: 17.6,
                    fontWeight: FontWeight.w600,
                    decoration: word.problems.isEmpty
                        ? null
                        : TextDecoration.underline,
                    decorationStyle: TextDecorationStyle.wavy,
                    decorationColor: problemRed,
                  ),
                ),
                // A language with accent data shows a line for each word: a
                // dash with no data, and the dictionary form in parentheses.
                if (info.hasAccents)
                  Text(
                    switch (accent) {
                      null => '–',
                      Accent(exact: true) => accent.form,
                      _ => '(${accent.form})',
                    },
                    style: base.copyWith(
                      fontSize: 16,
                      height: 1.5,
                      fontStyle: accent?.exact == false
                          ? FontStyle.italic
                          : null,
                      color: accent?.exact == false
                          ? chipText.withValues(alpha: 0.6)
                          : null,
                    ),
                  ),
                // How to say the word, for a script that does not show it.
                if (word.reading.isNotEmpty)
                  Text(word.reading, locale: locale, style: small),
                Text(
                  word.lemma,
                  locale: locale,
                  // Arabic and Hebrew have no italic.
                  style: small.copyWith(
                    fontStyle: rtl ? null : FontStyle.italic,
                  ),
                ),
                if (note.isEmpty)
                  tag
                else
                  Tooltip(
                    message: featNoteTitle(i18n, word),
                    triggerMode: TooltipTriggerMode.manual,
                    child: tag,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// The sentences of one side, each one a row of chips.
class Side {
  const Side(this.sentences, this.info);

  final List<Sentence> sentences;
  final LanguageInfo info;
}

class SentenceRow extends ConsumerWidget {
  const SentenceRow({
    super.key,
    required this.sentence,
    required this.info,
    this.padding = bottom,
  });

  static const bottom = EdgeInsets.only(bottom: 18);

  final Sentence sentence;
  final LanguageInfo info;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(
      breakdownProvider.select((state) => state.selected?.word),
    );
    final notifier = ref.read(breakdownProvider.notifier);
    return Padding(
      padding: padding,
      // A right-to-left sentence starts on the right.
      child: Directionality(
        textDirection: textDirection(info),
        child: Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final word in sentence.words)
              WordChip(
                key: chipKey(word),
                word: word,
                info: info,
                selected: identical(word, selected),
                onTap: () => notifier.select((word: word, info: info)),
              ),
          ],
        ),
      ),
    );
  }
}

/// The text that the user entered on top, and its translation under it.
class BreakdownResult extends ConsumerWidget {
  const BreakdownResult({super.key});

  /// The room between a sentence and its translation, for the curves.
  static const translated = EdgeInsets.only(top: 56, bottom: 40);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final state = ref.watch(breakdownProvider);
    final data = state.result;
    final languages = state.languages;
    if (data == null || languages == null) return const SizedBox.shrink();
    final translation = data.translation;
    // data.sentences is always the side of the study language.
    final study = Side(
      data.sentences,
      languages.study[data.language] ?? languages.english,
    );
    final english = Side(translation?.sentences ?? const [], languages.english);
    final (top, bottom) = data.source == Source.en
        ? (english, study)
        : (study, english);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    Widget note(String text) => Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(text, style: TextStyle(color: muted)),
    );
    final rows = <Widget>[
      for (final sentence in top.sentences)
        SentenceRow(sentence: sentence, info: top.info),
    ];
    if (translation != null && translation.error.isNotEmpty) {
      final error = codedMessage(
        i18n.message,
        translation.errorCode,
        translation.errorParams,
        translation.error,
      );
      rows.add(note(i18n.t('breakdown-no-translation', {'error': error})));
    } else if (translation != null) {
      // Each translated sentence goes directly under its source sentence,
      // which keeps the curves short. That needs the same number of
      // sentences on both sides. If not, all the translation comes last.
      final paired = top.sentences.length == bottom.sentences.length;
      for (final (index, sentence) in bottom.sentences.indexed) {
        final row = SentenceRow(
          sentence: sentence,
          info: bottom.info,
          padding: paired || index == 0 ? translated : SentenceRow.bottom,
        );
        if (paired) {
          rows.insert(2 * index + 1, row);
        } else {
          rows.add(row);
        }
      }
      final text = data.source == Source.en ? data.text : translation.text;
      final label = i18n.t('breakdown-side-label', {
        'language': i18n.languageName(bottom.info),
      });
      rows.add(note('$label $text'));
    }
    // A link is [study index, English index], over all the sentences.
    final studyWords = [for (final each in study.sentences) ...each.words];
    final englishWords = [for (final each in english.sentences) ...each.words];
    List<ChipLink> chipLinks(List<Link> pairs, {required bool guess}) => [
      for (final pair in pairs)
        if ((
              studyWords.elementAtOrNull(pair.study),
              englishWords.elementAtOrNull(pair.english),
            )
            case (final studyWord?, final englishWord?))
          top == study
              ? (upper: studyWord, lower: englishWord, guess: guess)
              : (upper: englishWord, lower: studyWord, guess: guess),
    ];
    return LinkLayer(
      links: [
        ...chipLinks(translation?.links ?? const [], guess: false),
        ...chipLinks(translation?.guesses ?? const [], guess: true),
      ],
      selected: state.selected?.word,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: rows,
      ),
    );
  }
}

/// The table of the selected word, with its problems and the dictionary
/// links of its language.
class WordDetail extends ConsumerWidget {
  const WordDetail({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(
      breakdownProvider.select((state) => state.selected),
    );
    if (selected == null) return const SizedBox.shrink();
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final (:word, :info) = selected;
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final line = BorderSide(color: theme.colorScheme.outlineVariant);
    final rows = <TableRow>[];
    void addRow(String name, Widget value) => rows.add(
      TableRow(
        decoration: BoxDecoration(border: Border(top: line)),
        children: [
          Padding(
            padding: const EdgeInsetsDirectional.fromSTEB(0, 4, 8, 4),
            child: Text(name, style: TextStyle(color: muted)),
          ),
          Padding(
            padding: const EdgeInsetsDirectional.fromSTEB(0, 4, 8, 4),
            child: value,
          ),
        ],
      ),
    );
    Widget valueText(String value, [String note = '']) => Text.rich(
      TextSpan(
        text: value,
        children: [
          if (note.isNotEmpty)
            TextSpan(
              text: ' $note',
              style: TextStyle(color: muted, fontSize: 13),
            ),
        ],
      ),
    );
    if (word.accent case final accent?) {
      addRow(
        i18n.t('detail-accent'),
        valueText(
          accent.form,
          accent.clitic
              ? i18n.t('detail-accent-clitic')
              : !accent.exact
              ? i18n.t('detail-accent-dictionary')
              : accent.ambiguous
              ? i18n.t('detail-accent-ambiguous')
              : '',
        ),
      );
    }
    if (word.reading.isNotEmpty) {
      addRow(i18n.t('detail-reading'), valueText(word.reading));
    }
    addRow(i18n.t('detail-lemma'), valueText(word.lemma));
    addRow(
      i18n.t('detail-upos'),
      valueText(uposName(i18n, word.upos), word.upos),
    );
    if (word.xpos.isNotEmpty) {
      addRow(
        i18n.tOr('language-${info.code}-tag-name', fallback: info.tagName),
        valueText(word.xpos),
      );
    }
    for (final MapEntry(key: name, :value) in word.feats.entries) {
      addRow(
        featName(i18n, name),
        valueText(featValue(i18n, name, value), '$name=$value'),
      );
    }
    if (word.seen case final seen?) {
      addRow(i18n.t('detail-seen'), valueText('$seen'));
    }
    if (info.dictionaryLinks.isNotEmpty) {
      addRow(
        i18n.t('detail-dictionaries'),
        Wrap(
          children: [
            for (final (index, link) in info.dictionaryLinks.indexed) ...[
              if (index > 0) const Text(' · '),
              DictionaryLinkText(link: link, lemma: word.lemma),
            ],
          ],
        ),
      );
    }
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLowest,
        border: Border.fromBorderSide(line),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: Text(
              word.text,
              locale: languageLocale(info),
              textDirection: textDirection(info),
              style: theme.textTheme.titleLarge?.copyWith(
                decoration: word.problems.isEmpty
                    ? null
                    : TextDecoration.underline,
                decorationStyle: TextDecorationStyle.wavy,
                decorationColor: problemRed,
              ),
            ),
          ),
          const SizedBox(height: 8),
          for (final (index, _) in word.problems.indexed)
            Padding(
              padding: const EdgeInsetsDirectional.only(start: 8, bottom: 4),
              child: Text(
                '• ${problemText(i18n, word, index, (code) => languages?.info(code))}',
                style: const TextStyle(color: problemRed),
              ),
            ),
          Table(
            columnWidths: const {0: FractionColumnWidth(0.38)},
            children: rows,
          ),
        ],
      ),
    );
  }
}

/// A (label, address) of a dictionary. "{lemma}" in either stands for the
/// lemma of the word. The address opens in a new tab.
class DictionaryLinkText extends StatelessWidget {
  const DictionaryLinkText({
    super.key,
    required this.link,
    required this.lemma,
  });

  final DictionaryLink link;
  final String lemma;

  @override
  Widget build(BuildContext context) {
    final address = Uri.parse(
      link.address.replaceAll('{lemma}', Uri.encodeComponent(lemma)),
    );
    final label = link.label.replaceAll('{lemma}', lemma);
    return Semantics(
      link: true,
      linkUrl: address,
      child: InkWell(
        onTap: () => launchUrl(address, webOnlyWindowName: '_blank'),
        child: Text(
          label,
          style: const TextStyle(decoration: TextDecoration.underline),
        ),
      ),
    );
  }
}
