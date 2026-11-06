FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .[web]

COPY config.example.yaml ./config.example.yaml

CMD ["chasse-logement", "run", "--config", "/app/config.yaml"]
