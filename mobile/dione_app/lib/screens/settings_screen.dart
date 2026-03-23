import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/connection_provider.dart';
import '../providers/theme_provider.dart';

/// Settings screen for configuring Dione connection and preferences.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _urlController.text = context.read<ConnectionProvider>().serverUrl;
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Connection section
          Text('Connection',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),

          TextField(
            controller: _urlController,
            decoration: InputDecoration(
              labelText: 'Server URL',
              hintText: 'http://192.168.1.100:8000',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              prefixIcon: const Icon(Icons.link),
            ),
          ),
          const SizedBox(height: 12),

          Consumer<ConnectionProvider>(
            builder: (context, conn, _) {
              return Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () {
                        conn.setServerUrl(_urlController.text.trim());
                        conn.disconnect();
                        conn.connect();
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Reconnect'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: conn.isConnected
                          ? Colors.green.withOpacity(0.1)
                          : Colors.red.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: conn.isConnected
                                ? Colors.green
                                : Colors.red,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(conn.isConnected
                            ? 'Connected'
                            : 'Disconnected'),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),

          const SizedBox(height: 32),

          // Appearance section
          Text('Appearance',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),

          Consumer<ThemeProvider>(
            builder: (context, theme, _) {
              return SwitchListTile(
                title: const Text('Dark Mode'),
                subtitle: const Text('Dione prefers the dark side'),
                value: theme.isDark,
                onChanged: (_) => theme.toggleTheme(),
                secondary: Icon(
                    theme.isDark ? Icons.dark_mode : Icons.light_mode),
              );
            },
          ),

          const SizedBox(height: 32),

          // About section
          Text('About', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),

          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Dione AI'),
            subtitle: Text(
                'v0.1.0 — Local Large Action Model Orchestration Engine'),
          ),
          const ListTile(
            leading: Icon(Icons.security),
            title: Text('Privacy'),
            subtitle: Text(
                'Everything runs locally on your PC. No data ever leaves your machine.'),
          ),
        ],
      ),
    );
  }
}
