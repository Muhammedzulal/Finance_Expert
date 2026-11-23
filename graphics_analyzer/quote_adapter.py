"""Quote adaptörü: graphics_analyzer fiyat verilerini Finance Expert Quote v1.0 sözleşmesine çevirir.

Sözleşme kuralları:
  - contracts/finance-v1.schema.json (#/$defs/Quote)
  - docs/veri-sozlesmeleri.md ("Quote, Wallet, TradeRequest, Trade")
"""

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

SYMBOL_REGEX = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
MONEY_REGEX = re.compile(r"^(0|[1-9][0-9]*)\.[0-9]{2,6}$")


def clean_symbol(symbol: str) -> str:
    """Sağlayıcı uzantılarını temizleyip standart BIST sembolü döndürür (ör. 'THYAO.IS' -> 'THYAO')."""
    if not symbol:
        return ""
    sym = symbol.strip().upper()
    if sym.endswith(".IS"):
        sym = sym[:-3]
    return sym


def format_money(price: float | Decimal | int | str) -> str:
    """Fiyatı 2-6 ondalık basamaklı geçerli para formatına çevirir."""
    if isinstance(price, (int, float)):
        val = f"{price:.2f}"
    elif isinstance(price, Decimal):
        val = f"{price:.2f}"
    elif isinstance(price, str):
        val = price.strip().replace(",", ".")
        if "." not in val:
            val += ".00"
        else:
            tam, ondalik = val.split(".", 1)
            if len(ondalik) < 2:
                val = f"{tam}.{ondalik.ljust(2, '0')}"
            elif len(ondalik) > 6:
                val = f"{tam}.{ondalik[:6]}"
    else:
        val = f"{float(price):.2f}"

    if not MONEY_REGEX.match(val):
        raise ValueError(f"Geçersiz para formatı: {val}")
    return val


def create_quote(
    symbol: str,
    price: float | Decimal | int | str,
    as_of: datetime | str | None = None,
    currency: str = "TRY",
    provider: str = "yfinance",
    is_delayed: bool = False,
) -> dict[str, Any]:
    """Sözleşmeye uygun Quote nesnesi üretir."""
    norm_symbol = clean_symbol(symbol)
    if not SYMBOL_REGEX.match(norm_symbol):
        raise ValueError(f"Sözleşmeye uymayan hisse sembolü: {symbol} -> {norm_symbol}")

    formatted_price = format_money(price)

    # Zaman damgası
    if as_of is None:
        as_of_str = datetime.now(timezone.utc).isoformat()
    elif isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        as_of_str = as_of.isoformat()
    elif isinstance(as_of, str):
        as_of_str = as_of.strip()
    else:
        as_of_str = datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": "1.0",
        "symbol": norm_symbol,
        "price": formatted_price,
        "currency": currency,
        "as_of": as_of_str,
        "provider": provider,
        "is_delayed": is_delayed,
    }


def quote_from_dataframe(
    symbol: str,
    df,
    provider: str = "yfinance",
    is_delayed: bool = False,
) -> dict[str, Any]:
    """DataLoader çıktısı DataFrame'den son kapanış fiyatını alarak Quote üretir."""
    if df is None or len(df) == 0:
        raise ValueError(f"{symbol} için DataFrame boş")

    son_satir = df.iloc[-1]
    son_fiyat = float(son_satir["Close"])

    # DataFrame index tarihi (pandas Timestamp)
    index_tarih = df.index[-1]
    try:
        if hasattr(index_tarih, "to_pydatetime"):
            dt = index_tarih.to_pydatetime()
        else:
            dt = datetime.fromisoformat(str(index_tarih))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        as_of_str = dt.isoformat()
    except Exception:
        as_of_str = datetime.now(timezone.utc).isoformat()

    return create_quote(
        symbol=symbol,
        price=son_fiyat,
        as_of=as_of_str,
        currency="TRY",
        provider=provider,
        is_delayed=is_delayed,
    )
