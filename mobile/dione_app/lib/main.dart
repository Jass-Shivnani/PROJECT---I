import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';

import 'providers/chat_provider.dart';
import 'providers/connection_provider.dart';
import 'providers/theme_provider.dart';
import 'providers/alive_provider.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const DioneApp());
}

class DioneApp extends StatelessWidget {
  const DioneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => ConnectionProvider()),
        ChangeNotifierProvider(create: (_) => AliveStateProvider()),
        ChangeNotifierProxyProvider3<ConnectionProvider, AliveStateProvider,
            ThemeProvider, ChatProvider>(
          create: (_) => ChatProvider(),
          update: (_, connection, alive, theme, chat) {
            chat?.setConnection(connection);
            chat?.setProviders(aliveProvider: alive, themeProvider: theme);
            return chat!;
          },
        ),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp(
            title: 'Dione AI',
            debugShowCheckedModeBanner: false,
            theme: _buildLightTheme(themeProvider),
            darkTheme: _buildDarkTheme(themeProvider),
            themeMode: themeProvider.themeMode,
            home: const HomeScreen(),
          );
        },
      ),
    );
  }

  ThemeData _buildLightTheme(ThemeProvider tp) {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorSchemeSeed: tp.primaryColor,
      textTheme: GoogleFonts.interTextTheme(),
    );
  }

  ThemeData _buildDarkTheme(ThemeProvider tp) {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorSchemeSeed: tp.primaryColor,
      scaffoldBackgroundColor: const Color(0xFF0D0D1A),
      textTheme: GoogleFonts.interTextTheme(
        ThemeData.dark().textTheme,
      ),
    );
  }
}
