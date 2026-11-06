"""Red flags « à vérifier » sur un bien (arnaques à la location et incohérences)."""

from __future__ import annotations

from statistics import median

from .models import Property

SCAM_KEYWORDS = [
    "western union",
    "moneygram",
    "mandat cash",
    "paiement avant la visite",
    "paiement avant visite",
    "virement avant",
    "envoyez l'argent",
    "envoyer l'argent",
    "propriétaire à l'étranger",
    "je suis à l'étranger",
    "réservation à distance",
    "paiement à distance",
    "livraison des clés",
]


def red_flags(prop: Property, pool_ppm: list[float]) -> list[str]:
    flags: list[str] = []
    for inc in prop.inconsistencies:
        flags.append(f"incohérence entre sources : {inc}")
    ppm = prop.price_per_m2
    if ppm and pool_ppm:
        med = median(pool_ppm)
        if med > 0 and ppm < 0.6 * med:
            flags.append(
                f"prix/m² très sous le marché ({ppm:.0f} € vs médiane suivie {med:.0f} €) "
                "— arnaque classique à la location"
            )
        elif med > 0 and ppm > 2.0 * med:
            flags.append(f"prix/m² très au-dessus du marché ({ppm:.0f} € vs {med:.0f} €)")
    text = f"{prop.title} {prop.description}".casefold()
    for kw in SCAM_KEYWORDS:
        if kw.casefold() in text:
            flags.append(f"formulation suspecte dans l'annonce : « {kw} »")
    if not prop.sources:
        flags.append("aucun lien de source disponible")
    return flags
