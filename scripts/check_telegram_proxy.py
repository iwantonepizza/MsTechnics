from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def _mask_proxy_url(proxy_url: str) -> str:
    if "@" not in proxy_url or "://" not in proxy_url:
        return proxy_url
    scheme, rest = proxy_url.split("://", 1)
    credentials, host = rest.rsplit("@", 1)
    username = credentials.split(":", 1)[0]
    return f"{scheme}://{username}:***@{host}"


def check_telegram_proxy() -> dict[str, Any]:
    token = _required_env("TELEGRAM_BOT_TOKEN")
    proxy_url = _required_env("TELEGRAM_PROXY_URL")
    timeout = float(os.environ.get("TELEGRAM_TIMEOUT_SEC", "15"))

    with httpx.Client(proxy=proxy_url, timeout=timeout) as client:
        response = client.get(f"https://api.telegram.org/bot{token}/getMe")
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError(f"Telegram getMe returned unexpected payload: {payload!r}")

    return {
        "ok": True,
        "proxy": _mask_proxy_url(proxy_url),
        "telegram_user": payload.get("result", {}).get("username"),
    }


def main() -> int:
    try:
        result = check_telegram_proxy()
    except (RuntimeError, httpx.HTTPError, ValueError) as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
