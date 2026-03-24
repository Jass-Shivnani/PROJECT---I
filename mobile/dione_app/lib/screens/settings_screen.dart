import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import '../providers/connection_provider.dart';
import '../providers/theme_provider.dart';
import '../config/server_config.dart';

/// Enhanced settings screen with server status, diagnostics, and rich controls.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();
  Map<String, dynamic> _serverInfo = {};
  Map<String, dynamic> _personality = {};
  bool _loadingInfo = false;
  String? _connectionError;

  @override
  void initState() {
    super.initState();
    _urlController.text = context.read<ConnectionProvider>().serverUrl;
    _fetchServerInfo();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _fetchServerInfo() async {
    setState(() {
      _loadingInfo = true;
      _connectionError = null;
    });

    try {
      final url = _urlController.text.trim();
      final infoRes = await http
          .get(Uri.parse('$url/api/status/info'))
          .timeout(const Duration(seconds: 5));

      if (infoRes.statusCode == 200) {
        _serverInfo = jsonDecode(infoRes.body);
      }

      try {
        final personalityRes = await http
            .get(Uri.parse('$url/api/status/personality'))
            .timeout(const Duration(seconds: 5));
        if (personalityRes.statusCode == 200) {
          _personality = jsonDecode(personalityRes.body);
        }
      } catch (_) {}

      _connectionError = null;
    } catch (e) {
      _connectionError = e.toString();
    } finally {
      if (mounted) setState(() => _loadingInfo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchServerInfo,
            tooltip: 'Refresh status',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Connection Section ──
          _buildSectionHeader(context, Icons.link, 'Connection'),
          const SizedBox(height: 12),
          _buildConnectionCard(context),

          const SizedBox(height: 24),

          // ── Server Info Section ──
          _buildSectionHeader(context, Icons.dns_outlined, 'Server'),
          const SizedBox(height: 12),
          _buildServerInfoCard(context),

          const SizedBox(height: 24),

          // ── Personality Section ──
          _buildSectionHeader(context, Icons.psychology_outlined, 'Personality'),
          const SizedBox(height: 12),
          _buildPersonalityCard(context),

          const SizedBox(height: 24),

          // ── Appearance Section ──
          _buildSectionHeader(context, Icons.palette_outlined, 'Appearance'),
          const SizedBox(height: 12),
          _buildAppearanceCard(context),

          const SizedBox(height: 24),

          // ── Diagnostics Section ──
          _buildSectionHeader(context, Icons.bug_report_outlined, 'Diagnostics'),
          const SizedBox(height: 12),
          _buildDiagnosticsCard(context),

          const SizedBox(height: 24),

          // ── About Section ──
          _buildSectionHeader(context, Icons.info_outline, 'About'),
          const SizedBox(height: 12),
          _buildAboutCard(context),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, IconData icon, String title) {
    return Row(
      children: [
        Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text(title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                )),
      ],
    );
  }

  Widget _buildConnectionCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _urlController,
              decoration: InputDecoration(
                labelText: 'Server URL',
                hintText: 'http://192.168.1.100:8900',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                prefixIcon: const Icon(Icons.link),
                helperText: 'Your PC\'s IP and Dione port',
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
                          _fetchServerInfo();
                        },
                        icon: const Icon(Icons.power_settings_new),
                        label: Text(conn.isConnected ? 'Reconnect' : 'Connect'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    _buildStatusChip(conn.isConnected),
                  ],
                );
              },
            ),
            if (_connectionError != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: Colors.redAccent, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Cannot reach server. Is Dione running?',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.redAccent.shade100,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusChip(bool connected) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: (connected ? Colors.green : Colors.red).withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: (connected ? Colors.green : Colors.red).withOpacity(0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: connected ? Colors.greenAccent : Colors.redAccent,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            connected ? 'Online' : 'Offline',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: connected ? Colors.greenAccent : Colors.redAccent,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServerInfoCard(BuildContext context) {
    if (_loadingInfo) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    if (_serverInfo.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Connect to server to see info',
            style: TextStyle(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5)),
          ),
        ),
      );
    }

    final llm = _serverInfo['llm'] ?? {};
    final server = _serverInfo['server'] ?? {};

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _infoRow('Version', _serverInfo['version'] ?? '?'),
            _infoRow('Backend', '${llm['backend'] ?? '?'}'),
            _infoRow('Model', '${llm['model'] ?? '?'}'),
            _infoRow('Uptime', '${server['uptime_seconds'] ?? 0}s'),
            _infoRow('Messages', '${_serverInfo['total_messages'] ?? 0}'),
          ],
        ),
      ),
    );
  }

  Widget _buildPersonalityCard(BuildContext context) {
    if (_personality.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Connect to view personality state',
            style: TextStyle(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5)),
          ),
        ),
      );
    }

    final mood = _personality['mood'] ?? {};
    final style = _personality['style'] ?? 'adaptive';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _infoRow('Mood', '${mood['label'] ?? 'balanced'}'),
            _infoRow('Energy', '${((mood['energy'] ?? 0.5) * 100).toInt()}%'),
            _infoRow('Warmth', '${((mood['warmth'] ?? 0.5) * 100).toInt()}%'),
            _infoRow('Curiosity', '${((mood['curiosity'] ?? 0.5) * 100).toInt()}%'),
            _infoRow('Style', style.toString()),
          ],
        ),
      ),
    );
  }

  Widget _buildAppearanceCard(BuildContext context) {
    return Card(
      child: Consumer<ThemeProvider>(
        builder: (context, theme, _) {
          return Column(
            children: [
              SwitchListTile(
                title: const Text('Dark Mode'),
                subtitle: const Text('The dark side is more comfortable'),
                value: theme.isDark,
                onChanged: (_) => theme.toggleTheme(),
                secondary: Icon(theme.isDark ? Icons.dark_mode : Icons.light_mode),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.color_lens_outlined),
                title: const Text('Accent Color'),
                subtitle: const Text('Adapts to Dione\'s mood automatically'),
                trailing: Container(
                  width: 24, height: 24,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: theme.primaryColor,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildDiagnosticsCard(BuildContext context) {
    return Card(
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.speed),
            title: const Text('Ping Server'),
            subtitle: const Text('Test connection latency'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              final start = DateTime.now();
              try {
                await http
                    .get(Uri.parse('${_urlController.text.trim()}/api/status/health'))
                    .timeout(const Duration(seconds: 5));
                final ms = DateTime.now().difference(start).inMilliseconds;
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('✅ Ping: ${ms}ms')),
                  );
                }
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('❌ Server unreachable')),
                  );
                }
              }
            },
          ),
          const Divider(height: 1),
          ListTile(
            leading: const Icon(Icons.delete_sweep_outlined),
            title: const Text('Clear Local Chat History'),
            subtitle: const Text('Messages on this device only'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Clear chat?'),
                  content: const Text('This only clears messages on this device. Server memory is not affected.'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Cancel'),
                    ),
                    FilledButton(
                      onPressed: () {
                        // Clear via provider
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Chat cleared')),
                        );
                      },
                      child: const Text('Clear'),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildAboutCard(BuildContext context) {
    return Card(
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('Dione AI'),
            subtitle: Text(
              'v0.2.0 — Local Large Action Model Engine\n'
              'Capstone Project',
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
            isThreeLine: true,
          ),
          const Divider(height: 1),
          const ListTile(
            leading: Icon(Icons.security),
            title: Text('Privacy'),
            subtitle: Text('Everything runs locally. Your data never leaves your machine.'),
          ),
          const Divider(height: 1),
          const ListTile(
            leading: Icon(Icons.code),
            title: Text('Architecture'),
            subtitle: Text(
              'ReAct Engine · Knowledge Graph · Adaptive Personality\n'
              'Plugin System · Proactive Heartbeat',
            ),
            isThreeLine: true,
          ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(
            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
          )),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
