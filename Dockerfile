# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

RUN groupadd -g 10001 traceweaver && \
    useradd -u 10001 -g traceweaver -s /bin/bash -m traceweaver

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/traceweaver /usr/local/bin/traceweaver
COPY --from=builder /app /app

RUN chown -R traceweaver:traceweaver /app

USER traceweaver

EXPOSE 4317 4318 8080

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

ENTRYPOINT ["traceweaver", "serve", "--host", "0.0.0.0", "--web-port", "8080", "--grpc-port", "4317"]
