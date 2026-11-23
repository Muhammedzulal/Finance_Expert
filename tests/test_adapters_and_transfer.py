"""Haber ve Fiyat Verisi Adaptörleri ile Backend Aktarım Testleri.

Kapsam:
  - Web_scaper/news_adapter.py (KAP & Bloomberg HT -> News v1.0)
  - graphics_analyzer/quote_adapter.py (yfinance/DataFrame -> Quote v1.0)
  - Web_scaper/backend_client.py (POST /api/v1/internal/news & POST /api/v1/internal/quotes)
  - contracts/finance-v1.schema.json sözleşme doğrulaması
  - ai/ornekler/ örnek veri setlerinin bütünlük kontrolü
"""

import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "Web_scaper"))
sys.path.insert(0, str(ROOT / "graphics_analyzer"))

from news_adapter import (
    adapt_bloomberg_news,
    adapt_kap_disclosure,
    normalize_url,
    extract_symbols,
    extract_keywords,
    clean_html,
    tr_lower,
)
from quote_adapter import (
    clean_symbol,
    format_money,
    create_quote,
)
from backend_client import BackendClient

SCHEMA = json.loads((ROOT / "contracts" / "finance-v1.schema.json").read_text(encoding="utf-8"))
FORMAT_CHECKER = FormatChecker()
NEWS_VALIDATOR = Draft202012Validator(
    {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/News"},
    format_checker=FORMAT_CHECKER
)
QUOTE_VALIDATOR = Draft202012Validator(
    {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], "$ref": "#/$defs/Quote"},
    format_checker=FORMAT_CHECKER
)


class TestNewsAdapter(unittest.TestCase):
    def test_url_normalization(self):
        url = "  HTTPS://WWW.BloombergHT.COM:443/haber-detay?id=1#yorumlar  "
        norm = normalize_url(url)
        self.assertEqual(norm, "https://www.bloomberght.com/haber-detay?id=1")

    def test_symbol_extraction_from_text(self):
        text = "Türk Hava Yolları yeni uçak alımı açıkladı, Aselsan ve Garanti BBVA hisseleri de yükseldi."
        symbols = extract_symbols(text)
        self.assertIn("THYAO", symbols)
        self.assertIn("ASELS", symbols)
        self.assertIn("GARAN", symbols)

    def test_symbol_extraction_from_kap_title(self):
        title = "ÖZEL DURUM AÇIKLAMASI / CEMAS"
        symbols = extract_symbols(title)
        self.assertEqual(symbols, ["CEMAS"])

    def test_bloomberg_adaptation_valid(self):
        raw = {
            "title": "SPK, iki şirketin sermaye artırımını onayladı",
            "summary": "Mercan Kimya ve Şekerbank sermaye artırımı yapacak.",
            "link": "https://www.bloomberght.com/spk-onayladi-1234",
            "published": "Fri, 16 Oct 2026 21:04:41 GMT",
            "fetched_at": "2026-10-19 09:53:19",
            "matched_keywords": ["sermaye artırımı"],
        }
        adapted = adapt_bloomberg_news(raw)
        self.assertEqual(adapted["schema_version"], "1.0")
        self.assertTrue(adapted["news_id"].startswith("bloomberg_ht:"))
        self.assertEqual(adapted["source"], "BLOOMBERG_HT")
        self.assertIsNone(adapted["source_id"])
        self.assertEqual(adapted["symbols"], ["SKBNK", "MERCN"])
        self.assertIn("sermaye artırımı", adapted["matched_keywords"])
        self.assertIsNone(adapted["disclosure_type"])
        # JSON Schema doğrulaması
        NEWS_VALIDATOR.validate(adapted)

    def test_kap_adaptation_valid(self):
        raw = {
            "source": "KAP",
            "disclosure_id": "1683417",
            "stock_code": "CEMAS",
            "title": "IŞIKLAR ENERJİ VE YAPI HOLDİNG A.Ş.Özel Durum Açıklaması / CEMAS",
            "disclosure_type": "Özel Durum Açıklaması (Genel)",
            "summary": "İştirakimiz in Çemaş Pay Alışı",
            "detail_url": "https://www.kap.org.tr/tr/Bildirim/1683417"
        }
        adapted = adapt_kap_disclosure(raw)
        self.assertEqual(adapted["schema_version"], "1.0")
        self.assertEqual(adapted["news_id"], "kap:1683417")
        self.assertEqual(adapted["source"], "KAP")
        self.assertEqual(adapted["source_id"], "1683417")
        self.assertIn("CEMAS", adapted["symbols"])
        self.assertEqual(adapted["disclosure_type"], "Özel Durum Açıklaması (Genel)")
        # JSON Schema doğrulaması
        NEWS_VALIDATOR.validate(adapted)

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            adapt_bloomberg_news({"title": "Test", "link": "http://insecure.com"})

    def test_empty_title_raises(self):
        with self.assertRaises(ValueError):
            adapt_bloomberg_news({"title": "   ", "link": "https://valid.com"})


class TestQuoteAdapter(unittest.TestCase):
    def test_clean_symbol(self):
        self.assertEqual(clean_symbol("THYAO.IS"), "THYAO")
        self.assertEqual(clean_symbol("garan.is"), "GARAN")
        self.assertEqual(clean_symbol("ASELS"), "ASELS")

    def test_format_money(self):
        self.assertEqual(format_money(330.5), "330.50")
        self.assertEqual(format_money(Decimal("100.25")), "100.25")
        self.assertEqual(format_money("125"), "125.00")
        self.assertEqual(format_money("125,75"), "125.75")

    def test_quote_creation_and_validation(self):
        quote = create_quote(
            symbol="THYAO.IS",
            price=328.75,
            as_of=datetime(2026, 11, 23, 14, 0, 0, tzinfo=timezone.utc),
            provider="yfinance"
        )
        self.assertEqual(quote["schema_version"], "1.0")
        self.assertEqual(quote["symbol"], "THYAO")
        self.assertEqual(quote["price"], "328.75")
        self.assertEqual(quote["currency"], "TRY")
        self.assertEqual(quote["provider"], "yfinance")
        self.assertFalse(quote["is_delayed"])
        # JSON Schema doğrulaması
        QUOTE_VALIDATOR.validate(quote)

    def test_invalid_symbol_raises(self):
        with self.assertRaises(ValueError):
            create_quote(symbol="1234INVALID#", price=100.0)


class TestBackendClient(unittest.TestCase):
    def setUp(self):
        self.client = BackendClient(base_url="http://testbackend:8000", api_key="secret-key")

    @patch("urllib.request.urlopen")
    def test_send_news_created_201(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.read.return_value = json.dumps({"news_id": "kap:1001"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        code, msg = self.client.send_news({"news_id": "kap:1001"})
        self.assertEqual(code, 201)
        self.assertIn("Yeni haber", msg)

    @patch("urllib.request.urlopen")
    def test_send_news_duplicate_200(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"news_id": "kap:1001"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        code, msg = self.client.send_news({"news_id": "kap:1001"})
        self.assertEqual(code, 200)
        self.assertIn("tekrar", msg)

    @patch("urllib.request.urlopen")
    def test_send_quote_created_201(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.read.return_value = json.dumps({"symbol": "THYAO", "price": "330.00"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        code, msg = self.client.send_quote({"symbol": "THYAO", "price": "330.00"})
        self.assertEqual(code, 201)
        self.assertIn("Fiyat kaydedildi", msg)

    @patch("urllib.request.urlopen")
    def test_batch_news_transfer(self, mock_urlopen):
        # 1. haber 201, 2. haber 200 (duplicate)
        resp1 = MagicMock(status=201, read=lambda: b'{}')
        resp2 = MagicMock(status=200, read=lambda: b'{}')
        mock_urlopen.return_value.__enter__.side_effect = [resp1, resp2]

        items = [{"news_id": "item1"}, {"news_id": "item2"}]
        stats = self.client.send_news_batch(items)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["duplicate"], 1)
        self.assertEqual(stats["failed"], 0)


class TestKutaySamples(unittest.TestCase):
    def test_gercek_haberler_samples(self):
        haber_file = ROOT / "ai" / "ornekler" / "gercek_haberler.json"
        self.assertTrue(haber_file.exists(), "gercek_haberler.json mevcut olmalı")
        items = json.loads(haber_file.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(items), 20)

        # Tüm haberlerin şemaya uyduğunu doğrula
        for item in items:
            NEWS_VALIDATOR.validate(item)

        # En az birkaç haberde hisse sembolü bulunmalı
        with_syms = [i for i in items if i["symbols"]]
        self.assertGreater(len(with_syms), 5)

    def test_gercek_indikatorler_samples(self):
        ind_file = ROOT / "ai" / "ornekler" / "gercek_indikatorler.json"
        self.assertTrue(ind_file.exists(), "gercek_indikatorler.json mevcut olmalı")
        data = json.loads(ind_file.read_text(encoding="utf-8"))
        self.assertIn("semboller", data)
        symbols = data["semboller"]

        expected = ["THYAO.IS", "GARAN.IS", "ASELS.IS", "USDTRY=X", "EURTRY=X", "GC=F", "BTC-USD", "ETH-USD"]
        for sym in expected:
            self.assertIn(sym, symbols)
            entry = symbols[sym]
            self.assertIn("son_kapanis", entry)
            self.assertIn("guncel_gostergeler", entry)
            self.assertIn("piyasa_baglami", entry)
            self.assertIn("son_25_gun_serisi", entry)
            self.assertEqual(len(entry["son_25_gun_serisi"]), 25)


if __name__ == "__main__":
    unittest.main()
