FROM python:3.12-slim

WORKDIR /app

# Bagimliliklari ayri katmanda kurarak tekrarlanan build'leri hizlandiriyoruz.
COPY requirements.compose.txt /app/requirements.compose.txt
RUN pip install --no-cache-dir -r /app/requirements.compose.txt

COPY main.py database.py /app/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
