import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/client.dart';
import '../api/models.dart' hide Locale;
import '../breakdown/tags.dart' show tagId;
import '../i18n/i18n.dart';
import '../providers.dart';

/// The questions of the server, read one time. Null when the server does not
/// answer: then no panel shows.
final questionsProvider = FutureProvider<QuestionsResponse?>((ref) async {
  try {
    return await ref.watch(apiProvider).explain.questions();
  } on Object catch (error) {
    debugPrint('explain: no questions: $error');
    return null;
  }
});

/// The server stops the AI service after 30 s (explain/base.py TIMEOUT), and
/// the tagger can load a model first. A request with no answer after this
/// time (a proxy that holds the connection) stops, so the user can ask again.
const explainTimeout = Duration(seconds: 60);

/// What the questions of a panel are about.
sealed class ExplainTarget {
  const ExplainTarget();

  /// The kinds of question that the route of the target can answer.
  List<QuestionPlace> get places;

  Future<ExplainResponse> ask(
    ExplainApi api, {
    required String question,
    required String userContext,
    required String locale,
  });
}

/// A text of the breakdown, in the study language.
final class SentenceTarget extends ExplainTarget {
  const SentenceTarget({required this.text, required this.language});

  final String text;
  final String language;

  @override
  List<QuestionPlace> get places => const [QuestionPlace.sentence];

  @override
  Future<ExplainResponse> ask(
    ExplainApi api, {
    required String question,
    required String userContext,
    required String locale,
  }) => api.sentence(
    ExplainSentenceRequest(
      question: question,
      userContext: userContext,
      locale: locale,
      text: text,
      language: language,
    ),
    timeout: explainTimeout,
  );

  @override
  bool operator ==(Object other) =>
      other is SentenceTarget &&
      other.text == text &&
      other.language == language;

  @override
  int get hashCode => Object.hash(text, language);
}

/// An answer to a card. The server reads the card and the answer from the
/// review.
final class ReviewTarget extends ExplainTarget {
  const ReviewTarget(this.reviewId);

  final int reviewId;

  @override
  List<QuestionPlace> get places => const [
    QuestionPlace.card,
    QuestionPlace.sentence,
  ];

  @override
  Future<ExplainResponse> ask(
    ExplainApi api, {
    required String question,
    required String userContext,
    required String locale,
  }) => api.review(
    reviewId,
    ExplainRequest(
      question: question,
      userContext: userContext,
      locale: locale,
    ),
    timeout: explainTimeout,
  );

  @override
  bool operator ==(Object other) =>
      other is ReviewTarget && other.reviewId == reviewId;

  @override
  int get hashCode => reviewId.hashCode;
}

typedef _Note = ({String text, bool error});

/// The "explain with AI" panel: one button for each question about
/// [target], and a field for more about the question. The server writes the
/// prompt, and the text goes to an AI service, so a request goes out only on
/// a click. With no key on the server, the panel does not show.
class ExplainPanel extends ConsumerStatefulWidget {
  const ExplainPanel({super.key, required this.target});

  final ExplainTarget target;

  @override
  ConsumerState<ExplainPanel> createState() => _ExplainPanelState();
}

class _ExplainPanelState extends ConsumerState<ExplainPanel> {
  final _context = TextEditingController();
  bool _working = false;
  ExplainResponse? _answer;
  _Note? _note;

  /// Changes with the target, so the answer about an older one is dropped.
  int _asks = 0;

  @override
  void didUpdateWidget(ExplainPanel old) {
    super.didUpdateWidget(old);
    // The same target again (an automatic send) keeps the answer.
    if (old.target == widget.target) return;
    _asks++;
    _context.clear();
    _working = false;
    _answer = null;
    _note = null;
  }

  @override
  void dispose() {
    _context.dispose();
    super.dispose();
  }

  Future<void> _ask(ExplainQuestion question) async {
    final asks = _asks;
    final i18n = I18n.of(context);
    setState(() {
      _working = true;
      _answer = null;
      _note = (text: i18n.t('explain-working'), error: false);
    });
    ExplainResponse? answer;
    _Note? note;
    try {
      // The AI answers in the language of the page.
      answer = await widget.target.ask(
        ref.read(apiProvider).explain,
        question: question.id,
        userContext: _context.text.trim(),
        locale: i18n.locale,
      );
    } on Object catch (error) {
      final timeout =
          error is ApiCanceled && error.reason == CancelReason.timeout;
      note = (
        text: timeout
            ? i18n.t('explain-timeout', {'seconds': explainTimeout.inSeconds})
            : i18n.errorText(error),
        error: true,
      );
    }
    if (!mounted || asks != _asks) return;
    setState(() {
      _working = false;
      _answer = answer;
      _note = note;
    });
  }

  @override
  Widget build(BuildContext context) {
    final questions = ref.watch(questionsProvider).value;
    if (questions == null || !questions.available) {
      return const SizedBox.shrink();
    }
    final places = widget.target.places;
    final asked = [
      for (final question in questions.questions)
        if (places.contains(question.where)) question,
    ];
    if (asked.isEmpty) return const SizedBox.shrink();
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    final muted = theme.colorScheme.onSurfaceVariant;
    final answer = _answer;
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.only(top: 12),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(i18n.t('explain-ask'), style: TextStyle(color: muted)),
              for (final question in asked)
                OutlinedButton(
                  onPressed: _working ? null : () => unawaited(_ask(question)),
                  // The server has the English label, for a question with no
                  // message.
                  child: Text(
                    i18n.tOr(
                      tagId('explain-question', question.id),
                      fallback: question.label,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _context,
            maxLength: questions.maxContextChars,
            decoration: InputDecoration(
              hintText: i18n.t('explain-context-placeholder'),
              border: const OutlineInputBorder(),
              isDense: true,
              counterText: '',
            ),
          ),
          if (answer != null) ...[
            const SizedBox(height: 10),
            // Only as text: the answer of a model is never markup.
            SelectionArea(
              child: Text(answer.text, locale: Locale(i18n.locale)),
            ),
            const SizedBox(height: 4),
            Text(
              i18n.t('explain-written-by', {'model': answer.model}),
              style: TextStyle(color: muted, fontSize: 14.4),
            ),
          ],
          if (_note case final note?)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Semantics(
                liveRegion: true,
                child: Text(
                  note.text,
                  style: TextStyle(
                    color: note.error ? const Color(0xFFC0392B) : muted,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
