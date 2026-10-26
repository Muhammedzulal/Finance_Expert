# AI modülü (Kutay)

Haberleri yerel LLM ile analiz edip `contracts/` altındaki **Analysis** sözleşmesine
uygun sonuç üretir. Uygulama al/sat/tut önerisi üretmez; haberin olası etkisini açıklar.

## Dosyalar

| Dosya | Görevi |
| --- | --- |
| `worker.py` | Backend'den iş alır (`claim`), analiz eder, sonucu kaydeder ya da `fail` bildirir |
| `analiz.py` | Analiz çekirdeği: prompt, model çağrısı, Türkçe cevabın sözleşmeye çevrilmesi, içerik denetimi |
| `piyasa.py` | Modele verilen fiyat bağlamı (son kapanış, 1/5/20 günlük değişim, RSI, 50 günlük ortalama) |
| `tutarlilik.py` | Model aynı habere aynı yorumu yapıyor mu? (gerçek modelle elle çalıştırılır) |
| `test_worker.py` | Ollama, MySQL ve internet gerektirmeyen testler (CI'da çalışır) |
| `gecici/` | **Silinecek.** Backend'e haber gelene kadar Muhammed'in JSON dosyalarıyla deneme |

## Kurulum

```sh
pip install ollama -r requirements-contracts.txt
pip install yfinance        # isteğe bağlı: fiyat bağlamı için
ollama pull qwen3.5:4b
```

`ai/.env.example` dosyasını `ai/.env` olarak kopyalayıp `INTERNAL_API_KEY` değerini yazın.
`ai/.env` git'e eklenmez.

## Komutlar

```sh
python ai/test_worker.py              # testler
python ai/worker.py                   # backend'e bağlı sürekli çalışma
python ai/worker.py --bir-kez         # bekleyen işleri bitirip çık
python ai/tutarlilik.py               # tutarlılık ölçümü (Ollama gerekir)
python ai/gecici/cevrimdisi.py        # backend olmadan deneme (Ollama gerekir)
```

## Kurallar

- Model hisse kodu belirlemez; yalnız haberle gelen semboller değerlendirilir.
- Eksik, şemaya uymayan ya da al/sat, hedef fiyat, kesin kazanç içeren çıktı kaydedilmez;
  en fazla 3 deneme yapılır, sonra iş `fail` olarak bildirilir.
- Hisse eşleşmeyen haberlerde yalnız özet üretilir, `impacts: []` kaydedilir.
- Fiyat verisi yalnız bağlamdır; etki yönünü haberin içeriği belirler. Fiyat verisi
  alınamazsa analiz bağlamsız yapılır.
- Sözleşme sürümü ve varsa zorunlu uyarı metni şemadan okunur.

## `gecici/` ne zaman silinir?

Muhammed'in News adaptörü haberleri `POST /api/v1/internal/news` ile backend'e
göndermeye başladığında. `worker.py`, `analiz.py` ve testler bu klasöre bağlı değildir;
yalnız `tutarlilik.py` varsayılan veri kaynağı olarak kullanır (`--dosya` ile değiştirilebilir).
