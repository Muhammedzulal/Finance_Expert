import 'package:flutter/material.dart';

import '../app_state.dart';
import '../data/finance_repository.dart';
import '../models/models.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'deposit_screen.dart';
import 'stock_detail_screen.dart';
import 'trade_screen.dart';

/// Sanal Cüzdan: portföy değeri, kâr/zarar, varlıklar ve işlem geçmişi.
class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  final FinanceRepository _repo = FinanceRepository.instance;

  Loaded<Valuation>? _valuation;
  Loaded<List<Trade>>? _trades;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    AppEvents.portfolioChanged.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    AppEvents.portfolioChanged.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final Loaded<Valuation> valuation = await _repo.valuation();
      Loaded<List<Trade>>? trades;
      try {
        trades = await _repo.trades(limit: 10);
      } catch (_) {
        trades = null;
      }
      if (!mounted) return;
      setState(() {
        _valuation = valuation;
        _trades = trades;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _openTrade(bool isBuy) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => TradeScreen(initialIsBuy: isBuy)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        color: AppColors.accent,
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(20.0),
          children: [
            const ScreenHeader(title: 'Sanal Cüzdanım'),
            const SizedBox(height: 24),
            if (_valuation?.fromCache ?? false)
              OfflineBanner(cachedAt: _valuation!.cachedAt),
            if (_valuation == null && _loading)
              const LoadingBox(height: 200)
            else if (_valuation == null)
              ErrorBox(
                message: _error ?? 'Cüzdan bilgisi alınamadı.',
                onRetry: _load,
              )
            else ...[
              _buildSummaryCard(_valuation!.data),
              const SizedBox(height: 18),
              _buildButtons(),
              if (_valuation!.data.warnings.isNotEmpty) ...[
                const SizedBox(height: 14),
                _buildWarnings(_valuation!.data.warnings),
              ],
              const SizedBox(height: 28),
              const SectionTitle('Varlıklarım'),
              const SizedBox(height: 14),
              _buildPositions(_valuation!.data),
              const SizedBox(height: 28),
              const SectionTitle('Son İşlemler'),
              const SizedBox(height: 14),
              _buildTrades(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(Valuation v) {
    final double? pnl = v.unrealizedPnl;
    final double? pnlPercent = v.unrealizedPnlPercent;
    final bool positive = (pnl ?? 0) >= 0;
    final Color pnlColor = pnl == null
        ? AppColors.muted
        : (positive ? AppColors.accent : AppColors.negative);

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
        border: Border.all(color: AppColors.borderBlue),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Toplam Portföy Değeri',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 10),
          Text(
            formatMoney(v.displayTotal),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 30,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (!v.isComplete)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                'Bazı hisselerin fiyatı olmadığı için maliyet üzerinden gösteriliyor.',
                style: TextStyle(color: AppColors.warning, fontSize: 11),
              ),
            ),
          const SizedBox(height: 16),
          Divider(color: Colors.white.withValues(alpha: 0.08), height: 1),
          const SizedBox(height: 14),
          _summaryRow('Nakit', formatMoney(v.cashBalance)),
          const SizedBox(height: 8),
          _summaryRow(
            'Gerçekleşmemiş kâr / zarar',
            pnl == null
                ? '—'
                : '${formatMoney(pnl)} (${formatPercent(pnlPercent)})',
            color: pnlColor,
          ),
          const SizedBox(height: 8),
          _summaryRow(
            'Gerçekleşen kâr / zarar',
            formatMoney(v.realizedPnl),
            color: v.realizedPnl >= 0 ? AppColors.accent : AppColors.negative,
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value, {Color color = Colors.white}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(color: AppColors.muted, fontSize: 13),
        ),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: TextStyle(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildButtons() {
    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 48,
            child: OutlinedButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const DepositScreen()),
              ),
              style: OutlinedButton.styleFrom(
                backgroundColor: AppColors.accent.withValues(alpha: 0.12),
                foregroundColor: AppColors.accent,
                side: BorderSide(color: AppColors.accent.withValues(alpha: 0.5)),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: const Text(
                'Para Yatır',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: () => _openTrade(true),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.accent,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: const Text(
                'Hisse Al',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SizedBox(
            height: 48,
            child: OutlinedButton(
              onPressed: () => _openTrade(false),
              style: OutlinedButton.styleFrom(
                backgroundColor: AppColors.card,
                foregroundColor: Colors.white,
                side: const BorderSide(color: AppColors.border),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: const Text(
                'Hisse Sat',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildWarnings(List<String> warnings) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        warnings.join('\n'),
        style: const TextStyle(color: AppColors.warning, fontSize: 12),
      ),
    );
  }

  Widget _buildPositions(Valuation v) {
    if (v.positions.isEmpty) {
      return const EmptyBox(
        message: 'Henüz hisseniz yok. "Hisse Al" ile ilk işleminizi yapın.',
        icon: Icons.account_balance_wallet_outlined,
      );
    }
    final List<Widget> rows = [];
    for (int i = 0; i < v.positions.length; i++) {
      if (i > 0) rows.add(listDivider);
      rows.add(_buildPositionRow(v.positions[i]));
    }
    return CardBox(child: Column(children: rows));
  }

  Widget _buildPositionRow(ValuedPosition p) {
    final double? pnlPercent = p.unrealizedPnlPercent;
    final bool positive = (pnlPercent ?? 0) >= 0;
    return InkWell(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => StockDetailScreen(symbol: p.symbol)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(
          children: [
            SymbolBadge(symbol: p.symbol),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    p.symbol,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${p.quantity} adet · ort. ${formatMoney(p.averageCost)}',
                    style: const TextStyle(color: AppColors.muted, fontSize: 12),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  formatMoney(p.marketValue ?? p.costBasis),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  pnlPercent == null ? 'Fiyat yok' : formatPercent(pnlPercent),
                  style: TextStyle(
                    color: pnlPercent == null
                        ? AppColors.muted
                        : (positive ? AppColors.accent : AppColors.negative),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTrades() {
    final List<Trade>? trades = _trades?.data;
    if (trades == null) {
      return const EmptyBox(message: 'İşlem geçmişi alınamadı.');
    }
    if (trades.isEmpty) {
      return const EmptyBox(
        message: 'Henüz işlem yapmadınız.',
        icon: Icons.receipt_long_outlined,
      );
    }
    final List<Widget> rows = [];
    for (int i = 0; i < trades.length; i++) {
      if (i > 0) rows.add(listDivider);
      final Trade t = trades[i];
      rows.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: (t.isBuy ? AppColors.blue : AppColors.negative)
                      .withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  t.isBuy ? Icons.south_west_rounded : Icons.north_east_rounded,
                  color: t.isBuy ? const Color(0xFF60A5FA) : AppColors.negative,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${t.symbol} · ${t.isBuy ? 'Alış' : 'Satış'}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${t.quantity} adet × ${formatMoney(t.executionPrice)} · ${formatShortTime(t.executedAt)}',
                      style: const TextStyle(color: AppColors.muted, fontSize: 12),
                    ),
                  ],
                ),
              ),
              Text(
                formatMoney(t.grossAmount),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      );
    }
    return CardBox(child: Column(children: rows));
  }
}
