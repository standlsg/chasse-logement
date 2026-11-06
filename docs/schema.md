# Schéma de fonctionnement — chasse-logement (actuel + modules IA proposés)

```mermaid
flowchart LR
  subgraph SOURCES["Sources légales"]
    IMAP["IMAP — boîte mail dédiée<br/>alertes natives Leboncoin / SeLoger / PAP<br/>Bien'ici / Logic-Immo / Gens de Confiance / Appartager"]
    RSS["RSS agences locales<br/>(détectés via `discover`)"]
    API["API agrégateur (option V1)<br/>Melo/Stream Estate, MoteurImmo…"]
  end

  SOURCES --> COLLECT["Collecte « polite »<br/>robots.txt vérifié, rate-limit par hôte,<br/>User-Agent honnête, jamais de contournement"]
  COLLECT --> STORE[("SQLite — data/chasse-logement.db<br/>sur FS Bucket persistant (Clever Cloud)<br/>dédup par URL/hash + rétention 90 j")]
  STORE --> DEDUP["Dédup cross-sources → Property<br/>heuristique (CP + prix + surface + titre)<br/>+ IA-2 (comparaison sémantique + inférence)"]
  DEDUP --> PROP["Property = bien fusionné<br/>champs canoniques (médiane) + sources[]"]
  PROP --> AI1["IA-1 : extraction de signaux texte<br/>« bureau à la cave » → has_office=true<br/>jardin / terrasse m² / nb parkings / dispo / DPE…<br/>(PII redactés avant envoi)"]
  PROP --> MATCH["Matching : filtres durs (budget, pièces,<br/>CP/rayon, meublé, exclusions) + score 0-100<br/>+ bonus signaux IA-1"]
  AI1 --> MATCH
  MATCH --> FLAGS["Red flags « à vérifier »<br/>incohérences entre sources, prix/m² anormal,<br/>formulations d'arnaque"]
  PROP --> GEO["Enrichissements géo<br/>adresse estimée (GéoPlateforme/IGN)<br/>écoles/commerces (Overpass/OSM)<br/>trajet hors trafic (OSRM) → Salesforce Marseille"]
  FLAGS --> UI["UI web (FastAPI)<br/>/ tableau de bord · /biens triable/filtrable<br/>liens multi-sources · encarts · /parametres"]
  GEO --> UI
  MATCH --> NOTIF["Notification — nouveaux biens uniquement<br/>digest email (Resend/SMTP) ou Telegram"]
  UI --> RUN["bouton « Lancer une tournée »"]
  SCHED["`serve` : boucle interne (interval_hours=24)<br/>ou cron `run`"] --> COLLECT
  NOTIF --> MAIL[("Boîtes mail des destinataires<br/>(paramétrées dans /parametres)")]
```

Version ASCII (actuelle, sans IA) : voir `docs/architecture.md` §1.

## Flux d'une tournée quotidienne (`run_once`)

1. **Collecte** : chaque source produit des `Listing` normalisés (titre, prix, m², pièces, CP, URL, date).
2. **Stockage + dédup** : `ListingStore.save` (clé = URL normalisée ou hash), puis re-clustering en `Property`.
3. **IA-1 (proposé)** : extraction de signaux depuis le texte libre → `Property.signals`.
4. **Matching** : filtres durs + score ; les signaux IA enrichissent pièces effectives (bureau) et le score.
5. **IA-2 (proposé)** : pour les paires ambiguës, comparaison sémantique cross-sources + inférence des champs canoniques.
6. **Red flags** : incohérences entre sources + heuristiques arnaque + prix/m² anormal.
7. **Enrichissements géo** : adresse (IGN), POI (OSM), trajet hors trafic (OSRM) — mis en cache.
8. **Notification** : uniquement les **nouveaux** biens matchés → digest email/Telegram.
9. **UI** : onglet Biens (triable/filtrable, dépliable par bien).

## Build vs buy — agrégateurs existants (MoteurImmo, Melo/Stream Estate, Yanport…)

| Besoin | Agrégateur API (payant) | Notre pipeline |
|---|---|---|
| Agrégation multi-portails + dédup de base | ✅ (flux officiels) | ✅ via alertes email gratuites |
| Alertes temps réel (webhooks) | ✅ | ~quotidien (ou interval_hours plus court) |
| Données structurées fiables | ✅ | ~parsed (regex) + IA-1/IA-2 |
| **Signaux texte perso** (bureau à la cave, jardin, parking…) | ❌ | ✅ IA-1 (différenciant) |
| **Incohérences cross-sources mises en évidence** | ❌ | ✅ (différenciant) |
| Red flags arnaques / prix anormal | ❌ | ✅ |
| Trajet hors trafic → Salesforce Marseille, écoles/commerces à proximité | ❌ | ✅ |
| UI perso (tri, filtres, liens multi-sources) | ❌ | ✅ |
| Coût | souvent centaines d'€/mois (tarifs pros) | ~5-10 €/mois d'hébergement + coûts IA faibles |

**Verdict** : hybride. On garde notre collecte gratuite (alertes natives) ; le connecteur
`api` (déjà prévu dans la config) permet d'ajouter **une** API d'agrégation en source
supplémentaire si le budget le permet. Les deux modules IA sont notre vraie valeur ajoutée
et n'existent pas clé en main → on les développe nous-mêmes. Voir `docs/ai-modules.md`.
