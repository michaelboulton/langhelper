import 'package:flutter/material.dart';

import 'courses.dart';

/// A line of the script of a lesson, ready to show. [speaker] is the name of
/// the speaker in the language of the page, and null for a pause. [locale]
/// and [direction] are those of [text]; a pause has neither.
typedef ScriptLine = ({
  String? speaker,
  String text,
  String? locale,
  TextDirection? direction,
});

/// The page of a lesson: the [header], then the [lines] of its script in a
/// lazy list, so that only the lines on the screen are built. This is the
/// version for a native app and for `flutter test`; script_web.dart is the
/// version for a browser.
class LessonScript extends StatelessWidget {
  const LessonScript({super.key, required this.header, required this.lines});

  final List<Widget> header;
  final List<ScriptLine> lines;

  @override
  Widget build(BuildContext context) {
    // The SelectionArea is over the scroll view, so that it can hold the
    // lazy list of the script. Only the script is selectable.
    return SelectionArea(
      child: AudioPage(
        sliver: SliverList.list(
          children: [for (final line in lines) _Line(line: line)],
        ),
        children: [
          SelectionContainer.disabled(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: header,
            ),
          ),
        ],
      ),
    );
  }
}

/// The speaker in the language of the page, then the text in its own
/// language and direction. A pause is grey and italic.
class _Line extends StatelessWidget {
  const _Line({required this.line});

  final ScriptLine line;

  @override
  Widget build(BuildContext context) {
    final speaker = line.speaker;
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    // One node for each line: else the SelectionArea merges the lines into
    // one label, out of order.
    return Semantics(
      container: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: speaker == null
            ? Text(
                line.text,
                style: TextStyle(color: muted, fontStyle: FontStyle.italic),
              )
            : Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    speaker,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      line.text,
                      locale: switch (line.locale) {
                        final code? => Locale(code),
                        null => null,
                      },
                      textDirection: line.direction,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
