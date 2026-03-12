from __future__ import annotations

import csv
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_CSV_PATH = os.path.join(BASE_DIR, "uszips.csv")
NOAA_ALERTS_URL = "https://api.weather.gov/alerts/active"
SEVERITIES = {"Severe", "Extreme"}
CACHE_TTL_SECONDS = 3600
USER_AGENT = "WeatherAlertPublic/1.0 (vgvishal31@gmail.com)"

STATE_NAME_TO_CODE = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}

_request_timeout = 30
_cache_lock = threading.Lock()
_city_index_cache: dict[str, dict[str, Any]] | None = None
_nationwide_cache: dict[str, Any] | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_spaces(value: str) -> str:
    return " ".join(value.replace(",", " ").replace(".", " ").split())


def _normalize_city_key(value: str) -> str:
    normalized = _normalize_spaces(value).upper()
    normalized = normalized.replace("ST ", "SAINT ")
    normalized = normalized.replace("FT ", "FORT ")
    normalized = normalized.replace("MT ", "MOUNT ")
    return normalized


def _normalize_state_code(value: str) -> str:
    normalized = _normalize_spaces(value).upper()
    if len(normalized) == 2:
        return normalized
    return STATE_NAME_TO_CODE.get(normalized, normalized)


def _iso_or_empty(value: str | None) -> str:
    if not value:
        return ""
    return value


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_active(properties: dict[str, Any]) -> bool:
    if properties.get("messageType") == "Cancel":
        return False
    if properties.get("severity") not in SEVERITIES:
        return False
    if properties.get("status") != "Actual":
        return False
    expires_at = _parse_timestamp(properties.get("expires"))
    ends_at = _parse_timestamp(properties.get("ends"))
    now = _utc_now()
    if expires_at and expires_at < now:
        return False
    if ends_at and ends_at < now:
        return False
    return True


def _extract_states(properties: dict[str, Any]) -> list[str]:
    geocode = properties.get("geocode") or {}
    states: set[str] = set()
    for code in geocode.get("UGC", []) or []:
        if isinstance(code, str) and len(code) >= 2:
            states.add(code[:2])
    return sorted(states)


def _alert_to_summary(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    state_codes = _extract_states(properties)
    onset = _parse_timestamp(properties.get("onset"))
    effective = _parse_timestamp(properties.get("effective"))
    expires_at = _parse_timestamp(properties.get("expires"))
    ends_at = _parse_timestamp(properties.get("ends"))
    area_desc = (properties.get("areaDesc") or "").strip()
    areas = [part.strip() for part in area_desc.split(";") if part.strip()]
    return {
        "id": properties.get("id") or feature.get("id") or "",
        "event": properties.get("event") or "Weather Alert",
        "severity": properties.get("severity") or "",
        "headline": properties.get("headline") or "",
        "area_desc": area_desc,
        "areas": areas[:8],
        "states": state_codes,
        "instruction": (properties.get("instruction") or "").strip(),
        "sender": properties.get("senderName") or "",
        "response": properties.get("response") or "",
        "onset": _iso_or_empty(properties.get("onset")),
        "effective": _iso_or_empty(properties.get("effective")),
        "expires": _iso_or_empty(properties.get("expires")),
        "ends": _iso_or_empty(properties.get("ends")),
        "onset_sort": onset.isoformat() if onset else "",
        "effective_sort": effective.isoformat() if effective else "",
        "expires_sort": expires_at.isoformat() if expires_at else "",
        "ends_sort": ends_at.isoformat() if ends_at else "",
        "url": properties.get("@id") or "",
    }


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
        }
    )
    return session


def _load_city_index() -> dict[str, dict[str, Any]]:
    global _city_index_cache
    with _cache_lock:
        if _city_index_cache is not None:
            return _city_index_cache

        aggregates: dict[str, dict[str, Any]] = {}
        with open(ZIP_CSV_PATH, "r", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                city = (row.get("city") or "").strip()
                state = (row.get("state_id") or "").strip()
                lat_text = (row.get("lat") or "").strip()
                lon_text = (row.get("lng") or "").strip()
                if not city or not state or not lat_text or not lon_text:
                    continue
                key = f"{_normalize_city_key(city)}|{_normalize_state_code(state)}"
                item = aggregates.setdefault(
                    key,
                    {
                        "city": city,
                        "state": state.upper(),
                        "lat_total": 0.0,
                        "lon_total": 0.0,
                        "count": 0,
                    },
                )
                item["lat_total"] += float(lat_text)
                item["lon_total"] += float(lon_text)
                item["count"] += 1

        _city_index_cache = {}
        for key, item in aggregates.items():
            _city_index_cache[key] = {
                "city": item["city"],
                "state": item["state"],
                "lat": round(item["lat_total"] / item["count"], 4),
                "lon": round(item["lon_total"] / item["count"], 4),
            }
        return _city_index_cache


def fetch_nationwide_alerts(force_refresh: bool = False) -> dict[str, Any]:
    global _nationwide_cache
    with _cache_lock:
        if (
            not force_refresh
            and _nationwide_cache
            and time.time() - _nationwide_cache["cached_at"] < CACHE_TTL_SECONDS
        ):
            return _nationwide_cache["payload"]

    session = _build_session()
    response = session.get(NOAA_ALERTS_URL, timeout=_request_timeout)
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features", [])

    alerts = []
    state_counts: dict[str, int] = defaultdict(int)
    for feature in features:
        properties = feature.get("properties") or {}
        if not _is_active(properties):
            continue
        summary = _alert_to_summary(feature)
        alerts.append(summary)
        for state_code in summary["states"]:
            state_counts[state_code] += 1

    alerts.sort(
        key=lambda item: (
            item["severity"] != "Extreme",
            item["effective_sort"] or item["onset_sort"] or "",
        )
    )
    now = _utc_now().isoformat()
    nationwide = {
        "generated_at": now,
        "alert_count": len(alerts),
        "state_count": len(state_counts),
        "states": [
            {"state": state, "active_alerts": count}
            for state, count in sorted(state_counts.items())
        ],
        "alerts": alerts,
    }

    with _cache_lock:
        _nationwide_cache = {
            "cached_at": time.time(),
            "payload": nationwide,
        }
    return nationwide


def search_city_state(city: str, state: str) -> dict[str, Any]:
    city = _normalize_spaces(city.strip())
    state = _normalize_state_code(state.strip())
    if not city or not state:
        raise ValueError("City and state are required.")

    city_index = _load_city_index()
    location = city_index.get(f"{_normalize_city_key(city)}|{state}")
    if location is None:
        raise LookupError("City/state not found. Try a nearby city name or a 2-letter state code.")

    session = _build_session()
    response = session.get(
        NOAA_ALERTS_URL,
        params={"point": f"{location['lat']},{location['lon']}"},
        timeout=_request_timeout,
    )
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features", [])

    matches = []
    for feature in features:
        properties = feature.get("properties") or {}
        if not _is_active(properties):
            continue
        matches.append(_alert_to_summary(feature))

    matches.sort(
        key=lambda item: (
            item["severity"] != "Extreme",
            item["effective_sort"] or item["onset_sort"] or "",
        )
    )
    return {
        "generated_at": _utc_now().isoformat(),
        "query": {
            "city": location["city"],
            "state": location["state"],
            "lat": location["lat"],
            "lon": location["lon"],
        },
        "has_alerts": bool(matches),
        "alert_count": len(matches),
        "alerts": matches,
    }
