from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from .config import load_config
from .pipeline import run_once


def _ensure_config(path: str) -> str:
    """Si le fichier de config n'existe pas (ex. 1er boot sur volume persistant Clever
    Cloud monté en /app/data), le copier depuis la config embarquée dans l'image."""
    p = Path(path)
    if not p.exists():
        baked = Path("config.yaml")
        if baked.exists() and p.resolve() != baked.resolve():
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(baked, p)
            print(f"config initialisée depuis l'image -> {p}", file=sys.stderr)
    return str(p)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chasse-logement",
        description="Recherche quotidienne de logement (sources légales : alertes natives, RSS).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="exécute une tournée unique (à planifier via cron)")
    run_p.add_argument("--config", default="config.yaml")

    daemon_p = sub.add_parser("daemon", help="boucle planifiée en continu")
    daemon_p.add_argument("--config", default="config.yaml")

    robots_p = sub.add_parser("check-robots", help="vérifie si robots.txt autorise une URL")
    robots_p.add_argument("url")
    robots_p.add_argument("--user-agent", default="*")

    serve_p = sub.add_parser("serve", help="UI web de paramétrage + exécution planifiée")
    serve_p.add_argument("--config", default="config.yaml")
    # Sur Render (env RENDER=... + PORT=...), on écoute sur 0.0.0.0:$PORT
    # Sur PaaS (Render/Clever Cloud : env RENDER ou PORT renseignée), on écoute sur 0.0.0.0:$PORT
    _on_paas = bool(os.environ.get("RENDER") or os.environ.get("PORT"))
    serve_p.add_argument("--host", default="0.0.0.0" if _on_paas else "127.0.0.1")
    serve_p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))

    disc_p = sub.add_parser("discover", help="détecte les flux RSS d'un site (robots.txt respecté)")
    disc_p.add_argument("url")

    purge_p = sub.add_parser("purge", help="supprime annonces/biens plus vieux que N jours")
    purge_p.add_argument("--config", default="config.yaml")
    purge_p.add_argument("--days", type=int, default=None)

    args = parser.parse_args(argv)

    if args.command in {"run", "daemon", "serve", "purge"}:
        args.config = _ensure_config(args.config)

    if args.command == "check-robots":
        from .robots import robots_summary

        print(json.dumps(robots_summary(args.url, args.user_agent), indent=2))
        return 0

    if args.command == "discover":
        from .discover import discover_rss

        print(json.dumps(discover_rss(args.url), indent=2, ensure_ascii=False))
        return 0

    if args.command == "purge":
        from .store import ListingStore

        try:
            cfg = load_config(args.config)
        except FileNotFoundError:
            print(f"erreur : fichier de configuration introuvable : {args.config}", file=sys.stderr)
            return 2
        days = args.days if args.days is not None else cfg.retention_days
        store = ListingStore(cfg.database_path)
        try:
            print(json.dumps(store.purge(days), indent=2))
        finally:
            store.close()
        return 0

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(
            f"erreur : fichier de configuration introuvable : {args.config}\n"
            "→ cp regions/aix-marseille.example.yaml config.yaml  (ou config.example.yaml)",
            file=sys.stderr,
        )
        return 2

    if args.command == "run":
        stats = run_once(cfg)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return 0

    if args.command == "serve":
        import uvicorn

        from .web.app import create_app

        uvicorn.run(create_app(args.config), host=args.host, port=args.port)
        return 0

    # daemon
    interval = max(1, cfg.schedule.interval_hours) * 3600
    while True:
        try:
            stats = run_once(cfg)
            print(json.dumps(stats, indent=2, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001 - un daemon ne doit pas mourir
            print(f"erreur: {exc}", file=sys.stderr, flush=True)
        time.sleep(interval)
    return 0
