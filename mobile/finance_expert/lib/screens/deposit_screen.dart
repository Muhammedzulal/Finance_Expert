import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_state.dart';
import '../data/finance_repository.dart';
import '../models/models.dart';
import '../services/api_client.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';

/// Para Yatır ekranı (Furkan'ın tasarımı).
///
/// Sanal cüzdana bakiye ekler. Kart bilgileri yalnızca biçim kontrolü için
/// kullanılır; hiçbir yere kaydedilmez ve gönderilmez. Gerçek ödeme alınmaz.
class DepositScreen extends StatefulWidget {
  const DepositScreen({super.key});

  @override
  State<DepositScreen> createState() => _DepositScreenState();
}

class _DepositScreenState extends State<DepositScreen> {
  final TextEditingController _amount = TextEditingController();
  final TextEditingController _name = TextEditingController();
  final TextEditingController _card = TextEditingController();
  final TextEditingController _expiry = TextEditingController();
  final TextEditingController _cvv = TextEditingController();

  double? _cash;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadBalance();
  }

  @override
  void dispose() {
    for (final TextEditingController c in [_amount, _name, _card, _expiry, _cvv]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _loadBalance() async {
    try {
      final Valuation v = (await FinanceRepository.instance.valuation()).data;
      if (mounted) setState(() => _cash = v.cashBalance);
    } catch (_) {}
  }

  /// "1.500,50" ve "1500.50" ikisi de 1500,50 olarak okunur.
  double? get _amountValue {
    final String raw = _amount.text.trim();
    final String normalized = raw.contains(',')
        ? raw.replaceAll('.', '').replaceAll(',', '.')
        : raw;
    return double.tryParse(normalized);
  }

  String? _validate() {
    final double? amount = _amountValue;
    if (amount == null || amount <= 0) return 'Geçerli bir tutar girin.';
    if (amount > 1000000) return 'Tek seferde en fazla 1.000.000 ₺ yatırılabilir.';
    if (_name.text.trim().length < 3) return 'Kart üzerindeki ismi girin.';
    if (_card.text.replaceAll(' ', '').length != 16) {
      return 'Kart numarası 16 haneli olmalı.';
    }
    if (!RegExp(r'^(0[1-9]|1[0-2])/\d{2}$').hasMatch(_expiry.text)) {
      return 'Son kullanma tarihini AA/YY biçiminde girin.';
    }
    if (_cvv.text.length != 3) return 'CVV 3 haneli olmalı.';
    return null;
  }

  Future<void> _submit() async {
    final String? problem = _validate();
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final double newBalance = await FinanceRepository.instance.deposit(
        _amountValue!,
      );
      AppEvents.portfolioChanged.value++;
      if (!mounted) return;
      setState(() => _cash = newBalance);
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: AppColors.card,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          title: const Row(
            children: [
              Icon(Icons.check_circle_rounded, color: AppColors.accent),
              SizedBox(width: 10),
              Text(
                'Bakiye eklendi',
                style: TextStyle(color: Colors.white, fontSize: 18),
              ),
            ],
          ),
          content: Text(
            '${formatMoney(_amountValue)} sanal cüzdanınıza eklendi.\n'
            'Yeni bakiye: ${formatMoney(newBalance)}',
            style: const TextStyle(color: AppColors.muted, height: 1.5),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text(
                'Tamam',
                style: TextStyle(color: AppColors.accent),
              ),
            ),
          ],
        ),
      );
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'İşlem tamamlanamadı, tekrar deneyin.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const ScreenHeader(
              title: 'Para Yatır',
              leading: BackSquareButton(),
              trailing: SizedBox.shrink(),
            ),
            const SizedBox(height: 22),
            _buildBalanceCard(),
            const SizedBox(height: 22),
            _label('Yatırılacak Tutar'),
            _field(
              _amount,
              hint: '0,00 ₺',
              keyboard: const TextInputType.numberWithOptions(decimal: true),
              formatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))],
            ),
            const SizedBox(height: 16),
            _label('Kart Üzerindeki İsim'),
            _field(
              _name,
              hint: 'Ad Soyad',
              capitalization: TextCapitalization.words,
            ),
            const SizedBox(height: 16),
            _label('Kart Numarası'),
            _field(
              _card,
              hint: '0000 0000 0000 0000',
              keyboard: TextInputType.number,
              formatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(16),
                _CardNumberFormatter(),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _label('Son Kullanma'),
                      _field(
                        _expiry,
                        hint: 'AA/YY',
                        keyboard: TextInputType.number,
                        formatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(4),
                          _ExpiryFormatter(),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _label('CVV'),
                      _field(
                        _cvv,
                        hint: '•••',
                        keyboard: TextInputType.number,
                        obscure: true,
                        formatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(3),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(
                _error!,
                style: const TextStyle(color: AppColors.negative, fontSize: 13),
              ),
            ],
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                onPressed: _submitting ? null : _submit,
                icon: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.lock_outline_rounded, size: 20),
                label: const Text(
                  'Ödemeyi Tamamla',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.accent,
                  disabledBackgroundColor: const Color(0xFF0E8F68),
                  foregroundColor: Colors.white,
                  disabledForegroundColor: Colors.white70,
                  elevation: 8,
                  shadowColor: AppColors.accent.withValues(alpha: 0.5),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Bu ekran demo amaçlıdır; gerçek ödeme alınmaz.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.muted, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBalanceCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1E3A6E), Color(0xFF142748)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderBlue),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.credit_card_rounded, color: AppColors.accent, size: 26),
              Spacer(),
              Text(
                'GÜVENLİ ÖDEME',
                style: TextStyle(
                  color: Color(0xFFCBD5E1),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          const Text(
            'Sanal cüzdan bakiyesi',
            style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 13),
          ),
          const SizedBox(height: 6),
          Text(
            _cash == null ? '—' : formatMoney(_cash),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
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
        fontWeight: FontWeight.w700,
      ),
    ),
  );

  Widget _field(
    TextEditingController controller, {
    required String hint,
    TextInputType? keyboard,
    List<TextInputFormatter>? formatters,
    TextCapitalization capitalization = TextCapitalization.none,
    bool obscure = false,
  }) {
    return TextField(
      controller: controller,
      keyboardType: keyboard,
      inputFormatters: formatters,
      textCapitalization: capitalization,
      obscureText: obscure,
      style: const TextStyle(color: Colors.white, fontSize: 15),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AppColors.subtle, fontSize: 14),
        filled: true,
        fillColor: AppColors.card,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
        ),
      ),
    );
  }
}

/// "1234567812345678" -> "1234 5678 1234 5678"
class _CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final String digits = newValue.text.replaceAll(' ', '');
    final StringBuffer b = StringBuffer();
    for (int i = 0; i < digits.length; i++) {
      if (i > 0 && i % 4 == 0) b.write(' ');
      b.write(digits[i]);
    }
    final String text = b.toString();
    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }
}

/// "1228" -> "12/28"
class _ExpiryFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final String digits = newValue.text.replaceAll('/', '');
    final String text = digits.length > 2
        ? '${digits.substring(0, 2)}/${digits.substring(2)}'
        : digits;
    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }
}
