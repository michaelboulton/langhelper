import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:go_router/go_router.dart';

import 'api/client.dart';
import 'i18n/i18n.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The browser tests find the widgets through the semantics tree (DART.md).
  SemanticsBinding.instance.ensureSemantics();
  runApp(LanghelperApp(i18n: await startI18n(Api())));
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

  final GoRouter router = GoRouter(
    routes: [GoRoute(path: '/', builder: (context, state) => const HomePage())],
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

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final i18n = I18n.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(
          i18n.t('breakdown-title', {'language': i18n.t('language-name-hr')}),
        ),
      ),
    );
  }
}
