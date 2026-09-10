"""
Wikipedia API - Get descriptions and information about places
Free! No API key needed.

Resilience features:
- 5-second connect + read timeout per request
- Up to 2 retries with exponential backoff on transient errors
- Circuit breaker: disables Wikipedia after 3 consecutive failures
  to prevent 40 × timeout = multi-minute hangs
"""

import time
import logging
from typing import Optional, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_TIMEOUT = (3, 5)       # (connect_timeout, read_timeout) in seconds
_MAX_FAILURES = 3       # circuit breaker threshold
_MAX_CALLS = 20         # safety cap: never do more than this many Wikipedia calls per request


def _make_session() -> requests.Session:
    """Return a requests Session with automatic urllib3-level retries on connection errors."""
    session = requests.Session()
    session.headers.update({"User-Agent": "TripPlanner/1.0 (Educational)"})

    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class WikipediaAPI:
    """
    Get information from Wikipedia with circuit-breaker and timeout protection.

    After _MAX_FAILURES consecutive network failures the circuit opens and all
    subsequent calls return None immediately, avoiding cascading timeouts.
    """

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.session = _make_session()
        self._failure_count = 0
        self._circuit_open = False
        self._call_count = 0

    def get_info(self, title: str) -> Optional[Dict]:
        """
        Get Wikipedia info about a place/topic.

        Returns:
            {"title": "...", "summary": "...", "url": "..."} or None
        """
        # Circuit breaker — stop hammering a clearly broken connection
        if self._circuit_open:
            return None

        # Safety cap — never issue more than _MAX_CALLS per pipeline run
        if self._call_count >= _MAX_CALLS:
            logger.debug("Wikipedia call cap reached (%d); skipping %s", _MAX_CALLS, title)
            return None

        self._call_count += 1

        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "format": "json",
            "exintro": True,
            "exlimit": 1,
        }

        try:
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            pages = data.get("query", {}).get("pages", {})

            for page_id, page in pages.items():
                if page_id != "-1":  # Valid page
                    extract = page.get("extract", "") or ""
                    if len(extract) > 300:
                        extract = extract[:300] + "..."

                    # Success — reset failure counter
                    self._failure_count = 0

                    return {
                        "title": page.get("title", title),
                        "summary": extract,
                        "url": (
                            "https://en.wikipedia.org/wiki/"
                            + page.get("title", "").replace(" ", "_")
                        ),
                    }

            # Page not found — not a network error, don't count as failure
            return None

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            self._failure_count += 1
            logger.warning(
                "Wikipedia network error for '%s' (failure %d/%d): %s",
                title, self._failure_count, _MAX_FAILURES, exc,
            )
            if self._failure_count >= _MAX_FAILURES:
                logger.error(
                    "Wikipedia circuit breaker OPEN after %d failures — "
                    "skipping all further Wikipedia enrichment.",
                    _MAX_FAILURES,
                )
                self._circuit_open = True
            return None

        except Exception as exc:
            logger.debug("Wikipedia error for '%s': %s", title, exc)
            return None