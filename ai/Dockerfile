FROM python:3.12-slim

WORKDIR /app

COPY ai/requirements.compose.txt /app/ai-requirements.txt
RUN pip install --no-cache-dir -r /app/ai-requirements.txt

# Mevcut Kutay kodu ile mevcut Berke JSON sozlesmelerini kullaniyor.
COPY ai/ /app/ai/
COPY contracts/ /app/contracts/

CMD ["python", "/app/ai/start_worker_container.py"]
