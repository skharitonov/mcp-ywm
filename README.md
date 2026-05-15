# Yandex Webmaster MCP Server

An MCP server that connects Yandex Webmaster to AI assistants — ask questions about your site's search performance, indexing, sitemaps, and diagnostics in plain language.

---

## What Can This Do?

### Site Management
- Add sites to Yandex Webmaster and retrieve their quality index (SQI)
- List all verified sites on your account
- Fetch detailed site metadata

### Search Analytics
- Pull top-3000 search queries with clicks, impressions, and average positions
- Get day-by-day search performance history
- List pages currently appearing in Yandex search results

### Indexing & Crawling
- Track indexed page counts by HTTP status over time
- Submit and manage sitemaps
- Check your daily recrawl quota
- Request individual URLs for immediate reindexing

### Diagnostics
- View critical site problems at FATAL, CRITICAL, and ERROR severity levels
- Get Yandex SEO recommendations
- Find broken internal links (404s, disallowed pages, unsupported formats)
- Inspect external backlinks pointing to your site

---

## Available Tools

| Tool | What It Does | What You Need to Provide |
|------|-------------|--------------------------|
| `setup_oauth_app` | Returns step-by-step instructions for creating a Yandex OAuth app | Nothing |
| `start_auth` | Returns an authorization URL — open it in your browser to approve access | `client_id` |
| `save_token` | Saves the token you copied from the browser authorization page | `access_token` |
| `get_user_id` | Returns your Yandex Webmaster user ID | Nothing |
| `get_hosts` | Lists all sites added to your Yandex Webmaster account | `user_id` |
| `add_host` | Adds a new site to Yandex Webmaster | `user_id`, `host_url` |
| `get_host_info` | Returns detailed info about a site including its SQI quality index | `user_id`, `host_id` |
| `get_search_queries` | TOP-3000 search queries with clicks, impressions, and positions | `user_id`, `host_id`, `date_from`, `date_to` |
| `get_query_history` | Aggregated search stats by day over a date range | `user_id`, `host_id`, `date_from`, `date_to` |
| `get_search_urls` | Sample pages currently appearing in Yandex search results (up to 50,000) | `user_id`, `host_id` |
| `get_indexing_stats` | Indexed page counts by HTTP status over time | `user_id`, `host_id`, `date_from`, `date_to` |
| `get_sitemap_info` | Lists user-submitted sitemaps with their processing status | `user_id`, `host_id` |
| `add_sitemap` | Submits a sitemap URL to Yandex Webmaster | `user_id`, `host_id`, `sitemap_url` |
| `get_recrawl_quota` | Shows how many URLs you can still submit for recrawl today | `user_id`, `host_id` |
| `add_recrawl_url` | Submits a single URL for immediate recrawl and reindexing | `user_id`, `host_id`, `url` |
| `get_site_problems` | Returns critical site problems (FATAL, CRITICAL, ERROR) | `user_id`, `host_id` |
| `get_recommendations` | Returns Yandex SEO recommendations for the site | `user_id`, `host_id` |
| `get_broken_internal_links` | Sample broken internal links found during crawling | `user_id`, `host_id` |
| `get_external_links` | Sample external backlinks pointing to the site | `user_id`, `host_id` |

---

## Getting Started

### Step 1 — Create a Yandex OAuth App

You need a Yandex OAuth application to authorize the server to access your Webmaster data. This is a one-time setup.

1. Open [https://oauth.yandex.ru/client/new](https://oauth.yandex.ru/client/new) in your browser
2. Fill in **App name** — for example, `Webmaster MCP`
3. Under **Platforms**, select **Web services**
4. In the **Callback URI** field, enter exactly: `https://oauth.yandex.ru/verification_code`
5. Under **Access**, expand **Yandex.Webmaster** and enable these two scopes:
   - `webmaster:hostinfo`
   - `webmaster:verify`
6. Click **Create app**
7. Copy the **CLIENT_ID** shown on the next page — you'll need it in Step 4

> **Alternative:** If you already have a Yandex Webmaster OAuth token, you can skip OAuth entirely by setting `YANDEX_WEBMASTER_API_KEY` in your MCP config's `env` block. See the [Environment Variables Reference](#environment-variables-reference) section below.

---

### Step 2 — Install uv

This server runs via `uvx`, which is part of the [uv](https://docs.astral.sh/uv/) package manager. You do not need to clone this repository — `uvx` fetches and runs it directly from GitHub.

**macOS / Linux**

Run these three commands in your terminal:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The installer places the `uv` and `uvx` binaries in `$HOME/.local/bin`. You need to make your shell aware of them for the current session:

```bash
source $HOME/.local/bin/env
```

To make this permanent so future terminal windows also have `uvx` available, add the source line to your shell config:

```bash
echo 'source $HOME/.local/bin/env' >> ~/.zshrc
```

> **Why all three commands?** The `curl` command installs uv but does not modify your current shell session. The `source` command activates it right now. The `echo` command ensures it is available every time you open a new terminal. Skipping either of the last two means you will see `command not found: uvx` in your terminal or in AI client logs.

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installation.

**Verify the installation**

```bash
uv --version
```

You should see output like `uv 0.5.x`. If you see `command not found`, see the [Troubleshooting](#troubleshooting) section.

---

### Step 3 — Configure your AI Client

#### Claude Code

Add the server to your project or global MCP settings. Run the following from your project directory or home directory:

```bash
claude mcp add --scope project ywm -- uvx --from git+https://github.com/skharitonov/mcp-ywm ywm-mcp
```

> Use `--scope user` instead of `--scope project` to make the server available across all your projects rather than just the current one.

Or edit `~/.claude/settings.json` directly and add an entry under `mcpServers`:

```json
{
  "mcpServers": {
    "ywm": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"]
    }
  }
}
```

#### Claude Desktop

Claude Desktop launches as a GUI application and does not inherit your shell's `PATH`. This means the bare `uvx` command will not be found — you must use the **full absolute path** to the `uvx` binary.

First, find the full path:

- **macOS / Linux:** run `which uvx` in your terminal — it will print something like `/Users/yourname/.local/bin/uvx`
- **Windows:** run `(Get-Command uvx).Source` in PowerShell — it will print something like `C:\Users\yourname\.local\bin\uvx.exe`

Then open the Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add the following, replacing the `uvx` path with the full path you found above:

```json
{
  "mcpServers": {
    "ywm": {
      "command": "/Users/yourname/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"]
    }
  }
}
```

After saving the config file, **fully quit the app** (on macOS: `Cmd+Q`, not just closing the window) and reopen it. Claude Desktop only reads the config at startup.

---

### Step 4 — Authenticate

Once the server is configured, open Claude and start the authorization flow with the `client_id` you copied in Step 1:

```
Call start_auth with client_id "YOUR_CLIENT_ID_HERE"
```

The server saves your `client_id` to `client_secret.json` and returns an authorization URL. Open it in your browser, log in with your Yandex account, and click **Allow**.

Yandex will redirect you to a page at `oauth.yandex.ru` that displays your access token. Copy the token value shown on that page, then save it:

```
Call save_token with access_token "YOUR_TOKEN_HERE"
```

Config files are stored at:

| File | Contents | OS default location |
|------|----------|-------------------|
| `client_secret.json` | `client_id` (saved by `start_auth`) | See [Environment Variables Reference](#environment-variables-reference) |
| `token.json` | OAuth access token (saved by `save_token`) | See [Environment Variables Reference](#environment-variables-reference) |

After calling `save_token` successfully, you will see: `Token saved to: <path>`. You are now ready to use all tools.

When your token expires, call `start_auth` again — your `client_id` is already saved in `client_secret.json`, so the server will remind you of it in any authentication error messages.

---

### Step 5 — Test

Ask Claude these two questions to confirm everything is working:

```
Get my Yandex Webmaster user ID
```

```
List all my Yandex Webmaster sites
```

If both return data, the server is set up correctly. Note the `user_id` from the first response — you will need it for site-specific queries.

---

## Sample Prompts

| Category | Sample Prompt |
|----------|--------------|
| Setup | "Walk me through creating a Yandex OAuth app for Webmaster" |
| Sites | "List all my sites in Yandex Webmaster" |
| Sites | "Add https://example.com to my Yandex Webmaster account" |
| Search — queries | "Show me the top 20 search queries for example.com in the last 30 days" |
| Search — trends | "How has my click-through rate changed week by week over the past 3 months?" |
| Search — pages | "Which pages from my site are currently showing up in Yandex search?" |
| Indexing / recrawl | "I just updated 5 pages — submit them all for immediate recrawling" |
| Sitemaps | "Check whether my sitemap at https://example.com/sitemap.xml has been accepted" |
| Diagnostics — problems | "Are there any critical errors Yandex has detected on my site?" |
| Diagnostics — links | "Find all broken internal links on my site" |
| Diagnostics — backlinks | "Show me which external sites are linking to example.com" |

---

## host_id Format

Yandex Webmaster identifies sites using a `host_id` — a colon-separated string derived from the site URL. The `get_hosts` tool returns `host_id` values for all your sites.

| Site URL | host_id |
|----------|---------|
| `https://example.com` | `https:example.com:443` |
| `http://example.com` | `http:example.com:80` |
| `https://www.example.com` | `https:www.example.com:443` |
| `https://example.com:8443` | `https:example.com:8443` |

When you pass a `host_id` to any tool, URL-encoding (e.g. `https%3Aexample.com%3A443`) is handled automatically — you provide the plain colon-separated form.

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `YANDEX_WEBMASTER_CONFIG_PATH` | Platform config dir | Directory for `token.json` and `client_secret.json`. Override to control where all config files live. |
| `YANDEX_WEBMASTER_TOKEN_FILE` | `{config_dir}/token.json` | Absolute path to a specific token file. Use this to run multiple MCP server instances with different Yandex accounts — point each instance at its own `token-account1.json`, `token-account2.json`, etc. |
| `YANDEX_WEBMASTER_CLIENT_ID_FILE` | `{config_dir}/client_secret.json` | Absolute path to a specific `client_secret.json` file. |

**Default config locations:**

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/yandex-webmaster-mcp/` |
| Linux | `~/.config/yandex-webmaster-mcp/` |
| Windows | `%LOCALAPPDATA%\yandex-webmaster-mcp\` |

**Multi-account example** — two MCP server entries, each with its own token file:

```json
{
  "mcpServers": {
    "ywm-site1": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"],
      "env": { "YANDEX_WEBMASTER_TOKEN_FILE": "/path/to/token-site1.json" }
    },
    "ywm-site2": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/skharitonov/mcp-ywm", "ywm-mcp"],
      "env": { "YANDEX_WEBMASTER_TOKEN_FILE": "/path/to/token-site2.json" }
    }
  }
}
```

---

## Troubleshooting

**`spawn uvx ENOENT` or `command not found: uvx`**

Claude Desktop cannot find `uvx` because GUI apps do not inherit your shell's `PATH`. Use the full absolute path to the binary. Find it by running `which uvx` (macOS/Linux) or `(Get-Command uvx).Source` (Windows), then update your config to use that full path instead of just `uvx`.

---

**`uv --version` returns "command not found" right after installing**

The installer modified `~/.local/bin/env` but has not updated your current shell session. Run:

```bash
source $HOME/.local/bin/env
```

Then try `uv --version` again. To avoid this in future sessions, add the source line to your `~/.zshrc` or `~/.bashrc`.

---

**"Token not found" or "Run start_auth first"**

Two ways to fix this:

1. Call `start_auth` with your `client_id` to run the browser auth flow and save a token automatically.
2. If you already have a token, set `YANDEX_WEBMASTER_API_KEY` in the `env` block of your MCP config — the server will use it directly without needing a token file.

---

**"Authorization timed out"**

The browser approval window is 5 minutes. If you did not approve in time, simply call `start_auth` again to get a fresh code.

---

**API returns 403 or "wrong scopes" error**

Your Yandex OAuth app was created without the required permissions. Go to [https://oauth.yandex.ru](https://oauth.yandex.ru), delete the existing app, and create a new one with both `webmaster:hostinfo` and `webmaster:verify` scopes enabled under Yandex.Webmaster. Then run `start_auth` again with the new `client_id`.

---

**`host_id` format errors**

Use the colon-separated format returned by `get_hosts`. Common mistakes:

| Wrong | Correct |
|-------|---------|
| `https://example.com` | `https:example.com:443` |
| `example.com` | `https:example.com:443` |
| `https:example.com` | `https:example.com:443` |

The port number is required. Use `443` for HTTPS and `80` for HTTP unless your site runs on a non-standard port.

---

**Config changes not taking effect**

Claude Desktop only reads its config file at startup. After editing the config, fully quit the app — on macOS use `Cmd+Q` (closing the window is not enough), on Windows right-click the tray icon and choose Quit — then reopen it.

---

## License

MIT — see [LICENSE](LICENSE)
