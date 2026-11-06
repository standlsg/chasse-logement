"""Géocodage via la GéoPlateforme (IGN) — gratuit, sans clé, 50 req/s.

Résultat mis en cache en SQLite pour ne pas re-geocoder deux fois la même requête.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

import httpx
from pydantic import BaseModel

GEO_BASE = "https://data.geopf.fr/geocodage/search"

ADDRESS_HINT_RE = re.compile(
    r"\d{1,4}\s+(rue|avenue|av\.|bd|boulevard|impasse|place|allée|allee|quai|cours|chemin|passage|square)"
    r"[\w\sàâäéèêëîïôöùûüç'.-]+",
    re.IGNORECASE,
)


class GeocodeResult(BaseModel):
    label: str
    latitude: float
    longitude: float
    score: float
    precision: str  # housenumber | street | locality | ...


class Cache(Protocol):
    def get_cached(self, table: str, key: str) -> str | None: ...

    def set_cached(self, table: str, key: str, payload: str) -> None: ...


def address_query(item: Any) -> str:
    """Construit la requête de géocodage la plus précise possible pour un bien."""
    for text in (getattr(item, "description", "") or "", getattr(item, "title", "") or ""):
        m = ADDRESS_HINT_RE.search(text)
        if m:
            return m.group(0).strip()
    return " ".join(x for x in [getattr(item, "postcode", None), getattr(item, "city", None)] if x)


class Geocoder:
    def __init__(self, fetch=None, cache: Cache | None = None) -> None:
        self._fetch = fetch or self._http_fetch
        self._cache = cache

    def geocode(self, query: str) -> GeocodeResult | None:
        query = (query or "").strip()
        if not query:
            return None
        if self._cache is not None:
            hit = self._cache.get_cached("geocodes", query)
            if hit:
                return GeocodeResult.model_validate(json.loads(hit))
        data = self._fetch(query)
        features = (data or {}).get("features") or []
        if not features:
            return None
        feat = features[0]
        props = feat.get("properties", {})
        lon, lat = feat["geometry"]["coordinates"]
        result = GeocodeResult(
            label=props.get("label", ""),
            latitude=lat,
            longitude=lon,
            score=float(props.get("score", 0.0)),
            precision=props.get("type", ""),
        )
        if self._cache is not None:
            self._cache.set_cached("geocodes", query, result.model_dump_json())
        return result

    def _http_fetch(self, query: str) -> dict | None:
        try:
            resp = httpx.get(GEO_BASE, params={"q": query, "limit": 1}, timeout=15.0)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        return resp.json()
