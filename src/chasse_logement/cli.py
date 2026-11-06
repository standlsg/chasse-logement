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

    args = parser.parse_args(argv)

    if args.command == "check-robots":
        from .robots import robots_summary

        print(json.dumps(robots_summary(args.url, args.user_agent), indent=2))
        return 0

    cfg = load_config(args.config)

    if args.command == "run":
        stats = run_once(cfg)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
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
