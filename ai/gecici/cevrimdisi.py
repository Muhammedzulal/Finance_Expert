"""Çevrimdışı deneme (SİLİNECEK): backend olmadan, Muhammed'in JSON dosyalarıyla analiz.

Bu klasördeki her şey geçicidir. Muhammed'in News adaptörü backend'e haber
göndermeye başlayınca ai/gecici/ klasörü tamamen silinebilir; worker.py ve
analiz.py bu klasöre bağlı değildir.

Kullanım:  python ai/gecici/cevrimdisi.py
"""

import json
import sys
import time
from pathlib import Path

GECICI = Path(__file__).resolve().parent
AI = GECICI.parent
sys.path.insert(0, str(AI))
sys.path.insert(0, str(GECICI))

import piyasa  # noqa: E402
from analiz import MAKS_DENEME, analiz_dogrulayici, haberi_isle, sema_bilgisi, sema_oku  # noqa: E402
from gecici_adaptor import haberleri_oku  # noqa: E402

CIKTI_DOSYASI = AI / "cikti" / "analizler.json"


def main():
    sema = sema_oku()
    surum, uyari = sema_bilgisi(sema)
    dogrulayici = analiz_dogrulayici(sema)
    print(f"Sözleşme: Analysis v{surum}" + (" (uyarı alanı zorunlu)" if uyari else ""))
    haberler = haberleri_oku()
    hisseli = [h for h in haberler if h["symbols"]]
    print(f"{len(haberler)} haber okundu, {len(hisseli)} tanesi hisseyle eşleşti.")
    print("Çevrimdışı deneme: sadece hisseli haberler analiz edilir "
          "(backend'e bağlı worker.py hissesiz haberleri de işler).\n")

    analizler = []
    for i, haber in enumerate(hisseli, 1):
        basla = time.time()
        haber["piyasa_baglami"] = piyasa.baglam_metni(haber["symbols"])
        analiz, deneme, son_hata = haberi_isle(haber, dogrulayici, surum, uyari)
        if analiz is None:
            print(f"[{i}] BAŞARISIZ ({MAKS_DENEME} deneme) {haber['title'][:60]}")
            print(f"     son hata: {son_hata}")
            continue

        analizler.append(analiz)
        ek = f", {deneme}. denemede" if deneme > 1 else ""
        print(f"[{i}] ({time.time() - basla:.1f} sn{ek}) {haber['title'][:70]}")
        if haber["piyasa_baglami"]:
            print("     piyasa: " + haber["piyasa_baglami"].replace("\n", " | "))
        for imp in analiz["impacts"]:
            print(f"     {imp['symbol']}: {imp['direction']} ({imp['confidence']}) - {imp['reason']}")

    CIKTI_DOSYASI.parent.mkdir(exist_ok=True)
    CIKTI_DOSYASI.write_text(json.dumps(analizler, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(analizler)} analiz şemadan geçti ve kaydedildi: {CIKTI_DOSYASI}")


if __name__ == "__main__":
    main()
