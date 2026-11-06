# Déployer sur Clever Cloud (Docker, France, persistant)

Clever Cloud (Nantes, France) héberge l'appli Docker avec **stockage persistant** —
contrairement au tier free de Render. Parfait pour ce projet.

## Réponse courte : faut-il une base de données dédiée ?

**Non, pas maintenant.** L'appli utilise **SQLite** (`data/chasse-logement.db`) :
il te suffit d'un **FS Bucket** (stockage persistant Clever Cloud) monté sur `/app/data`
pour que les données récoltées (annonces, biens, notifiés, caches géocodage/POI) **survivent
aux redéploiements**. Coût : quelques Mo = négligeable (tarif au Go).

Si plus tard tu veux une vraie DB managée : addon **PostgreSQL** Clever Cloud (~6 €/mois)
→ nécessitera un backend Postgres dans le code (prévu en V2, le store est isolé dans
`store.py`). Redis : inutile pour l'instant.

## Étapes

1. **Créer l'app** : [console.clever-cloud.com](https://console.clever-cloud.com) →
   "Add an app" → dépôt GitHub `standlsg/chasse-logement`, branche `prod` (ou `preprod`),
   runtime **Docker** (détecté via le `Dockerfile`). Région : Paris (FR).
2. **Instance** : taille **Nano** (512 Mo RAM) suffisante (~150 Mo utilisés). Facturation
   à la seconde ; compte ~5-10 €/mois si toujours allumé (mettable en pause).
3. **Stockage persistant** : app → Add-ons → **FS Bucket** → crée-le, puis **lie-le** à
   l'app avec le point de montage `/app/data`. (Alternative via `clevercloud/buckets.json`,
   voir `clevercloud/buckets.example.json` : remplacer `BUCKET_ID` par l'ID du bucket.)
4. **Config persistante** : le `Dockerfile` démarre avec
   `chasse-logement serve --config /app/data/config.yaml` ; au 1er boot, le CLI copie la
   config embarquée (région Aix-Marseille) vers le bucket (`cli._ensure_config`) → **les
   réglages faits dans l'UI /parametres persistent entre les redéploiements**.
5. **Secrets** (app → Environment variables) :
   - `CL_IMAP_PASSWORD` : mot de passe IMAP de la **boîte mail dédiée** (jamais tes comptes portails)
   - `CL_RESEND_API_KEY` : clé API [Resend](https://resend.com) (gratuit 3 000 mails/mois)
   - `CL_TELEGRAM_TOKEN` (optionnel)
   - `PORT` est injecté automatiquement par Clever Cloud (l'appli écoute sur `0.0.0.0:$PORT`).
6. **Mails** : dans l'UI `/parametres` (ou config), active **Resend**
   (`notify.resend.enabled: true` + `from_addr` = adresse sur domaine vérifié Resend,
   ou `*.resend.dev` pour tester) + destinataires dans « Destinataires email ».
   → les PaaS bloquent souvent le SMTP direct ; l'API HTTPS/443 passe partout.
7. **URL** : `https://<app>.cleverapps.io` (HTTPS auto). Domaine perso possible (CNAME + TLS auto).
   L'UI est **sans auth par défaut** sur cleverapps.io : pour protéger (critères perso),
   mets un reverse proxy avec basic auth devant, ou restreins l'accès ; idéalement domaine
   perso + Caddy comme dans `deploy/`.
8. **Tournée quotidienne** : le `serve` embarque le planificateur (boucle interne,
   `schedule.interval_hours: 24`) — aucune cron externe nécessaire, l'instance ne dort pas.
9. **Mises à jour** : chaque push sur la branche liée redéploie automatiquement. Les données
   restent sur le FS Bucket. Backup : copier `data/chasse-logement.db` via le CLI Clever
   (`clever`) ou un job périodique.

## Ordre de grandeur des coûts (2026)

- Instance Nano always-on : ~5-10 €/mois (facturation à la seconde, pausable).
- FS Bucket (quelques dizaines de Mo) : ~0,01 €/mois (négligeable).
- Resend : 0 € (3 000 mails/mois).
- **Total : ~5-10 €/mois**, français, persistant, mails OK.

Voir aussi `deploy/README.md` (comparatif complet) et `docs/render.md` (pourquoi Render free ne convient pas).
