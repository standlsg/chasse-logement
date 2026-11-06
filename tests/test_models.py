from chasse_logement.models import SourceKind, normalize_url


def test_price_per_m2(make_listing):
    listing = make_listing(price=900.0, surface_m2=40.0)
    assert listing.price_per_m2 == 22.5


def test_price_per_m2_missing():
    from chasse_logement.models import Listing

    listing = Listing(source_id="t", source_kind=SourceKind.RSS, external_id="x")
    assert listing.price_per_m2 is None
    assert listing.total_price is None


def test_dedup_key_stable_by_url(make_listing):
    a = make_listing(url="https://x.fr/a/1")
    b = make_listing(url="https://x.fr/a/1")
    c = make_listing(url="https://x.fr/a/2")
    assert a.dedup_key == b.dedup_key
    assert a.dedup_key != c.dedup_key


def test_dedup_key_ignores_tracking_params():
    assert normalize_url("https://x.fr/a/1?utm_source=mail&utm_campaign=x") == "https://x.fr/a/1"


def test_total_price_includes_charges(make_listing):
    listing = make_listing(price=900.0, charges=50.0)
    assert listing.total_price == 950.0
