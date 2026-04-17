FROM python:3.10-slim AS builder

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.10-slim

RUN useradd -m -u 1000 cassandra

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /home/cassandra/app
COPY ./CaSSAndRA .

# Data volume (maps, config, logs, measurements)
VOLUME ["/data"]

EXPOSE 8050

USER cassandra

ENTRYPOINT ["python", "app.py", "--data_path", "/data", "--init"]
