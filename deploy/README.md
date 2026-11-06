# Hébergement dynamique — comparatif et déploiement

L'interface (FastAPI) doit tourner sur une machine qui exécute Python. Pages = statique = ❌.

## Choisir un hébergeur

| Option | Prix | Région/données | Difficulté | Notes |
|---|---|---|---|---|
| **Poste perso en local** (`serve` sur 127.0.0.1) | 0 € | chez toi | ⭐ facile | Voir `docs/local.md` ; < 1 Go de disque. Accès distant via tunnel SSH / Tailscale. |
| **VPS** (Hetzner CX12, OVHcloud VPS Starter, Scaleway DEV1-S, Ionos) + `deploy/docker-compose.prod.yml` | ~3-6 €/mois | UE (Hetzner DE, OVH FR) | ⭐⭐ moyen | Contrôle total, RGPD-friendly. HTTPS auto + basic auth via Caddy. Déploiement auto via `.github/workflows/deploy.yml` (push sur `prod`). |
| **Koyeb** (France) | gratuit (hobby) puis payant | UE | ⭐ facile | Deploy depuis GitHub, volume persistant pour `data/`. Attention : l'instance hobby peut s'endormir → préférer un VPS pour le cron quotidien fiable. |
| **Clever Cloud** (Nantes, France) | ~5-10 €/mois | FR | ⭐⭐ moyen | Docker/Python + cron natif, très RGPD-friendly. |
| **Oracle Cloud Free Tier** (VM ARM) | 0 € (always free) | région EU (Paris/Franfurt) | ⭐⭐ moyen | Généreux mais compte Oracle (US) : données hébergées en UE. |
| **Raspberry Pi à la maison + Tailscale** | ~0 € (matériel existant) | chez toi | ⭐⭐ moyen | UI joignable uniquement via ton VPN privé Tailscale — jamais exposé publiquement. |

**Recommandation** : poste perso en local pour commencer (0 €, `docs/local.md`) ; VPS
Hetzner/OVH (~4 €/mois) avec `deploy/docker-compose.prod.yml` si tu veux un accès 24/7
à distance avec HTTPS.

## Déploiement VPS (Hetzner/OVH/Scaleway/Ionos), étape par étape

1. Créer le VPS (Ubuntu 24.04, 1 vCPU / 2 Go RAM suffit), noter son IP/DNS.
2. Sur le serveur : `apt install docker.io git`, cloner le dépôt dans `/var/www/chasse-logement`,
   copier `regions/aix-marseille.example.yaml` → `config.yaml`, créer `.env`
   (secrets `CL_*`, `DOMAIN=ton-domaine.fr`, `BASIC_USER`, `BASIC_HASH=$(docker run caddy:2 caddy hash-password --plaintext 'mot-de-passe-fort')`).
3. Premier lancement : `docker compose -f deploy/docker-compose.prod.yml up -d --build`
   → UI sur `https://ton-domaine.fr` (certificat Let's Encrypt auto, basic auth).
4. Mises à jour manuelles : `./deploy/deploy.sh root@ton-vps /var/www/chasse-logement`.
5. Mises à jour auto : merge sur `prod` → workflow `deploy.yml` (secrets `SSH_HOST`,
   `SSH_USER`, `SSH_KEY` dans Settings → Secrets → Actions ; l'environnement `prod`
   peut exiger une validation manuelle).

## Points de vigilance

- **Ne jamais ouvrir le port 8000 sans auth** : Caddy (basic auth + HTTPS) ou tunnel SSH/Tailscale.
- **Sauvegarde** : volume `data` (SQLite) — copier `data/chasse-logement.db` régulièrement
  (ex. cron `cp` vers un stockage externe).
- **Mémoire/disque** : l'appli tient dans ~300 Mo de RAM et < 100 Mo de disque de données
  (rétention auto `retention_days`).
- Le dépôt étant public : les secrets ne sont JAMAIS dans le dépôt (`.env`, `config.yaml`,
  `data/` gitignés) ; les secrets Actions d'un dépôt public ne sont exposés que sur les
  événements `push` du dépôt lui-même, jamais sur les PR de forks.
