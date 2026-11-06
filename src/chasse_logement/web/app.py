"""UI web de paramétrage et tableau de bord (FastAPI).

L'UI lit/écrit le fichier de configuration YAML (config.yaml) en ne touchant jamais
aux champs secrets (mots de passe) : ils sont chargés depuis le fichier mais jamais
affichés ni écrasés par les formulaires.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..config import load_config
from ..geocoding import Geocoder, address_query
from ..pipeline import run_once
from ..poi import PoiExplorer
from ..routing import Router
from ..sources.catalog import CATALOGS, apply_catalog
from ..store import ListingStore

PORTALS = [
    "leboncoin",
    "seloger",
    "pap",
    "bienici",
    "logic-immo",
    "gensdeconfiance",
    "appartager",
    "studapart",
]

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _parse_list(text: str) -> list[str]:
    return [item.strip() for item in text.replace(",", " ").split() if item.strip()]


def _f(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
            props = [p for p in store.get_properties() if p.notified][:30]
        finally:
            store.close()
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "stats": stats,
                "props": props,
                "criteria": cfg.criteria,
                "sources": cfg.sources,
                "notify": cfg.notify,
            },
        )

    @app.get("/biens", response_class=HTMLResponse)
    def biens(
        request: Request,
        q: str = "",
        source: str = "",
        postcode: str = "",
        prix_min: str = "",
        prix_max: str = "",
        score_min: str = "",
        flags_only: str = "",
        sort: str = "last_seen_at",
        order: str = "desc",
    ) -> HTMLResponse:
        cfg = load_config(config_path)
        store = ListingStore(cfg.database_path)
        try:
            props = store.get_properties()
            source_ids = sorted({s.source_id for p in props for s in p.sources})
            if q:
                ql = q.casefold()
                props = [
                    p
                    for p in props
                    if ql in f"{p.title} {p.address_label or ''} {p.postcode or ''}".casefold()
                ]
            if source:
                props = [p for p in props if any(s.source_id == source for s in p.sources)]
            if postcode:
                props = [p for p in props if p.postcode == postcode]
            lo, hi, ms = _f(prix_min), _f(prix_max), _f(score_min)
            if lo is not None:
                props = [p for p in props if (p.total_price or 0) >= lo]
            if hi is not None:
                props = [p for p in props if (p.total_price or 0) <= hi]
            if ms is not None:
                props = [p for p in props if p.score >= ms]
            if flags_only:
                props = [p for p in props if p.red_flags]
            sort_keys = {
                "title": lambda p: (p.title or "").casefold(),
                "price": lambda p: p.total_price or 0,
                "surface_m2": lambda p: p.surface_m2 or 0,
                "rooms": lambda p: p.rooms or 0,
                "score": lambda p: p.score,
                "postcode": lambda p: p.postcode or "",
                "nb_sources": lambda p: len(p.sources),
                "last_seen_at": lambda p: p.last_seen_at,
            }
            props.sort(
                key=sort_keys.get(sort, sort_keys["last_seen_at"]), reverse=(order == "desc")
            )
            total = len(props)
            geo = Geocoder(cache=store) if cfg.enrichment.geocode else None
            poix = PoiExplorer(radius_m=cfg.enrichment.poi_radius_m)
            router = Router()
            dest = None
            if cfg.commute.enabled and cfg.commute.destination_address and geo is not None:
                dest_geo = geo.geocode(cfg.commute.destination_address)
                if dest_geo is not None:
                    dest = (dest_geo.latitude, dest_geo.longitude)
            rows = []
            for p in props[:100]:
                if p.latitude is None and geo is not None:
                    g = geo.geocode(address_query(p))
                    if g is not None:
                        p.latitude, p.longitude = g.latitude, g.longitude
                        p.address_label, p.address_precision = g.label, g.precision
                        store.save_property(p)
                poi_data = None
                if p.latitude and cfg.enrichment.poi:
                    cached = store.get_cached("poi_cache", p.prop_id)
                    if cached:
                        poi_data = json.loads(cached)
                    else:
                        poi_data = poix.nearby(p.latitude, p.longitude)
                        if poi_data is not None:
                            store.set_cached(
                                "poi_cache", p.prop_id, json.dumps(poi_data, ensure_ascii=False)
                            )
                route = None
                if dest and p.latitude and cfg.commute.enabled:
                    rc = store.get_cached("route_cache", p.prop_id)
                    if rc:
                        route = json.loads(rc)
                    else:
                        route = router.route_hors_trafic(p.latitude, p.longitude, dest[0], dest[1])
                        if route is not None:
                            store.set_cached(
                                "route_cache", p.prop_id, json.dumps(route, ensure_ascii=False)
                            )
                rows.append({"prop": p, "poi": poi_data, "route": route})
        finally:
            store.close()
        filters = {
            "q": q,
            "source": source,
            "postcode": postcode,
            "prix_min": prix_min,
            "prix_max": prix_max,
            "score_min": score_min,
            "flags_only": flags_only,
        }
        return TEMPLATES.TemplateResponse(
            request,
            "biens.html",
            {
                "rows": rows,
                "total": total,
                "filters": filters,
                "qs": urlencode({k: v for k, v in filters.items() if v}),
                "sort": sort,
                "order": order,
                "source_ids": source_ids,
                "commute_label": cfg.commute.destination_label if cfg.commute.enabled else None,
            },
        )

    @app.get("/parametres", response_class=HTMLResponse)
    def get_parametres(request: Request, saved: bool = False) -> HTMLResponse:
        raw = load_raw()
        return TEMPLATES.TemplateResponse(
            request,
            "parametres.html",
            {"raw": raw, "portals": PORTALS, "saved": saved, "catalogs": CATALOGS},
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

    @app.post("/parametres/catalog")
    def post_catalog(
        region: str = Form(...), apply_postcodes: bool = Form(False)
    ) -> RedirectResponse:
        if region not in CATALOGS:
            return RedirectResponse("/parametres", status_code=303)
        raw = apply_catalog(load_raw(), region, apply_postcodes=apply_postcodes)
        save_raw(raw)
        return RedirectResponse("/parametres?saved=1", status_code=303)

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
