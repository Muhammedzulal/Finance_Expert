import 'local_cache.dart';

/// Ayarları (bildirim, güvenlik) cihazdaki Drift veritabanında saklar.
class SettingsStore {
  SettingsStore._();

  static Future<Map<String, bool>> read(
    String key,
    Map<String, bool> defaults,
  ) async {
    try {
      final CachedPayload? cached = await LocalCache.db.read('settings:$key');
      final dynamic data = cached?.payload;
      if (data is Map) {
        return {
          for (final MapEntry<String, bool> e in defaults.entries)
            e.key: data[e.key] is bool ? data[e.key] as bool : e.value,
        };
      }
    } catch (_) {}
    return Map<String, bool>.from(defaults);
  }

  static Future<void> write(String key, Map<String, bool> values) async {
    await LocalCache.db.put('settings:$key', values);
  }
}
