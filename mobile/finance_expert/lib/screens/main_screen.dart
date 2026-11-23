import 'package:flutter/material.dart';

import '../app_state.dart';
import '../data/finance_repository.dart';
import '../data/settings_store.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import '../services/price_alert_service.dart';
import '../services/auth_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'market_screen.dart';
import 'news_detail_screen.dart';
import 'profile_screen.dart';
import 'stock_detail_screen.dart';
import 'wallet_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;

  final List<Widget> _pages = const [
    HomeTab(),
    MarketScreen(),
    WalletScreen(),
    ProfileScreen(),
  ];

  final PriceAlertService _alerts = PriceAlertService.instance;

  @override
  void initState() {
    super.initState();
    _alerts.lastTriggered.addListener(_onAlert);
    _alerts.start();
  }

  @override
  void dispose() {
    _alerts.lastTriggered.removeListener(_onAlert);
    _alerts.stop();
    super.dispose();
  }

  /// Fiyat alarmı tetiklenince hangi ekranda olunursa olsun bildirim gösterir.
  Future<void> _onAlert() async {
    final PriceAlertEvent? e = _alerts.lastTriggered.value;
    if (e == null || !mounted) return;
    final Map<String, bool> settings = await SettingsStore.read(
      'notifications',
      const {'stock': true},
    );
    if (settings['stock'] == false || !mounted) return;
    final Color color = e.isUpper ? AppColors.accent : AppColors.negative;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 6),
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: color.withValues(alpha: 0.6)),
        ),
        content: Row(
          children: [
            Icon(
              e.isUpper
                  ? Icons.trending_up_rounded
                  : Icons.trending_down_rounded,
              color: color,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                e.message,
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
        action: SnackBarAction(
          label: 'Gör',
          textColor: color,
          onPressed: () => Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => StockDetailScreen(symbol: e.symbol),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1221),
      body: IndexedStack(index: _selectedIndex, children: _pages),
      bottomNavigationBar: Container(
        height: 80,
        decoration: const BoxDecoration(
          color: Color(0xFF0B1221),
          border: Border(top: BorderSide(color: Color(0xFF1E293B), width: 1)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildNavItem(0, Icons.home_outlined, 'Ana Sayfa'),
            _buildNavItem(1, Icons.show_chart_rounded, 'Piyasa'),
            _buildNavItem(2, Icons.account_balance_wallet_outlined, 'Cüzdan'),
            _buildNavItem(3, Icons.person_outline_rounded, 'Profil'),
          ],
        ),
      ),
    );
  }

  Widget _buildNavItem(int index, IconData icon, String label) {
    final bool isSelected = _selectedIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedIndex = index),
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: 76,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Üstteki yeşil aktif sekme çizgisi
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              height: 3,
              width: isSelected ? 28 : 0,
              decoration: BoxDecoration(
                color: const Color(0xFF10B981),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // İkon Kutusu
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: isSelected
                    ? const Color(0xFF10B981).withValues(alpha: 0.15)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                icon,
                size: 22,
                color: isSelected
                    ? const Color(0xFF10B981)
                    : const Color(0xFF94A3B8),
              ),
            ),
            // Sekme Başlığı
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  color: isSelected
                      ? const Color(0xFF10B981)
                      : const Color(0xFF94A3B8),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


/// Ana Sayfa: portföy özeti ve AI yorumlu piyasa gündemi.
class HomeTab extends StatefulWidget {
  const HomeTab({super.key});

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final FinanceRepository _repo = FinanceRepository.instance;

  Loaded<Valuation>? _valuation;
  String? _valuationError;
  Loaded<List<NewsItem>>? _news;
  String? _newsError;
  final Map<String, NewsAnalysis?> _analyses = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    AppEvents.portfolioChanged.addListener(_loadValuation);
    _loadAll();
  }

  @override
  void dispose() {
    AppEvents.portfolioChanged.removeListener(_loadValuation);
    super.dispose();
  }

  Future<void> _loadAll() async {
    setState(() => _loading = true);
    await Future.wait([_loadValuation(), _loadNews()]);
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadValuation() async {
    try {
      final Loaded<Valuation> v = await _repo.valuation();
      if (!mounted) return;
      setState(() {
        _valuation = v;
        _valuationError = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _valuationError = e.toString());
    }
  }

  Future<void> _loadNews() async {
    try {
      final Loaded<List<NewsItem>> n = await _repo.news(limit: 5);
      if (!mounted) return;
      setState(() {
        _news = n;
        _newsError = null;
      });
      // Her haberin AI analizini arka planda getir.
      final List<NewsAnalysis?> results = await Future.wait(
        n.data.map((item) => _repo.analysis(item.newsId)),
      );
      if (!mounted) return;
      setState(() {
        for (int i = 0; i < n.data.length; i++) {
          _analyses[n.data[i].newsId] = results[i];
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _newsError = e.toString());
    }
  }

  bool get _offline =>
      (_valuation?.fromCache ?? false) || (_news?.fromCache ?? false);

  @override
  Widget build(BuildContext context) {
    final String name = AuthService.instance.currentUser?.firstName ?? '';
    return SafeArea(
      child: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: _loadAll,
        child: ListView(
          padding: const EdgeInsets.all(20.0),
          children: [
            ScreenHeader(title: name.isEmpty ? 'Merhaba' : 'Merhaba, $name'),
            const SizedBox(height: 24),
            if (_offline)
              OfflineBanner(
                cachedAt: _valuation?.cachedAt ?? _news?.cachedAt,
              ),
            _buildBalanceCard(),
            const SizedBox(height: 28),
            const SectionTitle('Piyasa Gündemi'),
            const SizedBox(height: 14),
            ..._buildNews(),
          ],
        ),
      ),
    );
  }

  Widget _buildBalanceCard() {
    final Valuation? v = _valuation?.data;
    final double? pnlPercent = v?.unrealizedPnlPercent;
    final bool positive = (pnlPercent ?? 0) >= 0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.cardBlue, AppColors.cardDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderBlue, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Toplam Portföy Değeri',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 10),
          if (v == null && _loading)
            const SizedBox(
              height: 36,
              child: Align(
                alignment: Alignment.centerLeft,
                child: SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.4,
                    color: AppColors.accent,
                  ),
                ),
              ),
            )
          else if (v == null)
            Text(
              _valuationError ?? 'Portföy bilgisi alınamadı.',
              style: const TextStyle(color: AppColors.negative, fontSize: 13),
            )
          else
            Text(
              formatMoney(v.displayTotal),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 30,
                fontWeight: FontWeight.bold,
              ),
            ),
          const SizedBox(height: 16),
          Divider(color: Colors.white.withValues(alpha: 0.08), height: 1),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Nakit: ${formatMoney(v?.cashBalance)}',
                style: const TextStyle(color: AppColors.muted, fontSize: 13),
              ),
              Text(
                pnlPercent == null ? 'K/Z —' : formatPercent(pnlPercent),
                style: TextStyle(
                  color: pnlPercent == null
                      ? AppColors.muted
                      : (positive ? AppColors.accent : AppColors.negative),
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  List<Widget> _buildNews() {
    if (_news == null && _loading) return const [LoadingBox()];
    if (_news == null) {
      return [
        ErrorBox(
          message: _newsError ?? 'Haberler alınamadı.',
          onRetry: _loadNews,
        ),
      ];
    }
    if (_news!.data.isEmpty) {
      return const [
        EmptyBox(
          message: 'Henüz haber yok. Veri toplama servisi çalıştığında burada görünecek.',
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
    final bool analysisLoaded = _analyses.containsKey(item.newsId);
    final NewsAnalysis? analysis = _analyses[item.newsId];
    final String? symbol = item.symbols.isEmpty ? null : item.symbols.first;
    final AnalysisImpact? impact =
        (analysis != null && symbol != null) ? analysis.impactFor(symbol) : null;

    Widget badge;
    if (!analysisLoaded) {
      badge = const Pill(
        text: 'AI analizi yükleniyor',
        color: AppColors.muted,
        icon: Icons.auto_awesome_rounded,
      );
    } else if (analysis == null || !analysis.isCompleted) {
      badge = const Pill(
        text: 'AI analizi bekleniyor',
        color: AppColors.muted,
        icon: Icons.hourglass_empty_rounded,
      );
    } else if (impact == null) {
      badge = const Pill(
        text: 'AI özeti hazır',
        color: AppColors.accent,
        icon: Icons.auto_awesome_rounded,
      );
    } else {
      final style = impactStyle(impact.direction);
      badge = Pill(text: style.label, color: style.color, icon: style.icon);
    }

    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => NewsDetailScreen(
            item: item,
            analysis: analysisLoaded ? analysis : null,
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
              [
                item.source.toUpperCase(),
                if (item.symbols.isNotEmpty) item.symbols.join(', '),
                formatShortTime(item.publishedAt),
              ].join(' · '),
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
            if (analysis?.summary != null) ...[
              const SizedBox(height: 8),
              Text(
                analysis!.summary!,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppColors.muted, fontSize: 13),
              ),
            ],
            const SizedBox(height: 14),
            badge,
          ],
        ),
      ),
    );
  }
}
