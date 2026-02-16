FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
openai>=1.30.0


COPY . .
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

CMD ["bash", "-lc", "\
set -e; \
streamlit run hotena_basic.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --browser.gatherUsageStats=false \
  --server.fileWatcherType=none & \
exec nginx -g 'daemon off;' \
"]
