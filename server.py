"""Yandex Webmaster MCP Server — core API v4.1 tools."""

import json
from fastmcp import FastMCP
from client import WebmasterClient, WebmasterAPIError, OAuthFlow

mcp = FastMCP("Yandex Webmaster")

_client: WebmasterClient | None = None


def get_client() -> WebmasterClient:
    global _client
    if _client is None:
        _client = WebmasterClient()
    return _client


def _ok(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _err(e: WebmasterAPIError) -> str:
    return json.dumps(
        {"error": True, "error_code": e.error_code, "message": e.message, "status": e.status_code},
        ensure_ascii=False,
        indent=2,
    )


# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def setup_oauth_app() -> str:
    """Get step-by-step instructions to create a Yandex OAuth app for this MCP server."""
    return """To use this MCP server you need a Yandex OAuth app. Follow these steps:

1. Open https://oauth.yandex.ru/client/new in your browser
2. Fill in "App name": e.g. "Webmaster MCP"
3. Under "Platforms" select "Web services"
4. In "Callback URI" enter: https://oauth.yandex.ru
5. Under "Access" expand "Yandex.Webmaster" and enable:
   - webmaster:hostinfo
   - webmaster:verify
6. Click "Create app"
7. Copy the CLIENT_ID shown on the next page

Then call: start_auth(client_id="YOUR_CLIENT_ID")"""


@mcp.tool()
def start_auth(client_id: str) -> str:
    """Start Yandex OAuth device flow. Opens a browser page for you to approve access.

    Args:
        client_id: Your Yandex OAuth app client_id (from oauth.yandex.ru)
    """
    try:
        flow = OAuthFlow()
        device_data = flow.request_device_code(client_id)
        verification_url = device_data.get("verification_url", "https://ya.ru/device")
        user_code = device_data.get("user_code", "")
        device_code = device_data.get("device_code")
        if not device_code:
            raise WebmasterAPIError(400, "INVALID_DEVICE_CODE", "Server did not return device_code")

        result = (
            f"Open this URL in your browser and enter the code shown:\n\n"
            f"  URL:  {verification_url}\n"
            f"  Code: {user_code}\n\n"
            f"Waiting for approval (up to 5 minutes)..."
        )

        # Poll blocks until approved or timeout
        access_token = flow.poll_for_token(client_id, device_code)
        token_path = flow.save_token(access_token)

        return result + f"\n\nAuthentication successful! Token saved to: {token_path}"
    except WebmasterAPIError as e:
        return _err(e)
    except (OSError, ValueError) as e:
        return json.dumps({"error": True, "error_code": "TOKEN_SAVE_ERROR", "message": str(e)}, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# USER & SITES
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def get_user_id() -> str:
    """Get authenticated Yandex Webmaster user ID."""
    try:
        data = get_client().get("/user")
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_hosts(user_id: str) -> str:
    """Get list of all sites added to Yandex Webmaster.

    Args:
        user_id: Yandex Webmaster user ID (from get_user_id)
    """
    try:
        data = get_client().get(f"/user/{user_id}/hosts")
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def add_host(user_id: str, host_url: str) -> str:
    """Add a new site to Yandex Webmaster.

    Args:
        user_id: Yandex Webmaster user ID
        host_url: Site URL to add (e.g. https://example.com)
    """
    try:
        data = get_client().post(f"/user/{user_id}/hosts", json_body={"host_url": host_url})
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_host_info(user_id: str, host_id: str) -> str:
    """Get detailed information about a site including SQI (quality index).

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443 (from get_hosts)
    """
    try:
        c = get_client()
        data = c.get(c.host_url(user_id, host_id))
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


# ═══════════════════════════════════════════════════════════════
# SEARCH ANALYTICS
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def get_search_queries(
    user_id: str,
    host_id: str,
    date_from: str,
    date_to: str,
    order_by: str = "TOTAL_SHOWS",
    query_indicator: str | None = None,
    device_type_indicator: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> str:
    """Get TOP-3000 popular search queries with clicks, impressions, and positions.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        order_by: Sort by TOTAL_SHOWS or TOTAL_CLICKS
        query_indicator: Comma-separated: TOTAL_SHOWS,TOTAL_CLICKS,AVG_SHOW_POSITION,AVG_CLICK_POSITION
        device_type_indicator: ALL, DESKTOP, MOBILE, PHONE, TABLET
        limit: Results per page (1–500, default 500)
        offset: Pagination offset
    """
    try:
        c = get_client()
        indicators = query_indicator.split(",") if query_indicator else None
        data = c.get(
            f"{c.host_url(user_id, host_id)}/search-queries/popular",
            params={
                "order_by": order_by,
                "query_indicator": indicators,
                "device_type_indicator": device_type_indicator,
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
                "offset": offset,
            },
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_query_history(
    user_id: str,
    host_id: str,
    date_from: str,
    date_to: str,
    query_indicator: str | None = None,
    device_type_indicator: str | None = None,
) -> str:
    """Get aggregated search query statistics over time (all queries by day).

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        query_indicator: Comma-separated: TOTAL_SHOWS,TOTAL_CLICKS,AVG_SHOW_POSITION,AVG_CLICK_POSITION
        device_type_indicator: ALL, DESKTOP, MOBILE, PHONE, TABLET
    """
    try:
        c = get_client()
        indicators = query_indicator.split(",") if query_indicator else None
        data = c.get(
            f"{c.host_url(user_id, host_id)}/search-queries/all/history",
            params={
                "query_indicator": indicators,
                "device_type_indicator": device_type_indicator,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_search_urls(
    user_id: str,
    host_id: str,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Get samples of pages currently appearing in Yandex search results (up to 50,000).

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        limit: Results per page (1–100, default 50)
        offset: Pagination offset
    """
    try:
        c = get_client()
        data = c.get(
            f"{c.host_url(user_id, host_id)}/search-urls/in-search/samples",
            params={"limit": limit, "offset": offset},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


# ═══════════════════════════════════════════════════════════════
# INDEXING & CRAWLING
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def get_indexing_stats(
    user_id: str,
    host_id: str,
    date_from: str,
    date_to: str,
) -> str:
    """Get indexing history — number of indexed pages by HTTP status over time.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    """
    try:
        c = get_client()
        data = c.get(
            f"{c.host_url(user_id, host_id)}/indexing/history",
            params={"date_from": date_from, "date_to": date_to},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_sitemap_info(
    user_id: str,
    host_id: str,
    limit: int = 100,
    offset: str | None = None,
) -> str:
    """Get list of user-added sitemaps with their status.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        limit: Results per page (1–100, default 100)
        offset: Cursor-based pagination (sitemap ID)
    """
    try:
        c = get_client()
        data = c.get(
            f"{c.host_url(user_id, host_id)}/user-added-sitemaps",
            params={"limit": limit, "offset": offset},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def add_sitemap(user_id: str, host_id: str, sitemap_url: str) -> str:
    """Submit a sitemap to Yandex Webmaster.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        sitemap_url: Full URL of the sitemap (e.g. https://example.com/sitemap.xml)
    """
    try:
        c = get_client()
        data = c.post(
            f"{c.host_url(user_id, host_id)}/user-added-sitemaps",
            json_body={"url": sitemap_url},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_recrawl_quota(user_id: str, host_id: str) -> str:
    """Get daily recrawl quota — how many URLs can be submitted for reindexing today.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
    """
    try:
        c = get_client()
        data = c.get(f"{c.host_url(user_id, host_id)}/recrawl/quota")
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def add_recrawl_url(user_id: str, host_id: str, url: str) -> str:
    """Submit a URL for recrawl and reindexing by Yandex.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        url: Full URL to recrawl (e.g. https://example.com/updated-page/)
    """
    try:
        c = get_client()
        data = c.post(
            f"{c.host_url(user_id, host_id)}/recrawl/queue",
            json_body={"url": url},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


# ═══════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def get_site_problems(user_id: str, host_id: str) -> str:
    """Get critical site problems and diagnostics (FATAL, CRITICAL, ERROR severity).

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
    """
    try:
        c = get_client()
        data = c.get(f"{c.host_url(user_id, host_id)}/diagnostics")
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_recommendations(user_id: str, host_id: str) -> str:
    """Get Yandex SEO recommendations for the site.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
    """
    try:
        c = get_client()
        data = c.get(f"{c.host_url(user_id, host_id)}/diagnostics")
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_broken_internal_links(
    user_id: str,
    host_id: str,
    indicator: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get samples of broken internal links on the site.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        indicator: Comma-separated: SITE_ERROR,DISALLOWED_BY_USER,UNSUPPORTED_BY_ROBOT
        limit: Results per page (1–100, default 10)
        offset: Pagination offset
    """
    try:
        c = get_client()
        indicators = indicator.split(",") if indicator else None
        data = c.get(
            f"{c.host_url(user_id, host_id)}/links/internal/broken/samples",
            params={"indicator": indicators, "limit": limit, "offset": offset},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


@mcp.tool()
def get_external_links(
    user_id: str,
    host_id: str,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Get samples of external backlinks pointing to the site.

    Args:
        user_id: Yandex Webmaster user ID
        host_id: Host ID in format https:example.com:443
        limit: Results per page (1–100, default 10)
        offset: Pagination offset
    """
    try:
        c = get_client()
        data = c.get(
            f"{c.host_url(user_id, host_id)}/links/external/samples",
            params={"limit": limit, "offset": offset},
        )
        return _ok(data)
    except WebmasterAPIError as e:
        return _err(e)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════


def main():
    """Run the Yandex Webmaster MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
