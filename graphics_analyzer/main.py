from analyzer import TechnicalAnalyzer
from data_loader import DataLoader
from plotter import ChartPlotter


def main():
    # Analiz etmek istediğimiz tüm semboller (Döviz, BIST Hisse, Kripto vb.)
    takip_listesi = ["USDTRY=X", "THYAO.IS", "BTC-USD"]

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

        except Exception as e:
            print(f"[!] {symbol} işlenirken hata oluştu: {e}")


if __name__ == "__main__":
    main()
