import os
import matplotlib.pyplot as plt


class ChartPlotter:

    def __init__(self, df, symbol: str):
        self.df = df
        self.symbol = symbol

    def plot_and_save(self, output_filename: str):
        """Grafiği çizer, kaydeder ve ekranda gösterir."""
        fig, (ax1, ax2) = plt.subplots(
            2,
            1,
            figsize=(12, 8),
            sharex=True,
            gridspec_kw={"height_ratios": [3, 1]},
        )

        # Üst Grafik: Fiyat, SMA 50, EMA 20 ve Bollinger Bantları
        # Üst Grafik: Fiyat, SMA 50 ve EMA 20
        ax1.plot(
            self.df.index,
            self.df["Close"],
            label="Kapanış",
            color="blue",
            linewidth=1.8,
        )
        ax1.plot(
            self.df.index,
            self.df["SMA_50"],
            label="50 SMA",
            color="orange",
            linestyle="--",
        )
        ax1.plot(
            self.df.index,
            self.df["EMA_20"],
            label="20 EMA",
            color="green",
            linestyle="-.",
        )

        # Bollinger Bantlarını Çizgi Yerine Şeffaf Alan Olarak Boyuyoruz (Daha Temiz Görünüm)
        ax1.fill_between(
            self.df.index,
            self.df["Bollinger_Lower"],
            self.df["Bollinger_Upper"],
            color="gray",
            alpha=0.15,
            label="Bollinger Bandı",
        )

        ax1.set_title(f"{self.symbol} - Teknik Analiz Grafiği")
        ax1.set_ylabel("Fiyat")
        ax1.legend(loc="upper left")
        ax1.grid(True, linestyle=":", alpha=0.6)

        # Alt Grafik: RSI
        ax2.plot(self.df.index, self.df["RSI"], label="RSI (14)", color="purple")
        ax2.axhline(70, color="red", linestyle="--", alpha=0.7, label="70 (Aşırı Alım)")
        ax2.axhline(
            30, color="green", linestyle="--", alpha=0.7, label="30 (Aşırı Satış)"
        )
        ax2.set_ylabel("RSI")
        ax2.set_ylim(0, 100)
        ax2.legend(loc="upper left")
        ax2.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        target_dir = "graphics_analyzer/graphics"
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, output_filename)
        plt.savefig(file_path, dpi=300)
        print(f"[+] Grafik kaydedildi: {os.path.abspath(file_path)}")

        # plt.show()
