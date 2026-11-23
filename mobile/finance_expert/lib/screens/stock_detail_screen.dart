import 'package:flutter/material.dart';

import '../app_state.dart';
import '../data/finance_repository.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import '../services/price_alert_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import '../widgets/price_alert_sheet.dart';
import '../widgets/price_chart.dart';
import 'news_detail_screen.dart';
import 'trade_screen.dart';

/// Hisse Detay: son fiyat, fiyat grafiği, eldeki adet,
/// hisseyle ilgili haberler ve yapay zekâ yorumları.
class StockDetailScreen extends StatefulWidget {
  final String symbol;
  final String? companyName;

  const StockDetailScreen({super.key, required this.symbol, this.companyName});

  @override
  State<StockDetailScreen> createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  final FinanceRepository _repo = FinanceRepository.instance;

  Loaded<Quote?>? _quote;
  Loaded<PriceHistory>? _history;
  Loaded<List<NewsItem>>? _news;
  final Map<String, NewsAnalysis?> _analyses = {};
  int? _ownedQuantity;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    AppEvents.portfolioChanged.addListener(_loadPosition);
    PriceAlertService.instance.addListener(_onAlertsChanged);
    _load();
  }

  @override
  void dispose() {
    AppEvents.portfolioChanged.removeListener(_loadPosition);
    PriceAlertService.instance.removeListener(_onAlertsChanged);
    super.dispose();
  }

  void _onAlertsChanged() {
    if (mounted) setState(() {});
  }

  void _openAlert() => showPriceAlertSheet(
    context,
    symbol: widget.symbol,
    currentPrice: _quote?.data?.price,
  );

  Widget _buildAlertButton() {
    final PriceAlert? alert = PriceAlertService.instance.alertFor(
      widget.symbol,
    );
    final bool active = alert?.isWatching ?? false;
    return InkWell(
      onTap: _openAlert,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: active ? AppColors.warning.withValues(alpha: 0.15) : AppColors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: active ? AppColors.warning : AppColors.border,
          ),
        ),
        child: Icon(
          active
              ? Icons.notifications_active_rounded
              : Icons.add_alert_outlined,
          color: active ? AppColors.warning : Colors.white,
          size: 22,
        ),
      ),
    );
  }

  Widget _buildAlertSummary() {
    final PriceAlert? alert = PriceAlertService.instance.alertFor(
      widget.symbol,
    );
    if (alert == null) return const SizedBox.shrink();
    final List<String> parts = [
      if (alert.upper != null)
        'Üst ${formatMoney(alert.upper)}${alert.upperHitAt != null ? ' ✓' : ''}',
      if (alert.lower != null)
        'Alt ${formatMoney(alert.lower)}${alert.lowerHitAt != null ? ' ✓' : ''}',
    ];
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: InkWell(
        onTap: _openAlert,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppColors.warning.withValues(alpha: 0.35),
            ),
          ),
          child: Row(
            children: [
              const Icon(
                Icons.notifications_active_outlined,
                color: AppColors.warning,
                size: 18,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '${alert.enabled ? 'Fiyat alarmı' : 'Alarm kapalı'}: ${parts.join(' · ')}',
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                ),
              ),
              const Icon(
                Icons.chevron_right_rounded,
                color: AppColors.muted,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    await Future.wait([
      _loadPrices(),
      _loadNews(),
      _loadPosition(),
    ]);
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadPrices() async {
    try {
      final results = await Future.wait([
        _repo.quote(widget.symbol),
        _repo.history(widget.symbol),
      ]);
      if (!mounted) return;
      setState(() {
        _quote = results[0] as Loaded<Quote?>;
        _history = results[1] as Loaded<PriceHistory>;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    }
  }

  Future<void> _loadNews() async {
    try {
      final Loaded<List<NewsItem>> news = await _repo.news(
        symbol: widget.symbol,
        limit: 5,
      );
      if (!mounted) return;
      setState(() => _news = news);
      final List<NewsAnalysis?> analyses = await Future.wait(
        news.data.map((n) => _repo.analysis(n.newsId)),
      );
      if (!mounted) return;
      setState(() {
        for (int i = 0; i < news.data.length; i++) {
          _analyses[news.data[i].newsId] = analyses[i];
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _news = const Loaded<List<NewsItem>>([]));
    }
  }

  Future<void> _loadPosition() async {
    try {
      final Loaded<Valuation> v = await _repo.valuation();
      if (!mounted) return;
      setState(() => _ownedQuantity = v.data.quantityOf(widget.symbol));
    } catch (_) {
      // Pozisyon bilgisi olmadan da ekran çalışır.
    }
  }

  bool get _offline =>
      (_quote?.fromCache ?? false) ||
      (_history?.fromCache ?? false) ||
      (_news?.fromCache ?? false);

  Future<void> _openTrade(bool isBuy) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TradeScreen(
          initialSymbol: widget.symbol,
          initialIsBuy: isBuy,
        ),
      ),
    );
    _loadPrices();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.accent,
          onRefresh: _load,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              ScreenHeader(
                title: widget.symbol,
                leading: const BackSquareButton(),
                trailing: _buildAlertButton(),
              ),
              if ((widget.companyName ?? '').isNotEmpty) ...[
                const SizedBox(height: 6),
                Padding(
                  padding: const EdgeInsets.only(left: 56),
                  child: Text(
                    widget.companyName!,
                    style: const TextStyle(color: AppColors.muted, fontSize: 13),
                  ),
                ),
              ],
              const SizedBox(height: 20),
              if (_offline)
                OfflineBanner(
                  cachedAt: _quote?.cachedAt ?? _history?.cachedAt,
                ),
              _buildPriceCard(),
              _buildAlertSummary(),
              const SizedBox(height: 16),
              _buildTradeButtons(),
              const SizedBox(height: 28),
              const SectionTitle('Haberler ve AI Yorumları'),
              const SizedBox(height: 6),
              const Text(
                'Yorumlar yapay zekâ tarafından üretilir ve yatırım tavsiyesi değildir.',
                style: TextStyle(color: AppColors.subtle, fontSize: 12),
              ),
              const SizedBox(height: 14),
              ..._buildNews(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPriceCard() {
    if (_quote == null && _loading) return const LoadingBox(height: 300);
    if (_quote == null) {
      return ErrorBox(
        message: _error ?? 'Fiyat bilgisi alınamadı.',
        onRetry: _load,
      );
    }
    final Quote? quote = _quote!.data;
    final PriceHistory? history = _history?.data;
    final double? change = history?.changePercent;
    final bool up = (change ?? 0) >= 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.cardBlue, AppColors.cardDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderBlue),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Güncel fiyat',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                quote == null ? 'Fiyat yok' : formatMoney(quote.price),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 30,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 12),
              if (change != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 5),
                  child: Text(
                    formatPercent(change),
                    style: TextStyle(
                      color: up ? AppColors.accent : AppColors.negative,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            quote == null
                ? 'Bu hisse için henüz fiyat kaydı yok.'
                : '${formatDateTime(quote.asOf)} · ${quote.provider}${quote.isDelayed ? ' · gecikmeli' : ''}',
            style: TextStyle(
              color: quote?.isDelayed ?? false
                  ? AppColors.warning
                  : AppColors.subtle,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 20),
          if (history != null)
            PriceChart(points: history.points)
          else
            const LoadingBox(height: 180),
          if (_ownedQuantity != null) ...[
            const SizedBox(height: 16),
            Divider(color: Colors.white.withValues(alpha: 0.08), height: 1),
            const SizedBox(height: 14),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Portföyünüzde',
                  style: TextStyle(color: AppColors.muted, fontSize: 13),
                ),
                Text(
                  '$_ownedQuantity adet',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTradeButtons() {
    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 50,
            child: ElevatedButton.icon(
              onPressed: () => _openTrade(true),
              icon: const Icon(Icons.add_chart_rounded, size: 20),
              label: const Text(
                'Al',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.accent,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: SizedBox(
            height: 50,
            child: OutlinedButton.icon(
              onPressed: (_ownedQuantity ?? 0) > 0
                  ? () => _openTrade(false)
                  : null,
              icon: const Icon(Icons.sell_outlined, size: 20),
              label: const Text(
                'Sat',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
              style: OutlinedButton.styleFrom(
                backgroundColor: AppColors.card,
                foregroundColor: Colors.white,
                disabledForegroundColor: AppColors.subtle,
                side: const BorderSide(color: AppColors.border),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildNews() {
    if (_news == null) return const [LoadingBox(height: 120)];
    if (_news!.data.isEmpty) {
      return const [
        EmptyBox(
          message: 'Bu hisseyle ilgili henüz haber yok.',
          icon: Icons.newspaper_rounded,
        ),
      ];
    }
    final List<Widget> cards = [];
    for (final NewsItem item in _news!.data) {
      cards.add(_buildNewsCard(item));
      cards.add(const SizedBox(height: 12));
    }
    return cards;
  }

  Widget _buildNewsCard(NewsItem item) {
    final bool loaded = _analyses.containsKey(item.newsId);
    final NewsAnalysis? analysis = _analyses[item.newsId];
    final AnalysisImpact? impact = analysis?.impactFor(widget.symbol);

    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => NewsDetailScreen(
            item: item,
            analysis: loaded ? analysis : null,
          ),
        ),
      ),
      child: Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${item.source.toUpperCase()} · ${formatShortTime(item.publishedAt)}',
            style: const TextStyle(
              color: AppColors.accent,
              fontSize: 11,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            item.title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (item.summary.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              item.summary,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: AppColors.muted, fontSize: 13),
            ),
          ],
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: _buildAnalysisBody(loaded, analysis, impact),
          ),
        ],
      ),
      ),
    );
  }

  Widget _buildAnalysisBody(
    bool loaded,
    NewsAnalysis? analysis,
    AnalysisImpact? impact,
  ) {
    if (!loaded) {
      return const Text(
        'AI yorumu yükleniyor...',
        style: TextStyle(color: AppColors.muted, fontSize: 13),
      );
    }
    if (analysis == null || !analysis.isCompleted) {
      return const Row(
        children: [
          Icon(Icons.hourglass_empty_rounded, color: AppColors.muted, size: 16),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Bu haber için AI yorumu henüz hazır değil.',
              style: TextStyle(color: AppColors.muted, fontSize: 13),
            ),
          ),
        ],
      );
    }
    final style = impact == null ? null : impactStyle(impact.direction);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.auto_awesome_rounded,
              color: AppColors.accent,
              size: 16,
            ),
            const SizedBox(width: 6),
            const Text(
              'AI yorumu',
              style: TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Spacer(),
            if (style != null)
              Pill(text: style.label, color: style.color, icon: style.icon),
          ],
        ),
        if (analysis.summary != null) ...[
          const SizedBox(height: 10),
          Text(
            analysis.summary!,
            style: const TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ],
        if (impact != null && impact.reason.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            '${impact.symbol}: ${impact.reason}',
            style: const TextStyle(color: Colors.white, fontSize: 13),
          ),
          const SizedBox(height: 6),
          Text(
            'Güven: %${(impact.confidence * 100).round()}',
            style: const TextStyle(color: AppColors.subtle, fontSize: 12),
          ),
        ],
      ],
    );
  }
}
