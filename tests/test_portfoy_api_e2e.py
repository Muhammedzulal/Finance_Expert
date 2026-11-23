"""Hafta 4 / Ensar: fiyat gecmisi, islem gecmisi ve portfoy API'lerinin
uctan uca testi.

Mobil uygulamanin izleyecegi akisi adim adim taklit eder:
  kayit -> giris -> fiyat gecmisi -> alis -> tekrar alis -> satis
  -> islem gecmisi -> portfoy degeri
ve HER islemden sonra hem API yanitini hem de MySQL'deki kaydi
(users, wallets, positions, trades, quotes) kontrol eder.

Beklenen tutarlar elle hesaplanmistir (docs/financial-qa formulleri):
backend'in kendi hesabiyla degil, bagimsiz bir hesapla karsilastirilir.

Calisan bir backend ve MySQL gerekir; ortam degiskenleri yoksa testler
atlanir (CI'daki sozlesme isini bozmaz):

  E2E_BACKEND_URL       ornek: http://127.0.0.1:8001
  E2E_INTERNAL_API_KEY  backend'in INTERNAL_API_KEY degeri
  E2E_DB_HOST / E2E_DB_PORT / E2E_DB_NAME / E2E_DB_USER / E2E_DB_PASSWORD

Backend TRADE_ALLOWED_QUOTE_PROVIDERS=TEST ile baslatilmalidir; test,
her islemden hemen once taze bir TEST fiyati gonderir (60 sn kurali).

Calistirma:
  python -m pytest -v tests/test_portfoy_api_e2e.py
"""

import json
import os
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

BACKEND_URL = os.environ.get("E2E_BACKEND_URL", "").rstrip("/")
INTERNAL_KEY = os.environ.get("E2E_INTERNAL_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not BACKEND_URL or not INTERNAL_KEY,
    reason="E2E_BACKEND_URL ve E2E_INTERNAL_API_KEY tanimli degil",
)

SYMBOL = "THYAO"          # Ana senaryo hissesi
STALE_SYMBOL = "AKBNK"    # Bu hisseye hic taze fiyat gonderilmez
PROVIDER = "TEST"


# --------------------------------------------------
# Yardimcilar
# --------------------------------------------------

def api(method, path, body=None, token=None, internal=False):
    """Backend'e istek atar; (durum_kodu, json_govde) dondurur."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if internal:
        headers["X-API-Key"] = INTERNAL_KEY
    req = urllib.request.Request(BACKEND_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, raw.decode("utf-8", "replace")


@pytest.fixture(scope="module")
def db():
    pymysql = pytest.importorskip("pymysql")
    conn = pymysql.connect(
        host=os.environ.get("E2E_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("E2E_DB_PORT", "3306")),
        user=os.environ.get("E2E_DB_USER", ""),
        password=os.environ.get("E2E_DB_PASSWORD", ""),
        database=os.environ.get("E2E_DB_NAME", "finance_expert"),
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    yield conn
    conn.close()


def q(db, sql, *params):
    """Tek satir dondurur (yoksa None)."""
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def qall(db, sql, *params):
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def utc_now():
    return datetime.now(timezone.utc)


def post_quote(symbol, price, as_of=None, provider=PROVIDER):
    as_of = as_of or utc_now()
    status, body = api("POST", "/api/v1/internal/quotes", {
        "schema_version": "1.0",
        "symbol": symbol,
        "price": str(price),
        "currency": "TRY",
        "as_of": as_of.isoformat(),
        "provider": provider,
        "is_delayed": False,
    }, internal=True)
    assert status == 201, (status, body)
    return as_of


def trade(wallet_id, token, side, qty, key=None, symbol=SYMBOL):
    key = key or str(uuid.uuid4())
    status, body = api("POST", f"/api/v1/wallets/{wallet_id}/trades", {
        "schema_version": "1.0",
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "idempotency_key": key,
    }, token=token)
    return status, body, key


def wallet_row(db, numeric_wallet_id):
    return q(db, "SELECT cash_balance, realized_pnl FROM wallets WHERE wallet_id = %s",
             numeric_wallet_id)


def position_row(db, numeric_wallet_id, symbol=SYMBOL):
    return q(db, "SELECT quantity, average_cost FROM positions WHERE wallet_id = %s AND symbol = %s",
             numeric_wallet_id, symbol)


def trade_count(db, numeric_wallet_id):
    return q(db, "SELECT COUNT(*) AS n FROM trades WHERE wallet_id = %s", numeric_wallet_id)["n"]


def new_user(db):
    """Kayit + giris yapar; (token, wallet_id_metni, numeric_wallet_id) dondurur."""
    email = f"e2e-{uuid.uuid4().hex[:12]}@example.com"
    password = "Guclu-Sifre-12345"
    status, body = api("POST", "/api/v1/users/register", {
        "full_name": "E2E Test Kullanicisi",
        "email": email,
        "password": password,
    })
    assert status == 201, (status, body)
    assert body["initial_cash_balance"] == "100000.00"

    # DB: kullanici ve cuzdan birlikte olusmus olmali
    user = q(db, "SELECT id, password_hash FROM users WHERE email = %s", email)
    assert user is not None and user["id"] == body["user_id"]
    assert user["password_hash"] != password  # sifre duz metin saklanmiyor
    w = q(db, "SELECT wallet_id, user_id, currency, cash_balance, realized_pnl FROM wallets WHERE user_id = %s",
          user["id"])
    assert w["wallet_id"] == body["wallet_id"]
    assert w["currency"] == "TRY"
    assert w["cash_balance"] == Decimal("100000.00")
    assert w["realized_pnl"] == Decimal("0.00")

    status, login = api("POST", "/api/v1/users/login", {"email": email, "password": password})
    assert status == 200, (status, login)
    token = login["access_token"]

    status, me = api("GET", "/api/v1/users/me", token=token)
    assert status == 200 and me["wallet_id"] == w["wallet_id"]
    return token, f"wallet:{w['wallet_id']}", w["wallet_id"]


# --------------------------------------------------
# Ana senaryo: mobil uygulamanin tam akisi
# --------------------------------------------------

@pytest.fixture(scope="module")
def user(db):
    return new_user(db)


@pytest.fixture(scope="module")
def other_user(db):
    return new_user(db)


def test_01_fiyat_gecmisi(db):
    """GET /stocks/{symbol}/history: eskiden yeniye, limit, hata kodlari."""
    base = utc_now() - timedelta(minutes=30)
    prices = ["300.10", "301.20", "302.30", "303.40", "304.50"]
    times = [post_quote(SYMBOL, p, base + timedelta(minutes=i)) for i, p in enumerate(prices)]

    status, body = api("GET", f"/api/v1/stocks/{SYMBOL}/history?limit=500")
    assert status == 200, body
    assert body["symbol"] == SYMBOL
    assert body["count"] == len(body["history"])
    as_ofs = [h["as_of"] for h in body["history"]]
    assert as_ofs == sorted(as_ofs), "Grafik icin eski -> yeni sirali olmali"

    # Az once gonderilen 5 fiyat gecmiste, ayni sirayla ve ayni degerlerle.
    # Yalnizca bu kosuda gonderilen zaman damgalarina bakilir; onceki
    # kosulardan kalan fiyatlar testi etkilemez.
    sent = {t.astimezone(timezone.utc).replace(tzinfo=None) for t in times}
    ours = [h for h in body["history"]
            if h["provider"] == PROVIDER
            and datetime.fromisoformat(h["as_of"].replace("Z", "+00:00")).replace(tzinfo=None) in sent]
    assert [Decimal(h["price"]) for h in ours] == [Decimal(p) for p in prices]
    assert all(set(h) >= {"price", "currency", "as_of", "provider", "is_delayed"} for h in ours)

    # limit=2 en yeni iki kaydi, yine eskiden yeniye verir
    status, body2 = api("GET", f"/api/v1/stocks/{SYMBOL}/history?limit=2")
    assert status == 200 and body2["count"] == 2
    assert body2["history"] == body["history"][-2:]

    # DB ile ayni sayi (limit sinirinin altindaysa)
    n = q(db, "SELECT COUNT(*) AS n FROM quotes WHERE symbol = %s", SYMBOL)["n"]
    assert body["count"] == min(n, 500)

    assert api("GET", "/api/v1/stocks/ZZZZZ/history")[0] == 404
    assert api("GET", "/api/v1/stocks/thyao/history")[0] == 422
    assert api("GET", f"/api/v1/stocks/{SYMBOL}/history?limit=0")[0] == 422
    assert api("GET", f"/api/v1/stocks/{SYMBOL}/history?limit=501")[0] == 422


def test_02_ilk_alis(db, user):
    token, wid, nwid = user
    quote_at = post_quote(SYMBOL, "312.75")
    status, body, key = trade(wid, token, "buy", 10)
    assert status == 201, body

    # API yaniti
    assert body["wallet_id"] == wid
    assert body["symbol"] == SYMBOL and body["side"] == "buy" and body["quantity"] == 10
    assert body["execution_price"] == "312.750000"
    assert body["gross_amount"] == "3127.50"
    assert body["idempotency_key"] == key
    assert body["currency"] == "TRY"
    assert datetime.fromisoformat(body["quote_as_of"].replace("Z", "+00:00")) == quote_at.replace(
        microsecond=quote_at.microsecond)
    executed = datetime.fromisoformat(body["executed_at"].replace("Z", "+00:00"))
    assert abs((executed - utc_now()).total_seconds()) < 120, "executed_at UTC olmali"

    # DB: trade satiri
    trade_id = int(body["trade_id"].split(":")[1])
    t = q(db, "SELECT * FROM trades WHERE trade_id = %s", trade_id)
    assert t["wallet_id"] == nwid and t["side"] == "BUY" and t["quantity"] == 10
    assert t["price"] == Decimal("312.750000")
    assert t["total_amount"] == Decimal("3127.50")
    assert t["realized_pnl"] == Decimal("0.00")
    assert t["idempotency_key"] == key

    # DB: pozisyon ve bakiye
    p = position_row(db, nwid)
    assert p["quantity"] == 10 and p["average_cost"] == Decimal("312.750000")
    w = wallet_row(db, nwid)
    assert w["cash_balance"] == Decimal("96872.50")   # 100000 - 3127.50

    # Mobil cuzdan ekrani ayni veriyi gormeli
    status, wallet = api("GET", f"/api/v1/wallets/{wid}", token=token)
    assert status == 200
    assert wallet["cash_balance"] == "96872.50"
    assert wallet["positions"] == [{"symbol": SYMBOL, "quantity": 10, "average_cost": "312.750000"}]

    user_state["first_key"] = key
    user_state["first_trade_id"] = body["trade_id"]


user_state = {}


def test_03_ayni_istegin_tekrari(db, user):
    """Mobil ag hatasi sonrasi ayni anahtarla tekrar gonderirse ikinci islem olmamali."""
    token, wid, nwid = user
    before_count = trade_count(db, nwid)
    before_wallet = wallet_row(db, nwid)

    status, body, _ = trade(wid, token, "buy", 10, key=user_state["first_key"])
    assert status == 200, body
    assert body["trade_id"] == user_state["first_trade_id"]
    assert trade_count(db, nwid) == before_count
    assert wallet_row(db, nwid) == before_wallet

    # Ayni anahtar, farkli icerik -> 409
    status, body, _ = trade(wid, token, "buy", 11, key=user_state["first_key"])
    assert status == 409 and body["detail"] == "IDEMPOTENCY_CONFLICT"
    assert trade_count(db, nwid) == before_count


def test_04_ikinci_alis_ortalama_maliyet(db, user):
    token, wid, nwid = user
    post_quote(SYMBOL, "320.10")
    status, body, _ = trade(wid, token, "buy", 5)
    assert status == 201, body
    assert body["gross_amount"] == "1600.50"

    # (10*312.75 + 5*320.10) / 15 = 4728.00 / 15 = 315.20
    p = position_row(db, nwid)
    assert p["quantity"] == 15 and p["average_cost"] == Decimal("315.200000")
    assert wallet_row(db, nwid)["cash_balance"] == Decimal("95272.00")  # 96872.50 - 1600.50


def test_05_kismi_satis_gerceklesen_kar(db, user):
    token, wid, nwid = user
    post_quote(SYMBOL, "330.55")
    status, body, _ = trade(wid, token, "sell", 6)
    assert status == 201, body
    assert body["side"] == "sell" and body["gross_amount"] == "1983.30"

    # Gerceklesen K/Z = 6 * (330.55 - 315.20) = 92.10
    t = q(db, "SELECT side, realized_pnl, total_amount FROM trades WHERE trade_id = %s",
          int(body["trade_id"].split(":")[1]))
    assert t["side"] == "SELL" and t["realized_pnl"] == Decimal("92.10")
    p = position_row(db, nwid)
    assert p["quantity"] == 9
    assert p["average_cost"] == Decimal("315.200000"), "Satis ortalama maliyeti degistirmemeli"
    w = wallet_row(db, nwid)
    assert w["cash_balance"] == Decimal("97255.30")   # 95272.00 + 1983.30
    assert w["realized_pnl"] == Decimal("92.10")


def test_06_basarisiz_islemler_db_degistirmez(db, user):
    token, wid, nwid = user
    snapshot = (trade_count(db, nwid), wallet_row(db, nwid), position_row(db, nwid))

    post_quote(SYMBOL, "312.75")
    status, body, _ = trade(wid, token, "buy", 1000)          # 312750 > 97255.30
    assert status == 409 and body["detail"] == "INSUFFICIENT_FUNDS"

    status, body, _ = trade(wid, token, "sell", 100)          # 9 adet var
    assert status == 409 and body["detail"] == "INSUFFICIENT_POSITION"

    status, body, _ = trade(wid, token, "sell", 1, symbol="GARAN")  # hic pozisyon yok
    assert status in (409,), body

    # 10 dakikalik fiyatla islem yapilamaz
    post_quote(STALE_SYMBOL, "60.00", utc_now() - timedelta(minutes=10))
    status, body, _ = trade(wid, token, "buy", 1, symbol=STALE_SYMBOL)
    assert status == 409 and body["detail"].startswith("STALE_QUOTE")

    status, body, _ = trade(wid, token, "buy", 1, symbol="ZZZZZ")
    assert status == 400

    status, _, _ = trade(wid, token, "buy", 0)
    assert status == 422

    assert (trade_count(db, nwid), wallet_row(db, nwid), position_row(db, nwid)) == snapshot


def test_07_islem_gecmisi(db, user):
    token, wid, nwid = user
    status, body = api("GET", f"/api/v1/wallets/{wid}/trades?limit=100", token=token)
    assert status == 200, body
    assert body["wallet_id"] == wid
    assert body["total"] == trade_count(db, nwid) == 3
    assert body["has_more"] is False

    items = body["items"]
    assert [i["side"] for i in items] == ["sell", "buy", "buy"], "En yeniden eskiye"
    assert [i["quantity"] for i in items] == [6, 5, 10]
    assert [i["realized_pnl"] for i in items] == ["92.10", "0.00", "0.00"]

    # Her satir DB ile birebir
    rows = {f"trade:{r['trade_id']}": r for r in qall(
        db, "SELECT trade_id, price, total_amount, realized_pnl FROM trades WHERE wallet_id = %s", nwid)}
    for i in items:
        r = rows[i["trade_id"]]
        assert Decimal(i["execution_price"]) == r["price"]
        assert Decimal(i["gross_amount"]) == r["total_amount"]
        assert Decimal(i["realized_pnl"]) == r["realized_pnl"]

    # Sayfalama
    status, page = api("GET", f"/api/v1/wallets/{wid}/trades?limit=2&offset=0", token=token)
    assert page["has_more"] is True and len(page["items"]) == 2
    status, page2 = api("GET", f"/api/v1/wallets/{wid}/trades?limit=2&offset=2", token=token)
    assert page2["has_more"] is False and len(page2["items"]) == 1
    assert [i["trade_id"] for i in page["items"] + page2["items"]] == [i["trade_id"] for i in items]


def test_08_portfoy_degeri(db, user):
    token, wid, nwid = user
    post_quote(SYMBOL, "333.00")
    status, v = api("GET", f"/api/v1/wallets/{wid}/valuation", token=token)
    assert status == 200, v

    # Elle hesap:
    #   piyasa degeri   = 9 * 333.00              = 2997.00
    #   maliyet         = 9 * 315.20              = 2836.80
    #   gerceklesmemis  = 2997.00 - 2836.80       = 160.20
    #   yuzde           = 160.20 / 2836.80 * 100  = 5.65
    #   portfoy         = 97255.30 + 2997.00      = 100252.30
    assert v["cash_balance"] == "97255.30"
    assert v["realized_pnl"] == "92.10"
    assert v["positions_cost"] == "2836.80"
    assert v["positions_value"] == "2997.00"
    assert v["unrealized_pnl"] == "160.20"
    assert v["unrealized_pnl_percent"] == "5.65"
    assert v["portfolio_value"] == "100252.30"
    assert v["valuation_complete"] is True

    [pos] = v["positions"]
    assert pos["symbol"] == SYMBOL and pos["quantity"] == 9
    assert pos["last_price"] == "333.000000"
    assert pos["market_value"] == "2997.00" and pos["unrealized_pnl"] == "160.20"

    # TEST fiyatiyla yapilan degerleme "guncel" sayilmamali ve uyari vermeli
    assert pos["price_is_test"] is True and pos["price_status"] == "test"
    assert v["valuation_is_current"] is False
    assert any(SYMBOL in w for w in v["warnings"])

    # Toplam: nakit + pozisyon = baslangic + gerceklesen + gerceklesmemis
    assert Decimal(v["portfolio_value"]) == (
        Decimal("100000.00") + Decimal(v["realized_pnl"]) + Decimal(v["unrealized_pnl"]))


def test_09_baskasinin_cuzdani_ve_yetkisiz_erisim(user, other_user):
    token, wid, _ = user
    other_token, other_wid, _ = other_user
    for path in (f"/api/v1/wallets/{wid}", f"/api/v1/wallets/{wid}/trades",
                 f"/api/v1/wallets/{wid}/valuation"):
        assert api("GET", path, token=other_token)[0] == 404, path
        assert api("GET", path)[0] == 401, path
        assert api("GET", path, token="bozuk.token.degeri")[0] == 401, path
    status, _, _ = trade(wid, other_token, "buy", 1)
    assert status == 404
    assert api("GET", "/api/v1/wallets/1abc/trades", token=token)[0] == 400


def test_10_tum_pozisyonu_satmak(db, user):
    token, wid, nwid = user
    post_quote(SYMBOL, "310.00")
    status, body, _ = trade(wid, token, "sell", 9)
    assert status == 201, body
    # 9 * (310.00 - 315.20) = -46.80 ; toplam gerceklesen 92.10 - 46.80 = 45.30
    assert position_row(db, nwid) is None, "Biten pozisyon silinmeli"
    w = wallet_row(db, nwid)
    assert w["realized_pnl"] == Decimal("45.30")
    assert w["cash_balance"] == Decimal("100045.30")  # 97255.30 + 2790.00

    status, v = api("GET", f"/api/v1/wallets/{wid}/valuation", token=token)
    assert v["positions"] == [] and v["portfolio_value"] == "100045.30"
    assert v["unrealized_pnl"] == "0.00"


# --------------------------------------------------
# Eszamanlilik: iki istek ayni anda gelirse
# --------------------------------------------------

def test_11_eszamanli_alislar_bakiyeyi_asamaz(db):
    token, wid, nwid = new_user(db)
    post_quote(SYMBOL, "300.00")
    # Her biri 60.000 TL; ikisi birden 100.000 TL'ye sigmaz
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: trade(wid, token, "buy", 200), range(2)))
    statuses = sorted(r[0] for r in results)
    assert statuses == [201, 409], results
    assert trade_count(db, nwid) == 1
    assert wallet_row(db, nwid)["cash_balance"] == Decimal("40000.00")
    assert position_row(db, nwid)["quantity"] == 200


def test_12_eszamanli_ayni_anahtar_tek_islem(db):
    token, wid, nwid = new_user(db)
    post_quote(SYMBOL, "300.00")
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: trade(wid, token, "buy", 10, key=key), range(3)))
    statuses = sorted(r[0] for r in results)
    assert statuses == [200, 200, 201], results
    assert len({r[1]["trade_id"] for r in results}) == 1
    assert trade_count(db, nwid) == 1
    assert wallet_row(db, nwid)["cash_balance"] == Decimal("97000.00")
