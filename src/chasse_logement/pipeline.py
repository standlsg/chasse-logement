from __future__ import annotations

from .config import AppConfig
from .http import PoliteClient
from .matching import MatchResult, evaluate
from .models import Listing
from .notify import Notifier, build_notifier
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
            )
        )
    for feed in cfg.sources.rss_feeds:
        sources.append(RssSource(feed.name, feed.url, client=client))
    return sources


def run_once(
    cfg: AppConfig,
    notifier: Notifier | None = None,
    client: PoliteClient | None = None,
) -> dict:
    """Une tournée : collecte → dédup → matching → notification. Retourne des stats."""
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
            "matches": 0,
            "notified": False,
        }
        fresh: list[Listing] = []
        seen_keys: set[str] = set()
        for src in sources:
            for listing in src.collect():
                stats["collected"] += 1
                key = listing.dedup_key
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                if store.save(listing):
                    stats["new"] += 1
                    fresh.append(listing)
        pool = store.recent_pool(days=30) + fresh
        results: list[MatchResult] = []
        for listing in fresh:
            res = evaluate(listing, cfg.criteria, pool)
            if res is not None:
                results.append(res)
        results.sort(key=lambda r: r.score, reverse=True)
        stats["matches"] = len(results)
        if results and notifier is not None:
            subject = f"[chasse-logement] {len(results)} nouvelle(s) annonce(s)"
            if cfg.notify.mode == "instant":
                for res in results:
                    notifier.send_digest(f"[chasse-logement] annonce {res.score:.0f}/100", [res])
            else:
                notifier.send_digest(subject, results)
            store.mark_notified([r.listing.dedup_key for r in results])
            stats["notified"] = True
        return stats
    finally:
        store.close()
        if own_client:
            client.close()
