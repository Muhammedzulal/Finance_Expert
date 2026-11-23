import 'package:flutter/material.dart';

import '../data/settings_store.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'price_alerts_screen.dart';
import 'security_screen.dart' show SettingRow, settingsGroup;

/// Bildirim Ayarları ekranı (Furkan'ın tasarımı).
/// Seçimler cihazdaki Drift veritabanına kaydedilir.
class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends State<NotificationSettingsScreen> {
  static const Map<String, bool> _defaults = {
    'push': true,
    'email': true,
    'sms': false,
    'balance': true,
    'stock': true,
  };

  Map<String, bool> _values = Map<String, bool>.from(_defaults);
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    SettingsStore.read('notifications', _defaults).then((v) {
      if (mounted) setState(() => _values = v);
    });
  }

  void _set(String key, bool value) => setState(() => _values[key] = value);

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await SettingsStore.write('notifications', _values);
      if (!mounted) return;
      showAppSnack(context, 'Bildirim ayarlarınız kaydedildi.');
      Navigator.of(context).pop();
    } catch (_) {
      if (mounted) {
        showAppSnack(context, 'Ayarlar kaydedilemedi.', error: true);
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  const ScreenHeader(
                    title: 'Bildirim Ayarları',
                    leading: BackSquareButton(),
                    trailing: SizedBox.shrink(),
                  ),
                  const SizedBox(height: 22),
                  settingsGroup([
                    SettingRow(
                      icon: Icons.notifications_none_rounded,
                      title: 'Anlık Bildirimler',
                      subtitle: 'Uygulama içi uyarılar',
                      value: _values['push']!,
                      onChanged: (v) => _set('push', v),
                    ),
                    SettingRow(
                      icon: Icons.mail_outline_rounded,
                      title: 'E-posta Bildirimleri',
                      subtitle: 'E-posta özetleri',
                      value: _values['email']!,
                      onChanged: (v) => _set('email', v),
                    ),
                    SettingRow(
                      icon: Icons.smartphone_rounded,
                      title: 'SMS Bildirimleri',
                      subtitle: 'Telefonunuza kısa mesaj',
                      value: _values['sms']!,
                      onChanged: (v) => _set('sms', v),
                    ),
                  ]),
                  const SizedBox(height: 26),
                  const SectionTitle('Bildirim Kategorileri'),
                  const SizedBox(height: 12),
                  settingsGroup([
                    SettingRow(
                      icon: Icons.account_balance_wallet_outlined,
                      title: 'Bakiye Hareketleri',
                      subtitle: 'Para giriş ve çıkışları',
                      value: _values['balance']!,
                      onChanged: (v) => _set('balance', v),
                    ),
                  ]),
                  const SizedBox(height: 12),
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.card,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Column(
                      children: [
                        SettingRow(
                          icon: Icons.show_chart_rounded,
                          iconColor: const Color(0xFF60A5FA),
                          title: 'Hisse Uyarıları',
                          subtitle: 'Fiyat ve piyasa hareketleri',
                          value: _values['stock']!,
                          onChanged: (v) => _set('stock', v),
                        ),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                          child: SizedBox(
                            width: double.infinity,
                            height: 44,
                            child: OutlinedButton(
                              onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const PriceAlertsScreen(),
                                ),
                              ),
                              style: OutlinedButton.styleFrom(
                                backgroundColor: const Color(0xFF1E2E52),
                                side: const BorderSide(
                                  color: Color(0xFF2F4F8A),
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              child: const Text(
                                'Fiyat Uyarısı Yönet',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: AppColors.border)),
              ),
              child: SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.blue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: const Text(
                    'Kaydet',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
