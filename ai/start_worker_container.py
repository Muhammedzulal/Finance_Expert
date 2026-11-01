"""Docker icinde Ollama modelinin hazir olmasini bekleyip mevcut worker'i baslatir.

Bu dosya Kutay'in analiz.py / worker.py koduna dokunmaz.
Model indirilmeden haberleri 'failed' durumuna dusurmemek icin bekler.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("AI_MODEL", "qwen3.5:4b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")


def model_hazir_mi():
    try:
        with urllib.request.urlopen(OLLAMA_HOST + "/api/tags", timeout=5) as cevap:
            veriler = json.load(cevap)
        adlar = {m.get("name") or m.get("model") for m in veriler.get("models", [])}
        return MODEL in adlar
    except (OSError, ValueError, KeyError):
        return False


def main():
    while not model_hazir_mi():
        print(
            f"Ollama modeli henuz hazir degil: {MODEL}. "
            "Kurulum: docker compose --env-file .env.compose exec ollama "
            f"ollama pull {MODEL}",
            flush=True,
        )
        time.sleep(20)

    print(f"Ollama modeli hazir: {MODEL}. AI worker basliyor.", flush=True)
    raise SystemExit(subprocess.call([sys.executable, "/app/ai/worker.py"]))


if __name__ == "__main__":
    main()
