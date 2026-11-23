import 'package:flutter/material.dart';

import '../data/finance_repository.dart';
import '../models/models.dart';
import '../models/price_alert.dart';
import '../services/price_alert_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';

/// Bildirimler paneli (alttan açılan sayfa).
/// Son işlemlerden bildirim üretilir; işlem yoksa karşılama bildirimi görünür.
Future<void> showNotificationsSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    barrierColor: Colors.black.withValues(alpha: 0.55),
    builder: (_) => const _NotificationsSheet(),
  );
}

class _NotificationItem {
  final IconData icon;
  final Color color;
  final String text;
  final String time;
  final bool unread;

  const _NotificationItem({
    required this.icon,
    required this.color,
    required this.text,
    required this.time,
    this.unread = false,
  });
}

class _NotificationsSheet extends StatefulWidget {
  const _NotificationsSheet();

  @override
  State<_NotificationsSheet> createState() => _NotificationsSheetState();
}

class _NotificationsSheetState extends State<_NotificationsSheet> {
  List<_NotificationItem>? _items;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _ago(DateTime? t) {
    if (t == null) return '';
    final Duration d = DateTime.now().difference(t.toLocal());
    if (d.inMinutes < 1) return 'Az önce';
    if (d.inMinutes < 60) return '${d.inMinutes} dk önce';
    if (d.inHours < 24) return '${d.inHours} saat önce';
    if (d.inDays == 1) return 'Dün';
    return '${d.inDays} gün önce';
  }

  Future<void> _load() async {
    final List<_NotificationItem> items = [];
    final PriceAlertService alerts = PriceAlertService.instance;
    await alerts.load();
    for (final PriceAlertEvent e in alerts.events.take(10)) {
      items.add(
        _NotificationItem(
          icon: e.isUpper
              ? Icons.trending_up_rounded
              : Icons.trending_down_rounded,
          color: e.isUpper ? AppColors.accent : AppColors.negative,
          text: e.message,
          time: _ago(e.at),
          unread: !e.read,
        ),
      );
    }
    // Panel açıldığında fiyat alarmı bildirimleri okundu sayılır.
    await alerts.markAllRead();
    final bool hadAlerts = items.isNotEmpty;
    try {
      final List<Trade> trades =
          (await FinanceRepository.instance.trades(limit: 5)).data;
      for (int i = 0; i < trades.length; i++) {
        final Trade t = trades[i];
        items.add(
          _NotificationItem(
            icon: Icons.account_balance_wallet_outlined,
            color: t.isBuy ? AppColors.blue : AppColors.negative,
            text:
                '${t.quantity} adet ${t.symbol} hisse ${t.isBuy ? 'alım' : 'satış'} emriniz gerçekleşti (${formatMoney(t.grossAmount)}).',
            time: _ago(t.executedAt),
            unread: !hadAlerts && i < 3,
          ),
        );
      }
    } catch (_) {
      // İşlem geçmişi alınamazsa sadece genel bildirimler gösterilir.
    }
    items.add(
      const _NotificationItem(
        icon: Icons.check_rounded,
        color: AppColors.accent,
        text: 'Hesabınıza ₺100.000 sanal bakiye tanımlandı.',
        time: 'Hesap açılışı',
        unread: false,
      ),
    );
    items.add(
      const _NotificationItem(
        icon: Icons.lock_outline_rounded,
        color: AppColors.warning,
        text: 'Hesabınıza bu cihazdan giriş yapıldı.',
        time: 'Bu oturum',
      ),
    );
    if (mounted) setState(() => _items = items);
  }

  @override
  Widget build(BuildContext context) {
    final List<_NotificationItem>? items = _items;
    final int unread = items?.where((i) => i.unread).length ?? 0;
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.75,
      ),
      decoration: const BoxDecoration(
        color: Color(0xFF111A2E),
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
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
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Bildirimler',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      unread == 0
                          ? 'Okunmamış bildiriminiz yok'
                          : '$unread okunmamış bildiriminiz var',
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
              InkWell(
                onTap: () => Navigator.of(context).pop(),
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: AppColors.chip,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: const Icon(Icons.close_rounded, color: Colors.white),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (items == null)
            const Padding(
              padding: EdgeInsets.all(30),
              child: Center(
                child: CircularProgressIndicator(color: AppColors.accent),
              ),
            )
          else
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (_, i) => _buildItem(items[i]),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildItem(_NotificationItem item) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 12,
            child: item.unread
                ? Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color: item.color,
                      shape: BoxShape.circle,
                    ),
                  )
                : null,
          ),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: item.color.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(item.icon, color: item.color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.text,
                  style: TextStyle(
                    color: item.unread ? Colors.white : const Color(0xFFCBD5E1),
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    height: 1.35,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  item.time,
                  style: const TextStyle(color: AppColors.muted, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
