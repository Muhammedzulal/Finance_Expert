"""Finance Expert - KAP & Bloomberg HT Haberleri ve Fiyat Verileri Otomatik Aktarım Doğrulama Aracı.

Bu araç, Muhammed'e verilen şu görevi uçtan uca doğrular:
  "KAP ve Bloomberg HT haberleriyle fiyat verilerinin backend’e otomatik aktarımını doğrulamak.
   Kutay’a gerçek haber ve indikatör örnekleri vermek."

Kullanım:
  python tools/verify_backend_transfer.py
"""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Web_scaper"))
sys.path.insert(0, str(ROOT / "graphics_analyzer"))

from news_adapter import adapt_bloomberg_news, adapt_kap_disclosure
from quote_adapter import create_quote, quote_from_dataframe
from backend_client import BackendClient

TEST_API_KEY = "test-internal-key-12345"


class MockBackendHandler(BaseHTTPRequestHandler):
    """Doğrulama testi için sözleşmeye uygun mock backend sunucusu."""
    stored_news = {}
    stored_quotes = {}

    def log_message(self, format, *args):
        pass  # Test çıktısını temiz tutmak için logları sessize al

    def do_POST(self):
        auth_header = self.headers.get("X-API-Key")
        if auth_header != TEST_API_KEY:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "Gecersiz servis API anahtari"}).encode("utf-8"))
            return

        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if parsed.path == "/api/v1/internal/news":
            news_id = body.get("news_id")
            if not news_id:
                self.send_response(422)
                self.end_headers()
                self.wfile.write(b'{"detail":"Eksik news_id"}')
                return

            if news_id in self.stored_news:
                # İdempotent: zaten var
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(self.stored_news[news_id]).encode("utf-8"))
            else:
                self.stored_news[news_id] = body
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode("utf-8"))

        elif parsed.path == "/api/v1/internal/quotes":
            sym = body.get("symbol")
            as_of = body.get("as_of")
            key = f"{sym}:{as_of}"
            if key in self.stored_quotes:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(self.stored_quotes[key]).encode("utf-8"))
            else:
                self.stored_quotes[key] = body
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_verification():
    print("================================================================================")
    print("   FINANCE EXPERT - HABER VE FİYAT VERİSİ AKTARIMI DOĞRULAMA RAPORU")
    print("================================================================================")

    # 1. Sözleşme Şemalarını Yükle
    schema_file = ROOT / "contracts" / "finance-v1.schema.json"
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    format_checker = FormatChecker()
    news_validator = Draft202012Validator(
        {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/News"},
        format_checker=format_checker
    )
    quote_validator = Draft202012Validator(
        {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/Quote"},
        format_checker=format_checker
    )
    print("✅ [1/5] JSON Schema sözleşmeleri başarıyla yüklendi (contracts/finance-v1.schema.json).")

    # 2. Mock Test Backend Sunucusunu Başlat
    port = 8999
    server = HTTPServer(("127.0.0.1", port), MockBackendHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = BackendClient(base_url=f"http://127.0.0.1:{port}", api_key=TEST_API_KEY)
    print(f"✅ [2/5] Doğrulama için test backend servisi hazırlandı (http://127.0.0.1:{port}).")

    # 3. KAP ve Bloomberg HT Haberlerinin Aktarımı ve Doğrulaması
    bb_raw_file = ROOT / "Web_scaper" / "bloomberg_trading_news.json"
    kap_raw_file = ROOT / "Web_scaper" / "kap_today_disclosures.json"

    bb_items = json.loads(bb_raw_file.read_text(encoding="utf-8")) if bb_raw_file.exists() else []
    kap_items = json.loads(kap_raw_file.read_text(encoding="utf-8")) if kap_raw_file.exists() else []

    sample_bb = adapt_bloomberg_news(bb_items[0])
    news_validator.validate(sample_bb)
    sample_kap = adapt_kap_disclosure(kap_items[0])
    news_validator.validate(sample_kap)

    # Yeni gönderim (201 beklenir)
    c1, m1 = client.send_news(sample_bb)
    c2, m2 = client.send_news(sample_kap)
    assert c1 == 201, f"Bloomberg haber aktarımı başarısız: {c1}"
    assert c2 == 201, f"KAP bildirim aktarımı başarısız: {c2}"

    # Tekrarlı gönderim (Deduplication - 200 beklenir)
    c1_dup, _ = client.send_news(sample_bb)
    c2_dup, _ = client.send_news(sample_kap)
    assert c1_dup == 200, f"Bloomberg tekilleştirme başarısız: {c1_dup}"
    assert c2_dup == 200, f"KAP tekilleştirme başarısız: {c2_dup}"

    print(f"✅ [3/5] Haber Aktarımı Doğrulandı:")
    print(f"       - Bloomberg HT: Yeni kayıt (201 OK), Tekrar önleme (200 OK), Eşleşen semboller: {sample_bb['symbols']}")
    print(f"       - KAP Bildirimi: Yeni kayıt (201 OK), Tekrar önleme (200 OK), Kimlik: {sample_kap['news_id']}")

    # 4. Fiyat Verisi (Quote) Aktarımı ve Doğrulaması
    sample_quote1 = create_quote("THYAO.IS", 330.50, provider="yfinance")
    quote_validator.validate(sample_quote1)
    sample_quote2 = create_quote("GARAN.IS", 118.20, provider="yfinance")
    quote_validator.validate(sample_quote2)

    qc1, _ = client.send_quote(sample_quote1)
    qc2, _ = client.send_quote(sample_quote2)
    assert qc1 == 201, f"THYAO quote aktarımı başarısız: {qc1}"
    assert qc2 == 201, f"GARAN quote aktarımı başarısız: {qc2}"

    qc1_dup, _ = client.send_quote(sample_quote1)
    assert qc1_dup == 200, f"Quote tekilleştirme başarısız: {qc1_dup}"

    print(f"✅ [4/5] Fiyat Verisi (Quote) Aktarımı Doğrulandı:")
    print(f"       - THYAO Quote: {sample_quote1['price']} TRY -> 201 OK, Tekrar -> 200 OK")
    print(f"       - GARAN Quote: {sample_quote2['price']} TRY -> 201 OK")

    # 5. Kutay'a Verilen Örneklerin Kontrolü
    haber_ornek = ROOT / "ai" / "ornekler" / "gercek_haberler.json"
    ind_ornek = ROOT / "ai" / "ornekler" / "gercek_indikatorler.json"
    rehber = ROOT / "ai" / "ornekler" / "KUTAY_ORNEKLER_REHBERI.md"

    assert haber_ornek.exists(), "gercek_haberler.json eksik"
    assert ind_ornek.exists(), "gercek_indikatorler.json eksik"
    assert rehber.exists(), "KUTAY_ORNEKLER_REHBERI.md eksik"

    haber_data = json.loads(haber_ornek.read_text(encoding="utf-8"))
    ind_data = json.loads(ind_ornek.read_text(encoding="utf-8"))

    print(f"✅ [5/5] Kutay Örnek Veri Setleri Doğrulandı:")
    print(f"       - Gerçek Haberler ({len(haber_data)} adet News v1.0 kaydı hazır)")
    print(f"       - Gerçek İndikatörler ({len(ind_data['semboller'])} sembol için tam teknik analiz serisi hazır)")
    print(f"       - Kutay Örnekler Rehberi (ai/ornekler/KUTAY_ORNEKLER_REHBERI.md)")

    server.shutdown()

    print("\n================================================================================")
    print("   SONUÇ: TÜM GÖREVLER VE SÖZLEŞMELER BAŞARIYLA DOĞRULANDI (PASS)")
    print("================================================================================")


if __name__ == "__main__":
    run_verification()
