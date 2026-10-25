import yfinance as yf


class DataLoader:

    def __init__(self, symbol: str, period: str = "1y"):
        self.symbol = symbol
        self.period = period

    def _calculate_rsi(self, df, window=14):
        """Private metot: RSI değerini hesaplar."""
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_data(self):
        """Veriyi çeker, indikatörleri ekler ve temizlenmiş DataFrame döner."""
        print(f"[+] {self.symbol} için veri indiriliyor...")
        ticker = yf.Ticker(self.symbol)
        df = ticker.history(period=self.period)

        if df.empty:
            raise ValueError(
                f"'{self.symbol}' için veri bulunamadı! Sembolü kontrol edin."
            )

        # İndikatörleri ekle
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["RSI"] = self._calculate_rsi(df, window=14)

        # Eksik (NaN) değerleri temizle
        df.dropna(inplace=True)

        return df
