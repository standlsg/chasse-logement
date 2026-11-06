"""POI à proximité (écoles, commerces, restaurants, transports) via Overpass / OSM.

Données OpenStreetMap (ODbL, attribution OSM). Un seul appel Overpass par bien,
résultat mis en cache en SQLite.
"""

from __future__ import annotations

import httpx

from .geo import haversine_km

OVERPASS = "https://overpass-api.de/api/interpreter"

SCHOOL_AMENITIES = {"school", "kindergarten", "university"}
RESTAURANT_AMENITIES = {"restaurant", "cafe", "fast_food"}


class PoiExplorer:
    def __init__(self, fetch=None, radius_m: int = 800) -> None:
        self._fetch = fetch or self._http_fetch
        self.radius_m = radius_m

    def nearby(self, lat: float, lon: float) -> dict | None:
        query = (
            f"[out:json][timeout:20];"
            f"nwr(around:{self.radius_m},{lat},{lon})"
            f'[amenity~"^(school|kindergarten|university|restaurant|cafe|fast_food)$"];'
            f"nwr(around:{self.radius_m},{lat},{lon})[shop];"
            f"nwr(around:{self.radius_m},{lat},{lon})[public_transport=station];"
            f"out tags center;"
        )
        data = self._fetch(query)
        if data is None:
            return None
        elements = data.get("elements") or []
        buckets: dict[str, list[dict]] = {
            "écoles": [],
            "commerces": [],
            "restaurants": [],
            "transports": [],
        }
        for el in elements:
            tags = el.get("tags", {})
            el_lat = el.get("lat") or (el.get("center") or {}).get("lat")
            el_lon = el.get("lon") or (el.get("center") or {}).get("lon")
            if el_lat is None or el_lon is None:
                continue
            name = tags.get("name", "(sans nom)")
            distance = round(haversine_km(lat, lon, el_lat, el_lon) * 1000)
            amenity = tags.get("amenity", "")
            if amenity in SCHOOL_AMENITIES:
                buckets["écoles"].append({"name": name, "distance_m": distance})
            elif amenity in RESTAURANT_AMENITIES:
                buckets["restaurants"].append({"name": name, "distance_m": distance})
            elif tags.get("shop"):
                buckets["commerces"].append({"name": name, "distance_m": distance})
            elif tags.get("public_transport"):
                buckets["transports"].append({"name": name, "distance_m": distance})
        for cat in buckets.values():
            cat.sort(key=lambda x: x["distance_m"])
        return {cat: items[:8] for cat, items in buckets.items()}

    def _http_fetch(self, query: str) -> dict | None:
        try:
            resp = httpx.post(OVERPASS, data={"data": query}, timeout=30.0)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        return resp.json()
