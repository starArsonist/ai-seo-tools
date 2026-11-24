import pytest

from seo_tools.sites import bare_domain, pick_gsc_property, pick_webmaster_host


@pytest.mark.parametrize("raw", [
    "example.ru", "EXAMPLE.ru", "www.example.ru", "https://example.ru/", "http://www.example.ru/blog/x",
    "sc-domain:example.ru", "https:example.ru:443", "http:example.ru:80", "example.ru:8080",
])
def test_bare_domain(raw):
    assert bare_domain(raw) == "example.ru"


def test_bare_domain_keeps_subdomain():
    assert bare_domain("https://shop.example.ru/") == "shop.example.ru"


def test_gsc_prefers_domain_property():
    props = ["https://example.ru/", "sc-domain:example.ru", "https://other.ru/"]
    assert pick_gsc_property("example.ru", props) == "sc-domain:example.ru"


def test_gsc_exact_match_wins():
    props = ["https://example.ru/", "sc-domain:example.ru"]
    assert pick_gsc_property("https://example.ru/", props) == "https://example.ru/"


def test_gsc_unknown_site():
    with pytest.raises(LookupError):
        pick_gsc_property("nope.ru", ["sc-domain:example.ru"])


def test_webmaster_prefers_https_verified():
    hosts = [
        {"host_id": "http:example.ru:80", "verified": True},
        {"host_id": "https:example.ru:443", "verified": False},
        {"host_id": "https:www.example.ru:443", "verified": True},
    ]
    assert pick_webmaster_host("example.ru", hosts) == "https:www.example.ru:443"


def test_webmaster_unicode_host():
    hosts = [{"host_id": "https:xn--80aswg.xn--p1ai:443", "unicode_host_url": "https://сайт.рф/"}]
    assert pick_webmaster_host("сайт.рф", hosts) == "https:xn--80aswg.xn--p1ai:443"
