# Registre des sources

Dernière mise à jour : 2026-11. Pour chaque source : type d'accès retenu et base
juridique. Voir `docs/conformite.md` (grille d'entrée) avant toute évolution.

| source | type d'accès | base juridique | vérification |
|---|---|---|---|
| Leboncoin | alertes email (compte perso, boîte dédiée, lecture IMAP) | utilisation du service par son utilisateur | CGU 2026-11 |
| SeLoger | idem | idem | CGU 2026-11 |
| PAP | idem | idem | CGU 2026-11 |
| Bien'ici | idem | idem | CGU 2026-11 |
| Logic-Immo | idem | idem | CGU 2026-11 |
| Agences (par zone) | flux RSS publiés volontairement | contenu public prévu pour diffusion | robots.txt + flux 2026-11 |
| **MoteurImmo** (connecteur `sources/api.py`, config `sources.api`) | API REST sous contrat (freemium, pay-per-listing ; compte + clé sur moteurimmo.fr/offre-api) | contrat commercial | 2026-11 |
| Melo/Stream Estate, Yanport (alternatives) | idem | contrat commercial | à signer |
| (V1) Open data marché : Carte des loyers ANIL, OLL, DVF+ (data.gouv.fr) | téléchargement/API ouvertes | open data État (licence ouverte) | 2026-11 |
| (V1) Géocodage GéoPlateforme + API Géo | API publiques gratuites | service public (api.gouv.fr) | 2026-11 |
| POI écoles/commerces/transports | Overpass / OpenStreetMap | données OSM, licence ODbL (attribution © OpenStreetMap) | 2026-11 |
| Itinéraire « hors trafic » | OSRM (router.project-osrm.org, free-flow) | service public demo, données OSM ODbL | 2026-11 |

## Focus Aix-Marseille (13)

Catalogue régional : `src/chasse_logement/sources/catalog.py` (appliqué en un clic dans
l'UI /parametres). Portails avec alertes email : leboncoin, seloger, pap, bienici,
logic-immo, gensdeconfiance, appartager, studapart. Agences locales : Orpi, Foncia,
Century 21 Aix, Laforêt, Stéphane Plaza Marseille 6e, SAFTI + indépendants (voir
catalogue) — flux RSS à détecter via `chasse-logement discover <site>`. Dispositifs
manuels (compte requis) : CROUS Aix-Marseille, Lokaviz, Action Logement / AL'in, In'li,
demande-logement-social.gouv.fr. Voir `docs/etude-faisabilite.md` §6.
