import argparse
import json
import os
import time
from datetime import datetime
import feedparser

from keywords import Keywords
from news_adapter import adapt_bloomberg_news
from backend_client import BackendClient

# Bloomberg HT Tüm Haberler RSS Akışı
RSS_URL = "https://www.bloomberght.com/rss/tum-haberler.xml"

# Çekim aralığı (5 dakika = 300 saniye)
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
                seen_links = {item["link"] for item in news_list if "link" in item}
                return news_list, seen_links
        except Exception as e:
            print(f"⚠️ Var olan JSON okunurken hata oluştu, yeni dosya oluşturulacak: {e}")
    return [], set()


def fetch_and_append_news(sync_backend: bool = True):
    print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Bloomberg HT RSS Akışı kontrol ediliyor...")

    # 1. Mevcut haberleri ve kaydedilmiş linkleri al
    existing_news, seen_links = load_existing_news()

    # 2. RSS akışını çek
    feed = feedparser.parse(RSS_URL)
    if feed.bozo:
        print("❌ RSS akışı çekilirken bir hata oluştu.")
        return []

    new_raw_items = []
    new_adapted_items = []

    # RSS'ten gelen haberleri tara
    for entry in feed.entries:
        link = entry.get("link", "")
        if not link or link in seen_links:
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

            existing_news.insert(0, news_item)
            seen_links.add(link)
            new_raw_items.append(news_item)

            # News v1.0 sözleşmesine göre normalize et
            try:
                adapted = adapt_bloomberg_news(news_item)
                new_adapted_items.append(adapted)
            except Exception as e:
                print(f"⚠️ Haber normalize edilirken hata: {e}")

    # 3. Yerel JSON dosyasını güncelle
    if new_raw_items:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_news, f, ensure_ascii=False, indent=4)
        print(f"🎉 {len(new_raw_items)} adet YENİ haber tespit edildi ve JSON'a eklendi!")

        # 4. Backend'e otomatik aktarım
        if sync_backend and new_adapted_items:
            client = BackendClient()
            print(f"📡 {len(new_adapted_items)} adet haber backend'e aktarılıyor ({client.base_url})...")
            stats = client.send_news_batch(new_adapted_items)
            print(f"   Sonuç: {stats['created']} yeni kaydedildi, {stats['duplicate']} tekrar, {stats['failed']} hata.")
    else:
        print("💤 Yeni bir finansal haber bulunamadı.")

    return new_adapted_items


def start_loop(sync_backend: bool = True):
    print("🚀 Bloomberg HT Canlı Haber Takip ve Aktarım Botu Başlatıldı.")
    print(f"⏱️ Kontrol Aralığı: {FETCH_INTERVAL_SECONDS // 60} dakika\n")

    while True:
        try:
            fetch_and_append_news(sync_backend=sync_backend)
        except Exception as e:
            print(f"❌ Beklenmeyen bir hata oluştu: {e}")

        print(f"⏳ Bir sonraki kontrol için {FETCH_INTERVAL_SECONDS // 60} dakika bekleniyor...")
        time.sleep(FETCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bloomberg HT Haber Botu ve Backend Aktarıcısı")
    parser.add_argument("--bir-kez", "--once", action="store_true", help="Tek bir çekim ve aktarım yapıp sonlandır")
    parser.add_argument("--no-backend", action="store_true", help="Backend aktarımını atla, sadece JSON'a yaz")
    args = parser.parse_args()

    if args.bir_kez:
        fetch_and_append_news(sync_backend=not args.no_backend)
    else:
        start_loop(sync_backend=not args.no_backend)
