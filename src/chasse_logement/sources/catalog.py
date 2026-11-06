"""Catalogue de sources curatées par région.

Région « aix-marseille » : marché locatif de la Métropole Aix-Marseille-Provence (13).
- portals : portails avec alerte email (à activer dans la boîte dédiée)
- agencies : agences locales (leurs annonces passent surtout par les portails ;
  détecter un flux RSS propre avec `chasse-logement discover <site>`)
- manual : dispositifs à suivre manuellement (compte requis, pas d'API publique)
"""

from __future__ import annotations

CATALOGS: dict[str, dict] = {
    "aix-marseille": {
        "label": "Aix-en-Provence / Marseille — Métropole Aix-Marseille-Provence (13)",
        "postcodes": [
            "13001",
            "13002",
            "13003",
            "13004",
            "13005",
            "13006",
            "13007",
            "13008",
            "13009",
            "13010",
            "13011",
            "13012",
            "13013",
            "13014",
            "13015",
            "13016",
            "13080",
            "13090",
            "13100",
            "13120",
            "13127",
            "13170",
            "13290",
            "13300",
            "13330",
            "13400",
            "13420",
            "13500",
            "13530",
            "13600",
            "13610",
            "13800",
            "13880",
        ],
        "portals": [
            "leboncoin",
            "seloger",
            "pap",
            "bienici",
            "logic-immo",
            "gensdeconfiance",
            "appartager",
            "studapart",
        ],
        "rss_feeds": [],
        "agencies": [
            {
                "name": "Orpi Marseille (réseau coop., 50+ points de vente)",
                "site": "https://www.orpi.com/agences-immobilieres-marseille/",
            },
            {
                "name": "Orpi Aix-en-Provence",
                "site": "https://www.orpi.com/agences-immobilieres-aix-en-provence/",
            },
            {
                "name": "Century 21 Aix-en-Provence (marché technopôle Arbois)",
                "site": "https://www.century21.fr/",
            },
            {"name": "Foncia Marseille Prado / Aix-en-Provence", "site": "https://www.foncia.com/"},
            {"name": "Laforêt Marseille (1er, 7e…)", "site": "https://www.laforet.com/"},
            {
                "name": "Stéphane Plaza Immobilier Marseille 6e",
                "site": "https://www.stephaneprazaimmobilier-marseille.com/",
            },
            {"name": "SAFTI Marseille", "site": "https://www.safti.fr/"},
            {
                "name": "SGL Immo (Aix-Marseille, 13)",
                "site": "https://sgl-immo.com/agence-immobiliere-marseille/",
            },
            {
                "name": "Immobilière du Palais (Aix-en-Provence)",
                "site": "https://www.immobilieredupalais.net/",
            },
            {"name": "La Comtesse (Marseille 6/9/12 + Aix)", "site": "https://www.lacomtesse.fr/"},
            {"name": "Agence MJB (Aix-en-Provence)", "site": "https://mjb-immobilier.com/fr/"},
            {
                "name": "Annuaires : FNAIM Aix (51 agences)",
                "site": "https://www.fnaim.fr/agences-immobilieres/43-aix-en-provence-13090.htm",
            },
            {
                "name": "Annuaire SeLoger Aix (178 pros)",
                "site": "https://www.seloger.com/annuaire/aix-en-provence-13100/",
            },
            {
                "name": "Annuaire Monbien Aix (99 agences)",
                "site": "https://www.monbien.fr/agence-immobiliere/13/aix-en-provence",
            },
            {"name": "Annuaire agences aix.fr", "site": "https://www.aix.fr/immobilier/agences/"},
        ],
        "agencies_note": (
            "Aussi à Aix/Marseille (voir annuaires ci-dessus) : Immobilière Pujol, Homki, "
            "A La Lucarne, Guis Immobilier, La Marseillaise d'Immobilier, Mychezmoi, "
            "CRYZA Immobilier (Les Milles)."
        ),
        "manual": [
            {
                "name": "CROUS Aix-Marseille (26 résidences, 220-380 €/mois)",
                "url": "https://www.crous-aix-marseille.fr/",
                "why": "Dossier Social Étudiant requis, pas d'API",
            },
            {
                "name": "Lokaviz (chez l'habitant, gratuit, compte INE étudiant)",
                "url": "https://www.lokaviz.fr/",
                "why": "compte étudiant requis",
            },
            {
                "name": "Studapart (partenaire AMU, +120 000 logements vérifiés)",
                "url": "https://www.studapart.com/",
                "why": "alerte email possible ; aussi en portail IMAP",
            },
            {
                "name": "Action Logement — plateforme logement (salariés du privé éligibles)",
                "url": "https://logement-actionlogement.fr/search",
                "why": "compte + éligibilité requis",
            },
            {
                "name": "AL'in — logement social Action Logement",
                "url": "https://www.actionlogement.fr/le-logement-social",
                "why": "demande en ligne, pas d'annonces temps réel",
            },
            {
                "name": "In'li — logements à prix maîtrisé, Bouches-du-Rhône (13)",
                "url": "https://www.inli.fr/locations/offres/bouches-du-rhone_d:13",
                "why": "compte requis",
            },
            {
                "name": "demande-logement-social.gouv.fr (HLM : Marseille Habitat…)",
                "url": "https://www.demande-logement-social.gouv.fr/",
                "why": "demande + file d'attente",
            },
            {
                "name": "Colocations Aix/Marseille : La Carte des Colocs, Appartager, Locservice…",
                "url": "https://www.lacartedescolocs.fr/",
                "why": "alertes email possibles sur Appartager",
            },
            {
                "name": "Mairie d'Aix — page Offre de logements (liens CROUS, colocs…)",
                "url": "https://www.aixenprovence.fr/Offre-de-logements-2795",
                "why": "portail d'information",
            },
        ],
    }
}


def apply_catalog(raw: dict, region: str, apply_postcodes: bool = True) -> dict:
    """Fusionne le catalogue régional dans la config brute (union, sans doublons)."""
    reg = CATALOGS[region]
    sources = raw.setdefault("sources", {})
    imap = sources.setdefault("imap", {})
    portals = list(imap.get("portals") or [])
    for p in reg["portals"]:
        if p not in portals:
            portals.append(p)
    imap["portals"] = portals
    feeds = sources.setdefault("rss_feeds", [])
    existing = {f.get("url") for f in feeds}
    for f in reg.get("rss_feeds", []):
        if f["url"] not in existing:
            feeds.append({"name": f["name"], "url": f["url"], "enabled": True})
    if apply_postcodes:
        criteria = raw.setdefault("criteria", {})
        cps = list(criteria.get("postcodes") or [])
        for c in reg["postcodes"]:
            if c not in cps:
                cps.append(c)
        criteria["postcodes"] = cps
    return raw
