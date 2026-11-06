# Déployer sur Render (tier gratuit)

✅ **Ça marche pour l'UI** : ton build Render avance bien (Dockerfile compatible, service
`chasse-logement` en « Building… »). 3 pièges du tier free à connaître (2026) :

| Contrainte Render free | Impact pour chasse-logement | Solution retenue |
|---|---|---|
| Sleep après **15 min sans trafic** (cold start ~30-60 s) | UI OK à la demande, mais le **planificateur interne s'arrête** → plus de recherche quotidienne | **Keep-alive externe** : UptimeRobot (gratuit, 50 monitors, ping toutes les 5 min) ou cron-job.org sur `https://<svc>.onrender.com/healthz` → l'instance ne dort jamais, le scheduler interne tourne. Budget : ~730 h/mo < 750 h gratuites. |
| **Disque éphémère** (pas de disque persistant en free) | `data/chasse-logement.db` (SQLite) perdu à chaque sleep/redéploiement → historique/dédup perdus (les annonces sont re-collectées chaque jour ; les emails déjà envoyés peuvent être renvoyés une fois après un redeploy) | Acceptable en MVP. Fiabilisation V2 : base externe (Turso libSQL gratuit 5 Go, ou Postgres Render payant — note : Postgres free expire après 30 j). Les modifs faites dans l'UI (`/parametres`) sont aussi éphémères : à re-appliquer après chaque redeploy, ou à figer dans l'image. |
| **SMTP bloqué (ports 25/465/587)** | Les notifications email par SMTP ne partent pas | Notifier **API Resend** (HTTPS/443, 3 000 mails/mois gratuits) : `notify.resend.enabled: true`, `from_addr` domaine vérifié, clé dans `CL_RESEND_API_KEY`. |
| Cron jobs Render indisponibles en free (min 1 $/mois) | Pas de cron Render | Le scheduler interne (`serve`) + keep-alive externe. |
| 512 Mo RAM / 0,1 CPU partagés | OK pour cette appli (~150 Mo) | — |

## Déploiement (2 façons)

**A. Blueprint (recommandé)** : sur Render → New → Blueprint → connecte le repo
`standlsg/chasse-logement` → il détecte `render.yaml` → Deploy. Région `frankfurt` (UE),
plan `free`, healthcheck `/healthz`. Puis dans les **Environment variables** du service,
ajoute les secrets : `CL_IMAP_PASSWORD`, `CL_RESEND_API_KEY` (ou `CL_SMTP_PASSWORD`),
`CL_TELEGRAM_TOKEN`.

**B. Web service manuel** : New → Web Service → repo + branche `preprod` (ou `prod`),
runtime Docker, plan free, région Frankfurt, health check path `/healthz`.
Le `Dockerfile` embarque `regions/aix-marseille.example.yaml` comme `config.yaml` par
défaut, et `serve` écoute sur `0.0.0.0:$PORT` automatiquement (Render impose `$PORT`).

## Après le déploiement

1. Ouvre `https://<service>.onrender.com` → UI (Tableau de bord / Biens / Paramètres).
2. Règle critères + sources + emails dans `/parametres` (éphémère en free : à refaire après
   chaque redeploy, ou figer dans l'image via un fork du Dockerfile).
3. Crée le keep-alive : UptimeRobot → Add monitor → type HTTP(s), URL
   `https://<service>.onrender.com/healthz`, intervalle **5 min**.
4. Notifications : crée un compte [Resend](https://resend.com) (gratuit), vérifie ton domaine
   d'envoi (ou utilise `*.resend.dev` pour tester), mets la clé dans `CL_RESEND_API_KEY`
   et `notify.resend.enabled: true` + `from_addr` (via l'UI ou l'image).
5. Vérifie une tournée manuelle : bouton « ▶ Lancer une tournée » dans l'UI, ou les logs
   Render (onglet Logs).

## Limites à retenir

- Premier chargement après sommeil : ~30-60 s (cold start) — le keep-alive évite ça.
- 750 instance-hours/mois gratuits (1 service 24/7 ≈ 730 h → OK avec 1 seul service).
- Redéploiement (push git) = disque réinitialisé → re-collecte complète, éventuellement
  quelques emails en double. Pour de la prod fiable : passer en Starter (7 $/mois, disque
  persistant) ou VPS (voir `deploy/README.md`).
