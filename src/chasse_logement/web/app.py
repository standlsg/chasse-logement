"""UI web de paramétrage et tableau de bord (FastAPI).

L'UI lit/écrit le fichier de configuration YAML (config.yaml) en ne touchant jamais
aux champs secrets (mots de passe) : ils sont chargés depuis le fichier mais jamais
affichés ni écrasés par les formulaires.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import load_config
from ..pipeline import run_once
from ..store import ListingStore

PORTALS = ["leboncoin", "seloger", "pap", "bienici", "logic-immo"]

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _parse_list(text: str) -> list[str]:
    return [item.strip() for item in text.replace(",", " ").split() if item.strip()]


def create_app(config_path: str, run_scheduler: bool = True) -> FastAPI:
    app = FastAPI(title="chasse-logement")

    def load_raw() -> dict[str, Any]:
        return yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}

    def save_raw(raw: dict[str, Any]) -> None:
        Path(config_path).write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        cfg = load_config(config_path)
        store = ListingStore(cfg.database_path)
        try:
            stats = store.stats()
            matches = store.recent_matches(limit=30)
        finally:
            store.close()
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "stats": stats,
                "matches": matches,
                "criteria": cfg.criteria,
                "sources": cfg.sources,
                "notify": cfg.notify,
            },
        )

    @app.get("/parametres", response_class=HTMLResponse)
    def get_parametres(request: Request, saved: bool = False) -> HTMLResponse:
        raw = load_raw()
        return TEMPLATES.TemplateResponse(
            request, "parametres.html", {"raw": raw, "portals": PORTALS, "saved": saved}
        )

    @app.post("/parametres")
    def post_parametres(
        budget_max: float = Form(...),
        min_surface_m2: float = Form(0.0),
        min_rooms: int = Form(0),
        postcodes: str = Form(""),
        cities: str = Form(""),
        furnished: str = Form("any"),
        exclude_keywords: str = Form(""),
        min_score: float = Form(50.0),
        portals: list[str] = Form([]),
        api_enabled: bool = Form(False),
        email_to: str = Form(""),
        notify_mode: str = Form("digest"),
    ) -> RedirectResponse:
        raw = load_raw()
        criteria = raw.setdefault("criteria", {})
        criteria.update(
            {
                "budget_max": budget_max,
                "min_surface_m2": min_surface_m2,
                "min_rooms": min_rooms,
                "postcodes": _parse_list(postcodes),
                "cities": _parse_list(cities),
                "furnished": {"any": None, "true": True, "false": False}[furnished],
                "exclude_keywords": _parse_list(exclude_keywords),
                "min_score": min_score,
            }
        )
        sources = raw.setdefault("sources", {})
        sources.setdefault("imap", {})["portals"] = portals
        sources.setdefault("api", {})["enabled"] = api_enabled
        notify = raw.setdefault("notify", {})
        notify["mode"] = notify_mode
        notify.setdefault("email", {})["to_addrs"] = _parse_list(email_to)
        save_raw(raw)
        return RedirectResponse("/parametres?saved=1", status_code=303)

    @app.post("/parametres/feed/add")
    def post_feed_add(name: str = Form(...), url: str = Form(...)) -> RedirectResponse:
        raw = load_raw()
        feeds = raw.setdefault("sources", {}).setdefault("rss_feeds", [])
        feeds.append({"name": name, "url": url, "enabled": True})
        save_raw(raw)
        return RedirectResponse("/parametres", status_code=303)

    @app.post("/parametres/feed/update")
    def post_feed_update(
        idx: int = Form(...),
        name: str = Form(...),
        url: str = Form(...),
        enabled: list[str] = Form([]),
    ) -> RedirectResponse:
        raw = load_raw()
        feeds = raw.setdefault("sources", {}).setdefault("rss_feeds", [])
        if 0 <= idx < len(feeds):
            feeds[idx]["name"] = name
            feeds[idx]["url"] = url
            feeds[idx]["enabled"] = any(v == "1" for v in enabled)
        save_raw(raw)
        return RedirectResponse("/parametres", status_code=303)

    @app.post("/parametres/feed/delete")
    def post_feed_delete(idx: int = Form(...)) -> RedirectResponse:
        raw = load_raw()
        feeds = raw.setdefault("sources", {}).setdefault("rss_feeds", [])
        if 0 <= idx < len(feeds):
            feeds.pop(idx)
        save_raw(raw)
        return RedirectResponse("/parametres", status_code=303)

    @app.post("/run")
    def post_run() -> RedirectResponse:
        run_once(load_config(config_path))
        return RedirectResponse("/", status_code=303)

    if run_scheduler:

        def _loop() -> None:
            while True:
                try:
                    run_once(load_config(config_path))
                except Exception:  # noqa: BLE001 - le planificateur ne doit pas mourir
                    pass
                interval = max(1, load_config(config_path).schedule.interval_hours) * 3600
                time.sleep(interval)

        threading.Thread(target=_loop, daemon=True).start()

    return app
