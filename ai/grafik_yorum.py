"""Grafik yorumu: Muhammed'in indikatörlerinden al/sat demeden Türkçe yorum.

Akış:
  1. Veri: graphics_analyzer/data_loader.py (Muhammed) -> Close, SMA_50, EMA_20,
     RSI, Bollinger bantları, günlük % değişim
  2. Gerçekler: Kod, indikatörlerden kesin cümleler çıkarır ("fiyat 50 günlük
     ortalamanın %4,2 üzerinde"). Hesap modele bırakılmaz.
  3. Anlatım: Model bu gerçeklerden 2-4 cümlelik sade bir yorum yazar.
  4. Denetim: Tahmin, sinyal, al/sat ve gerçeklerde olmayan sayı içeren yorum
     reddedilir. Model 3 denemede başaramazsa kodun şablon metni kullanılır.

Kullanım:
  python ai/grafik_yorum.py                        # Muhammed'in 8 sembolü
  python ai/grafik_yorum.py --sembol THYAO.IS GARAN.IS

Sonuç ekrana ve ai/cikti/grafik_yorumlari.json dosyasına yazılır.
Çıktı biçimi bir sözleşme TASLAĞIDIR (ChartCommentary); Berke'nin onayı bekleniyor.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

AI = Path(__file__).resolve().parent
PROJE = AI.parent
sys.path.insert(0, str(AI))

from analiz import MAKS_DENEME, MODEL, tr_kucuk  # noqa: E402

PROMPT_VERSION = "chart-commentary-v1-tr"
TASLAK_SURUM = "0.1-taslak"
UYARI = ("Yatırım tavsiyesi değildir. Grafik göstergelerinin mevcut durumunu anlatan "
         "bilgilendirme amaçlı otomatik yorumdur; gelecekteki fiyatı tahmin etmez.")
CIKTI = AI / "cikti" / "grafik_yorumlari.json"

# graphics_analyzer/main.py'deki takip listesiyle aynı
SEMBOLLER = {
    "USDTRY=X": ("Dolar/TL", "TL"),
    "EURTRY=X": ("Euro/TL", "TL"),
    "GC=F": ("Altın (ons)", "USD"),
    "THYAO.IS": ("Türk Hava Yolları", "TL"),
    "GARAN.IS": ("Garanti BBVA", "TL"),
    "ASELS.IS": ("Aselsan", "TL"),
    "BTC-USD": ("Bitcoin", "USD"),
    "ETH-USD": ("Ethereum", "USD"),
}

# Gerçek cümlelerinde geçen sabit sayılar (periyotlar ve RSI eşikleri)
SABIT_SAYILAR = {14, 20, 30, 50, 70}


# ---------------------------------------------------------------- 1. Veri

def muhammed_verisi(sembol):
    """Muhammed'in DataLoader'ı ile son ~25 günün indikatörleri (eskiden yeniye).

    Her satır: {"tarih", "Close", "SMA_50", "EMA_20", "RSI", "Bollinger_Upper",
    "Bollinger_Lower", "Pct_Change"}. Veri alınamazsa None.
    """
    sys.path.insert(0, str(PROJE / "graphics_analyzer"))
    try:
        from data_loader import DataLoader
        df = DataLoader(symbol=sembol, period="1y").get_data()
    except Exception as hata:
        print(f"Bilgi: {sembol} verisi alınamadı ({hata}).")
        return None
    satirlar = []
    for tarih, s in df.tail(25).iterrows():
        satir = {k: float(s[k]) for k in ["Close", "SMA_50", "EMA_20", "RSI",
                                           "Bollinger_Upper", "Bollinger_Lower", "Pct_Change"]}
        satir["tarih"] = tarih.date().isoformat()
        satirlar.append(satir)
    return satirlar or None


# ------------------------------------------------------------ 2. Gerçekler

def sayi(deger, basamak=1):
    """Türkçe ondalık: 3.14159 -> '3,1'."""
    return f"{deger:.{basamak}f}".replace(".", ",")


def fiyat_yaz(deger):
    """Fiyat büyüklüğüne göre basamak: 105234.5 -> '105234,50', 0.0345 -> '0,0345'."""
    return sayi(deger, 4 if abs(deger) < 1 else 2)


def gostergeler(satirlar):
    """Son satır ve 20 gün öncesinden özet sayılar."""
    son = satirlar[-1]
    ilk = satirlar[max(0, len(satirlar) - 21)]
    bant = son["Bollinger_Upper"] - son["Bollinger_Lower"]
    orta = (son["Bollinger_Upper"] + son["Bollinger_Lower"]) / 2
    eski_bant = ilk["Bollinger_Upper"] - ilk["Bollinger_Lower"]
    eski_orta = (ilk["Bollinger_Upper"] + ilk["Bollinger_Lower"]) / 2
    return {
        "tarih": son["tarih"],
        "fiyat": son["Close"],
        "gunluk_degisim": son["Pct_Change"],
        "donem_degisim": (son["Close"] / ilk["Close"] - 1) * 100,
        "donem_gun": len(satirlar) - 1 - satirlar.index(ilk),
        "sma50_fark": (son["Close"] / son["SMA_50"] - 1) * 100,
        "ema20_fark": (son["Close"] / son["EMA_20"] - 1) * 100,
        "ema20_sma50_ustte": son["EMA_20"] > son["SMA_50"],
        "rsi": son["RSI"],
        "bant_konum": None if bant <= 0 else (son["Close"] - son["Bollinger_Lower"]) / bant * 100,
        "bant_genislik": bant / orta * 100 if orta else None,
        "eski_bant_genislik": eski_bant / eski_orta * 100 if eski_orta else None,
    }


def _ust_alt(fark):
    return "üzerinde" if fark >= 0 else "altında"


def gercekleri_cikar(g, birim):
    """Gösterge sözlüğünden kesin, yorumsuz cümleler."""
    gercekler = [
        # Borsa açıkken Yahoo'nun son satırı gün içi fiyattır; "kapanış" demiyoruz
        f"Son fiyat {fiyat_yaz(g['fiyat'])} {birim}; bir önceki kapanışa göre %{sayi(abs(g['gunluk_degisim']))} "
        f"{'yükseliş' if g['gunluk_degisim'] >= 0 else 'düşüş'}.",
        f"Son {g['donem_gun']} işlem gününde fiyat %{sayi(abs(g['donem_degisim']))} "
        f"{'yükseldi' if g['donem_degisim'] >= 0 else 'düştü'}.",
        f"Fiyat 50 günlük ortalamanın %{sayi(abs(g['sma50_fark']))} {_ust_alt(g['sma50_fark'])}.",
        f"Fiyat 20 günlük üstel ortalamanın %{sayi(abs(g['ema20_fark']))} {_ust_alt(g['ema20_fark'])}; "
        f"20 günlük ortalama 50 günlüğün {'üzerinde' if g['ema20_sma50_ustte'] else 'altında'}.",
    ]
    rsi = g["rsi"]
    if rsi >= 70:
        bolge = "70 eşiğinin üzerinde; son 14 günde yükselişler belirgin şekilde baskın"
    elif rsi <= 30:
        bolge = "30 eşiğinin altında; son 14 günde düşüşler belirgin şekilde baskın"
    else:
        bolge = "30-70 aralığında; son 14 günde yükseliş ve düşüşler görece dengeli"
    gercekler.append(f"RSI değeri {sayi(rsi, 0)}: {bolge}.")

    if g["bant_konum"] is not None:
        k = g["bant_konum"]
        if k > 100:
            yer = "Bollinger üst bandının üzerinde"
        elif k < 0:
            yer = "Bollinger alt bandının altında"
        elif k >= 80:
            yer = "Bollinger bandının üst kısmında"
        elif k <= 20:
            yer = "Bollinger bandının alt kısmında"
        else:
            yer = "Bollinger bandının orta bölgesinde"
        gercekler.append(f"Fiyat {yer}.")
    if g["bant_genislik"] is not None and g["eski_bant_genislik"]:
        oran = g["bant_genislik"] / g["eski_bant_genislik"]
        if oran > 1.15:
            hal = "genişledi; fiyat oynaklığı arttı"
        elif oran < 0.85:
            hal = "daraldı; fiyat oynaklığı azaldı"
        else:
            hal = "belirgin şekilde değişmedi; oynaklık benzer düzeyde"
        gercekler.append(f"Bollinger bandının genişliği son {g['donem_gun']} günde {hal}.")
    return gercekler


def sablon_yorum(ad, gercekler):
    """Model kullanılamazsa gösterilecek güvenli metin."""
    return f"{ad}: " + " ".join(gercekler)


# ------------------------------------------------------------- 3. Anlatım

SISTEM = """Görevin bir finans grafiğinin MEVCUT durumunu yeni başlayan bir yatırımcının
anlayacağı sade Türkçeyle anlatmak.
Sadece sana verilen gerçekleri kullan; yeni bilgi, yeni sayı veya hesap ekleme.
Sayıları verildiği gibi yaz.
Gelecekteki fiyat hakkında tahmin yapma: "yükselebilir", "düşebilir", "gelebilir",
"bekleniyor" gibi ifadeler kullanma.
Al, sat, tut, fırsat, sinyal, destek, direnç, hedef, ucuz, pahalı, aşırı alım,
aşırı satım gibi işlem çağrıştıran kelimeler kullanma.
Göstergenin ne anlama geldiğini bir cümleyle açıklayabilirsin; örneğin RSI'ın son
günlerdeki yükseliş ve düşüşlerin dengesini ölçtüğünü söyleyebilirsin.
Göstergeler arasında sebep-sonuç kurma: "RSI yüksek, bu da fiyatın bandın üstünde
olduğunu gösterir" gibi cümleler yanlıştır; her gösterge kendi gerçeğini anlatır.
Ortalamaların birbirini "geçtiğini" ya da "kestiğini" söyleme; sadece hangisinin
üzerinde ya da altında olduğunu yaz.
Sayıları her zaman rakamla yaz ("%1,0"); "yüzde bir", "iki ay" gibi yazıyla sayı
ya da gerçeklerde olmayan süre (hafta, ay, yıl) kullanma."""

PROMPT = """{ad} ({sembol}) için {tarih} tarihli gerçekler (borsa açıksa "son fiyat" gün içi fiyattır,
kapanış deme):
{gercekler}

Bu gerçekleri 2 ile 4 cümle arasında, akıcı bir paragrafla anlat.
SADECE şu JSON'u döndür: {{"yorum": "paragraf"}}"""


def modele_yazdir(ad, sembol, tarih, gercekler, sicaklik=0):
    import ollama
    cevap = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SISTEM},
            {"role": "user", "content": PROMPT.format(
                ad=ad, sembol=sembol, tarih=tarih,
                gercekler="\n".join(f"- {x}" for x in gercekler))},
        ],
        format="json",
        think=False,
        options={"temperature": sicaklik},
    )
    return json.loads(cevap.message.content)


# ------------------------------------------------------------- 4. Denetim

YASAK_KALIPLAR = [
    r"(?<!\w)(al|sat|tut|alın|tutun|satın\s+al)(?!\w)",
    r"(?<!\w)(alınmalı|satılmalı|tutulmalı|biriktir\w*)(?!\w)",
    r"(alım|satım|satış|al|sat)\s+sinyal\w*", r"(?<!\w)sinyal\w*",
    r"aşırı\s+(alım|satım|satış)\w*",
    r"(golden|death)\s+cross", r"altın\s+kesişim", r"ölüm\s+kesişim",
    r"(?<!\w)(destek|direnç|hedef)\w*",
    r"(?<!\w)(fırsat|ucuz|pahalı)\w*", r"(aşırı\s+)?değerlen(miş|di)\w*",
    # Fiyat fiilleri + gelecek/olasılık eki: yükselebilir, artacak, gerileyebilir...
    r"(?<!\w)(yüksel|düş|art|gerile|toparlan|kırıl|çık|in|sür|devam\s+ed)(y)?(e|a)(bilir|cek|cak|ceğ|cağ)\w*",
    r"(?<!\w)(gelebilir|beklen\w*|muhtemel\w*|tahmin\w*)(?!\w)",
    r"kırılım\w*", r"(?<!\w)tepki\s+(yükseliş|alım)\w*",
    r"(?<!\w)(buy|sell|hold)(?!\w)",
    # Kesişim olayı (golden/death cross tarifi): gerçeklerde sadece üzerinde/altında var
    r"(?<!\w)kesiş\w*", r"(?<!\w)(kes|geç)(ti|miş|erek|ip|mesi|mesiyle)(?!\w)",
    r"yukarı\s+(kes|geç)\w*", r"aşağı\s+(kes|geç)\w*",
]

# Yazıyla sayı ve gerçeklerde olmayan süreler: sayı denetimini atlatmasın
SAYI_KELIMELERI = (r"(bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on|yirmi|otuz|kırk|elli|"
                   r"altmış|yetmiş|seksen|doksan|yüz|birkaç|birçok)")
YAZIYLA_SAYI_KALIPLARI = [
    rf"yüzde\s+{SAYI_KELIMELERI}(?!\w)",
    rf"(?<!\w){SAYI_KELIMELERI}\s+(gün|hafta|ay|yıl|işlem\s+gün)\w*",
    r"(?<!\w)\d+\s+(hafta|ay|yıl)\w*",
    r"(?<!\w)son\s+(hafta|ay|yıl)\w*",
]


def yasak_bul(metin):
    kucuk = tr_kucuk(metin)
    for kalip in YASAK_KALIPLAR + YAZIYLA_SAYI_KALIPLARI:
        m = re.search(kalip, kucuk)
        if m:
            return m.group(0)
    return None


def _sayi_adaylari(parca):
    """'105.234,50' -> {105234.5}; '1.234' -> {1.234, 1234.0}; '3,2' -> {3.2}."""
    adaylar = set()
    if "," in parca and "." in parca:
        adaylar.add(float(parca.replace(".", "").replace(",", ".")))
    elif "," in parca:
        adaylar.add(float(parca.replace(",", ".")))
    elif "." in parca:
        adaylar.add(float(parca))
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", parca):
            adaylar.add(float(parca.replace(".", "")))
    else:
        adaylar.add(float(parca))
    return adaylar


def metindeki_sayilar(metin):
    return [(p, _sayi_adaylari(p)) for p in re.findall(r"\d+(?:[.,]\d+)*", metin)]


def izinli_sayilar(gercekler, tarih=None):
    izinli = set(SABIT_SAYILAR)
    if tarih:  # "2 Kasım 2026" gibi tarih yazımı serbest
        izinli |= {float(x) for x in tarih.split("-")}
    for _, adaylar in metindeki_sayilar(" ".join(gercekler)):
        izinli |= adaylar
    return izinli


def uydurma_sayi_bul(yorum, gercekler, tarih=None):
    """Yorumda gerçeklerde olmayan bir sayı varsa onu döndürür.

    Yuvarlama serbest: '%4,23' gerçeği yorumda '%4,2' ya da '4' olarak yazılabilir.
    """
    izinli = izinli_sayilar(gercekler, tarih)
    for parca, adaylar in metindeki_sayilar(yorum):
        tolerans = 0.051 if re.search(r"[.,]\d{1,2}$", parca) else 0.5
        if not any(abs(a - b) <= max(tolerans, abs(b) * 0.0005) for a in adaylar for b in izinli):
            return parca
    return None


# Her gerçek cümlesinin "konusu": bir sayı yorumda bu kelimelerin yakınında geçmeli
GERCEK_KONULARI = [
    ("Son fiyat", ["kapan", "son gün", "günde", "bugün", "bu gün", "seviye", "fiyat", "önceki"]),
    ("Son kapanış", ["kapan", "son gün", "günde", "bugün", "bu gün", "seviye", "fiyat", "önceki"]),
    ("işlem gününde", ["işlem gün", "son 20", "dönem"]),
    ("50 günlük ortalamanın", ["50 gün"]),
    ("20 günlük üstel", ["20 gün", "üstel"]),
    ("RSI", ["rsi", "rsı"]),
]


def _konu_kelimeleri(gercek):
    for isaret, kelimeler in GERCEK_KONULARI:
        if isaret in gercek:
            return kelimeler
    return None


def yanlis_baglanan_sayi_bul(yorum, gercekler, tarih=None):
    """Doğru sayı yanlış göstergeye mi yazılmış? (ör. 50 günlük ortalama farkı 'son gün' diye)

    Yorumdaki her sayının, onu içeren gerçek cümlesinin konu kelimelerinden biriyle
    yakın çevresinde (önce 60, sonra 30 karakter) birlikte geçmesi gerekir.
    """
    sabit = set(SABIT_SAYILAR) | ({float(x) for x in tarih.split("-")} if tarih else set())
    kucuk = tr_kucuk(yorum)
    for m in re.finditer(r"\d+(?:[.,]\d+)*", yorum):
        adaylar = _sayi_adaylari(m.group(0))
        if any(abs(a - b) < 1e-9 for a in adaylar for b in sabit):
            continue
        sahipler = []
        for gercek in gercekler:
            gercek_sayilari = set().union(*(a for _, a in metindeki_sayilar(gercek))) if \
                metindeki_sayilar(gercek) else set()
            if any(abs(a - b) <= max(0.051 if re.search(r"[.,]\d{1,2}$", m.group(0)) else 0.5,
                                     abs(b) * 0.0005) for a in adaylar for b in gercek_sayilari):
                kelimeler = _konu_kelimeleri(gercek)
                if kelimeler is None:
                    break  # konusu tanımsız gerçek: denetleme
                sahipler.append(kelimeler)
        else:
            if sahipler:
                cevre = kucuk[max(0, m.start() - 60): m.end() + 30]
                if not any(k in cevre for kelimeler in sahipler for k in kelimeler):
                    return m.group(0)
    return None


def denetle(yorum, gercekler, tarih=None):
    """Sorun yoksa None, varsa açıklaması."""
    if not isinstance(yorum, str) or len(yorum.strip()) < 40:
        return "yorum boş ya da çok kısa"
    cumle = len([c for c in re.split(r"[.!?]+\s", yorum.strip()) if c.strip()])
    if cumle > 6:
        return f"yorum çok uzun ({cumle} cümle)"
    ifade = yasak_bul(yorum)
    if ifade:
        return f"tahmin/işlem çağrışımı ('{ifade}')"
    sayi_ = uydurma_sayi_bul(yorum, gercekler, tarih)
    if sayi_:
        return f"gerçeklerde olmayan sayı ('{sayi_}')"
    sayi_ = yanlis_baglanan_sayi_bul(yorum, gercekler, tarih)
    if sayi_:
        return f"sayı yanlış göstergeye bağlanmış ('{sayi_}')"
    return None


# ------------------------------------------------------------- Birleştir

def yorum_uret(sembol, satirlar, yazdir=modele_yazdir):
    """Tek sembol için ChartCommentary taslağı. Model başarısızsa şablon kullanılır."""
    ad, birim = SEMBOLLER.get(sembol, (sembol, ""))
    g = gostergeler(satirlar)
    gercekler = gercekleri_cikar(g, birim)

    yorum, kaynak, son_hata, deneme = None, "sablon", None, 0
    for deneme in range(1, MAKS_DENEME + 1):
        try:
            aday = yazdir(ad, sembol, g["tarih"], gercekler, sicaklik=0 if deneme == 1 else 0.4)
            aday = str(aday.get("yorum", "")).strip()
        except Exception as hata:
            son_hata = f"model: {hata}"
            continue
        son_hata = denetle(aday, gercekler, g["tarih"])
        if son_hata is None:
            yorum, kaynak = aday, "model"
            break
    if yorum is None:
        yorum = sablon_yorum(ad, gercekler)

    son = satirlar[-1]
    return {
        "schema_version": TASLAK_SURUM,
        "commentary_id": f"chart:{sembol}:{g['tarih']}:{PROMPT_VERSION}",
        "ticker": sembol,
        "display_name": ad,
        "currency": birim,
        "as_of": g["tarih"],
        "indicators": {k: round(son[k], 6) for k in ["Close", "SMA_50", "EMA_20", "RSI",
                                                     "Bollinger_Upper", "Bollinger_Lower", "Pct_Change"]},
        "facts": gercekler,
        "commentary": yorum,
        "source": kaynak,
        "model": MODEL if kaynak == "model" else None,
        "prompt_version": PROMPT_VERSION,
        "attempts": deneme,
        "last_error": None if kaynak == "model" else son_hata,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "disclaimer": UYARI,
    }


def main():
    p = argparse.ArgumentParser(description="Grafik göstergelerinden Türkçe yorum üretir.")
    p.add_argument("--sembol", nargs="+", default=list(SEMBOLLER), help="Yahoo sembolleri")
    a = p.parse_args()

    sonuclar = []
    for sembol in a.sembol:
        satirlar = muhammed_verisi(sembol)
        if not satirlar:
            continue
        s = yorum_uret(sembol, satirlar)
        sonuclar.append(s)
        etiket = "model" if s["source"] == "model" else f"ŞABLON ({s['last_error']})"
        print(f"\n=== {s['display_name']} ({sembol}) | {s['as_of']} | {etiket}")
        print(s["commentary"])

    CIKTI.parent.mkdir(exist_ok=True)
    CIKTI.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    model_sayisi = sum(s["source"] == "model" for s in sonuclar)
    print(f"\n{len(sonuclar)} yorum ({model_sayisi} model, {len(sonuclar) - model_sayisi} şablon) "
          f"kaydedildi: {CIKTI}")


if __name__ == "__main__":
    main()
