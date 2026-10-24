import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../breakdown/state.dart';
import '../i18n/i18n.dart';
import 'state.dart';

String countsText(I18n i18n, Counts counts) => i18n.t('cards-counts', {
  'new': counts.newCards,
  'learning': counts.learning,
  'due': counts.due,
});

Counts sumCounts(Iterable<Deck> decks) {
  var (total, newCards, learning, due) = (0, 0, 0, 0);
  for (final each in decks) {
    total += each.counts.total;
    newCards += each.counts.newCards;
    learning += each.counts.learning;
    due += each.counts.due;
  }
  return Counts(total: total, newCards: newCards, learning: learning, due: due);
}

/// A part of the name of a subdeck, with the groups and the decks under it.
class DeckGroup {
  DeckGroup(this.name, this.depth);

  final String name;
  final int depth;

  /// Each one a DeckGroup or a Deck, in the order of the server.
  final items = <Object>[];

  Iterable<Deck> get decks sync* {
    for (final item in items) {
      switch (item) {
        case final Deck deck:
          yield deck;
        case final DeckGroup group:
          yield* group.decks;
      }
    }
  }
}

/// The tree of [decks]. A subdeck has a path: the name of its package, then
/// the parts of its Anki name. The decks come in the order of the tree, so
/// each new part opens one group, and a deck goes into the group of its
/// parent.
DeckGroup deckTree(List<Deck> decks) {
  final root = DeckGroup('', -1);
  final groups = <String, DeckGroup>{};
  for (final deck in decks) {
    var parent = root;
    final inner = deck.path.isEmpty
        ? const <String>[]
        : deck.path.sublist(0, deck.path.length - 1);
    for (final (depth, part) in inner.indexed) {
      // A name part cannot hold a newline.
      final key = inner.sublist(0, depth + 1).join('\n');
      final outer = parent;
      parent = groups.putIfAbsent(key, () {
        final group = DeckGroup(part, depth);
        outer.items.add(group);
        return group;
      });
    }
    parent.items.add(deck);
  }
  return root;
}

/// The decks of the admin, as a tree of the subdecks.
class DeckList extends StatelessWidget {
  const DeckList({super.key, required this.decks});

  final List<Deck> decks;

  @override
  Widget build(BuildContext context) => _GroupItems(group: deckTree(decks));
}

class _GroupItems extends StatelessWidget {
  const _GroupItems({required this.group});

  final DeckGroup group;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final (index, item) in group.items.indexed)
          Padding(
            padding: EdgeInsets.only(top: index == 0 ? 0 : 8),
            child: switch (item) {
              final Deck deck => DeckButton(deck: deck),
              final DeckGroup inner => _Group(group: inner),
              _ => const SizedBox.shrink(),
            },
          ),
      ],
    );
  }
}

class _Group extends StatelessWidget {
  const _Group({required this.group});

  final DeckGroup group;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    final under = group.decks.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 8, bottom: 8),
          child: Wrap(
            spacing: 16,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              Semantics(
                header: true,
                child: Text(
                  group.name,
                  style: TextStyle(
                    fontSize: group.depth == 0 ? 16 : 15.2,
                    fontWeight: group.depth == 0
                        ? FontWeight.bold
                        : FontWeight.w600,
                  ),
                ),
              ),
              Text(
                i18n.t('cards-group-summary', {
                  'decks': under.length,
                  'counts': countsText(i18n, sumCounts(under)),
                }),
                style: TextStyle(
                  color: theme.colorScheme.onSurfaceVariant,
                  fontSize: 14.4,
                ),
              ),
            ],
          ),
        ),
        Container(
          margin: const EdgeInsetsDirectional.only(start: 4),
          padding: const EdgeInsetsDirectional.only(start: 12),
          decoration: BoxDecoration(
            border: BorderDirectional(
              start: BorderSide(
                width: 2,
                color: theme.colorScheme.outlineVariant,
              ),
            ),
          ),
          child: _GroupItems(group: group),
        ),
      ],
    );
  }
}

/// One deck: its name, its language, the number of cards and the counts. A
/// tap shows its next card.
class DeckButton extends ConsumerWidget {
  const DeckButton({super.key, required this.deck});

  final Deck deck;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    final muted = TextStyle(color: theme.colorScheme.onSurfaceVariant);
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final info = languages?.info(deck.language);
    return Material(
      color: theme.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => ref.read(cardsProvider.notifier).openDeck(deck),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Wrap(
            spacing: 16,
            runSpacing: 4,
            children: [
              // In a group, the headings over it give the first parts of
              // the name.
              Text(
                deck.path.lastOrNull ?? deck.name,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Text(
                i18n.t('cards-deck-summary', {
                  'language': info == null
                      ? deck.language
                      : i18n.languageName(info),
                  'cards': deck.counts.total,
                }),
                style: muted,
              ),
              Text(countsText(i18n, deck.counts), style: muted),
            ],
          ),
        ),
      ),
    );
  }
}
