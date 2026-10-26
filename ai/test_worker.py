"""AI worker testleri. Ollama, MySQL veya gerçek backend GEREKMEZ.

Sahte bir model ve backend'in iç uçlarını taklit eden küçük bir HTTP sunucusu
kullanır. Çalıştırma:  python ai/test_worker.py
"""

import json
import re
import sys
import threading
import types
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ---- Sahte model: ollama modülünün yerine geçer ----
def sahte_chat(model, messages, options, **kwargs):
    istem = messages[1]["content"]
    kodlar = re.findall(r"^- ([A-Z0-9]+)", istem, re.M)
    if "YASAKLI" in istem:
        gerekce = "THYAO al"
    else:
        gerekce = "Bilgi sınırlı olduğundan etki belirsiz."
    etkiler = [{"hisse": "KLRO" if k == "KLRHO" else k,  # model harf düşürür
                "etki": "olumlu", "guven": "orta", "gerekce": gerekce} for k in kodlar]
    etkiler.append({"hisse": "UYDURMA", "etki": "olumlu", "guven": "yuksek", "gerekce": "x"})
    icerik = json.dumps({"ozet": "Haber özeti.", "etkiler": etkiler}, ensure_ascii=False)
    return types.SimpleNamespace(message=types.SimpleNamespace(content=icerik))


sys.modules["ollama"] = types.SimpleNamespace(chat=sahte_chat)

import analiz  # noqa: E402
import worker  # noqa: E402

ANAHTAR = "test-anahtari"


def haber(news_id, baslik, semboller):
    return {"schema_version": "1.0", "news_id": news_id, "source": "KAP", "source_id": "1",
            "title": baslik, "summary": "", "url": "https://example.com", "published_at": None,
            "fetched_at": "2026-10-26T10:00:00+00:00", "symbols": semboller,
            "matched_keywords": [], "disclosure_type": None}


class SahteBackend(BaseHTTPRequestHandler):
    """backend/main.py'deki claim / analyses / fail davranışının sadeleştirilmiş kopyası."""
    isler, kayitlar, hatalar = {}, {}, []

    def log_message(self, *args):
        pass

    def _gonder(self, kod, veri):
        govde = json.dumps(veri).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        if self.path == "/api/v1/stocks":
            return self._gonder(200, {"stocks": [
                {"symbol": "SKBNK", "company_name": "ŞEKERBANK T.A.Ş.", "market": "BIST", "is_active": True}]})
        self._gonder(404, {"detail": "yok"})

    def do_POST(self):
        if self.headers.get("X-API-Key") != ANAHTAR:
            return self._gonder(401, {"detail": "Gecersiz servis API anahtari"})
        uzunluk = int(self.headers.get("Content-Length", 0))
        govde = json.loads(self.rfile.read(uzunluk)) if uzunluk else None
        isler = SahteBackend.isler

        if self.path.endswith("/claim"):
            for nid, is_ in isler.items():
                if is_["status"] == "pending" and is_["attempts"] < 3:
                    is_["status"], is_["attempts"] = "processing", is_["attempts"] + 1
                    return self._gonder(200, {"job": {"news_id": nid, "status": "processing",
                                                      "attempts": is_["attempts"], "locked_until": None,
                                                      "news": is_["news"]}})
            return self._gonder(200, {"job": None})

        if self.path == "/api/v1/internal/analyses":
            izinli = {"schema_version", "analysis_id", "news_id", "model", "prompt_version",
                      "created_at", "summary", "impacts"}
            if set(govde) - izinli:
                return self._gonder(422, {"detail": "beklenmeyen alan"})
            semboller = isler[govde["news_id"]]["news"]["symbols"]
            if any(i["symbol"] not in semboller for i in govde["impacts"]):
                return self._gonder(422, {"detail": "Analizde haberle eslesmeyen hisse var"})
            SahteBackend.kayitlar[govde["news_id"]] = govde
            isler[govde["news_id"]]["status"] = "completed"
            return self._gonder(201, govde)

        if self.path.endswith("/fail"):
            nid = urllib.parse.unquote(self.path.split("/")[-2])
            SahteBackend.hatalar.append((nid, govde["error"]))
            isler[nid]["status"] = "pending" if isler[nid]["attempts"] < 3 else "failed"
            return self._gonder(200, {"news_id": nid})

        self._gonder(404, {"detail": "yok"})


class WorkerTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sunucu = HTTPServer(("127.0.0.1", 0), SahteBackend)
        threading.Thread(target=cls.sunucu.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.sunucu.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.shutdown()

    def setUp(self):
        SahteBackend.isler = {}
        SahteBackend.kayitlar = {}
        SahteBackend.hatalar = []
        sema = analiz.sema_oku()
        self.surum, self.uyari = analiz.sema_bilgisi(sema)
        self.dogrulayici = analiz.analiz_dogrulayici(sema)

    def is_ekle(self, *haberler):
        for h in haberler:
            SahteBackend.isler[h["news_id"]] = {"status": "pending", "attempts": 0, "news": h}

    def calistir(self):
        backend = worker.Backend(self.url, ANAHTAR)
        adlar = backend.sirket_adlari()
        while (is_ := backend.is_al()) is not None:
            worker.isi_isle(backend, is_, adlar, self.dogrulayici, self.surum, self.uyari)

    def test_basarili_analiz_kaydedilir_ve_semaya_uyar(self):
        self.is_ekle(haber("kap:1", "Şekerbank sermaye artırımı", ["SKBNK"]))
        self.calistir()
        kayit = SahteBackend.kayitlar["kap:1"]
        self.assertEqual([i["symbol"] for i in kayit["impacts"]], ["SKBNK"])  # UYDURMA atıldı
        self.assertEqual(kayit["impacts"][0]["direction"], "positive")
        self.assertEqual(kayit["impacts"][0]["confidence"], 0.6)
        self.assertEqual(list(self.dogrulayici.iter_errors(kayit)), [])

    def test_harf_dusuren_kod_eslestirilir(self):
        self.is_ekle(haber("kap:2", "Pay Alım Satım Bildirimi", ["KLRHO"]))
        self.calistir()
        self.assertEqual(SahteBackend.kayitlar["kap:2"]["impacts"][0]["symbol"], "KLRHO")

    def test_hissesiz_haber_bos_etkiyle_kaydedilir(self):
        self.is_ekle(haber("bloomberg_ht:3", "Faiz kararı açıklandı", []))
        self.calistir()
        self.assertEqual(SahteBackend.kayitlar["bloomberg_ht:3"]["impacts"], [])

    def test_yatirim_tavsiyesi_kaydedilmez_ve_basarisiz_bildirilir(self):
        self.is_ekle(haber("kap:4", "YASAKLI içerikli haber", ["THYAO"]))
        self.calistir()
        self.assertNotIn("kap:4", SahteBackend.kayitlar)
        self.assertEqual(SahteBackend.isler["kap:4"]["status"], "failed")
        self.assertEqual(len(SahteBackend.hatalar), 3)
        self.assertIn("işlem yönlendirmesi", SahteBackend.hatalar[0][1])

    def test_yanlis_anahtar_401_verir(self):
        with self.assertRaises(worker.BackendHatasi) as h:
            worker.Backend(self.url, "yanlis").is_al()
        self.assertEqual(h.exception.durum, 401)


class IcerikDenetimiTesti(unittest.TestCase):
    def test_yasakli_ifadeler(self):
        for metin in ["THYAO al", "Hisseyi satın al.", "Kesin kazanç sağlar.",
                      "Hedef fiyat 50 TL.", "Uzun vadede tutulmalı.", "Portföyünüze ekleyin."]:
            self.assertIsNotNone(analiz.yasak_ifade_bul(metin), metin)

    def test_normal_haber_dili(self):
        for metin in ["Şirket rakibini satın aldı.", "Satın alma işlemi tamamlandı.",
                      "Altın fiyatları yükseldi.", "Tutar açıklanmadı.", "Alım satım bildirimi yayımlandı.",
                      "Sermaye artırımı likiditeyi artırabilir."]:
            self.assertIsNone(analiz.yasak_ifade_bul(metin), metin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
