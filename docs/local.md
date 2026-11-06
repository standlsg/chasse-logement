# Hébergement local (recommandé si espace disque limité)

L'appli tourne très bien sur un poste perso : **pas besoin de Docker en local**
(Docker = ~1-2 Go d'images ; un venv Python = ~250 Mo).

## Prérequis

- Python ≥ 3.11
- ~300 Mo de disque libres (voir budget ci-dessous)
- ~256 Mo de RAM (l'appli consomme ~100-200 Mo)

## Budget disque (ordres de grandeur)

| Élément | Taille |
|---|---|
| dépôt git (`.git`) | ~15 Mo |
| venv Python (`.venv`, deps web) | ~250 Mo |
| base SQLite `data/chasse-logement.db` | ~2 Mo pour 1 000 annonces, ~20 Mo pour 10 000 |
| caches géocodage/POI/routes | ~1-5 Mo |
| **Total** | **< 1 Go** |

La rétention automatique (`retention_days: 90` dans `config.yaml`) purge les
annonces/biens de plus de 90 jours à chaque tournée ; purge manuelle :
`chasse-logement purge --config config.yaml --days 90`.

## Installation et lancement (une fois)

```bash
git clone https://github.com/standlsg/chasse-logement.git
cd chasse-logement
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[web]"          # ~250 Mo
cp regions/aix-marseille.example.yaml config.yaml
cp .env.example .env              # puis éditer .env avec les vrais secrets
chasse-logement serve --config config.yaml --host 127.0.0.1 --port 8000
```

Puis ouvrir **http://127.0.0.1:8000** (Tableau de bord / Biens / Paramètres).
`serve` lance aussi la tournée quotidienne en arrière-plan (`schedule.interval_hours`).

## Lancement automatique au démarrage (optionnel)

- **Linux (systemd)** : unit `~/.config/systemd/user/chasse-logement.service` avec
  `ExecStart=<repo>/.venv/bin/chasse-logement serve --config <repo>/config.yaml --host 127.0.0.1 --port 8000`,
  puis `systemctl --user enable --now chasse-logement`.
- **macOS (launchd)** : `~/Library/LaunchAgents/fr.chasse-logement.plist` pointant sur le même binaire.
- **Tournée seule sans UI** (cron) : `0 8 * * * <repo>/.venv/bin/chasse-logement run --config <repo>/config.yaml >> <repo>/run.log 2>&1`

## Sauvegarde / ménage

- Sauvegarder : copier `data/chasse-logement.db` (c'est toute la mémoire du moteur).
- Nettoyer pip : `pip cache purge` (libère ~100-200 Mo).
- Le dossier `data/` et `.env` sont gitignés : jamais commités.

## Si un jour tu veux l'exposer à distance

Ne ouvre pas le port 8000 sur Internet sans protection : passe par un **tunnel SSH**
(`ssh -L 8000:localhost:8000 <poste>`) ou un **VPN/overlay (Tailscale, WireGuard)** —
l'UI contient tes critères personnels. Voir `deploy/README.md` pour un déploiement
VPS avec HTTPS + basic auth (Caddy).
