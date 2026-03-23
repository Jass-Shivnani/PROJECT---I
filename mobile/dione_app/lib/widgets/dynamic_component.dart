import 'package:flutter/material.dart';
import '../models/alive_state.dart';

/// Renders dynamic UI components that the AI generates.
///
/// Dione decides what the user sees — suggestion cards,
/// system stats, action panels, etc. This widget takes
/// a UIComponent and renders it appropriately.
class DynamicComponentRenderer extends StatelessWidget {
  final UIComponent component;
  final VoidCallback? onAction;

  const DynamicComponentRenderer({
    super.key,
    required this.component,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    switch (component.type) {
      case 'suggestion_card':
      case 'habit_card':
        return _buildSuggestionCard(context);
      case 'action_panel':
        return _buildActionPanel(context);
      case 'system_stats':
        return _buildSystemStats(context);
      case 'mood_indicator':
        return _buildMoodIndicator(context);
      case 'notification':
        return _buildNotification(context);
      case 'code_block':
        return _buildCodeBlock(context);
      case 'reminder':
        return _buildReminder(context);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildSuggestionCard(BuildContext context) {
    final theme = Theme.of(context);
    final title = component.data['title'] ?? '';
    final body = component.data['body'] ?? '';
    final glow = component.style['glow'] == true;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primaryContainer.withOpacity(0.8),
            theme.colorScheme.secondaryContainer.withOpacity(0.6),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: glow
            ? [
                BoxShadow(
                  color: theme.colorScheme.primary.withOpacity(0.3),
                  blurRadius: 20,
                  spreadRadius: 2,
                ),
              ]
            : null,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(body, style: theme.textTheme.bodyMedium),
            if (component.actions.isNotEmpty) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: component.actions.map((action) {
                  return Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: action.style == 'primary'
                        ? FilledButton(
                            onPressed: onAction,
                            child: Text(action.label),
                          )
                        : OutlinedButton(
                            onPressed: onAction,
                            child: Text(action.label),
                          ),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionPanel(BuildContext context) {
    final theme = Theme.of(context);
    final title = component.data['title'] ?? 'Quick Actions';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                title,
                style: theme.textTheme.labelMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.6),
                  letterSpacing: 1,
                ),
              ),
            ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: component.actions.map((action) {
              return ActionChip(
                label: Text(action.label),
                onPressed: onAction,
                avatar: _getActionIcon(action.actionType),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSystemStats(BuildContext context) {
    final theme = Theme.of(context);
    final data = component.data;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: theme.colorScheme.surfaceContainerHighest,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.monitor_heart,
                  size: 18, color: theme.colorScheme.primary),
              const SizedBox(width: 8),
              Text('System', style: theme.textTheme.labelLarge),
            ],
          ),
          const SizedBox(height: 12),
          if (data['cpu_usage'] != null)
            _buildStatBar(context, 'CPU', data['cpu_usage'].toDouble()),
          if (data['ram_usage'] != null)
            _buildStatBar(context, 'RAM', data['ram_usage'].toDouble()),
          if (data['disk_usage'] != null)
            _buildStatBar(context, 'Disk', data['disk_usage'].toDouble()),
        ],
      ),
    );
  }

  Widget _buildStatBar(BuildContext context, String label, double percent) {
    final theme = Theme.of(context);
    final normalized = (percent / 100).clamp(0.0, 1.0);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 40,
            child: Text(label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                )),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: normalized,
                minHeight: 6,
                backgroundColor:
                    theme.colorScheme.surfaceContainerHigh,
                color: normalized > 0.8
                    ? Colors.redAccent
                    : normalized > 0.6
                        ? Colors.amber
                        : theme.colorScheme.primary,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text('${percent.toStringAsFixed(0)}%',
              style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }

  Widget _buildMoodIndicator(BuildContext context) {
    final mood = component.data['mood'] ?? 'balanced';
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: Theme.of(context)
            .colorScheme
            .primaryContainer
            .withOpacity(0.5),
      ),
      child: Text(
        'Mood: $mood',
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }

  Widget _buildNotification(BuildContext context) {
    final theme = Theme.of(context);
    final title = component.data['title'] ?? '';
    final body = component.data['body'] ?? '';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.primary.withOpacity(0.3),
        ),
        color: theme.colorScheme.primaryContainer.withOpacity(0.3),
      ),
      child: Row(
        children: [
          Icon(Icons.notifications_active,
              size: 20, color: theme.colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title.isNotEmpty)
                  Text(title,
                      style: theme.textTheme.labelLarge
                          ?.copyWith(fontWeight: FontWeight.bold)),
                if (body.isNotEmpty) Text(body, style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeBlock(BuildContext context) {
    final code = component.data['code'] ?? '';
    final language = component.data['language'] ?? '';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: const Color(0xFF1E1E2E),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (language.isNotEmpty)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: const BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: Color(0xFF313244)),
                ),
              ),
              child: Text(
                language,
                style: const TextStyle(
                  fontSize: 11,
                  color: Color(0xFF6C7086),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: SelectableText(
              code,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                color: Color(0xFFCDD6F4),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReminder(BuildContext context) {
    final theme = Theme.of(context);
    final title = component.data['title'] ?? '';
    final body = component.data['body'] ?? '';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: LinearGradient(
          colors: [
            Colors.amber.withOpacity(0.2),
            Colors.orange.withOpacity(0.1),
          ],
        ),
        border: Border.all(color: Colors.amber.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.schedule, color: Colors.amber),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: theme.textTheme.labelLarge
                        ?.copyWith(fontWeight: FontWeight.bold)),
                if (body.isNotEmpty)
                  Text(body, style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Icon? _getActionIcon(String actionType) {
    switch (actionType) {
      case 'execute':
        return const Icon(Icons.play_arrow, size: 16);
      case 'navigate':
        return const Icon(Icons.open_in_new, size: 16);
      case 'confirm':
        return const Icon(Icons.check, size: 16);
      case 'dismiss':
        return const Icon(Icons.close, size: 16);
      default:
        return null;
    }
  }
}
