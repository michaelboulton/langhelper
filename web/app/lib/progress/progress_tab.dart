import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart';
import '../flashcards/browser.dart'
    if (dart.library.js_interop) '../flashcards/browser_web.dart';
import '../flashcards/decks.dart' show countsText;
import '../i18n/i18n.dart';
import 'charts.dart';
import 'state.dart';

/// The title of the tab. It is also the title of the browser tab.
class ProgressTitle extends StatelessWidget {
  const ProgressTitle({super.key});

  @override
  Widget build(BuildContext context) {
    final title = I18n.of(context).t('tab-progress');
    return Title(
      title: title,
      color: Theme.of(context).primaryColor,
      child: Text(title),
    );
  }
}

/// The Progress tab: the numbers and the charts of the user, for all decks.
/// An admin can select another user.
class ProgressTab extends ConsumerWidget {
  const ProgressTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final state = ref.watch(progressProvider);
    final users = state.users;
    final stats = state.stats;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    final error = state.error;
    final status = error != null
        ? i18n.errorText(error)
        : stats != null && stats.reviews == 0
        ? i18n.t('progress-no-answers')
        : '';
    return SingleChildScrollView(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 860),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 64),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (users != null && users.admin)
                  _UserSelector(users: users, of: state.of ?? users.me),
                if (status.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(
                        status,
                        style: TextStyle(
                          color: error != null
                              ? const Color(0xFFC0392B)
                              : muted,
                        ),
                      ),
                    ),
                  ),
                if (error == null && stats != null && stats.reviews > 0) ...[
                  StatsTable(stats: stats),
                  ProgressCharts(days: stats.days),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// "Cards of" and the users whose numbers the admin can see.
class _UserSelector extends ConsumerWidget {
  const _UserSelector({required this.users, required this.of});

  final UsersResponse users;
  final String of;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    return Wrap(
      spacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text(i18n.t('progress-cards-of')),
        DropdownButton<String>(
          value: of,
          onChanged: (id) {
            if (id == null) return;
            unawaited(ref.read(progressProvider.notifier).select(id));
          },
          items: [
            for (final user in users.users)
              DropdownMenuItem(
                value: user.id,
                // The entry of the user has an English name from the server.
                child: Text(
                  user.id == users.me
                      ? i18n.t('progress-own-cards')
                      : user.name,
                ),
              ),
          ],
        ),
      ],
    );
  }
}

/// The answers, the share that was not "Again", the lapses, the days in a
/// row and the cards.
class StatsTable extends StatelessWidget {
  const StatsTable({super.key, required this.stats});

  final StatsResponse stats;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final counts = stats.counts;
    final rows = [
      (i18n.t('progress-answers'), '${stats.reviews}'),
      if (stats.successRate case final rate?)
        (i18n.t('progress-passed'), percent(i18n.locale, rate)),
      (i18n.t('progress-lapses'), '${stats.lapses}'),
      (i18n.t('progress-streak'), '${stats.streakDays}'),
      if (counts != null)
        (
          i18n.t('progress-cards'),
          i18n.t('progress-cards-value', {
            'total': counts.total,
            'counts': countsText(i18n, counts),
          }),
        ),
    ];
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Table(
        columnWidths: const {0: IntrinsicColumnWidth()},
        defaultVerticalAlignment: TableCellVerticalAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          for (final (name, value) in rows)
            TableRow(
              children: [
                Padding(
                  padding: const EdgeInsetsDirectional.only(
                    end: 16,
                    top: 4,
                    bottom: 4,
                  ),
                  child: Text(
                    name,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                Text(value),
              ],
            ),
        ],
      ),
    );
  }
}
