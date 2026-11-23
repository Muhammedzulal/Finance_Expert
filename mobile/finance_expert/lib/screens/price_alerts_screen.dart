import 'package:flutter/material.dart';

import '../data/finance_repository.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import '../services/price_alert_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import '../widgets/price_alert_sheet.dart';

/// Fiyat Uyarıları: kurulu alt/üst limit alarmları ve son tetiklenenler.
class PriceAlertsScreen extends StatefulWidget {
  const PriceAlertsScreen({super.key});

  @override
  State<PriceAlertsScreen> createState() => _PriceAlertsScreenState();
}

class _PriceAlertsScreenState extends State<PriceAlertsScreen> {
  final PriceAlertService _service = PriceAlertService.instance;
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    _service.addListener(_onChange);
    _service.load();
  }

  @override
  void dispose() {
    _service.removeListener(_onChange);
    super.dispose();
  }

  void _onChange() {
    if (mounted) setState(() {});
  }

  Future<void> _checkNow() async {
    setState(() => _checking = true);
    await _service.check();
    if (!mounted) return;
    setState(() => _checking = false);
    showAppSnack(context, 'Fiyatlar kontrol edildi.');
  }

  Future<void> _addAlert() async {
    final String? symbol = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: const Color(0xFF111A2E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (_) => const _StockPicker(),
    );
    if (symbol == null || !mounted) return;
    await showPriceAlertSheet(context, symbol: symbol);
  }

  @override
  Widget build(BuildContext context) {
    final List<PriceAlert> alerts = _service.alerts;
    final List<PriceAlertEvent> events = _service.events;
    return Scaffold(
      backgroundColor: AppColors.background,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addAlert,
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_alert_rounded),
        label: const Text(
          'Yeni Alarm',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.accent,
          onRefresh: _checkNow,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
            children: [
              ScreenHeader(
                title: 'Fiyat Uyarıları',
                leading: const BackSquareButton(),
                trailing: IconButton(
                  tooltip: 'Şimdi kontrol et',
                  onPressed: _checking ? null : _checkNow,
                  icon: _checking
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppColors.accent,
                          ),
                        )
                      : const Icon(Icons.refresh_rounded, color: Colors.white),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                _service.lastCheckAt == null
                    ? 'Fiyatlar her ${_service.interval.inSeconds} saniyede bir kontrol edilir.'
                    : 'Son kontrol: ${formatShortTime(_service.lastCheckAt)} · her ${_service.interval.inSeconds} sn',
                style: const TextStyle(color: AppColors.subtle, fontSize: 12),
              ),
              const SizedBox(height: 20),
              const SectionTitle('Kurulu Alarmlar'),
              const SizedBox(height: 12),
              if (alerts.isEmpty)
                const EmptyBox(
                  message:
                      'Henüz fiyat alarmı yok. Bir hisse için alt veya üst limit belirleyin.',
                  icon: Icons.notifications_none_rounded,
                )
              else
                ...alerts.map(_alertCard),
              const SizedBox(height: 26),
              const SectionTitle('Son Tetiklenenler'),
              const SizedBox(height: 12),
              if (events.isEmpty)
                const EmptyBox(
                  message: 'Henüz tetiklenen alarm yok.',
                  icon: Icons.history_rounded,
                )
              else
                CardBox(
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      for (int i = 0; i < events.length; i++) ...[
                        if (i > 0) listDivider,
                        _eventRow(events[i]),
                      ],
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _alertCard(PriceAlert a) {
    final double? last = _service.lastPrices[a.symbol];
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () => showPriceAlertSheet(
          context,
          symbol: a.symbol,
          currentPrice: last,
        ),
        child: CardBox(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  SymbolBadge(symbol: a.symbol),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          a.symbol,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          last != null
                              ? 'Son fiyat: ${formatMoney(last)}'
                              : a.basePrice != null
                              ? 'Kurulurken: ${formatMoney(a.basePrice)}'
                              : 'Fiyat bekleniyor',
                          style: const TextStyle(
                            color: AppColors.muted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: a.enabled,
                    activeTrackColor: AppColors.accent,
                    onChanged: (v) => _service.setEnabled(a.symbol, v),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _limitChip(
                      'Üst',
                      a.upper,
                      AppColors.accent,
                      a.upperHitAt,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _limitChip(
                      'Alt',
                      a.lower,
                      AppColors.negative,
                      a.lowerHitAt,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _limitChip(String label, double? value, Color color, DateTime? hit) {
    final bool off = value == null;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: off ? AppColors.chip : color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: off ? AppColors.border : color.withValues(alpha: 0.35),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$label limit',
            style: const TextStyle(color: AppColors.muted, fontSize: 11),
          ),
          const SizedBox(height: 4),
          Text(
            off ? '—' : formatMoney(value),
            style: TextStyle(
              color: off ? AppColors.subtle : Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (hit != null) ...[
            const SizedBox(height: 4),
            Text(
              'Tetiklendi · ${formatShortTime(hit)}',
              style: const TextStyle(color: AppColors.warning, fontSize: 11),
            ),
          ],
        ],
      ),
    );
  }

  Widget _eventRow(PriceAlertEvent e) {
    final Color color = e.isUpper ? AppColors.accent : AppColors.negative;
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(
              e.isUpper
                  ? Icons.trending_up_rounded
                  : Icons.trending_down_rounded,
              color: color,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  e.message,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  formatDateTime(e.at),
                  style: const TextStyle(color: AppColors.subtle, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Yeni alarm için hisse seçimi.
class _StockPicker extends StatefulWidget {
  const _StockPicker();

  @override
  State<_StockPicker> createState() => _StockPickerState();
}

class _StockPickerState extends State<_StockPicker> {
  List<Stock>? _stocks;
  String? _error;

  @override
  void initState() {
    super.initState();
    FinanceRepository.instance
        .stocks()
        .then((s) {
          if (mounted) setState(() => _stocks = s.data);
        })
        .catchError((Object e) {
          if (mounted) setState(() => _error = e.toString());
        });
  }

  @override
  Widget build(BuildContext context) {
    final List<Stock>? stocks = _stocks;
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.6,
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Hisse seçin',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 14),
              if (_error != null)
                Text(_error!, style: const TextStyle(color: AppColors.negative))
              else if (stocks == null)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.accent),
                  ),
                )
              else if (stocks.isEmpty)
                const Text(
                  'Backend’de kayıtlı hisse yok.',
                  style: TextStyle(color: AppColors.muted),
                )
              else
                Flexible(
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: stocks.length,
                    separatorBuilder: (_, _) => listDivider,
                    itemBuilder: (_, i) {
                      final Stock s = stocks[i];
                      return ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: SymbolBadge(symbol: s.symbol),
                        title: Text(
                          s.symbol,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        subtitle: Text(
                          s.companyName,
                          style: const TextStyle(color: AppColors.muted),
                        ),
                        trailing: PriceAlertService.instance.alertFor(
                                  s.symbol,
                                ) !=
                                null
                            ? const Icon(
                                Icons.notifications_active_rounded,
                                color: AppColors.warning,
                                size: 20,
                              )
                            : null,
                        onTap: () => Navigator.of(context).pop(s.symbol),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
