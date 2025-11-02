# ical_program.py
import datetime as dt
import threading
import urllib.request
from typing import Dict, List, Optional


class InMemoryCalendarSchedule:
    """
    Tiny stand-in for Niagara BCalendarSchedule:
    stores one 'event per day' as name strings keyed by YYYY-MM-DD.
    """
    def __init__(self):
        self._days: Dict[str, str] = {}

    def clear_all(self) -> None:
        self._days.clear()

    def add_day(self, y: int, m: int, d: int, label: str) -> None:
        key = f"{y:04d}-{m:02d}-{d:02d}"
        # If multiple events fall on same day, append
        if key in self._days and self._days[key] != label:
            self._days[key] = f"{self._days[key]} / {label}"
        else:
            self._days[key] = label

    def keys_sorted(self) -> List[str]:
        return sorted(self._days.keys())

    def get(self, k: str) -> Optional[str]:
        return self._days.get(k)

    def as_dict(self) -> Dict[str, str]:
        return dict(self._days)


class IcalProgram:
    """
    ProgramObject-like Python class with explicit getters/setters,
    heartbeat scheduling, statusTrace/apiResponse, and ICS ingest.
    """

    def __init__(self):
        # "Slots"
        self._calendar = InMemoryCalendarSchedule()
        self._updateNow: bool = False
        self._apiResponse: str = ""
        self._executePeriodSeconds: int = 0         # 0 = no heartbeat
        self._logToConsole: bool = True
        self._lastFetchTs: str = ""
        self._statusTrace: str = "OK"
        self._icsUrl: str = ""                      # set this via set_icsUrl()
        self._eventsAdded: int = 0
        self._nextEvent: str = ""
        self._maxEvents: int = 0                    # 0 = no cap
        self._namePrefix: str = "Event"

        # runtime state
        self._ticket: Optional[threading.Timer] = None
        self._lastIcsHash: Optional[str] = None

    # -------------------------
    # Getters / Setters (Niagara-style names)
    # -------------------------
    def getCalendar(self) -> InMemoryCalendarSchedule: return self._calendar
    def getUpdateNow(self) -> bool: return self._updateNow
    def setUpdateNow(self, v: bool) -> None: self._updateNow = bool(v)

    def getApiResponse(self) -> str: return self._apiResponse
    def setApiResponse(self, v: str) -> None: self._apiResponse = str(v)

    def getExecutePeriodSeconds(self) -> int: return self._executePeriodSeconds
    def setExecutePeriodSeconds(self, v: int) -> None:
        self._executePeriodSeconds = max(0, min(int(v), 3600))

    def getLogToConsole(self) -> bool: return self._logToConsole
    def setLogToConsole(self, v: bool) -> None: self._logToConsole = bool(v)

    def getLastFetchTs(self) -> str: return self._lastFetchTs
    def setLastFetchTs(self, v: str) -> None: self._lastFetchTs = str(v)

    def getStatusTrace(self) -> str: return self._statusTrace
    def setStatusTrace(self, v: str) -> None: self._statusTrace = str(v)

    def getIcsUrl(self) -> str: return self._icsUrl
    def setIcsUrl(self, v: str) -> None: self._icsUrl = str(v).strip()

    def getEventsAdded(self) -> int: return self._eventsAdded
    def setEventsAdded(self, v: int) -> None: self._eventsAdded = int(v)

    def getNextEvent(self) -> str: return self._nextEvent
    def setNextEvent(self, v: str) -> None: self._nextEvent = str(v)

    def getMaxEvents(self) -> int: return self._maxEvents
    def setMaxEvents(self, v: int) -> None: self._maxEvents = max(0, int(v))

    def getNamePrefix(self) -> str: return self._namePrefix
    def setNamePrefix(self, v: str) -> None: self._namePrefix = str(v).strip() or "Event"

    # -------------------------
    # Lifecycle
    # -------------------------
    def onStart(self) -> None:
        self._normalize_defaults()
        ok = self._refresh_from_ics(force=True)
        if not ok:
            self._safe_status("ERROR: startup - initial fetch failed")
        self._schedule_next()
        self._log("Started.")

    def onExecute(self) -> None:
        try:
            if self.getUpdateNow():
                self._log("updateNow=TRUE → forcing refresh")
                self._refresh_from_ics(force=True)
                self.setUpdateNow(False)
                self._schedule_next()
                return
        except Exception:
            pass

        self._refresh_from_ics(force=False)
        self._schedule_next()

    def onStop(self) -> None:
        if self._ticket:
            self._ticket.cancel()
            self._ticket = None
        self._log("Stopped.")

    # -------------------------
    # Scheduling
    # -------------------------
    def _schedule_next(self) -> None:
        if self._ticket:
            self._ticket.cancel()
            self._ticket = None

        period = self.getExecutePeriodSeconds()
        if period <= 0:
            self._log("Heartbeat disabled (executePeriodSeconds <= 0).")
            return

        def _tick():
            try:
                self.onExecute()
            except Exception as e:
                self._fail("timer", str(e))

        self._ticket = threading.Timer(period, _tick)
        self._ticket.daemon = True
        self._ticket.start()
        self._log(f"Next execute in {period}s")

    # -------------------------
    # Core
    # -------------------------
    def _refresh_from_ics(self, force: bool) -> bool:
        url = self.getIcsUrl()
        if not url:
            self._fail("refreshFromIcs", "icsUrl is empty")
            return False

        try:
            ics_text = self._http_get(url)
        except Exception as e:
            self._fail("httpGet", str(e))
            return False

        # Skip rewrite if unchanged (unless forced)
        cur_hash = str(hash(ics_text))
        changed = (self._lastIcsHash != cur_hash)
        if not force and not changed:
            self._ok(f"ICS unchanged; using cached calendar (len={len(ics_text)})")
            self._trace_ok()
            self._update_next_event()
            return True

        # Parse VEVENTs into day->label
        day_map: Dict[str, str] = {}
        self._parse_ics_into(ics_text, day_map)

        # Optional maxEvents cap (keep earliest N)
        if self.getMaxEvents() > 0:
            keys = sorted(day_map.keys())[: self.getMaxEvents()]
            day_map = {k: day_map[k] for k in keys}

        # Rewrite calendar
        self._calendar.clear_all()
        made = 0
        for k in sorted(day_map.keys()):
            y, m, d = map(int, k.split("-"))
            self._calendar.add_day(y, m, d, f"{self.getNamePrefix()}:{day_map[k]}")
            made += 1

        self.setEventsAdded(made)
        self._lastIcsHash = cur_hash
        self.setLastFetchTs(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._ok(f"ICS parsed days={len(day_map)}; created/updated={made}")
        self._trace_ok()
        self._update_next_event()
        return True

    # -------------------------
    # Helpers
    # -------------------------
    def _update_next_event(self) -> None:
        today = dt.date.today().isoformat()
        keys = self._calendar.keys_sorted()
        next_key = None
        for k in keys:
            if k >= today:
                next_key = k
                break
        if next_key:
            label = self._calendar.get(next_key) or ""
            days = (dt.date.fromisoformat(next_key) - dt.date.today()).days
            self.setNextEvent(f"{next_key} ({label}; in {days} days)")
        else:
            self.setNextEvent("N/A")

    def _parse_ics_into(self, ics: str, out: Dict[str, str]) -> None:
        """
        Minimal VEVENT parser supporting:
          DTSTART[:|;VALUE=DATE]YYYYMMDD[THHMMSSZ]
          DTEND[:|;VALUE=DATE]YYYYMMDD[THHMMSSZ]   (exclusive)
          SUMMARY: text
        """
        in_event = False
        dt_start = None
        dt_end = None
        summary = None

        for raw in ics.splitlines():
            line = raw.strip()
            if line.upper() == "BEGIN:VEVENT":
                in_event = True
                dt_start = dt_end = None
                summary = None
                continue
            if line.upper() == "END:VEVENT":
                if in_event and dt_start:
                    s = self._parse_ics_date(dt_start)
                    e = self._parse_ics_date(dt_end) if dt_end else (s + dt.timedelta(days=1))
                    if s and e:
                        d = s
                        while d < e and d < s + dt.timedelta(days=366 * 3):
                            key = d.strftime("%Y-%m-%d")
                            label = (summary or "Event").strip()
                            if key in out and out[key] != label:
                                out[key] = f"{out[key]} / {label}"
                            else:
                                out[key] = label
                            d += dt.timedelta(days=1)
                in_event = False
                continue
            if not in_event:
                continue

            if line.startswith("DTSTART"):
                dt_start = line.split(":", 1)[1]
            elif line.startswith("DTEND"):
                dt_end = line.split(":", 1)[1]
            elif line.startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):]

    @staticmethod
    def _parse_ics_date(token: Optional[str]) -> Optional[dt.date]:
        if not token:
            return None
        if "T" in token:
            token = token.split("T", 1)[0]
        if len(token) != 8 or not token.isdigit():
            return None
        y, m, d = int(token[:4]), int(token[4:6]), int(token[6:8])
        try:
            return dt.date(y, m, d)
        except ValueError:
            return None

    def _http_get(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "python-ical-program/1.0", "Accept": "text/calendar,*/*"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        self._ok(f"HTTP {getattr(resp, 'status', 200)} bytes={len(data)}")
        return data.decode("utf-8", errors="replace")

    # ---- status/log helpers ----
    def _ok(self, msg: str) -> None: self.setApiResponse(msg)
    def _fail(self, where: str, msg: str) -> None:
        self.setApiResponse(f"ERROR: {where} - {msg}")
        self.setStatusTrace(f"ERROR: {where} - {msg}")
        self._log(f"[ERROR] {where}: {msg}")

    def _trace_ok(self) -> None:
        # Clear stale error if present
        cur = self.getStatusTrace() or ""
        if not cur.startswith("ERROR"):
            self.setStatusTrace("OK")
        else:
            self.setStatusTrace("OK")

    def _safe_status(self, s: str) -> None:
        self.setStatusTrace(s)

    def _log(self, msg: str) -> None:
        if self.getLogToConsole():
            print(f"[IcalProgram] {msg}")

    def _normalize_defaults(self) -> None:
        if not self.getIcsUrl():
            # default to NextSpaceFlight public GCal ICS (you can override)
            self.setIcsUrl(
                "https://calendar.google.com/calendar/ical/"
                "nextspaceflight.com_l328q9n2alm03mdukb05504c44%40group.calendar.google.com/public/basic.ics"
            )
        if self.getNamePrefix() == "":
            self.setNamePrefix("Event")
        # default: no heartbeat; run once unless you set a period
        if self.getExecutePeriodSeconds() < 0:
            self.setExecutePeriodSeconds(0)


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    prog = IcalProgram()
    prog.setLogToConsole(True)
    prog.setExecutePeriodSeconds(0)  # set e.g. 3600 to poll hourly
    prog.setNamePrefix("Launch")
    # prog.setIcsUrl("https://…/basic.ics")  # optional override
    prog.onStart()  # runs one fetch

    # Show results
    print("\n== apiResponse:", prog.getApiResponse())
    print("== statusTrace:", prog.getStatusTrace())
    print("== lastFetchTs:", prog.getLastFetchTs())
    print("== eventsAdded:", prog.getEventsAdded())
    print("== nextEvent  :", prog.getNextEvent())
    print("\n== Calendar days (first 10) ==")
    for k in list(prog.getCalendar().keys_sorted())[:10]:
        print(k, "->", prog.getCalendar().get(k))
