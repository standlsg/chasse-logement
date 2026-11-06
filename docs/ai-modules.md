# Modules IA — implémentés (provider Mistral API)

✅ Implémentés sur `preprod` : `src/chasse_logement/ai/` (`redact.py`, `signals.py`,
`dedup.py`, `assess.py`), config `ai:` (provider `off` par défaut), cache `ai_cache`, UI
(encart « 🤖 Signaux IA » dans /biens), tests mockés. Branchement pipeline : IA-1 sur les
nouveaux biens, IA-2 via `decider` sur les paires ambiguës uniquement, **IA-3** (`assess.py`) :
risque d'arnaque 0..1 + cohérence cross-sources → red flags « IA: … ».

✅ Connecteur **API MoteurImmo** : `src/chasse_logement/sources/api.py` (config
`sources.api`, générique/configurable), branché comme source dans le pipeline.

Deux modules, plug-ins du pipeline existant (voir `docs/schema.md`). Point commun :
**jamais de données personnelles d'annonceurs envoyées telles quelles** — les textes sont
nettoyés (regex tél/email/nom) avant tout appel externe ; option modèle local pour zéro
fuite (voir « Confidentialité »).

## IA-1 — Extraction de signaux depuis le texte libre (`ai/signals.py`)

Objectif : remonter ce que les champs structurés ne disent pas.
Exemple : « bureau aménagé à la cave » → `has_office: true`, alors que `rooms` ne le compte pas.

- **Entrée** : `Property.title + description` (+ descriptions par source).
- **Sortie** : JSON strict (schéma) :
  ```json
  {
    "has_office": true, "office_location": "cave",
    "has_garden": true, "garden_m2": 300,
    "terrace_m2": 25, "parking_places": 2,
    "furnished": true, "charges_included": false,
    "available_from": "2026-11-14", "dpe": "C",
    "pets_allowed": null, "smoking_allowed": null,
    "evidence": ["bureau aménagé à la cave", "jardin clos de 300 m²"]
  }
  ```
- **Branchement** : après `build_property`, avant `matching`. Les signaux enrichissent
  `Property.signals` ; effets : `rooms_effective = rooms + (1 if has_office)` pour le filtre
  « 3 chambres + bureau », bonus de score pour jardin/terrasse/parking, affichage dans
  l'onglet Biens.
- **Provider** (config `ai.provider`) :
  - `mistral` : API Mistral (`mistral-small-latest`, `response_format=json_object`),
    ~0,20 €/M tokens → quelques centimes par tournée pour ~50 nouveaux biens.
  - `ollama` : modèle local sur le VPS (ex. `mistral:7b`) — zéro fuite, zéro coût API,
    plus lent (OK en batch nocturne).
  - `off` : désactivé (défaut MVP).
- **Coût/garde-fous** : uniquement sur les **nouveaux** biens ; cache par hash de texte ;
  timeout + retry ; si l'IA échoue → signaux vides, le reste du pipeline continue.

## IA-2 — Dédup sémantique cross-sources + inférence (`ai/dedup.py`)

Objectif : remplacer/affiner `merge.cluster` (heuristique CP+prix+surface+titre).

- **Entrée** : paires de `Listing` du même bucket CP (candidats), ou un `Listing` vs un
  `Property` existant.
- **Sortie** : `{same_property: bool, confidence: 0..1, inferred: {price, surface_m2, rooms,
  address, city}}` — l'adresse inférée sert ensuite au géocodage (adresse plus précise).
- **Stratégie économique** : l'heuristique reste en premier filtre ; l'IA n'est appelée que
  pour les paires **ambiguës** (score heuristique entre 0,3 et 0,7) → très peu d'appels.
  Complément non-IA : hash perceptuel des photos (dedup visuel) si URLs photos dispos.
- **Provider** : idem IA-1 (`ai.provider`), mêmes règles de confidentialité.

## Confidentialité (RGPD)

- **Redaction avant envoi** : `ai/redact.py` — regex tél FR (`0[1-9]…`), emails, et
  suppression des lignes « contact : … ». Seul le texte restant part vers l'API.
- **Mistral API** : DPA dispo ; données traitées UE. Alternative `ollama` local = aucune
  donnée ne sort du VPS.
- **Journalisation** : on ne logue jamais le texte envoyé à l'IA.

## Config (exemple)

```yaml
ai:
  provider: mistral        # mistral | ollama | off
  mistral_api_key: ""      # CL_MISTRAL_API_KEY
  mistral_model: mistral-small-latest
  ollama_url: http://127.0.0.1:11434
  ollama_model: mistral:7b
  run_signals: true        # IA-1
  run_dedup: true          # IA-2 (paires ambiguës uniquement)
```

## Activation

```yaml
ai:
  provider: mistral        # off | mistral
  model: mistral-small-latest
  run_signals: true
  run_dedup: true
  max_pairs_per_run: 50
```

Secret : `CL_MISTRAL_API_KEY` (console Mistral → API keys). Coût indicatif :
`mistral-small-latest` ~0,20 €/M tokens → quelques centimes par tournée pour ~50
nouveaux biens (cache `ai_cache` inclus).

## Évolution prévue

- provider `ollama` (modèle local sur le VPS, zéro fuite) en V2 — l'abstraction
  `MistralClient.complete_json` est prête à être complétée.
- score bonus pour jardin/terrasse/parking détectés par IA-1.
