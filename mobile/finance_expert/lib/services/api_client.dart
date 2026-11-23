import 'package:dio/dio.dart';

import '../config.dart';
import '../data/demo_backend.dart';

/// Ekranlarda doğrudan gösterilebilecek Türkçe hata.
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  /// Backend'in "detail" alanı (ör. INSUFFICIENT_FUNDS)
  final String? code;

  /// Sunucuya hiç ulaşılamadıysa true (internet yok, backend kapalı...)
  final bool isNetworkError;

  ApiException(
    this.message, {
    this.statusCode,
    this.code,
    this.isNetworkError = false,
  });

  /// Önbellekteki veriye geri dönülebilecek hata mı?
  bool get canUseCache => isNetworkError || (statusCode ?? 0) >= 500;

  @override
  String toString() => message;
}

/// Tüm HTTP isteklerinin geçtiği tek Dio istemcisi.
/// Oturum açıksa her isteğe `Authorization: Bearer <JWT>` ekler.
class ApiClient {
  ApiClient._() {
    dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 15),
        headers: const {'Accept': 'application/json'},
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final String? currentToken = token;
          if (currentToken != null && currentToken.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $currentToken';
          }
          handler.next(options);
        },
        onError: (error, handler) {
          // Oturum açıkken 401 gelirse token süresi dolmuştur.
          if (error.response?.statusCode == 401 && token != null) {
            onUnauthorized?.call();
          }
          handler.next(error);
        },
      ),
    );
  }

  static final ApiClient instance = ApiClient._();

  late final Dio dio;

  /// Bellekteki JWT. Kalıcı kopyası AuthService'te güvenli depoda tutulur.
  String? token;

  /// main.dart'ta ayarlanır: kullanıcıyı giriş ekranına yönlendirir.
  void Function()? onUnauthorized;

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    if (AppConfig.demoMode) {
      return DemoBackend.instance.handle('GET', path, query: query);
    }
    try {
      final Response<dynamic> response = await dio.get<dynamic>(
        path,
        queryParameters: query,
      );
      return response.data;
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<dynamic> post(String path, Object? body) async {
    if (AppConfig.demoMode) {
      return DemoBackend.instance.handle('POST', path, body: body);
    }
    try {
      final Response<dynamic> response = await dio.post<dynamic>(
        path,
        data: body,
      );
      return response.data;
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  ApiException _toApiException(DioException e) {
    final Response<dynamic>? response = e.response;
    if (response == null) {
      return ApiException(
        'Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.',
        isNetworkError: true,
      );
    }
    final int? status = response.statusCode;
    String? detail;
    final dynamic data = response.data;
    if (data is Map && data['detail'] != null) {
      final dynamic d = data['detail'];
      if (d is String) {
        detail = d;
      } else if (d is List && d.isNotEmpty && d.first is Map) {
        detail = (d.first as Map)['msg']?.toString();
      }
    }
    return ApiException(
      _friendlyMessage(status, detail),
      statusCode: status,
      code: detail,
    );
  }

  static String _friendlyMessage(int? status, String? detail) {
    final String d = detail ?? '';
    if (d.startsWith('INSUFFICIENT_FUNDS')) {
      return 'Yetersiz bakiye: bu işlem için cüzdanınızda yeterli para yok.';
    }
    if (d.startsWith('INSUFFICIENT_POSITION')) {
      return 'Yetersiz hisse: satmak istediğiniz adet portföyünüzdekinden fazla.';
    }
    if (d.startsWith('STALE_QUOTE')) {
      return 'Bu hisse için güncel fiyat yok; işlem şu anda yapılamıyor.';
    }
    if (d.startsWith('IDEMPOTENCY_CONFLICT')) {
      return 'Bu işlem zaten gönderildi.';
    }
    if (status == 401) {
      return d.toLowerCase().contains('sifre')
          ? 'E-posta veya şifre hatalı.'
          : 'Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.';
    }
    if (status == 409 && d.toLowerCase().contains('e-posta')) {
      return 'Bu e-posta adresi zaten kayıtlı.';
    }
    if (status == 404) {
      return d.isNotEmpty ? d : 'Kayıt bulunamadı.';
    }
    if (status == 422) {
      return d.isNotEmpty ? 'Geçersiz bilgi: $d' : 'Girilen bilgiler geçersiz.';
    }
    if (status != null && status >= 500) {
      return 'Servis şu anda yanıt vermiyor, biraz sonra tekrar deneyin.';
    }
    if (d.isNotEmpty) return d;
    return 'Beklenmeyen bir hata oluştu (HTTP ${status ?? '-'}).';
  }
}
