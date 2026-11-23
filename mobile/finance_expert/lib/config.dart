/// Uygulama ayarları.
///
/// Backend adresi derleme sırasında değiştirilebilir:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8001
///
/// Varsayılan değer Android emülatöründen bilgisayardaki
/// docker-compose backend'ine (127.0.0.1:8001) ulaşır.
class AppConfig {
  /// Uygulama varsayılan olarak gerçek backend'e bağlanır.
  /// Her zaman demo verisiyle açmak için:
  ///   flutter run --dart-define=DEMO_MODE=true
  static const bool forceDemo = bool.fromEnvironment(
    'DEMO_MODE',
    defaultValue: false,
  );

  /// Demo modu: backend'e bağlanmadan, uygulama içindeki örnek verilerle
  /// çalışır. Giriş ekranındaki "Demo hesabıyla dene" ile açılır,
  /// çıkış yapınca kapanır.
  static bool demoMode = forceDemo;

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8001',
  );
}
