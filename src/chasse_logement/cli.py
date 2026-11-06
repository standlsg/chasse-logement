from __future__ import annotations

import argparse
import json
import sys
import time

from .config import load_config
from .pipeline import run_once


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
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8000)

    disc_p = sub.add_parser("discover", help="détecte les flux RSS d'un site (robots.txt respecté)")
    disc_p.add_argument("url")

    purge_p = sub.add_parser("purge", help="supprime annonces/biens plus vieux que N jours")
    purge_p.add_argument("--config", default="config.yaml")
    purge_p.add_argument("--days", type=int, default=None)

    args = parser.parse_args(argv)

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
