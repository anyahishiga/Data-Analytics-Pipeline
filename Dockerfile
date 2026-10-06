# =================================================================
# Dockerfile
# Dong goi pipeline thanh 1 image co the chay o BAT KY MAY NAO da
# cai Docker, khong can cai Python/PostgreSQL client thu cong.
# =================================================================
FROM python:3.11-slim

# Thu vien he thong can cho psycopg2 (ket noi PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY sql/ ./sql/

# data/ va logs/ se duoc "mount" tu may that qua docker-compose.yml,
# nhung van tao truoc o day de container tu chay doc lap (docker run)
# cung khong bi loi thieu thu muc.
RUN mkdir -p data/raw data/processed logs

CMD ["python", "src/pipeline.py", "--skip-s3"]
