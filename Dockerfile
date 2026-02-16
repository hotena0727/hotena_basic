FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# nginx 설치
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

# ✅ 루트 정적 파일 폴더 준비 (iOS 대응)
RUN mkdir -p /app/static_root && \
    cp -f static/apple-touch-icon.png /app/static_root/apple-touch-icon.png && \
    cp -f static/icon-192.png /app/static_root/icon-192.png && \
    cp -f static/icon-512.png /app/static_root/icon-512.png && \
    cp -f static/manifest.json /app/static_root/manifest.json || true

# nginx 설정 복사
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

# ✅ Streamlit은 내부 8501로, nginx는 8080으로
CMD ["bash", "-lc", "streamlit run hotena_basic.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false & nginx -g 'daemon off;'"]
