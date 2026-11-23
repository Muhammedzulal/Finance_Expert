import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';
import '../data/local_cache.dart';
import '../models/models.dart';
import 'api_client.dart';

/// Giriş, kayıt ve oturum yönetimi.
///
/// JWT ve kullanıcı bilgisi cihazın güvenli deposunda (Android Keystore /
/// iOS Keychain) saklanır; uygulama yeniden açıldığında oturum geri yüklenir.
class AuthService {
  AuthService._();

  static final AuthService instance = AuthService._();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _tokenKey = 'access_token';
  static const String _profileKey = 'user_profile';
  static const String _demoKey = 'demo_mode';
  static const String demoEmail = 'demo@financeexpert.app';

  UserProfile? currentUser;

  bool get isLoggedIn => currentUser != null && ApiClient.instance.token != null;

  /// Kayıtlı oturum varsa geri yükler. İnternet gerektirmez; token süresi
  /// dolmuşsa ilk API isteğindeki 401 kullanıcıyı giriş ekranına götürür.
  Future<bool> restoreSession() async {
    try {
      final String? token = await _storage.read(key: _tokenKey);
      final String? profileJson = await _storage.read(key: _profileKey);
      if (token == null || profileJson == null) return false;
      AppConfig.demoMode =
          AppConfig.forceDemo || await _storage.read(key: _demoKey) == '1';
      ApiClient.instance.token = token;
      currentUser = UserProfile.fromJson(jsonDecode(profileJson));
      return true;
    } catch (_) {
      return false;
    }
  }

  /// POST /api/v1/users/login, ardından GET /api/v1/users/me
  Future<UserProfile> login(String email, String password) async {
    ApiClient.instance.token = null;
    final dynamic data = await ApiClient.instance.post(
      '/api/v1/users/login',
      {'email': email.trim().toLowerCase(), 'password': password},
    );
    final String token = (data as Map)['access_token'].toString();
    ApiClient.instance.token = token;

    final UserProfile me;
    try {
      me = UserProfile.fromJson(
        await ApiClient.instance.get('/api/v1/users/me'),
      );
    } catch (_) {
      ApiClient.instance.token = null;
      rethrow;
    }

    await _storage.write(key: _tokenKey, value: token);
    await _storage.write(key: _profileKey, value: jsonEncode(me.toJson()));
    await _storage.write(key: _demoKey, value: AppConfig.demoMode ? '1' : '0');
    currentUser = me;
    return me;
  }

  /// Backend olmadan uygulamayı denemek için örnek verilerle giriş.
  Future<UserProfile> loginDemo() async {
    AppConfig.demoMode = true;
    try {
      return await login(demoEmail, 'demo');
    } catch (_) {
      AppConfig.demoMode = AppConfig.forceDemo;
      rethrow;
    }
  }

  /// POST /api/v1/users/register — kayıt sonrası otomatik giriş yapılır.
  /// Backend her yeni kullanıcıya 100.000 TL sanal bakiye açar.
  Future<UserProfile> register(
    String fullName,
    String email,
    String password,
  ) async {
    ApiClient.instance.token = null;
    await ApiClient.instance.post('/api/v1/users/register', {
      'full_name': fullName.trim(),
      'email': email.trim().toLowerCase(),
      'password': password,
    });
    return login(email, password);
  }

  /// Token, kullanıcı bilgisi ve önbellek silinir.
  Future<void> logout() async {
    ApiClient.instance.token = null;
    currentUser = null;
    try {
      await _storage.delete(key: _tokenKey);
      await _storage.delete(key: _profileKey);
      await _storage.delete(key: _demoKey);
    } catch (_) {}
    AppConfig.demoMode = AppConfig.forceDemo;
    try {
      await LocalCache.db.clear();
    } catch (_) {}
  }
}
