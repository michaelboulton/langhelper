import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/models.dart' hide Locale;
import '../i18n/i18n.dart';
import 'state.dart';

/// The key of the text field, for the tests.
const textFieldKey = Key('breakdown-text');

TextDirection textDirection(LanguageInfo info) =>
    info.direction == ScriptDirection.rtl
    ? TextDirection.rtl
    : TextDirection.ltr;

/// The name of the study language for the text of the tab. Before the list
/// of languages loads, Croatian, as on the page of static/.
String studyName(I18n i18n, LanguageInfo? info) =>
    info == null ? i18n.t('language-name-hr') : i18n.languageName(info);

/// The language, the side that the user enters, the text and the options.
/// A change sends the form after [debounceTime], and Ctrl+Enter or
/// Cmd+Enter sends it at once.
class BreakdownForm extends ConsumerStatefulWidget {
  const BreakdownForm({super.key});

  @override
  ConsumerState<BreakdownForm> createState() => _BreakdownFormState();
}

class _BreakdownFormState extends ConsumerState<BreakdownForm> {
  final _text = TextEditingController();
  final _timeout = TextEditingController(text: '5');

  /// The text that the notifier has.
  String _known = '';

  @override
  void initState() {
    super.initState();
    _text.addListener(_onText);
  }

  @override
  void dispose() {
    _text.dispose();
    _timeout.dispose();
    super.dispose();
  }

  void _onText() {
    final value = _text.value;
    // An input method (IME) makes a word from many keys, for example kanji
    // from Latin letters. The text in the middle of that is not what the
    // user means.
    if (value.isComposingRangeValid || value.text == _known) return;
    _known = value.text;
    ref.read(breakdownProvider.notifier).setText(value.text);
  }

  void _onTimeout(String text) {
    final seconds = int.tryParse(text) ?? 0;
    ref
        .read(breakdownProvider.notifier)
        .setTimeout(seconds > 0 ? seconds.clamp(1, 600) : 5);
  }

  @override
  Widget build(BuildContext context) {
    // The saved text comes with the list of languages. Only that change
    // goes from the state to the field: a notification can come after newer
    // keys, and must not undo them.
    ref.listen(breakdownProvider.select((state) => state.languages), (_, _) {
      final text = ref.read(breakdownProvider).text;
      if (text == _known) return;
      _known = text;
      _text.text = text;
    });
    final i18n = I18n.of(context);
    final state = ref.watch(breakdownProvider);
    final notifier = ref.read(breakdownProvider.notifier);
    final info = state.info;
    final english = state.source == Source.en;
    final named = {'language': studyName(i18n, info)};
    final entered = english ? state.languages?.english : info;
    final submit = notifier.submit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 16,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            _LanguageMenu(state: state, onChanged: notifier.setLanguage),
            RadioGroup<Source>(
              groupValue: state.source,
              onChanged: (source) => notifier.setSource(source!),
              child: Wrap(
                spacing: 16,
                children: [
                  _RadioLabel(
                    value: Source.study,
                    label: i18n.t('breakdown-source-study', named),
                    onTap: () => notifier.setSource(Source.study),
                  ),
                  _RadioLabel(
                    value: Source.en,
                    label: i18n.t('breakdown-source-english', named),
                    onTap: () => notifier.setSource(Source.en),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.enter, control: true):
                submit,
            const SingleActivator(LogicalKeyboardKey.enter, meta: true): submit,
          },
          child: TextField(
            key: textFieldKey,
            controller: _text,
            autofocus: true,
            minLines: 3,
            maxLines: null,
            maxLength: 1000,
            keyboardType: TextInputType.multiline,
            textDirection: entered == null ? null : textDirection(entered),
            decoration: InputDecoration(
              hintText: entered?.placeholder,
              border: const OutlineInputBorder(),
              counterText: '',
            ),
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (state.hasVariant('heavy'))
              _CheckboxLabel(
                label: i18n.t('option-heavy'),
                value: state.heavy,
                onChanged: notifier.setHeavy,
              ),
            if (state.useHeavy && state.hasVariant('nonstandard'))
              _CheckboxLabel(
                label: i18n.t('option-nonstandard'),
                value: state.nonstandard,
                // An English text always gets its translation, and DeepL
                // writes the standard language.
                onChanged: english ? null : notifier.setNonstandard,
              ),
            _CheckboxLabel(
              label: i18n.t('option-translate'),
              value: state.translate,
              onChanged: english ? null : notifier.setTranslate,
            ),
            SizedBox(
              width: 140,
              child: TextField(
                controller: _timeout,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                onChanged: _onTimeout,
                decoration: InputDecoration(
                  labelText: i18n.t('option-time-limit'),
                  suffixText: i18n.t('unit-seconds'),
                  isDense: true,
                  border: const OutlineInputBorder(),
                ),
              ),
            ),
            if (state.sending)
              OutlinedButton(
                onPressed: notifier.cancel,
                child: Text(i18n.t('breakdown-cancel')),
              ),
            FilledButton(
              onPressed: submit,
              child: Text(i18n.t('breakdown-go')),
            ),
          ],
        ),
      ],
    );
  }
}

class _LanguageMenu extends StatelessWidget {
  const _LanguageMenu({required this.state, required this.onChanged});

  final BreakdownState state;
  final void Function(String code) onChanged;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final languages = state.languages?.study.values ?? const <LanguageInfo>[];
    final label = i18n.t('breakdown-language');
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label),
        const SizedBox(width: 8),
        Semantics(
          label: label,
          child: DropdownButton<String>(
            // No list: the menu stays empty, and the form sends nothing.
            value: state.info?.code,
            onChanged: (code) => onChanged(code!),
            items: [
              for (final info in languages)
                DropdownMenuItem(
                  value: info.code,
                  child: Text(i18n.languageName(info)),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _RadioLabel extends StatelessWidget {
  const _RadioLabel({
    required this.value,
    required this.label,
    required this.onTap,
  });

  final Source value;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return MergeSemantics(
      child: InkWell(
        onTap: onTap,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Radio<Source>(value: value),
            Flexible(child: Text(label)),
            const SizedBox(width: 8),
          ],
        ),
      ),
    );
  }
}

/// A checkbox with its label. With no [onChanged], it is greyed out.
class _CheckboxLabel extends StatelessWidget {
  const _CheckboxLabel({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final bool value;
  final void Function(bool value)? onChanged;

  @override
  Widget build(BuildContext context) {
    final change = onChanged;
    final theme = Theme.of(context);
    return Opacity(
      opacity: change == null ? 0.5 : 1,
      child: MergeSemantics(
        child: InkWell(
          onTap: change == null ? null : () => change(!value),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Checkbox(
                value: value,
                onChanged: change == null ? null : (value) => change(value!),
              ),
              Flexible(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
              const SizedBox(width: 8),
            ],
          ),
        ),
      ),
    );
  }
}
