import feedparser

from chasse_logement.sources.rss import listing_from_entry


def test_listing_from_entry(sample_rss):
    feed = feedparser.parse(sample_rss)
    assert len(feed.entries) == 1
    listing = listing_from_entry(
        feed.entries[0], source_id="agence-test.fr", feed_name="Agence Test"
    )
    assert listing.source_id == "agence-test.fr"
    assert listing.external_id == "https://agence-test.fr/annonce/1"
    assert listing.url == "https://agence-test.fr/annonce/1"
    assert listing.price == 950.0
    assert listing.surface_m2 == 45.0
    assert listing.rooms == 2
    assert listing.postcode == "75011"
    assert listing.published_at is not None
    assert listing.published_at.year == 2026
