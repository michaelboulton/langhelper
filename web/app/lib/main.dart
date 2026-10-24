import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'api/client.dart';
import 'breakdown/breakdown_tab.dart';
import 'flashcards/flashcards_tab.dart';
import 'i18n/i18n.dart';
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

/// The title of the tab over the tabs, and the tab under them.
class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.shell});

  final StatefulNavigationShell shell;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage>
    with SingleTickerProviderStateMixin {
  late final _tabs = TabController(
    length: 2,
    vsync: this,
    initialIndex: widget.shell.currentIndex,
  );

  @override
  void didUpdateWidget(HomePage old) {
    super.didUpdateWidget(old);
    // The Back button of the browser changes the tab too.
    _tabs.index = widget.shell.currentIndex;
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
        title: shell.currentIndex == 0
            ? const BreakdownTitle()
            : const FlashcardsTitle(),
        bottom: TabBar(
          controller: _tabs,
          // Scrolls sideways on a narrow screen.
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          onTap: shell.goBranch,
          tabs: [
            Tab(text: i18n.t('tab-breakdown')),
            Tab(text: i18n.t('tab-cards')),
          ],
        ),
      ),
      body: shell,
    );
  }
}
