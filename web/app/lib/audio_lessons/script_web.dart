import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

import 'courses.dart';
import 'script.dart' show ScriptLine;

export 'script.dart' show ScriptLine;

/// The page of a lesson in a browser: the [header], then the [lines] of its
/// script as HTML. Flutter draws on a canvas, so only HTML lets the browser
/// scroll the script, select in it, and find a text in it (Ctrl+F). The
/// header stays above the script. The style is `.lesson-script` in
/// index.html.
class LessonScript extends StatefulWidget {
  const LessonScript({super.key, required this.header, required this.lines});

  final List<Widget> header;
  final List<ScriptLine> lines;

  @override
  State<LessonScript> createState() => _LessonScriptState();
}

class _LessonScriptState extends State<LessonScript> {
  web.HTMLElement? _root;

  /// The lines in the HTML now.
  List<ScriptLine>? _shown;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _render();
  }

  @override
  void didUpdateWidget(LessonScript old) {
    super.didUpdateWidget(old);
    _render();
  }

  void _render() {
    final root = _root;
    if (root == null) return;
    final scheme = Theme.of(context).colorScheme;
    root.style
      ..setProperty('--text', _css(scheme.onSurface))
      ..setProperty('--muted', _css(scheme.onSurfaceVariant));
    // The page rebuilds on each save of the position. A new HTML would drop
    // the selection and the match of Ctrl+F.
    if (listEquals(_shown, widget.lines)) return;
    _shown = widget.lines;
    final column = web.document.createElement('div');
    for (final line in widget.lines) {
      final row = web.document.createElement('p');
      if (line.speaker case final speaker?) {
        final name = web.document.createElement('b')..textContent = speaker;
        final text = web.document.createElement('span')
          ..textContent = line.text;
        if (line.locale case final locale?) text.setAttribute('lang', locale);
        if (line.direction case final direction?) {
          text.setAttribute('dir', direction.name);
        }
        // The space is for a copy of the line and for the text of the row.
        row
          ..append(name)
          ..append(web.document.createTextNode(' '))
          ..append(text);
      } else {
        row
          ..className = 'pause'
          ..textContent = line.text;
      }
      column.append(row);
    }
    root
      ..textContent = ''
      ..append(column);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, box) {
        final side = pageSide(box.maxWidth);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // A long header scrolls, and leaves the script at least half of
            // the height.
            Flexible(
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(side, 16, side, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: widget.header,
                ),
              ),
            ),
            Expanded(
              child: HtmlElementView.fromTagName(
                tagName: 'div',
                onElementCreated: (element) {
                  _root = (element as web.HTMLElement)
                    ..className = 'lesson-script';
                  _render();
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

/// [color] as a CSS colour.
String _css(Color color) {
  int byte(double channel) => (channel * 255).round();
  return 'rgb(${byte(color.r)} ${byte(color.g)} ${byte(color.b)} / ${color.a})';
}
