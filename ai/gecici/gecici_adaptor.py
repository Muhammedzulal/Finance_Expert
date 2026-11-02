"""Geçici adaptör (SİLİNECEK): Muhammed'in ham JSON dosyalarını News benzeri kayıtlara çevirir.

Gerçek sistemde AI worker haberleri backend'den, hisse kodları eşleşmiş
News v1 kayıtları olarak alacak. Muhammed'in adaptörü ve Ensar'ın API'si
hazır olunca bu dosya silinecek.
"""

import hashlib
import json
import re
from pathlib import Path

from hisseler import hisse_adi, metinde_hisse_bul

PROJE = Path(__file__).resolve().parents[2]  # ai/gecici/ -> proje kökü
BLOOMBERG = PROJE / "Web_scaper" / "bloomberg_trading_news.json"
KAP = PROJE / "Web_scaper" / "kap_today_disclosures.json"

SEMBOL = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")


def _kap_sembolleri(baslik):
    """KAP başlığının sonundaki '/ CEMAS' gibi hisse kodlarını alır."""
    if "/" not in baslik:
        return []
    kodlar = [k.strip() for k in baslik.rsplit("/", 1)[1].split(",")]
    kodlar = [k for k in kodlar if SEMBOL.match(k)]
    # Onlarca hisseyi kapsayan genel duyurular tek tek analiz edilmez
    return kodlar if 1 <= len(kodlar) <= 3 else []


def _kap_sirket_adi(baslik):
    """'IŞIKLAR ENERJİ ... A.Ş.Özel Durum...' -> 'IŞIKLAR ENERJİ ... A.Ş.'"""
    if baslik.startswith("KAMUYU AYDINLATMA PLATFORMU") or "A.Ş." not in baslik:
        return None
    return baslik.split("A.Ş.", 1)[0].strip() + " A.Ş."


def _adlar(semboller, kap_adi=None):
    """Modelin kodu şirketle eşleştirebilmesi için kod -> şirket adı.

    Gerçek sistemde bu bilgi hisse ana listesinden gelecek.
    """
    adlar = {}
    for kod in semboller:
        ad = hisse_adi(kod) or (kap_adi if len(semboller) == 1 else None)
        if ad:
            adlar[kod] = ad
    return adlar


def haberleri_oku():
    haberler = []

    if BLOOMBERG.exists():
        for h in json.loads(BLOOMBERG.read_text(encoding="utf-8")):
            url = h["link"].strip()
            haberler.append({
                "news_id": "bloomberg_ht:" + hashlib.sha256(url.encode("utf-8")).hexdigest(),
                "source": "BLOOMBERG_HT",
                "title": h["title"],
                "summary": h.get("summary", ""),
                "url": url,
                "symbols": metinde_hisse_bul(h["title"] + " " + h.get("summary", "")),
            })
            haberler[-1]["sirket_adlari"] = _adlar(haberler[-1]["symbols"])

    if KAP.exists():
        for h in json.loads(KAP.read_text(encoding="utf-8")):
            if not h.get("disclosure_id"):
                continue
            sembol = _kap_sembolleri(h["title"]) or metinde_hisse_bul(h["title"])
            haberler.append({
                "news_id": "kap:" + h["disclosure_id"],
                "source": "KAP",
                "title": h["title"],
                "summary": h.get("summary", ""),
                "url": h["detail_url"],
                "symbols": sembol,
                "sirket_adlari": _adlar(sembol, _kap_sirket_adi(h["title"])),
            })

    return haberler
