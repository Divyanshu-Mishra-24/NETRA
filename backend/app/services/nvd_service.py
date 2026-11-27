"""Official NIST NVD CVE API 2.0 client with bounded retries and caching."""

from __future__ import annotations

import os
import time
import logging
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NVDNotFoundError(Exception):
    pass


class NVDAuthenticationError(Exception):
    pass


class NVDRateLimitError(Exception):
    pass


class NVDUnavailableError(Exception):
    pass


class NVDBadRequestError(Exception):
    pass


class NVDResponseError(Exception):
    pass


class NVDClient:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "NVD_API_BASE_URL",
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
        ).rstrip("/")
        self.api_key = os.getenv("NVD_API_KEY")
        self.timeout = float(os.getenv("NVD_TIMEOUT_SECONDS", "15"))
        self.cache_ttl = float(os.getenv("NVD_CACHE_TTL_HOURS", "24")) * 3600
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["apiKey"] = self.api_key
        return headers

    def _get(self, params: dict[str, str | int]) -> dict[str, Any]:
        cache_key = str(sorted(params.items()))
        now = time.time()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and now - cached[0] < self.cache_ttl:
                return cached[1]

        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = httpx.get(
                    self.base_url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if response.status_code == 400:
                    raise NVDBadRequestError("NVD rejected the request parameters")
                if response.status_code == 404:
                    raise NVDNotFoundError("CVE or NVD resource was not found")
                if response.status_code == 403:
                    raise NVDAuthenticationError("NVD rejected the API key or request")
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    logger.warning(
                        "NVD rate limit reached; Retry-After=%s",
                        retry_after or "not provided",
                    )
                    raise NVDRateLimitError("NVD rate limit reached")
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"NVD service returned {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                try:
                    data = response.json()
                except (ValueError, json.JSONDecodeError) as exc:
                    raise NVDResponseError("NVD returned invalid JSON") from exc
                if not isinstance(data, dict):
                    raise NVDResponseError("NVD returned an unexpected JSON response")
                vulnerabilities = data.get("vulnerabilities")
                if vulnerabilities is not None and not isinstance(vulnerabilities, list):
                    raise NVDResponseError("NVD response contains an invalid vulnerabilities field")
                with self._lock:
                    self._cache[cache_key] = (now, data)
                return data
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(delay)
                    delay *= 2
            except (NVDAuthenticationError, NVDRateLimitError):
                raise
        raise NVDUnavailableError("NVD is temporarily unavailable") from last_error

    def search(self, keyword: str, start_index: int = 0, results_per_page: int = 20) -> dict[str, Any]:
        if not keyword or not keyword.strip():
            raise ValueError("A search keyword is required")
        data = self._get(
            {
                "keywordSearch": keyword.strip(),
                "startIndex": max(0, start_index),
                "resultsPerPage": min(max(results_per_page, 1), 2000),
            }
        )
        vulnerabilities = data.get("vulnerabilities", [])
        return {
            "total_results": int(data.get("totalResults", len(vulnerabilities))),
            "start_index": int(data.get("startIndex", start_index)),
            "results_per_page": int(data.get("resultsPerPage", results_per_page)),
            "items": [parse_cve(item["cve"]) for item in vulnerabilities if item.get("cve")],
        }

    def get_cve(self, cve_id: str) -> dict[str, Any]:
        data = self._get({"cveId": cve_id.upper()})
        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            raise NVDNotFoundError(f"CVE '{cve_id}' was not found")
        return parse_cve(vulnerabilities[0]["cve"])


nvd_client = NVDClient()


def _english_description(cve: dict[str, Any]) -> str | None:
    for description in cve.get("descriptions", []) or []:
        if description.get("lang") == "en":
            return description.get("value")
    return None


def parse_cvss(metrics: dict[str, Any]) -> tuple[float | None, str | None, str | None, str | None]:
    if not isinstance(metrics, dict):
        return None, None, None, None
    for metric_name, version, cvss_key in (
        ("cvssMetricV40", "4.0", "cvssData"),
        ("cvssMetricV31", "3.1", "cvssData"),
        ("cvssMetricV30", "3.0", "cvssData"),
        ("cvssMetricV2", "2.0", "cvssData"),
    ):
        entries = metrics.get(metric_name) or []
        if entries:
            entry = entries[0]
            data = entry.get(cvss_key) or {}
            score = data.get("baseScore")
            vector = data.get("vectorString")
            severity = data.get("baseSeverity") or entry.get("baseSeverity")
            if score is not None:
                return float(score), version, vector, str(severity).lower() if severity else None
    return None, None, None, None


def parse_cve(cve: dict[str, Any]) -> dict[str, Any]:
    cve_id = cve.get("id") or cve.get("cveId")
    description = _english_description(cve)
    score, version, vector, severity = parse_cvss(cve.get("metrics") or {})
    if severity is None and score is not None:
        if score >= 9:
            severity = "critical"
        elif score >= 7:
            severity = "high"
        elif score >= 4:
            severity = "medium"
        elif score > 0:
            severity = "low"
        else:
            severity = "none"

    rejected = any(
        "rejected" in (item.get("value") or "").lower()
        for item in cve.get("descriptions", []) or []
    )
    references = [
        item.get("url")
        for item in cve.get("references", []) or []
        if item.get("url")
    ]
    return {
        "cve_id": cve_id,
        "description": description,
        "severity": severity,
        "cvss_score": score,
        "cvss_version": version,
        "cvss_vector": vector,
        "published_at": cve.get("published"),
        "last_modified_at": cve.get("lastModified"),
        "source": "nvd",
        "references": references,
        "last_fetched_at": datetime.now(timezone.utc).isoformat(),
        "rejected": rejected,
    }
