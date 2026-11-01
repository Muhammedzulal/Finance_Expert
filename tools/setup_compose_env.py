"""Finance Expert Docker Compose icin yerel gizli ayarlari olusturur.

Asla var olan .env.compose veya backend/.env dosyasini ezmez.
"""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env.compose"
if path.exists():
    print(".env.compose zaten mevcut. Uzerine yazilmadi.")
else:
    lines = [
        "# Finance Expert - Docker Compose test ortami. Git'e eklemeyin.",
        "DB_USER=finance_dev",
        "DB_PASSWORD=" + secrets.token_urlsafe(32),
        "MYSQL_ROOT_PASSWORD=" + secrets.token_urlsafe(32),
        "JWT_SECRET_KEY=" + secrets.token_urlsafe(48),
        "INTERNAL_API_KEY=" + secrets.token_urlsafe(32),
        "HOST_BACKEND_PORT=8001",
        "HOST_MYSQL_PORT=3308",
        "# Sadece guvenilir gercek veri saglayicilari burada tanimlanmali.",
        "TRADE_ALLOWED_QUOTE_PROVIDERS=",
    ]
    with path.open("x", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(".env.compose olusturuldu. Sifreler terminale yazdirilmadi.")
print("backend/.env ve eski MySQL konteyneri degistirilmedi.")
