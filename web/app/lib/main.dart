import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api/client.dart';
import 'audio_lessons/courses.dart';
import 'audio_lessons/lesson_view.dart';
import 'breakdown/breakdown_tab.dart';
import 'flashcards/flashcards_tab.dart';
import 'i18n/i18n.dart';
import 'progress/progress_tab.dart';
import 'progress/state.dart';
import 'providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The browser tests find the widgets through the semantics tree (DART.md).
  SemanticsBinding.instance.ensureSemantics();
  final api = Api();
  final i18n = await startI18n(api);
  runApp(
    ProviderScope(
      overrides: [apiProvider.overrideWithValue(api)],
      child: LanghelperApp(i18n: i18n),
    ),
  );
}

/// The theme colour of the manifest and of index.html.
const brand = Color(0xFF171796);

ThemeData theme(Brightness brightness) => ThemeData(
  colorScheme: ColorScheme.fromSeed(seedColor: brand, brightness: brightness),
  fontFamily: 'NotoSans',
  fontFamilyFallback: const ['NotoSansArabic', 'NotoSansHebrew'],
);

class LanghelperApp extends StatelessWidget {
  LanghelperApp({super.key, required this.i18n});

  final I18n i18n;

  /// One branch for each tab, so each tab keeps its state while another one
  /// shows. The address keeps the tab: /#/cards.
  final GoRouter router = GoRouter(
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomePage(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/', builder: (context, _) => const BreakdownTab()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/cards',
                builder: (context, _) => const FlashcardsTab(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/progress',
                builder: (context, _) => const ProgressTab(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/audio',
                builder: (context, _) => const CoursesView(),
                routes: [
                  GoRoute(
                    path: ':course/:lesson',
                    redirect: (context, state) =>
                        int.tryParse(state.pathParameters['lesson']!) == null
                        ? '/audio'
                        : null,
                    builder: (context, state) {
                      final course = state.pathParameters['course']!;
                      final number = int.parse(state.pathParameters['lesson']!);
                      return LessonView(
                        // A new lesson gets a new player.
                        key: ValueKey((course, number)),
                        course: course,
                        number: number,
                      );
                    },
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
    // An unknown address shows the Breakdown tab, as on the page of static/.
    onException: (context, state, router) => router.go('/'),
  );

  @override
  Widget build(BuildContext context) {
    return I18nScope(
      i18n: i18n,
      child: MaterialApp.router(
        title: 'Sentence breakdown',
        theme: theme(Brightness.light),
        darkTheme: theme(Brightness.dark),
        routerConfig: router,
        builder: (context, child) =>
            Directionality(textDirection: i18n.direction, child: child!),
      ),
    );
  }
}

/// The index of the Progress branch of the router.
const progressTab = 2;

/// The title of the tab over the tabs, and the tab under them.
class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key, required this.shell});

  final StatefulNavigationShell shell;

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage>
    with SingleTickerProviderStateMixin {
  late final _tabs = TabController(
    length: 4,
    vsync: this,
    initialIndex: widget.shell.currentIndex,
  );

  @override
  void initState() {
    super.initState();
    _opened(widget.shell.currentIndex);
  }

  @override
  void didUpdateWidget(HomePage old) {
    super.didUpdateWidget(old);
    // The Back button of the browser changes the tab too.
    _tabs.index = widget.shell.currentIndex;
    if (old.shell.currentIndex != widget.shell.currentIndex) {
      _opened(widget.shell.currentIndex);
    }
  }

  /// The Progress tab shows the numbers of now each time that it opens.
  void _opened(int tab) {
    if (tab != progressTab) return;
    // Not during the build.
    final progress = ref.read(progressProvider.notifier);
    unawaited(Future.microtask(progress.load));
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    final shell = widget.shell;
    return Scaffold(
      appBar: AppBar(
        title: switch (shell.currentIndex) {
          0 => const BreakdownTitle(),
          1 => const FlashcardsTitle(),
          progressTab => const ProgressTitle(),
          _ => const AudioTitle(),
        },
        bottom: TabBar(
          controller: _tabs,
          // Scrolls sideways on a narrow screen.
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          onTap: shell.goBranch,
          tabs: [
            Tab(text: i18n.t('tab-breakdown')),
            Tab(text: i18n.t('tab-cards')),
            Tab(text: i18n.t('tab-progress')),
            Tab(text: i18n.t('tab-audio')),
          ],
        ),
      ),
      body: shell,
    );
  }
}
