from __future__ import annotations

import pytest

from chasse_logement.models import Listing, SourceKind

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Agence Test</title>
    <link>https://agence-test.fr</link>
    <item>
      <title>Appartement 2 pièces 45 m² - 950 € - 75011 Paris</title>
      <link>https://agence-test.fr/annonce/1</link>
      <guid>https://agence-test.fr/annonce/1</guid>
      <description>Bel appartement lumineux proche métro.</description>
      <pubDate>Mon, 03 Nov 2026 10:00:00 +0100</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_EMAIL = b"""From: alertes@leboncoin.fr
Subject: =?UTF-8?Q?Nouvelle_annonce_=3A_2_pi=C3=A8ces_45_m=C2=B2_-_950_=E2=82=AC?=
Message-ID: <abc123@leboncoin.fr>
Content-Type: text/html; charset="utf-8"

<html><body><p>Une nouvelle annonce :</p>
<a href="https://www.leboncoin.fr/annonces/123456789.html?utm_source=alert">Voir l'annonce</a>
</body></html>
"""


@pytest.fixture
def sample_rss() -> str:
    return SAMPLE_RSS


@pytest.fixture
def sample_email() -> bytes:
    return SAMPLE_EMAIL


@pytest.fixture
def make_listing():
    def _make(**overrides) -> Listing:
        base = dict(
            source_id="test",
            source_kind=SourceKind.RSS,
            external_id="1",
            url="https://agence-test.fr/annonce/1",
            title="Appartement 2 pièces 40 m² 75011 - 900 €",
            price=900.0,
            surface_m2=40.0,
            rooms=2,
            postcode="75011",
        )
        base.update(overrides)
        return Listing(**base)

    return _make
