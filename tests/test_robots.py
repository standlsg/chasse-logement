from chasse_logement.robots import RobotsChecker

ROBOTS = "User-agent: *\nDisallow: /admin\nDisallow: /private/\n"


def fake_fetch(url: str) -> str | None:
    if url.endswith("/robots.txt"):
        return ROBOTS
    return None


def test_robots_allows_public_paths():
    checker = RobotsChecker(fetch=fake_fetch)
    assert checker.allowed("https://example.com/annonces/1", "*")


def test_robots_blocks_disallowed():
    checker = RobotsChecker(fetch=fake_fetch)
    assert not checker.allowed("https://example.com/admin/panel", "*")
    assert not checker.allowed("https://example.com/private/x", "*")


def test_robots_missing_file_allows_all():
    checker = RobotsChecker(fetch=lambda url: None)
    assert checker.allowed("https://no-robots.example/anything", "*")


def test_robots_cached_per_host():
    calls = []

    def fetch(url: str) -> str | None:
        calls.append(url)
        return ROBOTS

    checker = RobotsChecker(fetch=fetch)
    checker.allowed("https://example.com/a", "*")
    checker.allowed("https://example.com/b", "*")
    assert calls == ["https://example.com/robots.txt"]
