# Portföy API'leri uçtan uca testi (Hafta 4 · Ensar)

Görev: fiyat geçmişi, işlem geçmişi ve portföy API'lerini mobil uygulamanın
kullanacağı akışla test etmek; her işlemden sonra API yanıtını ve veritabanı
kaydını kontrol etmek.

Test dosyası: `tests/test_portfoy_api_e2e.py` (12 test).

## Neyi test ediyor?

| # | Senaryo | API kontrolü | Veritabanı kontrolü |
|---|---|---|---|
| 01 | Fiyat geçmişi | `GET /stocks/{symbol}/history` eskiden yeniye sıralı, `limit` doğru, 404/422 hata kodları | `quotes` satır sayısı |
| 02 | İlk alış (10 × 312,75) | 201, tutar `3127.50`, `quote_as_of`, `executed_at` UTC | `trades`, `positions`, `wallets.cash_balance = 96872.50` |
| 03 | Aynı isteğin tekrarı | 200 ve aynı `trade_id`; farklı içerikle 409 `IDEMPOTENCY_CONFLICT` | Yeni trade yok, bakiye değişmedi |
| 04 | İkinci alış (5 × 320,10) | 201, tutar `1600.50` | Ortalama maliyet `315.200000`, adet 15 |
| 05 | Kısmi satış (6 × 330,55) | 201, tutar `1983.30` | `realized_pnl = 92.10`, maliyet değişmedi, adet 9 |
| 06 | Başarısız işlemler | `INSUFFICIENT_FUNDS`, `INSUFFICIENT_POSITION`, `STALE_QUOTE`, geçersiz hisse, adet 0 | Hiçbir tablo değişmedi |
| 07 | İşlem geçmişi | `GET /wallets/{id}/trades` en yeniden eskiye, sayfalama, `has_more` | Her satır `trades` ile birebir |
| 08 | Portföy değeri (son fiyat 333,00) | Nakit, maliyet, piyasa değeri, K/Z, yüzde, TEST uyarısı | Nakit + pozisyon = başlangıç + gerçekleşen + gerçekleşmemiş |
| 09 | Yetki | Başkasının cüzdanı 404, token yok veya bozuk 401 | — |
| 10 | Tüm pozisyonu satmak | Değerlemede pozisyon kalmıyor | Pozisyon satırı silindi, `realized_pnl = 45.30` |
| 11 | Eşzamanlı iki alış (2 × 60.000 TL) | Biri 201, diğeri 409 | Tek trade, bakiye `40000.00` |
| 12 | Aynı anahtarla eşzamanlı 3 istek | Bir 201, iki 200, tek `trade_id` | Tek trade |

Beklenen tutarlar elle hesaplandı. Testler backend'in kendi hesabını değil,
bu bağımsız hesabı esas alıyor.

## Çalıştırma

1. Backend ve MySQL'i başlatın (Compose ya da yerel). Backend'in
   `TRADE_ALLOWED_QUOTE_PROVIDERS=TEST` ile çalışması gerekir. Test her
   işlemden hemen önce taze bir `TEST` fiyatı gönderir, çünkü işlem için
   fiyat en fazla 60 saniyelik olmalı.
2. Hisse listesinin yüklü olduğundan emin olun (`database/02_seed_stocks.sql`).
   Compose bunu yalnızca **yeni** bir volume'da kendiliğinden yükler; mevcut
   veritabanı için:
   `mysql -u <kullanici> -p finance_expert < database/02_seed_stocks.sql`
3. Testi çalıştırın:

```sh
python -m pip install pytest PyMySQL cryptography
export E2E_BACKEND_URL=http://127.0.0.1:8001
export E2E_INTERNAL_API_KEY=<INTERNAL_API_KEY>
export E2E_DB_HOST=127.0.0.1 E2E_DB_PORT=3308
export E2E_DB_USER=<DB_USER> E2E_DB_PASSWORD=<DB_PASSWORD>
python -m pytest -v tests/test_portfoy_api_e2e.py
```

Ortam değişkenleri tanımlı değilse testler atlanır, CI'daki sözleşme işini
bozmaz. Testler her çalıştırmada yeni kullanıcı açar; tekrar tekrar
çalıştırılabilir.

## Sonuç (23.11.2026, MySQL 8.0)

- 12 testin 12'si geçti, üç ardışık çalıştırmada da sonuç aynı.
- Kontrol amaçlı, backend'in bir kopyasına bilerek iki hata konuldu: satışta
  K/Z işareti ters çevrildi ve cüzdan kilidi (`FOR UPDATE`) kaldırıldı.
  Testlerin 6'sı düştü; iki hata da yakalandı.

## Bulunan sorunlar ve notlar

1. **Boş `stocks` tablosu (düzeltildi).** Şemada hisse verisi yoktu; yeni
   kurulan bir sistemde hisse kodu taşıyan her haber ve fiyat 422 alıyordu.
   `database/02_seed_stocks.sql` eklendi ve Compose'a bağlandı.
2. **Gerçek fiyatla işlem yapılamıyor (karar bekliyor).** Fiyat botu yfinance'ten
   günlük kapanış gönderiyor; bu fiyatın zamanı saatler öncesi olduğu için 60 sn
   kuralına takılıyor ve her işlem `STALE_QUOTE` alıyor. Demo şimdilik `TEST`
   sağlayıcısıyla yapılabilir. Kalıcı çözüm (daha sık fiyat ya da sanal işlem
   için gevşek kural) Şükrü'nün onayına bağlı hesap kuralı olduğu için
   değiştirilmedi.
3. **Satış yanıtında gerçekleşen K/Z yok.** `POST /trades` yanıtında
   `realized_pnl` alanı yok, `GET /trades` listesinde var. Mobil, satıştan
   hemen sonra kârı göstermek isterse ya listeyi yeniden çekmeli ya da bu
   alan yanıta eklenmeli.
4. **`POST /internal/quotes` yanıtı** `GET /quote` ile aynı biçimde değil
   (`schema_version` alanı yok). Mobili etkilemez, sözleşme açısından not.

## Mobil (Eray) için kontrol listesi

Flutter tarafı API'ye bağlandığında aynı akış uygulamadan elle denenebilir:

1. Kayıt ol → cüzdanda 100.000,00 TL görünmeli.
2. THYAO detay → grafik `/history`'den eskiden yeniye çizilmeli.
3. 10 adet al → cüzdan ekranında nakit ve pozisyon güncellenmeli.
4. Al butonuna iki kez hızlı bas → tek işlem oluşmalı (aynı
   `idempotency_key` kullanılmalı).
5. Bakiyeden fazla al → "Yetersiz bakiye" durumu (`INSUFFICIENT_FUNDS`).
6. İşlem geçmişi → en yeni üstte, satışlarda K/Z görünmeli.
7. Portföy → `valuation_is_current = false` ise "fiyat güncel değil/test"
   uyarısı gösterilmeli.
