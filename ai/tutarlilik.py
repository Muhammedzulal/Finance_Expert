"""Tutarlılık testi: model aynı habere her seferinde aynı yorumu yapıyor mu?

İki şeyi ölçer:
  1. Tekrar tutarlılığı: Aynı haber N kez analiz edilince yön ve güven ne
     sıklıkla aynı çıkıyor? (%100 = hep aynı)
  2. Benzer haber tutarlılığı: Aynı türdeki haberler (ör. hepsi "Pay Alım
     Satım Bildirimi") benzer yorum alıyor mu?

Gerçek modeli (Ollama) kullanır, bu yüzden CI'da değil elle çalıştırılır:
  python ai/tutarlilik.py                    # varsayılan: 8 haber x 5 tekrar
  python ai/tutarlilik.py --tekrar 10 --limit 14 --sicaklik 0
  python ai/tutarlilik.py --dosya haberler.json   # News listesi içeren JSON

Sonuç ekrana ve ai/cikti/tutarlilik.json dosyasına yazılır.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

AI = Path(__file__).resolve().parent
sys.path.insert(0, str(AI))

from analiz import analysis_olustur, kontrol_et, analiz_dogrulayici, modele_sor, sema_bilgisi, sema_oku  # noqa: E402

CIKTI = AI / "cikti" / "tutarlilik.json"


def en_sik_oran(degerler):
    """En sık görülen değer ve oranı: ['a','a','b'] -> ('a', 0.67)."""
    if not degerler:
        return None, 0.0
    deger, adet = Counter(degerler).most_common(1)[0]
    return deger, adet / len(degerler)


def tekrar_olc(haber, tekrar, sicaklik, dogrulayici, surum, uyari, sor=modele_sor):
    """Haberi 'tekrar' kez analiz eder; her hisse için yön/güven dağılımı döner."""
    yonler = {s: [] for s in haber["symbols"]}
    guvenler = {s: [] for s in haber["symbols"]}
    hatalar = []
    for _ in range(tekrar):
        try:
            analiz = analysis_olustur(haber, sor(haber, sicaklik=sicaklik), surum, uyari)
        except Exception as hata:
            hatalar.append(f"model: {hata}")
            continue
        hata = kontrol_et(haber, analiz, dogrulayici)
        if hata:
            hatalar.append(hata)
            continue
        for imp in analiz["impacts"]:
            yonler[imp["symbol"]].append(imp["direction"])
            guvenler[imp["symbol"]].append(imp["confidence"])

    hisseler = {}
    for s in haber["symbols"]:
        yon, yon_orani = en_sik_oran(yonler[s])
        guven, guven_orani = en_sik_oran(guvenler[s])
        hisseler[s] = {"yon": yon, "yon_uyumu": round(yon_orani, 2),
                       "guven": guven, "guven_uyumu": round(guven_orani, 2),
                       "dagilim": dict(Counter(yonler[s]))}
    return {"news_id": haber["news_id"], "baslik": haber["title"], "tur": haber_turu(haber),
            "basarili": tekrar - len(hatalar), "tekrar": tekrar, "hatalar": hatalar,
            "hisseler": hisseler}


def haber_turu(haber):
    """Benzer haberleri gruplamak için anahtar: KAP bildirim türü ya da özet."""
    return haber.get("disclosure_type") or (haber.get("summary") or "").strip() or None


def benzer_haber_karsilastir(sonuclar):
    """Aynı türdeki haberlerin en sık yönleri farklıysa listeler."""
    gruplar = {}
    for sonuc in sonuclar:
        if not sonuc["tur"]:
            continue
        for sembol, h in sonuc["hisseler"].items():
            if h["yon"]:
                gruplar.setdefault(sonuc["tur"], []).append((sembol, h["yon"]))
    tutarsiz = {}
    for tur, uyeler in gruplar.items():
        if len(uyeler) >= 2 and len({yon for _, yon in uyeler}) > 1:
            tutarsiz[tur] = uyeler
    return tutarsiz


def ozet(sonuclar):
    yon = [h["yon_uyumu"] for s in sonuclar for h in s["hisseler"].values() if h["yon"]]
    guven = [h["guven_uyumu"] for s in sonuclar for h in s["hisseler"].values() if h["guven"] is not None]
    toplam = sum(s["tekrar"] for s in sonuclar)
    basarili = sum(s["basarili"] for s in sonuclar)
    return {
        "ortalama_yon_uyumu": round(sum(yon) / len(yon), 2) if yon else None,
        "ortalama_guven_uyumu": round(sum(guven) / len(guven), 2) if guven else None,
        "basari_orani": round(basarili / toplam, 2) if toplam else None,
    }


def haberleri_yukle(dosya):
    if dosya:
        return json.loads(Path(dosya).read_text(encoding="utf-8"))
    sys.path.insert(0, str(AI / "gecici"))
    from gecici_adaptor import haberleri_oku
    return haberleri_oku()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tekrar", type=int, default=5, help="her haber kaç kez analiz edilsin (5)")
    p.add_argument("--limit", type=int, default=8, help="kaç haber denensin (8)")
    p.add_argument("--sicaklik", type=float, default=0.4,
                   help="model sıcaklığı; 0 = en kararlı, worker tekrar denemelerde 0.4 kullanır (0.4)")
    p.add_argument("--dosya", help="News listesi içeren JSON dosyası (yoksa geçici adaptör)")
    a = p.parse_args()

    sema = sema_oku()
    surum, uyari = sema_bilgisi(sema)
    dogrulayici = analiz_dogrulayici(sema)
    haberler = [h for h in haberleri_yukle(a.dosya) if h["symbols"]][: a.limit]
    print(f"{len(haberler)} haber x {a.tekrar} tekrar, sıcaklık {a.sicaklik}\n")

    sonuclar = []
    for i, haber in enumerate(haberler, 1):
        s = tekrar_olc(haber, a.tekrar, a.sicaklik, dogrulayici, surum, uyari)
        sonuclar.append(s)
        print(f"[{i}] {haber['title'][:60]}  ({s['basarili']}/{a.tekrar} başarılı)")
        for sembol, h in s["hisseler"].items():
            print(f"     {sembol}: yön {h['yon']} (%{h['yon_uyumu'] * 100:.0f} aynı) "
                  f"| güven {h['guven']} (%{h['guven_uyumu'] * 100:.0f} aynı) | {h['dagilim']}")

    tutarsiz = benzer_haber_karsilastir(sonuclar)
    genel = ozet(sonuclar)
    print("\n=== ÖZET ===")
    print(f"Yön uyumu ortalaması:   %{(genel['ortalama_yon_uyumu'] or 0) * 100:.0f}")
    print(f"Güven uyumu ortalaması: %{(genel['ortalama_guven_uyumu'] or 0) * 100:.0f}")
    print(f"Başarılı analiz oranı:  %{(genel['basari_orani'] or 0) * 100:.0f}")
    if tutarsiz:
        print("Benzer haberlere farklı yön verilen türler:")
        for tur, uyeler in tutarsiz.items():
            print(f"  - {tur}: " + ", ".join(f"{s}={y}" for s, y in uyeler))
    else:
        print("Benzer haberler arasında yön tutarsızlığı yok.")

    CIKTI.parent.mkdir(exist_ok=True)
    CIKTI.write_text(json.dumps({"ayarlar": vars(a), "ozet": genel, "benzer_tutarsiz": tutarsiz,
                                 "sonuclar": sonuclar}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAyrıntılar: {CIKTI}")


if __name__ == "__main__":
    main()
