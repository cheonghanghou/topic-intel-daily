import json
import time
import urllib.request

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_text(url, headers=None):
    last_error = None
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers=merged_headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def get_json(url, headers=None):
    return json.loads(get_text(url, headers=headers))
