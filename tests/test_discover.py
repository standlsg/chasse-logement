from chasse_logement.discover import discover_rss, looks_like_feed


class FakeRobots:
    def __init__(self, allowed=True):
        self.allowed_flag = allowed

    def allowed(self, url, user_agent="*"):
        return self.allowed_flag


class FakeClient:
    def __init__(self, feeds, robots_allowed=True):
        self.robots = FakeRobots(robots_allowed)
        self.user_agent = "test"
        self._feeds = feeds

    def get_text(self, url):
        return self._feeds.get(url)


def test_looks_like_feed():
    assert looks_like_feed('<?xml version="1.0"?><rss version="2.0">')
    assert looks_like_feed("<feed xmlns='http://www.w3.org/2005/Atom'>")
    assert not looks_like_feed("<html><body>page</body></html>")


def test_discover_finds_rss():
    client = FakeClient({"https://agence-x.fr/rss.xml": "<rss version='2.0'></rss>"})
    assert discover_rss("https://agence-x.fr/", client=client) == ["https://agence-x.fr/rss.xml"]


def test_discover_respects_robots():
    client = FakeClient(
        {"https://agence-x.fr/rss.xml": "<rss version='2.0'></rss>"}, robots_allowed=False
    )
    assert discover_rss("https://agence-x.fr/", client=client) == []


def test_discover_none():
    client = FakeClient({"https://agence-x.fr/": "<html></html>"})
    assert discover_rss("https://agence-x.fr/", client=client) == []
