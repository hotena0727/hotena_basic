FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run will set $PORT. Default to 8080 if not set.
EXPOSE 8080

CMD ["bash", "-lc", "streamlit run home.py --server.address=0.0.0.0 --server.port=${PORT:-8080} --server.headless=true --browser.gatherUsageStats=false --server.fileWatcherType=none"]
