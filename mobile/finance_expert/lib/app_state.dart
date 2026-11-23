import 'package:flutter/material.dart';

/// Oturum süresi dolduğunda giriş ekranına dönebilmek için.
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

/// Ekranlar arası basit olaylar.
class AppEvents {
  AppEvents._();

  /// Alım/satım yapıldığında artar; cüzdan ve ana sayfa yeniden yüklenir.
  static final ValueNotifier<int> portfolioChanged = ValueNotifier<int>(0);
}
