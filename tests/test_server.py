import asyncio

from seo_tools.server import mcp

EXPECTED = {
    "gsc_sites", "gsc_query", "gsc_cannibalization", "gsc_sitemaps", "gsc_inspect_url",
    "ya_hosts", "ya_summary", "ya_search_queries", "ya_indexing_history", "ya_search_events", "ya_sitemaps",
    "wordstat_top", "wordstat_dynamics", "wordstat_regions",
}


def test_tool_list_matches_agent_and_readme():
    # Если список меняется, обнови tools в agents/seo-specialist.md и таблицу в README.
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED


def test_every_tool_has_description():
    for t in asyncio.run(mcp.list_tools()):
        assert t.description and len(t.description) > 30, t.name
