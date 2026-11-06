FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .[web]

COPY config.example.yaml ./config.example.yaml
# config par défaut embarquée (ex. région Aix-Marseille). Le CMD vise /app/data/config.yaml :
# sur Clever Cloud (FS Bucket monté en /app/data), la config éditée via l'UI persiste entre
# les redéploiements (bootstrap copiée depuis l'image au 1er boot, voir cli._ensure_config).
COPY regions/aix-marseille.example.yaml ./config.yaml

CMD ["chasse-logement", "serve", "--config", "/app/data/config.yaml"]
