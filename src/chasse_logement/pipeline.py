from __future__ import annotations

from .config import AppConfig
from .geocoding import Geocoder, address_query
from .http import PoliteClient
from .matching import MatchResult, evaluate
from .merge import build_property, cluster
from .models import Listing, Property
from .notify import Notifier, build_notifier
from .redflags import red_flags
from .sources.base import Source
from .sources.imap_alerts import ImapAlertsSource
from .sources.rss import RssSource
from .store import ListingStore


def build_sources(cfg: AppConfig, client: PoliteClient) -> list[Source]:
    sources: list[Source] = []
    if cfg.sources.imap.enabled:
        imap = cfg.sources.imap
        sources.append(
            ImapAlertsSource(
                host=imap.host,
                port=imap.port,
                user=imap.user,
                password=imap.password,
                mailbox=imap.mailbox,
                since_days=imap.since_days,
                portals=imap.portals,
            )
        )
    for feed in cfg.sources.rss_feeds:
        if not feed.enabled:
            continue
        sources.append(RssSource(feed.name, feed.url, client=client))
    return sources


def rebuild_properties(store: ListingStore) -> list[Property]:
    """Reclusterise toutes les annonces en biens (Property) fusionnés cross-sources."""
    return [build_property(group) for group in cluster(store.all_listings())]


def run_once(
    cfg: AppConfig,
    notifier: Notifier | None = None,
    client: PoliteClient | None = None,
) -> dict:
    """Une tournée : collecte → dédup → fusion en biens → matching → notification
    (uniquement les nouveaux biens) → stats."""
    own_client = client is None
    client = client or PoliteClient(
        user_agent=cfg.http.user_agent,
        min_interval_s=cfg.http.min_interval_s,
        respect_robots=cfg.http.respect_robots,
        timeout_s=cfg.http.timeout_s,
    )
    if notifier is None:
        notifier = build_notifier(cfg.notify)
    store = ListingStore(cfg.database_path)
    try:
        sources = build_sources(cfg, client)
        stats: dict = {
            "sources": len(sources),
            "collected": 0,
            "new": 0,
            "properties": 0,
            "new_properties": 0,
            "matches": 0,
            "notified": False,
        }
        fresh: list[Listing] = []
        seen_keys: set[str] = set()
        for src in sources:
            try:
                for listing in src.collect():
                    stats["collected"] += 1
                    key = listing.dedup_key
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    if store.save(listing):
                        stats["new"] += 1
                        fresh.append(listing)
            except Exception as exc:  # noqa: BLE001 - une source en panne ne bloque pas la tournée
                stats.setdefault("source_errors", {})[src.name] = str(exc)
        if fresh:
            props = rebuild_properties(store)
            stats["properties"] = len(props)
            pool = store.recent_pool(days=30)
            pool_ppm = [lst.price_per_m2 for lst in pool if lst.price_per_m2]
            geocoder = Geocoder(cache=store) if cfg.enrichment.geocode else None
            new_matches: list[MatchResult] = []
            for prop in props:
                existing = store.get_property(prop.prop_id)
                is_new = existing is None
                if is_new:
                    stats["new_properties"] += 1
                prop.red_flags = red_flags(prop, pool_ppm)
                if is_new and geocoder is not None and prop.latitude is None:
                    geo = geocoder.geocode(address_query(prop))
                    if geo is not None:
                        prop.latitude = geo.latitude
                        prop.longitude = geo.longitude
                        prop.address_label = geo.label
                        prop.address_precision = geo.precision
                if is_new:
                    res = evaluate(prop, cfg.criteria, pool)
                    if res is not None:
                        prop.score = res.score
                        new_matches.append(res)
                store.save_property(prop, notified=bool(existing.notified) if existing else False)
            new_matches.sort(key=lambda r: r.score, reverse=True)
            stats["matches"] = len(new_matches)
            if new_matches and notifier is not None:
                subject = f"[chasse-logement] {len(new_matches)} nouveau(x) bien(s)"
                if cfg.notify.mode == "instant":
                    for res in new_matches:
                        notifier.send_digest(f"[chasse-logement] bien {res.score:.0f}/100", [res])
                else:
                    notifier.send_digest(subject, new_matches)
                for res in new_matches:
                    if isinstance(res.listing, Property):
                        store.save_property(res.listing, notified=True)
                stats["notified"] = True
        return stats
    finally:
        store.close()
        if own_client:
            client.close()
