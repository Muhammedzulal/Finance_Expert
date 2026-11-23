import 'dart:math';

import '../services/api_client.dart';

/// Demo modu: backend'e ulaşılamadığında ekranları test edebilmek için
/// API'yi uygulama içinde taklit eder.
///
/// Yanıtlar gerçek backend'le AYNI JSON biçimindedir; böylece modeller,
/// önbellek ve ekranlar gerçek kullanımdaki gibi çalışır.
/// Fiyatlar ve haberler gerçek DEĞİLDİR.
class DemoBackend {
  DemoBackend._();

  static final DemoBackend instance = DemoBackend._();

  final Random _random = Random();

  String _fullName = 'Demo Kullanıcı';
  String _email = 'demo@financeexpert.app';
  double _cash = 100000;
  double _realizedPnl = 0;
  final Map<String, _Position> _positions = {};
  final List<Map<String, dynamic>> _trades = [];
  int _tradeCounter = 0;

  static const Map<String, (String, double)> _stocks = {
    'THYAO': ('Türk Hava Yolları', 245.30),
    'GARAN': ('Garanti BBVA', 125.60),
    'ASELS': ('Aselsan', 351.25),
    'AKBNK': ('Akbank', 62.15),
    'BIMAS': ('BİM Mağazalar', 538.50),
    'EREGL': ('Ereğli Demir Çelik', 27.84),
  };

  late final Map<String, double> _prices = {
    for (final e in _stocks.entries) e.key: e.value.$2,
  };

  late final Map<String, List<Map<String, dynamic>>> _history = {
    for (final s in _stocks.keys) s: _makeHistory(s),
  };

  /// GET / POST isteğini karşılar. Gerçek ağ gecikmesini taklit eder.
  Future<dynamic> handle(
    String method,
    String path, {
    Map<String, dynamic>? query,
    Object? body,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 350));
    final List<String> parts = Uri.parse(path).pathSegments;
    // /api/v1/... -> ilk iki parçayı at
    final List<String> p = parts.length > 2 ? parts.sublist(2) : parts;
    final Map<String, dynamic> b = body is Map
        ? Map<String, dynamic>.from(body)
        : <String, dynamic>{};

    if (method == 'POST' && _is(p, ['users', 'login'])) return _login(b);
    if (method == 'POST' && _is(p, ['users', 'register'])) return _register(b);
    if (method == 'GET' && _is(p, ['users', 'me'])) return _me();
    if (method == 'GET' && _is(p, ['stocks'])) return _stockList();
    if (method == 'GET' && p.length == 3 && p[0] == 'stocks' && p[2] == 'quote') {
      return _quote(_symbol(p[1]));
    }
    if (method == 'GET' && p.length == 3 && p[0] == 'stocks' && p[2] == 'history') {
      return _historyOf(_symbol(p[1]), query);
    }
    if (method == 'GET' && _is(p, ['news'])) return _news(query);
    if (method == 'GET' && p.length == 3 && p[0] == 'news' && p[2] == 'analysis') {
      return _analysis(Uri.decodeComponent(p[1]));
    }
    if (p.length == 3 && p[0] == 'wallets') {
      if (method == 'GET' && p[2] == 'valuation') return _valuation();
      if (method == 'GET' && p[2] == 'trades') return _tradeList(query);
      if (method == 'POST' && p[2] == 'trades') return _placeTrade(b);
      if (method == 'POST' && p[2] == 'deposits') return _deposit(b);
    }
    throw ApiException('Demo modunda bu istek desteklenmiyor: $path',
        statusCode: 404);
  }

  bool _is(List<String> p, List<String> expected) =>
      p.length == expected.length &&
      List.generate(p.length, (i) => p[i] == expected[i]).every((x) => x);

  String _symbol(String raw) {
    final String s = raw.toUpperCase();
    if (!_stocks.containsKey(s)) {
      throw ApiException('Hisse bulunamadı.', statusCode: 404);
    }
    return s;
  }

  String _now() => DateTime.now().toUtc().toIso8601String();

  String _money(double v) => v.toStringAsFixed(6);

  // ---------------- Kullanıcı ----------------

  Map<String, dynamic> _login(Map<String, dynamic> b) {
    final String email = (b['email'] ?? '').toString();
    if (email.isNotEmpty) _email = email;
    return {
      'access_token': 'demo-token',
      'token_type': 'bearer',
      'expires_in': 3600,
    };
  }

  Map<String, dynamic> _register(Map<String, dynamic> b) {
    _fullName = (b['full_name'] ?? _fullName).toString();
    _email = (b['email'] ?? _email).toString();
    return {'id': 1, 'full_name': _fullName, 'email': _email};
  }

  Map<String, dynamic> _me() => {
    'id': 1,
    'full_name': _fullName,
    'email': _email,
    'wallet_id': 1,
  };

  // ---------------- Piyasa ----------------

  Map<String, dynamic> _stockList() => {
    'stocks': [
      for (final e in _stocks.entries)
        {
          'symbol': e.key,
          'company_name': e.value.$1,
          'market': 'BIST',
          'is_active': true,
        },
    ],
  };

  /// Her istekte fiyat çok az oynar; böylece ekran "canlı" görünür.
  double _tick(String symbol) {
    final double next =
        _prices[symbol]! * (1 + (_random.nextDouble() - 0.5) * 0.004);
    _prices[symbol] = double.parse(next.toStringAsFixed(2));
    return _prices[symbol]!;
  }

  Map<String, dynamic> _quote(String symbol) => {
    'symbol': symbol,
    'price': _money(_tick(symbol)),
    'currency': 'TRY',
    'as_of': _now(),
    'provider': 'DEMO',
    'is_delayed': false,
  };

  List<Map<String, dynamic>> _makeHistory(String symbol) {
    final Random r = Random(symbol.hashCode);
    final double end = _stocks[symbol]!.$2;
    final List<double> values = [end];
    for (int i = 0; i < 59; i++) {
      values.add(values.last * (1 + (r.nextDouble() - 0.5) * 0.04));
    }
    final List<double> ordered = values.reversed.toList();
    final DateTime now = DateTime.now().toUtc();
    return [
      for (int i = 0; i < ordered.length; i++)
        {
          'symbol': symbol,
          'price': _money(ordered[i]),
          'currency': 'TRY',
          'as_of': now
              .subtract(Duration(days: ordered.length - 1 - i))
              .toIso8601String(),
          'provider': 'DEMO',
          'is_delayed': false,
        },
    ];
  }

  Map<String, dynamic> _historyOf(String symbol, Map<String, dynamic>? query) {
    final int limit = int.tryParse('${query?['limit'] ?? 100}') ?? 100;
    final List<Map<String, dynamic>> all = _history[symbol]!;
    final List<Map<String, dynamic>> points = all.length > limit
        ? all.sublist(all.length - limit)
        : all;
    return {'symbol': symbol, 'history': points};
  }

  // ---------------- Haber ve AI ----------------

  static final List<Map<String, dynamic>> _newsItems = [
    {
      'news_id': 'demo-1',
      'source': 'Bloomberg HT',
      'title': 'THY yolcu sayısında yıllık %8,4 artış bildirdi',
      'summary':
          'Türk Hava Yolları, son döneme ilişkin trafik sonuçlarını açıkladı; dış hatlardaki talep büyümeyi destekledi.',
      'symbols': ['THYAO'],
      'hours': 2,
      'analysis': {
        'summary':
            'Yolcu sayısındaki artış şirketin operasyonel performansına olumlu yansıyabilir.',
        'impacts': [
          {
            'symbol': 'THYAO',
            'direction': 'positive',
            'confidence': 0.72,
            'reason': 'Artan yolcu trafiği gelir beklentisini destekleyebilir.',
          },
        ],
      },
    },
    {
      'news_id': 'demo-2',
      'source': 'KAP',
      'title': 'Aselsan yeni bir savunma sözleşmesi imzaladı',
      'summary':
          'Şirket, yurt içi bir kurumla yeni bir tedarik sözleşmesi imzaladığını KAP’a bildirdi.',
      'symbols': ['ASELS'],
      'hours': 5,
      'analysis': {
        'summary':
            'Yeni sözleşme şirketin sipariş birikimini artırabilir; tutar bilgisi sınırlı.',
        'impacts': [
          {
            'symbol': 'ASELS',
            'direction': 'positive',
            'confidence': 0.64,
            'reason': 'Sipariş birikimindeki artış olumlu algılanabilir.',
          },
        ],
      },
    },
    {
      'news_id': 'demo-3',
      'source': 'Bloomberg HT',
      'title': 'Bankacılık sektöründe kredi büyümesi yavaşladı',
      'summary':
          'Son verilere göre ticari kredilerdeki büyüme hızı bir önceki aya göre geriledi.',
      'symbols': ['GARAN', 'AKBNK'],
      'hours': 9,
      'analysis': {
        'summary':
            'Kredi büyümesindeki yavaşlama bankaların faiz gelirlerini sınırlayabilir.',
        'impacts': [
          {
            'symbol': 'GARAN',
            'direction': 'negative',
            'confidence': 0.55,
            'reason': 'Daha yavaş kredi büyümesi gelir artışını sınırlayabilir.',
          },
          {
            'symbol': 'AKBNK',
            'direction': 'negative',
            'confidence': 0.52,
            'reason': 'Sektör genelindeki yavaşlama bankayı da etkileyebilir.',
          },
        ],
      },
    },
    {
      'news_id': 'demo-4',
      'source': 'KAP',
      'title': 'BİM yeni mağaza açılışlarını duyurdu',
      'summary': 'Şirket, yıl sonuna kadar planlanan yeni mağaza sayısını açıkladı.',
      'symbols': ['BIMAS'],
      'hours': 26,
      'analysis': null,
    },
  ];

  Map<String, dynamic> _newsJson(Map<String, dynamic> n) => {
    'news_id': n['news_id'],
    'source': n['source'],
    'title': n['title'],
    'summary': n['summary'],
    'url': 'https://example.com/${n['news_id']}',
    'published_at': DateTime.now()
        .toUtc()
        .subtract(Duration(hours: n['hours'] as int))
        .toIso8601String(),
    'symbols': n['symbols'],
  };

  Map<String, dynamic> _news(Map<String, dynamic>? query) {
    final String? symbol = query?['symbol']?.toString();
    final int limit = int.tryParse('${query?['limit'] ?? 10}') ?? 10;
    final Iterable<Map<String, dynamic>> filtered = _newsItems.where(
      (n) => symbol == null || (n['symbols'] as List).contains(symbol),
    );
    return {'items': filtered.take(limit).map(_newsJson).toList()};
  }

  Map<String, dynamic> _analysis(String newsId) {
    final Map<String, dynamic> n = _newsItems.firstWhere(
      (e) => e['news_id'] == newsId,
      orElse: () => throw ApiException('Haber bulunamadı.', statusCode: 404),
    );
    if (n['analysis'] == null) {
      return {'news_id': newsId, 'status': 'pending', 'analysis': null};
    }
    return {
      'news_id': newsId,
      'status': 'completed',
      'analysis': n['analysis'],
    };
  }

  // ---------------- Cüzdan ----------------

  Map<String, dynamic> _valuation() {
    double positionsCost = 0;
    double marketTotal = 0;
    final List<Map<String, dynamic>> positions = [];
    for (final MapEntry<String, _Position> e in _positions.entries) {
      final _Position pos = e.value;
      final double last = _prices[e.key]!;
      final double cost = pos.quantity * pos.averageCost;
      final double value = pos.quantity * last;
      positionsCost += cost;
      marketTotal += value;
      positions.add({
        'symbol': e.key,
        'quantity': pos.quantity,
        'average_cost': _money(pos.averageCost),
        'cost_basis': _money(cost),
        'last_price': _money(last),
        'market_value': _money(value),
        'unrealized_pnl': _money(value - cost),
        'unrealized_pnl_percent': cost == 0
            ? '0'
            : ((value - cost) / cost * 100).toStringAsFixed(4),
        'price_status': 'current',
      });
    }
    final double pnl = marketTotal - positionsCost;
    return {
      'wallet_id': 'wallet:1',
      'currency': 'TRY',
      'cash_balance': _money(_cash),
      'realized_pnl': _money(_realizedPnl),
      'positions_cost': _money(positionsCost),
      'portfolio_value': _money(_cash + marketTotal),
      'unrealized_pnl': _money(pnl),
      'unrealized_pnl_percent': positionsCost == 0
          ? '0'
          : (pnl / positionsCost * 100).toStringAsFixed(4),
      'valuation_complete': true,
      'valuation_is_current': true,
      'positions': positions,
      'warnings': <String>[],
    };
  }

  Map<String, dynamic> _deposit(Map<String, dynamic> b) {
    final double amount = double.tryParse('${b['amount']}') ?? 0;
    if (amount <= 0) {
      throw ApiException('Geçerli bir tutar girin.', statusCode: 422);
    }
    _cash += amount;
    return {
      'wallet_id': 'wallet:1',
      'amount': _money(amount),
      'cash_balance': _money(_cash),
      'deposited_at': _now(),
    };
  }

  Map<String, dynamic> _tradeList(Map<String, dynamic>? query) {
    final int limit = int.tryParse('${query?['limit'] ?? 20}') ?? 20;
    return {'items': _trades.reversed.take(limit).toList()};
  }

  Map<String, dynamic> _placeTrade(Map<String, dynamic> b) {
    final String symbol = _symbol(b['symbol'].toString());
    final bool isBuy = b['side'] == 'buy';
    final int quantity = int.tryParse('${b['quantity']}') ?? 0;
    if (quantity <= 0) {
      throw ApiException('Adet en az 1 olmalı.', statusCode: 422);
    }
    final double price = _tick(symbol);
    final double amount = price * quantity;
    double? realized;

    if (isBuy) {
      if (amount > _cash) {
        throw ApiException(
          'Yetersiz bakiye: bu işlem için cüzdanınızda yeterli para yok.',
          statusCode: 409,
          code: 'INSUFFICIENT_FUNDS',
        );
      }
      _cash -= amount;
      final _Position pos = _positions[symbol] ?? _Position(0, 0);
      final double newCost =
          pos.quantity * pos.averageCost + amount;
      pos.quantity += quantity;
      pos.averageCost = newCost / pos.quantity;
      _positions[symbol] = pos;
    } else {
      final _Position? pos = _positions[symbol];
      if (pos == null || pos.quantity < quantity) {
        throw ApiException(
          'Yetersiz hisse: satmak istediğiniz adet portföyünüzdekinden fazla.',
          statusCode: 409,
          code: 'INSUFFICIENT_POSITION',
        );
      }
      realized = (price - pos.averageCost) * quantity;
      _realizedPnl += realized;
      _cash += amount;
      pos.quantity -= quantity;
      if (pos.quantity == 0) _positions.remove(symbol);
    }

    _tradeCounter++;
    final Map<String, dynamic> trade = {
      'trade_id': 'demo-trade-$_tradeCounter',
      'symbol': symbol,
      'side': isBuy ? 'buy' : 'sell',
      'quantity': quantity,
      'execution_price': _money(price),
      'gross_amount': _money(amount),
      'realized_pnl': realized == null ? null : _money(realized),
      'executed_at': _now(),
    };
    _trades.add(trade);
    return trade;
  }
}

class _Position {
  int quantity;
  double averageCost;

  _Position(this.quantity, this.averageCost);
}
