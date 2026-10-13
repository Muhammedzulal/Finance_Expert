import json
import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def scrape_kap_today():
    with sync_playwright() as p:
        # headless=True yaparsan arka planda sessizce çalışır
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 800, "height": 600})
        page = context.new_page()

        print("🌍 KAP sorgu sayfasına gidiliyor...")
        page.goto(
            "https://www.kap.org.tr/tr/bildirim-sorgu", wait_until="domcontentloaded"
        )

        # Sayfanın etkileşime hazır olması için kısa bir es
        page.wait_for_timeout(2000)

        print("🖱️ 'Ara' butonuna tıklanıyor...")
        try:
            # 1. Butona resmi Playwright yöntemiyle (Case-insensitive) tıkla
            ara_button = page.get_by_role(
                "button", name=re.compile("Ara", re.IGNORECASE)
            )
            if not ara_button.is_visible():
                # Alternatif locator
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

        # 2. Sonuç tablosunun yüklenmesini bekle
        print("⏳ Sonuç tablosu bekleniyor...")
        try:
            # Tablodaki bildirim satırlarını bekle
            page.wait_for_selector("tr[id^='notification']", timeout=15000)
            print("🎉 Bildirimler ekrana geldi!")

            # 3. DOM HTML'ini alıp BeautifulSoup ile ayıkla
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            rows = soup.find_all("tr", id=lambda x: x and x.startswith("notification"))

            disclosures = []
            for row in rows:
                checkbox_input = row.find("input", {"type": "checkbox"})
                disclosure_id = checkbox_input.get("id") if checkbox_input else None

                tds = row.find_all("td")
                if len(tds) > 7:
                    # Tablodaki sütun metinlerini temizle
                    title = tds[4].get_text(strip=True) if len(tds) > 4 else ""
                    disclosure_type = (
                        tds[6].get_text(strip=True) if len(tds) > 6 else ""
                    )
                    summary = tds[7].get_text(strip=True) if len(tds) > 7 else ""
                    stock = tds[8].get_text(strip=True) if len(tds) > 8 else ""

                    disclosures.append(
                        {
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
                    )

            print(f"💾 Toplam {len(disclosures)} adet bildirim çekildi.")

            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, "kap_today_disclosures.json")

            # JSON dosyasına kaydediyoruz
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(disclosures, f, ensure_ascii=False, indent=4)
            print("✅ Veriler 'kap_today_disclosures.json' dosyasına yazıldı.")

            browser.close()
            return disclosures

        except Exception as e:
            print(f"❌ Tablo yüklenirken hata oluştu: {e}")
            page.screenshot(path="debug_error2.png")
            browser.close()
            return []


if __name__ == "__main__":
    scrape_kap_today()
