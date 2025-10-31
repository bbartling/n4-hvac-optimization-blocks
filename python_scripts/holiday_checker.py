import json
import threading
import time
from datetime import datetime, date
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class HolidayChecker:
    """Periodically checks Nager.Date and flags if TODAY is a holiday."""

    def __init__(
        self,
        execute_period_seconds: int = 300,         # how often we evaluate "today"
        country_code: str = "US",
        refresh_interval_seconds: int = 6 * 3600,  # how often we refetch the API (default 6h)
    ):
        self._lock = threading.RLock()
        self._timer = None
        self._stopped = True  # must exist before calling setters

        # writable “slots”
        self._execute_period_seconds = 300
        self._country_code = "US"
        self._refresh_interval_seconds = 6 * 3600  # 1h..30d clamp below

        # read-only “slots”
        self._holiday_today = False
        self._holiday_name = ""
        self._last_fetch_ts = ""
        self._status_trace = "Idle."

        # cache
        self._last_fetch_ms = 0
        self._cache_year_a = -1
        self._cache_year_b = -1
        self._cache_country = None
        self._holiday_by_date = {}

        # init config (via setters)
        self.set_execute_period_seconds(execute_period_seconds)
        self.set_country_code(country_code)
        self.set_refresh_interval_seconds(refresh_interval_seconds)

    # ---- getters/setters (config) ----
    def get_execute_period_seconds(self) -> int:
        with self._lock:
            return self._execute_period_seconds

    def set_execute_period_seconds(self, seconds: int):
        with self._lock:
            seconds = max(60, min(int(seconds), 3600))  # 60..3600
            self._execute_period_seconds = seconds
            if not self._stopped:
                self._schedule_next()

    def get_country_code(self) -> str:
        with self._lock:
            return self._country_code

    def set_country_code(self, cc: str):
        with self._lock:
            self._country_code = (cc or "US").upper()
            self._cache_country = None  # force next refresh

    def get_refresh_interval_seconds(self) -> int:
        with self._lock:
            return self._refresh_interval_seconds

    def set_refresh_interval_seconds(self, seconds: int):
        with self._lock:
            # clamp 1 hour .. 30 days
            seconds = max(3600, min(int(seconds), 30 * 24 * 3600))
            self._refresh_interval_seconds = seconds

    # ---- read-only getters ----
    def get_holiday_today(self) -> bool:
        with self._lock:
            return self._holiday_today

    def get_holiday_name(self) -> str:
        with self._lock:
            return self._holiday_name

    def get_last_fetch_ts(self) -> str:
        with self._lock:
            return self._last_fetch_ts

    def get_status_trace(self) -> str:
        with self._lock:
            return self._status_trace

    # ---- lifecycle ----
    def start(self, fetch_on_start: bool = True):
        with self._lock:
            if not self._stopped:
                return
            self._stopped = False
            self._status_trace = "Holiday checker started."
        if fetch_on_start:
            # do the first poll immediately (outside lock)
            try:
                self._poll_once()
            except Exception as ex:
                with self._lock:
                    self._status_trace = f"startup fetch error: {ex}"
        # schedule the regular evaluation loop
        with self._lock:
            self._schedule_next()


    def stop(self):
        with self._lock:
            self._stopped = True
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def refresh_now(self):
        try:
            self._poll_once()
        except Exception as ex:
            with self._lock:
                self._status_trace = f"manual refresh error: {ex}"

    # ---- scheduling ----
    def _schedule_next(self):
        if self._timer:
            self._timer.cancel()
        period = self._execute_period_seconds
        self._timer = threading.Timer(period, self._execute_tick)
        self._timer.daemon = True
        self._timer.start()

    def _execute_tick(self):
        try:
            self._poll_once()
        except Exception as ex:
            with self._lock:
                self._status_trace = f"poll error: {ex}"
        finally:
            with self._lock:
                if not self._stopped:
                    self._schedule_next()

    # ---- core logic ----
    def _poll_once(self):
        with self._lock:
            cc = self._country_code or "US"
            refresh_window_ms = self._refresh_interval_seconds * 1000

        today = date.today()
        today_iso = today.isoformat()
        y1, y2 = today.year, today.year + 1
        now_ms = int(time.time() * 1000)

        with self._lock:
            need_refresh = (
                not self._holiday_by_date
                or (now_ms - self._last_fetch_ms) > refresh_window_ms
                or self._cache_year_a != y1
                or self._cache_year_b != y2
                or self._cache_country != cc.upper()
            )

        if need_refresh:
            map_out = {}
            self._fetch_into(cc, y1, map_out)
            self._fetch_into(cc, y2, map_out)
            with self._lock:
                self._holiday_by_date = map_out
                self._cache_year_a, self._cache_year_b = y1, y2
                self._cache_country = cc.upper()
                self._last_fetch_ms = now_ms
                self._last_fetch_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._status_trace = f"Fetched {len(map_out)} holidays for {cc} ({y1},{y2})"

            print("\n--- Holiday List ---")
            for d, name in sorted(map_out.items()):
                print(f"{d} : {name}")
            print("--------------------\n")

        # evaluate today
        with self._lock:
            label = self._holiday_by_date.get(today_iso, "")
            self._holiday_today = bool(label)
            self._holiday_name = label if label else ""

    # ---- holiday utilities ----
    def get_all_holidays(self):
        """Return a sorted list of (YYYY-MM-DD, name)."""
        with self._lock:
            items = list(self._holiday_by_date.items())
        items.sort(key=lambda kv: kv[0])
        return items

    def get_next_holiday(self, from_date: date | None = None):
        """Return (YYYY-MM-DD, name, days_until) from given date (default: today), or None."""
        if from_date is None:
            from_date = date.today()
        from_iso = from_date.isoformat()
        candidates = []
        with self._lock:
            for dstr, name in self._holiday_by_date.items():
                candidates.append((dstr, name))
        if not candidates:
            return None
        candidates.sort(key=lambda kv: kv[0])
        for dstr, name in candidates:
            if dstr >= from_iso:
                d = date.fromisoformat(dstr)
                days = (d - from_date).days
                return dstr, name, days
        return None

    # ---- HTTP + parsing ----
    def _fetch_into(self, cc: str, year: int, out: dict):
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{cc}"
        data = self._http_get_json(url)
        if not isinstance(data, list):
            return
        for item in data:
            d = item.get("date")
            label = item.get("localName") or item.get("name") or ""
            if not d or not label:
                continue
            if d in out and out[d] != label:
                out[d] = f"{out[d]} / {label}"
            else:
                out[d] = label

    @staticmethod
    def _http_get_json(url: str):
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "holiday-checker/1.0"})
        try:
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} {e.reason}")
        except URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")
        except json.JSONDecodeError:
            raise RuntimeError("Invalid JSON from API")

    def is_today_holiday(self) -> bool:
        self.refresh_now()
        return self.get_holiday_today()


# ---- Example usage ----
if __name__ == "__main__":
    # Check every 5 min, refresh API every 24h (nice for long-term deployments)
    hc = HolidayChecker(300, "US", 24*3600)
    hc.start(fetch_on_start=True)  # default True; included here for clarity

    print("Running HolidayChecker (press Ctrl+C to exit)")
    try:
        while True:
            time.sleep(10)
            now = datetime.now()
            date_str = now.strftime("%A, %B %d %H:%M:%S")
            nxt = hc.get_next_holiday()
            nxt_str = f"{nxt[0]} ({nxt[1]}; in {nxt[2]} days)" if nxt else "N/A"
            print(
                f"[{date_str}] "
                f"holidayToday={hc.get_holiday_today()} "
                f"name='{hc.get_holiday_name()}' "
                f"lastFetch='{hc.get_last_fetch_ts()}' "
                f"nextHoliday={nxt_str} "
                f"status='{hc.get_status_trace()}'"
            )
    except KeyboardInterrupt:
        hc.stop()
        print("Stopped.")
