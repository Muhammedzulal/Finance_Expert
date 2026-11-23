import argparse
import os
import sys
from pathlib import Path

from analyzer import TechnicalAnalyzer
from data_loader import DataLoader
from plotter import ChartPlotter

# Quote adaptörü ve Backend client
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Web_scaper"))
from quote_adapter import quote_from_dataframe
from backend_client import BackendClient


def main(sync_backend: bool = True):
    # Analiz etmek istediğimiz tüm semboller (Döviz, BIST Hisse, Kripto vb.)
    takip_listesi = [
        # Döviz & Maden
        "USDTRY=X",
        "EURTRY=X",
        "GC=F",
        # BIST Hisseleri
        "THYAO.IS",
        "GARAN.IS",
        "ASELS.IS",
        # Kripto
        "BTC-USD",
        "ETH-USD",
    ]

    backend_client = BackendClient() if sync_backend else None

    for symbol in takip_listesi:
        print(f"\n==========================================")
        print(f"   {symbol} ANALİZİ BAŞLATILIYOR")
        print(f"==========================================")

        try:
            # 1. Veriyi Yükle (1 Yıllık periyot ile indiriyoruz)
            loader = DataLoader(symbol=symbol, period="1y")
            df = loader.get_data()

            # Son günün yüzdesel değişimi
            son_pct = df["Pct_Change"].iloc[-1]
            print(f"[i] Son Günlük Değişim: %{son_pct:.2f}")

            # 2. Yorumla
            analyzer = TechnicalAnalyzer(df)
            yorum = analyzer.analyze()

            print("\n--- TEKNİK YORUM ---")
            print(yorum)

            # 3. Grafiği Çiz ve Kaydet
            dosya_adi = f"{symbol.replace('=', '_').replace('-', '_')}_grafik.png"
            plotter = ChartPlotter(df, symbol=symbol)
            plotter.plot_and_save(output_filename=dosya_adi)

            # 4. BIST Hisseleri için Fiyatı Backend'e Aktar
            if sync_backend and backend_client and symbol.endswith(".IS"):
                try:
                    quote = quote_from_dataframe(symbol, df, provider="yfinance")
                    status_code, msg = backend_client.send_quote(quote)
                    print(f"[📡 Backend Quote] {symbol} -> HTTP {status_code}: {msg}")
                except Exception as q_err:
                    print(f"[!] Quote aktarımı hatası ({symbol}): {q_err}")

        except Exception as e:
            print(f"[!] {symbol} işlenirken hata oluştu: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graphics Analyzer ve Fiyat Aktarımı")
    parser.add_argument("--no-backend", action="store_true", help="Backend fiyat aktarımını devre dışı bırak")
    args = parser.parse_args()

    main(sync_backend=not args.no_backend)
