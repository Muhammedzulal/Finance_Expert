"""BIST hisse fiyatlarını yfinance üzerinden çekip backend Quote API'sine aktaran modül.

Uç:
  POST /api/v1/internal/quotes

Kullanım:
  python graphics_analyzer/sync_quotes.py
  python graphics_analyzer/sync_quotes.py --sembol THYAO GARAN ASELS
  python graphics_analyzer/sync_quotes.py --validate-only
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "graphics_analyzer"))
sys.path.insert(0, str(ROOT / "Web_scaper"))

from data_loader import DataLoader
from quote_adapter import quote_from_dataframe, create_quote
from backend_client import BackendClient

VARSAYILAN_HISSELER = [
    "THYAO.IS",
    "GARAN.IS",
    "ASELS.IS",
    "SISE.IS",
    "KCHOL.IS",
    "TUPRS.IS",
    "AKBNK.IS",
    "BIMAS.IS",
]


def sync_stock_quotes(symbols: list[str] | None = None, validate_only: bool = False):
    symbols = symbols or VARSAYILAN_HISSELER
    client = BackendClient()

    print("==================================================================")
    print("   FINANCE EXPERT - FİYAT VERİSİ (QUOTE) AKTARIM PİPELINE")
    print(f"   Hedef Backend: {client.base_url}")
    print(f"   İşlenecek Semboller: {', '.join(symbols)}")
    print("==================================================================")

    quotes = []
    for sym in symbols:
        # Quote sözleşmesi yalnız TRY bazlı BIST hisselerini kapsar
        if not sym.endswith(".IS") and sym not in ("THYAO", "GARAN", "ASELS", "SISE", "KCHOL"):
            continue

        raw_sym = sym if sym.endswith(".IS") else f"{sym}.IS"
        print(f"\n[+] {raw_sym} için son fiyat indiriliyor...")
        try:
            loader = DataLoader(symbol=raw_sym, period="5d")
            df = loader.get_data()
            quote = quote_from_dataframe(symbol=raw_sym, df=df, provider="yfinance")
            quotes.append(quote)
            print(f"    -> Hazırlandı: {quote['symbol']} = {quote['price']} TRY ({quote['as_of']})")
        except Exception as e:
            print(f"    [!] {raw_sym} fiyatı alınamadı: {e}")

    print(f"\n✅ Toplam {len(quotes)} geçerli Quote v1.0 kaydı üretildi.")

    if validate_only:
        print("\n🔎 '--validate-only' aktif; backend'e gönderim yapılmadı.")
        return quotes

    print(f"\n📡 Backend'e aktarılıyor ({client.base_url}/api/v1/internal/quotes)...")
    stats = client.send_quotes_batch(quotes)

    print("\n------------------------------------------------------------------")
    print("   FİYAT AKTARIM ÖZETİ")
    print("------------------------------------------------------------------")
    print(f"   İşlenen Fiyat Sayısı : {stats['total']}")
    print(f"   Yeni Eklenen (201)   : {stats['created']}")
    print(f"   Mevcut/Tekrar (200)  : {stats['duplicate']}")
    print(f"   Başarısız/Hata       : {stats['failed']}")
    print("------------------------------------------------------------------")

    return quotes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hisse fiyatlarını backend'e aktarma")
    parser.add_argument("--sembol", nargs="+", help="İşlenecek semboller (ör. THYAO.IS GARAN.IS)")
    parser.add_argument("--validate-only", action="store_true", help="Yalnızca doğrula, aktarma")
    args = parser.parse_args()

    sync_stock_quotes(symbols=args.sembol, validate_only=args.validate_only)
