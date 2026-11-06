from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import feedparser

from ..http import PoliteClient
from ..models import Listing, SourceKind
from .parsing import extract_postcode, extract_price, extract_rooms, extract_surface


def _entry_datetime(entry: Any, key: str) -> datetime | None:
    parsed = entry.get(key)
    if parsed:
        return datetime(*parsed[:6], tzinfo=UTC)
    return None


def listing_from_entry(entry: Any, source_id: str, feed_name: str) -> Listing:
    title = str(entry.get("title", ""))
    link = str(entry.get("link", ""))
    description = str(entry.get("summary", "") or entry.get("description", ""))
    text = f"{title}\n{description}"
    photos = [
        str(link_.get("href"))
        for link_ in entry.get("links", [])
        if link_.get("rel") == "enclosure" and "image" in str(link_.get("type", ""))
    ]
    published = _entry_datetime(entry, "published_parsed") or _entry_datetime(
        entry, "updated_parsed"
    )
    return Listing(
        source_id=source_id,
        source_kind=SourceKind.RSS,
        external_id=str(entry.get("id") or link or entry.get("title", "")),
        url=link,
        title=title,
        price=extract_price(text),
        surface_m2=extract_surface(text),
        rooms=extract_rooms(text),
        postcode=extract_postcode(text),
        description=description[:2000],
        photos=photos,
        publisher=feed_name,
        published_at=published,
    )


class RssSource:
    """Lit un flux RSS/Atom publié volontairement par une agence."""

    kind = SourceKind.RSS

    def __init__(self, name: str, feed_url: str, client: PoliteClient | None = None) -> None:
        self.name = name
        self.feed_url = feed_url
        self.source_id = urlsplit(feed_url).netloc
        self._client = client or PoliteClient()

    def collect(self) -> Iterator[Listing]:
        text = self._client.get_text(self.feed_url)
        if not text:
            return
        feed = feedparser.parse(text)
        for entry in feed.entries:
            yield listing_from_entry(entry, source_id=self.source_id, feed_name=self.name)
