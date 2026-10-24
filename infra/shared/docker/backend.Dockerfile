FROM python:3.12-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --prefix=/install --require-hashes -r /tmp/requirements.lock

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /opt/quantnest
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY backend/ /opt/quantnest/backend/
RUN useradd --system --uid 10001 quantnest && mkdir -p /var/lib/quantnest/runtime /var/lib/quantnest/scheduler /opt/quantnest/backend/media /opt/quantnest/backend/staticfiles /opt/quantnest/backend/logs && chown -R quantnest:quantnest /var/lib/quantnest /opt/quantnest/backend/media /opt/quantnest/backend/staticfiles /opt/quantnest/backend/logs
USER quantnest
WORKDIR /opt/quantnest/backend
CMD ["uvicorn","backend.asgi:application","--host","0.0.0.0","--port","8000","--no-proxy-headers","--no-access-log"]
