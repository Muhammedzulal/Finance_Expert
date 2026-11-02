"""Geçici hisse tablosu.

Sözleşmeye göre hisse eşleştirmesi Muhammed'in adaptörünün işidir.
O hazır olana kadar test için bu küçük tabloyu kullanıyoruz.
"""

import re

# Metinde geçen anahtar ifade -> BIST hisse kodu
HISSELER = {
    "şekerbank": "SKBNK",
    "türk hava yolları": "THYAO",
    "thy": "THYAO",
    "aselsan": "ASELS",
    "tüpraş": "TUPRS",
    "garanti bbva": "GARAN",
    "akbank": "AKBNK",
    "iş bankası": "ISCTR",
    "yapı kredi": "YKBNK",
    "koç holding": "KCHOL",
    "sabancı holding": "SAHOL",
    "bim": "BIMAS",
    "ereğli": "EREGL",
    "ford otosan": "FROTO",
    "tofaş": "TOASO",
    "turkcell": "TCELL",
    "türk telekom": "TTKOM",
    "şişecam": "SISE",
    "pegasus": "PGSUS",
}


def hisse_adi(kod):
    """Hisse kodunun tablodaki ilk adını döndürür (SKBNK -> 'şekerbank')."""
    for anahtar, k in HISSELER.items():
        if k == kod:
            return anahtar
    return None


def tr_kucuk_harf(metin):
    """Türkçe'ye uygun küçük harf: 'İ' -> 'i', 'I' -> 'ı'.

    Python'un normal lower() fonksiyonu 'İŞ BANKASI'nı 'iş bankası' yapamaz.
    """
    return metin.replace("İ", "i").replace("I", "ı").lower()


def metinde_hisse_bul(metin):
    """Metinde geçen şirketlerin hisse kodlarını sırayla döndürür."""
    metin = tr_kucuk_harf(metin)
    bulunan = []
    for anahtar, kod in HISSELER.items():
        # (?<!\w) ve (?!\w): kelimenin ortasında eşleşmesin ("bim" -> "birimi" olmasın)
        if re.search(rf"(?<!\w){re.escape(anahtar)}(?!\w)", metin) and kod not in bulunan:
            bulunan.append(kod)
    return bulunan
