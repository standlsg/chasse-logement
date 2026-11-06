# chasse-logement

Recherche **quotidienne et automatisée** de logement en France, sur toutes les sources
accessibles légalement : alertes natives des portails (Leboncoin, SeLoger, PAP, Bien'ici,
Logic-Immo) centralisées dans une boîte mail dédiée, flux RSS des agences immobilières,
et en V1 une API d'agrégation commerciale. Matching sur tes critères + notification
email/Telegram.

> ⚠️ **Conformité** : ce projet ne scrappe aucun portail majeur (CGU + droit sui generis,
> Cass. civ. 1re, 15 oct. 2025) et ne contourne jamais aucune protection technique.
> Il respecte robots.txt, utilise un User-Agent honnête et une cadence lente.
> Voir [docs/conformite.md](docs/conformite.md).

## Documentation

- [docs/etude-faisabilite.md](docs/etude-faisabilite.md) — sources accessibles, cadre juridique, options, verdict
- [docs/architecture.md](docs/architecture.md) — schéma, composants, roadmap MVP → V1
- [docs/conformite.md](docs/conformite.md) — règles impératives (robots.txt, CGU, RGPD, anti-contournement)
- [docs/sources.md](docs/sources.md) — registre des sources et de leur base juridique

## Prérequis

- Python ≥ 3.11
- Une **adresse mail dédiée** (ex. `alertes-logement@…`) sur laquelle tu actives les
  alertes email de tes recherches sauvegardées sur chaque portail
- (Optionnel) les flux RSS des agences de tes zones

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
```

## Configuration

```bash
cp config.example.yaml config.yaml   # éditer : zones, budget, sources, notifications
cp .env.example .env                 # secrets uniquement (CL_IMAP_PASSWORD, CL_SMTP_PASSWORD, ...)
```

Sur chaque portail : sauvegarde ta recherche avec les bons critères, puis active
l'alerte **email** vers la boîte dédiée.

## Utilisation

```bash
# une tournée unique (à planifier avec cron, ex. tous les jours à 8h) :
chasse-logement run --config config.yaml

# ou en boucle :
chasse-logement daemon --config config.yaml

# vérifier robots.txt avant d'ajouter une source HTML :
chasse-logement check-robots https://www.agence-x.fr/annonces --user-agent "chasse-logement/0.1"
```

Cron (tous les jours à 8 h) :

```
0 8 * * * cd /chemin/vers/chasse-logement && .venv/bin/chasse-logement run --config config.yaml >> run.log 2>&1
```

Docker :

```bash
cp config.example.yaml config.yaml && cp .env.example .env
# éditer config.yaml et .env, puis :
docker compose up -d --build
```

## Tests & lint

```bash
pytest -q
ruff check .
ruff format --check .
```

## Roadmap

MVP (ce dépôt) : IMAP + RSS + matching + digest. V1 : PostGIS, géocodage, scoring prix
vs marché (Carte des loyers ANIL), API d'agrégation, UI web. Détails dans
[docs/architecture.md](docs/architecture.md).
