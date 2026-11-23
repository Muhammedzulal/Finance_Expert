import argparse
import json
import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from news_adapter import adapt_kap_disclosure
from backend_client import BackendClient


def scrape_kap_today(sync_backend: bool = True):
    with sync_playwright() as p:
        # Otomasyon tespitini zorlaştıran argümanlar
        browser = p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )

        # Gerçek tarayıcı süsü (User-Agent) ekliyoruz
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        print("🌍 KAP sorgu sayfasına gidiliyor...")
        page.goto("https://www.kap.org.tr/tr/bildirim-sorgu", wait_until="networkidle")

        print("🖱️ 'Ara' butonuna tıklanıyor...")
        try:
            ara_button = page.get_by_role(
                "button", name=re.compile("Ara", re.IGNORECASE)
            )
            if not ara_button.is_visible():
                ara_button = page.locator(
                    "button:has-text('Ara'), div:has-text('Ara')"
                ).last

            ara_button.click()
            print("✅ 'Ara' butonuna başarıyla tıklandı!")

        except Exception as e:
            print(f"⚠️ Buton standart yolla tıklanamadı, JavaScript tetikleniyor: {e}")
            page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button, div, a'));
                    const target = btns.find(b => b.innerText.trim() === 'Ara');
                    if (target) target.click();
                }
            """)

        print("⏳ Sonuç tablosu bekleniyor...")
        try:
            page.wait_for_selector("tr[id^='notification']", timeout=20000)
            print("🎉 Bildirimler ekrana geldi!")

            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            rows = soup.find_all("tr", id=lambda x: x and x.startswith("notification"))

            disclosures = []
            adapted_news = []
            for row in rows:
                checkbox_input = row.find("input", {"type": "checkbox"})
                disclosure_id = checkbox_input.get("id") if checkbox_input else None

                tds = row.find_all("td")
                if len(tds) > 7:
                    title = tds[4].get_text(strip=True) if len(tds) > 4 else ""
                    disclosure_type = (
                        tds[6].get_text(strip=True) if len(tds) > 6 else ""
                    )
                    summary = tds[7].get_text(strip=True) if len(tds) > 7 else ""
                    stock = tds[8].get_text(strip=True) if len(tds) > 8 else ""

                    item = {
                        "source": "KAP",
                        "disclosure_id": disclosure_id,
                        "stock_code": stock,
                        "title": title,
                        "disclosure_type": disclosure_type,
                        "summary": summary,
                        "detail_url": (
                            f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"
                            if disclosure_id
                            else ""
                        ),
                    }
                    disclosures.append(item)

                    try:
                        adapted = adapt_kap_disclosure(item)
                        adapted_news.append(adapted)
                    except Exception as err:
                        print(f"⚠️ Bildirim normalize edilemedi ({disclosure_id}): {err}")

            print(f"💾 Toplam {len(disclosures)} adet bildirim çekildi.")

            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, "kap_today_disclosures.json")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(disclosures, f, ensure_ascii=False, indent=4)
            print("✅ Veriler 'kap_today_disclosures.json' dosyasına yazıldı.")

            # Backend'e otomatik aktarım
            if sync_backend and adapted_news:
                client = BackendClient()
                print(f"📡 {len(adapted_news)} adet KAP bildirimi backend'e aktarılıyor ({client.base_url})...")
                stats = client.send_news_batch(adapted_news)
                print(f"   Sonuç: {stats['created']} yeni kaydedildi, {stats['duplicate']} tekrar, {stats['failed']} hata.")

            browser.close()
            return adapted_news

        except Exception as e:
            print(f"❌ Tablo yüklenirken hata oluştu: {e}")
            page.screenshot(path="debug_error2.png")
            browser.close()
            return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAP Bildirim Çekici ve Backend Aktarıcısı")
    parser.add_argument("--no-backend", action="store_true", help="Backend aktarımını atla, sadece JSON'a yaz")
    args = parser.parse_args()

    scrape_kap_today(sync_backend=not args.no_backend)
