FROM python:3.11-slim

WORKDIR /app

# Gerekli sistem kütüphaneleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["python3", "web_server.py", "8080"]
