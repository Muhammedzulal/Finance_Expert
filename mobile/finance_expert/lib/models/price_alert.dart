import '../utils/format.dart';

/// Bir hisse için kullanıcının kurduğu alt / üst fiyat limiti.
///
/// Her limit bir kez tetiklenir (aracı kurum uygulamalarındaki gibi);
/// tetiklenen limit, kullanıcı alarmı yeniden kaydedene kadar pasif kalır.
class PriceAlert {
  final String symbol;
  final double? lower;
  final double? upper;
  final bool enabled;

  /// Alarm kurulurken görülen fiyat (bilgi amaçlı).
  final double? basePrice;
  final DateTime createdAt;
  final DateTime? lowerHitAt;
  final DateTime? upperHitAt;

  const PriceAlert({
    required this.symbol,
    required this.lower,
    required this.upper,
    required this.createdAt,
    this.enabled = true,
    this.basePrice,
    this.lowerHitAt,
    this.upperHitAt,
  });

  bool get lowerActive => lower != null && lowerHitAt == null;
  bool get upperActive => upper != null && upperHitAt == null;

  /// Kontrol edilmesi gereken bir limit kaldı mı?
  bool get isWatching => enabled && (lowerActive || upperActive);

  bool get anyTriggered => lowerHitAt != null || upperHitAt != null;

  PriceAlert withEnabled(bool value) => PriceAlert(
    symbol: symbol,
    lower: lower,
    upper: upper,
    enabled: value,
    basePrice: basePrice,
    createdAt: createdAt,
    lowerHitAt: lowerHitAt,
    upperHitAt: upperHitAt,
  );

  PriceAlert withHits({DateTime? lowerHit, DateTime? upperHit}) => PriceAlert(
    symbol: symbol,
    lower: lower,
    upper: upper,
    enabled: enabled,
    basePrice: basePrice,
    createdAt: createdAt,
    lowerHitAt: lowerHit ?? lowerHitAt,
    upperHitAt: upperHit ?? upperHitAt,
  );

  Map<String, dynamic> toJson() => {
    'symbol': symbol,
    'lower': lower,
    'upper': upper,
    'enabled': enabled,
    'base_price': basePrice,
    'created_at': createdAt.toIso8601String(),
    'lower_hit_at': lowerHitAt?.toIso8601String(),
    'upper_hit_at': upperHitAt?.toIso8601String(),
  };

  factory PriceAlert.fromJson(dynamic json) {
    final Map m = json as Map;
    return PriceAlert(
      symbol: m['symbol'].toString(),
      lower: parseNum(m['lower']),
      upper: parseNum(m['upper']),
      enabled: m['enabled'] != false,
      basePrice: parseNum(m['base_price']),
      createdAt: parseDate(m['created_at']) ?? DateTime.now(),
      lowerHitAt: parseDate(m['lower_hit_at']),
      upperHitAt: parseDate(m['upper_hit_at']),
    );
  }
}

/// Tetiklenen bir fiyat alarmı (bildirim kaydı).
class PriceAlertEvent {
  final String symbol;
  final bool isUpper;
  final double limit;
  final double price;
  final DateTime at;
  final bool read;

  const PriceAlertEvent({
    required this.symbol,
    required this.isUpper,
    required this.limit,
    required this.price,
    required this.at,
    this.read = false,
  });

  String get message => isUpper
      ? '$symbol üst limitinize ulaştı: ${formatMoney(price)} (limit ${formatMoney(limit)}).'
      : '$symbol alt limitinize düştü: ${formatMoney(price)} (limit ${formatMoney(limit)}).';

  PriceAlertEvent markRead() => PriceAlertEvent(
    symbol: symbol,
    isUpper: isUpper,
    limit: limit,
    price: price,
    at: at,
    read: true,
  );

  Map<String, dynamic> toJson() => {
    'symbol': symbol,
    'is_upper': isUpper,
    'limit': limit,
    'price': price,
    'at': at.toIso8601String(),
    'read': read,
  };

  factory PriceAlertEvent.fromJson(dynamic json) {
    final Map m = json as Map;
    return PriceAlertEvent(
      symbol: m['symbol'].toString(),
      isUpper: m['is_upper'] == true,
      limit: parseNum(m['limit']) ?? 0,
      price: parseNum(m['price']) ?? 0,
      at: parseDate(m['at']) ?? DateTime.now(),
      read: m['read'] == true,
    );
  }
}
