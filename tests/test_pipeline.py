from chasse_logement.config import (
    AppConfig,
    CommuteConfig,
    Criteria,
    EnrichmentConfig,
    NotifyConfig,
    NotifyEmailConfig,
    SourcesConfig,
)
from chasse_logement.models import Property, SourceKind
from chasse_logement.pipeline import run_once


class FakeSource:
    name = "fake"
    kind = SourceKind.RSS

    def __init__(self, listings):
        self._listings = listings

    def collect(self):
        return iter(self._listings)


class FakeNotifier:
    def __init__(self):
        self.digests = []

    def send_digest(self, subject, results):
        self.digests.append((subject, results))


def make_cfg(tmp_path, **criteria_overrides) -> AppConfig:
    base = dict(
        budget_max=1000.0, min_surface_m2=30.0, min_rooms=2, postcodes=["75011"], min_score=0.0
    )
    base.update(criteria_overrides)
    return AppConfig(
        database_path=str(tmp_path / "t.db"),
        criteria=Criteria(**base),
        sources=SourcesConfig(),
        notify=NotifyConfig(email=NotifyEmailConfig(enabled=False)),
        enrichment=EnrichmentConfig(geocode=False, poi=False),
        commute=CommuteConfig(enabled=False),
    )


def run_with(monkeypatch, cfg, listings, notifier):
    monkeypatch.setattr(
        "chasse_logement.pipeline.build_sources", lambda c, client: [FakeSource(listings)]
    )
    return run_once(cfg, notifier=notifier, client=object())


def test_run_once_filters_and_notifies(tmp_path, monkeypatch, make_listing):
    cfg = make_cfg(tmp_path)
    good = make_listing(external_id="g", url="https://x.fr/g", price=900.0)
    too_expensive = make_listing(external_id="b", url="https://x.fr/b", price=5000.0)
    notifier = FakeNotifier()
    stats = run_with(monkeypatch, cfg, [good, too_expensive], notifier)
    assert stats["collected"] == 2
    assert stats["new"] == 2
    assert stats["properties"] == 2
    assert stats["matches"] == 1
    assert stats["notified"] is True
    assert len(notifier.digests) == 1
    result = notifier.digests[0][1][0]
    assert isinstance(result.listing, Property)
    assert result.listing.price == 900.0


def test_run_once_merges_cross_source_into_one_property(tmp_path, monkeypatch, make_listing):
    cfg = make_cfg(tmp_path)
    a = make_listing(
        external_id="a",
        url="https://leboncoin.fr/a/1",
        source_id="leboncoin",
        title="Appartement 2 pièces 40 m² 75011 - 900 €",
        price=900.0,
    )
    b = make_listing(
        external_id="b",
        url="https://www.seloger.com/b/2",
        source_id="seloger",
        title="Appartement 2 pièces 40 m² 75011 - 920 €",
        price=920.0,
    )
    notifier = FakeNotifier()
    stats = run_with(monkeypatch, cfg, [a, b], notifier)
    assert stats["collected"] == 2
    assert stats["properties"] == 1
    assert stats["new_properties"] == 1
    assert stats["matches"] == 1
    prop = notifier.digests[0][1][0].listing
    assert isinstance(prop, Property)
    assert len(prop.sources) == 2
    assert {s.source_id for s in prop.sources} == {"leboncoin", "seloger"}
    assert any("prix" in inc for inc in prop.inconsistencies)
    assert prop.red_flags  # incohérence entre sources remontée en red flag


def test_run_once_second_pass_no_duplicates(tmp_path, monkeypatch, make_listing):
    cfg = make_cfg(tmp_path)
    listing = make_listing()
    notifier = FakeNotifier()
    run_with(monkeypatch, cfg, [listing], notifier)
    stats2 = run_with(monkeypatch, cfg, [listing], notifier)
    assert stats2["new"] == 0
    assert stats2["matches"] == 0
    assert stats2["notified"] is False
    assert len(notifier.digests) == 1


def test_run_once_no_notifier_configured(tmp_path, monkeypatch, make_listing):
    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(
        "chasse_logement.pipeline.build_sources", lambda c, client: [FakeSource([make_listing()])]
    )
    monkeypatch.setattr("chasse_logement.pipeline.build_notifier", lambda n: None)
    stats = run_once(cfg, client=object())
    assert stats["matches"] == 1
    assert stats["notified"] is False


def test_run_once_source_error_does_not_crash(tmp_path, monkeypatch, make_listing):
    class BrokenSource:
        name = "broken"
        kind = SourceKind.RSS

        def collect(self):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    cfg = make_cfg(tmp_path)
    monkeypatch.setattr(
        "chasse_logement.pipeline.build_sources", lambda c, client: [BrokenSource()]
    )
    stats = run_once(cfg, notifier=FakeNotifier(), client=object())
    assert stats["source_errors"] == {"broken": "boom"}
    assert stats["collected"] == 0
