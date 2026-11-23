import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

/// Önbellekten okunan bir API yanıtı.
class CachedPayload {
  final dynamic payload;
  final DateTime updatedAt;

  const CachedPayload(this.payload, this.updatedAt);
}

/// Offline-first önbellek: her başarılı API yanıtı Drift (SQLite) tablosuna
/// yazılır, internet yokken ekranlar buradan beslenir.
///
/// Tek bir anahtar-değer tablosu kullandığımız için kod üretimi
/// (build_runner) gerekmez; tablo SQL ile oluşturulur.
class CacheDatabase extends GeneratedDatabase {
  CacheDatabase() : super(driftDatabase(name: 'finance_expert_cache'));

  @override
  Iterable<TableInfo<Table, Object?>> get allTables => const [];

  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => const [];

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (Migrator m) async {
      await customStatement('''
        CREATE TABLE IF NOT EXISTS api_cache (
          cache_key TEXT NOT NULL PRIMARY KEY,
          payload TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        )
      ''');
    },
  );

  Future<void> put(String key, Object? data) {
    return customStatement(
      'INSERT OR REPLACE INTO api_cache (cache_key, payload, updated_at) '
      'VALUES (?, ?, ?)',
      [key, jsonEncode(data), DateTime.now().millisecondsSinceEpoch],
    );
  }

  Future<CachedPayload?> read(String key) async {
    final QueryRow? row = await customSelect(
      'SELECT payload, updated_at FROM api_cache WHERE cache_key = ?',
      variables: [Variable.withString(key)],
    ).getSingleOrNull();
    if (row == null) return null;
    return CachedPayload(
      jsonDecode(row.read<String>('payload')),
      DateTime.fromMillisecondsSinceEpoch(row.read<int>('updated_at')),
    );
  }

  Future<void> clear() => customStatement('DELETE FROM api_cache');
}

/// Uygulama boyunca tek veritabanı bağlantısı.
class LocalCache {
  LocalCache._();

  static final CacheDatabase db = CacheDatabase();
}
