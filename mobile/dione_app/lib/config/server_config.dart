/// Dione AI — Server Configuration
///
/// Central place for server connection settings.

class ServerConfig {
  /// The base URL of the Dione server (your PC).
  /// Using localhost via ADB reverse port forwarding (adb reverse tcp:8900 tcp:8900).
  /// For wireless: change to your PC's local IP address.
  static const String baseUrl = 'http://127.0.0.1:8900';

  /// WebSocket URL for real-time chat
  static String get wsUrl => baseUrl
      .replaceFirst('http://', 'ws://')
      .replaceFirst('https://', 'wss://');

  /// --- Core API Endpoints ---
  static String get chatUrl => '$baseUrl/api/chat';
  static String get chatWsUrl => '$wsUrl/api/chat/ws';
  static String get chatResetUrl => '$baseUrl/api/chat/reset';
  static String get historyUrl => '$baseUrl/api/chat/history';

  /// --- Status & Alive Endpoints ---
  static String get healthUrl => '$baseUrl/api/status/health';
  static String get aliveUrl => '$baseUrl/api/status/alive';
  static String get infoUrl => '$baseUrl/api/status/info';
  static String get modelsUrl => '$baseUrl/api/status/models';

  /// --- Personality & Profile ---
  static String get personalityUrl => '$baseUrl/api/status/personality';
  static String get userProfileUrl => '$baseUrl/api/status/user-profile';
  static String get heartbeatUrl => '$baseUrl/api/status/heartbeat';

  /// --- Plugins & Knowledge ---
  static String get knowledgeUrl => '$baseUrl/api/knowledge';
  static String get pluginsUrl => '$baseUrl/api/plugins';
}
