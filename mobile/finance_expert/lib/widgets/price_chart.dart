import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';

/// Fiyat geçmişini çizen basit çizgi grafik (ek paket gerektirmez).
class PriceChart extends StatelessWidget {
  final List<Quote> points;
  final double height;

  const PriceChart({super.key, required this.points, this.height = 180});

  @override
  Widget build(BuildContext context) {
    if (points.length < 2) {
      return SizedBox(
        height: height,
        child: const Center(
          child: Text(
            'Grafik için yeterli fiyat verisi yok.',
            style: TextStyle(color: AppColors.muted, fontSize: 13),
          ),
        ),
      );
    }
    final List<double> prices = points.map((p) => p.price).toList();
    final double minPrice = prices.reduce(math.min);
    final double maxPrice = prices.reduce(math.max);
    final bool up = prices.last >= prices.first;
    final Color lineColor = up ? AppColors.accent : AppColors.negative;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: height,
          width: double.infinity,
          child: CustomPaint(
            painter: _LinePainter(
              prices: prices,
              minPrice: minPrice,
              maxPrice: maxPrice,
              color: lineColor,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              formatShortTime(points.first.asOf),
              style: const TextStyle(color: AppColors.subtle, fontSize: 11),
            ),
            Text(
              'En düşük ${formatMoney(minPrice, suffix: '')} · En yüksek ${formatMoney(maxPrice, suffix: '')}',
              style: const TextStyle(color: AppColors.subtle, fontSize: 11),
            ),
            Text(
              formatShortTime(points.last.asOf),
              style: const TextStyle(color: AppColors.subtle, fontSize: 11),
            ),
          ],
        ),
      ],
    );
  }
}

class _LinePainter extends CustomPainter {
  final List<double> prices;
  final double minPrice;
  final double maxPrice;
  final Color color;

  _LinePainter({
    required this.prices,
    required this.minPrice,
    required this.maxPrice,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final double range = (maxPrice - minPrice).abs() < 1e-9
        ? 1
        : maxPrice - minPrice;
    const double padding = 6;
    final double usableHeight = size.height - padding * 2;

    Offset pointAt(int i) {
      final double x = prices.length == 1
          ? 0
          : size.width * i / (prices.length - 1);
      final double y =
          padding + usableHeight * (1 - (prices[i] - minPrice) / range);
      return Offset(x, y);
    }

    // Yatay kılavuz çizgileri
    final Paint grid = Paint()
      ..color = AppColors.border
      ..strokeWidth = 1;
    for (int i = 0; i < 4; i++) {
      final double y = padding + usableHeight * i / 3;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }

    final Path line = Path()..moveTo(pointAt(0).dx, pointAt(0).dy);
    for (int i = 1; i < prices.length; i++) {
      line.lineTo(pointAt(i).dx, pointAt(i).dy);
    }

    final Path area = Path.from(line)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    final Paint fill = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [color.withValues(alpha: 0.28), color.withValues(alpha: 0.0)],
      ).createShader(Offset.zero & size);
    canvas.drawPath(area, fill);

    final Paint stroke = Paint()
      ..color = color
      ..strokeWidth = 2.4
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(line, stroke);

    final Offset last = pointAt(prices.length - 1);
    canvas.drawCircle(last, 4.5, Paint()..color = color);
  }

  @override
  bool shouldRepaint(covariant _LinePainter old) =>
      old.prices != prices || old.color != color;
}
