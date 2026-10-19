import json
import os
import time
import feedparser
from datetime import datetime
from keywords import Keywords

# Bloomberg HT Tüm Haberler RSS Akışı
RSS_URL = "https://www.bloomberght.com/rss/tum-haberler.xml"

# Çekim aralığı (30 dakika = 1800 saniye)
FETCH_INTERVAL_SECONDS = 5 * 60

# Al/Sat kararlarını veya piyasayı etkileyebilecek anahtar kelimeler
FINANCIAL_KEYWORDS = Keywords.FINANCIAL_KEYWORDS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(SCRIPT_DIR, "bloomberg_trading_news.json")


def load_existing_news():
    """Mevcut JSON dosyasındaki haberleri ve kaydedilmiş linkleri yükler."""
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                news_list = json.load(f)
                # Daha önce kaydedilmiş haberlerin linklerini benzersiz bir kümede (set) topluyoruz
                seen_links = {item["link"] for item in news_list if "link" in item}
                return news_list, seen_links
        except Exception as e:
            print(
                f"⚠️ Var olan JSON okunurken hata oluştu, yeni dosya oluşturulacak: {e}"
            )
    return [], set()


def fetch_and_append_news():
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] RSS Akışı kontrol ediliyor...")

    # 1. Mevcut haberleri ve kaydedilmiş linkleri al
    existing_news, seen_links = load_existing_news()

    # 2. RSS akışını çek
    feed = feedparser.parse(RSS_URL)
    if feed.bozo:
        print("❌ RSS akışı çekilirken bir hata oluştu.")
        return

    new_items_added = 0

    # RSS'ten gelen haberleri tara
    for entry in feed.entries:
        link = entry.get("link", "")

        # EĞER HABER DAHA ÖNCE KAYDEDİLDİYSE PAS GEÇ (TEKRARI ENGELE)
        if link in seen_links:
            continue

        title = entry.get("title", "")
        summary = entry.get("summary", "")
        published = entry.get("published", "")

        content_text = f"{title} {summary}".lower()
        matched_keywords = [kw for kw in FINANCIAL_KEYWORDS if kw in content_text]

        if matched_keywords:
            news_item = {
                "source": "Bloomberg HT",
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "matched_keywords": matched_keywords,
            }

            # Hem listeye hem de kontrol kümesine ekle
            existing_news.insert(0, news_item)  # En yeni haberi en başa ekler
            seen_links.add(link)
            new_items_added += 1

    # 3. Eğer yeni haber varsa JSON dosyasını güncelle
    if new_items_added > 0:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_news, f, ensure_ascii=False, indent=4)
        print(f"🎉 {new_items_added} adet YENİ haber tespit edildi ve JSON'a eklendi!")
    else:
        print("💤 Yeni bir finansal haber bulunamadı.")


def start_loop():
    print("🚀 Bloomberg HT Canlı Haber Takip Botu Başlatıldı.")
    print(f"⏱️ Kontrol Aralığı: {FETCH_INTERVAL_SECONDS // 60} dakika\n")

    while True:
        try:
            fetch_and_append_news()
        except Exception as e:
            print(f"❌ Beklenmeyen bir hata oluştu: {e}")

        print(
            f"⏳ Bir sonraki kontrol için {FETCH_INTERVAL_SECONDS // 60} dakika bekleniyor..."
        )
        time.sleep(FETCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    start_loop()
