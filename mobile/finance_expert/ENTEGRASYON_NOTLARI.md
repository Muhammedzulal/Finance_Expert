# Mobil uygulama – 3. hafta entegrasyonu

Uygulama artık sabit veri yerine backend API'sini kullanıyor.

## Çalıştırma

```sh
flutter pub get
flutter run
```

Backend `docker compose up -d` ile bilgisayarda `127.0.0.1:8001` adresinde çalışmalı.
Android emülatörü bu adrese `http://10.0.2.2:8001` üzerinden ulaşır (varsayılan ayar).

Farklı adres için:

```sh
# Gerçek telefon (bilgisayarın yerel IP'si; backend portu dışarı açık olmalı)
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8001
# Windows/Chrome üzerinde çalıştırırken
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8001
```

## Neler eklendi

| Özellik | Dosya | API |
| --- | --- | --- |
| Giriş / kayıt, JWT güvenli depoda | `services/auth_service.dart`, `screens/login_screen.dart`, `screens/register_screen.dart` | `/users/login`, `/users/register`, `/users/me` |
| HTTP istemcisi (Dio), Türkçe hata mesajları | `services/api_client.dart` | — |
| Offline-first önbellek (Drift/SQLite) | `data/local_cache.dart`, `data/finance_repository.dart` | tüm GET istekleri |
| Ana sayfa: portföy özeti, AI yorumlu haberler | `screens/main_screen.dart` | `/wallets/{id}/valuation`, `/news`, `/news/{id}/analysis` |
| Piyasa: hisse listesi, arama, fiyatlar | `screens/market_screen.dart` | `/stocks`, `/stocks/{symbol}/quote` |
| Hisse Detay: fiyat grafiği, haberler, AI yorumu | `screens/stock_detail_screen.dart`, `widgets/price_chart.dart` | `/stocks/{symbol}/history`, `/news?symbol=` |
| Al/Sat ekranı | `screens/trade_screen.dart` | `POST /wallets/{id}/trades` |
| Cüzdan: değer, kâr/zarar, varlıklar, işlem geçmişi | `screens/wallet_screen.dart` | `/wallets/{id}/valuation`, `/wallets/{id}/trades` |

İnternet yokken ekranlar son kaydedilen verileri gösterir ve üstte "Çevrimdışı" uyarısı çıkar.
Alım-satım internet gerektirir.

## Gerçek API modu ve demo

- Uygulama artık varsayılan olarak **gerçek backend'e** bağlanır (giriş, piyasa, cüzdan).
- Backend'e ulaşılamazsa giriş ekranındaki **"Demo hesabıyla dene"** butonu örnek verilerle açar; çıkış yapınca demo kapanır.
- Her zaman demo ile açmak için: `flutter run --dart-define=DEMO_MODE=true`

### Backend'de gerçek veri için gerekenler

1. `stocks` tablosu boş gelir; fiyat botu (`graphics_analyzer/sync_quotes.py`) yalnızca kayıtlı hisselere fiyat yazar:

```sql
INSERT IGNORE INTO stocks (symbol, company_name, market, is_active) VALUES
('THYAO','Türk Hava Yolları','BIST',1), ('GARAN','Garanti BBVA','BIST',1),
('ASELS','Aselsan','BIST',1), ('SISE','Şişecam','BIST',1),
('KCHOL','Koç Holding','BIST',1), ('TUPRS','Tüpraş','BIST',1),
('AKBNK','Akbank','BIST',1), ('BIMAS','BİM Mağazalar','BIST',1);
```

2. Fiyatları gönder: `py graphics_analyzer/sync_quotes.py`
3. Al/Sat için `.env.compose` içine `TRADE_ALLOWED_QUOTE_PROVIDERS=YFINANCE` eklenmeli; ayrıca fiyat 60 saniyeden eski olmamalı (yoksa `STALE_QUOTE`).

## Alt / üst fiyat limiti bildirimi

| Parça | Dosya |
| --- | --- |
| Alarm modeli | `models/price_alert.dart` |
| Kontrol servisi (uygulama açıkken 30 sn'de bir, demoda 10 sn) | `services/price_alert_service.dart` |
| Alarm kurma paneli | `widgets/price_alert_sheet.dart` |
| Fiyat Uyarıları ekranı | `screens/price_alerts_screen.dart` |

- Hisse Detay sağ üstteki zil butonu veya Profil → Bildirim Ayarları → **Fiyat Uyarısı Yönet**.
- Fiyat üst limite çıkınca / alt limite düşünce: ekranda bildirim + titreşim, Bildirimler paneline kayıt.
- Her limit bir kez tetiklenir; alarm yeniden kaydedilince tekrar kurulur.
- Bildirim Ayarları'nda "Hisse Uyarıları" kapalıysa açılır bildirim gösterilmez (kayıt yine tutulur).
- Backend'de alarm servisi yok; alarmlar cihazdaki Drift veritabanında saklanır.
