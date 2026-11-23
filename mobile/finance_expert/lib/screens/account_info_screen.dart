import 'package:flutter/material.dart';

import '../config.dart';
import '../models/models.dart';
import '../services/auth_service.dart';
import '../theme/app_colors.dart';
import '../utils/format.dart';
import '../widgets/common.dart';

/// Hesap Bilgileri ekranı (Furkan'ın tasarımı).
///
/// Ad ve e-posta backend'den gelir. Kimlik, telefon ve banka bilgisi için
/// backend'de henüz alan olmadığından demo modunda örnek (maskeli) değerler,
/// gerçek modda "Eklenmedi" gösterilir.
class AccountInfoScreen extends StatelessWidget {
  const AccountInfoScreen({super.key});

  void _soon(BuildContext context) =>
      showAppSnack(context, 'Bu bilgiyi düzenleme özelliği yakında eklenecek.');

  Future<void> _confirmDelete(BuildContext context) async {
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text(
          'Hesabı sil',
          style: TextStyle(color: Colors.white, fontSize: 18),
        ),
        content: const Text(
          'Hesabınız ve sanal cüzdanınız kalıcı olarak silinecek. Emin misiniz?',
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
              'Sil',
              style: TextStyle(color: AppColors.negative),
            ),
          ),
        ],
      ),
    );
    if (ok == true && context.mounted) {
      showAppSnack(
        context,
        'Hesap silme işlemi henüz backend’de desteklenmiyor.',
        error: true,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final UserProfile? user = AuthService.instance.currentUser;
    final String name = user?.fullName ?? 'Kullanıcı';
    final bool demo = AppConfig.demoMode;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const ScreenHeader(
              title: 'Hesap Bilgileri',
              leading: BackSquareButton(),
              trailing: SizedBox.shrink(),
            ),
            const SizedBox(height: 26),
            Center(
              child: Container(
                width: 88,
                height: 88,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF1E2B4A),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: AppColors.accent, width: 2.5),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.accent.withValues(alpha: 0.25),
                      blurRadius: 18,
                    ),
                  ],
                ),
                child: Text(
                  initialsOf(name),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Center(
              child: Text(
                name,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Center(
              child: Pill(
                text: 'Onaylı Hesap',
                color: AppColors.accent,
                icon: Icons.check_rounded,
              ),
            ),
            const SizedBox(height: 24),
            _infoRow(
              context,
              icon: Icons.person_outline_rounded,
              label: 'T.C. Kimlik No',
              value: demo ? '12•••••••34' : 'Eklenmedi',
            ),
            const SizedBox(height: 12),
            _infoRow(
              context,
              icon: Icons.smartphone_rounded,
              label: 'Telefon',
              value: demo ? '+90 5•• ••• •• 42' : 'Eklenmedi',
            ),
            const SizedBox(height: 12),
            _infoRow(
              context,
              icon: Icons.mail_outline_rounded,
              label: 'E-posta',
              value: user?.email ?? '—',
            ),
            const SizedBox(height: 26),
            const SectionTitle('Bağlı Banka Hesapları'),
            const SizedBox(height: 12),
            if (demo)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: _cardDecoration(),
                child: const Row(
                  children: [
                    _IconBox(
                      icon: Icons.credit_card_rounded,
                      color: Color(0xFF60A5FA),
                    ),
                    SizedBox(width: 14),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Garanti BBVA',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 3),
                        Text(
                          'TR•• •••• •••• •••• 4582',
                          style: TextStyle(color: AppColors.muted, fontSize: 12),
                        ),
                      ],
                    ),
                  ],
                ),
              )
            else
              const EmptyBox(
                message: 'Henüz bağlı banka hesabı yok.',
                icon: Icons.account_balance_outlined,
              ),
            const SizedBox(height: 14),
            _wideButton(
              text: '+ Yeni IBAN Ekle',
              color: AppColors.accent,
              onTap: () => _soon(context),
            ),
            const SizedBox(height: 26),
            _wideButton(
              text: 'Hesabımı Sil',
              icon: Icons.logout_rounded,
              color: const Color(0xFFFDA4AF),
              background: const Color(0xFF3B1A2C),
              border: const Color(0xFF5B2440),
              onTap: () => _confirmDelete(context),
            ),
          ],
        ),
      ),
    );
  }

  BoxDecoration _cardDecoration() => BoxDecoration(
    color: AppColors.card,
    borderRadius: BorderRadius.circular(16),
    border: Border.all(color: AppColors.border),
  );

  Widget _infoRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _cardDecoration(),
      child: Row(
        children: [
          _IconBox(icon: icon, color: AppColors.accent),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
                ),
                const SizedBox(height: 3),
                Text(
                  value,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          InkWell(
            onTap: () => _soon(context),
            borderRadius: BorderRadius.circular(10),
            child: Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: AppColors.chip,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(
                Icons.edit_outlined,
                color: AppColors.muted,
                size: 17,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _wideButton({
    required String text,
    required Color color,
    required VoidCallback onTap,
    IconData? icon,
    Color? background,
    Color? border,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        height: 54,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: background ?? color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: border ?? color.withValues(alpha: 0.45)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
            ],
            Text(
              text,
              style: TextStyle(
                color: color,
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IconBox extends StatelessWidget {
  final IconData icon;
  final Color color;

  const _IconBox({required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: color, size: 20),
    );
  }
}
