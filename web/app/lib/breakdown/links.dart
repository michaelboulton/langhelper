import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../api/models.dart';

/// Two linked words: [upper] is on the upper row. A guess comes only from
/// the position of the two words.
typedef ChipLink = ({Word upper, Word lower, bool guess});

/// One curve, in the coordinates of the layer.
typedef LinkLine = ({Offset from, Offset to, bool guess, bool selected});

final _chipKeys = Expando<GlobalKey>('chip');

/// The key of the chip of [word]. The layer finds the chip through it.
GlobalKey chipKey(Word word) => _chipKeys[word] ??= GlobalKey();

/// The chips of [child], with a curve for each of [links] under them. The
/// links of [selected] are thick. web/README.md, "The link layer", has the
/// details.
class LinkLayer extends StatefulWidget {
  const LinkLayer({
    super.key,
    required this.links,
    this.selected,
    required this.child,
  });

  final List<ChipLink> links;
  final Word? selected;

  /// The sentences. Each chip of a linked word has its [chipKey].
  final Widget child;

  @override
  State<LinkLayer> createState() => _LinkLayerState();
}

class _LinkLayerState extends State<LinkLayer> {
  List<LinkLine> _lines = const [];

  @override
  void initState() {
    super.initState();
    // The web app loads a fallback font after the first frame, and the
    // chips change size.
    PaintingBinding.instance.systemFonts.addListener(_measureSoon);
  }

  @override
  void dispose() {
    PaintingBinding.instance.systemFonts.removeListener(_measureSoon);
    super.dispose();
  }

  void _measureSoon() =>
      SchedulerBinding.instance.addPostFrameCallback((_) => _measure());

  void _measure() {
    if (!mounted) return;
    final layer = context.findRenderObject() as RenderBox?;
    if (layer == null || !layer.hasSize) return;
    Rect? rect(Word word) {
      final box =
          chipKey(word).currentContext?.findRenderObject() as RenderBox?;
      if (box == null || !box.hasSize) return null;
      return MatrixUtils.transformRect(
        box.getTransformTo(layer),
        Offset.zero & box.size,
      );
    }

    final selected = widget.selected;
    final lines = <LinkLine>[
      for (final link in widget.links)
        if ((rect(link.upper), rect(link.lower)) case (final a?, final b?))
          (
            from: a.bottomCenter,
            to: b.topCenter,
            guess: link.guess,
            selected:
                identical(link.upper, selected) ||
                identical(link.lower, selected),
          ),
    ];
    if (!listEquals(lines, _lines)) setState(() => _lines = lines);
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.onSurface;
    // A new width moves the chips, so the layer measures them again.
    return LayoutBuilder(
      builder: (context, constraints) {
        _measureSoon();
        final curves = IgnorePointer(
          child: CustomPaint(painter: LinkPainter(_lines, color)),
        );
        return Stack(
          children: [
            Positioned.fill(
              // The number of curves, for the browser tests.
              child: _lines.isEmpty
                  ? curves
                  : Semantics(
                      container: true,
                      label: 'links: ${_lines.length}',
                      child: curves,
                    ),
            ),
            widget.child,
          ],
        );
      },
    );
  }
}

/// A curve from the bottom centre of the upper chip to the top centre of the
/// lower chip. It leaves and arrives vertically, so crossed links stay
/// readable.
class LinkPainter extends CustomPainter {
  const LinkPainter(this.lines, this.color);

  final List<LinkLine> lines;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    for (final (:from, :to, :guess, :selected) in lines) {
      final bend = max(24.0, (to.dy - from.dy) / 2);
      final path = Path()
        ..moveTo(from.dx, from.dy)
        ..cubicTo(from.dx, from.dy + bend, to.dx, to.dy - bend, to.dx, to.dy);
      canvas.drawPath(
        guess ? dashed(path) : path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = selected ? 3 : 1.5
          ..color = color.withValues(alpha: selected ? 0.9 : 0.35),
      );
    }
  }

  @override
  bool shouldRepaint(LinkPainter oldDelegate) =>
      !listEquals(oldDelegate.lines, lines) || oldDelegate.color != color;
}

/// [path] in dashes of 5 px with gaps of 4 px.
Path dashed(Path path) {
  final dashes = Path();
  for (final metric in path.computeMetrics()) {
    for (var start = 0.0; start < metric.length; start += 9) {
      dashes.addPath(metric.extractPath(start, start + 5), Offset.zero);
    }
  }
  return dashes;
}
