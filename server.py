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
4. In "Callback URI" enter exactly: https://oauth.yandex.ru/verification_code
5. Under "Access" expand "Yandex.Webmaster" and enable:
   - webmaster:hostinfo
   - webmaster:verify
6. Click "Create app"
7. Copy the CLIENT_ID shown on the next page

Then call: start_auth(client_id="YOUR_CLIENT_ID")
It saves your client_id to client_secret.json and returns an authorization URL.
Open that URL in your browser, approve access, copy the token from the redirect page,
and call: save_token(access_token="YOUR_TOKEN")"""


@mcp.tool()
def start_auth(client_id: str) -> str:
    """Generate a Yandex OAuth authorization URL. Open it in your browser to approve access.

    Saves client_id to client_secret.json so it is available for re-authentication when the token expires.
    After approving in the browser, copy the token from the redirect page and call save_token.

    Args:
        client_id: Your Yandex OAuth app client_id (from oauth.yandex.ru)
    """
    try:
        secret_path = OAuthFlow.save_client_id(client_id)
    except (OSError, ValueError) as e:
        return json.dumps({"error": True, "error_code": "CLIENT_ID_SAVE_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)

    auth_url = OAuthFlow.get_auth_url(client_id)
    return json.dumps({
        "client_id_saved_to": str(secret_path),
        "auth_url": auth_url,
        "instructions": (
            f"Step 1: Open this URL in your browser:\n  {auth_url}\n\n"
            "Step 2: Log in with your Yandex account and click 'Allow'\n\n"
            "Step 3: You will be redirected to a page at oauth.yandex.ru that shows your token. "
            "Copy the access_token value from that page.\n\n"
            "Step 4: Call save_token(access_token='TOKEN') to complete authentication."
        ),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def save_token(access_token: str) -> str:
    """Save a Yandex OAuth token obtained from the browser authorization flow.

    Call this after completing the start_auth browser flow and copying your token from the browser.

    Args:
        access_token: The OAuth token shown on the Yandex authorization page
    """
    global _client
    try:
        token_path = OAuthFlow.save_token(access_token)
        _client = None  # Reset singleton so next call picks up new token
        return json.dumps({"success": True, "message": f"Token saved to: {token_path}"}, ensure_ascii=False, indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": True, "error_code": "TOKEN_SAVE_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
        offset: Cursor-based pagination — pass a sitemap ID string to start from (not a numeric index)
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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


@mcp.tool()
def get_recommendations(user_id: str, host_id: str) -> str:
    """Get Yandex SEO recommendations for the site. Returns the full diagnostics response which includes both problems and recommendations.

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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


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
    except ValueError as e:
        return json.dumps({"error": True, "error_code": "AUTH_ERROR", "message": str(e)}, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════


def main():
    """Run the Yandex Webmaster MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
