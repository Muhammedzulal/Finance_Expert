import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/finance_repository.dart';
import '../models/models.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'stock_detail_screen.dart';

/// Haber Detay ekranı (Furkan'ın tasarımı).
class NewsDetailScreen extends StatefulWidget {
  final NewsItem item;

  /// Liste ekranında zaten yüklendiyse tekrar istenmez.
  final NewsAnalysis? analysis;

  const NewsDetailScreen({super.key, required this.item, this.analysis});

  @override
  State<NewsDetailScreen> createState() => _NewsDetailScreenState();
}

class _NewsDetailScreenState extends State<NewsDetailScreen> {
  NewsAnalysis? _analysis;
  bool _analysisLoaded = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    if (widget.analysis != null) {
      _analysis = widget.analysis;
      _analysisLoaded = true;
    } else {
      _loadAnalysis();
    }
  }

  Future<void> _loadAnalysis() async {
    final NewsAnalysis? a = await FinanceRepository.instance.analysis(
      widget.item.newsId,
    );
    if (!mounted) return;
    setState(() {
      _analysis = a;
      _analysisLoaded = true;
    });
  }

  String get _sourceBadge {
    final String s = widget.item.source.trim();
    if (s.toLowerCase().contains('bloomberg')) return 'BHT';
    if (s.length <= 4) return s.toUpperCase();
    return s
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .take(3)
        .map((w) => w[0].toUpperCase())
        .join();
  }

  String get _dateLine {
    final DateTime? d = widget.item.publishedAt?.toLocal();
    if (d == null) return '';
    final DateTime now = DateTime.now();
    final bool today =
        d.year == now.year && d.month == now.month && d.day == now.day;
    final String hm =
        '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    final String day = today ? 'Bugün' : formatDateTime(d).split(' ').first;
    final int words =
        '${widget.item.title} ${widget.item.summary}'.split(RegExp(r'\s+')).length;
    final int minutes = (words / 180).ceil().clamp(1, 60);
    return '$day, $hm · $minutes dk okuma';
  }

  Future<void> _share() async {
    final String text = widget.item.url.isNotEmpty
        ? '${widget.item.title}\n${widget.item.url}'
        : widget.item.title;
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) return;
    showAppSnack(context, 'Haber bağlantısı panoya kopyalandı.');
  }

  @override
  Widget build(BuildContext context) {
    final NewsItem item = widget.item;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          children: [
            Row(
              children: [
                const BackSquareButton(),
                const Spacer(),
                _topButton(
                  icon: _saved
                      ? Icons.bookmark_rounded
                      : Icons.bookmark_border_rounded,
                  label: _saved ? 'Kaydedildi' : 'Kaydet',
                  highlighted: _saved,
                  onTap: () => setState(() => _saved = !_saved),
                ),
                const SizedBox(width: 10),
                _topButton(
                  icon: Icons.share_outlined,
                  label: 'Paylaş',
                  onTap: _share,
                ),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.blue,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    _sourceBadge,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.source,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _dateLine,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Text(
              item.title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 26,
                height: 1.25,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 22),
            _buildBanner(item),
            const SizedBox(height: 22),
            Text(
              item.summary.isEmpty ? 'Bu haber için özet bulunmuyor.' : item.summary,
              style: const TextStyle(
                color: Color(0xFFE2E8F0),
                fontSize: 15,
                height: 1.65,
              ),
            ),
            const SizedBox(height: 24),
            _buildAnalysis(),
            if (item.symbols.isNotEmpty) ...[
              const SizedBox(height: 24),
              const SectionTitle('İlgili Hisseler'),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: item.symbols
                    .map(
                      (s) => ActionChip(
                        backgroundColor: AppColors.card,
                        side: const BorderSide(color: AppColors.border),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        avatar: const Icon(
                          Icons.show_chart_rounded,
                          size: 16,
                          color: AppColors.accent,
                        ),
                        label: Text(
                          s,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => StockDetailScreen(symbol: s),
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _topButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    bool highlighted = false,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: highlighted ? AppColors.accent : AppColors.border,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 18,
              color: highlighted ? AppColors.accent : Colors.white,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Haber kaynağında görsel olmadığı için tasarımdaki fotoğraf alanı
  /// kaynak ve ilgili hisselerle doldurulur.
  Widget _buildBanner(NewsItem item) {
    return Container(
      height: 180,
      width: double.infinity,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1D3A63), Color(0xFF0E1A33)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderBlue),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -20,
            bottom: -30,
            child: Icon(
              Icons.trending_up_rounded,
              size: 190,
              color: Colors.white.withValues(alpha: 0.05),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.newspaper_rounded,
                  color: AppColors.accent,
                  size: 30,
                ),
                const Spacer(),
                Text(
                  item.symbols.isEmpty ? 'Piyasa Gündemi' : item.symbols.join(' · '),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Kaynak: ${item.source}',
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysis() {
    final NewsAnalysis? a = _analysis;
    Widget body;
    if (!_analysisLoaded) {
      body = const Text(
        'AI yorumu yükleniyor...',
        style: TextStyle(color: AppColors.muted, fontSize: 13),
      );
    } else if (a == null || !a.isCompleted) {
      body = const Text(
        'Bu haber için AI yorumu henüz hazır değil.',
        style: TextStyle(color: AppColors.muted, fontSize: 13),
      );
    } else {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (a.summary != null)
            Text(
              a.summary!,
              style: const TextStyle(
                color: Color(0xFFE2E8F0),
                fontSize: 14,
                height: 1.5,
              ),
            ),
          for (final AnalysisImpact i in a.impacts) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Text(
                  i.symbol,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 10),
                Builder(
                  builder: (_) {
                    final style = impactStyle(i.direction);
                    return Pill(
                      text: style.label,
                      color: style.color,
                      icon: style.icon,
                    );
                  },
                ),
                const Spacer(),
                Text(
                  'Güven %${(i.confidence * 100).round()}',
                  style: const TextStyle(color: AppColors.subtle, fontSize: 12),
                ),
              ],
            ),
            if (i.reason.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                i.reason,
                style: const TextStyle(color: AppColors.muted, fontSize: 13),
              ),
            ],
          ],
        ],
      );
    }
    return Container(
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
          const Row(
            children: [
              Icon(Icons.auto_awesome_rounded, color: AppColors.accent, size: 18),
              SizedBox(width: 8),
              Text(
                'Yapay Zekâ Yorumu',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          body,
          const SizedBox(height: 14),
          const Text(
            'Bu yorum yapay zekâ tarafından üretilmiştir ve yatırım tavsiyesi değildir.',
            style: TextStyle(color: AppColors.subtle, fontSize: 11),
          ),
        ],
      ),
    );
  }
}
