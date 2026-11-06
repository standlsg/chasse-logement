from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field


class SourceKind(StrEnum):
    IMAP_ALERT = "imap_alert"
    RSS = "rss"
    API = "api"
    HTML = "html"


class ListingType(StrEnum):
    APARTMENT = "appartement"
    HOUSE = "maison"
    STUDIO = "studio"
    ROOM = "chambre"
    SHARED = "colocation"
    OTHER = "autre"


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_url(url: str) -> str:
    """Retire les paramètres de tracking pour stabiliser la clé de déduplication."""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class Listing(BaseModel):
    """Annonce normalisée, quelle que soit la source."""

    source_id: str
    source_kind: SourceKind
    external_id: str
    url: str = ""
    title: str = ""
    price: float | None = None
    charges: float | None = None
    surface_m2: float | None = None
    rooms: int | None = None
    bedrooms: int | None = None
    listing_type: ListingType = ListingType.OTHER
    furnished: bool | None = None
    city: str | None = None
    postcode: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str = ""
    photos: list[str] = Field(default_factory=list)
    publisher: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)

    @property
    def price_per_m2(self) -> float | None:
        if self.price and self.surface_m2 and self.surface_m2 > 0:
            return round(self.price / self.surface_m2, 2)
        return None

    @property
    def total_price(self) -> float | None:
        if self.price is None:
            return None
        return self.price + (self.charges or 0.0)

    @property
    def dedup_key(self) -> str:
        if self.url:
            return hashlib.sha256(normalize_url(self.url).encode()).hexdigest()[:32]
        raw = "|".join(
            [
                self.source_id,
                (self.title or "").strip().casefold(),
                str(self.price),
                str(self.surface_m2),
                self.postcode or "",
            ]
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
