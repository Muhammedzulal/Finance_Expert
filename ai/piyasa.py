"""Hisse fiyat bağlamı: haberi yorumlarken modele verilecek sayısal piyasa bilgisi.

Muhammed'in graphics_analyzer modülüyle aynı veri kaynağını (Yahoo Finance,
yfinance) ve aynı RSI formülünü kullanır. Modele sadece SAYISAL GERÇEKLER
verilir ("RSI 72"); "düşüş gelebilir" gibi tahminler verilmez, çünkü analiz
alım/satım sinyali üretmemelidir (docs/analiz-ilkeleri.md).

yfinance kurulu değilse ya da veri alınamazsa analiz fiyat bağlamı olmadan
devam eder; fiyat verisi analizin ön koşulu değildir.
"""

import logging
import time

ONBELLEK_SURESI = 15 * 60  # Aynı hisse için 15 dakika tekrar indirme yapma
_onbellek = {}
_yfinance_uyarisi_verildi = False


def yuzde_degisim(kapanislar, gun):
    """Son 'gun' işlem günündeki yüzde değişim; veri yetmezse None."""
    if len(kapanislar) <= gun or kapanislar[-1 - gun] == 0:
        return None
    return (kapanislar[-1] / kapanislar[-1 - gun] - 1) * 100


def basit_ortalama(kapanislar, gun):
    if len(kapanislar) < gun:
        return None
    return sum(kapanislar[-gun:]) / gun


def rsi(kapanislar, pencere=14):
    """graphics_analyzer/data_loader.py ile aynı formül (basit hareketli ortalama)."""
    if len(kapanislar) <= pencere:
        return None
    farklar = [kapanislar[i] - kapanislar[i - 1] for i in range(len(kapanislar) - pencere, len(kapanislar))]
    kazanc = sum(f for f in farklar if f > 0) / pencere
    kayip = sum(-f for f in farklar if f < 0) / pencere
    if kayip == 0:
        return 100.0
    return 100 - 100 / (1 + kazanc / kayip)


def gostergeler(kapanislar):
    """Kapanış fiyatları listesinden (eskiden yeniye) özet göstergeler."""
    if not kapanislar:
        return None
    son = kapanislar[-1]
    sma50 = basit_ortalama(kapanislar, 50)
    return {
        "son_kapanis": son,
        "degisim_1g": yuzde_degisim(kapanislar, 1),
        "degisim_5g": yuzde_degisim(kapanislar, 5),
        "degisim_20g": yuzde_degisim(kapanislar, 20),
        "rsi14": rsi(kapanislar, 14),
        "sma50_farki": None if sma50 is None else (son / sma50 - 1) * 100,
    }


def _yahoo_kapanislari(sembol):
    """BIST sembolü için son ~3 ayın günlük kapanışları. Hata olursa None."""
    global _yfinance_uyarisi_verildi
    try:
        import yfinance as yf
    except ImportError:
        if not _yfinance_uyarisi_verildi:
            print("Bilgi: yfinance kurulu değil, analizler fiyat bağlamı olmadan yapılacak "
                  "(kurmak için: pip install yfinance).")
            _yfinance_uyarisi_verildi = True
        return None
    # yfinance kendi hata mesajlarını basmasın ("No data found" vb.); biz tek satır yazarız
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    try:
        df = yf.Ticker(f"{sembol}.IS").history(period="3mo")
        kapanislar = [float(x) for x in df["Close"].dropna().tolist()]
        if not kapanislar:
            print(f"Bilgi: {sembol} için fiyat verisi yok, bağlamsız analiz yapılacak.")
        return kapanislar or None
    except Exception as hata:  # Ağ hatası, bilinmeyen sembol vb.
        print(f"Bilgi: {sembol} fiyat verisi alınamadı ({hata}).")
        return None


# Kapanış fiyatlarını getiren fonksiyon. Testler internete çıkmamak için bunu değiştirir.
VERI_KAYNAGI = _yahoo_kapanislari


def hisse_gostergeleri(sembol, veri_kaynagi=None):
    """Önbellekli gösterge hesabı."""
    veri_kaynagi = veri_kaynagi or VERI_KAYNAGI
    simdi = time.time()
    if sembol in _onbellek and simdi - _onbellek[sembol][0] < ONBELLEK_SURESI:
        return _onbellek[sembol][1]
    kapanislar = veri_kaynagi(sembol)
    sonuc = gostergeler(kapanislar) if kapanislar else None
    _onbellek[sembol] = (simdi, sonuc)
    return sonuc


def _yuzde(deger):
    return "veri yok" if deger is None else f"%{deger:+.1f}"


def baglam_metni(semboller, veri_kaynagi=None):
    """Prompt'a eklenecek metin. Hiçbir hisse için veri yoksa boş string."""
    satirlar = []
    for sembol in semboller:
        g = hisse_gostergeleri(sembol, veri_kaynagi)
        if not g:
            continue
        parca = [f"son kapanış {g['son_kapanis']:.2f} TL",
                 f"1 gün {_yuzde(g['degisim_1g'])}",
                 f"5 gün {_yuzde(g['degisim_5g'])}",
                 f"20 gün {_yuzde(g['degisim_20g'])}"]
        if g["rsi14"] is not None:
            parca.append(f"RSI(14) {g['rsi14']:.0f}")
        if g["sma50_farki"] is not None:
            parca.append(f"50 günlük ortalamaya göre {_yuzde(g['sma50_farki'])}")
        satirlar.append(f"- {sembol}: " + ", ".join(parca))
    return "\n".join(satirlar)
