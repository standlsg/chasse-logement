# Étude de faisabilité — recherche quotidienne de logement (France)

Date : 2026-11. Périmètre : location, France métropolitaine. Objectif : détecter chaque
jour les nouvelles annonces correspondant aux critères de l'utilisateur, sur « toutes les
agences et tous les sites » possibles, et notifier (email/Telegram).

## 1. Verdict

**Faisable, mais le verrou n'est ni technique ni algorithmique : c'est l'accès aux sources
et le cadre juridique.** Aucun portail majeur français n'expose d'API publique de lecture
d'annonces, leurs CGU interdisent l'extraction automatisée, et la jurisprudence récente
sanctionne ce scraping. La stratégie retenue repose donc sur des **canaux légaux** :

1. alertes natives des portails (compte perso) centralisées dans une boîte mail dédiée,
2. flux RSS publiés volontairement par les sites d'agences,
3. (option) API commerciale d'agrégation,
4. scraping HTML ciblé uniquement sur des sites dont robots.txt/CGU l'autorisent, avec
   robots.txt respecté, cadence lente, User-Agent honnête, et **jamais** de contournement
   de CAPTCHA/authentification/blocage IP.

## 2. Inventaire des sources (état 2025-2026)

| Source | Accès | Légalité | Notes |
|---|---|---|---|
| Leboncoin « Mes recherches » (≤ 50 recherches, alerte email/app) | compte perso → email | ✅ | 83 M d'annonces ; pas d'API publique ; CGU interdisent les robots |
| SeLoger, Logic-Immo, Bien'ici, PAP : alertes email de recherches sauvegardées | compte perso → email | ✅ | Cadence non maîtrisée, pas de dédup croisée |
| Jinka | app, alertes temps réel, 5 000+ sites annoncés, dédup, anti-arnaque | ✅ côté utilisateur | Gratuit + premium. **Condamnations en appel** (CA Versailles, déc. 2025) pour extraction d'annonces SeLoger/Logic-Immo → périmètre évolutif, ne pas en faire la seule source |
| API d'agrégation commerciales : Melo/Stream Estate (~1 500 sources, webhooks), MoteurImmo (~97 % des annonces), Yanport, API-Immobiliere.fr | API REST payante | ✅ contrat | Option « clé en main » ; coût à chiffrer avant engagement |
| Flux RSS des agences (très nombreux sites d'agences en publient) | RSS/Atom public | ✅ si publié | Couvre « toutes les agences » d'une zone sans scraping |
| Open data data.gouv.fr | fichiers/API gratuits | ✅ | Agrégé/historique, pas de nouveautés en temps réel : « Carte des loyers » ANIL 2025 (9,1 M d'annonces leboncoin + SeLoger, 2019-2025, indicateurs par commune), Observatoires locaux des loyers, DVF+ (prix de vente notariés). Sert à **scorer le prix d'une annonce vs le marché local** |
| API Géo (`geo.api.gouv.fr`), géocodage GéoPlateforme (`data.geopf.fr/geocodage`, ex `api-adresse.data.gouv.fr`, 50 req/s, sans clé) | API gratuites | ✅ | Résolution des zones de recherche (communes, CP, rayon autour d'un point) |
| Facebook Marketplace, groupes WhatsApp/Facebook | aucun | ❌ | Pas d'API utilisable légalement ; surveillance manuelle uniquement |

## 3. Cadre juridique (France/UE, 2025-2026)

- **Droit sui generis du producteur de base de données** (CPI art. L341-1 à L343-4,
  directive 96/9/CE) : extraction/réutilisation d'une partie substantielle d'une base
  protégée = illicite. **Cass. civ. 1re, 15 oct. 2025, n° 23-23.167 (aff. La Centrale)** :
  le scraping peut être sanctionné sur ce fondement, la finalité commerciale ou non étant
  indifférente. Sanction pénale possible (art. L343-4 : 3 ans / 300 000 €).
- **CGU** : contrat d'adhésion opposable (TJ Paris, 21 fév. 2025). Leboncoin, SeLoger, PAP,
  Logic-Immo, Bien'ici interdisent explicitement l'extraction automatisée.
- **Contournement de mesures techniques de protection** (CAPTCHA, blocage IP, auth) :
  **pénal** — accès frauduleux à un STAD (C. pén. art. 323-1 : 2 ans / 60 000 €) ;
  collecte de données personnelles par moyen frauduleux/déloyal (art. 226-18 : 5 ans /
  300 000 €) ; directive 2001/29/CE art. 6 (UE).
- **RGPD / CNIL** : les annonces contiennent des données personnelles d'annonceurs
  (nom, tél., email). Fiche focus CNIL juin 2025 sur le moissonnage : base légale
  « intérêt légitime » possible uniquement avec garanties strictes (minimisation,
  pseudonymisation, respect impératif de robots.txt, pas de contournement de blocage).
  Sanction Clearview AI : 20 M€ (oct. 2022).
- **Directive DSM 2019/790** : text-and-data mining — art. 3 (recherche non commerciale,
  sans opt-out) et art. 4 (opt-out possible pour le reste, signalable via robots.txt/CGU).
- **robots.txt** : convention technique, non pénalement contraignante en soi en droit
  français, mais son non-respect est retenu comme élément de déloyauté et la CNIL exige
  de le respecter.

**Ligne rouge du projet** : on ne scrappe aucun portail majeur ; on ne contourne aucune
protection technique ; on respecte robots.txt et la cadence demandée ; on minimise les
données personnelles stockées (RGPD).

## 4. Options produit

| Option | Effort | Coût | Couverture | Risque juridique | Recommandation |
|---|---|---|---|---|---|
| A. Alertes natives seules (manuelles ou via boîte dédiée) | nul | 0 | portails majeurs uniquement | nul | ✅ base, toujours activer |
| B. Jinka (ou équivalent) | nul | 0 à ~10 €/mois | très large, temps réel | nul côté utilisateur (périmètre côté éditeur) | ✅ complémentaire, pas unique |
| C. API d'agrégation payante | faible | à chiffrer (tarifs pros) | ~97 % du marché | nul | ⚠️ évaluer le budget ; bon complément V1 |
| D. **Self-hosted multi-sources (ce projet)** : IMAP + RSS + (API) + HTML ciblé | moyen | hébergement 5-10 €/mois | portails (via alertes) + agences RSS + zones ciblées | faible si règles de conformité suivies | ✅ **recommandé** |

## 5. Recommandation

Déployer l'**option D** en MVP (IMAP des alertes natives + RSS agences + matching +
notification quotidienne), avec Jinka en parallèle côté téléphone, et évaluer l'option C
en V1 si la couverture des agences reste insuffisante. Voir `architecture.md` pour le
détail et `conformite.md` pour les règles impératives.
