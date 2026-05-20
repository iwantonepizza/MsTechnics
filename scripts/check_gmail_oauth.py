from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Config.settings")


DEFAULT_QUERY = "from:service@alimail.vnnox.com is:unread"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Gmail OAuth credentials for the VNNOX parser.")
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Gmail search query used for the verification request.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=1,
        help="How many Gmail message ids to include in the JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        import django
        from django.core.exceptions import ImproperlyConfigured
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError
    except ModuleNotFoundError as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 1

    try:
        django.setup()
        from apps.integrations.gmail_alarms.services import check_gmail_oauth

        result = check_gmail_oauth(query=args.query, max_results=args.max_results)
    except (FileNotFoundError, ImproperlyConfigured, OSError, RefreshError, HttpError, ValueError) as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stderr, ensure_ascii=False)
        sys.stderr.write("\n")
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
