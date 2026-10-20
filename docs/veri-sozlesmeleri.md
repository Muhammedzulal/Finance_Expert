# Veri sözleşmeleri ve REST API v1 taslağı

Durum: İlk entegrasyon için öneri. Repoda henüz bu endpoint'ler yoktur.
Şema: `contracts/finance-v1.schema.json`, örnek: `contracts/examples.json`.
JSON Schema Draft 2020-12 kullanılır; her mesaj kendi `$defs` adıyla doğrulanır.

## Ortak kurallar

- Alan adları `snake_case`, metinler UTF-8, `schema_version` değeri `1.0`.
- Tüm listelenen nesne alanları zorunludur. Bilinmeyen alanlar reddedilir.
  Bilinmeyen değer yalnız şemanın izin verdiği yerde `null` veya boş listedir.
- Zamanlar saat dilimi içeren RFC 3339 biçimindedir. Depolama UTC,
  Android gösterimi Europe/Istanbul olabilir; `2026-10-20 09:00:00` kabul edilmez.
- Para/fiyat alanları 2-6 ondalık basamaklı metindir (`"100.00"`). Sayısal JSON
  veya virgüllü metin kabul edilmez. Hesaplar Decimal/BigDecimal ile yapılır.
- İlk kapsam TRY, tam lot hisse ve sanal işlemdir. Sembol büyük harfli ve
  sağlayıcı uzantısızdır. Şema biçim denetler; geçerliliği hisse ana listesi belirler.
- Tüm örnekler temsili ve `DEMO` sembollüdür; gerçek fiyat/haber değildir.
- Sözleşme değişikliği şema, doküman ve örnekleri birlikte günceller. Yeni alan
  bile mevcut sıkı doğrulayıcıları bozabilir: tüketiciler hazırlanıp sürüm birlikte
  yükseltilir; mevcut `1.0` biçimi sessizce değiştirilmez.

## News: Muhammed -> backend -> Kutay / Android

| Alan | Anlam |
| --- | --- |
| news_id | Kaynak bazında kararlı ve benzersiz haber anahtarı |
| source | `KAP` veya `BLOOMBERG_HT`; yeni kaynak enum'u sürümle eklenir |
| source_id | KAP bildirim kimliği; kaynak kimliği yoksa null |
| title / summary | Temiz düz metin; summary boş olabilir |
| url | Kaynağın HTTPS bağlantısı |
| published_at | Kaynak yayın zamanı, bilinmiyorsa null |
| fetched_at | Adaptörün haberi gerçekten aldığı saat dilimli zaman |
| symbols | Doğrulanmış hisse kodları; eşleşme yoksa [] |
| matched_keywords | Eşleşen anahtar kelimeler; yoksa [] |
| disclosure_type | KAP açıklama türü; RSS için null |

### Mevcut botlardan geçiş tablosu

| Ham alan | Ortak alan | Dönüşüm |
| --- | --- | --- |
| KAP source | source | `KAP` |
| KAP disclosure_id | source_id, news_id | Kimlik varsa source_id aynen, news_id `kap:<kimlik>` |
| KAP stock_code | symbols | `-`/boş -> []; dolu değer hisse ana listesiyle doğrulanır |
| KAP title, summary | title, summary | Boşluk/HTML temizliği; boş başlık karantinaya |
| KAP detail_url | url | Geçerli HTTPS yoksa karantinaya |
| KAP disclosure_type | disclosure_type | Boşsa null |
| KAP'ta yok | published_at, fetched_at, matched_keywords | null, yeni çekimde saat dilimli zaman, [] |
| Bloomberg source | source | `Bloomberg HT` -> `BLOOMBERG_HT` |
| Bloomberg title, summary | title, summary | HTML temizlenir, düz metne çevrilir |
| Bloomberg link | url, news_id | URL normalize edilir; `bloomberg_ht:<sha256(url)>` |
| Bloomberg published | published_at | RSS tarihi parse edilip RFC 3339'a çevrilir; hata -> null |
| Bloomberg fetched_at | fetched_at | Yeni çekimler saat dilimli yazılır; eski kaydın dilimi tahmin edilmez |
| Bloomberg matched_keywords | matched_keywords | Tekilleştirilir |
| Bloomberg'de yok | source_id, symbols, disclosure_type | null, doğrulanmış eşleşmeler veya [], null |

URL normalizasyonu: baş/son boşluğu kaldır, scheme/host küçük harf, fragment'i
kaldır, varsayılan HTTPS portunu kaldır, path/query ve query sırasını koru.
Hash UTF-8 URL üzerinde SHA-256 küçük harfli hex'tir. KAP kimliği yoksa aynı
kuralla `kap:url:<sha256(url)>` kullanılır. URL veya kimlik olmadan kararlı
tekillik sağlanamaz; kayıt karantinaya alınır. Aynı haberin tekrar çekilmesi
yeni kayıt üretmez. İlk fazda aynı kimlikle gelen kayıt mevcut içeriği ezmez;
kaynak düzeltmelerinin sürümlenmesi sonraki iştir.

Eski arşivde gerçek çekim zamanı bilinmiyorsa yeni zaman uydurulmaz; arşiv geçişi
ayrı ele alınır. Repo örnekleri doğrudan yeni şemaya uyuyor sayılmaz. Bu paket
geçişi tarif eder; adaptör uygulaması Muhammed'in takip işidir.

## Analysis: Kutay -> backend -> Android

`analysis_id` kalıcı çıktı kimliği, `news_id` mevcut habere FK'dır. `model`,
`prompt_version`, `created_at` izlenebilirlik içindir. `summary` kısa açıklamadır.
`impacts` her sembol için `symbol`, `direction`, `confidence`, `reason` içerir.
Yön: `positive`, `negative`, `neutral`, `uncertain`. Confidence 0-1 arasıdır;
kazanç olasılığı anlamına gelmez. Sembol eşleşmemişse `impacts: []` döner.

Backend aynı sembolü iki kez kabul etmez, sembolleri News eşleşmeleriyle kontrol
eder; yeni eşleşme gerekiyorsa ana listeyle ayrı doğrular. LLM kendi kendine
geçerli bir hisse kodu belirleyemez. Bozuk JSON kaydedilmez; hata iş durumundadır.
Analiz başarısızlığında sahte `neutral` analiz üretilmez.

## Quote, Wallet, TradeRequest, Trade

Quote: `symbol`, `price`, `currency`, `as_of`, `provider`, `is_delayed`.
Fiyat > 0 ve sağlayıcısı bilinen gerçek bir kayıt olmalıdır. Şema metin biçimini,
backend fiyatın pozitifliğini ve güncelliğini kontrol eder. `as_of` fiyatın
zamanıdır; API'ye geldiği zaman değildir. Quote grafiğin OHLC verisi değildir;
mum grafiği endpoint'i sağlayıcı seçildikten sonra ayrı sözleşmeye bağlanacak.

Wallet: `wallet_id`, `currency`, `cash_balance`, `realized_pnl`, `positions`,
`updated_at`. Her pozisyon `symbol`, pozitif tam `quantity`, `average_cost` taşır.
Aynı sembol tek pozisyondur. Satışla miktar sıfır olunca listeden kaldırılır.

TradeRequest: `symbol`, `side` (`buy`/`sell`), pozitif tam `quantity`, UUID
`idempotency_key`. Cüzdan kimliği URL'den, sahibi oturumdan gelir. İstemci fiyat,
komisyon, bakiye veya gerçekleşme zamanı göndermez.

Trade: istek alanlarına ek olarak `trade_id`, `wallet_id`, `execution_price`,
`gross_amount`, `currency`, `quote_as_of`, `executed_at` içerir. Bu kayıt yalnız
gerçekleşmiş sanal işlemdir; reddedilen emir Error döndürür.

Önerilen MVP hesap kuralları (Şükrü'nün kabulü bekleniyor):

1. Başlangıç sanal bakiye 100000.00 TRY, komisyon/vergi sıfır, açığa satış yok.
2. Alış tutarı = miktar × sunucudaki fiyat. Yetersiz nakit veya lot reddedilir.
3. Alış ortalama maliyeti = (eski miktar × eski ortalama + alış tutarı) / yeni miktar.
4. Satış gerçekleşen kârı = miktar × (satış fiyatı - ortalama maliyet).
5. Toplam gerçekleşen kâr cüzdanda birikir; kalan lotun ortalama maliyeti değişmez.
6. Nakit/tutar 2, ortalama maliyet 6 basamağa ROUND_HALF_UP yuvarlanır.
7. Kaynak fiyatı 60 saniyeden eskiyse, gelecekteyse veya `is_delayed=true` ise
   emir reddedilir (`STALE_QUOTE`). Bu eşik sağlayıcı seçilince tekrar değerlendirilir.
8. Cüzdan ve pozisyon satır kilidi, bakiye değişimi, Trade ve idempotency kaydı aynı
   DB transaction içindedir. Aynı cüzdan+anahtar+aynı istek tekrarında önceki Trade
   döner; aynı anahtar+farklı istek `IDEMPOTENCY_CONFLICT` olur.

Örnek dosyadaki alış: başlangıç 100000.00, 10 lot × 100.00 = 1000.00,
kalan 99000.00 ve 10 lotun ortalaması 100.00. Aynı pozisyondan 4 lot 110.00'a
satılırsa nakit 99440.00, kalan 6 lot ve gerçekleşen kâr 40.00 olur.
Bu kurallar tasarım örneğidir; çalışır işlem motoru bu teslimin parçası değildir.

## Önerilen REST uçları

| Metot ve yol | Erişim | İstek -> yanıt |
| --- | --- | --- |
| POST /api/v1/internal/news | Servis | News -> 201 yeni News, 200 mevcut News |
| POST /api/v1/internal/analyses | Servis | Analysis -> 201 yeni, 200 aynı analysis_id/aynı gövde |
| POST /api/v1/internal/quotes | Servis | Quote -> 201 yeni, 200 aynı sembol/zaman/aynı gövde |
| GET /api/v1/news | Kullanıcı | Filtre -> News sayfası |
| GET /api/v1/news/{news_id} | Kullanıcı | Yok -> News |
| GET /api/v1/news/{news_id}/analysis | Kullanıcı | Yok -> analiz durum yanıtı |
| GET /api/v1/stocks/{symbol}/quote | Kullanıcı | Yok -> en son Quote |
| GET /api/v1/wallets/{wallet_id} | Cüzdan sahibi | Yok -> Wallet |
| POST /api/v1/wallets/{wallet_id}/trades | Cüzdan sahibi | TradeRequest -> 201 Trade; tekrarda 200 Trade |

Tekil başarılı yanıtlar doğrudan ilgili nesnedir. `news_id` gibi path
parametreleri URL-encode edilir. İç analiz/fiyat tekrarında kimlik aynı ama
içerik farklıysa 409/VALIDATION_ERROR döner; kayıt sessizce ezilmez.
Haber liste filtresi `symbol` (opsiyonel), `limit` (1-100, varsayılan 20),
`cursor` (opak, opsiyonel). Sıralama `fetched_at DESC, news_id DESC`.
Yanıt: `{"schema_version":"1.0","items":[<News>],"next_cursor":null}`.
Sonraki sayfa varsa next_cursor string olur. Sayfalama zarfı bu ilk pakette
makine şemasına dahil değildir; News öğeleri doğrulanır.

Analiz durum yanıtı:
`{"schema_version":"1.0","news_id":"kap:demo-001","status":"pending","analysis":null}`.
`status`: pending, processing, completed, failed; yalnız completed ise analysis
Analysis nesnesidir, diğerlerinde null. Haber yoksa 404. Bu durum zarfının
makine şeması ilk API uygulamasında eklenecek; Analysis nesnesi burada tanımlıdır.

Hatalar Error şemasına uyar: 400 VALIDATION_ERROR, 401 UNAUTHORIZED,
403 FORBIDDEN, 404 NOT_FOUND, 409 INSUFFICIENT_FUNDS / INSUFFICIENT_POSITION /
STALE_QUOTE / IDEMPOTENCY_CONFLICT / VALIDATION_ERROR,
429 RATE_LIMITED, 503 SERVICE_UNAVAILABLE. SQL/stack trace istemciye verilmez.

## Şema dışındaki kontroller

JSON Schema tek başına FK, sembol ana listesi, tutar hesabı, mükerrer pozisyon,
zaman sırası, cüzdan sahipliği, fiyat yaşı ve transaction bütünlüğünü doğrulamaz.
Bu kontroller backend ve Şükrü'nün entegrasyon senaryolarında uygulanacaktır.
