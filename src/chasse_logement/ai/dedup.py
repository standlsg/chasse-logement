"""IA-2 : déduplication sémantique cross-sources + inférence (provider Mistral).

L'heuristique (merge.cluster) décide seule quand c'est clair ; l'IA n'est appelée que
pour les paires ambiguës (similarité de titre intermédiaire), avec un budget d'appels.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..merge import title_similarity
from ..models import Listing
from .redact import redact
from .signals import MistralClient

DEDUP_SYSTEM = (
    "Tu compares deux annonces immobilières françaises. Même bien ou deux biens différents ? "
    'Retourne UNIQUEMENT un JSON : {"same_property": bool, "confidence": 0..1, '
    '"reason": str, "inferred": {"price": number|null, "surface_m2": number|null, '
    '"rooms": integer|null, "address": string|null}}.'
)


def compare_pair(a: Listing, b: Listing, cfg: Any, client: MistralClient) -> dict:
    user = (
        f"ANNONCE A:\n{redact((a.title + ' ' + a.description)[:3000])}\n\n"
        f"ANNONCE B:\n{redact((b.title + ' ' + b.description)[:3000])}"
    )
    return client.complete_json(DEDUP_SYSTEM, user)


def make_ai_decider(
    cfg: Any,
    client: MistralClient,
    cache: Any = None,
    max_pairs: int = 50,
):
    """Retourne decider(a, b) -> bool | None (None = laisser l'heuristique décider).

    Appelle l'API Mistral uniquement pour les paires ambiguës, avec cache et budget.
    """
    budget = {"n": 0}

    def decider(a: Listing, b: Listing) -> bool | None:
        if a.dedup_key == b.dedup_key:
            return None
        sim = title_similarity(a.title, b.title)
        if sim < 0.25 or sim > 0.75:
            return None  # cas clair : l'heuristique suffit
        if budget["n"] >= max_pairs:
            return None
        key = "dedup:" + hashlib.sha256((a.dedup_key + "|" + b.dedup_key).encode()).hexdigest()
        if cache is not None:
            hit = cache.get_cached("ai_cache", key)
            if hit:
                return bool(json.loads(hit)["same_property"])
        budget["n"] += 1
        raw = compare_pair(a, b, cfg, client)
        same = bool(raw.get("same_property"))
        if cache is not None:
            cache.set_cached("ai_cache", key, json.dumps(raw))
        return same

    return decider
