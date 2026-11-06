"""IA-3 : évaluation du risque d'arnaque + cohérence cross-sources (provider Mistral).

Complète les red flags heuristiques (redflags.py) : le modèle lit le texte de l'annonce
(déjà redacté) + le résumé des valeurs par source et renvoie un risque 0..1 + raisons.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from .redact import redact
from .signals import MistralClient

RISK_SYSTEM = (
    "Tu es un expert anti-arnaque pour la location immobilière en France. On te donne le texte "
    "d'une annonce (données perso redactées) et un résumé des valeurs vues sur chaque source. "
    'Retourne UNIQUEMENT un JSON : {"scam_risk": 0..1, "reasons": [str], "summary": str}. '
    "Signaux d'arnaque : paiement avant visite, western union/moneygram, proprio à l'étranger, "
    "prix très sous le marché, pression temporelle, contact par email étranger uniquement. "
    "Incohérences fortes entre sources (prix/surface/pièces) montent aussi le risque."
)


class RiskAssessment(BaseModel):
    scam_risk: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    summary: str = ""


def assess_property(
    prop_text: str,
    sources_summary: str,
    cfg: Any,
    client: MistralClient,
    cache: Any = None,
) -> RiskAssessment:
    cleaned = redact(prop_text or "")[:6000]
    cache_key = "risk:" + hashlib.sha256((cleaned + "|" + sources_summary).encode()).hexdigest()
    if cache is not None:
        hit = cache.get_cached("ai_cache", cache_key)
        if hit:
            return RiskAssessment.model_validate(json.loads(hit))
    user = f"ANNONCE:\n{cleaned}\n\nVALEURS PAR SOURCE:\n{sources_summary}"
    raw = client.complete_json(RISK_SYSTEM, user)
    risk = RiskAssessment.model_validate(raw)
    risk.scam_risk = max(0.0, min(1.0, risk.scam_risk))
    if cache is not None:
        cache.set_cached("ai_cache", cache_key, risk.model_dump_json())
    return risk
