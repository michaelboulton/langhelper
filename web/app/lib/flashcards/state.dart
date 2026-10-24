import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../breakdown/state.dart';
import '../providers.dart';

/// The line over the decks and the card.
sealed class CardsStatus {
  const CardsStatus();
}

class CardsIdle extends CardsStatus {
  const CardsIdle();
}

class CardsWorking extends CardsStatus {
  const CardsWorking({required this.heavy});

  final bool heavy;
}

class CardsFailed extends CardsStatus {
  const CardsFailed(this.error);

  final Object error;
}

/// The message [id] of the catalogs.
class CardsNote extends CardsStatus {
  const CardsNote(this.id, {this.args = const {}, this.error = false});

  final String id;
  final Map<String, Object?> args;
  final bool error;
}

/// The user enters the study language: a "to_study" or a "dictation" card.
bool studyAnswers(CardDirection direction) =>
    direction == CardDirection.toStudy || direction == CardDirection.dictation;

const _keep = Object();

@immutable
class CardsState {
  const CardsState({
    this.decks,
    this.deck,
    this.next,
    this.answered,
    this.typed = '',
    this.rating,
    this.nextDue,
    this.status = const CardsIdle(),
    this.selected,
  });

  /// Null until the list loads.
  final List<Deck>? decks;

  /// The deck of the card. Null on the list of decks.
  final Deck? deck;

  /// The card, or the note that the deck has no card for now. Null until it
  /// loads.
  final NextResult? next;

  /// The answer of the server to the text of the user. Null before the
  /// answer.
  final AnswerResponse? answered;

  /// The text that the user sent.
  final String typed;

  /// The rating of the answer and the next due time, ISO 8601. The user can
  /// change the rating.
  final int? rating;
  final String? nextDue;
  final CardsStatus status;
  final Selected? selected;

  NextCard? get card => switch (next) {
    final NextCard card => card,
    _ => null,
  };

  CardsState copyWith({
    Object? decks = _keep,
    Object? deck = _keep,
    Object? next = _keep,
    Object? answered = _keep,
    String? typed,
    Object? rating = _keep,
    Object? nextDue = _keep,
    CardsStatus? status,
    Object? selected = _keep,
  }) => CardsState(
    decks: identical(decks, _keep) ? this.decks : decks as List<Deck>?,
    deck: identical(deck, _keep) ? this.deck : deck as Deck?,
    next: identical(next, _keep) ? this.next : next as NextResult?,
    answered: identical(answered, _keep)
        ? this.answered
        : answered as AnswerResponse?,
    typed: typed ?? this.typed,
    rating: identical(rating, _keep) ? this.rating : rating as int?,
    nextDue: identical(nextDue, _keep) ? this.nextDue : nextDue as String?,
    status: status ?? this.status,
    selected: identical(selected, _keep)
        ? this.selected
        : selected as Selected?,
  );
}

final cardsProvider = NotifierProvider<Cards, CardsState>(Cards.new);

/// The decks, the card, the answer and the rating of the Flashcards tab.
class Cards extends Notifier<CardsState> {
  late Api _api;

  /// Changes with each new list or card, so the answer of an older request
  /// is dropped.
  int _view = 0;

  /// A check is in flight: a second click sends nothing.
  bool _checking = false;
  final _shown = Stopwatch();

  @override
  CardsState build() {
    _api = ref.watch(apiProvider);
    unawaited(Future.microtask(loadDecks));
    return const CardsState();
  }

  /// The "Large models" choice of the Breakdown tab, for a language that has
  /// them.
  bool _heavy(String language) {
    final breakdown = ref.read(breakdownProvider);
    final info = breakdown.languages?.study[language];
    return breakdown.heavy && (info?.variants.contains('heavy') ?? false);
  }

  /// Run [action] for the view of now. An error goes to the status line.
  Future<void> _attempt(
    Future<void> Function(int view) action, {
    bool heavy = false,
  }) async {
    final view = _view;
    final working = CardsWorking(heavy: heavy);
    state = state.copyWith(status: working);
    try {
      await action(view);
      if (ref.mounted && view == _view && identical(state.status, working)) {
        state = state.copyWith(status: const CardsIdle());
      }
    } on Object catch (error) {
      if (!ref.mounted || view != _view) return;
      state = state.copyWith(status: CardsFailed(error));
    }
  }

  /// The list of decks, with the counts of now.
  Future<void> loadDecks() async {
    _view++;
    _checking = false;
    state = const CardsState();
    await _attempt((view) async {
      final decks = (await _api.flashcards.decks()).decks;
      if (!ref.mounted || view != _view) return;
      state = state.copyWith(
        decks: decks,
        status: decks.isEmpty ? const CardsNote('cards-no-decks') : null,
      );
    });
  }

  Future<void> openDeck(Deck deck) {
    state = state.copyWith(deck: deck);
    return nextCard();
  }

  Future<void> nextCard() async {
    final deck = state.deck;
    if (deck == null) return;
    _view++;
    _checking = false;
    final heavy = _heavy(deck.language);
    await _attempt((view) async {
      final next = await _api.flashcards.next(deck.id, heavy: heavy);
      if (!ref.mounted || view != _view) return;
      state = state.copyWith(
        next: next,
        answered: null,
        typed: '',
        rating: null,
        nextDue: null,
        selected: null,
      );
      _shown
        ..reset()
        ..start();
    }, heavy: heavy);
  }

  Future<void> check(String typed) async {
    final card = state.card;
    if (card == null || state.answered != null || _checking) return;
    _checking = true;
    final heavy = _heavy(card.language);
    await _attempt((view) async {
      try {
        final answered = await _api.flashcards.answer(
          card.cardId,
          AnswerRequest(
            typed: typed,
            heavy: heavy,
            elapsedMs: _shown.elapsedMilliseconds,
          ),
        );
        if (!ref.mounted || view != _view) return;
        state = state.copyWith(
          answered: answered,
          typed: typed,
          rating: answered.rating,
          nextDue: answered.nextDue,
          selected: null,
        );
      } finally {
        if (view == _view) _checking = false;
      }
    }, heavy: heavy);
  }

  /// Another rating than the one of the server.
  Future<void> rate(int rating) async {
    final answered = state.answered;
    if (answered == null) return;
    await _attempt((view) async {
      final result = await _api.flashcards.rating(answered.reviewId, rating);
      if (!ref.mounted || view != _view) return;
      state = state.copyWith(rating: result.rating, nextDue: result.nextDue);
    });
  }

  void select(Selected? selected) => state = state.copyWith(selected: selected);

  /// A note of the card view, such as an error of the voices of the
  /// browser.
  void note(CardsStatus status) => state = state.copyWith(status: status);
}
