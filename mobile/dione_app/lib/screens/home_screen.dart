import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/connection_provider.dart';
import '../providers/alive_provider.dart';
import '../providers/theme_provider.dart';
import '../widgets/mood_orb.dart';
import 'chat_screen.dart';
import 'settings_screen.dart';

/// Home screen — Dione's living landing page.
///
/// The MoodOrb replaces the static logo. The entire screen
/// reacts to Dione's emotional state: colors shift, text
/// changes, proactive suggestions appear.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Auto-connect and start heartbeat
      context.read<ConnectionProvider>().connect();
      context.read<AliveStateProvider>().startHeartbeat();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          final gradient = themeProvider.moodGradient;

          return Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  gradient[0].withOpacity(0.08),
                  theme.colorScheme.surface,
                  gradient[1].withOpacity(0.05),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: SafeArea(
              child: Column(
                children: [
                  const SizedBox(height: 48),

                  // The Mood Orb — Dione's beating heart
                  const MoodOrb(size: 140, showLabel: true),

                  const SizedBox(height: 20),

                  // Title
                  Text(
                    'DIONE',
                    style: theme.textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      letterSpacing: 8,
                    ),
                  ),
                  const SizedBox(height: 4),

                  // Dynamic subtitle based on mood
                  Consumer<AliveStateProvider>(
                    builder: (context, alive, _) {
                      return Text(
                        _getMoodSubtitle(alive),
                        style: theme.textTheme.bodyLarge?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      );
                    },
                  ),

                  const SizedBox(height: 16),

                  // Connection & alive status
                  _buildStatusRow(context),

                  const SizedBox(height: 24),

                  // Proactive suggestions from Dione
                  _buildProactiveSuggestions(context),

                  const Spacer(),

                  // Chat button
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: FilledButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const ChatScreen()),
                          );
                        },
                        icon: const Icon(Icons.chat_bubble_outline),
                        label: const Text('Start Chatting'),
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Settings button
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const SettingsScreen()),
                          );
                        },
                        icon: const Icon(Icons.settings_outlined),
                        label: const Text('Settings'),
                      ),
                    ),
                  ),

                  const SizedBox(height: 32),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatusRow(BuildContext context) {
    return Consumer2<ConnectionProvider, AliveStateProvider>(
      builder: (context, connection, alive, _) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Connection dot
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: connection.isConnected || alive.isAlive
                    ? Colors.greenAccent
                    : Colors.redAccent,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              connection.isConnected || alive.isAlive
                  ? 'Dione is alive'
                  : 'Disconnected',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: connection.isConnected || alive.isAlive
                        ? Colors.greenAccent
                        : Colors.redAccent,
                  ),
            ),
            if (alive.lastHeartbeat != null) ...[
              const SizedBox(width: 12),
              Text(
                '${alive.mood.moodEmoji} ${alive.mood.label}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withOpacity(0.5),
                    ),
              ),
            ],
          ],
        );
      },
    );
  }

  /// Display proactive suggestions from Dione's heartbeat
  Widget _buildProactiveSuggestions(BuildContext context) {
    return Consumer<AliveStateProvider>(
      builder: (context, alive, _) {
        if (alive.suggestions.isEmpty) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'DIONE SUGGESTS',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      letterSpacing: 2,
                      color: Theme.of(context)
                          .colorScheme
                          .onSurface
                          .withOpacity(0.4),
                    ),
              ),
              const SizedBox(height: 8),
              ...alive.suggestions.take(3).map((s) {
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    dense: true,
                    leading: const Icon(Icons.lightbulb_outline, size: 20),
                    title: Text(
                      s['message'] ?? s['title'] ?? '',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (_) => const ChatScreen()),
                      );
                    },
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }

  String _getMoodSubtitle(AliveStateProvider alive) {
    if (!alive.isAlive) return 'Your Personal AI';

    switch (alive.mood.label) {
      case 'enthusiastic':
        return 'Excited to help you today!';
      case 'calm':
        return 'Relaxed and ready';
      case 'cheerful':
        return 'Feeling great, let\'s go!';
      case 'focused':
        return 'Locked in and productive';
      case 'curious':
        return 'Wondering what you\'re up to';
      case 'professional':
        return 'At your service';
      case 'playful':
        return 'Let\'s have some fun!';
      default:
        return 'Your Personal AI';
    }
  }
}
