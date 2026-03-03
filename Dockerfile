FROM python:3.11-slim

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App copy
COPY . .

# Cloud Run uses this port
ENV PORT=8080
EXPOSE 8080

# Run Streamlit directly (no nginx, no supervisor)
CMD streamlit run home.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT} \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.fileWatcherType=none
