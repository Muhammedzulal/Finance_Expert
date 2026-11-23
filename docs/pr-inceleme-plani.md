# PR inceleme planı - 24 Kasım 2026

Bu belge inceleme sırasını ve kabul ölçütlerini tanımlar; kişilere mesaj gönderildiği
veya GitHub üzerinde reviewer atandığı anlamına gelmez. Başka bir kişinin onayı yerine geçmez.

| PR | Kapsam | İnceleme sorumluluğu | Kabul ölçütü |
| --- | --- | --- | --- |
| #9 docs/mimari-veri-sozlesmeleri | Mimari, sözleşme ve CI | Backend: Ensar; AI: Kutay; mobil: Eray/Furkan | Şema ile gerçek yanıt uyumu, üç CI işi yeşil, mobil model onayı |
| #11 test/ensar-portfoy-e2e | MySQL ile portföy/işlem/fiyat E2E | Finansal senaryolar: Şükrü; API uyumu: Berke | İzole DB'de gerçek koşu çıktısı, testler skip olmadan geçmeli |

## İnceleme sırası

1. #9: Analysis v1.1, disclaimer kabul/kayıt/yanıt; eski v1.0 kayıtların okunması.
2. #9: fiyat geçmişi schema_version alanı; Flutter'ın null toplam ve eski fiyatı ayrı göstermesi.
3. #11: geçici/test MySQL ortamı, seed hisseleri ve TEST sağlayıcısıyla tam koşu.
4. Her iki PR'da çözülmemiş yorumlar kapatılıp ilgili katmanların kabulü alınır.
5. Birleştirmeyi repo sorumlusu yapar. Bu çalışma main'e merge edilmez.

## #11 ilk inceleme notları

Kod incelendi; bu çalışma sırasında canlı MySQL E2E koşusu yapılmadı.
Testler ortam değişkenleri yokken skip olur. Bu nedenle yalnız pytest'in başarılı
çıkması gerçek E2E doğrulaması sayılmaz. İzole ve yeniden oluşturulabilir DB'de
`E2E_*` ayarlarıyla çalıştırılıp kaç testin gerçekten geçtiği PR'a eklenmelidir.
PR test kullanıcıları ve TEST fiyatları yazar; üretim/veri paylaşımı olan DB kullanılmamalıdır.
Günlük kapanış fiyatları ile 60 saniyelik emir fiyatı kuralının uyuşmazlığı mevcut
PR'da da belirtilmiş; bu finansal kural otomatik olarak gevşetilmemelidir.

## Zorunlu kontroller

- validate-contracts: şema/örnek ve AI worker kontrolleri.
- backend-tests: pytest backend ve haber/fiyat adaptör testleri; DB taklidi.
- flutter-analyze: stable SDK, pub get, fatal info/warning ile statik analiz.

GitHub reviewer ataması/branch protection bu teslimde değiştirilmemiştir.
