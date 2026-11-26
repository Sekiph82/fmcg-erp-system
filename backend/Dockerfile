FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# M50.S01.T010: SAML (xmlsec), Parquet (pyarrow) and OCR (rapidocr + onnxruntime) are pip wheels only; fail the build if one does not load
RUN python -c "import xmlsec, pyarrow, rapidocr, onnxruntime; from onelogin.saml2.auth import OneLogin_Saml2_Auth"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" --workers ${WEB_CONCURRENCY:-2} --timeout 120"]
