from chasse_logement.ai.signals import Signals
from chasse_logement.config import (
    AiConfig,
    AppConfig,
    CommuteConfig,
    Criteria,
    EnrichmentConfig,
    NotifyConfig,
    NotifyEmailConfig,
    SourcesConfig,
)
from chasse_logement.models import SourceKind
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


def make_cfg(tmp_path, min_rooms=4) -> AppConfig:
    return AppConfig(
        database_path=str(tmp_path / "t.db"),
        criteria=Criteria(
            budget_max=3000.0,
            min_surface_m2=0,
            min_rooms=min_rooms,
            postcodes=["13100"],
            min_score=0.0,
        ),
        sources=SourcesConfig(),
        notify=NotifyConfig(email=NotifyEmailConfig(enabled=False)),
        enrichment=EnrichmentConfig(geocode=False, poi=False),
        commute=CommuteConfig(enabled=False),
        ai=AiConfig(provider="mistral", api_key="k", run_signals=True, run_dedup=False),
    )


def test_ai_office_counts_as_room(tmp_path, monkeypatch, make_listing):
    """« 3 pièces + bureau à la cave » (IA) doit passer un filtre min_rooms=4."""
    cfg = make_cfg(tmp_path, min_rooms=4)
    listing = make_listing(
        external_id="1",
        url="https://x/1",
        source_id="leboncoin",
        title="Maison 4 pièces 13100 - 2500 €",
        price=2500.0,
        surface_m2=110.0,
        rooms=3,
        postcode="13100",
        description="Maison avec bureau aménagé à la cave",
    )
    monkeypatch.setattr(
        "chasse_logement.pipeline.build_sources", lambda c, client: [FakeSource([listing])]
    )
    monkeypatch.setattr(
        "chasse_logement.pipeline.extract_signals",
        lambda text, cfg, client=None, cache=None: Signals(
            has_office=True, office_location="cave", evidence=["bureau aménagé à la cave"]
        ),
    )
    notifier = FakeNotifier()
    stats = run_once(cfg, notifier=notifier, client=object())
    assert stats["matches"] == 1
    prop = notifier.digests[0][1][0].listing
    assert prop.signals["has_office"] is True
    assert prop.rooms_effective == 4


def test_without_ai_office_does_not_pass(tmp_path, monkeypatch, make_listing):
    cfg = make_cfg(tmp_path, min_rooms=4)
    listing = make_listing(
        external_id="1",
        url="https://x/1",
        rooms=3,
        postcode="13100",
        price=2500.0,
        surface_m2=110.0,
        title="Maison 4 pièces 13100 - 2500 €",
    )
    monkeypatch.setattr(
        "chasse_logement.pipeline.build_sources", lambda c, client: [FakeSource([listing])]
    )
    monkeypatch.setattr(
        "chasse_logement.pipeline.extract_signals",
        lambda text, cfg, client=None, cache=None: Signals(),
    )
    stats = run_once(cfg, notifier=FakeNotifier(), client=object())
    assert stats["matches"] == 0
