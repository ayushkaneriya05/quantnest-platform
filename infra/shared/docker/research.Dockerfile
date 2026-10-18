FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/quantnest
COPY research_service/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock
COPY research_service/ /opt/quantnest/research_service/
RUN useradd --system --uid 10001 quantnest
USER quantnest
CMD ["uvicorn","research_service.main:app","--host","0.0.0.0","--port","8001","--workers","1","--no-access-log"]
