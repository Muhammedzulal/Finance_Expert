class TechnicalAnalyzer:

    def __init__(self, df):
        self.df = df

    def analyze(self):
        """En son satırdaki veriyi alıp Türkçe yorum üretir."""
        son_kapanis = self.df["Close"].iloc[-1]
        son_sma = self.df["SMA_50"].iloc[-1]
        son_rsi = self.df["RSI"].iloc[-1]

        yorumlar = []

        # 1. Trend Analizi
        if son_kapanis > son_sma:
            yorumlar.append(
                f"Fiyat ({son_kapanis:.2f}), 50 günlük ortalamanın ({son_sma:.2f}) üzerinde. Genel trend YUKARI."
            )
        else:
            yorumlar.append(
                f"Fiyat ({son_kapanis:.2f}), 50 günlük ortalamanın ({son_sma:.2f}) altında. Genel trend AŞAĞI."
            )

        # 2. RSI Analizi
        if son_rsi > 70:
            yorumlar.append(
                f"RSI değeri {son_rsi:.2f} ile AŞIRI ALIM bölgesinde. Kısa vadede düşüş/düzeltme gelebilir."
            )
        elif son_rsi < 30:
            yorumlar.append(
                f"RSI değeri {son_rsi:.2f} ile AŞIRI SATIŞ bölgesinde. Tepki yükselişi gelebilir."
            )
        else:
            yorumlar.append(
                f"RSI değeri {son_rsi:.2f} ile nötr bölgede. Dengeli seyir var."
            )

        return "\n".join(yorumlar)
