"""Fusion cross-sources : regroupe les annonces parlant du même bien en un Property.

Heuristique : même code postal + prix/surface proches + titres similaires (Jaccard).
Un même bien publié sur Leboncoin, SeLoger et le site d'une agence n'apparaît qu'une
fois dans l'onglet Biens, avec un lien vers chaque source.
"""

from __future__ import annotations

import hashlib
import re
from statistics import median

from .models import Listing, Property, SourceRef

TOKEN_RE = re.compile(r"[a-z0-9àâäéèêëîïôöùûüç]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall((text or "").casefold()))


def title_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _close(a: float | None, b: float | None, rel_tol: float, abs_tol: float) -> bool:
    if a is None or b is None:
        return True
    return abs(a - b) <= max(abs_tol, rel_tol * max(a, b))


def same_property(a: Listing, b: Listing) -> bool:
    if a.dedup_key == b.dedup_key:
        return True
    if a.postcode and b.postcode and a.postcode != b.postcode:
        return False
    if not _close(a.price, b.price, rel_tol=0.07, abs_tol=30.0):
        return False
    if not _close(a.surface_m2, b.surface_m2, rel_tol=0.08, abs_tol=3.0):
        return False
    if a.rooms is not None and b.rooms is not None and a.rooms != b.rooms:
        return False
    return title_similarity(a.title, b.title) >= 0.45


def cluster(listings: list[Listing]) -> list[list[Listing]]:
    """Union-find sur les annonces (bucket par code postal pour rester rapide)."""
    buckets: dict[str, list[Listing]] = {}
    for lst in listings:
        buckets.setdefault(lst.postcode or "", []).append(lst)
    parent = {lst.dedup_key: lst.dedup_key for lst in listings}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    for bucket in buckets.values():
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                if same_property(bucket[i], bucket[j]):
                    union(bucket[i].dedup_key, bucket[j].dedup_key)
    groups: dict[str, list[Listing]] = {}
    for lst in listings:
        groups.setdefault(find(lst.dedup_key), []).append(lst)
    return list(groups.values())


def _median(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return float(median(vals)) if vals else None


def _inconsistencies(group: list[Listing]) -> list[str]:
    out: list[str] = []
    prices = sorted({lst.price for lst in group if lst.price is not None})
    if len(prices) > 1 and prices[0] > 0:
        rel = (prices[-1] - prices[0]) / prices[0]
        out.append(
            f"prix : de {prices[0]:.0f} € à {prices[-1]:.0f} € selon les sources "
            f"({rel * 100:.0f} % d'écart)"
        )
    surfaces = sorted({lst.surface_m2 for lst in group if lst.surface_m2 is not None})
    if len(surfaces) > 1 and surfaces[-1] - surfaces[0] > 2:
        out.append(f"surface : de {surfaces[0]:.0f} m² à {surfaces[-1]:.0f} m² selon les sources")
    rooms = sorted({lst.rooms for lst in group if lst.rooms is not None})
    if len(rooms) > 1:
        out.append(f"nombre de pièces : {rooms[0]} à {rooms[-1]} selon les sources")
    furnished = {lst.furnished for lst in group if lst.furnished is not None}
    if len(furnished) > 1:
        out.append("meublé/non meublé contradictoire selon les sources")
    return out


def build_property(group: list[Listing]) -> Property:
    group = sorted(group, key=lambda lst: lst.first_seen_at)
    first = group[0]
    prop_id = hashlib.sha256(first.dedup_key.encode()).hexdigest()[:16]
    titles = [lst.title for lst in group if lst.title]
    descriptions = [lst.description for lst in group if lst.description]
    published = [lst.published_at for lst in group if lst.published_at]
    rooms_vals = [lst.rooms for lst in group if lst.rooms is not None]
    return Property(
        prop_id=prop_id,
        title=max(titles, key=len, default=""),
        description=max(descriptions, key=len, default=""),
        price=_median([lst.price for lst in group]),
        charges=_median([lst.charges for lst in group]),
        surface_m2=_median([lst.surface_m2 for lst in group]),
        rooms=int(median(rooms_vals)) if rooms_vals else None,
        listing_type=first.listing_type,
        furnished=next((lst.furnished for lst in group if lst.furnished is not None), None),
        city=next((lst.city for lst in group if lst.city), None),
        postcode=first.postcode,
        sources=[
            SourceRef(
                source_id=lst.source_id,
                url=lst.url,
                title=lst.title,
                price=lst.price,
                surface_m2=lst.surface_m2,
                rooms=lst.rooms,
                first_seen_at=lst.first_seen_at,
            )
            for lst in group
        ],
        inconsistencies=_inconsistencies(group),
        published_at=min(published) if published else None,
        first_seen_at=first.first_seen_at,
        last_seen_at=max(lst.last_seen_at for lst in group),
    )
