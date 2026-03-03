FROM python:3.11-slim

WORKDIR /app

# (선택) 빌드에 필요한 최소 패키지들만
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run will set $PORT
ENV PORT=8080
EXPOSE 8080

CMD streamlit run home.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT} \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.fileWatcherType=none
