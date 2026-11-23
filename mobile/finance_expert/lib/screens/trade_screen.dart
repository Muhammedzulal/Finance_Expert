import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_state.dart';
import '../data/finance_repository.dart';
import '../models/models.dart';
import '../services/api_client.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';

/// Hisse İşlemleri (Al/Sat) — POST /api/v1/wallets/{id}/trades
class TradeScreen extends StatefulWidget {
  final String? initialSymbol;
  final bool initialIsBuy;

  const TradeScreen({super.key, this.initialSymbol, this.initialIsBuy = true});

  @override
  State<TradeScreen> createState() => _TradeScreenState();
}

class _TradeScreenState extends State<TradeScreen> {
  final FinanceRepository _repo = FinanceRepository.instance;
  final TextEditingController _quantityController = TextEditingController(
    text: '1',
  );

  late bool _isBuy = widget.initialIsBuy;
  List<Stock> _stocks = const [];
  String? _symbol;
  Quote? _quote;
  Valuation? _valuation;
  bool _loading = true;
  bool _loadingQuote = false;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _symbol = widget.initialSymbol;
    _quantityController.addListener(() => setState(() {}));
    _load();
  }

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final Loaded<List<Stock>> stocks = await _repo.stocks();
      Valuation? valuation;
      try {
        valuation = (await _repo.valuation()).data;
      } catch (_) {
        valuation = null;
      }
      if (!mounted) return;
      setState(() {
        _stocks = stocks.data.where((s) => s.isActive).toList();
        _valuation = valuation;
        if (_symbol == null && _stocks.isNotEmpty) {
          _symbol = _stocks.first.symbol;
        }
      });
      await _loadQuote();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadQuote() async {
    final String? symbol = _symbol;
    if (symbol == null) return;
    setState(() => _loadingQuote = true);
    try {
      final Loaded<Quote?> q = await _repo.quote(symbol);
      if (!mounted || symbol != _symbol) return;
      setState(() => _quote = q.data);
    } catch (_) {
      if (!mounted) return;
      setState(() => _quote = null);
    } finally {
      if (mounted) setState(() => _loadingQuote = false);
    }
  }

  int get _quantity => int.tryParse(_quantityController.text.trim()) ?? 0;

  double? get _estimatedAmount =>
      _quote == null ? null : _quote!.price * _quantity;

  int get _ownedQuantity =>
      _symbol == null ? 0 : (_valuation?.quantityOf(_symbol!) ?? 0);

  /// Sunucuya göndermeden önceki basit kontroller (sunucu da kontrol eder).
  String? get _localProblem {
    if (_symbol == null) return 'Bir hisse seçin.';
    if (_quantity <= 0) return 'Adet en az 1 olmalı.';
    if (_quote == null) return 'Bu hisse için fiyat yok; işlem yapılamaz.';
    final double? amount = _estimatedAmount;
    if (_isBuy &&
        _valuation != null &&
        amount != null &&
        amount > _valuation!.cashBalance) {
      return 'Yetersiz bakiye: kullanılabilir nakit ${formatMoney(_valuation!.cashBalance)}.';
    }
    if (!_isBuy && _valuation != null && _quantity > _ownedQuantity) {
      return 'Yetersiz hisse: portföyünüzde $_ownedQuantity adet var.';
    }
    return null;
  }

  Future<void> _submit() async {
    final String? problem = _localProblem;
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final Trade trade = await _repo.placeTrade(
        symbol: _symbol!,
        isBuy: _isBuy,
        quantity: _quantity,
      );
      AppEvents.portfolioChanged.value++;
      if (!mounted) return;
      await _showSuccess(trade);
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'İşlem gerçekleştirilemedi, tekrar deneyin.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _showSuccess(Trade trade) {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: AppColors.accent),
            const SizedBox(width: 10),
            Text(
              trade.isBuy ? 'Alım gerçekleşti' : 'Satış gerçekleşti',
              style: const TextStyle(color: Colors.white, fontSize: 18),
            ),
          ],
        ),
        content: Text(
          '${trade.quantity} adet ${trade.symbol}\n'
          'Fiyat: ${formatMoney(trade.executionPrice)}\n'
          'Tutar: ${formatMoney(trade.grossAmount)}',
          style: const TextStyle(color: AppColors.muted, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text(
              'Tamam',
              style: TextStyle(color: AppColors.accent),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: _loading && _stocks.isEmpty
            ? const LoadingBox(height: 400)
            : ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const ScreenHeader(
                    title: 'Hisse İşlemleri',
                    leading: BackSquareButton(),
                    trailing: SizedBox.shrink(),
                  ),
                  const SizedBox(height: 22),
                  _buildActiveCard(),
                  const SizedBox(height: 18),
                  _buildSideSwitch(),
                  const SizedBox(height: 22),
                  _label('Hisse Seçin'),
                  _buildSymbolPicker(),
                  const SizedBox(height: 18),
                  _label('Adet / Lot'),
                  _buildQuantityField(),
                  const SizedBox(height: 18),
                  _buildSummary(),
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
                  const SizedBox(height: 22),
                  _buildSubmitButton(),
                  const SizedBox(height: 12),
                  const Text(
                    'Sanal işlemdir; gerçek para kullanılmaz. Yatırım tavsiyesi değildir.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.subtle, fontSize: 12),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      text,
      style: const TextStyle(
        color: Colors.white,
        fontSize: 13,
        fontWeight: FontWeight.w600,
      ),
    ),
  );

  Widget _buildActiveCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.blue,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.show_chart_rounded, color: Colors.white),
          ),
          const SizedBox(width: 14),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Aktif İşlem',
                style: TextStyle(color: Color(0xFFD6E4FF), fontSize: 12),
              ),
              SizedBox(height: 2),
              Text(
                'Hisse Alım & Satım',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSideSwitch() {
    Widget option(String text, bool buy) {
      final bool selected = _isBuy == buy;
      return Expanded(
        child: GestureDetector(
          onTap: () => setState(() {
            _isBuy = buy;
            _error = null;
          }),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected ? AppColors.blue : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              text,
              style: TextStyle(
                color: selected ? Colors.white : AppColors.muted,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(children: [option('Al', true), option('Sat', false)]),
    );
  }

  Widget _buildSymbolPicker() {
    if (_stocks.isEmpty) {
      return ErrorBox(
        message: _error ?? 'Hisse listesi alınamadı.',
        onRetry: _load,
      );
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF13214A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.borderBlue),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _stocks.any((s) => s.symbol == _symbol) ? _symbol : null,
          isExpanded: true,
          dropdownColor: AppColors.card,
          iconEnabledColor: Colors.white,
          hint: const Text(
            'Hisse seçin',
            style: TextStyle(color: AppColors.subtle),
          ),
          items: _stocks
              .map(
                (s) => DropdownMenuItem<String>(
                  value: s.symbol,
                  child: Text(
                    '${s.symbol} · ${s.companyName}',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                  ),
                ),
              )
              .toList(),
          onChanged: (value) {
            setState(() {
              _symbol = value;
              _quote = null;
              _error = null;
            });
            _loadQuote();
          },
        ),
      ),
    );
  }

  Widget _buildQuantityField() {
    return TextField(
      controller: _quantityController,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: const TextStyle(color: Colors.white, fontSize: 16),
      decoration: InputDecoration(
        filled: true,
        fillColor: AppColors.card,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.blue, width: 1.5),
        ),
      ),
    );
  }

  Widget _buildSummary() {
    Widget row(String label, String value, {Color color = Colors.white}) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(color: AppColors.muted, fontSize: 13),
            ),
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      );
    }

    final String priceText = _loadingQuote
        ? 'Yükleniyor...'
        : (_quote == null ? 'Fiyat yok' : formatMoney(_quote!.price));

    return CardBox(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Column(
        children: [
          row('Güncel fiyat', priceText),
          row(
            'İşlem türü',
            _isBuy ? 'Al' : 'Sat',
            color: _isBuy ? const Color(0xFF60A5FA) : AppColors.negative,
          ),
          row('Tahmini tutar', formatMoney(_estimatedAmount)),
          if (_valuation != null)
            _isBuy
                ? row(
                    'Kullanılabilir nakit',
                    formatMoney(_valuation!.cashBalance),
                  )
                : row('Portföydeki adet', '$_ownedQuantity adet'),
        ],
      ),
    );
  }

  Widget _buildSubmitButton() {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: ElevatedButton.icon(
        onPressed: _submitting || _loadingQuote ? null : _submit,
        icon: _submitting
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.show_chart_rounded, size: 20),
        label: Text(
          _isBuy ? 'Al Emrini Onayla' : 'Sat Emrini Onayla',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.blue,
          disabledBackgroundColor: const Color(0xFF1E40AF),
          foregroundColor: Colors.white,
          disabledForegroundColor: Colors.white70,
          elevation: 8,
          shadowColor: AppColors.blue.withValues(alpha: 0.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
    );
  }
}
