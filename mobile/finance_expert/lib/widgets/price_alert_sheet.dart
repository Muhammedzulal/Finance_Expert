import 'package:flutter/material.dart';

import '../data/finance_repository.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import '../services/price_alert_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import 'common.dart';

/// Bir hisse için alt / üst fiyat limiti kurma paneli.
/// [currentPrice] verilmezse son fiyat API'den alınır.
Future<void> showPriceAlertSheet(
  BuildContext context, {
  required String symbol,
  double? currentPrice,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    barrierColor: Colors.black.withValues(alpha: 0.55),
    builder: (_) => _PriceAlertSheet(symbol: symbol, currentPrice: currentPrice),
  );
}

/// "245,50" ve "245.50" girişlerini kabul eder.
double? parsePriceInput(String text) {
  String s = text.trim().replaceAll('₺', '').replaceAll(' ', '');
  if (s.isEmpty) return null;
  if (s.contains(',')) s = s.replaceAll('.', '').replaceAll(',', '.');
  return double.tryParse(s);
}

String _inputText(double? v) =>
    v == null ? '' : v.toStringAsFixed(2).replaceAll('.', ',');

class _PriceAlertSheet extends StatefulWidget {
  final String symbol;
  final double? currentPrice;

  const _PriceAlertSheet({required this.symbol, this.currentPrice});

  @override
  State<_PriceAlertSheet> createState() => _PriceAlertSheetState();
}

class _PriceAlertSheetState extends State<_PriceAlertSheet> {
  final PriceAlertService _service = PriceAlertService.instance;
  final TextEditingController _lower = TextEditingController();
  final TextEditingController _upper = TextEditingController();
  double? _price;
  bool _loadingPrice = false;
  bool _saving = false;
  String? _error;
  PriceAlert? _existing;

  @override
  void initState() {
    super.initState();
    _price = widget.currentPrice;
    _existing = _service.alertFor(widget.symbol);
    _lower.text = _inputText(_existing?.lower);
    _upper.text = _inputText(_existing?.upper);
    if (_price == null) _loadPrice();
  }

  Future<void> _loadPrice() async {
    setState(() => _loadingPrice = true);
    try {
      final Loaded<Quote?> q = await FinanceRepository.instance.quote(
        widget.symbol,
      );
      if (mounted) setState(() => _price = q.data?.price);
    } catch (_) {
      // Fiyat olmadan da limit girilebilir.
    } finally {
      if (mounted) setState(() => _loadingPrice = false);
    }
  }

  void _fillPercent(TextEditingController c, double percent) {
    final double? p = _price;
    if (p == null) return;
    c.text = _inputText(p * (1 + percent / 100));
    setState(() => _error = null);
  }

  Future<void> _save() async {
    final double? lower = parsePriceInput(_lower.text);
    final double? upper = parsePriceInput(_upper.text);
    String? error;
    if (_lower.text.trim().isNotEmpty && (lower == null || lower <= 0)) {
      error = 'Alt limit geçerli bir fiyat olmalı.';
    } else if (_upper.text.trim().isNotEmpty && (upper == null || upper <= 0)) {
      error = 'Üst limit geçerli bir fiyat olmalı.';
    } else if (lower == null && upper == null) {
      error = 'En az bir limit girin.';
    } else if (lower != null && upper != null && lower >= upper) {
      error = 'Alt limit üst limitten küçük olmalı.';
    } else if (_price != null && upper != null && upper <= _price!) {
      error = 'Üst limit güncel fiyatın (${formatMoney(_price)}) üzerinde olmalı.';
    } else if (_price != null && lower != null && lower >= _price!) {
      error = 'Alt limit güncel fiyatın (${formatMoney(_price)}) altında olmalı.';
    }
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    setState(() => _saving = true);
    await _service.save(
      symbol: widget.symbol,
      lower: lower,
      upper: upper,
      basePrice: _price,
    );
    if (!mounted) return;
    showAppSnack(context, '${widget.symbol} fiyat alarmı kaydedildi.');
    Navigator.of(context).pop();
  }

  Future<void> _delete() async {
    await _service.remove(widget.symbol);
    if (!mounted) return;
    showAppSnack(context, '${widget.symbol} fiyat alarmı silindi.');
    Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _lower.dispose();
    _upper.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        decoration: const BoxDecoration(
          color: Color(0xFF111A2E),
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 44,
                    height: 5,
                    decoration: BoxDecoration(
                      color: const Color(0xFF475569),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    SymbolBadge(symbol: widget.symbol),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${widget.symbol} Fiyat Alarmı',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _loadingPrice
                                ? 'Güncel fiyat alınıyor…'
                                : _price == null
                                ? 'Güncel fiyat bilinmiyor'
                                : 'Güncel fiyat: ${formatMoney(_price)}',
                            style: const TextStyle(
                              color: AppColors.muted,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                _limitField(
                  label: 'Üst limit',
                  hint: 'Fiyat bu değere çıkınca bildir',
                  icon: Icons.trending_up_rounded,
                  color: AppColors.accent,
                  controller: _upper,
                  hitAt: _existing?.upperHitAt,
                  quick: const [1, 3, 5],
                ),
                const SizedBox(height: 18),
                _limitField(
                  label: 'Alt limit',
                  hint: 'Fiyat bu değere düşünce bildir',
                  icon: Icons.trending_down_rounded,
                  color: AppColors.negative,
                  controller: _lower,
                  hitAt: _existing?.lowerHitAt,
                  quick: const [-1, -3, -5],
                ),
                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Text(
                    _error!,
                    style: const TextStyle(
                      color: AppColors.negative,
                      fontSize: 13,
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                const Text(
                  'Uygulama açıkken fiyat düzenli olarak kontrol edilir. '
                  'Limit aşılınca bildirim gelir ve o limit kapanır; '
                  'tekrar kaydederek yeniden kurabilirsiniz.',
                  style: TextStyle(color: AppColors.subtle, fontSize: 12),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    if (_existing != null) ...[
                      Expanded(
                        child: SizedBox(
                          height: 52,
                          child: OutlinedButton(
                            onPressed: _saving ? null : _delete,
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: AppColors.negative),
                              foregroundColor: AppColors.negative,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                            child: const Text(
                              'Alarmı Sil',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                    ],
                    Expanded(
                      flex: 2,
                      child: SizedBox(
                        height: 52,
                        child: ElevatedButton(
                          onPressed: _saving ? null : _save,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.accent,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                          child: Text(
                            _existing == null ? 'Alarmı Kur' : 'Alarmı Güncelle',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _limitField({
    required String label,
    required String hint,
    required IconData icon,
    required Color color,
    required TextEditingController controller,
    required DateTime? hitAt,
    required List<double> quick,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (hitAt != null) ...[
              const SizedBox(width: 8),
              const Pill(text: 'Tetiklendi', color: AppColors.warning),
            ],
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          onChanged: (_) {
            if (_error != null) setState(() => _error = null);
          },
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: AppColors.subtle, fontSize: 14),
            prefixIcon: Icon(icon, color: color, size: 20),
            suffixText: '₺',
            suffixStyle: const TextStyle(color: AppColors.muted),
            filled: true,
            fillColor: AppColors.card,
            contentPadding: const EdgeInsets.symmetric(vertical: 16),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.border),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: color, width: 1.5),
            ),
          ),
        ),
        if (_price != null) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final double p in quick)
                ActionChip(
                  label: Text(p > 0 ? '+%${p.toInt()}' : '-%${(-p).toInt()}'),
                  labelStyle: TextStyle(
                    color: color,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                  backgroundColor: color.withValues(alpha: 0.12),
                  side: BorderSide(color: color.withValues(alpha: 0.35)),
                  onPressed: () => _fillPercent(controller, p),
                ),
              ActionChip(
                label: const Text('Temizle'),
                labelStyle: const TextStyle(
                  color: AppColors.muted,
                  fontSize: 12,
                ),
                backgroundColor: AppColors.chip,
                side: const BorderSide(color: AppColors.border),
                onPressed: () => setState(() => controller.clear()),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
