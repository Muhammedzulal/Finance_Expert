# Kutay için Gerçek Haber ve İndikatör Örnekleri Rehberi

Bu rehber, Muhammed (Web Scraper & Graphics Analyzer sorumlusu) tarafından hazırlanan gerçek veri setlerini ve AI analiz modülüyle entegrasyon yöntemlerini açıklar.

---

## 1. Teslim Edilen Örnek Dosyalar

Tüm örnekler `ai/ornekler/` dizini altına yerleştirilmiştir:

| Dosya | Açıklama | Kaynak Modül |
| --- | --- | --- |
| `ai/ornekler/gercek_haberler.json` | 47 adet gerçek KAP ve Bloomberg HT haberi (`News v1.0` sözleşmesine %100 uyumlu) | `Web_scaper` |
| `ai/ornekler/gercek_indikatorler.json` | 8 sembol için gerçek fiyat ve hesaplanmış teknik indikatör serileri | `graphics_analyzer` |

---

## 2. Gerçek Haber Verisi (`gercek_haberler.json`)

`contracts/finance-v1.schema.json` dosyasındaki **News** sözleşmesine tam uyumludur. BIST hisse senetleri (THYAO, GARAN, ASELS, SKBNK, MERCN, CEMAS vb.) şirket adları ve duyuru başlıklarıyla otomatik olarak eşleştirilmiştir.

### Örnek Kayıt:
```json
{
  "schema_version": "1.0",
  "news_id": "bloomberg_ht:84d973beda70297fa18da4e05ac47b95189f897985877cec674aee17a3c30de8",
  "source": "BLOOMBERG_HT",
  "source_id": null,
  "title": "SPK, iki şirketin sermaye artırımını onayladı",
  "summary": "SPK, Mercan Kimya Sanayi ve Ticaret A.Ş. ve Şekerbank T.A.Ş.'nin sermaye artırımına onay verdi.",
  "url": "https://www.bloomberght.com/spk-iki-sirketin-sermaye-artirimini-onayladi-3791715",
  "published_at": "2026-10-16T21:04:41+00:00",
  "fetched_at": "2026-10-19T09:53:19+00:00",
  "symbols": ["SKBNK", "MERCN"],
  "matched_keywords": ["sermaye artırımı"],
  "disclosure_type": null
}
```

### Kutay'ın Kullanımı:
1. **Tutarlılık Ölçümü (`ai/tutarlilik.py`):**
   ```sh
   python ai/tutarlilik.py --dosya ai/ornekler/gercek_haberler.json --limit 8 --tekrar 5
   ```
2. **`ai/gecici/` Klasöründen Geçiş:**
   `ai/README.md` dosyasında belirtilen geçici dönüştürücü yerine doğrudan bu JSON verisini kullanabilir ya da backend üzerinden canlı işleri alabilirsin.

---

## 3. Gerçek İndikatör Verisi (`gercek_indikatorler.json`)

`graphics_analyzer/data_loader.py` tarafından üretilen teknik indikatörler, `ai/piyasa.py` ve `ai/grafik_yorum.py` modüllerinin doğrudan tüketebileceği şekilde yapılandırılmıştır.

Takip edilen 8 sembol:
- **BIST Hisseleri:** `THYAO.IS`, `GARAN.IS`, `ASELS.IS`
- **Döviz & Emtia:** `USDTRY=X`, `EURTRY=X`, `GC=F` (Ons Altın)
- **Kripto:** `BTC-USD`, `ETH-USD`

### Veri Yapısı:
Her sembol için 4 ana bölüm bulunur:
1. `guncel_gostergeler`:
   - `RSI_14`: 14 periyotluk RSI (örn. `47.25`)
   - `SMA_50`: 50 günlük basit hareketli ortalama
   - `EMA_20`: 20 günlük üstel hareketli ortalama
   - `Bollinger_Ust`, `Bollinger_Orta`, `Bollinger_Alt`: 20 periyotluk Bollinger bantları
   - `Son_Gun_Degisim_Yuzde`: Günlük yüzdesel değişim
2. `piyasa_baglami` (`ai/piyasa.py` için):
   - `degisim_1g`, `degisim_5g`, `degisim_20g`
   - `sma50_farki`: Fiyatın SMA_50'ye göre yüzdesel farkı
3. `teknik_yorum_sablonu`:
   - `TechnicalAnalyzer` tarafından üretilen kural tabanlı nesnel Türkçe özet
4. `son_25_gun_serisi` (`ai/grafik_yorum.py` için):
   - Son 25 günün indikatör değerleri (Ollama ve çevrimdışı testler için hazır besleme)

---

## 4. Backend Otomatik Aktarım Bilgisi

Haber ve fiyat botları backend'e otomatik aktarım yapacak şekilde bağlanmıştır:
- **Haberler:** `POST /api/v1/internal/news` -> Otomatik olarak `analysis_jobs` tablosunda `pending` durumunda iş açar.
- **Worker:** `ai/worker.py` çalıştırıldığında `POST /api/v1/internal/analysis-jobs/claim` ile bu gerçek haberleri sırayla alıp analiz edebilir.
- **Fiyatlar:** `POST /api/v1/internal/quotes` -> `Quote v1.0` sözleşmesiyle BIST hisselerinin son fiyatlarını backend'e yazar.
