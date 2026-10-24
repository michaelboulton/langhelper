import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../breakdown/breakdown_tab.dart' show AccentsLegend, UposLegend;
import '../breakdown/state.dart';
import '../i18n/i18n.dart';
import 'card_view.dart';
import 'decks.dart';
import 'state.dart';

/// The title of the tab. It is also the title of the browser tab.
class FlashcardsTitle extends StatelessWidget {
  const FlashcardsTitle({super.key});

  @override
  Widget build(BuildContext context) {
    final title = I18n.of(context).t('cards-title');
    return Title(
      title: title,
      color: Theme.of(context).primaryColor,
      child: Text(title),
    );
  }
}

/// The Flashcards tab under its title: the list of decks, or a card.
class FlashcardsTab extends ConsumerWidget {
  const FlashcardsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final decks = ref.watch(cardsProvider.select((state) => state.decks));
    final deck = ref.watch(cardsProvider.select((state) => state.deck));
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    // The list of decks has no words, so it has no accent note.
    final accents =
        deck != null && (languages?.info(deck.language)?.hasAccents ?? false);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return SingleChildScrollView(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 64),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(i18n.t('cards-intro'), style: TextStyle(color: muted)),
                const SizedBox(height: 12),
                Callout(text: i18n.t('cards-language-note')),
                const SizedBox(height: 12),
                const CardsStatusLine(),
                const SizedBox(height: 8),
                if (deck != null)
                  const CardView()
                else if (decks != null)
                  DeckList(decks: decks),
                const SizedBox(height: 24),
                const UposLegend(),
                if (accents) const AccentsLegend(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// The yellow note over the decks.
class Callout extends StatelessWidget {
  const Callout({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Semantics(
      container: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: dark ? const Color(0xFF3A3315) : const Color(0xFFFFF8D6),
          border: Border.all(
            color: dark ? const Color(0xFF7A6A2A) : const Color(0xFFE6D27A),
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text),
      ),
    );
  }
}

/// What the tab does now, an error, or a note.
class CardsStatusLine extends ConsumerWidget {
  const CardsStatusLine({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final status = ref.watch(cardsProvider.select((state) => state.status));
    final (text, error) = switch (status) {
      CardsIdle() => ('', false),
      CardsWorking(heavy: true) => (i18n.t('status-working-heavy'), false),
      CardsWorking() => (i18n.t('status-working'), false),
      CardsFailed(error: final failure) => (i18n.errorText(failure), true),
      CardsNote(:final id, :final args, :final error) => (
        i18n.t(id, args),
        error,
      ),
    };
    return Semantics(
      liveRegion: true,
      child: Text(
        text,
        style: TextStyle(
          color: error
              ? const Color(0xFFC0392B)
              : Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}
