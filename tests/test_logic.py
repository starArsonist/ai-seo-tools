import csv

from seo_tools.config import Settings, read_env_file, write_env_value
from seo_tools.gsc import find_cannibalization, normalize_row
from seo_tools.reports import package
from seo_tools.webmaster import normalize_query


def row(query, page, clicks, impressions, position):
    return {"query": query, "page": page, "clicks": clicks, "impressions": impressions, "position": position}


def test_normalize_gsc_row():
    raw = {"keys": ["купить диван", "https://x.ru/a"], "clicks": 3, "impressions": 120,
           "ctr": 0.025, "position": 7.345}
    assert normalize_row(raw, ["query", "page"]) == {
        "query": "купить диван", "page": "https://x.ru/a",
        "clicks": 3, "impressions": 120, "ctr": 2.5, "position": 7.3}


def test_cannibalization_finds_conflict_and_owner():
    rows = [
        row("диван", "/a", 5, 300, 8.0),
        row("диван", "/b", 9, 200, 6.0),
        row("диван", "/c", 0, 5, 9.0),      # мало показов, не считается
        row("кресло", "/a", 1, 50, 4.0),
        row("кресло", "/d", 0, 40, 35.0),   # за пределами топ-20
        row("стол", "/e", 2, 90, 3.0),
    ]
    result = find_cannibalization(rows, min_impressions=10, max_position=20)
    assert len(result) == 1
    c = result[0]
    assert c["query"] == "диван" and c["owner"] == "/b"
    assert [p["page"] for p in c["pages"]] == ["/b", "/a"]
    assert c["total_impressions"] == 500


def test_cannibalization_tie_on_clicks_uses_impressions():
    rows = [row("q", "/a", 0, 40, 5.0), row("q", "/b", 0, 90, 12.0)]
    assert find_cannibalization(rows, min_impressions=1, max_position=20)[0]["owner"] == "/b"


def test_normalize_yandex_query():
    raw = {"query_text": "ремонт", "indicators": {"TOTAL_SHOWS": 200, "TOTAL_CLICKS": 10,
                                                  "AVG_SHOW_POSITION": 4.456, "AVG_CLICK_POSITION": None}}
    assert normalize_query(raw) == {"query": "ремонт", "shows": 200, "clicks": 10, "ctr": 5.0,
                                    "avg_show_position": 4.5, "avg_click_position": None}


def test_normalize_yandex_query_zero_shows():
    assert normalize_query({"query_text": "x", "indicators": {}})["ctr"] == 0.0


def test_env_override_and_empty_plugin_option(tmp_path, monkeypatch):
    monkeypatch.setenv("SEO_TOOLS_HOME", str(tmp_path))
    (tmp_path / ".env").write_text("YANDEX_OAUTH_TOKEN=from-file\nYANDEX_CLOUD_FOLDER_ID='b1g'\n", encoding="utf-8")
    monkeypatch.setenv("YANDEX_OAUTH_TOKEN", "from-env")
    monkeypatch.setenv("YANDEX_CLOUD_FOLDER_ID", "")  # незаполненная опция плагина
    monkeypatch.setenv("YANDEX_CLOUD_API_KEY", "${user_config.yandex_cloud_api_key}")
    s = Settings.load()
    assert s.get("YANDEX_CLOUD_API_KEY") is None
    assert s.get("YANDEX_OAUTH_TOKEN") == "from-env"
    assert s.get("YANDEX_CLOUD_FOLDER_ID") == "b1g"
    assert s.reports_dir == tmp_path / "reports"


def test_google_credentials_found_by_type(tmp_path, monkeypatch):
    monkeypatch.setenv("SEO_TOOLS_HOME", str(tmp_path))
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    (tmp_path / "a-other.json").write_text('{"type": "authorized_user"}', encoding="utf-8")
    key = tmp_path / "b-key.json"
    key.write_text('{"type": "service_account"}', encoding="utf-8")
    assert Settings.load().google_credentials() == key


def test_write_env_value_replaces_only_one_key(tmp_path, monkeypatch):
    monkeypatch.setenv("SEO_TOOLS_HOME", str(tmp_path))
    (tmp_path / ".env").write_text("A=1\nYANDEX_OAUTH_TOKEN=old\n# comment\n", encoding="utf-8")
    write_env_value("YANDEX_OAUTH_TOKEN", "new")
    assert read_env_file(tmp_path / ".env") == {"A": "1", "YANDEX_OAUTH_TOKEN": "new"}
    assert "# comment" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_package_saves_csv(tmp_path):
    rows = [{"query": "диван", "clicks": 1}, {"query": "стол", "clicks": 2, "extra": "x"}]
    res = package(rows, save=True, reports_dir=tmp_path, site="sc-domain:example.ru", name="gsc_query")
    assert res["count"] == 2 and "example.ru" in res["saved_to"]
    with open(res["saved_to"], encoding="utf-8-sig") as f:
        saved = list(csv.DictReader(f))
    assert saved[1] == {"query": "стол", "clicks": "2", "extra": "x"}


def test_package_inline():
    assert package([{"a": 1}], save=False, reports_dir=None, site="x.ru", name="n") == {"count": 1, "rows": [{"a": 1}]}
