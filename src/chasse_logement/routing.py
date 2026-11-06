"""Trajet « hors trafic » via OSRM (demo publique).

OSRM calcule des temps **à vide (free-flow)** : c'est exactement une estimation
« hors trafic » en voiture. Résultat mis en cache en SQLite par bien.
"""

from __future__ import annotations

import httpx

OSRM = "https://router.project-osrm.org/route/v1/driving"


class Router:
    def __init__(self, fetch=None) -> None:
        self._fetch = fetch or self._http_fetch

    def route_hors_trafic(self, lat1: float, lon1: float, lat2: float, lon2: float) -> dict | None:
        data = self._fetch(f"{lon1},{lat1};{lon2},{lat2}")
        routes = (data or {}).get("routes") or []
        if (data or {}).get("code") != "Ok" or not routes:
            return None
        route = routes[0]
        duration_s = float(route.get("duration", 0))
        distance_m = float(route.get("distance", 0))
        minutes = round(duration_s / 60)
        return {
            "duration_s": duration_s,
            "duration_min": minutes,
            "distance_km": round(distance_m / 1000, 1),
            "label": f"≈ {minutes} min ({distance_m / 1000:.1f} km) en voiture, hors trafic",
        }

    def _http_fetch(self, coords: str) -> dict | None:
        try:
            resp = httpx.get(f"{OSRM}/{coords}", params={"overview": "false"}, timeout=15.0)
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        return resp.json()
