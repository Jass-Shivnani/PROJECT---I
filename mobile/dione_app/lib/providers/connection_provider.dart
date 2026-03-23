import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter/foundation.dart';
import '../config/server_config.dart';

/// Manages the WebSocket connection to the Dione server.
class ConnectionProvider extends ChangeNotifier {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  String _serverUrl = ServerConfig.baseUrl;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();

  bool get isConnected => _isConnected;
  String get serverUrl => _serverUrl;
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;

  /// Update server URL (e.g., from settings)
  void setServerUrl(String url) {
    _serverUrl = url;
    notifyListeners();
  }

  /// Connect to the Dione server via WebSocket
  Future<void> connect() async {
    if (_isConnected) return;

    try {
      final wsUrl = _serverUrl
          .replaceFirst('http://', 'ws://')
          .replaceFirst('https://', 'wss://');

      _channel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/api/chat/ws'),
      );

      _channel!.stream.listen(
        (data) {
          try {
            final message = jsonDecode(data as String) as Map<String, dynamic>;
            _messageController.add(message);
          } catch (e) {
            debugPrint('Failed to parse WS message: $e');
          }
        },
        onDone: () {
          _isConnected = false;
          notifyListeners();
          // Auto-reconnect after 3 seconds
          Future.delayed(const Duration(seconds: 3), () => connect());
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _isConnected = false;
          notifyListeners();
        },
      );

      _isConnected = true;
      notifyListeners();

      // Send a ping to confirm connection
      sendRaw({'type': 'ping'});
    } catch (e) {
      debugPrint('Failed to connect: $e');
      _isConnected = false;
      notifyListeners();
    }
  }

  /// Disconnect from the server
  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
    notifyListeners();
  }

  /// Send a raw JSON message
  void sendRaw(Map<String, dynamic> data) {
    if (_isConnected && _channel != null) {
      _channel!.sink.add(jsonEncode(data));
    }
  }

  /// Send a chat message
  void sendMessage(String content) {
    sendRaw({
      'type': 'message',
      'content': content,
    });
  }

  /// Send a confirmation response
  void sendConfirmation(bool confirmed) {
    sendRaw({
      'type': confirmed ? 'confirm' : 'deny',
    });
  }

  @override
  void dispose() {
    disconnect();
    _messageController.close();
    super.dispose();
  }
}
