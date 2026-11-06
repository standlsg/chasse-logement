"""Connecteur API d'agrégation commerciale (ex. MoteurImmo, Melo/Stream Estate, Yanport).

Accès légal sous contrat (pas de scraping). Le connecteur est générique et configurable :
base_url, path, nom du header d'auth, chemin de la liste de résultats, et mapping tolérant
des champs (plusieurs clés candidates testées). À ajuster selon la doc du fournisseur
(ex. MoteurImmo : moteurimmo.fr/offre-api, facturation à l'annonce, freemium).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from ..config import ApiAggregatorConfig, Criteria
from ..models import Listing, SourceKind
from ..sources.parsing import _to_float

FIELD_CANDIDATES: dict[str, list[str]] = {
    "title": ["title", "titre", "name", "intitule"],
    "price": ["price", "prix", "loyer", "prix_mois", "amount", "prix_total"],
    "charges": ["charges", "price_charges", "charges_mensuelles", "cc"],
    "surface": ["surface", "surface_m2", "surfaceM2", "area", "m2", "superficie"],
    "rooms": ["rooms", "nb_pieces", "pieces", "nbRooms", "nb_pieces_total"],
    "postcode": ["postcode", "code_postal", "cp", "zip", "zipcode", "codePostal"],
    "city": ["city", "ville", "commune", "adresse_ville"],
    "url": ["url", "link", "lien", "href", "annonce_url", "url_annonce"],
    "id": ["id", "uuid", "reference", "ref", "annonce_id"],
    "description": ["description", "desc", "texte", "body", "resume"],
    "published": [
        "published_at",
        "date_publication",
        "date",
        "created_at",
        "published",
        "date_ajout",
    ],
    "photos": ["photos", "images", "pictures", "visuels"],
}


def _pick(item: dict, field: str) -> Any:
    for key in FIELD_CANDIDATES[field]:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return _to_float(value)
        except ValueError:
            return None
    return None


def _photos(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for p in value:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            url = p.get("url") or p.get("src") or p.get("lien")
            if url:
                out.append(str(url))
    return out


def listing_from_api_item(item: dict, source_id: str) -> Listing:
    title = str(_pick(item, "title") or "")
    url = str(_pick(item, "url") or "")
    external_id = str(_pick(item, "id") or url or title)
    rooms = _num(_pick(item, "rooms"))
    return Listing(
        source_id=source_id,
        source_kind=SourceKind.API,
        external_id=external_id,
        url=url,
        title=title,
        price=_num(_pick(item, "price")),
        charges=_num(_pick(item, "charges")),
        surface_m2=_num(_pick(item, "surface")),
        rooms=int(rooms) if rooms is not None else None,
        postcode=str(_pick(item, "postcode") or "") or None,
        city=str(_pick(item, "city") or "") or None,
        description=str(_pick(item, "description") or "")[:2000],
        photos=_photos(_pick(item, "photos")),
        published_at=_parse_date(_pick(item, "published")),
    )


def _dig(data: Any, items_path: str) -> list:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if items_path:
        node = data
        for part in items_path.split("."):
            if not isinstance(node, dict) or part not in node:
                return []
            node = node[part]
        return node if isinstance(node, list) else []
    for key in ("annonces", "items", "results", "data", "listings", "properties"):
        if isinstance(data.get(key), list):
            return data[key]
    return []


class ApiAggregatorSource:
    """Source API d'agrégation (MoteurImmo & co.) : une requête par tournée, critères en query."""

    kind = SourceKind.API

    def __init__(
        self, cfg: ApiAggregatorConfig, criteria: Criteria, name: str = "agregateur-api"
    ) -> None:
        self.name = name
        self.cfg = cfg
        self.criteria = criteria
        self.source_id = urlsplit(cfg.base_url).netloc or name

    def _params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"type": "location", "limit": self.cfg.limit}
        if self.criteria.budget_max:
            params["prix_max"] = self.criteria.budget_max
        if self.criteria.min_surface_m2:
            params["surface_min"] = self.criteria.min_surface_m2
        if self.criteria.min_rooms:
            params["nb_pieces_min"] = self.criteria.min_rooms
        if self.criteria.postcodes:
            params["code_postal"] = ",".join(self.criteria.postcodes)
        elif self.criteria.cities:
            params["ville"] = ",".join(self.criteria.cities)
        params.update(self.cfg.extra_params)
        return params

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "chasse-logement/0.1 (+https://github.com/standlsg/chasse-logement)"
        }
        if self.cfg.bearer:
            headers["Authorization"] = f"Bearer {self.cfg.api_key}"
        else:
            headers[self.cfg.header_name] = self.cfg.api_key
        return headers

    def collect(self):
        if not (self.cfg.enabled and self.cfg.base_url and self.cfg.api_key):
            return
        url = self.cfg.base_url.rstrip("/") + self.cfg.path
        with httpx.Client(timeout=30.0) as http:
            resp = http.get(url, params=self._params(), headers=self._headers())
        if resp.status_code >= 400:
            return
        data = resp.json()
        for item in _dig(data, self.cfg.items_path):
            if isinstance(item, dict):
                yield listing_from_api_item(item, self.source_id)
