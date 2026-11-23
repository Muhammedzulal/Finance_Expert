import 'package:flutter/material.dart';

import 'app_state.dart';
import 'screens/login_screen.dart';
import 'screens/main_screen.dart';
import 'services/api_client.dart';
import 'services/auth_service.dart';
import 'theme/app_colors.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Kayıtlı oturum varsa doğrudan ana ekrana geçilir (internet gerekmez).
  final bool loggedIn = await AuthService.instance.restoreSession();

  // Token süresi dolarsa kullanıcıyı giriş ekranına gönder.
  bool handlingExpiry = false;
  ApiClient.instance.onUnauthorized = () async {
    if (handlingExpiry) return;
    handlingExpiry = true;
    await AuthService.instance.logout();
    navigatorKey.currentState?.pushAndRemoveUntil(
      MaterialPageRoute(
        builder: (_) => const LoginScreen(sessionExpired: true),
      ),
      (route) => false,
    );
    handlingExpiry = false;
  };

  runApp(FinanceExpertApp(loggedIn: loggedIn));
}

class FinanceExpertApp extends StatelessWidget {
  final bool loggedIn;

  const FinanceExpertApp({super.key, required this.loggedIn});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Finance Expert',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: AppColors.background,
        colorScheme: ThemeData.dark().colorScheme.copyWith(
          primary: AppColors.accent,
          secondary: AppColors.accent,
        ),
      ),
      home: loggedIn ? const MainScreen() : const LoginScreen(),
    );
  }
}
