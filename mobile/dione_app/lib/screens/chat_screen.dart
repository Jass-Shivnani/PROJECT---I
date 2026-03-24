import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../providers/connection_provider.dart';
import '../providers/alive_provider.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/typing_indicator.dart';
import '../widgets/mood_orb.dart';
import '../widgets/dynamic_component.dart';

/// The main chat screen — where the user talks to Dione.
///
/// Features:
/// - Mood orb in the app bar reflecting Dione's emotional state
/// - Dynamic AI-generated UI components between messages
/// - REST fallback when WebSocket isn't available
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    final connection = context.read<ConnectionProvider>();
    final chat = context.read<ChatProvider>();

    if (connection.isConnected) {
      chat.sendMessage(text);
    } else {
      // Fallback to REST
      chat.sendMessageRest(text);
    }

    _controller.clear();
    _focusNode.requestFocus();

    // Scroll to bottom
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(context),
      body: Column(
        children: [
          // Proactive suggestions bar
          _buildSuggestionsBar(context),

          // Messages list with dynamic components
          Expanded(
            child: Consumer<ChatProvider>(
              builder: (context, chat, _) {
                if (chat.messages.isEmpty) {
                  return _buildEmptyState(context);
                }

                return ListView.builder(
                  controller: _scrollController,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: _calculateItemCount(chat),
                  itemBuilder: (context, index) =>
                      _buildListItem(context, chat, index),
                );
              },
            ),
          ),

          // Input bar
          _buildInputBar(context),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    return AppBar(
      titleSpacing: 0,
      title: Row(
        children: [
          // Mini mood orb — Dione's heartbeat in the app bar
          const SizedBox(
            width: 36,
            height: 36,
            child: MoodOrb(size: 36, showLabel: false),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Dione',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              Consumer2<ConnectionProvider, AliveStateProvider>(
                builder: (context, conn, alive, _) {
                  final moodLabel = alive.mood.label;
                  final isOnline = conn.isConnected || alive.isAlive;
                  return Text(
                    isOnline ? 'Feeling $moodLabel' : 'Offline',
                    style: TextStyle(
                      fontSize: 12,
                      color: isOnline ? Colors.greenAccent : Colors.redAccent,
                    ),
                  );
                },
              ),
            ],
          ),
        ],
      ),
      actions: [
        // Mood emoji quick indicator
        Consumer<AliveStateProvider>(
          builder: (context, alive, _) {
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text(
                  alive.mood.moodEmoji,
                  style: const TextStyle(fontSize: 20),
                ),
              ),
            );
          },
        ),
        PopupMenuButton<String>(
          icon: const Icon(Icons.more_vert),
          onSelected: (value) {
            if (value == 'clear') {
              context.read<ChatProvider>().clearMessages();
            }
          },
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'clear', child: Text('Clear chat')),
          ],
        ),
      ],
    );
  }

  /// Shows proactive suggestions from Dione's heartbeat
  Widget _buildSuggestionsBar(BuildContext context) {
    return Consumer<AliveStateProvider>(
      builder: (context, alive, _) {
        if (alive.suggestions.isEmpty) return const SizedBox.shrink();

        return Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: alive.suggestions.map((s) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: ActionChip(
                  label: Text(
                    s['message'] ?? s['title'] ?? 'Suggestion',
                    style: const TextStyle(fontSize: 12),
                  ),
                  avatar: const Icon(Icons.lightbulb_outline, size: 14),
                  onPressed: () {
                    // Send suggestion as message
                    _controller.text =
                        s['message'] ?? s['title'] ?? '';
                    _sendMessage();
                  },
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }

  /// Calculate total list items (messages + interspersed dynamic components)
  int _calculateItemCount(ChatProvider chat) {
    int count = chat.messages.length;
    // Add typing indicator slot
    if (chat.isTyping) count++;
    // Add dynamic component slots for messages that have them
    for (final msg in chat.messages) {
      if (msg.uiComponents.isNotEmpty) count += msg.uiComponents.length;
    }
    return count;
  }

  /// Build individual list items — messages, components, or typing indicator
  Widget _buildListItem(BuildContext context, ChatProvider chat, int index) {
    // Build a flat list: for each message, show the bubble,
    // then any UI components attached to it
    int currentIdx = 0;
    for (int i = 0; i < chat.messages.length; i++) {
      final msg = chat.messages[i];

      if (currentIdx == index) {
        return ChatBubble(message: msg);
      }
      currentIdx++;

      // Render dynamic components attached to this message
      for (int j = 0; j < msg.uiComponents.length; j++) {
        if (currentIdx == index) {
          return Padding(
            padding: const EdgeInsets.only(left: 36),
            child: DynamicComponentRenderer(
              component: msg.uiComponents[j],
              onAction: () {
                // Handle component actions
                debugPrint(
                    'Component action: ${msg.uiComponents[j].type}');
              },
            ),
          );
        }
        currentIdx++;
      }
    }

    // Typing indicator at the end
    if (chat.isTyping && currentIdx == index) {
      return const TypingIndicator();
    }

    return const SizedBox.shrink();
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Show the mood orb as the greeting
            const MoodOrb(size: 100, showLabel: true),
            const SizedBox(height: 24),
            Text(
              'Hey! I\'m Dione.',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Your local AI assistant that remembers and acts.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.5),
                  ),
            ),
            const SizedBox(height: 32),
            // Quick action chips in a grid
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  _quickChip(context, '💡', 'What can you do?', 'What can you do?'),
                  _quickChip(context, '🌙', 'How are you?', 'How are you feeling right now?'),
                  _quickChip(context, '📂', 'List my files', 'List the files on my desktop'),
                  _quickChip(context, '🔍', 'Search the web', 'Search the web for latest AI news'),
                  _quickChip(context, '📝', 'Summarize', 'Can you help me write a summary?'),
                  _quickChip(context, '⚡', 'System info', 'Tell me about my system'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _quickChip(BuildContext context, String emoji, String label, String message) {
    return ActionChip(
      avatar: Text(emoji, style: const TextStyle(fontSize: 14)),
      label: Text(label, style: const TextStyle(fontSize: 13)),
      onPressed: () {
        _controller.text = message;
        _sendMessage();
      },
    );
  }

  Widget _buildInputBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                textCapitalization: TextCapitalization.sentences,
                maxLines: 4,
                minLines: 1,
                decoration: InputDecoration(
                  hintText: 'Message Dione...',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(24),
                    borderSide: BorderSide.none,
                  ),
                  filled: true,
                  fillColor:
                      Theme.of(context).colorScheme.surfaceContainerHighest,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                ),
                onSubmitted: (_) => _sendMessage(),
              ),
            ),
            const SizedBox(width: 8),
            Consumer<ChatProvider>(
              builder: (context, chat, _) {
                return FloatingActionButton.small(
                  onPressed: chat.isTyping ? null : _sendMessage,
                  child: chat.isTyping
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send_rounded),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
