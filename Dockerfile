FROM python:3.12-slim

ARG SERVICO
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY ${SERVICO}/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY comum ./comum
COPY ${SERVICO} ./${SERVICO}

CMD ["sh", "-c", "python ${SERVICO}/app.py"]