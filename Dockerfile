FROM python:3.11-slim

WORKDIR /app

# --- System deps for Nginx + supervisor + envsubst ---
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx supervisor gettext-base \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Nginx config template + supervisor
RUN rm -f /etc/nginx/conf.d/default.conf
COPY deploy/nginx.default.conf.template /etc/nginx/conf.d/default.conf.template
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Cloud Run will set $PORT. Default to 8080 if not set.
ENV PORT=8080
EXPOSE 8080

CMD ["/bin/bash","-lc","/app/deploy/entrypoint.sh"]
