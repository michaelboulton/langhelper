import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart' hide Locale;
import '../breakdown/form.dart' show CheckboxLabel, textDirection;
import '../breakdown/links.dart';
import '../breakdown/result.dart';
import '../breakdown/state.dart';
import '../i18n/i18n.dart';
import 'decks.dart' show countsText;
import 'diff.dart';
import 'media.dart';
import 'read_aloud.dart';
import 'state.dart';
import 'time.dart';

/// The key of the answer field, for the tests.
const answerFieldKey = Key('cards-answer');

/// The deck, its next card or the note that it has none for now, and the
/// button back to the list.
class CardView extends ConsumerWidget {
  const CardView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final state = ref.watch(cardsProvider);
    final deck = state.deck;
    if (deck == null) return const SizedBox.shrink();
    final next = state.next;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 4,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              deck.path.isEmpty ? deck.name : deck.path.join(' › '),
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            if (next != null)
              Text(
                countsText(i18n, next.counts),
                style: TextStyle(color: muted, fontSize: 14.4),
              ),
            OutlinedButton(
              onPressed: () =>
                  unawaited(ref.read(cardsProvider.notifier).loadDecks()),
              child: Text(i18n.t('cards-all-decks')),
            ),
          ],
        ),
        const SizedBox(height: 8),
        switch (next) {
          null => const SizedBox.shrink(),
          NoCard(:final nextDue) => Text(
            nextDue == null
                ? i18n.t('cards-done')
                : i18n.t('cards-done-next', {'when': when(i18n, nextDue)}),
            style: TextStyle(color: muted),
          ),
          // A new card is a new widget: an empty field and new clips, also
          // for the same card again.
          final NextCard card => _Card(key: ObjectKey(card), card: card),
        },
      ],
    );
  }
}

class _Card extends ConsumerStatefulWidget {
  const _Card({super.key, required this.card});

  final NextCard card;

  @override
  ConsumerState<_Card> createState() => _CardState();
}

class _CardState extends ConsumerState<_Card> {
  final _answer = TextEditingController();

  @override
  void dispose() {
    _answer.dispose();
    super.dispose();
  }

  void _submit() {
    // In an input method (IME), Enter accepts a word. That Enter must not
    // send the answer.
    if (_answer.value.isComposingRangeValid) return;
    unawaited(ref.read(cardsProvider.notifier).check(_answer.text));
  }

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final card = widget.card;
    final state = ref.watch(cardsProvider);
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    if (languages == null) return const SizedBox.shrink();
    final notifier = ref.read(cardsProvider.notifier);
    final answered = state.answered;
    final study = languages.study[card.language] ?? languages.english;
    final toStudy = studyAnswers(card.direction);
    final (promptInfo, answerInfo) = toStudy
        ? (languages.english, study)
        : (study, languages.english);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    final rating = state.rating;
    final nextDue = state.nextDue;
    // A "listen" card gets the text of its clip only with the answer.
    final prompt = card.prompt.isEmpty && answered != null
        ? answered.prompt
        : card.prompt;
    return CallbackShortcuts(
      // 1 to 4 change the rating, as in Anki. Enter is "Next card": that
      // button has the focus. An answered card has no text field, so the
      // digits are free.
      bindings: {
        if (answered != null)
          for (final each in [1, 2, 3, 4])
            CharacterActivator('$each'): () => unawaited(notifier.rate(each)),
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            i18n.t(
              card.prompt.isEmpty ? 'cards-task-media' : 'cards-task-text',
              {'language': i18n.languageName(answerInfo)},
            ),
            style: TextStyle(color: muted),
          ),
          const SizedBox(height: 12),
          MediaView(media: card.media, autoplay: true),
          SelectionArea(
            child: CardResult(
              card: card,
              answered: answered,
              typed: state.typed,
              promptInfo: promptInfo,
              answerInfo: answerInfo,
              selected: state.selected?.word,
              onSelect: notifier.select,
            ),
          ),
          if (answered == null)
            _AnswerForm(
              controller: _answer,
              info: answerInfo,
              heavy: study.variants.contains('heavy'),
              onSubmit: _submit,
              onGiveUp: () => unawaited(notifier.check('')),
            )
          else ...[
            DiffText(diff: answered.diff, info: answerInfo),
            const SizedBox(height: 4),
            if (answered.answers.length > 1)
              _OtherAnswers(answers: answered.answers, info: answerInfo),
            const SizedBox(height: 12),
            MediaView(media: answered.media, autoplay: true),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                for (final each in [1, 2, 3, 4])
                  _RatingButton(
                    rating: each,
                    current: each == rating,
                    onPressed: () => unawaited(notifier.rate(each)),
                  ),
                if (rating != null && nextDue != null)
                  Text(
                    i18n.t('cards-next-due', {
                      'rating': i18n.t('rating-$rating'),
                      'when': when(i18n, nextDue),
                    }),
                    style: TextStyle(color: muted, fontSize: 14.4),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                // Always the text in the study language: the answer, or for
                // a card that asks for the English, the prompt.
                if (languages.study.containsKey(card.language))
                  ReadAloud(
                    text: toStudy
                        ? answered.correct.sentences
                              .map((each) => each.text)
                              .join(' ')
                        : prompt,
                    info: study,
                  ),
                FilledButton(
                  autofocus: true,
                  onPressed: () => unawaited(notifier.nextCard()),
                  child: Text(i18n.t('cards-next')),
                ),
              ],
            ),
          ],
          if (state.selected case final selected?)
            SelectionArea(
              child: WordTable(selected: selected, languages: languages),
            ),
        ],
      ),
    );
  }
}

/// The prompt. After the answer: the answer of the user over it, and the
/// correct answer under it, each with the curves of its links to the
/// prompt.
class CardResult extends StatelessWidget {
  const CardResult({
    super.key,
    required this.card,
    required this.answered,
    required this.typed,
    required this.promptInfo,
    required this.answerInfo,
    required this.selected,
    required this.onSelect,
  });

  final NextCard card;
  final AnswerResponse? answered;

  /// The text that the user sent.
  final String typed;
  final LanguageInfo promptInfo;
  final LanguageInfo answerInfo;
  final Word? selected;
  final void Function(Selected selected) onSelect;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    final answered = this.answered;
    Widget note(String text) => Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(text, style: TextStyle(color: muted)),
    );
    Widget row(Sentence sentence, LanguageInfo info, {bool apart = false}) =>
        SentenceRow(
          sentence: sentence,
          info: info,
          selected: selected,
          onSelect: onSelect,
          padding: apart ? BreakdownResult.translated : SentenceRow.bottom,
        );
    final promptSentences = card.promptSentences.isEmpty && answered != null
        ? answered.promptSentences
        : card.promptSentences;
    if (answered == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [for (final each in promptSentences) row(each, promptInfo)],
      );
    }
    List<Word> words(List<Sentence> sentences) => [
      for (final each in sentences) ...each.words,
    ];
    final promptWords = words(promptSentences);
    final typedWords = words(answered.typed.sentences);
    final correctWords = words(answered.correct.sentences);
    // A link is [word of the study language, English word]. The answer of
    // the user is over the prompt, and the correct answer under it.
    final toStudy = studyAnswers(card.direction);
    List<ChipLink> pairs(
      Links side,
      List<Word> answer, {
      required bool above,
    }) => [
      for (final (pairs, guess) in [(side.links, false), (side.guesses, true)])
        for (final pair in pairs)
          if ((toStudy
                  ? (
                      answer.elementAtOrNull(pair.study),
                      promptWords.elementAtOrNull(pair.english),
                    )
                  : (
                      answer.elementAtOrNull(pair.english),
                      promptWords.elementAtOrNull(pair.study),
                    ))
              case (final answerWord?, final promptWord?))
            above
                ? (upper: answerWord, lower: promptWord, guess: guess)
                : (upper: promptWord, lower: answerWord, guess: guess),
    ];
    return LinkLayer(
      links: [
        ...pairs(answered.typed, typedWords, above: true),
        ...pairs(answered.correct, correctWords, above: false),
      ],
      selected: selected,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          note(
            i18n.t(
              typed.trim().isEmpty ? 'cards-no-answer' : 'cards-your-answer',
            ),
          ),
          for (final each in answered.typed.sentences) row(each, answerInfo),
          // A prompt with only a picture has no line.
          for (final (index, each) in promptSentences.indexed)
            row(each, promptInfo, apart: index == 0 && typedWords.isNotEmpty),
          for (final (index, each) in answered.correct.sentences.indexed)
            row(each, answerInfo, apart: index == 0),
          note(i18n.t('cards-correct-answer')),
        ],
      ),
    );
  }
}

class _AnswerForm extends ConsumerWidget {
  const _AnswerForm({
    required this.controller,
    required this.info,
    required this.heavy,
    required this.onSubmit,
    required this.onGiveUp,
  });

  final TextEditingController controller;

  /// The language of the answer.
  final LanguageInfo info;

  /// The language of the card has large models.
  final bool heavy;
  final VoidCallback onSubmit;
  final VoidCallback onGiveUp;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final useHeavy = ref.watch(
      breakdownProvider.select((state) => state.heavy),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 4),
        TextField(
          key: answerFieldKey,
          controller: controller,
          autofocus: true,
          maxLength: 1000,
          autocorrect: false,
          enableSuggestions: false,
          textDirection: textDirection(info),
          textInputAction: TextInputAction.done,
          // Not onSubmitted: the field ends the IME text before that.
          onEditingComplete: onSubmit,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            counterText: '',
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            // One choice with the Breakdown tab.
            if (heavy)
              CheckboxLabel(
                label: i18n.t('option-heavy'),
                value: useHeavy,
                onChanged: ref.read(breakdownProvider.notifier).setHeavy,
              ),
            OutlinedButton(
              onPressed: onGiveUp,
              child: Text(i18n.t('cards-give-up')),
            ),
            FilledButton(
              onPressed: onSubmit,
              child: Text(i18n.t('cards-check')),
            ),
          ],
        ),
      ],
    );
  }
}

/// All the answers that the card accepts, each in its own direction.
class _OtherAnswers extends StatelessWidget {
  const _OtherAnswers({required this.answers, required this.info});

  final List<String> answers;
  final LanguageInfo info;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final muted = TextStyle(
      color: Theme.of(context).colorScheme.onSurfaceVariant,
    );
    return Wrap(
      spacing: 6,
      children: [
        Text(i18n.t('cards-accepted-answers'), style: muted),
        for (final (index, answer) in answers.indexed) ...[
          if (index > 0) Text('·', style: muted),
          Text(
            answer,
            locale: languageLocale(info),
            textDirection: textDirection(info),
            style: muted,
          ),
        ],
      ],
    );
  }
}

/// A rating. The rating of now is filled. The number is the key.
class _RatingButton extends StatelessWidget {
  const _RatingButton({
    required this.rating,
    required this.current,
    required this.onPressed,
  });

  final int rating;
  final bool current;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final label = Text(I18n.of(context).t('rating-button-$rating'));
    return Semantics(
      selected: current,
      child: current
          ? FilledButton(onPressed: onPressed, child: label)
          : OutlinedButton(onPressed: onPressed, child: label),
    );
  }
}
