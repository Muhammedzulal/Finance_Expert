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

        # 1. Mevcut İndikatörler
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["RSI"] = self._calculate_rsi(df, window=14)

        # 2. Yeni Eklenen İndikatörler
        # EMA 20 (Üstel Hareketli Ortalama)
        df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

        # Bollinger Bantları (20 Periyotluk SMA + 2 Standart Sapma)
        orta_bant = df["Close"].rolling(window=20).mean()
        std = df["Close"].rolling(window=20).std()
        df["Bollinger_Upper"] = orta_bant + (std * 2)
        df["Bollinger_Lower"] = orta_bant - (std * 2)

        # Günlük Yüzdesel Değişim (%)
        df["Pct_Change"] = df["Close"].pct_change() * 100

        # Eksik (NaN) değerleri temizle
        df.dropna(inplace=True)

        return df
