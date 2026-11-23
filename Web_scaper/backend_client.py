"""Backend istemcisi: News ve Quote verilerini backend internal API uçlarına aktarır.

Uçlar:
  - POST /api/v1/internal/news   (Haber aktarımı)
  - POST /api/v1/internal/quotes (Fiyat/Quote aktarımı)
"""

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("backend_client")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

PROJE_KOKU = Path(__file__).resolve().parents[1]


def _ortam_yukle():
    """backend/.env, ai/.env veya .env.compose dosyalarından ayarları yükler."""
    olasi_dosyalar = [
        PROJE_KOKU / "backend" / ".env",
        PROJE_KOKU / "ai" / ".env",
        PROJE_KOKU / ".env.compose",
        PROJE_KOKU / ".env",
    ]
    for dosya in olasi_dosyalar:
        if dosya.exists():
            try:
                for line in dosya.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ.setdefault(k, v)
            except Exception:
                pass


_ortam_yukle()


class BackendClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 15
    ):
        self.base_url = (
            base_url
            or os.getenv("BACKEND_URL")
            or "http://127.0.0.1:8000"
        ).rstrip("/")
        self.api_key = api_key or os.getenv("INTERNAL_API_KEY") or ""
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str | None]:
        url = self.base_url + path
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                res_json = json.loads(body) if body else None
                return status_code, res_json, None
        except urllib.error.HTTPError as e:
            status_code = e.code
            err_body = e.read().decode("utf-8", "replace")
            err_msg = err_body
            try:
                parsed = json.loads(err_body)
                err_msg = parsed.get("detail", err_body)
            except Exception:
                pass
            return status_code, None, f"HTTP {status_code}: {err_msg}"
        except urllib.error.URLError as e:
            return 0, None, f"Bağlantı hatası: {e.reason}"
        except Exception as e:
            return 0, None, f"Beklenmeyen hata: {str(e)}"

    def send_news(self, news_item: dict[str, Any]) -> tuple[int, str]:
        """Haber kaydını POST /api/v1/internal/news ile aktarır.

        Döndürür: (status_code, mesaj)
          - 201: Yeni haber başarıyla oluşturuldu.
          - 200: Haber zaten mevcut (tekrarlı gönderim önlendi).
          - Diğer: Hata kodu ve hata mesajı.
        """
        code, resp, err = self._post("/api/v1/internal/news", news_item)
        if code == 201:
            return 201, f"Yeni haber kaydedildi: {news_item.get('news_id')}"
        elif code == 200:
            return 200, f"Haber zaten kayıtlı (tekrar): {news_item.get('news_id')}"
        else:
            return code, err or f"HTTP {code}"

    def send_quote(self, quote_item: dict[str, Any]) -> tuple[int, str]:
        """Fiyat/Quote kaydını POST /api/v1/internal/quotes ile aktarır.

        Döndürür: (status_code, mesaj)
          - 201: Yeni fiyat kaydı başarıyla eklendi.
          - 200: Fiyat zaten mevcut (aynı tarih ve kaynak).
          - Diğer: Hata kodu ve hata mesajı.
        """
        code, resp, err = self._post("/api/v1/internal/quotes", quote_item)
        sym = quote_item.get("symbol")
        pr = quote_item.get("price")
        if code == 201:
            return 201, f"Fiyat kaydedildi ({sym}: {pr} TRY)"
        elif code == 200:
            return 200, f"Fiyat zaten mevcut ({sym}: {pr} TRY)"
        else:
            return code, err or f"HTTP {code}"

    def send_news_batch(self, news_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Haber listesini topluca aktarır ve istatistik döner."""
        stats = {"total": len(news_items), "created": 0, "duplicate": 0, "failed": 0, "details": []}
        for item in news_items:
            code, msg = self.send_news(item)
            news_id = item.get("news_id")
            if code == 201:
                stats["created"] += 1
                stats["details"].append({"news_id": news_id, "status": "created", "code": code})
            elif code == 200:
                stats["duplicate"] += 1
                stats["details"].append({"news_id": news_id, "status": "duplicate", "code": code})
            else:
                stats["failed"] += 1
                stats["details"].append({"news_id": news_id, "status": "failed", "code": code, "error": msg})
        return stats

    def send_quotes_batch(self, quote_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Fiyat listesini topluca aktarır ve istatistik döner."""
        stats = {"total": len(quote_items), "created": 0, "duplicate": 0, "failed": 0, "details": []}
        for item in quote_items:
            code, msg = self.send_quote(item)
            sym = item.get("symbol")
            if code == 201:
                stats["created"] += 1
                stats["details"].append({"symbol": sym, "status": "created", "code": code})
            elif code == 200:
                stats["duplicate"] += 1
                stats["details"].append({"symbol": sym, "status": "duplicate", "code": code})
            else:
                stats["failed"] += 1
                stats["details"].append({"symbol": sym, "status": "failed", "code": code, "error": msg})
        return stats
