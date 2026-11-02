import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


# Veritabani bilgilerimizi .env dosyasindan okuyoruz.
env_path = Path(__file__).with_name(".env")
load_dotenv(env_path)

# MySQL baglanti bilgileri
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


# Eksik ayar olup olmadigini kontrol ediyoruz.
if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    raise RuntimeError("Veritabani baglanti ayarlari eksik!")


# MySQL baglanti adresini olusturuyoruz.
database_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)


# SQLAlchemy baglanti motoru
engine = create_engine(
    database_url,
    pool_pre_ping=True
)


# Veritabani oturumlarini olusturmak icin kullanilacak.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# API endpoint'lerinde veritabani oturumu kullanmamizi saglar.
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()