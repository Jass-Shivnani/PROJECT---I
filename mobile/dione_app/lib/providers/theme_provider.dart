import 'package:flutter/material.dart';
import '../models/alive_state.dart';

/// AI-driven theme provider.
///
/// Dione controls the visual atmosphere:
/// - Colors shift based on mood
/// - Background mode changes with time of day
/// - Avatar expression reflects emotional state
/// - Animations respond to interaction patterns
class ThemeProvider extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.dark;
  ThemeDirective _directive = ThemeDirective();
  MoodState _mood = MoodState();

  ThemeMode get themeMode => _themeMode;
  bool get isDark => _themeMode == ThemeMode.dark;
  ThemeDirective get directive => _directive;
  MoodState get mood => _mood;
  String get avatarExpression => _directive.avatarExpression;
  String get accentAnimation => _directive.accentAnimation;

  /// Parse hex color string to Color
  Color get primaryColor => _hexToColor(_directive.primaryColor);
  Color get secondaryColor => _hexToColor(_directive.secondaryColor);

  void toggleTheme() {
    _themeMode =
        _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    notifyListeners();
  }

  void setTheme(ThemeMode mode) {
    _themeMode = mode;
    notifyListeners();
  }

  /// Called when the server sends new UI directives.
  /// The AI decides how the app looks.
  void applyDirective(ThemeDirective directive) {
    _directive = directive;

    // Background mode → theme mode
    if (directive.backgroundMode == 'dark') {
      _themeMode = ThemeMode.dark;
    } else if (directive.backgroundMode == 'warm' ||
        directive.backgroundMode == 'default') {
      // Keep user preference unless explicitly overridden
    }

    notifyListeners();
  }

  /// Update mood state (affects UI animations, colors)
  void updateMood(MoodState mood) {
    _mood = mood;
    notifyListeners();
  }

  /// Mood-aware gradient colors for backgrounds and accents
  List<Color> get moodGradient {
    switch (_mood.label) {
      case 'enthusiastic':
        return [const Color(0xFF6C5CE7), const Color(0xFFFF6B6B)];
      case 'calm':
        return [const Color(0xFF2d3436), const Color(0xFF636e72)];
      case 'cheerful':
        return [const Color(0xFF6C5CE7), const Color(0xFFFFC312)];
      case 'focused':
        return [const Color(0xFF0984e3), const Color(0xFF6C5CE7)];
      case 'curious':
        return [const Color(0xFF6C5CE7), const Color(0xFF00cec9)];
      case 'professional':
        return [const Color(0xFF2d3436), const Color(0xFF0984e3)];
      case 'playful':
        return [const Color(0xFFe84393), const Color(0xFF6C5CE7)];
      default:
        return [const Color(0xFF6C5CE7), const Color(0xFFa29bfe)];
    }
  }

  /// Avatar glow intensity based on energy
  double get avatarGlowIntensity => _mood.energy * 30 + 10;

  Color _hexToColor(String hex) {
    hex = hex.replaceAll('#', '');
    if (hex.length == 6) hex = 'FF$hex';
    return Color(int.parse(hex, radix: 16));
  }
}
