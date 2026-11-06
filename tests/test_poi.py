from chasse_logement.poi import PoiExplorer

OVERPASS_RESP = {
    "elements": [
        {"tags": {"name": "École Jean Jaurès", "amenity": "school"}, "lat": 43.3001, "lon": 5.4},
        {
            "tags": {"name": "Carrefour City", "shop": "supermarket"},
            "center": {"lat": 43.3002, "lon": 5.4001},
        },
        {
            "tags": {"name": "Métro Vieux-Port", "public_transport": "station"},
            "lat": 43.296,
            "lon": 5.37,
        },
        {"tags": {"name": "Pizzeria du Port", "amenity": "restaurant"}, "lat": 43.3, "lon": 5.4},
    ]
}


def test_nearby_classifies_and_sorts_by_distance():
    explorer = PoiExplorer(fetch=lambda q: OVERPASS_RESP, radius_m=800)
    res = explorer.nearby(43.3, 5.4)
    assert res is not None
    assert res["écoles"][0]["name"] == "École Jean Jaurès"
    assert res["commerces"][0]["name"] == "Carrefour City"
    assert res["transports"][0]["name"] == "Métro Vieux-Port"
    assert res["restaurants"][0]["name"] == "Pizzeria du Port"
    assert all("distance_m" in item for cat in res.values() for item in cat)
    distances = [item["distance_m"] for item in res["écoles"]]
    assert distances == sorted(distances)


def test_nearby_http_error():
    explorer = PoiExplorer(fetch=lambda q: None)
    assert explorer.nearby(43.3, 5.4) is None
