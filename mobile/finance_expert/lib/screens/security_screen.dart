import 'package:flutter/material.dart';

import '../config.dart';
import '../data/settings_store.dart';
import '../services/auth_service.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';
import 'login_screen.dart';

/// Ayar ekranlarında kullanılan simgeli, anahtarlı satır.
class SettingRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String? subtitle;
  final bool? value;
  final ValueChanged<bool>? onChanged;
  final VoidCallback? onTap;

  const SettingRow({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.value,
    this.onChanged,
    this.onTap,
    this.iconColor = AppColors.accent,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap ?? (value == null ? null : () => onChanged?.call(!value!)),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: 3),
                    Text(
                      subtitle!,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (value != null)
              Switch(
                value: value!,
                onChanged: onChanged,
                thumbColor: const WidgetStatePropertyAll(Colors.white),
                activeTrackColor: AppColors.accent,
                inactiveTrackColor: const Color(0xFF475569),
                trackOutlineColor: const WidgetStatePropertyAll(
                  Colors.transparent,
                ),
              )
            else
              const Icon(
                Icons.chevron_right_rounded,
                color: AppColors.subtle,
              ),
          ],
        ),
      ),
    );
  }
}

/// Satırları tek kart içinde, aralarında çizgiyle gösterir.
Widget settingsGroup(List<Widget> rows) {
  final List<Widget> children = [];
  for (int i = 0; i < rows.length; i++) {
    if (i > 0) children.add(listDivider);
    children.add(rows[i]);
  }
  return Container(
    decoration: BoxDecoration(
      color: AppColors.card,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: AppColors.border),
    ),
    clipBehavior: Clip.antiAlias,
    child: Column(children: children),
  );
}

/// Güvenlik ekranı (Furkan'ın tasarımı).
class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});

  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
  static const Map<String, bool> _defaults = {'twoFactor': true, 'faceId': false};

  Map<String, bool> _values = Map<String, bool>.from(_defaults);

  @override
  void initState() {
    super.initState();
    SettingsStore.read('security', _defaults).then((v) {
      if (mounted) setState(() => _values = v);
    });
  }

  Future<void> _set(String key, bool value) async {
    setState(() => _values[key] = value);
    try {
      await SettingsStore.write('security', _values);
    } catch (_) {}
  }

  bool get _high => _values['twoFactor']!;

  Future<void> _logoutAll() async {
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text(
          'Tüm cihazlardan çıkış',
          style: TextStyle(color: Colors.white, fontSize: 18),
        ),
        content: const Text(
          'Bu cihaz dahil tüm oturumlarınız kapatılacak. Devam edilsin mi?',
          style: TextStyle(color: AppColors.muted, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Vazgeç', style: TextStyle(color: AppColors.muted)),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text(
              'Çıkış yap',
              style: TextStyle(color: AppColors.negative),
            ),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await AuthService.instance.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final Color levelColor = _high ? AppColors.accent : AppColors.warning;
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const ScreenHeader(
              title: 'Güvenlik',
              leading: BackSquareButton(),
              trailing: SizedBox.shrink(),
            ),
            const SizedBox(height: 22),
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: levelColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: levelColor.withValues(alpha: 0.6)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: levelColor,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.verified_user_outlined,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Güvenlik Seviyesi',
                        style: TextStyle(color: levelColor, fontSize: 12),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        _high ? 'Yüksek' : 'Orta',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            settingsGroup([
              SettingRow(
                icon: Icons.lock_outline_rounded,
                iconColor: const Color(0xFF60A5FA),
                title: 'Şifre Değiştir',
                onTap: () => showAppSnack(
                  context,
                  'Şifre değiştirme özelliği yakında eklenecek.',
                ),
              ),
              SettingRow(
                icon: Icons.verified_user_outlined,
                title: '2FA Doğrulama',
                subtitle: 'İki adımlı doğrulama',
                value: _values['twoFactor']!,
                onChanged: (v) => _set('twoFactor', v),
              ),
              SettingRow(
                icon: Icons.face_retouching_natural,
                title: 'Face ID',
                subtitle: 'Biyometrik giriş',
                value: _values['faceId']!,
                onChanged: (v) => _set('faceId', v),
              ),
            ]),
            const SizedBox(height: 26),
            Row(
              children: [
                const Expanded(child: SectionTitle('Aktif Cihazlar')),
                TextButton(
                  onPressed: _logoutAll,
                  child: const Text(
                    'Tüm Cihazlardan Çıkış Yap',
                    style: TextStyle(
                      color: Color(0xFFFB7185),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            settingsGroup([
              const _DeviceRow(
                icon: Icons.smartphone_rounded,
                name: 'Bu cihaz',
                detail: 'Şu an aktif',
              ),
              if (AppConfig.demoMode)
                const _DeviceRow(
                  icon: Icons.laptop_mac_rounded,
                  name: 'MacBook Pro',
                  detail: 'İstanbul · 2 saat önce',
                ),
            ]),
          ],
        ),
      ),
    );
  }
}

class _DeviceRow extends StatelessWidget {
  final IconData icon;
  final String name;
  final String detail;

  const _DeviceRow({
    required this.icon,
    required this.name,
    required this.detail,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.chip,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: AppColors.muted, size: 20),
          ),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                name,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                detail,
                style: const TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
