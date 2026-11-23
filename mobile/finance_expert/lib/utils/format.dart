// Türkçe sayı ve tarih biçimlendirme yardımcıları (ek paket gerektirmez).

/// 1234567.5 -> "1.234.567,50 ₺"
String formatMoney(num? value, {String suffix = '₺', int decimals = 2}) {
  if (value == null) return '—';
  final bool negative = value < 0;
  final String fixed = value.abs().toStringAsFixed(decimals);
  final List<String> parts = fixed.split('.');
  final String intPart = parts[0];
  final StringBuffer grouped = StringBuffer();
  for (int i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 == 0) grouped.write('.');
    grouped.write(intPart[i]);
  }
  final String decimalPart = parts.length > 1 ? ',${parts[1]}' : '';
  final String sign = negative ? '-' : '';
  final String unit = suffix.isEmpty ? '' : ' $suffix';
  return '$sign$grouped$decimalPart$unit';
}

/// 3.456 -> "+%3,46"
String formatPercent(num? value) {
  if (value == null) return '—';
  final String sign = value > 0 ? '+' : (value < 0 ? '-' : '');
  return '$sign%${value.abs().toStringAsFixed(2).replaceAll('.', ',')}';
}

/// API sayıları metin olarak gönderir ("312.750000"); güvenle çevirir.
double? parseNum(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString());
}

DateTime? parseDate(dynamic value) {
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}

String _two(int n) => n.toString().padLeft(2, '0');

/// "03.11.2026 14:05"
String formatDateTime(DateTime? value) {
  if (value == null) return '—';
  final DateTime d = value.toLocal();
  return '${_two(d.day)}.${_two(d.month)}.${d.year} ${_two(d.hour)}:${_two(d.minute)}';
}

/// "14:05" bugünse, değilse "03.11 14:05"
String formatShortTime(DateTime? value) {
  if (value == null) return '—';
  final DateTime d = value.toLocal();
  final DateTime now = DateTime.now();
  final bool today =
      d.year == now.year && d.month == now.month && d.day == now.day;
  final String time = '${_two(d.hour)}:${_two(d.minute)}';
  return today ? time : '${_two(d.day)}.${_two(d.month)} $time';
}

/// Hisse kodunun ilk iki harfi: "THYAO" -> "TH"
String symbolShortCode(String symbol) =>
    symbol.length >= 2 ? symbol.substring(0, 2) : symbol;

/// "Eray Kırşan" -> "EK"
String initialsOf(String fullName) {
  final List<String> parts = fullName
      .trim()
      .split(RegExp(r'\s+'))
      .where((p) => p.isNotEmpty)
      .toList();
  if (parts.isEmpty) return '?';
  if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
  return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
      .toUpperCase();
}
