# bazı metotları deneyorum o yüzden burda  :9
import matplotlib.pyplot as plt
import yfinance as yf

"""days = ["Pzt", "Sal", "Çar", "Per", "Cuma", "Cmt", "Paz"]
temperaturesE = [12, 14, 11, 15, 17, 18, 16]
temperaturesI = [18, 19, 17, 20, 21, 22, 20]

plt.plot(days, temperaturesE, color="red", linestyle="--")
plt.plot(days, temperaturesI, color="blue", linestyle="-")
plt.title("Elazığ vs İstanbul Haftalık Sıcaklık Karşılaştırması")
plt.ylabel("Sıcaklıklar")
plt.xlabel("Günler")
plt.legend(["Elazığ", "İstanbul"])
plt.grid(True)
plt.show()"""

"""
langs = ["Python", "C++", "Java", "JavaScript"]
points = [95, 70, 80, 85]
plt.bar(langs, points, color="green")
plt.title("Popularity of Programming Languages")
plt.xlabel("Langs")
plt.ylabel("Points")
plt.show()"""
"""
days = ["Pzt", "Sal", "Çar", "Per", "Cuma"]
prices = [100, 102, 101, 105, 108]
volume = [500, 700, 400, 900, 1200]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
ax1.plot(days, prices)
ax1.set_title("Fiyat Grafiği")
ax2.bar(days, volume)
ax2.set_title("Hacim Grafiği")
plt.show()"""

"""ticker = yf.Ticker("USDTRY=X")
df = ticker.history(period="1y")

dun_kapanis = df["Close"].iloc[-2]
bugun_max = df["High"].iloc[-1]
y1max = df["High"].max()
y1min = df["High"].min()
df["SMA_20"] = df["Close"].rolling(window=20).mean()
print(df.tail(3))
print("*" * 50)

print(f"Dünün Kapanış Fiyatı : {dun_kapanis:.2f} TL")
print(f"Bugünün En Yükseği   : {bugun_max:.2f} TL")
print(f"1 Yılın En Yükseği   : {y1max:.5f} TL")
print(f"1 Yılın En Düşüğü    : {y1min:.5f} TL")"""


df = yf.Ticker("USDTRY=X").history(period="3mo")


df["SMA_20"] = df["Close"].rolling(window=20).mean()
df["Pct_Change"] = df["Close"].pct_change() * 100

df.dropna(inplace=True)

print(df[["Close", "SMA_20", "Pct_Change"]].tail(5))
