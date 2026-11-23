import '../utils/format.dart';

/// Backend (FastAPI) yanıtlarının Dart karşılıkları.
/// Alan adları contracts/ altındaki JSON sözleşmeleriyle aynıdır.

Map<String, dynamic> _map(dynamic json) =>
    Map<String, dynamic>.from(json as Map);

List<dynamic> _list(dynamic json) => (json as List?) ?? const [];

class UserProfile {
  final int id;
  final String fullName;
  final String email;
  final int? walletNumber;

  const UserProfile({
    required this.id,
    required this.fullName,
    required this.email,
    this.walletNumber,
  });

  /// API cüzdanı "wallet:1" biçiminde bekler.
  String? get walletId => walletNumber == null ? null : 'wallet:$walletNumber';

  String get firstName => fullName.trim().split(RegExp(r'\s+')).first;

  factory UserProfile.fromJson(dynamic json) {
    final m = _map(json);
    return UserProfile(
      id: (m['id'] as num).toInt(),
      fullName: (m['full_name'] ?? '').toString(),
      email: (m['email'] ?? '').toString(),
      walletNumber: (m['wallet_id'] as num?)?.toInt(),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'full_name': fullName,
    'email': email,
    'wallet_id': walletNumber,
  };
}

class Stock {
  final String symbol;
  final String companyName;
  final String market;
  final bool isActive;

  const Stock({
    required this.symbol,
    required this.companyName,
    required this.market,
    required this.isActive,
  });

  factory Stock.fromJson(dynamic json) {
    final m = _map(json);
    return Stock(
      symbol: m['symbol'].toString(),
      companyName: (m['company_name'] ?? '').toString(),
      market: (m['market'] ?? 'BIST').toString(),
      isActive: m['is_active'] != false,
    );
  }
}

class Quote {
  final String symbol;
  final double price;
  final String currency;
  final DateTime? asOf;
  final String provider;
  final bool isDelayed;

  const Quote({
    required this.symbol,
    required this.price,
    required this.currency,
    required this.asOf,
    required this.provider,
    required this.isDelayed,
  });

  factory Quote.fromJson(dynamic json) {
    final m = _map(json);
    return Quote(
      symbol: m['symbol'].toString(),
      price: parseNum(m['price']) ?? 0,
      currency: (m['currency'] ?? 'TRY').toString(),
      asOf: parseDate(m['as_of']),
      provider: (m['provider'] ?? '').toString(),
      isDelayed: m['is_delayed'] == true,
    );
  }
}

class PriceHistory {
  final String symbol;
  final List<Quote> points;

  const PriceHistory({required this.symbol, required this.points});

  /// İlk ve son fiyata göre yüzde değişim.
  double? get changePercent {
    if (points.length < 2 || points.first.price == 0) return null;
    return (points.last.price - points.first.price) / points.first.price * 100;
  }

  factory PriceHistory.fromJson(dynamic json) {
    final m = _map(json);
    return PriceHistory(
      symbol: m['symbol'].toString(),
      points: _list(m['history']).map(Quote.fromJson).toList(),
    );
  }
}

class NewsItem {
  final String newsId;
  final String source;
  final String title;
  final String summary;
  final String url;
  final DateTime? publishedAt;
  final List<String> symbols;

  const NewsItem({
    required this.newsId,
    required this.source,
    required this.title,
    required this.summary,
    required this.url,
    required this.publishedAt,
    required this.symbols,
  });

  factory NewsItem.fromJson(dynamic json) {
    final m = _map(json);
    return NewsItem(
      newsId: m['news_id'].toString(),
      source: (m['source'] ?? '').toString(),
      title: (m['title'] ?? '').toString(),
      summary: (m['summary'] ?? '').toString(),
      url: (m['url'] ?? '').toString(),
      publishedAt: parseDate(m['published_at']),
      symbols: _list(m['symbols']).map((e) => e.toString()).toList(),
    );
  }
}

class AnalysisImpact {
  final String symbol;

  /// positive | negative | neutral | uncertain
  final String direction;
  final double confidence;
  final String reason;

  const AnalysisImpact({
    required this.symbol,
    required this.direction,
    required this.confidence,
    required this.reason,
  });

  factory AnalysisImpact.fromJson(dynamic json) {
    final m = _map(json);
    return AnalysisImpact(
      symbol: m['symbol'].toString(),
      direction: (m['direction'] ?? 'uncertain').toString(),
      confidence: parseNum(m['confidence']) ?? 0,
      reason: (m['reason'] ?? '').toString(),
    );
  }
}

class NewsAnalysis {
  final String newsId;

  /// completed ya da backend'deki iş durumu (pending, processing, failed...)
  final String status;
  final String? summary;
  final List<AnalysisImpact> impacts;

  const NewsAnalysis({
    required this.newsId,
    required this.status,
    required this.summary,
    required this.impacts,
  });

  bool get isCompleted => status == 'completed';

  AnalysisImpact? impactFor(String symbol) {
    for (final i in impacts) {
      if (i.symbol == symbol) return i;
    }
    return impacts.isEmpty ? null : impacts.first;
  }

  factory NewsAnalysis.fromJson(dynamic json) {
    final m = _map(json);
    final analysis = m['analysis'];
    if (analysis == null) {
      return NewsAnalysis(
        newsId: m['news_id'].toString(),
        status: (m['status'] ?? 'pending').toString(),
        summary: null,
        impacts: const [],
      );
    }
    final a = _map(analysis);
    return NewsAnalysis(
      newsId: m['news_id'].toString(),
      status: (m['status'] ?? 'completed').toString(),
      summary: a['summary']?.toString(),
      impacts: _list(a['impacts']).map(AnalysisImpact.fromJson).toList(),
    );
  }
}

class ValuedPosition {
  final String symbol;
  final int quantity;
  final double averageCost;
  final double? costBasis;
  final double? lastPrice;
  final double? marketValue;
  final double? unrealizedPnl;
  final double? unrealizedPnlPercent;

  /// current | stale | test | missing | invalid | currency_mismatch
  final String priceStatus;

  const ValuedPosition({
    required this.symbol,
    required this.quantity,
    required this.averageCost,
    required this.costBasis,
    required this.lastPrice,
    required this.marketValue,
    required this.unrealizedPnl,
    required this.unrealizedPnlPercent,
    required this.priceStatus,
  });

  factory ValuedPosition.fromJson(dynamic json) {
    final m = _map(json);
    return ValuedPosition(
      symbol: m['symbol'].toString(),
      quantity: (m['quantity'] as num).toInt(),
      averageCost: parseNum(m['average_cost']) ?? 0,
      costBasis: parseNum(m['cost_basis']),
      lastPrice: parseNum(m['last_price']),
      marketValue: parseNum(m['market_value']),
      unrealizedPnl: parseNum(m['unrealized_pnl']),
      unrealizedPnlPercent: parseNum(m['unrealized_pnl_percent']),
      priceStatus: (m['price_status'] ?? 'missing').toString(),
    );
  }
}

/// GET /api/v1/wallets/{id}/valuation
class Valuation {
  final String walletId;
  final String currency;
  final double cashBalance;
  final double realizedPnl;
  final double positionsCost;
  final double? portfolioValue;
  final double? unrealizedPnl;
  final double? unrealizedPnlPercent;
  final bool isComplete;
  final bool isCurrent;
  final List<ValuedPosition> positions;
  final List<String> warnings;

  const Valuation({
    required this.walletId,
    required this.currency,
    required this.cashBalance,
    required this.realizedPnl,
    required this.positionsCost,
    required this.portfolioValue,
    required this.unrealizedPnl,
    required this.unrealizedPnlPercent,
    required this.isComplete,
    required this.isCurrent,
    required this.positions,
    required this.warnings,
  });

  /// Toplam değer hesaplanamazsa en azından nakit + maliyet gösterilir.
  double get displayTotal =>
      portfolioValue ?? (cashBalance + positionsCost);

  int quantityOf(String symbol) {
    for (final p in positions) {
      if (p.symbol == symbol) return p.quantity;
    }
    return 0;
  }

  factory Valuation.fromJson(dynamic json) {
    final m = _map(json);
    return Valuation(
      walletId: m['wallet_id'].toString(),
      currency: (m['currency'] ?? 'TRY').toString(),
      cashBalance: parseNum(m['cash_balance']) ?? 0,
      realizedPnl: parseNum(m['realized_pnl']) ?? 0,
      positionsCost: parseNum(m['positions_cost']) ?? 0,
      portfolioValue: parseNum(m['portfolio_value']),
      unrealizedPnl: parseNum(m['unrealized_pnl']),
      unrealizedPnlPercent: parseNum(m['unrealized_pnl_percent']),
      isComplete: m['valuation_complete'] == true,
      isCurrent: m['valuation_is_current'] == true,
      positions: _list(m['positions']).map(ValuedPosition.fromJson).toList(),
      warnings: _list(m['warnings']).map((e) => e.toString()).toList(),
    );
  }
}

class Trade {
  final String tradeId;
  final String symbol;

  /// buy | sell
  final String side;
  final int quantity;
  final double executionPrice;
  final double grossAmount;
  final double? realizedPnl;
  final DateTime? executedAt;

  const Trade({
    required this.tradeId,
    required this.symbol,
    required this.side,
    required this.quantity,
    required this.executionPrice,
    required this.grossAmount,
    required this.realizedPnl,
    required this.executedAt,
  });

  bool get isBuy => side == 'buy';

  factory Trade.fromJson(dynamic json) {
    final m = _map(json);
    return Trade(
      tradeId: m['trade_id'].toString(),
      symbol: m['symbol'].toString(),
      side: (m['side'] ?? 'buy').toString(),
      quantity: (m['quantity'] as num).toInt(),
      executionPrice: parseNum(m['execution_price']) ?? 0,
      grossAmount: parseNum(m['gross_amount']) ?? 0,
      realizedPnl: parseNum(m['realized_pnl']),
      executedAt: parseDate(m['executed_at']),
    );
  }
}
