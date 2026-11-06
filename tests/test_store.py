from datetime import UTC, datetime

from chasse_logement.store import ListingStore


def test_save_dedup(tmp_path, make_listing):
    store = ListingStore(tmp_path / "t.db")
    assert store.save(make_listing()) is True
    assert store.save(make_listing()) is False
    assert store.count() == 1
    store.close()


def test_recent_pool_and_notified(tmp_path, make_listing):
    store = ListingStore(tmp_path / "t.db")
    listing = make_listing()
    store.save(listing)
    pool = store.recent_pool(days=30)
    assert len(pool) == 1 and pool[0].external_id == "1"
    store.mark_notified([(listing.dedup_key, 80.0, "[]")])
    assert store.stats() == {"total": 1, "notified": 1, "properties": 0}
    matches = store.recent_matches()
    assert matches[0]["score"] == 80.0
    store.close()


def test_purge_old_listings(tmp_path, make_listing):
    store = ListingStore(tmp_path / "t.db")
    old = make_listing(first_seen_at=datetime(2020, 1, 1, tzinfo=UTC))
    store.save(old)
    store.save(make_listing(external_id="2", url="https://x.fr/2"))
    res = store.purge(days=90)
    assert res["listings_deleted"] == 1
    assert store.count() == 1
    store.close()
