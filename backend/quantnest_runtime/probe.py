"""Lightweight container readiness probe; never start Django in a second process."""
import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-mode", choices=("development", "public", "private"), required=True)
    args = parser.parse_args()
    headers = {"X-Forwarded-Proto": "https"}
    token = os.environ.get("QUANTNEST_PROXY_TOKEN")
    if token:
        headers["X-QuantNest-Proxy-Token"] = token
    try:
        request = Request("http://127.0.0.1:8000/health/", headers=headers)
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
            status = json.load(response)
        if not isinstance(status, dict):
            raise ValueError("Invalid readiness response")
        checks = status.get("checks")
        if (
            status.get("mode") != args.require_mode
            or status.get("status") != "healthy"
            or not isinstance(checks, dict)
            or not checks
            or not all(checks.values())
        ):
            raise ValueError("Unready deployment")
    except (HTTPError, URLError, OSError, ValueError):
        raise SystemExit("API readiness probe failed") from None


if __name__ == "__main__":
    main()
