import 'package:uuid/uuid.dart';

import '../models/models.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import 'local_cache.dart';

/// Ekranın gösterdiği veri ve nereden geldiği.
class Loaded<T> {
  final T data;

  /// true: internet yoktu, veri Drift önbelleğinden geldi.
  final bool fromCache;
  final DateTime? cachedAt;

  const Loaded(this.data, {this.fromCache = false, this.cachedAt});
}

/// Ekranların kullandığı tek veri kaynağı.
///
/// Önce API denenir; başarılı yanıt önbelleğe yazılır. Sunucuya
/// ulaşılamazsa son kaydedilen yanıt gösterilir (offline-first).
class FinanceRepository {
  FinanceRepository._();

  static final FinanceRepository instance = FinanceRepository._();

  final ApiClient _api = ApiClient.instance;
  CacheDatabase get _cache => LocalCache.db;

  Future<Loaded<T>> _load<T>(
    String cacheKey,
    Future<dynamic> Function() fetch,
    T Function(dynamic json) parse,
  ) async {
    try {
      final dynamic json = await fetch();
      try {
        await _cache.put(cacheKey, json);
      } catch (_) {
        // Önbellek hatası ekranı bozmasın.
      }
      return Loaded(parse(json));
    } on ApiException catch (e) {
      if (!e.canUseCache) rethrow;
      CachedPayload? cached;
      try {
        cached = await _cache.read(cacheKey);
      } catch (_) {
        cached = null;
      }
      if (cached == null) rethrow;
      return Loaded(
        parse(cached.payload),
        fromCache: true,
        cachedAt: cached.updatedAt,
      );
    }
  }

  String get _walletId {
    final String? id = AuthService.instance.currentUser?.walletId;
    if (id == null) {
      throw ApiException('Bu hesaba bağlı bir cüzdan bulunamadı.');
    }
    return id;
  }

  // ---------------- Piyasa ----------------

  /// GET /api/v1/stocks
  Future<Loaded<List<Stock>>> stocks() => _load(
    'stocks',
    () => _api.get('/api/v1/stocks'),
    (json) => ((json as Map)['stocks'] as List).map(Stock.fromJson).toList(),
  );

  /// GET /api/v1/stocks/{symbol}/quote — fiyat yoksa data null döner.
  Future<Loaded<Quote?>> quote(String symbol) async {
    try {
      return await _load<Quote?>(
        'quote:$symbol',
        () => _api.get('/api/v1/stocks/$symbol/quote'),
        Quote.fromJson,
      );
    } on ApiException catch (e) {
      if (e.statusCode == 404) return const Loaded<Quote?>(null);
      rethrow;
    }
  }

  /// Birden çok hissenin son fiyatı (paralel istek).
  Future<Map<String, Quote?>> quotes(Iterable<String> symbols) async {
    final List<String> list = symbols.toList();
    final List<Quote?> results = await Future.wait(
      list.map((s) async {
        try {
          return (await quote(s)).data;
        } catch (_) {
          return null;
        }
      }),
    );
    return {for (int i = 0; i < list.length; i++) list[i]: results[i]};
  }

  /// GET /api/v1/stocks/{symbol}/history
  Future<Loaded<PriceHistory>> history(String symbol, {int limit = 100}) =>
      _load(
        'history:$symbol:$limit',
        () => _api.get(
          '/api/v1/stocks/$symbol/history',
          query: {'limit': limit},
        ),
        PriceHistory.fromJson,
      );

  // ---------------- Haber ve AI analizi ----------------

  /// GET /api/v1/news?symbol=...&limit=...
  Future<Loaded<List<NewsItem>>> news({String? symbol, int limit = 10}) =>
      _load(
        'news:${symbol ?? 'all'}:$limit',
        () => _api.get(
          '/api/v1/news',
          query: {'limit': limit, 'symbol': ?symbol},
        ),
        (json) =>
            ((json as Map)['items'] as List).map(NewsItem.fromJson).toList(),
      );

  /// GET /api/v1/news/{id}/analysis — analiz yoksa null döner.
  Future<NewsAnalysis?> analysis(String newsId) async {
    try {
      final Loaded<NewsAnalysis> loaded = await _load(
        'analysis:$newsId',
        () => _api.get(
          '/api/v1/news/${Uri.encodeComponent(newsId)}/analysis',
        ),
        NewsAnalysis.fromJson,
      );
      return loaded.data;
    } catch (_) {
      return null;
    }
  }

  // ---------------- Cüzdan ----------------

  /// GET /api/v1/wallets/{id}/valuation — nakit, pozisyonlar, kâr/zarar
  Future<Loaded<Valuation>> valuation() {
    final String walletId = _walletId;
    return _load(
      'valuation:$walletId',
      () => _api.get('/api/v1/wallets/$walletId/valuation'),
      Valuation.fromJson,
    );
  }

  /// GET /api/v1/wallets/{id}/trades
  Future<Loaded<List<Trade>>> trades({int limit = 20}) {
    final String walletId = _walletId;
    return _load(
      'trades:$walletId:$limit',
      () => _api.get(
        '/api/v1/wallets/$walletId/trades',
        query: {'limit': limit},
      ),
      (json) => ((json as Map)['items'] as List).map(Trade.fromJson).toList(),
    );
  }

  /// Sanal cüzdana bakiye ekler ve yeni nakit bakiyesini döndürür.
  /// Şimdilik yalnızca demo modunda çalışır; backend'de bu uç nokta yok.
  Future<double> deposit(double amount) async {
    try {
      final dynamic json = await _api.post(
        '/api/v1/wallets/$_walletId/deposits',
        {'amount': amount.toStringAsFixed(2)},
      );
      return double.tryParse('${(json as Map)['cash_balance']}') ?? 0;
    } on ApiException catch (e) {
      if (e.statusCode == 404 || e.statusCode == 405) {
        throw ApiException('Para yatırma özelliği henüz backend’de yok.');
      }
      rethrow;
    }
  }

  /// POST /api/v1/wallets/{id}/trades — sanal alım/satım.
  /// İşlem internet gerektirir; önbelleğe düşmez.
  Future<Trade> placeTrade({
    required String symbol,
    required bool isBuy,
    required int quantity,
  }) async {
    final dynamic json = await _api.post(
      '/api/v1/wallets/$_walletId/trades',
      {
        'schema_version': '1.0',
        'symbol': symbol,
        'side': isBuy ? 'buy' : 'sell',
        'quantity': quantity,
        // Aynı isteğin iki kez işlenmesini engeller.
        'idempotency_key': const Uuid().v4(),
      },
    );
    return Trade.fromJson(json);
  }
}
