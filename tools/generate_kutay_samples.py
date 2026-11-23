"""Kutay'ın AI modülü için gerçek haber ve indikatör örnekleri üretme aracı.

Üretilen çıktılar:
  - ai/ornekler/gercek_haberler.json: Sözleşmeye (News v1.0) tam uyumlu, BIST sembolleri eşleşmiş gerçek KAP ve Bloomberg HT haberleri.
  - ai/ornekler/gercek_indikatorler.json: 8 sembol için graphics_analyzer tarafından üretilen gerçek indikatör değerleri ve piyasa özetleri.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Web_scaper"))
sys.path.insert(0, str(ROOT / "graphics_analyzer"))
sys.path.insert(0, str(ROOT / "ai"))

from news_adapter import adapt_bloomberg_news, adapt_kap_disclosure
from data_loader import DataLoader
from analyzer import TechnicalAnalyzer

BLOOMBERG_JSON = ROOT / "Web_scaper" / "bloomberg_trading_news.json"
KAP_JSON = ROOT / "Web_scaper" / "kap_today_disclosures.json"
OUT_DIR = ROOT / "ai" / "ornekler"


def generate_news_samples():
    print("[+] Gerçek haber örnekleri oluşturuluyor...")
    news_items = []

    if BLOOMBERG_JSON.exists():
        raw_bb = json.loads(BLOOMBERG_JSON.read_text(encoding="utf-8"))
        for item in raw_bb:
            try:
                adapted = adapt_bloomberg_news(item)
                news_items.append(adapted)
            except Exception as e:
                print(f"    [!] Bloomberg atlandı: {e}")

    if KAP_JSON.exists():
        raw_kap = json.loads(KAP_JSON.read_text(encoding="utf-8"))
        for item in raw_kap:
            try:
                adapted = adapt_kap_disclosure(item)
                news_items.append(adapted)
            except Exception as e:
                print(f"    [!] KAP atlandı: {e}")

    out_file = OUT_DIR / "gercek_haberler.json"
    out_file.write_text(json.dumps(news_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(news_items)} adet gerçek haber yazıldı -> {out_file}")
    return news_items


def generate_indicator_samples():
    print("\n[+] Gerçek indikatör örnekleri hesaplanıyor...")
    symbols = [
        # BIST Hisseleri
        "THYAO.IS",
        "GARAN.IS",
        "ASELS.IS",
        # Döviz & Maden
        "USDTRY=X",
        "EURTRY=X",
        "GC=F",
        # Kripto
        "BTC-USD",
        "ETH-USD",
    ]

    indicator_data = {
        "aciklama": "Muhammed (graphics_analyzer) tarafından üretilen gerçek indikatör ve piyasa bağlamı örnekleri",
        "olusturulma_tarihi": datetime.now(timezone.utc).isoformat(),
        "semboller": {},
    }

    for sym in symbols:
        print(f"    İndiriliyor: {sym}...")
        try:
            loader = DataLoader(symbol=sym, period="1y")
            df = loader.get_data()

            # Son 25 günün indikatör satırları (ai/grafik_yorum.py formatında)
            satirlar = []
            for tarih, s in df.tail(25).iterrows():
                satir = {
                    "tarih": tarih.date().isoformat() if hasattr(tarih, "date") else str(tarih)[:10],
                    "Close": round(float(s["Close"]), 4),
                    "SMA_50": round(float(s["SMA_50"]), 4),
                    "EMA_20": round(float(s["EMA_20"]), 4),
                    "RSI": round(float(s["RSI"]), 2),
                    "Bollinger_Upper": round(float(s["Bollinger_Upper"]), 4),
                    "Bollinger_Lower": round(float(s["Bollinger_Lower"]), 4),
                    "Pct_Change": round(float(s["Pct_Change"]), 2),
                }
                satirlar.append(satir)

            son = satirlar[-1]
            ilk = satirlar[0]
            kapanislar = [float(x) for x in df["Close"].dropna().tolist()]

            # ai/piyasa.py bağlam metrikleri
            degisim_1g = (kapanislar[-1] / kapanislar[-2] - 1) * 100 if len(kapanislar) > 1 else None
            degisim_5g = (kapanislar[-1] / kapanislar[-6] - 1) * 100 if len(kapanislar) > 5 else None
            degisim_20g = (kapanislar[-1] / kapanislar[-21] - 1) * 100 if len(kapanislar) > 20 else None
            sma50_val = son["SMA_50"]
            sma50_farki = (son["Close"] / sma50_val - 1) * 100 if sma50_val else None

            # TechnicalAnalyzer yorumu
            analyzer = TechnicalAnalyzer(df)
            yorum = analyzer.analyze()

            indicator_data["semboller"][sym] = {
                "son_kapanis": son["Close"],
                "guncel_gostergeler": {
                    "RSI_14": son["RSI"],
                    "SMA_50": son["SMA_50"],
                    "EMA_20": son["EMA_20"],
                    "Bollinger_Orta": round((son["Bollinger_Upper"] + son["Bollinger_Lower"]) / 2, 4),
                    "Bollinger_Ust": son["Bollinger_Upper"],
                    "Bollinger_Alt": son["Bollinger_Lower"],
                    "Son_Gun_Degisim_Yuzde": son["Pct_Change"],
                },
                "piyasa_baglami": {
                    "degisim_1g": round(degisim_1g, 2) if degisim_1g is not None else None,
                    "degisim_5g": round(degisim_5g, 2) if degisim_5g is not None else None,
                    "degisim_20g": round(degisim_20g, 2) if degisim_20g is not None else None,
                    "sma50_farki": round(sma50_farki, 2) if sma50_farki is not None else None,
                },
                "teknik_yorum_sablonu": yorum,
                "son_25_gun_serisi": satirlar,
            }
        except Exception as e:
            print(f"    [!] {sym} indikatörleri hesaplanırken hata: {e}")

    out_file = OUT_DIR / "gercek_indikatorler.json"
    out_file.write_text(json.dumps(indicator_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(indicator_data['semboller'])} sembol için indikatörler yazıldı -> {out_file}")
    return indicator_data


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_news_samples()
    generate_indicator_samples()
    print("\n🎉 Tüm örnekler başarıyla üretildi!")


if __name__ == "__main__":
    main()
