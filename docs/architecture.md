# Architecture — chasse-logement

> Schéma complet (actuel + modules IA proposés) : [docs/schema.md](schema.md) —
> design des modules IA : [docs/ai-modules.md](ai-modules.md) (IA-1 signaux texte,
> IA-2 dédup sémantique cross-sources) — build vs buy (agrégateurs type MoteurImmo) :
> [docs/schema.md](schema.md) §build-vs-buy.

## 1. Vue d'ensemble

```
┌───────────── sources (légaux) ─────────────┐
│  IMAP : boîte mail dédiée ← alertes natives │  on ne fetch JAMAIS les pages
│           des portails (Leboncoin, SeLoger, │  des portails majeurs
│           PAP, Bien'ici, Logic-Immo)        │
│  RSS : flux publiés par les agences         │
│  (V1) API d'agrégation commerciale          │
│  (V1) HTML ciblé : robots.txt OK + CGU OK   │
└──────────────┬──────────────────────────────┘
               ▼  Listing normalisé (pydantic)
┌──────────────────────────────┐
│ store : SQLite (MVP)         │  dédup par clé (URL normalisée ou hash titre+prix+surface+CP)
│ → V1 : PostgreSQL + PostGIS  │  rétention limitée (RGPD)
└──────────────┬───────────────┘
               ▼
│ matching : filtres durs (budget, surface, pièces, zone CP/ville/rayon, meublé,
│           mots-clés exclus) + score 0-100 (fraîcheur + prix/m² vs marché suivi,
│           enrichi en V1 par la Carte des loyers ANIL)
               ▼
│ notify : digest email (SMTP) et/ou Telegram ; mode digest ou instant
               ▼
   scheduler : `run` (cron) ou `daemon` (boucle, interval_hours, ex. 24 h à 8 h)
```

## 2. Schéma de données — `Listing`

| champ | type | notes |
|---|---|---|
| source_id / source_kind | str / enum | ex. `leboncoin` / `imap_alert` |
| external_id | str | id annonce côté source (guid RSS, Message-ID, URL) |
| url, title, description | str | URL = clé de dédup principale |
| price, charges | float € | total = price + charges pour le filtre budget |
| surface_m2, rooms, bedrooms | float/int | extraits du texte (regex) ou du flux |
| listing_type, furnished | enum/bool | |
| city, postcode, latitude, longitude | str/float | géocodage V1 via GéoPlateforme |
| photos, publisher | list/str | |
| published_at, first_seen_at, last_seen_at | datetime UTC | fraîcheur + rétention |

## 3. Composants (packages)

- `sources/` : un connecteur par type de source, interface commune `Source.collect() -> Iterator[Listing]`.
  - `imap_alerts.py` : lit la boîte dédiée (imaplib), parse sujet/corps/liens des emails
    d'alerte, détecte le portail (From/Subject). **Aucun fetch de page de portail.**
  - `rss.py` : feedparser + client HTTP poli (robots.txt vérifié, rate limit, UA honnête).
  - `parsing.py` : extraction prix / m² / pièces / CP / URLs depuis le texte libre.
- `robots.py` + `http.py` : `RobotsChecker` (cache par hôte) et `PoliteClient`
  (User-Agent honnête, intervalle min par hôte, respect de robots.txt, pas de retry
  agressif). Toute source HTML passe obligatoirement par là.
- `store.py` : SQLite (MVP) — table `listings` (dedup_key PK, JSON, first/last_seen,
  notified). V1 : migration PostgreSQL + PostGIS pour les requêtes géo natives.
- `matching.py` : `Criteria` (YAML) → filtres durs + `score()` 0-100 (base 50 +
  fraîcheur ≤ 20 + prix/m² vs pool ≤ 30) → `MatchResult`.
- `notify.py` : `EmailNotifier` (SMTP, digest HTML+texte) et `TelegramNotifier` (Bot API).
- `pipeline.py` : `run_once()` = collect → save/dédup → evaluate → notify → stats JSON.
- `web/` : UI FastAPI — tableau de bord (`/`), onglet **Biens** (`/biens`, liste triable
  et filtrable, un bien = une ligne avec liens vers chaque source, incohérences
  surlignées, encart « à vérifier », adresse estimée, écoles/commerces, trajet hors
  trafic) et paramétrage (`/parametres`) : critères, sources cochables (portails IMAP +
  flux RSS ajout/suppression + **catalogue régional** appliquable en un clic),
  destinataires email, mode digest/instantané. L'UI écrit `config.yaml` sans jamais
  toucher aux secrets.
- `merge.py` : fusion cross-sources des annonces en `Property` (même bien = une ligne).
- `redflags.py` : encart « à vérifier » (incohérences entre sources, prix/m² anormal,
  formulations d'arnaque).
- `geocoding.py` (GéoPlateforme/IGN), `poi.py` (Overpass/OSM), `routing.py` (OSRM
  free-flow = « hors trafic »), `discover.py` + `sources/catalog.py` (détection de flux
  RSS d'agences + catalogue régional Aix-Marseille).
- `cli.py` : `chasse-logement run --config config.yaml` (cron), `daemon` (boucle),
  `serve` (UI web + planificateur en arrière-plan), `check-robots`.
- `config.py` : YAML non secret (`config.yaml`) + secrets en env (`CL_*`, `.env`).

## 4. Exécution

- **MVP local** : `pip install -e .` ; `cp config.example.yaml config.yaml` ; `.env` ;
  `chasse-logement run --config config.yaml` ; cron système :
  `0 8 * * * cd /chemin && chasse-logement run --config config.yaml >> run.log 2>&1`
- **Docker** : `docker compose up -d` (service `daemon`, volumes `config.yaml` + `data/`).
- **VPS** : même compose sur un VPS 5-10 €/mois. En zone tendue, passer
  `interval_hours: 4` en journée (les bonnes annonces partent en heures).

## 5. Roadmap

| version | contenu |
|---|---|
| MVP (ce PR) | IMAP alertes natives + RSS agences + SQLite + matching + digest email/Telegram + UI web de paramétrage + tests + CI |
| V1 | PostGIS + rayon/polygones, géocodage GéoPlateforme, scoring prix vs Carte des loyers ANIL, connecteur API agrégateur (Melo/MoteurImmo), scraping HTML ciblé de sites d'agences robots-OK, mini UI web (FastAPI) pour gérer critères et marquer vu/contacté |
| V2 | détection de baisses de prix et d'annonces supprimées, dossier de candidature auto (DossierFacile), multi-profils |

## 6. Questions ouvertes

- Budget éventuel pour une API d'agrégation (option C) ?
- Zones exactes et budget : à renseigner dans `config.yaml` → `criteria`.
- Préférence de notification : email uniquement, ou Telegram aussi ?
