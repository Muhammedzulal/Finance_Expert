"""News adaptörü: KAP ve Bloomberg HT verilerini Finance Expert News v1.0 sözleşmesine çevirir.

Sözleşme kuralları:
  - contracts/finance-v1.schema.json (#/$defs/News)
  - docs/veri-sozlesmeleri.md ("Mevcut botlardan geçiş tablosu")
"""

import hashlib
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlunparse
from typing import Any

from keywords import Keywords

# BIST Şirket Adları ve Eşleşen Semboller
# Modelin ve backend'in tanıdığı standart BIST hisse sembolleri
COMPANY_SYMBOL_MAP = {
    # Havacılık & Ulaştırma
    "türk hava yolları": "THYAO",
    "turk hava yollari": "THYAO",
    "thy": "THYAO",
    "pegasus": "PGSUS",
    "tav havalimanları": "TAVHL",
    "tav havalimanlari": "TAVHL",
    # Bankacılık & Finans
    "garanti bbva": "GARAN",
    "garanti bankası": "GARAN",
    "garanti bankasi": "GARAN",
    "akbank": "AKBNK",
    "iş bankası": "ISCTR",
    "is bankasi": "ISCTR",
    "yapı kredi": "YKBNK",
    "yapi kredi": "YKBNK",
    "şekerbank": "SKBNK",
    "sekerbank": "SKBNK",
    "halkbank": "HALKB",
    "vakıfbank": "VAKBN",
    "vakifbank": "VAKBN",
    # Savunma & Teknoloji & Telekomünikasyon
    "aselsan": "ASELS",
    "turkcell": "TCELL",
    "türk telekom": "TTKOM",
    "turk telekom": "TTKOM",
    "kontrolmatik": "KONTR",
    "astor enerji": "ASTOR",
    "astor": "ASTOR",
    # Holding & Sanayi & Enerji
    "koç holding": "KCHOL",
    "koc holding": "KCHOL",
    "sabancı holding": "SAHOL",
    "sabanci holding": "SAHOL",
    "tüpraş": "TUPRS",
    "tupras": "TUPRS",
    "şişecam": "SISE",
    "sisecam": "SISE",
    "ereğli": "EREGL",
    "eregli": "EREGL",
    "erdemir": "EREGL",
    "kardemir": "KRDMD",
    "petkim": "PETKM",
    "ford otosan": "FROTO",
    "tofaş": "TOASO",
    "tofas": "TOASO",
    "çemaş": "CEMAS",
    "cemas": "CEMAS",
    "mercan kimya": "MERCN",
    "enerjisa": "ENJSA",
    "alarko holding": "ALARK",
    "alarko": "ALARK",
    "sasa polyester": "SASA",
    "sasa": "SASA",
    "hektaş": "HEKTS",
    "hektas": "HEKTS",
    # Perakende & Tüketim & Gıda
    "bim": "BIMAS",
    "migros": "MGROS",
    "şok marketler": "SOKM",
    "sok marketler": "SOKM",
    "ülker": "ULKER",
    "ulker": "ULKER",
    "vestel": "VESTL",
    "mavi giyim": "MAVI",
    "otokar": "OTKAR",
}

SYMBOL_REGEX = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
FINANCIAL_KEYWORDS = Keywords.FINANCIAL_KEYWORDS


def tr_lower(text: str) -> str:
    """Türkçe karakterleri gözeterek küçük harfe çevirir."""
    if not text:
        return ""
    return text.replace("İ", "i").replace("I", "ı").lower()


def clean_html(raw_html: str) -> str:
    """HTML etiketlerini ve özel HTML karakterlerini temizler."""
    if not raw_html:
        return ""
    # HTML entities çözümlenir (örn &amp; -> &)
    text = html.unescape(raw_html)
    # Etiketleri kaldır
    text = re.sub(r"<[^>]+>", " ", text)
    # Birden fazla boşluğu teke indir
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url: str) -> str:
    """Sözleşmeye uygun URL normalizasyonu:
    - Baş/son boşluğu kaldır
    - Scheme ve hostname küçük harf
    - Fragment (#...) kaldır
    - Varsayılan HTTPS portunu (:443) kaldır
    - Path ve query'yi koru
    """
    if not url:
        return ""
    url = url.strip()
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if netloc.endswith(":443"):
        netloc = netloc[:-4]

    # Fragment boşaltılır
    normalized = urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, ""))
    return normalized


def extract_symbols(text: str, explicit_symbol: str | None = None) -> list[str]:
    """Metinden veya hazır hisse kodundan geçerli BIST hisse sembollerini çıkarır."""
    found_symbols = []

    # 1. Hazır verilen sembol (KAP stock_code veya başlık uzantısı)
    if explicit_symbol:
        cand = explicit_symbol.strip().upper()
        if SYMBOL_REGEX.match(cand) and cand not in ("-", "NULL", "NONE"):
            found_symbols.append(cand)

    # 2. KAP başlığındaki '/ CEMAS' veya '/ THYAO, GARAN' deseni
    if "/" in text:
        after_slash = text.rsplit("/", 1)[1]
        for part in after_slash.split(","):
            cand = part.strip().upper()
            if SYMBOL_REGEX.match(cand) and cand not in found_symbols and cand not in ("-", "KAP"):
                found_symbols.append(cand)

    # 3. Şirket isimleri tablosu üzerinden arama
    lower_text = tr_lower(text)
    for company_name, sym in COMPANY_SYMBOL_MAP.items():
        if re.search(rf"(?<!\w){re.escape(company_name)}(?!\w)", lower_text):
            if sym not in found_symbols:
                found_symbols.append(sym)

    # 4. Metin içinde doğrudan büyük harfli sembol geçiyorsa
    for sym in set(COMPANY_SYMBOL_MAP.values()):
        if sym not in found_symbols:
            if re.search(rf"\b{sym}\b", text):
                found_symbols.append(sym)

    return found_symbols


def extract_keywords(text: str) -> list[str]:
    """Metin içindeki finansal anahtar kelimeleri tespit edip tekilleştirir."""
    if not text:
        return []
    lower_text = tr_lower(text)
    matched = [kw for kw in FINANCIAL_KEYWORDS if kw in lower_text]
    # Tekilleştir ve sıralamayı koru
    seen = set()
    result = []
    for kw in matched:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


def parse_rfc3339_or_none(date_str: str | None) -> str | None:
    """Çeşitli tarih biçimlerini RFC 3339 / ISO 8601 (saat dilimli) biçimine çevirir."""
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()
    try:
        # Örn RSS: "Fri, 16 Oct 2026 21:04:41 GMT"
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        pass

    try:
        # ISO format denemesi
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            # Yerel saat ise UTC olarak işaretle veya +03:00 kabul et
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        pass

    return None


def now_rfc3339() -> str:
    """Şu anki zamanı UTC bazında RFC 3339 olarak döndürür."""
    return datetime.now(timezone.utc).isoformat()


def adapt_bloomberg_news(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Ham Bloomberg HT haberini News v1.0 formatına çevirir."""
    link = raw_item.get("link") or raw_item.get("url") or ""
    norm_url = normalize_url(link)
    if not norm_url.startswith("https://"):
        raise ValueError(f"Geçersiz HTTPS URL: {link}")

    news_id = "bloomberg_ht:" + hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

    title = clean_html(raw_item.get("title") or "")
    if not title:
        raise ValueError("Haber başlığı boş olamaz")

    summary = clean_html(raw_item.get("summary") or "")

    # Tarihler
    published_raw = raw_item.get("published") or raw_item.get("published_at")
    published_at = parse_rfc3339_or_none(published_raw)

    fetched_raw = raw_item.get("fetched_at")
    fetched_at = parse_rfc3339_or_none(fetched_raw) or now_rfc3339()

    # Semboller ve anahtar kelimeler
    full_text = f"{title} {summary}"
    symbols = extract_symbols(full_text)
    matched_keywords = raw_item.get("matched_keywords") or extract_keywords(full_text)
    # Anahtar kelimeleri tekilleştir
    matched_keywords = list(dict.fromkeys(matched_keywords))

    return {
        "schema_version": "1.0",
        "news_id": news_id,
        "source": "BLOOMBERG_HT",
        "source_id": None,
        "title": title,
        "summary": summary,
        "url": norm_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "symbols": symbols,
        "matched_keywords": matched_keywords,
        "disclosure_type": None,
    }


def adapt_kap_disclosure(raw_item: dict[str, Any]) -> dict[str, Any]:
    """Ham KAP bildirimini News v1.0 formatına çevirir."""
    disclosure_id = str(raw_item.get("disclosure_id") or "").strip()
    detail_url = raw_item.get("detail_url") or raw_item.get("url") or ""

    if not detail_url and disclosure_id:
        detail_url = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"

    norm_url = normalize_url(detail_url)
    if not norm_url.startswith("https://"):
        raise ValueError(f"Geçersiz HTTPS URL: {detail_url}")

    if disclosure_id:
        news_id = f"kap:{disclosure_id}"
        source_id = disclosure_id
    else:
        news_id = "kap:url:" + hashlib.sha256(norm_url.encode("utf-8")).hexdigest()
        source_id = None

    title = clean_html(raw_item.get("title") or "")
    if not title:
        raise ValueError("KAP bildirimi başlığı boş olamaz")

    summary = clean_html(raw_item.get("summary") or "")

    # Stock code
    stock_code = raw_item.get("stock_code") or ""
    full_text = f"{title} {summary}"
    symbols = extract_symbols(full_text, explicit_symbol=stock_code)

    published_raw = raw_item.get("published_at") or raw_item.get("published")
    published_at = parse_rfc3339_or_none(published_raw)

    fetched_raw = raw_item.get("fetched_at")
    fetched_at = parse_rfc3339_or_none(fetched_raw) or now_rfc3339()

    disclosure_type = clean_html(raw_item.get("disclosure_type") or "") or None

    matched_keywords = raw_item.get("matched_keywords") or extract_keywords(full_text)
    matched_keywords = list(dict.fromkeys(matched_keywords))

    return {
        "schema_version": "1.0",
        "news_id": news_id,
        "source": "KAP",
        "source_id": source_id,
        "title": title,
        "summary": summary,
        "url": norm_url,
        "published_at": published_at,
        "fetched_at": fetched_at,
        "symbols": symbols,
        "matched_keywords": matched_keywords,
        "disclosure_type": disclosure_type,
    }
