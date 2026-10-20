# Şirket adında geçen anahtar kelime -> BIST hisse kodu
# Şimdilik elle yazılmış küçük bir liste. İleride Muhammed KAP'taki
# tüm BIST şirketleri listesini çekince bu tablo otomatik dolacak.
HISSELER = {
    "şekerbank": "SKBNK",
    "türk hava yolları": "THYAO",
    "thy": "THYAO",
    "aselsan": "ASELS",
    "tüpraş": "TUPRS",
    "garanti": "GARAN",
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


def hisse_kodu_bul(sirket_adi):
    """Şirket adından hisse kodunu bulur, bulamazsa None döner."""
    ad = sirket_adi.lower()
    for anahtar, kod in HISSELER.items():
        if anahtar in ad:
            return kod
    return None