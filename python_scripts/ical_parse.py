# ical_parse.py
# Pure synchronous iCal parser → simple schedule dict → exit.
# - Works with either a URL (https/ical/webcal) or a local .ics file path.
# - Keeps only FUTURE events (relative to local tz).
# - Prints concise logs and exits with code 0 on success, 1 on failure.

from __future__ import annotations

import sys
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

# stdlib tz (Python 3.9+)
try:
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:
    ZoneInfo = None  # pragma: no cover

# Optional: requests for URL fetch (falls back to urllib if missing)
try:
    import requests  # type: ignore
except Exception:
    requests = None  # pragma: no cover

import urllib.request


# -------- Config (tweak as you like) --------
LOCAL_TZ_NAME = "America/Chicago"  # matches your environment
EVENT_NAME_PREFIX = "ICal_"
KEEP_MAX_EVENTS = 100


@dataclass
class ICalEvent:
    summary: str
    start: datetime
    location: Optional[str] = None
    description: Optional[str] = None


def load_ics(source: str) -> str:
    """Load ICS text from URL (http/https/webcal) or local file path."""
    if re.match(r"^(https?|webcal)://", source, re.IGNORECASE):
        url = source.replace("webcal://", "https://")
        if requests:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        # fallback to urllib
        with urllib.request.urlopen(url, timeout=30) as fh:  # nosec B310
            return fh.read().decode("utf-8", errors="replace")
    # Local file
    with open(source, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def unfold_ical_lines(text: str) -> List[str]:
    """Handle iCal line folding (continuations start with a single space or tab)."""
    raw_lines = text.splitlines()
    lines: List[str] = []
    for line in raw_lines:
        if (line.startswith(" ") or line.startswith("\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def get_local_tz() -> timezone:
    if ZoneInfo is None:
        return datetime.now().astimezone().tzinfo or timezone.utc
    try:
        return ZoneInfo(LOCAL_TZ_NAME)
    except Exception:
        return datetime.now().astimezone().tzinfo or timezone.utc


def _normalize_ical_dt(v: str) -> str:
    """
    Normalize common iCal date-time forms to ISO-8601 so fromisoformat() can parse:
      - 20251105T234500Z        -> 2025-11-05T23:45:00+00:00
      - 20251105T234500         -> 2025-11-05T23:45:00
      - 20251105                -> 2025-11-05
    """
    v = v.strip()
    # DATE-TIME with Z
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", v)
    if m:
        y, M, d, h, mnt, s = m.groups()
        return f"{y}-{M}-{d}T{h}:{mnt}:{s}+00:00"
    # DATE-TIME local
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})", v)
    if m:
        y, M, d, h, mnt, s = m.groups()
        return f"{y}-{M}-{d}T{h}:{mnt}:{s}"
    # DATE only
    m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", v)
    if m:
        y, M, d = m.groups()
        return f"{y}-{M}-{d}"
    return v  # last resort; may fail later, that’s okay


def parse_ical_datetime(value: str, params: Dict[str, str], local_tz: timezone) -> Optional[datetime]:
    """
    Parse DTSTART / DTEND values with minimal param handling.
    Supports:
      - Zulu UTC timestamps
      - local floating timestamps → localized to local_tz
      - DATE (all-day) → start-of-day in local_tz
      - DTSTART;TZID=America/New_York:20251101T13000000  (basic TZID support)
    """
    # Extract TZID if present
    tzid = params.get("TZID")
    iso = _normalize_ical_dt(value)

    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return None

    # If date only → make it local midnight
    if dt.tzinfo is None and len(iso) == 10:
        return datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=local_tz)

    # If TZ given and dt is naive, attach that tz; else if naive, assume local
    if dt.tzinfo is None:
        if tzid and ZoneInfo is not None:
            try:
                tz = ZoneInfo(tzid)
                return dt.replace(tzinfo=tz).astimezone(local_tz)
            except Exception:
                return dt.replace(tzinfo=local_tz)
        return dt.replace(tzinfo=local_tz)

    # If already aware, convert to local tz
    return dt.astimezone(local_tz)


def split_prop(line: str) -> Tuple[str, Dict[str, str], str]:
    """
    Split a VCALENDAR property line into (name, params, value).
    Example: 'DTSTART;TZID=America/Chicago:20251101T123000' ->
      ('DTSTART', {'TZID':'America/Chicago'}, '20251101T123000')
    """
    if ":" not in line:
        return line, {}, ""
    head, value = line.split(":", 1)
    parts = head.split(";")
    name = parts[0].strip().upper()
    params: Dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().upper()] = v.strip()
        else:
            params[p.strip().upper()] = ""
    return name, params, value.strip()


def parse_ics(text: str, local_tz: timezone) -> List[ICalEvent]:
    """
    Super-light iCal VEVENT parser: grabs SUMMARY, DTSTART, LOCATION, DESCRIPTION.
    Ignores canceled/past events.
    """
    lines = unfold_ical_lines(text)
    events: List[ICalEvent] = []

    in_event = False
    cur: Dict[str, Tuple[Dict[str, str], str]] = {}

    print("Done 1")  # keep from your logs

    for line in lines:
        if line.strip().upper() == "BEGIN:VEVENT":
            in_event = True
            cur = {}
            print("[IcalProgram] ... found BEGIN:VEVENT")
            continue
        if line.strip().upper() == "END:VEVENT":
            if in_event:
                # build event
                summary_val = cur.get("SUMMARY", ({}, ""))[1].strip()
                dt_params, dt_val = cur.get("DTSTART", ({}, ""))
                start_dt = parse_ical_datetime(dt_val, dt_params, local_tz) if dt_val else None

                if summary_val:
                    print(f"[IcalProgram]        SUMMARY: {summary_val}")
                if "LOCATION" in cur:
                    print(f"[IcalProgram]       LOCATION: {cur['LOCATION'][1]}")
                if "DESCRIPTION" in cur:
                    print(f"[IcalProgram]    DESCRIPTION: {cur['DESCRIPTION'][1]}")

                if summary_val and start_dt and start_dt >= datetime.now(local_tz):
                    ev = ICalEvent(
                        summary=summary_val,
                        start=start_dt,
                        location=cur.get("LOCATION", ({}, ""))[1] or None,
                        description=cur.get("DESCRIPTION", ({}, ""))[1] or None,
                    )
                    print(f"[IcalProgram] ... adding event: {ev.summary} @ {ev.start.isoformat()}")
                    events.append(ev)
                else:
                    print("[IcalProgram] ... skipping event (missing summary/start, or is in the past)")
            in_event = False
            cur = {}
            continue

        if in_event and line and ":" in line:
            name, params, value = split_prop(line)
            if name in ("SUMMARY", "DTSTART", "LOCATION", "DESCRIPTION"):
                cur[name] = (params, value)

    return events


def build_schedule(events: List[ICalEvent]) -> Dict[str, List[str]]:
    """
    Create a simple schedule: { 'YYYY-MM-DD': ['ICal_<Event1>', 'ICal_<Event2>', ...], ... }
    """
    schedule: Dict[str, List[str]] = {}
    for ev in events[:KEEP_MAX_EVENTS]:
        key = ev.start.date().isoformat()
        nm = f"{EVENT_NAME_PREFIX}{ev.summary}"
        schedule.setdefault(key, []).append(nm)
    return schedule


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Usage: python ical_parse.py <ics_url_or_path>")
        return 1

    source = argv[1]
    try:
        local_tz = get_local_tz()
        text = load_ics(source)
        events = parse_ics(text, local_tz=local_tz)

        print(f"[IcalProgram] parsed future events: {len(events)}")
        print(f"[IcalProgram] Preparing to add events: parsed={len(events)}, max={KEEP_MAX_EVENTS}, prefix='{EVENT_NAME_PREFIX}'")

        schedule = build_schedule(events)

        # Print a tiny summary (you can remove this if you prefer silent success)
        if schedule:
            print("\n=== Built Schedule (date → event names) ===")
            for day, names in sorted(schedule.items()):
                print(f"{day}:")
                for n in names:
                    print(f"  - {n}")
        else:
            print("\n(No future events found)")

        print("Done 2")  # your sentinel showing we reached the end
        return 0

    except Exception as e:
        print(f"[IcalProgram] ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
