import os
import json
import base64
import binascii
import re
import secrets

from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse
from typing import Literal
from pathlib import Path
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Header, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

load_dotenv(Path(__file__).resolve().parent / ".env")
from database import engine


# ==================================================
# FINANCE EXPERT API
# ==================================================

app = FastAPI(
    title="Finance Expert API",
    description="Finance Expert mobil uygulamasinin REST API servisi",
    version="1.0.0"
)


# ==================================================
# YARDIMCI FONKSIYONLAR
# ==================================================

# MySQL'den gelen UTC tarihlerini JSON formatina cevirir.
def format_datetime(value):
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


# Gelen tarihleri MySQL icin UTC'ye cevirir.
def to_mysql_datetime(value):
    if value is None:
        return None

    return value.astimezone(
        timezone.utc
    ).replace(tzinfo=None)


# Haber listeleme icin sayfalama bilgisi olusturur.
def create_cursor(fetched_at, news_id):
    data = {
        "fetched_at": fetched_at.isoformat(),
        "news_id": news_id
    }

    return base64.urlsafe_b64encode(
        json.dumps(data).encode("utf-8")
    ).decode("utf-8")


# Sayfalama bilgisini cozer.
def decode_cursor(cursor):
    try:
        data = json.loads(
            base64.urlsafe_b64decode(
                cursor.encode("utf-8")
            )
        )

        fetched_at = datetime.fromisoformat(
            data["fetched_at"]
        )

        news_id = data["news_id"]

        if fetched_at.tzinfo is not None:
            raise ValueError()

        if not isinstance(news_id, str) or not news_id:
            raise ValueError()

        return fetched_at, news_id

    except (
        ValueError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        binascii.Error
    ):
        raise HTTPException(
            status_code=400,
            detail="Gecersiz sayfalama bilgisi"
        )


# Servis API anahtarini kontrol eder.
def check_internal_api_key(api_key):
    expected_key = os.getenv("INTERNAL_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Servis kimlik dogrulamasi yapilandirilmamis"
        )

    if not api_key or not secrets.compare_digest(
        api_key,
        expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Gecersiz servis API anahtari"
        )


# Bir habere ait hisse kodlarini getirir.
def get_news_symbols(connection, news_id):
    result = connection.execute(
        text("""
            SELECT symbol
            FROM news_stocks
            WHERE news_id = :news_id
            ORDER BY symbol
        """),
        {
            "news_id": news_id
        }
    )

    return [row[0] for row in result]


# Veritabanindaki haberi ortak JSON formatina cevirir.
def serialize_news(row, symbols):
    keywords = row["matched_keywords"]

    if isinstance(keywords, str):
        keywords = json.loads(keywords)

    return {
        "schema_version": "1.0",
        "news_id": row["news_id"],
        "source": row["source"],
        "source_id": row["source_id"],
        "title": row["title"],
        "summary": row["summary"],
        "url": row["url"],
        "published_at": format_datetime(
            row["published_at"]
        ),
        "fetched_at": format_datetime(
            row["fetched_at"]
        ),
        "symbols": symbols,
        "matched_keywords": keywords,
        "disclosure_type": row["disclosure_type"]
    }


# Veritabanindaki analiz etkilerini JSON'a cevirir.
def get_analysis_impacts(connection, analysis_id):
    rows = connection.execute(
        text("""
            SELECT
                symbol,
                direction,
                confidence,
                reason
            FROM analysis_impacts
            WHERE analysis_id = :analysis_id
            ORDER BY symbol
        """),
        {
            "analysis_id": analysis_id
        }
    ).mappings().all()

    return [
        {
            "symbol": row["symbol"],
            "direction": row["direction"],
            "confidence": float(row["confidence"]),
            "reason": row["reason"]
        }
        for row in rows
    ]


# Analizi GitHub'daki Analysis v1.0 formatina cevirir.
def serialize_analysis(row, impacts):
    return {
        "schema_version": row["schema_version"],
        "analysis_id": row["analysis_id"],
        "news_id": row["news_id"],
        "model": row["model"],
        "prompt_version": row["prompt_version"],
        "created_at": format_datetime(
            row["created_at"]
        ),
        "summary": row["summary"],
        "impacts": impacts
    }


# ==================================================
# HABER VERI MODELI
# ==================================================

class NewsCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]

    news_id: str = Field(
        min_length=1,
        max_length=191
    )

    source: Literal[
        "KAP",
        "BLOOMBERG_HT"
    ]

    source_id: str | None

    title: str = Field(min_length=1)

    summary: str | None

    url: str

    published_at: datetime | None

    fetched_at: datetime

    symbols: list[str]

    matched_keywords: list[str]

    disclosure_type: str | None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value.strip():
            raise ValueError("Haber basligi bos olamaz")

        return value

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        parsed = urlparse(value)

        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Haber adresi HTTPS olmali")

        return value

    @field_validator("published_at", "fetched_at")
    @classmethod
    def validate_datetime(cls, value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Tarih saat dilimi icermeli")

        return value

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, symbols):

        if len(symbols) != len(set(symbols)):
            raise ValueError("Tekrarlanan hisse kodu var")

        for symbol in symbols:
            if not re.fullmatch(r"[A-Z0-9]{1,15}", symbol):
                raise ValueError("Gecersiz hisse kodu")

        return symbols


# ==================================================
# AI ANALIZ VERI MODELLERI
# ==================================================

# Kutay'in AI kodunun urettigi her hisse etkisi.
class AnalysisImpactCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(
        min_length=1,
        max_length=15
    )

    direction: Literal[
        "positive",
        "negative",
        "neutral",
        "uncertain"
    ]

    confidence: float = Field(
        ge=0,
        le=1
    )

    reason: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value):
        if not re.fullmatch(r"[A-Z0-9]{1,15}", value):
            raise ValueError("Gecersiz hisse kodu")

        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value):
        if not value.strip():
            raise ValueError("Analiz gerekcesi bos olamaz")

        return value


# Kutay'in gonderecegi Analysis v1.0 modeli.
class AnalysisCreate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]

    analysis_id: str = Field(
        min_length=1,
        max_length=255
    )

    news_id: str = Field(
        min_length=1,
        max_length=191
    )

    model: str = Field(min_length=1)

    prompt_version: str = Field(min_length=1)

    created_at: datetime

    summary: str = Field(min_length=1)

    impacts: list[AnalysisImpactCreate]

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Tarih saat dilimi icermeli")

        return value

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value):
        if not value.strip():
            raise ValueError("Analiz ozeti bos olamaz")

        return value

    @field_validator("impacts")
    @classmethod
    def validate_impacts(cls, impacts):
        symbols = [
            impact.symbol for impact in impacts
        ]

        if len(symbols) != len(set(symbols)):
            raise ValueError("Tekrarlanan hisse kodu var")

        return impacts


# ==================================================
# SISTEM KONTROL API'LERI
# ==================================================

@app.get("/")
def home():
    return {
        "message": "Finance Expert API calisiyor"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/health/db")
def database_health_check():

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected"
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Veritabani baglantisi kurulamadi"
        )


# ==================================================
# HISSE API'LERI
# ==================================================

@app.get("/api/v1/stocks")
def get_stocks():

    try:
        with engine.connect() as connection:

            result = connection.execute(
                text("""
                    SELECT
                        symbol,
                        company_name,
                        market,
                        is_active
                    FROM stocks
                    ORDER BY symbol
                """)
            )

            stocks = []

            for row in result.mappings():
                stocks.append({
                    "symbol": row["symbol"],
                    "company_name": row["company_name"],
                    "market": row["market"],
                    "is_active": bool(row["is_active"])
                })

        return {
            "stocks": stocks,
            "total": len(stocks)
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Hisse bilgileri alinamiyor"
        )


# ==================================================
# HABER LISTELEME API'SI
# ==================================================

@app.get("/api/v1/news")
def get_news(
    symbol: str | None = None,
    limit: int = Query(
        default=20,
        ge=1,
        le=100
    ),
    cursor: str | None = None
):

    params = {
        "limit": limit + 1,
        "symbol": symbol,
        "cursor_time": None,
        "cursor_id": None
    }

    if cursor:
        cursor_time, cursor_id = decode_cursor(cursor)
        params["cursor_time"] = cursor_time
        params["cursor_id"] = cursor_id

    query = text("""
        SELECT
            n.news_id,
            n.source,
            n.source_id,
            n.title,
            n.summary,
            n.url,
            n.published_at,
            n.fetched_at,
            n.disclosure_type,
            n.matched_keywords
        FROM news n
        WHERE (
            :symbol IS NULL
            OR EXISTS (
                SELECT 1
                FROM news_stocks ns
                WHERE ns.news_id = n.news_id
                AND ns.symbol = :symbol
            )
        )
        AND (
            :cursor_time IS NULL
            OR n.fetched_at < :cursor_time
            OR (
                n.fetched_at = :cursor_time
                AND n.news_id < :cursor_id
            )
        )
        ORDER BY
            n.fetched_at DESC,
            n.news_id DESC
        LIMIT :limit
    """)

    try:
        with engine.connect() as connection:

            rows = connection.execute(
                query,
                params
            ).mappings().all()

            has_more = len(rows) > limit
            selected_rows = rows[:limit]
            news_list = []

            for row in selected_rows:
                symbols = get_news_symbols(
                    connection,
                    row["news_id"]
                )

                news_list.append(
                    serialize_news(row, symbols)
                )

            next_cursor = None

            if has_more and selected_rows:
                last_row = selected_rows[-1]

                next_cursor = create_cursor(
                    last_row["fetched_at"],
                    last_row["news_id"]
                )

        return {
            "schema_version": "1.0",
            "items": news_list,
            "next_cursor": next_cursor
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Haberler su anda alinamiyor"
        )


# ==================================================
# HABER DETAY API'SI
# ==================================================

@app.get("/api/v1/news/{news_id}")
def get_news_detail(news_id: str):

    try:
        with engine.connect() as connection:

            news = connection.execute(
                text("""
                    SELECT
                        news_id,
                        source,
                        source_id,
                        title,
                        summary,
                        url,
                        published_at,
                        fetched_at,
                        disclosure_type,
                        matched_keywords
                    FROM news
                    WHERE news_id = :news_id
                """),
                {
                    "news_id": news_id
                }
            ).mappings().first()

            if news is None:
                raise HTTPException(
                    status_code=404,
                    detail="Haber bulunamadi"
                )

            symbols = get_news_symbols(
                connection,
                news_id
            )

            return serialize_news(news, symbols)

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Haber detaylari su anda alinamiyor"
        )


# ==================================================
# HABER EKLEME API'SI
# ==================================================

@app.post("/api/v1/internal/news")
def create_news(
    news: NewsCreate,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key"
    )
):

    check_internal_api_key(x_api_key)

    try:
        # Haber, hisse iliskileri ve analiz gorevi
        # tek transaction icinde kaydedilir.
        with engine.begin() as connection:

            existing_news = connection.execute(
                text("""
                    SELECT *
                    FROM news
                    WHERE news_id = :news_id
                """),
                {
                    "news_id": news.news_id
                }
            ).mappings().first()

            # Ayni haber ikinci kez kaydedilmez.
            if existing_news:
                symbols = get_news_symbols(
                    connection,
                    news.news_id
                )

                return JSONResponse(
                    status_code=200,
                    content=serialize_news(
                        existing_news,
                        symbols
                    )
                )

            # Hisse kodlarinin aktifligini kontrol et.
            for symbol in news.symbols:
                stock = connection.execute(
                    text("""
                        SELECT symbol
                        FROM stocks
                        WHERE symbol = :symbol
                        AND is_active = TRUE
                    """),
                    {
                        "symbol": symbol
                    }
                ).first()

                if stock is None:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Kayitli veya aktif olmayan "
                            f"hisse: {symbol}"
                        )
                    )

            # Haberi kaydet.
            connection.execute(
                text("""
                    INSERT INTO news (
                        news_id,
                        source,
                        source_id,
                        title,
                        summary,
                        url,
                        published_at,
                        fetched_at,
                        disclosure_type,
                        matched_keywords
                    )
                    VALUES (
                        :news_id,
                        :source,
                        :source_id,
                        :title,
                        :summary,
                        :url,
                        :published_at,
                        :fetched_at,
                        :disclosure_type,
                        :matched_keywords
                    )
                """),
                {
                    "news_id": news.news_id,
                    "source": news.source,
                    "source_id": news.source_id,
                    "title": news.title,
                    "summary": news.summary,
                    "url": news.url,
                    "published_at": to_mysql_datetime(
                        news.published_at
                    ),
                    "fetched_at": to_mysql_datetime(
                        news.fetched_at
                    ),
                    "disclosure_type": news.disclosure_type,
                    "matched_keywords": json.dumps(
                        news.matched_keywords,
                        ensure_ascii=False
                    )
                }
            )

            # Habere ait hisse kodlarini kaydet.
            for symbol in news.symbols:
                connection.execute(
                    text("""
                        INSERT INTO news_stocks (
                            news_id,
                            symbol
                        )
                        VALUES (
                            :news_id,
                            :symbol
                        )
                    """),
                    {
                        "news_id": news.news_id,
                        "symbol": symbol
                    }
                )

            # Otomatik analiz gorevi olustur.
            connection.execute(
                text("""
                    INSERT INTO analysis_jobs (
                        news_id,
                        status,
                        attempts
                    )
                    VALUES (
                        :news_id,
                        'pending',
                        0
                    )
                """),
                {
                    "news_id": news.news_id
                }
            )

        return JSONResponse(
            status_code=201,
            content=news.model_dump(mode="json")
        )

    except HTTPException:
        raise

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Haber kaydi sirasinda kimlik cakismasi olustu"
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Haber kaydedilirken veritabani hatasi olustu"
        )


# ==================================================
# HABER ANALIZ DURUMU API'SI
# ==================================================

@app.get("/api/v1/news/{news_id}/analysis")
def get_news_analysis(news_id: str):

    try:
        with engine.connect() as connection:

            # Haber var mi?
            news_exists = connection.execute(
                text("""
                    SELECT 1
                    FROM news
                    WHERE news_id = :news_id
                """),
                {
                    "news_id": news_id
                }
            ).first()

            if news_exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Haber bulunamadi"
                )

            # Analiz gorevinin durumunu getir.
            job = connection.execute(
                text("""
                    SELECT status
                    FROM analysis_jobs
                    WHERE news_id = :news_id
                """),
                {
                    "news_id": news_id
                }
            ).mappings().first()

            if job is None:
                raise HTTPException(
                    status_code=503,
                    detail="Haberin analiz gorevi bulunamadi"
                )

            status = job["status"]

            # Analiz henuz tamamlanmadiysa.
            if status != "completed":
                return {
                    "schema_version": "1.0",
                    "news_id": news_id,
                    "status": status,
                    "analysis": None
                }

            # Tamamlanan analizi getir.
            analysis = connection.execute(
                text("""
                    SELECT
                        analysis_id,
                        news_id,
                        schema_version,
                        model,
                        prompt_version,
                        created_at,
                        summary
                    FROM analyses
                    WHERE news_id = :news_id
                    ORDER BY
                        created_at DESC,
                        analysis_id DESC
                    LIMIT 1
                """),
                {
                    "news_id": news_id
                }
            ).mappings().first()

            if analysis is None:
                raise HTTPException(
                    status_code=503,
                    detail="Tamamlanan analiz kaydi bulunamadi"
                )

            impacts = get_analysis_impacts(
                connection,
                analysis["analysis_id"]
            )

            return {
                "schema_version": "1.0",
                "news_id": news_id,
                "status": "completed",
                "analysis": serialize_analysis(
                    analysis,
                    impacts
                )
            }

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Analiz bilgileri su anda alinamiyor"
        )


# ==================================================
# AI ANALIZ KAYDETME API'SI
# ==================================================

# Kutay'in AI modulu analiz sonucunu buraya gonderecek.
@app.post("/api/v1/internal/analyses")
def create_analysis(
    analysis: AnalysisCreate,
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key"
    )
):

    # Servis API anahtarini kontrol et.
    check_internal_api_key(x_api_key)

    try:
        # Butun kayitlar ayni transaction icinde.
        with engine.begin() as connection:

            # Haberin analiz gorevini kilitle.
            job = connection.execute(
                text("""
                    SELECT news_id, status
                    FROM analysis_jobs
                    WHERE news_id = :news_id
                    FOR UPDATE
                """),
                {
                    "news_id": analysis.news_id
                }
            ).mappings().first()

            if job is None:
                raise HTTPException(
                    status_code=404,
                    detail="Haber veya analiz gorevi bulunamadi"
                )

            # Bu analiz daha once kaydedilmis mi?
            existing = connection.execute(
                text("""
                    SELECT
                        analysis_id,
                        news_id,
                        schema_version,
                        model,
                        prompt_version,
                        created_at,
                        summary
                    FROM analyses
                    WHERE analysis_id = :analysis_id
                """),
                {
                    "analysis_id": analysis.analysis_id
                }
            ).mappings().first()

            if existing is not None:

                # Kayitli analizin hisse etkilerini al.
                saved_impacts = get_analysis_impacts(
                    connection,
                    analysis.analysis_id
                )

                # Gelen hisse etkilerini ayni siraya koy.
                incoming_impacts = sorted(
                    [
                        {
                            "symbol": impact.symbol,
                            "direction": impact.direction,
                            "confidence": float(
                                impact.confidence
                            ),
                            "reason": impact.reason
                        }
                        for impact in analysis.impacts
                    ],
                    key=lambda item: item["symbol"]
                )

                # Ayni kimlik ayni icerikle mi geldi?
                is_same = (
                    existing["news_id"] == analysis.news_id
                    and existing["schema_version"]
                    == analysis.schema_version
                    and existing["model"] == analysis.model
                    and existing["prompt_version"]
                    == analysis.prompt_version
                    and existing["created_at"]
                    == to_mysql_datetime(analysis.created_at)
                    and existing["summary"] == analysis.summary
                    and saved_impacts == incoming_impacts
                )

                if not is_same:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Ayni analiz kimligi "
                            "farkli veriyle kullanilmis"
                        )
                    )

                return JSONResponse(
                    status_code=200,
                    content=serialize_analysis(
                        existing,
                        saved_impacts
                    )
                )

            # AI yalnizca haberle eslesen hisseleri analiz edebilir.
            news_symbols = set(
                get_news_symbols(
                    connection,
                    analysis.news_id
                )
            )

            for impact in analysis.impacts:
                if impact.symbol not in news_symbols:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Analizde haberle eslesmeyen hisse var: "
                            f"{impact.symbol}"
                        )
                    )

            # Analizi kaydet.
            connection.execute(
                text("""
                    INSERT INTO analyses (
                        analysis_id,
                        news_id,
                        schema_version,
                        model,
                        prompt_version,
                        created_at,
                        summary,
                        disclaimer
                    )
                    VALUES (
                        :analysis_id,
                        :news_id,
                        :schema_version,
                        :model,
                        :prompt_version,
                        :created_at,
                        :summary,
                        NULL
                    )
                """),
                {
                    "analysis_id": analysis.analysis_id,
                    "news_id": analysis.news_id,
                    "schema_version": analysis.schema_version,
                    "model": analysis.model,
                    "prompt_version": analysis.prompt_version,
                    "created_at": to_mysql_datetime(
                        analysis.created_at
                    ),
                    "summary": analysis.summary
                }
            )

            # Hisse etkilerini kaydet.
            for impact in analysis.impacts:
                connection.execute(
                    text("""
                        INSERT INTO analysis_impacts (
                            analysis_id,
                            symbol,
                            direction,
                            confidence,
                            reason
                        )
                        VALUES (
                            :analysis_id,
                            :symbol,
                            :direction,
                            :confidence,
                            :reason
                        )
                    """),
                    {
                        "analysis_id": analysis.analysis_id,
                        "symbol": impact.symbol,
                        "direction": impact.direction,
                        "confidence": impact.confidence,
                        "reason": impact.reason
                    }
                )

            # Analiz gorevini tamamlandi olarak isaretle.
            connection.execute(
                text("""
                    UPDATE analysis_jobs
                    SET
                        status = 'completed',
                        locked_until = NULL,
                        last_error = NULL
                    WHERE news_id = :news_id
                """),
                {
                    "news_id": analysis.news_id
                }
            )

        # Yeni analiz olusturuldu.
        return JSONResponse(
            status_code=201,
            content=analysis.model_dump(mode="json")
        )

    except HTTPException:
        raise

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Analiz kaydinda kimlik cakismasi olustu"
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Analiz kaydedilirken veritabani hatasi olustu"
        )

# ==================================================
# ANALIZ GOREV KUYRUGU API'LERI
# ==================================================

# En fazla 3 kez denemeye izin veriyoruz.
MAX_ANALYSIS_ATTEMPTS = 3


class AnalysisJobFailRequest(BaseModel):
    # AI worker, islemin neden basarisiz oldugunu bildirir.
    model_config = ConfigDict(extra="forbid")
    error: str = Field(min_length=1, max_length=2000)

    @field_validator("error")
    @classmethod
    def validate_error(cls, value):
        if not value.strip():
            raise ValueError("Hata aciklamasi bos olamaz")
        return value


# Bekleyen analiz gorevini atomik sekilde worker'a ayirir.
# InnoDB / MySQL 8: SKIP LOCKED iki worker'in ayni
# gorevi ayni anda almasini engeller.
@app.post("/api/v1/internal/analysis-jobs/claim")
def claim_analysis_job(
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
):
    check_internal_api_key(x_api_key)

    try:
        with engine.begin() as connection:
            # Son deneme suresi de asilan gorevleri basarisiz say.
            connection.execute(
                text("""
                    UPDATE analysis_jobs
                    SET status = 'failed',
                        locked_until = NULL,
                        last_error = 'Analiz gorevi zaman asimina ugradi'
                    WHERE status = 'processing'
                      AND locked_until < UTC_TIMESTAMP(6)
                      AND attempts >= :max_attempts
                """),
                {"max_attempts": MAX_ANALYSIS_ATTEMPTS}
            )

            # Bekleyen veya kilit suresi dolmus gorevleri sec.
            # Biten isler ve maksimum deneme sayisina
            # ulasan isler tekrar verilmez.
            job = connection.execute(
                text("""
                    SELECT news_id, status, attempts
                    FROM analysis_jobs
                    WHERE attempts < :max_attempts
                      AND (
                          status = 'pending'
                          OR (
                              status = 'processing'
                              AND locked_until < UTC_TIMESTAMP(6)
                          )
                      )
                    ORDER BY created_at ASC, news_id ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """),
                {"max_attempts": MAX_ANALYSIS_ATTEMPTS}
            ).mappings().first()

            if job is None:
                # Bekleyen is yok: bu durum hata degil.
                return {"job": None}

            # Gorevi worker'a 15 dakikaligina ayir.
            connection.execute(
                text("""
                    UPDATE analysis_jobs
                    SET status = 'processing',
                        attempts = attempts + 1,
                        locked_until = DATE_ADD(
                            UTC_TIMESTAMP(6), INTERVAL 15 MINUTE
                        ),
                        last_error = NULL
                    WHERE news_id = :news_id
                """),
                {"news_id": job["news_id"]}
            )

            claimed = connection.execute(
                text("""
                    SELECT news_id, status, attempts, locked_until
                    FROM analysis_jobs
                    WHERE news_id = :news_id
                """),
                {"news_id": job["news_id"]}
            ).mappings().one()

            # Daha once yazdigimiz News v1.0 formatinda
            # haber bilgisini de worker'a veriyoruz.
            news = connection.execute(
                text("""
                    SELECT * FROM news WHERE news_id = :news_id
                """),
                {"news_id": job["news_id"]}
            ).mappings().one()
            symbols = get_news_symbols(connection, job["news_id"])

            return {
                "job": {
                    "news_id": claimed["news_id"],
                    "status": claimed["status"],
                    "attempts": claimed["attempts"],
                    "locked_until": format_datetime(
                        claimed["locked_until"]
                    ),
                    "news": serialize_news(news, symbols)
                }
            }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Analiz gorevi alinamiyor"
        )


# Basarisiz AI gorevini yeniden siraya koyar
# veya deneme siniri dolduysa failed yapar.
@app.post("/api/v1/internal/analysis-jobs/{news_id}/fail")
def fail_analysis_job(
    news_id: str,
    payload: AnalysisJobFailRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
):
    check_internal_api_key(x_api_key)

    try:
        with engine.begin() as connection:
            # Durumu degistirirken ayni satiri kilitle.
            job = connection.execute(
                text("""
                    SELECT news_id, status, attempts
                    FROM analysis_jobs
                    WHERE news_id = :news_id
                    FOR UPDATE
                """),
                {"news_id": news_id}
            ).mappings().first()

            if job is None:
                raise HTTPException(
                    status_code=404, detail="Analiz gorevi bulunamadi"
                )

            if job["status"] != "processing":
                raise HTTPException(
                    status_code=409,
                    detail="Sadece processing durumundaki gorev basarisiz bildirilebilir"
                )

            next_status = (
                "failed" if job["attempts"] >= MAX_ANALYSIS_ATTEMPTS
                else "pending"
            )

            connection.execute(
                text("""
                    UPDATE analysis_jobs
                    SET status = :status,
                        last_error = :last_error,
                        locked_until = NULL
                    WHERE news_id = :news_id
                """),
                {
                    "status": next_status,
                    "last_error": payload.error,
                    "news_id": news_id
                }
            )

            return {
                "news_id": news_id,
                "status": next_status,
                "attempts": job["attempts"],
                "max_attempts": MAX_ANALYSIS_ATTEMPTS
            }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Analiz gorevinin hata durumu kaydedilemedi"
        )


# ==================================================
# HISSE FIYATI (QUOTE) API'LERI
# ==================================================

# Fiyat kaynagi olan ekip arkadasimizin gonderecegi veri.
# DECIMAL(18,6) tablo yapisini korumak icin Decimal kullaniyoruz.
class QuoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=15)
    price: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    currency: str = Field(default="TRY", min_length=3, max_length=3)
    as_of: datetime
    provider: str = Field(min_length=1, max_length=100)
    is_delayed: bool = False

    @field_validator("symbol")
    @classmethod
    def check_symbol(cls, value):
        if not re.fullmatch(r"[A-Z0-9]{1,15}", value):
            raise ValueError("Gecersiz hisse kodu")
        return value

    @field_validator("currency")
    @classmethod
    def check_currency(cls, value):
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Para birimi uc buyuk harf olmali")
        return value

    @field_validator("provider")
    @classmethod
    def check_provider(cls, value):
        if not value.strip():
            raise ValueError("Fiyat saglayicisi bos olamaz")
        return value

    @field_validator("as_of")
    @classmethod
    def check_as_of(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Fiyat tarihi saat dilimi icermeli")
        return value


def serialize_quote(row):
    # Price metin doner: ondalik hassasiyeti kaybolmaz.
    return {
        "symbol": row["symbol"],
        "price": str(row["price"]),
        "currency": row["currency"],
        "as_of": format_datetime(row["as_of"]),
        "provider": row["provider"],
        "is_delayed": bool(row["is_delayed"])
    }


# KAP/Muhammed fiyat botundan gelen fiyat kaydini saklar.
@app.post("/api/v1/internal/quotes", status_code=201)
def create_quote(
    quote: QuoteCreate,
    x_api_key: str | None = Header(default=None, alias="X-API-Key")
):
    check_internal_api_key(x_api_key)

    try:
        with engine.begin() as connection:
            # Olmayan veya pasif hisselere fiyat kaydetme.
            stock = connection.execute(
                text("""
                    SELECT symbol FROM stocks
                    WHERE symbol = :symbol AND is_active = TRUE
                """),
                {"symbol": quote.symbol}
            ).first()
            if stock is None:
                raise HTTPException(
                    status_code=422,
                    detail="Hisse kayitli veya aktif degil"
                )

            quote_time = to_mysql_datetime(quote.as_of)

            # Ayni kaynak ve zaman damgasiyla gelen fiyatin tekrarini engelle.
            # Birden fazla worker icin DB unique constraint ayrica onerilir.
            existing = connection.execute(
                text("""
                    SELECT id, symbol, price, currency, as_of,
                           provider, is_delayed
                    FROM quotes
                    WHERE symbol = :symbol
                      AND provider = :provider
                      AND as_of = :as_of
                    ORDER BY id DESC LIMIT 1
                """),
                {
                    "symbol": quote.symbol,
                    "provider": quote.provider,
                    "as_of": quote_time
                }
            ).mappings().first()

            if existing is not None:
                is_same = (
                    Decimal(str(existing["price"])) == quote.price
                    and existing["currency"] == quote.currency
                    and bool(existing["is_delayed"]) == quote.is_delayed
                )
                if not is_same:
                    raise HTTPException(
                        status_code=409,
                        detail="Ayni kaynak ve tarihte farkli fiyat mevcut"
                    )
                return JSONResponse(
                    status_code=200,
                    content=serialize_quote(existing)
                )

            connection.execute(
                text("""
                    INSERT INTO quotes (
                        symbol, price, currency, as_of, provider, is_delayed
                    ) VALUES (
                        :symbol, :price, :currency, :as_of, :provider, :is_delayed
                    )
                """),
                {
                    "symbol": quote.symbol,
                    "price": quote.price,
                    "currency": quote.currency,
                    "as_of": quote_time,
                    "provider": quote.provider,
                    "is_delayed": quote.is_delayed
                }
            )

        return {
            "symbol": quote.symbol,
            "price": str(quote.price),
            "currency": quote.currency,
            "as_of": format_datetime(quote_time),
            "provider": quote.provider,
            "is_delayed": quote.is_delayed
        }

    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Fiyat kaydi cakismasi")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Fiyat kaydedilemedi")


# Android uygulamasina en yeni kayitli fiyat bilgisini verir.
@app.get("/api/v1/stocks/{symbol}/quote")
def get_latest_quote(symbol: str):
    if not re.fullmatch(r"[A-Z0-9]{1,15}", symbol):
        raise HTTPException(status_code=422, detail="Gecersiz hisse kodu")

    try:
        with engine.connect() as connection:
            stock = connection.execute(
                text("SELECT symbol FROM stocks WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).first()
            if stock is None:
                raise HTTPException(status_code=404, detail="Hisse bulunamadi")

            quote = connection.execute(
                text("""
                    SELECT symbol, price, currency, as_of,
                           provider, is_delayed
                    FROM quotes WHERE symbol = :symbol
                    ORDER BY as_of DESC, id DESC LIMIT 1
                """),
                {"symbol": symbol}
            ).mappings().first()

            if quote is None:
                raise HTTPException(status_code=404, detail="Fiyat bulunamadi")
            return serialize_quote(quote)

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Fiyat bilgisi alinamadi")


# ==================================================
# KULLANICI KAYDI, GIRIS VE TOKEN YONETIMI
# ==================================================

password_hasher = PasswordHash.recommended()
bearer_security = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 60


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def check_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Ad soyad en az 2 karakter olmali")
        return value


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


def get_jwt_secret():
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="JWT gizli anahtari eksik veya yetersiz"
        )
    return secret


def make_access_token(user_id: int):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=JWT_EXPIRES_MINUTES),
        "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_security)
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Giris yapmalisiniz")
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]}
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Yanlis token turu")
        user_id_text = payload["sub"]
        if not isinstance(user_id_text, str) or not user_id_text.isdecimal():
            raise InvalidTokenError("Gecersiz kullanici")
        user_id = int(user_id_text)
        if user_id <= 0:
            raise InvalidTokenError("Gecersiz kullanici")
        return user_id
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Gecersiz veya suresi dolmus token")


@app.post("/api/v1/users/register", status_code=201, tags=["Users"])
def register_user(body: UserRegister):
    # Kayit ve ilk sanal cuzdan birlikte tamamlanir veya geri alinir.
    normalized_email = str(body.email).strip().lower()
    hashed = password_hasher.hash(body.password)
    try:
        with engine.begin() as connection:
            user_result = connection.execute(
                text("""
                    INSERT INTO users (full_name, email, password_hash)
                    VALUES (:name, :email, :password_hash)
                """),
                {
                    "name": body.full_name,
                    "email": normalized_email,
                    "password_hash": hashed
                }
            )
            user_id = int(user_result.lastrowid)
            wallet_result = connection.execute(
                text("""
                    INSERT INTO wallets (user_id, currency, cash_balance, realized_pnl)
                    VALUES (:user_id, 'TRY', 100000.00, 0.00)
                """),
                {"user_id": user_id}
            )
            wallet_id = int(wallet_result.lastrowid)
        return {
            "user_id": user_id,
            "full_name": body.full_name,
            "email": normalized_email,
            "wallet_id": wallet_id,
            "currency": "TRY",
            "initial_cash_balance": "100000.00"
        }
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayitli")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Kullanici kaydi su anda tamamlanamiyor")


@app.post("/api/v1/users/login", tags=["Users"])
def login_user(body: UserLogin):
    email = str(body.email).strip().lower()
    try:
        with engine.connect() as connection:
            user = connection.execute(
                text("SELECT id, password_hash FROM users WHERE email = :email"),
                {"email": email}
            ).mappings().first()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Giris servisi kullanilamiyor")

    # Kullanici yoksa da ayrintili hata bilgisi vermiyoruz.
    if user is None or not password_hasher.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="E-posta veya sifre hatali")
    return {
        "access_token": make_access_token(int(user["id"])),
        "token_type": "bearer",
        "expires_in": JWT_EXPIRES_MINUTES * 60
    }


@app.get("/api/v1/users/me", tags=["Users"])
def get_my_profile(user_id: int = Depends(current_user_id)):
    try:
        with engine.connect() as connection:
            profile = connection.execute(
                text("""
                    SELECT u.id, u.full_name, u.email, w.wallet_id
                    FROM users u
                    LEFT JOIN wallets w ON w.user_id = u.id
                    WHERE u.id = :user_id
                """),
                {"user_id": user_id}
            ).mappings().first()
        if profile is None:
            raise HTTPException(status_code=401, detail="Kullanici bulunamadi")
        return dict(profile)
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Profil bilgileri alinamiyor")


# ==================================================
# WALLET V1 - KULLANICININ KENDI CUZDANINI GORMESI
# ==================================================

@app.get("/api/v1/wallets/{wallet_id}", tags=["Wallets"])
def get_wallet(wallet_id: str, user_id: int = Depends(current_user_id)):
    # API kimligi "wallet:1" seklinde metindir; MySQL'de wallet_id BIGINT.
    match = re.fullmatch(r"wallet:([1-9][0-9]*)", wallet_id)
    if match is None:
        raise HTTPException(status_code=400, detail="Gecersiz cuzdan kimligi. Ornek: wallet:1")

    numeric_wallet_id = int(match.group(1))

    try:
        with engine.connect() as connection:
            # Cuzdan sahipligini JWT ile dogrula; baskasinin cuzdani acilamaz.
            wallet = connection.execute(
                text("""
                    SELECT wallet_id, currency, cash_balance, realized_pnl, updated_at
                    FROM wallets
                    WHERE wallet_id = :wallet_id AND user_id = :user_id
                """),
                {"wallet_id": numeric_wallet_id, "user_id": user_id}
            ).mappings().first()

            if wallet is None:
                raise HTTPException(status_code=404, detail="Cuzdan bulunamadi")

            positions = connection.execute(
                text("""
                    SELECT symbol, quantity, average_cost
                    FROM positions
                    WHERE wallet_id = :wallet_id AND quantity > 0
                    ORDER BY symbol
                """),
                {"wallet_id": numeric_wallet_id}
            ).mappings().all()

        return {
            "schema_version": "1.0",
            "wallet_id": f"wallet:{numeric_wallet_id}",
            "currency": wallet["currency"],
            "cash_balance": format(Decimal(str(wallet["cash_balance"])), ".2f"),
            "realized_pnl": format(Decimal(str(wallet["realized_pnl"])), ".2f"),
            "positions": [
                {
                    "symbol": position["symbol"],
                    "quantity": int(position["quantity"]),
                    "average_cost": format(Decimal(str(position["average_cost"])), ".6f")
                }
                for position in positions
            ],
            "updated_at": format_datetime(wallet["updated_at"])
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Cuzdan bilgileri alinamiyor")


# ==================================================
# SANAL ALIM-SATIM API'SI - TRADE V1 (MVP TASLAK)
# Hesap kurallari Sukru'nun nihai onayina tabidir.
# ==================================================

MONEY_STEP = Decimal("0.01")
COST_STEP = Decimal("0.000001")
MAX_QUOTE_AGE_SECONDS = 60


def money_round(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def cost_round(value: Decimal) -> Decimal:
    return value.quantize(COST_STEP, rounding=ROUND_HALF_UP)


class TradeRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    symbol: str = Field(min_length=1, max_length=15)
    side: Literal["buy", "sell"]
    quantity: int = Field(strict=True, gt=0)
    idempotency_key: UUID

    @field_validator("symbol")
    @classmethod
    def validate_trade_symbol(cls, value):
        if not re.fullmatch(r"[A-Z0-9]{1,15}", value):
            raise ValueError("Gecersiz hisse kodu")
        return value


def trade_to_contract(row):
    return {
        "schema_version": "1.0",
        "trade_id": f"trade:{row['trade_id']}",
        "wallet_id": f"wallet:{row['wallet_id']}",
        "symbol": row["symbol"],
        "side": row["side"].lower(),
        "quantity": int(row["quantity"]),
        "idempotency_key": row["idempotency_key"],
        "execution_price": format(Decimal(str(row["price"])), ".6f"),
        "gross_amount": format(Decimal(str(row["total_amount"])), ".2f"),
        "currency": row["currency"],
        "quote_as_of": format_datetime(row["quote_as_of"]),
        "executed_at": format_datetime(row["executed_at"]),
    }


@app.post("/api/v1/wallets/{wallet_id}/trades", tags=["Wallets"], status_code=201)
def execute_virtual_trade(
    wallet_id: str,
    body: TradeRequestCreate,
    user_id: int = Depends(current_user_id),
):
    # Kimlik dogrulama token'dan; istemci fiyat/bakiye gonderemez.
    match = re.fullmatch(r"wallet:([1-9][0-9]*)", wallet_id)
    if match is None:
        raise HTTPException(status_code=400, detail="Gecersiz cuzdan kimligi")
    numeric_wallet_id = int(match.group(1))
    request_key = str(body.idempotency_key)
    side_db = body.side.upper()

    try:
        # Cuzdan kilidi butun islemleri seri hale getirir: bakiye,
        # pozisyon, tekrar anahtari ve trade ayni transaction icindedir.
        with engine.begin() as connection:
            wallet = connection.execute(
                text("""
                    SELECT wallet_id, user_id, currency, cash_balance, realized_pnl
                    FROM wallets
                    WHERE wallet_id = :wid AND user_id = :uid
                    FOR UPDATE
                """),
                {"wid": numeric_wallet_id, "uid": user_id},
            ).mappings().first()
            if wallet is None:
                # Var olmayan ve baskasina ait cuzdan ayni yaniti alir.
                raise HTTPException(status_code=404, detail="Cuzdan bulunamadi")

            # Ayni anahtar / ayni istek tekrarinda onceki trade'i dondur.
            previous = connection.execute(
                text("""
                    SELECT trade_id, wallet_id, symbol, side, quantity,
                           price, total_amount, currency, quote_as_of,
                           executed_at, idempotency_key
                    FROM trades
                    WHERE wallet_id = :wid AND idempotency_key = :key
                    LIMIT 1
                """),
                {"wid": numeric_wallet_id, "key": request_key},
            ).mappings().first()
            if previous is not None:
                same_request = (
                    previous["symbol"] == body.symbol
                    and previous["side"] == side_db
                    and int(previous["quantity"]) == body.quantity
                )
                if not same_request:
                    raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
                return JSONResponse(status_code=200, content=trade_to_contract(previous))

            if wallet["currency"] != "TRY":
                raise HTTPException(status_code=409, detail="VALIDATION_ERROR: Sadece TRY")

            stock = connection.execute(
                text("""
                    SELECT symbol FROM stocks
                    WHERE symbol = :symbol AND is_active = TRUE
                """),
                {"symbol": body.symbol},
            ).first()
            if stock is None:
                raise HTTPException(status_code=400, detail="VALIDATION_ERROR: Gecersiz hisse")

            quote = connection.execute(
                text("""
                    SELECT price, currency, as_of, provider, is_delayed
                    FROM quotes
                    WHERE symbol = :symbol
                    ORDER BY as_of DESC, id DESC
                    LIMIT 1
                """),
                {"symbol": body.symbol},
            ).mappings().first()
            if quote is None:
                raise HTTPException(status_code=409, detail="STALE_QUOTE: Fiyat bulunamadi")

            # Test/mock saglayici bilgileriyle gercek emir gerceklestirme.
            # Yalnizca yetkilendirilmis gercek saglayicilar kabul edilir.
            allowed_providers = {
                name.strip().upper()
                for name in os.getenv("TRADE_ALLOWED_QUOTE_PROVIDERS", "").split(",")
                if name.strip()
            }
            if not allowed_providers or str(quote["provider"]).upper() not in allowed_providers:
                raise HTTPException(status_code=409, detail="STALE_QUOTE: Onayli fiyat saglayicisi yok")

            db_utc_now = connection.execute(
                text("SELECT UTC_TIMESTAMP(6)")
            ).scalar_one().replace(tzinfo=timezone.utc)
            quote_time = quote["as_of"].replace(tzinfo=timezone.utc)
            age_seconds = (db_utc_now - quote_time).total_seconds()
            if bool(quote["is_delayed"]) or not (0 <= age_seconds <= MAX_QUOTE_AGE_SECONDS):
                raise HTTPException(status_code=409, detail="STALE_QUOTE")
            if quote["currency"] != wallet["currency"]:
                raise HTTPException(status_code=409, detail="VALIDATION_ERROR: Para birimi uyusmuyor")

            price = Decimal(str(quote["price"]))
            if not price.is_finite() or price <= 0:
                raise HTTPException(status_code=409, detail="VALIDATION_ERROR: Gecersiz fiyat")
            gross = money_round(price * body.quantity)
            balance = Decimal(str(wallet["cash_balance"]))
            total_realized = Decimal(str(wallet["realized_pnl"]))

            # Birden fazla pozisyon anomalisini gizlemiyoruz.
            positions = connection.execute(
                text("""
                    SELECT position_id, quantity, average_cost
                    FROM positions
                    WHERE wallet_id = :wid AND symbol = :symbol
                    FOR UPDATE
                """),
                {"wid": numeric_wallet_id, "symbol": body.symbol},
            ).mappings().all()
            if len(positions) > 1:
                raise HTTPException(status_code=503, detail="Pozisyon butunlugu hatasi")
            position = positions[0] if positions else None
            old_qty = int(position["quantity"]) if position else 0
            old_avg = Decimal(str(position["average_cost"])) if position else Decimal("0")

            realized = Decimal("0.00")
            if body.side == "buy":
                if balance < gross:
                    raise HTTPException(status_code=409, detail="INSUFFICIENT_FUNDS")
                new_qty = old_qty + body.quantity
                new_avg = cost_round(
                    (old_avg * old_qty + price * body.quantity) / Decimal(new_qty)
                )
                if position:
                    connection.execute(
                        text("""
                            UPDATE positions SET quantity = :qty,
                                average_cost = :avg
                            WHERE position_id = :pid
                        """),
                        {"qty": new_qty, "avg": new_avg, "pid": position["position_id"]},
                    )
                else:
                    connection.execute(
                        text("""
                            INSERT INTO positions (wallet_id, symbol, quantity, average_cost)
                            VALUES (:wid, :symbol, :qty, :avg)
                        """),
                        {"wid": numeric_wallet_id, "symbol": body.symbol,
                         "qty": new_qty, "avg": new_avg},
                    )
                balance = money_round(balance - gross)
            else:
                if old_qty < body.quantity:
                    raise HTTPException(status_code=409, detail="INSUFFICIENT_POSITION")
                realized = money_round(Decimal(body.quantity) * (price - old_avg))
                remain = old_qty - body.quantity
                if remain == 0:
                    connection.execute(
                        text("DELETE FROM positions WHERE position_id = :pid"),
                        {"pid": position["position_id"]},
                    )
                else:
                    connection.execute(
                        text("UPDATE positions SET quantity = :qty WHERE position_id = :pid"),
                        {"qty": remain, "pid": position["position_id"]},
                    )
                balance = money_round(balance + gross)
                total_realized = money_round(total_realized + realized)

            connection.execute(
                text("""
                    UPDATE wallets
                    SET cash_balance = :cash, realized_pnl = :pnl
                    WHERE wallet_id = :wid
                """),
                {"cash": balance, "pnl": total_realized, "wid": numeric_wallet_id},
            )
            result = connection.execute(
                text("""
                    INSERT INTO trades
                      (wallet_id, symbol, side, quantity, price, total_amount,
                       realized_pnl, idempotency_key, currency, quote_as_of)
                    VALUES
                      (:wid, :symbol, :side, :qty, :price, :gross,
                       :realized, :key, :currency, :quote_at)
                """),
                {"wid": numeric_wallet_id, "symbol": body.symbol,
                 "side": side_db, "qty": body.quantity, "price": price,
                 "gross": gross, "realized": realized, "key": request_key,
                 "currency": wallet["currency"],
                 "quote_at": quote["as_of"]},
            )
            saved_trade = connection.execute(
                text("""
                    SELECT trade_id, wallet_id, symbol, side, quantity,
                           price, total_amount, currency, quote_as_of,
                           executed_at, idempotency_key
                    FROM trades WHERE trade_id = :id
                """),
                {"id": int(result.lastrowid)},
            ).mappings().one()
            return JSONResponse(status_code=201, content=trade_to_contract(saved_trade))

    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(status_code=409, detail="VALIDATION_ERROR: Islem kaydi cakismasi")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Sanal islem gerceklestirilemedi")
