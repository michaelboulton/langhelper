import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../api/models.dart';
import '../flashcards/browser.dart'
    if (dart.library.js_interop) '../flashcards/browser_web.dart';
import '../i18n/i18n.dart';

/// The two bar charts of the last 90 days: the answers of each day, and the
/// share that was not "Again".
class ProgressCharts extends StatelessWidget {
  const ProgressCharts({super.key, required this.days});

  final List<StatsDay> days;

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final colors = Theme.of(context).colorScheme;
    final muted = TextStyle(color: colors.onSurfaceVariant, fontSize: 14.4);
    final most = days.fold(1, (most, day) => max(most, day.reviews));
    Widget note(String id) => Padding(
      padding: const EdgeInsets.only(top: 16, bottom: 8),
      child: Text(i18n.t(id), style: muted),
    );
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        note('progress-days-note'),
        DayBars(
          days: days,
          maxY: most.toDouble(),
          // The light part is the answers that were "Again".
          rod: (day, width) => BarChartRodData(
            toY: day.reviews.toDouble(),
            width: width,
            color: colors.outlineVariant,
            borderRadius: BorderRadius.zero,
            rodStackItems: [
              BarChartRodStackItem(0, day.passed.toDouble(), colors.onSurface),
            ],
          ),
          tooltip: (day) => i18n.t('progress-day-answers', {
            'date': day.date,
            'answers': day.reviews,
            'passed': day.passed,
          }),
        ),
        note('progress-rate-note'),
        DayBars(
          days: days,
          maxY: 1,
          rod: (day, width) => BarChartRodData(
            toY: day.reviews == 0 ? 0 : day.passed / day.reviews,
            width: width,
            color: colors.onSurface,
            borderRadius: BorderRadius.zero,
          ),
          tooltip: (day) => day.reviews == 0
              ? i18n.t('progress-day-none', {'date': day.date})
              : i18n.t('progress-day-rate', {
                  'date': day.date,
                  'rate': percent(i18n.locale, day.passed / day.reviews),
                }),
        ),
      ],
    );
  }
}

/// One bar for each day, 1 px apart, with the text of the day over the bar
/// under the pointer.
class DayBars extends StatelessWidget {
  const DayBars({
    super.key,
    required this.days,
    required this.maxY,
    required this.rod,
    required this.tooltip,
  });

  static const height = 80.0;
  static const gap = 1.0;

  final List<StatsDay> days;
  final double maxY;
  final BarChartRodData Function(StatsDay day, double width) rod;
  final String Function(StatsDay day) tooltip;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final direction = Directionality.of(context);
    return SizedBox(
      height: height,
      child: LayoutBuilder(
        builder: (context, size) {
          final width = max(
            1.0,
            (size.maxWidth - (days.length - 1) * gap) / max(1, days.length),
          );
          return BarChart(
            duration: Duration.zero,
            BarChartData(
              alignment: BarChartAlignment.spaceBetween,
              minY: 0,
              maxY: maxY,
              titlesData: const FlTitlesData(show: false),
              gridData: const FlGridData(show: false),
              borderData: FlBorderData(
                show: true,
                border: Border(
                  bottom: BorderSide(color: colors.outlineVariant),
                ),
              ),
              barTouchData: BarTouchData(
                // The whole height of a day is its target, also for a day
                // with no bar.
                allowTouchBarBackDraw: true,
                touchTooltipData: BarTouchTooltipData(
                  fitInsideHorizontally: true,
                  fitInsideVertically: true,
                  maxContentWidth: 240,
                  getTooltipColor: (_) => colors.inverseSurface,
                  getTooltipItem: (group, index, rod, rodIndex) =>
                      BarTooltipItem(
                        tooltip(days[index]),
                        TextStyle(
                          color: colors.onInverseSurface,
                          fontSize: 12.8,
                        ),
                        textDirection: direction,
                      ),
                ),
              ),
              barGroups: [
                for (final (index, day) in days.indexed)
                  BarChartGroupData(
                    x: index,
                    barRods: [
                      rod(day, width).copyWith(
                        backDrawRodData: BackgroundBarChartRodData(
                          show: true,
                          toY: maxY,
                          color: Colors.transparent,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}
