# Conformité — règles impératives du projet

Ce projet collecte des annonces publiées par des tiers, dont certaines comportent des
données personnelles (nom, téléphone, email d'annonceurs). Règles non négociables :

## 1. Ce qu'on ne fait JAMAIS

- ❌ Scraper Leboncoin, SeLoger, PAP, Logic-Immo, Bien'ici (CGU + droit sui generis,
  Cass. civ. 1re, 15 oct. 2025, aff. La Centrale).
- ❌ Contourner un CAPTCHA, une authentification, un blocage IP, un rate-limit actif
  (pénal : C. pén. art. 323-1 et 226-18 ; directive 2001/29/CE art. 6).
- ❌ Utiliser des proxies rotatifs, de faux comptes, un UA trompeur.
- ❌ Stocker les données personnelles des annonceurs au-delà du strict nécessaire
  (téléphone, email, nom) — on garde titre/prix/surface/zone/URL/description courte.

## 2. Ce qu'on fait systématiquement

- ✅ Lire uniquement les **emails d'alerte reçus dans la boîte dédiée** (ton propre
  compte portail) : légal, couvre tous les portails majeurs sans toucher à leurs pages.
- ✅ Lire les **flux RSS/Atom volontairement publiés** par les agences.
- ✅ Avant tout fetch HTTP : vérifier **robots.txt** (`RobotsChecker`) et respecter le
  `Crawl-delay` ; UA honnête (`chasse-logement/0.1 (+contact)`) ; rate limit par hôte
  (`min_interval_s`) ; un seul thread.
- ✅ Pour toute nouvelle source HTML : remplir la **grille d'entrée** ci-dessous avant
  d'activer le connecteur.
- ✅ RGPD : minimisation, rétention limitée (purge auto des annonces > 90 jours en V1),
  pas de logs avec PII, secrets uniquement en variables d'environnement (`.env`,
  gitigné), dépôt GitHub **privé** recommandé.
- ✅ Tenir un registre des sources dans `docs/sources.md` (URL, type d'accès, base
  juridique, date de vérification CGU/robots.txt).

## 3. Grille d'entrée d'une nouvelle source

| question | si réponse | action |
|---|---|---|
| La source publie-t-elle un flux RSS/Atom/API publique documentée ? | oui | connecteur RSS/API, aucun scraping |
| robots.txt autorise-t-il notre UA sur les pages concernées ? | non | ❌ ne pas fetcher |
| Les CGU interdisent-elles l'extraction automatisée ? | oui | ❌ ne pas fetcher (sauf flux public prévu à cet effet) |
| La page est-elle protégée par CAPTCHA/auth ? | oui | ❌ ne jamais contourner |
| Des données personnelles d'annonceurs sont-elles exposées ? | oui | minimiser (ne pas stocker tél./email/nom) |

## 4. Références

- CPI art. L341-1 à L343-4 (droit sui generis) ; Cass. civ. 1re, 15 oct. 2025, n° 23-23.167.
- C. pén. art. 323-1 à 323-8 (accès frauduleux à un STAD) ; art. 226-18 (collecte de
  données personnelles par moyen frauduleux).
- Directive (UE) 2019/790 art. 3 et 4 (text-and-data mining, opt-out).
- CNIL, fiche focus « intérêt légitime » et moissonnage, juin 2025 ; sanction Clearview
  AI, 20 M€, oct. 2022.
- CA Versailles, déc. 2025 : condamnation d'un agrégateur pour extraction d'annonces
  SeLoger/Logic-Immo (rappel : le périmètre des agrégateurs évolue).
