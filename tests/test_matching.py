from chasse_logement.config import Criteria
from chasse_logement.matching import evaluate, matches, score


def base_criteria(**overrides) -> Criteria:
    base = dict(
        budget_max=1000.0, min_surface_m2=30.0, min_rooms=2, postcodes=["75011"], min_score=0.0
    )
    base.update(overrides)
    return Criteria(**base)


def test_matches_ok(make_listing):
    ok, failed = matches(make_listing(), base_criteria())
    assert ok and failed == []


def test_budget_includes_charges(make_listing):
    listing = make_listing(price=980.0, charges=50.0)
    ok, failed = matches(listing, base_criteria())
    assert not ok and any("budget" in f for f in failed)


def test_surface_filter(make_listing):
    ok, failed = matches(make_listing(surface_m2=20.0), base_criteria())
    assert not ok and any("surface" in f for f in failed)


def test_rooms_filter(make_listing):
    ok, failed = matches(make_listing(rooms=1), base_criteria())
    assert not ok and any("pièces" in f for f in failed)


def test_postcode_filter(make_listing):
    ok, failed = matches(make_listing(postcode="75020"), base_criteria())
    assert not ok and any("postal" in f for f in failed)


def test_radius_filter(make_listing):
    criteria = Criteria(
        budget_max=2000.0,
        center_latitude=48.8566,
        center_longitude=2.3522,
        radius_km=5.0,
        min_score=0.0,
    )
    near = make_listing(latitude=48.86, longitude=2.36)
    far = make_listing(latitude=45.76, longitude=4.83)  # Lyon
    assert matches(near, criteria)[0]
    ok, failed = matches(far, criteria)
    assert not ok and any("rayon" in f for f in failed)


def test_exclude_keywords(make_listing):
    criteria = base_criteria(exclude_keywords=["arnaque"])
    ok, failed = matches(make_listing(title="Super appart arnaque 75011"), criteria)
    assert not ok and any("arnaque" in f for f in failed)


def test_furnished_filter(make_listing):
    criteria = base_criteria(furnished=False)
    assert not matches(make_listing(furnished=True), criteria)[0]
    assert matches(make_listing(furnished=False), criteria)[0]


def test_score_bounds_and_reasons(make_listing):
    s, reasons = score(make_listing(), [make_listing(price=1200.0, surface_m2=40.0)])
    assert 0 <= s <= 100
    assert reasons


def test_evaluate_min_score(make_listing):
    criteria = base_criteria(min_score=101.0)
    assert evaluate(make_listing(), criteria, []) is None
    criteria = base_criteria(min_score=0.0)
    res = evaluate(make_listing(), criteria, [])
    assert res is not None and res.listing.external_id == "1"
