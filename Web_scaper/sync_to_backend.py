"""KAP ve Bloomberg HT haberlerini backend'e aktarma ve doğrulama aracı.

Kullanım:
  python Web_scaper/sync_to_backend.py                 # Mevcut yerel JSON'ları doğrula ve backend'e aktar
  python Web_scaper/sync_to_backend.py --fetch-bloomberg # Önce taze Bloomberg haberlerini çek ve aktar
  python Web_scaper/sync_to_backend.py --validate-only # Sadece şema ve sözleşme doğrulaması yap, gönderme
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Web_scaper"))

from news_adapter import adapt_bloomberg_news, adapt_kap_disclosure
from backend_client import BackendClient

BLOOMBERG_JSON = ROOT / "Web_scaper" / "bloomberg_trading_news.json"
KAP_JSON = ROOT / "Web_scaper" / "kap_today_disclosures.json"
SCHEMA_FILE = ROOT / "contracts" / "finance-v1.schema.json"


def get_schema_validator():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        return Draft202012Validator(
            {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/News"},
            format_checker=FormatChecker()
        )
    except Exception as e:
        print(f"⚠️ jsonschema yüklenemedi ({e}); temel kontrollerle devam ediliyor.")
        return None


def sync_all_news(validate_only: bool = False, fetch_bloomberg: bool = False):
    validator = get_schema_validator()
    client = BackendClient()

    print("==================================================================")
    print("   FINANCE EXPERT - HABER AKTARIM VE DOĞRULAMA PİPELINE")
    print(f"   Hedef Backend: {client.base_url}")
    print("==================================================================")

    if fetch_bloomberg:
        from blmbrght import fetch_and_append_news
        print("\n[+] Bloomberg HT RSS'ten taze haberler taranıyor...")
        fetch_and_append_news(sync_backend=False)

    all_adapted = []
    skipped_count = 0

    # 1. Bloomberg HT Haberleri
    if BLOOMBERG_JSON.exists():
        raw_bb = json.loads(BLOOMBERG_JSON.read_text(encoding="utf-8"))
        print(f"\n[+] Bloomberg HT kayıtları okunuyor ({len(raw_bb)} adet)...")
        for idx, item in enumerate(raw_bb):
            try:
                adapted = adapt_bloomberg_news(item)
                if validator:
                    validator.validate(adapted)
                all_adapted.append(adapted)
            except Exception as e:
                skipped_count += 1
                print(f"    [!] Bloomberg #{idx} atlandı: {e}")

    # 2. KAP Bildirimleri
    if KAP_JSON.exists():
        raw_kap = json.loads(KAP_JSON.read_text(encoding="utf-8"))
        print(f"\n[+] KAP bildirimleri okunuyor ({len(raw_kap)} adet)...")
        for idx, item in enumerate(raw_kap):
            try:
                adapted = adapt_kap_disclosure(item)
                if validator:
                    validator.validate(adapted)
                all_adapted.append(adapted)
            except Exception as e:
                skipped_count += 1
                print(f"    [!] KAP #{idx} atlandı: {e}")

    print(f"\n✅ Toplam {len(all_adapted)} geçerli News v1.0 kaydı hazırlandı (Atlanan/Hatalı: {skipped_count}).")

    if validate_only:
        print("\n🔎 '--validate-only' belirtildi, backend aktarımı yapılmadı.")
        return all_adapted

    # 3. Backend'e Gönderim
    print(f"\n📡 Backend'e aktarılıyor ({client.base_url}/api/v1/internal/news)...")
    stats = client.send_news_batch(all_adapted)

    print("\n------------------------------------------------------------------")
    print("   AKTARIM ÖZETİ")
    print("------------------------------------------------------------------")
    print(f"   İşlenen Toplam Haber: {stats['total']}")
    print(f"   Yeni Eklenen (201)  : {stats['created']}")
    print(f"   Mevcut/Tekrar (200) : {stats['duplicate']}")
    print(f"   Başarısız/Hata      : {stats['failed']}")
    print("------------------------------------------------------------------")

    if stats["failed"] > 0:
        print("\n⚠️ Karşılaşılan hatalar (ilk 5):")
        failed_entries = [d for d in stats["details"] if d.get("status") == "failed"]
        for f in failed_entries[:5]:
            print(f"   - {f.get('news_id')}: {f.get('error')}")

    return all_adapted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Haberleri backend'e aktarma ve doğrulama")
    parser.add_argument("--fetch-bloomberg", action="store_true", help="Önce Bloomberg RSS'i tara")
    parser.add_argument("--validate-only", action="store_true", help="Yalnızca şemayı doğrula, aktarma")
    args = parser.parse_args()

    sync_all_news(validate_only=args.validate_only, fetch_bloomberg=args.fetch_bloomberg)
