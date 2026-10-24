import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../explain/explain_panel.dart';
import '../i18n/i18n.dart';
import '../listen/listen_panel.dart';
import 'form.dart';
import 'result.dart';
import 'state.dart';
import 'tags.dart';

/// "Croatian heavy": the models of one language and one model type.
String modelName(I18n i18n, Languages? languages, String code, String variant) {
  final info = languages?.info(code);
  return i18n.t('model-name', {
    'language': info == null ? code : i18n.languageName(info),
    'variant': variant,
  });
}

/// The title of the tab, with the name of the study language. It is also
/// the title of the browser tab.
class BreakdownTitle extends ConsumerWidget {
  const BreakdownTitle({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final info = ref.watch(breakdownProvider.select((state) => state.info));
    final title = i18n.t('breakdown-title', {
      'language': studyName(i18n, info),
    });
    return Title(
      title: title,
      color: Theme.of(context).primaryColor,
      child: Text(title),
    );
  }
}

/// The Breakdown tab under its title.
class BreakdownTab extends ConsumerWidget {
  const BreakdownTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final info = ref.watch(breakdownProvider.select((state) => state.info));
    final heavy = ref.watch(
      breakdownProvider.select((state) => state.useHeavy),
    );
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
                const ModelsBanner(),
                Text(
                  i18n.t('breakdown-intro', {
                    'language': studyName(i18n, info),
                  }),
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 20),
                const BreakdownForm(),
                const SizedBox(height: 16),
                // What the light model of the language cannot do.
                if (info != null && !heavy && info.lightNote.isNotEmpty) ...[
                  Text(
                    i18n.tOr(
                      'language-${info.code}-light-note',
                      fallback: info.lightNote,
                    ),
                    style: TextStyle(color: muted),
                  ),
                  const SizedBox(height: 16),
                ],
                const StatusLine(),
                const SizedBox(height: 8),
                // The words and the table can be copied.
                const SelectionArea(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [BreakdownResult(), WordDetail()],
                  ),
                ),
                const BreakdownExplain(),
                const BreakdownListen(),
                const SizedBox(height: 16),
                const UposLegend(),
                if (info?.hasAccents ?? false) const AccentsLegend(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// The questions to the AI about the text in the study language. A
/// translation that failed has no such text.
class BreakdownExplain extends ConsumerWidget {
  const BreakdownExplain({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(breakdownProvider.select((state) => state.result));
    if (data == null || data.text.isEmpty) return const SizedBox.shrink();
    return ExplainPanel(
      target: SentenceTarget(text: data.text, language: data.language),
    );
  }
}

/// The Listen panel of the breakdown: the text that the user entered, and
/// its translation.
class BreakdownListen extends ConsumerWidget {
  const BreakdownListen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(breakdownProvider.select((state) => state.result));
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    if (data == null || languages == null) return const SizedBox.shrink();
    final translation = data.translation;
    // data.text is always the study language, and translation.text English.
    return ListenPanel(
      targets: [
        if (languages.study[data.language] case final study?)
          (text: data.text, info: study),
        if (translation != null && translation.error.isEmpty)
          (text: translation.text, info: languages.english),
      ],
    );
  }
}

/// A note while the server loads models, for example in the first 10 to 20
/// seconds after a boot.
class ModelsBanner extends ConsumerWidget {
  const ModelsBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(modelsProvider);
    if (status == null || !loadingModels(status)) {
      return const SizedBox.shrink();
    }
    final i18n = I18n.of(context);
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final model = status.loadingModel;
    // A server of before the locales gives only the English name.
    final models = model == null
        ? status.loading!
        : modelName(i18n, languages, model.language, model.variant);
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLowest,
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Semantics(
        liveRegion: true,
        child: Row(
          children: [
            const SizedBox.square(
              dimension: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                i18n.t('status-loading-models', {'models': models}),
                style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// What the form does now, the models of the last answer, or the error.
class StatusLine extends ConsumerWidget {
  const StatusLine({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final i18n = I18n.of(context);
    final status = ref.watch(breakdownProvider.select((state) => state.status));
    final languages = ref.watch(
      breakdownProvider.select((state) => state.languages),
    );
    final (text, error) = switch (status) {
      Idle() => ('', false),
      Working(heavy: true) => (i18n.t('status-working-heavy'), false),
      Working() => (i18n.t('status-working'), false),
      Done(:final language, :final variant) => (
        i18n.t('status-models', {
          'models': modelName(i18n, languages, language, variant),
        }),
        false,
      ),
      Canceled() => (i18n.t('status-canceled'), false),
      TimedOut(:final seconds) => (
        i18n.t('status-timeout', {'seconds': seconds}),
        true,
      ),
      Failed(error: final failure) => (i18n.errorText(failure), true),
      NoLanguages(error: final failure) => (
        '${i18n.t('error-no-languages')} ${i18n.errorText(failure)}',
        true,
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

/// The colour of each part of speech.
class UposLegend extends StatelessWidget {
  const UposLegend({super.key});

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLowest,
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          for (final MapEntry(key: tag, value: colour) in uposColors.entries)
            DecoratedBox(
              decoration: BoxDecoration(
                color: colour,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                child: Text(
                  '$tag ${uposName(i18n, tag)}',
                  style: const TextStyle(color: chipText, fontSize: 12.8),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// The accent marks, for a language with accent data. Each accent letter
/// that is a word of its own in the text is bold.
class AccentsLegend extends StatelessWidget {
  const AccentsLegend({super.key});

  static final _letter = RegExp(r'(?<=^|\s)[ȁȃàáā](?=\s)');

  @override
  Widget build(BuildContext context) {
    final text = I18n.of(context).t('accents-legend');
    final spans = <TextSpan>[];
    var start = 0;
    for (final match in _letter.allMatches(text)) {
      spans
        ..add(TextSpan(text: text.substring(start, match.start)))
        ..add(
          TextSpan(
            text: match[0],
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        );
      start = match.end;
    }
    spans.add(TextSpan(text: text.substring(start)));
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Text.rich(
        TextSpan(children: spans),
        style: TextStyle(
          fontSize: 13.6,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}
