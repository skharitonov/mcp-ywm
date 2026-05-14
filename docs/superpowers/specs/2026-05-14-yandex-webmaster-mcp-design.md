# Yandex Webmaster MCP — Design Spec

**Date:** 2026-05-14
**Package:** `yandex-webmaster-mcp`
**CLI command:** `ywm-mcp`
**Install:** `uvx --from git+https://github.com/skharitonov/mcp-ywm ywm-mcp`

---

## Reference Projects (already cloned)

Both repos are cloned locally and the coding agent must use them directly:

- **Python codebase reference:** `/tmp/ywm-ref/`
  - `src/yandex_webmaster_mcp/client.py` — HTTP client with retry logic, URL encoding, `WebmasterAPIError`
  - `src/yandex_webmaster_mcp/server.py` — 37 FastMCP tools, copy the subset we need
  - `pyproject.toml` — use as baseline, adapt for flat layout + uvx
- **Project structure / docs / README reference:** `/tmp/gsc-ref/`
  - `gsc_server.py` — FastMCP pattern: `@mcp.tool()` decorators, `main()` entry point
  - `pyproject.toml` — uvx-compatible packaging with `[tool.setuptools] py-modules`
  - `README.md` — full documentation style to replicate (see README section below)
  - `.mcp.json` — MCP config template to copy and adapt

The coding agent must read these files before writing any code.

---

## Repository Layout

```
mcp-ywm/
├── client.py          # HTTP client + OAuth device flow (from /tmp/ywm-ref/src/.../client.py)
├── server.py          # FastMCP tool definitions + main() (subset from /tmp/ywm-ref/src/.../server.py)
├── pyproject.toml     # Package metadata and entry point (pattern from /tmp/gsc-ref/pyproject.toml)
├── README.md          # Detailed setup guide (structure from /tmp/gsc-ref/README.md)
├── .mcp.json          # MCP config template (copy from /tmp/gsc-ref/.mcp.json, adapt)
├── .env.example       # Documents that no env vars are needed post-auth
└── LICENSE
```

---

## Packaging (`pyproject.toml`)

```toml
[project]
name = "yandex-webmaster-mcp"
version = "0.1.0"
description = "MCP server for Yandex Webmaster API v4.1"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.28.0",
    "platformdirs>=4.0.0",
]

[project.scripts]
ywm-mcp = "server:main"

[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
py-modules = ["server", "client"]
```

**Install command (no clone needed):**
```
uvx --from git+https://github.com/skharitonov/mcp-ywm ywm-mcp
```

**Claude Code `settings.json`:**
```json
{
  "mcpServers": {
    "yandex-webmaster": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"]
    }
  }
}
```

**Claude Desktop `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "yandex-webmaster": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"]
    }
  }
}
```

---

## Authentication Design (`client.py`)

Uses Yandex **OAuth device code flow** — no local callback server required, works reliably as an MCP subprocess.

### Flow

1. User calls `setup_oauth_app` tool → receives step-by-step instructions to create an app at `oauth.yandex.ru` (what to name it, which scopes: `webmaster:hostinfo webmaster:verify`, where to find `client_id`)
2. User calls `start_auth(client_id)` tool
3. `client.py` posts to `https://oauth.yandex.ru/device/code` with `client_id` and scopes
4. Returns a verification URL + user code for the user to open in their browser
5. Polls `https://oauth.yandex.ru/token` every 5 seconds, up to 5 minutes, until approved
6. Saves token to platform config dir via `platformdirs.user_config_dir("yandex-webmaster-mcp")`:
   - Linux/Mac: `~/.config/yandex-webmaster-mcp/token.json`
   - Windows: `%APPDATA%\yandex-webmaster-mcp\token.json`
7. On subsequent calls, `WebmasterClient` loads the token from disk automatically

### Token file structure

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_at": 1234567890
}
```

### `client.py` components

- `OAuthFlow` class — device code request, polling loop, token save/load
- `WebmasterClient` class — ported from `/tmp/ywm-ref/src/yandex_webmaster_mcp/client.py`, loads token from disk on init, raises clear `"Run start_auth(client_id) first"` if missing
- `WebmasterAPIError` — ported as-is from reference

### Error states

- Token file not found → `"Run start_auth(client_id) first to authenticate"`
- Device flow timeout (5 min) → `"Authorization timed out. Call start_auth again."`
- API 4xx → JSON `{"error": true, "error_code": "...", "message": "..."}`
- 500/502/503 → retry 3× with exponential backoff (ported from reference client)

---

## MCP Tools (`server.py`)

Port the listed tools verbatim from `/tmp/ywm-ref/src/yandex_webmaster_mcp/server.py`. The tool names, docstrings, and parameter names in that file are the source of truth.

### Auth (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `setup_oauth_app` | — | Step-by-step instructions to create a Yandex OAuth app at oauth.yandex.ru |
| `start_auth` | `client_id: str` | Triggers device flow, returns verification URL + code, polls, saves token |

### User & Sites (4 tools) — from reference `server.py`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_user_id` | — | Get authenticated user ID |
| `get_hosts` | `user_id` | List all sites added to Webmaster |
| `add_host` | `user_id`, `host_url` | Add a site |
| `get_host_info` | `user_id`, `host_id` | Site details + quality metrics (ICS index) |

### Search Analytics (3 tools) — from reference `server.py`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_search_queries` | `user_id`, `host_id`, `date_from`, `date_to`, `limit?` | Top queries with clicks, impressions, position |
| `get_query_history` | `user_id`, `host_id`, `query_indicator`, `date_from`, `date_to` | Historical trend for a metric |
| `get_search_urls` | `user_id`, `host_id`, `date_from`, `date_to`, `limit?` | Top pages in search results |

### Indexing & Crawling (5 tools) — from reference `server.py`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_indexing_stats` | `user_id`, `host_id` | Indexation history by HTTP status |
| `get_sitemap_info` | `user_id`, `host_id` | Sitemap list + status |
| `add_sitemap` | `user_id`, `host_id`, `sitemap_url` | Submit a sitemap |
| `get_recrawl_quota` | `user_id`, `host_id` | Remaining recrawl quota |
| `add_recrawl_url` | `user_id`, `host_id`, `url` | Request URL reindex |

### Diagnostics (4 tools) — from reference `server.py`

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_site_problems` | `user_id`, `host_id` | Critical site issues |
| `get_broken_internal_links` | `user_id`, `host_id` | Broken internal link report |
| `get_external_links` | `user_id`, `host_id` | Backlink analysis |
| `get_recommendations` | `user_id`, `host_id` | Yandex SEO recommendations |

**Total: 18 tools**

### Implementation notes

- `FastMCP("Yandex Webmaster")` instance in `server.py` — follow pattern in `/tmp/gsc-ref/gsc_server.py`
- Lazy `WebmasterClient` singleton — initialized on first non-auth tool call, same pattern as reference `server.py`
- All tools return JSON strings: `json.dumps(data, ensure_ascii=False, indent=2)`
- `host_id` format: `protocol:domain:port` (e.g. `https:example.com:443`) — URL-encoded automatically by `WebmasterClient.encode_host_id()`
- `main()` calls `mcp.run()`

---

## Error Handling

All tools follow this pattern (ported from reference):

```python
try:
    data = get_client().get(...)
    return json.dumps(data, ensure_ascii=False, indent=2)
except WebmasterAPIError as e:
    return json.dumps({
        "error": True,
        "error_code": e.error_code,
        "message": e.message,
        "status": e.status_code
    })
```

---

## README Structure

The README must follow the same depth and style as `/tmp/gsc-ref/README.md`. Sections:

### 1. Title + one-line description
```
# Yandex Webmaster MCP Server
An MCP server that connects Yandex Webmaster to AI assistants...
```

### 2. What Can This Do? (feature categories with bullets)
- Site Management
- Search Analytics
- Indexing & Crawling
- Diagnostics

### 3. Available Tools (full table: Tool | What It Does | What You Need to Provide)

### 4. Getting Started

#### Step 1 — Create a Yandex OAuth App
Numbered instructions:
1. Go to https://oauth.yandex.ru/client/new
2. Name the app (e.g. "Webmaster MCP")
3. Enable scopes: `webmaster:hostinfo` and `webmaster:verify`
4. Set platform to "Web services", add any redirect URI (e.g. `https://oauth.yandex.ru`)
5. Click Create — copy the `client_id`

#### Step 2 — Install uv
Platform-specific commands (macOS/Linux and Windows), including how to activate in current shell and make permanent. Explain why all steps are needed (same detail level as GSC ref).

#### Step 3 — Configure your AI client

**Claude Code** — `settings.json` snippet with `uvx --from git+...`
**Claude Desktop** — `claude_desktop_config.json` snippet
Include note about full path to uvx for GUI apps and how to find it with `which uvx`.

#### Step 4 — Authenticate
```
"Call the setup_oauth_app tool"
"Call start_auth with client_id YOUR_CLIENT_ID"
```
Explain the browser flow: open URL, approve, done. Token stored automatically.

#### Step 5 — Test
`"Get my user ID"` or `"List all my Yandex Webmaster sites"`

### 5. Sample Prompts (table: Tool | Sample Prompt)
At least 8 prompts covering all tool categories.

### 6. Tool Reference (full table of all 18 tools)

### 7. host_id Format
Explain `protocol:domain:port` format with examples. Note that URL-encoding is automatic.

### 8. Troubleshooting
- `spawn uvx ENOENT` — full path fix
- Token expired — call `start_auth` again
- Wrong scopes — re-create app with correct scopes
- `host_id` format errors — examples of correct format

### 9. License
MIT

---

## Out of Scope

- The remaining ~19 tools from the full API v4.1 (can be added later by porting from `/tmp/ywm-ref/src/yandex_webmaster_mcp/server.py`)
- Unit/integration tests (thin API wrappers, require live token)
- Docker support
- PyPI publish (install from GitHub only for now)
