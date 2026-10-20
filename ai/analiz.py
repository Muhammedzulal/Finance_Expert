import json
import time
from pathlib import Path

import ollama

from hisseler import hisse_kodu_bul

MODEL = "qwen3.5:4b"

PROJE = Path(__file__).resolve().parent.parent
HABER_DOSYASI = PROJE / "Web_scaper" / "bloomberg_trading_news.json"
SONUC_DOSYASI = PROJE / "ai" / "analiz_sonuclari.json"

PROMPT = """Sen Borsa İstanbul'u takip eden bir finans analistisin. Haberi oku ve SADECE JSON döndür.

Alanlar:
- "piyasa_ilgisi": "yok" (borsayı etkilemez), "dusuk" veya "yuksek"
- "sirketler": haberde AÇIKÇA adı geçen şirketlerin listesi. Yer adı, bakanlık veya kurum yazma. Yoksa []
- "etki": "olumlu", "olumsuz" veya "notr"
- "tavsiye": "AL", "SAT" veya "TUT"
- "gerekce": tek kısa cümle

Örnek:
Haber: Belediye parklarda yeni bank düzenlemesi yaptı.
Cevap: {{"piyasa_ilgisi": "yok", "sirketler": [], "etki": "notr", "tavsiye": "TUT", "gerekce": "Haberin borsaya etkisi yok."}}

Haber başlığı: {baslik}
Haber özeti: {ozet}
Cevap:"""


def modele_sor(haber):
    cevap = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT.format(
            baslik=haber["title"], ozet=haber["summary"])}],
        format="json",
        think=False,
        options={"temperature": 0},
    )
    return json.loads(cevap.message.content)


def dogrula(analiz):
    """Modelin cevabını kurallarımıza göre düzeltir."""
    # 1) Sadece BIST'te işlem gören şirketleri tut
    hisseler = []
    for sirket in analiz.get("sirketler", []):
        kod = hisse_kodu_bul(sirket)
        if kod and kod not in hisseler:
            hisseler.append(kod)

    # 2) Hisse yoksa tavsiye verilmez
    tavsiye = analiz.get("tavsiye") if hisseler else "YOK"

    return {
        "piyasa_ilgisi": analiz.get("piyasa_ilgisi"),
        "hisseler": hisseler,
        "modelin_buldugu_sirketler": analiz.get("sirketler", []),
        "etki": analiz.get("etki"),
        "tavsiye": tavsiye,
        "gerekce": analiz.get("gerekce"),
    }


def main():
    haberler = json.loads(HABER_DOSYASI.read_text(encoding="utf-8"))
    print(f"{len(haberler)} haber analiz ediliyor...\n")

    sonuclar = []
    for i, haber in enumerate(haberler, 1):
        basla = time.time()
        try:
            analiz = dogrula(modele_sor(haber))
        except Exception as hata:
            print(f"[{i}] HATA: {hata}")
            continue
        sure = time.time() - basla

        sonuclar.append({"haber": haber["title"], "link": haber["link"], "analiz": analiz})
        print(f"[{i}] ({sure:.1f} sn) {haber['title']}")
        print(f"     model={analiz['modelin_buldugu_sirketler']} -> hisseler={analiz['hisseler']} | "
              f"etki={analiz['etki']} | tavsiye={analiz['tavsiye']}")

    SONUC_DOSYASI.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(sonuclar)} sonuç kaydedildi.")


if __name__ == "__main__":
    main()