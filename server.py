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
        device_code = device_data["device_code"]

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


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════


def main():
    mcp.run()


if __name__ == "__main__":
    main()
