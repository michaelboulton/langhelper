import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:go_router/go_router.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // The browser tests find the widgets through the semantics tree (DART.md).
  SemanticsBinding.instance.ensureSemantics();
  runApp(LanghelperApp());
}

/// The theme colour of the manifest and of index.html.
const brand = Color(0xFF171796);

ThemeData theme(Brightness brightness) => ThemeData(
  colorScheme: ColorScheme.fromSeed(seedColor: brand, brightness: brightness),
  fontFamily: 'NotoSans',
  fontFamilyFallback: const ['NotoSansArabic', 'NotoSansHebrew'],
);

class LanghelperApp extends StatelessWidget {
  LanghelperApp({super.key});

  final GoRouter router = GoRouter(
    routes: [GoRoute(path: '/', builder: (context, state) => const HomePage())],
  );

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Sentence breakdown',
      theme: theme(Brightness.light),
      darkTheme: theme(Brightness.dark),
      routerConfig: router,
    );
  }
}

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(appBar: AppBar(title: const Text('Sentence breakdown')));
  }
}
