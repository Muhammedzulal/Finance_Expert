"""AI worker: backend'den bekleyen haberleri alır, analiz eder, sonucu geri yazar.

Döngü (docs/mimari.md, "Haberden ekrana akış"):
  1. POST /api/v1/internal/analysis-jobs/claim      -> bekleyen bir haber al
  2. Haberi yerel LLM ile analiz et (analiz.py)
  3a. Başarılıysa POST /api/v1/internal/analyses    -> analizi kaydet
  3b. Başarısızsa POST .../analysis-jobs/{id}/fail  -> hatayı bildir

Ayarlar ortam değişkenlerinden ya da ai/.env dosyasından okunur:
  BACKEND_URL        (varsayılan http://127.0.0.1:8000)
  INTERNAL_API_KEY   (zorunlu; Ensar'dan alınır, git'e eklenmez)
  BEKLEME_SANIYE     (iş yokken bekleme, varsayılan 30)

Kullanım:
  python ai/worker.py          # sürekli çalışır, Ctrl+C ile durur
  python ai/worker.py --bir-kez  # bekleyen işleri bitirince çıkar
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from analiz import analiz_dogrulayici, haberi_isle, sema_bilgisi, sema_oku

AI_KLASORU = Path(__file__).resolve().parent
ZAMAN_ASIMI = 30  # HTTP isteği için saniye


class BackendHatasi(Exception):
    def __init__(self, durum, mesaj):
        super().__init__(f"HTTP {durum}: {mesaj}")
        self.durum = durum


def ayarlari_oku():
    """ai/.env dosyasını (varsa) okur; ortam değişkenleri önceliklidir."""
    env = AI_KLASORU / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if satir and not satir.startswith("#") and "=" in satir:
                anahtar, deger = satir.split("=", 1)
                os.environ.setdefault(anahtar.strip(), deger.strip().strip('"'))
    return {
        "url": os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/"),
        "anahtar": os.environ.get("INTERNAL_API_KEY", ""),
        "bekleme": int(os.environ.get("BEKLEME_SANIYE", "30")),
    }


class Backend:
    def __init__(self, url, anahtar):
        self.url = url
        self.anahtar = anahtar

    def _istek(self, yontem, yol, govde=None, servis=True):
        veri = None if govde is None else json.dumps(govde, ensure_ascii=False).encode("utf-8")
        basliklar = {"Accept": "application/json"}
        if veri is not None:
            basliklar["Content-Type"] = "application/json"
        if servis:
            basliklar["X-API-Key"] = self.anahtar
        istek = urllib.request.Request(self.url + yol, data=veri, headers=basliklar, method=yontem)
        try:
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as cevap:
                return cevap.status, json.loads(cevap.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as hata:
            icerik = hata.read().decode("utf-8", "replace")
            try:
                icerik = json.loads(icerik).get("detail", icerik)
            except (ValueError, AttributeError):
                pass
            raise BackendHatasi(hata.code, icerik) from None

    def sirket_adlari(self):
        """GET /api/v1/stocks -> {sembol: şirket adı}. Hata olursa boş döner."""
        try:
            _, veri = self._istek("GET", "/api/v1/stocks", servis=False)
            return {h["symbol"]: h["company_name"] for h in veri.get("stocks", []) if h.get("company_name")}
        except (BackendHatasi, OSError) as hata:
            print(f"Uyarı: hisse listesi alınamadı ({hata}); modele sadece kodlar verilecek.")
            return {}

    def is_al(self):
        _, veri = self._istek("POST", "/api/v1/internal/analysis-jobs/claim")
        return veri.get("job")

    def analizi_kaydet(self, analiz):
        return self._istek("POST", "/api/v1/internal/analyses", analiz)

    def basarisiz_bildir(self, news_id, mesaj):
        yol = f"/api/v1/internal/analysis-jobs/{urllib.parse.quote(news_id, safe='')}/fail"
        return self._istek("POST", yol, {"error": mesaj[:2000]})


def isi_isle(backend, is_, adlar, dogrulayici, surum, uyari):
    """Tek bir işi işler. Başarılıysa True döner."""
    haber = is_["news"]
    haber["sirket_adlari"] = {s: adlar[s] for s in haber["symbols"] if s in adlar}
    baslik = haber["title"][:60]
    basla = time.time()

    analiz, deneme, son_hata = haberi_isle(haber, dogrulayici, surum, uyari)

    if analiz is not None:
        try:
            durum, _ = backend.analizi_kaydet(analiz)
            etkiler = ", ".join(f"{i['symbol']}={i['direction']}" for i in analiz["impacts"]) or "hisse yok"
            print(f"  OK ({time.time() - basla:.1f} sn, HTTP {durum}) {baslik} -> {etkiler}")
            return True
        except BackendHatasi as hata:
            son_hata = f"backend analizi reddetti: {hata}"
        except OSError as hata:
            son_hata = f"backend'e ulaşılamadı: {hata}"

    print(f"  BAŞARISIZ {baslik}\n     {son_hata}")
    try:
        backend.basarisiz_bildir(haber["news_id"], son_hata)
    except (BackendHatasi, OSError) as hata:
        # Bildirilemezse kilit 15 dk sonra düşer, backend işi tekrar verir
        print(f"     (hata backend'e bildirilemedi: {hata})")
    return False


def main():
    bir_kez = "--bir-kez" in sys.argv
    ayar = ayarlari_oku()
    if not ayar["anahtar"]:
        sys.exit("INTERNAL_API_KEY tanımlı değil. ai/.env dosyasına ekleyin (Ensar'dan alın).")

    sema = sema_oku()
    surum, uyari = sema_bilgisi(sema)
    dogrulayici = analiz_dogrulayici(sema)
    backend = Backend(ayar["url"], ayar["anahtar"])
    adlar = backend.sirket_adlari()

    print(f"Worker başladı: {ayar['url']} | Analysis v{surum} | {len(adlar)} hisse adı yüklendi")
    tamam = hata = 0
    try:
        while True:
            try:
                is_ = backend.is_al()
            except BackendHatasi as h:
                if h.durum == 401:
                    sys.exit("API anahtarı geçersiz (HTTP 401). INTERNAL_API_KEY'i kontrol edin.")
                print(f"İş alınamadı: {h}")
                is_ = None
            except OSError as h:
                print(f"Backend'e ulaşılamıyor: {h}")
                is_ = None

            if is_ is None:
                if bir_kez:
                    break
                time.sleep(ayar["bekleme"])
                continue

            print(f"[{is_['attempts']}. deneme] {is_['news_id']}")
            if isi_isle(backend, is_, adlar, dogrulayici, surum, uyari):
                tamam += 1
            else:
                hata += 1
    except KeyboardInterrupt:
        print("\nDurduruldu.")
    print(f"Toplam: {tamam} analiz kaydedildi, {hata} başarısız.")


if __name__ == "__main__":
    main()
