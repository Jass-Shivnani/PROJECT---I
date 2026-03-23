import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import '../config/server_config.dart';
import '../models/chat_message.dart';
import '../models/alive_state.dart';
import 'connection_provider.dart';
import 'alive_provider.dart';
import 'theme_provider.dart';

/// Manages chat state: messages, streaming, tools, mood, UI directives.
class ChatProvider extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  ConnectionProvider? _connection;
  AliveStateProvider? _aliveProvider;
  ThemeProvider? _themeProvider;
  StreamSubscription? _subscription;
  bool _isTyping = false;
  String _streamBuffer = '';
  String? _currentStreamId;
  MoodState? _lastMood;
  List<UIComponent> _pendingComponents = [];

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isTyping => _isTyping;
  MoodState? get lastMood => _lastMood;
  List<UIComponent> get pendingComponents => _pendingComponents;

  void setConnection(ConnectionProvider connection) {
    _subscription?.cancel();
    _connection = connection;
    _subscription = connection.messageStream.listen(_handleServerEvent);
  }

  /// Wire up auxiliary providers for cross-provider updates
  void setProviders({
    AliveStateProvider? aliveProvider,
    ThemeProvider? themeProvider,
  }) {
    _aliveProvider = aliveProvider;
    _themeProvider = themeProvider;
  }

  /// Send a user message to Dione via REST (with full response including UI directives)
  Future<void> sendMessageRest(String content) async {
    if (content.trim().isEmpty) return;

    final userMsg = ChatMessage(
      id: const Uuid().v4(),
      role: 'user',
      content: content.trim(),
      timestamp: DateTime.now(),
    );
    _messages.add(userMsg);
    _isTyping = true;
    notifyListeners();

    try {
      final response = await http.post(
        Uri.parse(ServerConfig.chatUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': content.trim()}),
      ).timeout(const Duration(seconds: 120));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _processRestResponse(data);
      } else {
        _addAssistantMessage('[Error: Server returned ${response.statusCode}]');
      }
    } catch (e) {
      _addAssistantMessage('[Error: $e]');
    }

    _isTyping = false;
    notifyListeners();
  }

  /// Process REST response including UI directives and mood
  void _processRestResponse(Map<String, dynamic> data) {
    final responseText = data['response'] ?? '';
    final toolsUsed = List<String>.from(data['tools_used'] ?? []);

    // Parse mood
    MoodState? mood;
    if (data['mood'] != null) {
      mood = MoodState.fromJson(data['mood']);
      _lastMood = mood;
      _aliveProvider?.updateMoodFromResponse(data['mood']);
      _themeProvider?.updateMood(mood);
    }

    // Parse UI components
    List<UIComponent> components = [];
    if (data['ui'] != null) {
      final ui = data['ui'] as Map<String, dynamic>;
      if (ui['components'] != null) {
        components = (ui['components'] as List)
            .map((c) => UIComponent.fromJson(c))
            .toList();
      }
      // Apply theme directive if present
      if (ui['theme'] != null && _themeProvider != null) {
        _themeProvider!.applyDirective(ThemeDirective.fromJson(ui['theme']));
      }
    }

    _pendingComponents = components;

    final assistantMsg = ChatMessage(
      id: const Uuid().v4(),
      role: 'assistant',
      content: responseText,
      timestamp: DateTime.now(),
      toolsUsed: toolsUsed,
      uiComponents: components,
      mood: mood,
    );
    _messages.add(assistantMsg);
  }

  /// Send a user message via WebSocket (streaming)
  void sendMessage(String content) {
    if (content.trim().isEmpty) return;

    final userMsg = ChatMessage(
      id: const Uuid().v4(),
      role: 'user',
      content: content.trim(),
      timestamp: DateTime.now(),
    );
    _messages.add(userMsg);

    _isTyping = true;
    _streamBuffer = '';
    _currentStreamId = const Uuid().v4();

    _messages.add(ChatMessage(
      id: _currentStreamId!,
      role: 'assistant',
      content: '',
      timestamp: DateTime.now(),
      isStreaming: true,
    ));

    notifyListeners();
    _connection?.sendMessage(content);
  }

  void _addAssistantMessage(String content) {
    _messages.add(ChatMessage(
      id: const Uuid().v4(),
      role: 'assistant',
      content: content,
      timestamp: DateTime.now(),
    ));
  }

  /// Handle incoming events from the WebSocket
  void _handleServerEvent(Map<String, dynamic> event) {
    final type = event['type'] as String?;

    switch (type) {
      case 'token':
        _streamBuffer += event['content'] as String? ?? '';
        _updateStreamingMessage();
        break;

      case 'tool_call':
        final tool = event['tool'] as String? ?? 'unknown';
        debugPrint('Tool call: $tool');
        break;

      case 'tool_result':
        final tool = event['tool'] as String? ?? 'unknown';
        debugPrint('Tool result from: $tool');
        break;

      case 'sentiment':
        debugPrint('Sentiment: ${event['data']}');
        break;

      case 'mood':
        // Real-time mood update from server
        if (event['data'] != null) {
          final mood = MoodState.fromJson(event['data']);
          _lastMood = mood;
          _aliveProvider?.updateMoodFromResponse(event['data']);
          _themeProvider?.updateMood(mood);
          notifyListeners();
        }
        break;

      case 'ui_directive':
        // Dynamic UI component from server
        if (event['data'] != null) {
          final component = UIComponent.fromJson(event['data']);
          _pendingComponents.add(component);
          notifyListeners();
        }
        break;

      case 'done':
        final fullResponse =
            event['full_response'] as String? ?? _streamBuffer;
        _finalizeStreamingMessage(fullResponse, event);
        break;

      case 'error':
        final errorMsg = event['message'] as String? ?? 'Unknown error';
        _finalizeStreamingMessage('[Error: $errorMsg]', null);
        break;

      case 'confirmation_needed':
        final tool = event['tool'] as String? ?? 'unknown';
        final message = event['message'] as String? ?? 'Confirm action?';
        _streamBuffer = '⚠️ **Confirmation needed**: $message\n\n'
            'Tool: `$tool`\n\n'
            'Tap to confirm or deny.';
        _updateStreamingMessage();
        break;

      case 'pong':
        debugPrint('Server pong received');
        break;
    }
  }

  void _updateStreamingMessage() {
    if (_currentStreamId == null) return;

    final idx = _messages.indexWhere((m) => m.id == _currentStreamId);
    if (idx >= 0) {
      _messages[idx] = _messages[idx].copyWith(
        content: _streamBuffer,
        isStreaming: true,
      );
      notifyListeners();
    }
  }

  void _finalizeStreamingMessage(
      String content, Map<String, dynamic>? event) {
    if (_currentStreamId == null) return;

    // Extract mood from done event
    MoodState? mood;
    List<UIComponent> components = [];
    if (event != null) {
      if (event['mood'] != null) {
        mood = MoodState.fromJson(event['mood']);
        _lastMood = mood;
        _aliveProvider?.updateMoodFromResponse(event['mood']);
        _themeProvider?.updateMood(mood);
      }
      if (event['ui_components'] != null) {
        components = (event['ui_components'] as List)
            .map((c) => UIComponent.fromJson(c))
            .toList();
      }
    }

    final idx = _messages.indexWhere((m) => m.id == _currentStreamId);
    if (idx >= 0) {
      _messages[idx] = _messages[idx].copyWith(
        content: content,
        isStreaming: false,
        mood: mood,
        uiComponents: components.isNotEmpty ? components : null,
      );
    }

    _isTyping = false;
    _streamBuffer = '';
    _currentStreamId = null;
    notifyListeners();
  }

  /// Clear all messages
  void clearMessages() {
    _messages.clear();
    _pendingComponents.clear();
    notifyListeners();
  }

  /// Clear pending UI components after they're rendered
  void clearPendingComponents() {
    _pendingComponents.clear();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
