"""HTTP client + OAuth browser flow for Yandex Webmaster API v4.1."""

import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import httpx
from platformdirs import user_config_dir

BASE_URL = "https://api.webmaster.yandex.net/v4"
TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_STATUSES = {500, 502, 503}

AUTH_URL = "https://oauth.yandex.ru/authorize"


def _config_dir() -> Path:
    """Return config directory. Respects YANDEX_WEBMASTER_CONFIG_PATH env var."""
    override = os.environ.get("YANDEX_WEBMASTER_CONFIG_PATH")
    if override:
        return Path(override)
    return Path(user_config_dir("yandex-webmaster-mcp", appauthor=False))


def _token_path() -> Path:
    """Return token file path. Respects YANDEX_WEBMASTER_TOKEN_FILE env var."""
    override = os.environ.get("YANDEX_WEBMASTER_TOKEN_FILE")
    if override:
        return Path(override)
    return _config_dir() / "token.json"


def _client_secret_path() -> Path:
    """Return client_secret file path. Respects YANDEX_WEBMASTER_CLIENT_ID_FILE env var."""
    override = os.environ.get("YANDEX_WEBMASTER_CLIENT_ID_FILE")
    if override:
        return Path(override)
    return _config_dir() / "client_secret.json"


class WebmasterAPIError(Exception):
    """Yandex Webmaster API error."""

    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{status_code}] {error_code}: {message}")


class WebmasterClient:
    """Sync HTTP client for Yandex Webmaster API."""

    def __init__(self, token: str | None = None):
        if token:
            self.token = token
        else:
            path = _token_path()
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    self.token = data.get("access_token")
                    if not self.token:
                        raise ValueError("token.json missing 'access_token' field")
                except (json.JSONDecodeError, OSError, ValueError) as e:
                    raise ValueError(f"Failed to read token file at {path}: {e}")
            else:
                hint = ""
                secret = _client_secret_path()
                if secret.exists():
                    try:
                        cid = json.loads(secret.read_text()).get("client_id", "")
                        if cid:
                            hint = f" Saved client_id: {cid}. Call start_auth(client_id='{cid}') to re-authenticate."
                    except Exception:
                        pass
                raise ValueError(
                    f"No token found at {path}. Run start_auth to authenticate.{hint}"
                )

        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Authorization": f"OAuth {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json; charset=UTF-8",
            },
            timeout=TIMEOUT,
        )

    @staticmethod
    def encode_host_id(host_id: str) -> str:
        """URL-encode host_id: 'https:example.com:443' -> 'https%3Aexample.com%3A443'."""
        return quote(host_id, safe="")

    def host_url(self, user_id: str, host_id: str) -> str:
        """Build base path for host endpoints."""
        return f"/user/{user_id}/hosts/{self.encode_host_id(host_id)}"

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict | list | None:
        """Make HTTP request with retry on 500/502/503."""
        raw_params: list[tuple[str, str]] = []
        if params:
            for key, val in params.items():
                if val is None:
                    continue
                if isinstance(val, list):
                    for v in val:
                        raw_params.append((key, str(v)))
                else:
                    raw_params.append((key, str(val)))

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._client.request(
                    method,
                    path,
                    params=raw_params if raw_params else None,
                    json=json_body,
                )

                if resp.status_code in RETRY_STATUSES and attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue

                if resp.status_code == 204:
                    return None

                data = resp.json() if resp.content else {}

                if resp.status_code >= 400:
                    error_code = data.get("error_code", f"HTTP_{resp.status_code}")
                    error_msg = data.get("error_message", data.get("message", resp.text))
                    raise WebmasterAPIError(resp.status_code, error_code, error_msg)

                return data

            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise WebmasterAPIError(0, "TIMEOUT", f"Request timed out: {e}")

            except httpx.HTTPError as e:
                last_exc = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise WebmasterAPIError(0, "CONNECTION_ERROR", str(e))

        raise WebmasterAPIError(0, "MAX_RETRIES", f"Failed after {MAX_RETRIES} retries: {last_exc}")

    def get(self, path: str, params: dict | None = None) -> dict | list | None:
        return self._request("GET", path, params=params)

    def post(self, path: str, params: dict | None = None, json_body: dict | None = None) -> dict | list | None:
        return self._request("POST", path, params=params, json_body=json_body)

    def delete(self, path: str) -> dict | list | None:
        return self._request("DELETE", path)


class OAuthFlow:
    """Yandex OAuth browser (implicit) flow."""

    @staticmethod
    def get_auth_url(client_id: str) -> str:
        """Return the authorization URL for the user to open in a browser."""
        return f"{AUTH_URL}?response_type=token&client_id={client_id}"

    @staticmethod
    def save_client_id(client_id: str) -> Path:
        """Save client_id to client_secret.json in config dir."""
        path = _client_secret_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"client_id": client_id}))
        return path

    @staticmethod
    def load_client_id() -> str:
        """Read saved client_id from client_secret.json. Returns empty string if not found."""
        path = _client_secret_path()
        try:
            return json.loads(path.read_text()).get("client_id", "")
        except Exception:
            return ""

    @staticmethod
    def save_token(access_token: str) -> Path:
        """Save access token to token.json in config dir."""
        path = _token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"access_token": access_token, "token_type": "bearer"}))
        return path
