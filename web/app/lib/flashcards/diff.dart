import 'package:flutter/material.dart';

import '../api/models.dart' hide Locale;
import '../breakdown/form.dart' show textDirection;
import '../breakdown/result.dart' show languageLocale;
import '../breakdown/tags.dart' show chipText;

/// The letters of a wrong answer: struck out in red. The color of the page
/// of static/.
const deleteRed = Color(0xFFC0392B);

/// The missing letters: on the green of ADJ.
const insertGreen = Color(0xFFA8E6A1);

/// The answer of the user against the correct one: the wrong letters are
/// struck out, and the missing ones are marked.
class DiffText extends StatelessWidget {
  const DiffText({super.key, required this.diff, required this.info});

  final List<DiffSpan> diff;

  /// The language of the answer.
  final LanguageInfo info;

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          for (final span in diff)
            TextSpan(
              text: span.text,
              style: switch (span.op) {
                DiffOp.equal => null,
                DiffOp.delete => const TextStyle(
                  color: deleteRed,
                  decoration: TextDecoration.lineThrough,
                  decorationColor: deleteRed,
                ),
                DiffOp.insert => const TextStyle(
                  color: chipText,
                  backgroundColor: insertGreen,
                ),
              },
            ),
        ],
      ),
      locale: languageLocale(info),
      textDirection: textDirection(info),
      style: const TextStyle(fontSize: 19.2),
    );
  }
}
