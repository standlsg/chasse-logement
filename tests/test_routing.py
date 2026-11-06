from chasse_logement.routing import Router


def test_route_hors_trafic():
    def fetch(coords):
        assert coords == "5.4,43.3;5.37,43.296"
        return {"code": "Ok", "routes": [{"duration": 540.0, "distance": 3200.0}]}

    r = Router(fetch=fetch).route_hors_trafic(43.3, 5.4, 43.296, 5.37)
    assert r is not None
    assert r["duration_min"] == 9
    assert r["distance_km"] == 3.2
    assert "hors trafic" in r["label"]


def test_route_no_route():
    r = Router(fetch=lambda c: {"code": "NoRoute", "routes": []}).route_hors_trafic(1, 2, 3, 4)
    assert r is None
