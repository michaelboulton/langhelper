import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/models.dart';
import '../providers.dart';

@immutable
class ProgressState {
  const ProgressState({this.users, this.of, this.stats, this.error});

  /// The users whose numbers the user can see. Null until the list loads.
  final UsersResponse? users;

  /// The `id` of the selected user. Null for the user.
  final String? of;

  /// The numbers of the selected user. Null until they load, and after an
  /// error.
  final StatsResponse? stats;
  final Object? error;
}

final progressProvider = NotifierProvider<Progress, ProgressState>(
  Progress.new,
);

/// The users and the numbers of the Progress tab. The tab loads them each
/// time that it opens.
class Progress extends Notifier<ProgressState> {
  late Api _api;

  /// Changes with each load, so the answer of an older load is dropped.
  int _load = 0;

  @override
  ProgressState build() {
    _api = ref.watch(apiProvider);
    return const ProgressState();
  }

  Future<void> load() async {
    final load = ++_load;
    final of = state.of;
    try {
      final users = state.users ?? await _api.flashcards.users();
      final stats = await _api.flashcards.stats(of: of);
      if (!ref.mounted || load != _load) return;
      state = ProgressState(users: users, of: of, stats: stats);
    } on Object catch (error) {
      if (!ref.mounted || load != _load) return;
      state = ProgressState(users: state.users, of: of, error: error);
    }
  }

  /// The numbers of another user, for an admin.
  Future<void> select(String id) {
    final users = state.users;
    state = ProgressState(
      users: users,
      of: id == users?.me ? null : id,
      stats: state.stats,
    );
    return load();
  }
}
