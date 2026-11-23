import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../config.dart';
import '../data/finance_repository.dart';
import '../data/local_cache.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import 'auth_service.dart';

/// Alt / üst fiyat limiti alarmları.
///
/// Backend'de alarm servisi olmadığı için alarmlar cihazdaki Drift
/// veritabanında tutulur. Uygulama açıkken son fiyatlar belirli aralıkla
/// GET /api/v1/stocks/{symbol}/quote ile kontrol edilir; fiyat limite
/// ulaşınca bildirim üretilir.
class PriceAlertService extends ChangeNotifier {
  PriceAlertService._();

  static final PriceAlertService instance = PriceAlertService._();

  static const String _alertsKey = 'price_alerts';
  static const String _eventsKey = 'price_alert_events';
  static const int _maxEvents = 30;

  final FinanceRepository _repo = FinanceRepository.instance;

  List<PriceAlert> _alerts = [];
  List<PriceAlertEvent> _events = [];
  bool _loaded = false;
  bool _checking = false;
  Timer? _timer;

  /// Son tetiklenen alarm; ana ekran dinleyip kullanıcıya gösterir.
  final ValueNotifier<PriceAlertEvent?> lastTriggered =
      ValueNotifier<PriceAlertEvent?>(null);

  /// Son başarılı kontrolde okunan fiyatlar.
  final Map<String, double> lastPrices = {};
  DateTime? lastCheckAt;

  List<PriceAlert> get alerts => List.unmodifiable(_alerts);
  List<PriceAlertEvent> get events => List.unmodifiable(_events);
  int get unreadCount => _events.where((e) => !e.read).length;

  /// Demo modunda fiyat hızlı değiştiği için daha sık kontrol edilir.
  Duration get interval => AppConfig.demoMode
      ? const Duration(seconds: 10)
      : const Duration(seconds: 30);

  PriceAlert? alertFor(String symbol) {
    for (final PriceAlert a in _alerts) {
      if (a.symbol == symbol) return a;
    }
    return null;
  }

  // ---------------- Yaşam döngüsü ----------------

  Future<void> load() async {
    if (_loaded) return;
    try {
      final CachedPayload? a = await LocalCache.db.read(_alertsKey);
      final CachedPayload? e = await LocalCache.db.read(_eventsKey);
      _alerts = a?.payload is List
          ? (a!.payload as List).map(PriceAlert.fromJson).toList()
          : [];
      _events = e?.payload is List
          ? (e!.payload as List).map(PriceAlertEvent.fromJson).toList()
          : [];
    } catch (_) {
      _alerts = [];
      _events = [];
    }
    _loaded = true;
    notifyListeners();
  }

  /// Ana ekran açıldığında çağrılır.
  Future<void> start() async {
    await load();
    _timer?.cancel();
    _timer = Timer.periodic(interval, (_) => check());
    unawaited(check());
  }

  /// Çıkış yapıldığında çağrılır; bellek temizlenir (önbellek zaten silinir).
  void stop() {
    _timer?.cancel();
    _timer = null;
    _alerts = [];
    _events = [];
    lastPrices.clear();
    lastCheckAt = null;
    lastTriggered.value = null;
    _loaded = false;
  }

  // ---------------- Alarm yönetimi ----------------

  /// Alarmı kaydeder; aynı hisse için önceki alarmın yerine geçer ve
  /// tetiklenmiş limitleri yeniden kurar.
  Future<void> save({
    required String symbol,
    required double? lower,
    required double? upper,
    double? basePrice,
  }) async {
    await load();
    _alerts.removeWhere((a) => a.symbol == symbol);
    _alerts.insert(
      0,
      PriceAlert(
        symbol: symbol,
        lower: lower,
        upper: upper,
        basePrice: basePrice,
        createdAt: DateTime.now(),
      ),
    );
    await _persistAlerts();
    notifyListeners();
    unawaited(check());
  }

  Future<void> setEnabled(String symbol, bool enabled) async {
    final int i = _alerts.indexWhere((a) => a.symbol == symbol);
    if (i < 0) return;
    _alerts[i] = _alerts[i].withEnabled(enabled);
    await _persistAlerts();
    notifyListeners();
    if (enabled) unawaited(check());
  }

  Future<void> remove(String symbol) async {
    _alerts.removeWhere((a) => a.symbol == symbol);
    await _persistAlerts();
    notifyListeners();
  }

  Future<void> markAllRead() async {
    if (unreadCount == 0) return;
    _events = _events.map((e) => e.markRead()).toList();
    await _persistEvents();
    notifyListeners();
  }

  // ---------------- Fiyat kontrolü ----------------

  /// Takipteki hisselerin son fiyatını alır ve limitleri karşılaştırır.
  Future<void> check() async {
    if (_checking || !_loaded) return;
    if (AuthService.instance.currentUser == null) return;
    final List<PriceAlert> watching = _alerts
        .where((a) => a.isWatching)
        .toList();
    if (watching.isEmpty) return;

    _checking = true;
    try {
      final List<PriceAlertEvent> fired = [];
      for (final PriceAlert alert in watching) {
        final Quote? quote = await _freshQuote(alert.symbol);
        if (quote == null || quote.price <= 0) continue;
        final double price = quote.price;
        lastPrices[alert.symbol] = price;

        final DateTime now = DateTime.now();
        DateTime? upperHit;
        DateTime? lowerHit;
        if (alert.upperActive && price >= alert.upper!) {
          upperHit = now;
          fired.add(
            PriceAlertEvent(
              symbol: alert.symbol,
              isUpper: true,
              limit: alert.upper!,
              price: price,
              at: now,
            ),
          );
        }
        if (alert.lowerActive && price <= alert.lower!) {
          lowerHit = now;
          fired.add(
            PriceAlertEvent(
              symbol: alert.symbol,
              isUpper: false,
              limit: alert.lower!,
              price: price,
              at: now,
            ),
          );
        }
        if (upperHit != null || lowerHit != null) {
          // Kontrol sırasında alarm silinmiş/değişmiş olabilir.
          final int i = _alerts.indexWhere(
            (a) => a.symbol == alert.symbol && a.createdAt == alert.createdAt,
          );
          if (i >= 0) {
            _alerts[i] = _alerts[i].withHits(
              lowerHit: lowerHit,
              upperHit: upperHit,
            );
          }
        }
      }
      lastCheckAt = DateTime.now();

      if (fired.isNotEmpty) {
        _events = [...fired.reversed, ..._events];
        if (_events.length > _maxEvents) {
          _events = _events.sublist(0, _maxEvents);
        }
        await _persistAlerts();
        await _persistEvents();
        try {
          await HapticFeedback.heavyImpact();
          await SystemSound.play(SystemSoundType.alert);
        } catch (_) {}
        for (final PriceAlertEvent e in fired) {
          lastTriggered.value = e;
        }
      }
      notifyListeners();
    } finally {
      _checking = false;
    }
  }

  /// Önbellekten gelen (eski) fiyatla alarm tetiklenmez.
  Future<Quote?> _freshQuote(String symbol) async {
    try {
      final Loaded<Quote?> q = await _repo.quote(symbol);
      if (q.fromCache) return null;
      return q.data;
    } catch (_) {
      return null;
    }
  }

  Future<void> _persistAlerts() async {
    try {
      await LocalCache.db.put(
        _alertsKey,
        _alerts.map((a) => a.toJson()).toList(),
      );
    } catch (_) {}
  }

  Future<void> _persistEvents() async {
    try {
      await LocalCache.db.put(
        _eventsKey,
        _events.map((e) => e.toJson()).toList(),
      );
    } catch (_) {}
  }
}
