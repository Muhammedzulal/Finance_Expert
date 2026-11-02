# Grafik, işlem geçmişi ve portföy değeri sözleşmeleri

Mevcut `backend/main.py` davranışı esas alınmıştır. Makine şeması:
`contracts/read-endpoints.schema.json`. Eski `finance-v1.schema.json` nesneleri
bu yanıtların yerine kullanılmaz: tarihçe fiyat öğelerinde schema_version yoktur;
işlem geçmişi öğelerinde ek realized_pnl vardır. Bu farklar şemada açıkça tanımlıdır.

## Fiyat geçmişi

`GET /api/v1/stocks/{symbol}/history?limit=100`

- symbol backend biçimi `[A-Z0-9]{1,15}`; Flutter doğrulanmış hisse listesindeki
  sembolü kullanır. Yeni okuma şeması backend ile aynı sembol biçimini kullanır.
- limit: 1-500, varsayılan 100. Son N kayıt alınır, `as_of ASC` olarak döndürülür;
  eşit zamanlarda kaynak sırası id ile belirlenir. Tarih filtresi ve sayfalama yoktur.
- Yanıt: `{symbol, count, history}`. history öğesi
  `{symbol, price, currency, as_of, provider, is_delayed}` içerir.
- price ondalık metin; as_of saat dilimli RFC 3339. OHLC/mum verisi değildir,
  çizgi grafik noktasıdır. Eksik aralıklar doldurulmaz, işlem hacmi üretilmez.
- Bilinen hissede kayıt yoksa 200 ve boş history; bilinmeyen hisse 404,
  geçersiz parametre 422, DB hatası 503. Bu uç şu an JWT istemez.

Örnek: `{"symbol":"DEMO","count":1,"history":[{"symbol":"DEMO","price":"100.00","currency":"TRY","as_of":"2026-11-02T09:00:00Z","provider":"TEST","is_delayed":false}]}`.

## İşlem geçmişi

`GET /api/v1/wallets/{wallet_id}/trades?limit=20&offset=0`

Bearer JWT zorunlu. wallet_id `wallet:<pozitif tam sayı>`. limit 1-100,
offset >= 0. Sıralama `executed_at DESC, trade_id DESC`.
Yanıt alanları: schema_version=1.0, wallet_id, total, limit, offset, has_more, items.
Her öğe Trade alanları yanında `realized_pnl` taşır: yalnız o işlemin gerçekleşen
kâr/zararıdır, cüzdanın birikmiş kârı değildir. Satış negatif olabilir.
Fiyat 6, tutar/kâr 2 ondalık basamaklı metin döner; lot tam sayıdır.

`has_more = offset + len(items) < total`. Son sayfada false; sınır ötesinde boş
liste döner. Offset sayfalama sırasında yeni işlem eklenirse kayma olabilir;
Flutter listeyi yenilerken offset'i sıfırlar ve trade_id ile tekrarları ayıklar.

## Portföy değeri

`GET /api/v1/wallets/{wallet_id}/valuation`, Bearer JWT zorunlu.

- schema_version=1.0, wallet_id, currency, cash_balance, realized_pnl.
- positions_cost: bütün açık pozisyonların toplam maliyeti.
- priced_positions_value: fiyatı kullanılabilen pozisyonların kısmi toplamı.
- positions_value: yalnız bütün pozisyonlar fiyatlanabildiyse toplam, aksi halde null.
- portfolio_value: cash_balance + positions_value; eksik fiyat varsa null.
- unrealized_pnl: positions_value - positions_cost; eksik fiyat varsa null.
- unrealized_pnl_percent: unrealized_pnl / positions_cost × 100; maliyet sıfırsa
  veya değer eksikse null. realized_pnl portföy değerine tekrar eklenmez.
- valuation_complete: eksik/geçersiz/farklı para birimli fiyat yok.
- valuation_is_current: complete, en az bir pozisyon var ve tüm fiyatlar güncel.
- valuation_basis=latest_stored_quote, calculated_at RFC 3339, positions ve warnings listeleri.

Pozisyon alanları: symbol, quantity, average_cost, cost_basis, last_price,
market_value, unrealized_pnl, unrealized_pnl_percent, quote_as_of, provider,
is_delayed, price_is_stale, price_is_test, price_status. Son fiyatla ilgili alanlar
kullanılamayan fiyatta null olur. price_status: missing, currency_mismatch, invalid,
test, stale, current. TEST sağlayıcısı test, gecikmeli/gelecek zamanlı veya
backend MAX_QUOTE_AGE_SECONDS eşiğini aşan fiyat stale kabul edilir. Test ve eski
fiyatlar hesapta kullanılır fakat değer güncel sayılmaz; Flutter uyarıyı gösterir.
Boş cüzdanda portfolio_value nakittir, complete=true, current=false.
Para hesabı Decimal ile, tutarlar 2 basamağa ROUND_HALF_UP yuvarlanır.

## Ortak hata davranışı ve Flutter

Cüzdan kimliği bozuksa 400, JWT yok/geçersizse 401, cüzdan yoksa veya sahibi
başkasıysa 404, query sınırı ihlalinde 422, DB hatasında 503 döner.
Mevcut FastAPI HTTP hatası `{"detail":"..."}`; query hatasında detail bir listedir.
Önceki taslak Error zarfı bu üç uçta uygulanmış değildir. Flutter HTTP durum kodu
ve detail tipini birlikte ele alır; yalnız başarı JSON'unu parse etmez.

Grafikte fiyat zamanını, cüzdanda calculated_at ve fiyat güncelliğini göster.
Null toplam için “Hesaplanamadı” göster; 0 veya kısmi toplamı tam değer gibi yazma.
İşlem sonrası cüzdan, işlem geçmişi ve valuation verilerini yeniden iste.
UI ve ağ katmanının uygulanması bu sözleşme tesliminin kapsamında değildir.

## Doğrulama

`python -m pip install -r backend/requirements-test.txt`

`python -m pytest backend/tests -q`

Testler gerçek endpoint yanıtlarını read-endpoints şemasına karşı doğrular;
DB erişimi taklittir. MySQL entegrasyonu ayrıca sınanmalıdır.
