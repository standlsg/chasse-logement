from chasse_logement.geo import haversine_km


def test_haversine_paris_lyon():
    d = haversine_km(48.8566, 2.3522, 45.7640, 4.8357)
    assert 380 < d < 410


def test_haversine_same_point():
    assert haversine_km(48.85, 2.35, 48.85, 2.35) == 0.0
