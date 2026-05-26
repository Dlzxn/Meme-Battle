FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /tmp && chmod 1777 /tmp

COPY requirements.txt .
RUN mkdir -p /app/tmp && TMPDIR=/app/tmp pip install --no-cache-dir -r requirements.txt && rm -rf /app/tmp

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
