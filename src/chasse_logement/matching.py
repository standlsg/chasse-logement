from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .config import Criteria
from .geo import haversine_km
from .models import Listing, Property


class MatchResult(BaseModel):
    listing: Listing | Property
    score: float
    reasons: list[str] = Field(default_factory=list)


def matches(item: Listing | Property, criteria: Criteria) -> tuple[bool, list[str]]:
    """Filtres durs. Retourne (ok, raisons_d_echec)."""
    failed: list[str] = []

    total = item.total_price
    if total is not None and total > criteria.budget_max:
        failed.append(f"budget dépassé ({total:.0f} € > {criteria.budget_max:.0f} €)")

    if criteria.min_surface_m2 and (item.surface_m2 or 0) < criteria.min_surface_m2:
        failed.append(
            f"surface insuffisante ({item.surface_m2 or 0:.0f} m² "
            f"< {criteria.min_surface_m2:.0f} m²)"
        )

    rooms = getattr(item, "rooms_effective", None)
    if rooms is None:
        rooms = item.rooms or 0
    if criteria.min_rooms and rooms < criteria.min_rooms:
        failed.append(f"pièces insuffisantes ({rooms} < {criteria.min_rooms})")

    if criteria.postcodes:
        if item.postcode not in criteria.postcodes:
            failed.append(f"code postal hors zone ({item.postcode or 'inconnu'})")
    elif criteria.cities:
        cities = {c.casefold() for c in criteria.cities}
        if (item.city or "").casefold() not in cities:
            failed.append(f"ville hors zone ({item.city or 'inconnue'})")
    elif (
        criteria.center_latitude is not None
        and criteria.center_longitude is not None
        and criteria.radius_km
    ):
        if item.latitude is None or item.longitude is None:
            failed.append("coordonnées inconnues (critère rayon)")
        else:
            dist = haversine_km(
                criteria.center_latitude,
                criteria.center_longitude,
                item.latitude,
                item.longitude,
            )
            if dist > criteria.radius_km:
                failed.append(f"hors rayon ({dist:.1f} km > {criteria.radius_km:.0f} km)")

    if (
        criteria.furnished is not None
        and item.furnished is not None
        and item.furnished != criteria.furnished
    ):
        failed.append(f"meublé={item.furnished} ≠ critère {criteria.furnished}")

    text = f"{item.title} {item.description}".casefold()
    for kw in criteria.exclude_keywords:
        if kw.casefold() in text:
            failed.append(f"mot-clé exclu : {kw}")

    return (not failed, failed)


def score(item: Listing | Property, pool: list[Listing]) -> tuple[float, list[str]]:
    """Score 0-100 : base 50 + fraîcheur (≤ 20) + position prix/m² vs pool (≤ 30)."""
    reasons: list[str] = []
    s = 50.0

    if item.published_at is not None:
        hours = max(0.0, (datetime.now(UTC) - item.published_at).total_seconds() / 3600)
        fresh = max(0.0, 1.0 - hours / (7 * 24))
        s += 20 * fresh
        reasons.append(f"fraîcheur {fresh * 100:.0f}% (+{20 * fresh:.0f})")
    else:
        s += 10
        reasons.append("date de publication inconnue (+10)")

    ppm = item.price_per_m2
    pool_ppm = [item.price_per_m2 for item in pool if item.price_per_m2]
    if ppm and pool_ppm:
        cheaper = sum(1 for p in pool_ppm if p is not None and p > ppm) / len(pool_ppm)
        s += 30 * cheaper
        reasons.append(
            f"prix/m² {ppm:.0f} € mieux placé que {cheaper * 100:.0f}% "
            f"du marché suivi (+{30 * cheaper:.0f})"
        )
    else:
        s += 15
        reasons.append("prix/m² non comparable (+15)")

    return min(100.0, s), reasons


def evaluate(
    item: Listing | Property, criteria: Criteria, pool: list[Listing]
) -> MatchResult | None:
    ok, _failed = matches(item, criteria)
    if not ok:
        return None
    s, reasons = score(item, pool)
    if s < criteria.min_score:
        return None
    return MatchResult(listing=item, score=round(s, 1), reasons=reasons)
