import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/server_config.dart';
import '../models/alive_state.dart';

/// Polls Dione's heartbeat endpoint to keep the app
/// in sync with the AI's mood, personality, and proactive state.
///
/// This is the "pulse" — the continuous connection that makes
/// Dione feel alive even when the user isn't chatting.
class AliveStateProvider extends ChangeNotifier {
  AliveState? _aliveState;
  MoodState _mood = MoodState();
  Timer? _heartbeatTimer;
  bool _isAlive = false;
  List<Map<String, dynamic>> _suggestions = [];
  DateTime? _lastHeartbeat;

  AliveState? get aliveState => _aliveState;
  MoodState get mood => _mood;
  bool get isAlive => _isAlive;
  List<Map<String, dynamic>> get suggestions => _suggestions;
  DateTime? get lastHeartbeat => _lastHeartbeat;

  /// Start polling the alive endpoint
  void startHeartbeat({Duration interval = const Duration(seconds: 10)}) {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(interval, (_) => _fetchAliveState());
    // Immediate first fetch
    _fetchAliveState();
  }

  /// Stop polling
  void stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Manually update mood from a chat response
  void updateMoodFromResponse(Map<String, dynamic>? moodJson) {
    if (moodJson == null) return;
    _mood = MoodState.fromJson(moodJson);
    _lastHeartbeat = DateTime.now();
    notifyListeners();
  }

  /// Fetch the alive state from the server
  Future<void> _fetchAliveState() async {
    try {
      final response = await http
          .get(Uri.parse(ServerConfig.aliveUrl))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _aliveState = AliveState.fromJson(data);
        _isAlive = true;
        _lastHeartbeat = DateTime.now();

        // Update mood
        if (data['mood'] != null) {
          _mood = MoodState.fromJson(data['mood']);
        }

        // Get greeting as a suggestion if present
        if (data['greeting'] != null) {
          final greeting = data['greeting'] as Map<String, dynamic>;
          if (greeting['message'] != null) {
            _suggestions = [
              {'title': 'Greeting', 'message': greeting['message']}
            ];
          }
        }

        notifyListeners();
      }
    } catch (e) {
      debugPrint('Heartbeat fetch failed: $e');
      _isAlive = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    stopHeartbeat();
    super.dispose();
  }
}
