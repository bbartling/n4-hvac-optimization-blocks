# 📅 Schedules & Programmatic Weekly Calendars

* ***TODO NOT FINISHED!***

Niagara schedules are components that emit values over time. A ProgramObject can either **read** them or **own** them by writing to `In`.

---

### ⚠️ **IMPORTANT — Best Practice for Exception Handling in ProgramObjects**

Whenever you build Niagara algorithm blocks, **always reference the fault-handling patterns** documented in:

- 👉 [`AGENTS.md`](AGENTS.md) — _Core agent loop patterns, safety rules, and how to use `BStatus.fault` as an exception channel._  
- 👉 [`README_BEGINNER_TUTORIALS.md`](README_BEGINNER_TUTORIALS.md) — _Hands-on intro to status-aware programming and safe ProgramObject design._

These documents show the **correct, Niagara-native method** for handling runtime exceptions using **point status**, not Java exceptions.  
In ProgramObjects, throwing errors will break the station thread — therefore the recommended technique is:

- Detect invalid / unwired / bad inputs  
- Set outputs to **`BStatus.fault`** or **`BStatus.nullStatus`**  
- Publish human-readable diagnostics via a `statusTrace` string  
- Continue running without crashing Workbench or the station

This pattern is the **official best practice** and may not be present in the advanced algorithm tutorials (optimal start, GL-36 logic, DSM, FDD, solar, schedule agents, etc.).

Always follow this model when developing new logic — it ensures consistent behavior, safe evaluation cycles, and clean debugging inside the station.

---

#### Schedule types

- **WeeklySchedule** (`BooleanSchedule`, `NumericSchedule`, `EnumSchedule`, `StringSchedule`)  
  Repeating time-of-day events by weekday. Can reference calendars for exceptions.
- **CalendarSchedule**  
  Specific dates / date ranges (holidays, shutdowns, etc.).
- **TriggerSchedule**  
  Fires “topics” or actions at specific times (alarms, reports, scripts, MQTT, digital I/O).
- **ScheduleSelector**  
  Operator dropdown to choose between multiple schedules.

---

#### WeeklySchedule behavior

Key slots:

- `Out` – current effective output (what the rest of the station sees)
- `In` – optional override; non-null bypasses the internal schedule logic

Priority stack (high → low):

1. `In` override (non-null)
2. Special event (holiday / exception)
3. Normal weekly block
4. Default output (Properties tab)

If your ProgramObject writes to `BooleanSchedule.in`, that value **wins** until you clear it.

---

#### Special events

Weekly schedules can define one-off or recurring exceptions:

- Holidays / shutdown days  
- Early release / late start

They sit just under `In` in the priority order and temporarily replace the normal week.

---

#### Parent / Child schedules

At the driver layer, a **Parent** schedule can fan out to **Child** schedules on many devices:

- Enterprise holiday calendars  
- Chain-wide store hours  
- Campus-wide occupancy

Change the Parent → all Childs follow.

---

#### Internal scheduler (from `scheduleModule`)

Notable classes:

- `BIScheduleSnapshotHandler` / `BScheduleSnapshotHandler` – apply UI edits, validate, write back
- `ScheduleUtil` – helpers (month/day arrays, deep copy, property ordering)
- `ScheduleValidator` – validates date / time / weekday / range logic
- `Chronometer` – time arithmetic (wraps `BAbsTime`, `BWeekday`)
- `ExecutionQueue` – worker threads for schedule evaluation
- `ScheduleSpyManager` – debugging / timing visibility

You don’t call these directly; they guarantee deterministic, thread-safe, “next time” evaluation.

---

#### Programmatically driving a WeeklySchedule

**Goal:** Build a simple Monday–Friday 08:00–17:00 occupancy schedule in code and still respect high-level overrides.

Pattern:

- Use a `ProgramObject` to compute a boolean `occupied` output.
- Link `ProgramObject.out` → `BooleanSchedule.in`.

Effects:

- While `in` is non-null, the ProgramObject fully controls the schedule.
- Clearing `in` hands control back to the configured weekly + calendar events.
- Operators can still use:
  - Calendar holidays
  - Default schedule
  - Parent / Child patterns



---


<details>
<summary>🧪 Programmatically Driving a Weekly Schedule</summary>


### *Using a ProgramObject to override a BooleanSchedule.In*

Use case:

* You want to bypass the schedule UI
* You want a computed schedule (e.g., ML model, occupancy prediction)
* You want a simple hard-coded 8–5 building hours

Just **link the ProgramObject output → BooleanSchedule.in**.

This is the recommended way to override a schedule.


![Schedule Tut Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/scheduleTutSnip.png)

---

# 🕒 Monday–Friday 8-5 Occupancy ProgramObject

### 🧩 Required Slots (create in Slot Sheet)

| Slot Name     | Type             | Purpose                                |
| ------------- | ---------------- | -------------------------------------- |
| `enable`      | `BStatusBoolean` | Parent enable flag                     |
| `occupiedOut` | `BStatusBoolean` | The value written to the schedule `In` |
| `statusTrace` | `BStatusString`  | Debug output                           |

You wire it like this on the wiresheet:

```
ProgramObject.occupiedOut  →  BooleanSchedule.in
```

The schedule will show:
➡️ **In: (linked)**
➡️ **Out** = whatever your ProgramObject computes

---

# 💻 ProgramObject Code 

```java
// ======================================
// 1. Class-Level Variables
// ======================================
private Clock.Ticket ticket = null;

// Run every 60 seconds
private static final int EXEC_PERIOD_SEC = 10;

// Office hours (local station time) 
// 8:00 AM to 5:00 PM
private static final int START_HOUR = 8;
private static final int END_HOUR   = 17;

// ======================================
// 2. Lifecycle Methods (Start/Stop)
// ======================================

public void onStart() throws Exception {
    // Optional: initialize outputs to NULL on startup
    getOccupiedOut().setValue(false);
    getOccupiedOut().setStatus(BStatus.nullStatus);
    getStatusTrace().setValue("Office-hours block started (outputs NULL)");

    // Start timer
    updateTimer();
}

public void onStop() throws Exception {
    // Kill timer
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }

    // Optional: mark outputs NULL on stop
    getOccupiedOut().setValue(false);
    getOccupiedOut().setStatus(BStatus.nullStatus);
    getStatusTrace().setValue("Office-hours block stopped (outputs NULL)");
}

// ======================================
// 3. Main Logic
// ======================================

public void onExecute() throws Exception {
    // Always schedule the next run first
    updateTimer();

    try {
        // Safety Check: If disabled, return NULL
        if (!safeBool(getEnable())) {
            getOccupiedOut().setValue(false);
            getOccupiedOut().setStatus(BStatus.nullStatus);
            getStatusTrace().setValue("Disabled — output forced NULL");
            return;
        }

        // Get Current Time using Java Calendar (station local time)
        java.util.Calendar cal = java.util.Calendar.getInstance();

        // Java Calendar: Sunday=1, Monday=2, ... Saturday=7
        int dow    = cal.get(java.util.Calendar.DAY_OF_WEEK);
        int hour   = cal.get(java.util.Calendar.HOUR_OF_DAY); // 0-23
        int minute = cal.get(java.util.Calendar.MINUTE);

        // Logic: Is it a Weekday? (Mon=2 through Fri=6)
        boolean isWeekday = (dow >= java.util.Calendar.MONDAY &&
                             dow <= java.util.Calendar.FRIDAY);

        // Logic: Is it within hours?
        boolean inHourRange = (hour >= START_HOUR && hour < END_HOUR);

        // Combine logic
        boolean occ = isWeekday && inHourRange;

        // Compute when the output will change next
        java.util.Calendar nextChange = computeNextChange(cal);

        // Format times as human-readable station time (YYYY-MM-DD HH:MM)
        String nowStr  = String.format("%1$tY-%1$tm-%1$td %1$tH:%1$tM", cal);
        String nextStr = String.format("%1$tY-%1$tm-%1$td %1$tH:%1$tM", nextChange);

        // Set Outputs (normal OK path)
        getOccupiedOut().setValue(occ);
        getOccupiedOut().setStatus(BStatus.ok);

        boolean nextValue = !occ;
        
        getStatusTrace().setValue(
            "StationTime=" + nowStr +
            " | NextChange=" + nextStr +
            " | NextValue=" + nextValue
        );

    }
    catch (Exception e) {
        // FAULT path: something went wrong in our logic
        getOccupiedOut().setValue(false);
        getOccupiedOut().setStatus(BStatus.fault);
        getStatusTrace().setValue("FAULT in office-hours block: " + e.toString());
    }
}


// ======================================
// 4. Helper Methods
// ======================================

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(
        getComponent(),
        BRelTime.makeSeconds(EXEC_PERIOD_SEC),
        BProgram.execute,
        null
    );
}

private boolean safeBool(BStatusBoolean b) {
    if (b == null) return false;
    if (!b.getStatus().isOk()) return false;
    return b.getValue();
}

/**
 * Compute the next time (station local) when the occupied flag will change.
 * Occupied = true on weekdays between START_HOUR and END_HOUR.
 */
private java.util.Calendar computeNextChange(java.util.Calendar cal) {
    java.util.Calendar next = (java.util.Calendar) cal.clone();
    next.set(java.util.Calendar.SECOND, 0);
    next.set(java.util.Calendar.MILLISECOND, 0);

    int dow    = cal.get(java.util.Calendar.DAY_OF_WEEK);
    int hour   = cal.get(java.util.Calendar.HOUR_OF_DAY);
    int minute = cal.get(java.util.Calendar.MINUTE);

    boolean isWeekday = (dow >= java.util.Calendar.MONDAY &&
                         dow <= java.util.Calendar.FRIDAY);
    boolean inHourRange = (hour >= START_HOUR && hour < END_HOUR);
    boolean occNow = isWeekday && inHourRange;

    if (isWeekday && hour < START_HOUR) {
        // Before office hours on a weekday: next change is today at START_HOUR
        next.set(java.util.Calendar.HOUR_OF_DAY, START_HOUR);
        next.set(java.util.Calendar.MINUTE, 0);
    }
    else if (isWeekday && inHourRange) {
        // During office hours on a weekday: next change is today at END_HOUR
        next.set(java.util.Calendar.HOUR_OF_DAY, END_HOUR);
        next.set(java.util.Calendar.MINUTE, 0);
    }
    else {
        // After hours on a weekday OR weekend: next change is next weekday at START_HOUR
        do {
            next.add(java.util.Calendar.DAY_OF_MONTH, 1);
            int ndow = next.get(java.util.Calendar.DAY_OF_WEEK);
            if (ndow >= java.util.Calendar.MONDAY && ndow <= java.util.Calendar.FRIDAY) {
                break;
            }
        } while (true);

        next.set(java.util.Calendar.HOUR_OF_DAY, START_HOUR);
        next.set(java.util.Calendar.MINUTE, 0);
    }

    return next;
}


```

</details>

---

````markdown
<details>
<summary>📅 iCal Schedule Agent</summary>

This ProgramObject turns an **iCalendar (.ics) feed** into a live Boolean
schedule and “next event” hints for optimal start.

It exposes:

- `occupiedOut` → **BooleanSchedule.in** (true when *any* event is active)
- `statusTrace` → human-readable debug string  
  `StationTime / EventState / EventName / NextChange / NextValue / ParsedEvents`
- Optimal-start signals:
  - `scheduleNextValue` → occupancy value at the **next change edge** (true/false)
  - `scheduleNextEventTime` → Java **milliseconds timestamp** of that next change

Under the hood it does two distinct loops:

1. **Slow loop – Fetch & parse ICS (network)**  
   - Runs only when:
     - the `updateNow` flag is set, **or**
     - the cached data is older than `icsFetchPeriodSeconds`, **or**
     - the cache is empty on startup.
   - Downloads the `.ics` file, parses all `VEVENT` blocks, and builds an
     in-memory `eventCache` list (typically a few hundred events).
   - Replaces the old cache in one shot so memory doesn’t grow over time.
   - Updates:
     - `lastFetchTs` with a human-readable timestamp
     - `statusTrace` and optional console logs (`logToConsole`).

2. **Fast loop – Evaluate schedule (no network)**  
   - Runs every `EXEC_PERIOD_SEC` seconds (currently 10s).
   - Compares the current **station time** against the cached events:
     - If `now` falls between any event’s `startMillis`/`endMillis`,
       `occupiedOut = true`.
     - Finds the **next change edge**:
       - from unoccupied → occupied (next event start)
       - or occupied → unoccupied (end of the current event).
   - Writes:
     - `occupiedOut` (for the BooleanSchedule `In` slot)
     - `scheduleNextEventTime` (Java millis)
     - `scheduleNextValue` (true/false at that millis)
     - `statusTrace` (single debug line)

Because the evaluation loop never hits the network, the output toggles
**instantly** when an event starts/stops, even if you only fetch the ICS once
per hour.

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalAxPropSheetSnip.png" alt="iCal AX / N4 Property Sheet" width="850">
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalSnip.png" alt="iCal Wiresheet Snip" width="850">
</p>

---

### 🧩 Slots

Create these slots on your ProgramObject:

| Slot Name                 | Type             | Writable | Flags        | Notes |
|---------------------------|------------------|----------|--------------|-------|
| `enable`                  | `BStatusBoolean` | ✅        | `sL`         | Master enable; when false, all outputs are forced `NULL`. |
| `occupiedOut`             | `BStatusBoolean` | ❌        | `rs`         | **Output** wired to `BooleanSchedule.in` (true when any event is active). |
| `statusTrace`             | `BStatusString`  | ❌        | `rs`         | Human-readable log of current state, next change, and parsed count. |
| `icsUrl`                  | `BStatusString`  | ✅        | `f`          | HTTPS URL of the `.ics` feed. Defaults to **Google US Holidays** on start if empty. |
| `icsFetchPeriodSeconds`   | `BStatusNumeric` | ✅        | `f`          | Fetch period for the slow loop (seconds). Defaults to **3600** (1 hour) if `NULL`/bad. |
| `updateNow`               | `BStatusBoolean` | ✅        | `sX`         | Manual trigger; when set `true`, forces an immediate fetch, then auto-resets to `false`. |
| `scheduleNextValue`       | `BStatusBoolean` | ❌        | `rs`         | **Output** for optimal-start: occupancy value at `scheduleNextEventTime`. |
| `scheduleNextEventTime`   | `BStatusNumeric` | ❌        | `rs`         | **Output** for optimal-start: next change edge in Java millis (`double`). |
| `lastFetchTs`             | `BStatusString`  | ❌        | `rs`         | Time of the last successful ICS fetch, for troubleshooting. |
| `logToConsole`            | `BStatusBoolean` | ✅        | `s`          | When true, prints lightweight debug logs to the station console. |
| `Link` (optional helper)  | `baja:Link`      | —        |              | Only needed if you want to visually wire things in an AX/N4 demo palette. |

> **Wiring pattern (basic schedule):**  
> `iCalProgram.occupiedOut → BooleanSchedule.in`  
> `BooleanSchedule.out → Your AHU/VAV schedule consumer`

> **Wiring pattern (optimal start):**  
> `iCalProgram.scheduleNextValue      → OptimalStart.scheduleNextValue`  
> `iCalProgram.scheduleNextEventTime  → OptimalStart.scheduleNextEventTime`

---

### Application Director Logs When Set True

* Parsing ical events debug will show up like below in Platform Application Director

```
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Tue Jul 04 00:00:00 CDT 2028 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Wed Jul 05 00:00:00 CDT 2028
[IcalScheduleAgent]     SUMMARY: Independence Day
[IcalScheduleAgent] ... adding event: Independence Day | start=Tue Jul 04 00:00:00 CDT 2028 | end=Wed Jul 05 00:00:00 CDT 2028 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Sun Dec 24 00:00:00 CST 2028 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Mon Dec 25 00:00:00 CST 2028
[IcalScheduleAgent]     SUMMARY: Christmas Eve
[IcalScheduleAgent] ... adding event: Christmas Eve | start=Sun Dec 24 00:00:00 CST 2028 | end=Mon Dec 25 00:00:00 CST 2028 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Sun Dec 31 00:00:00 CST 2028 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Mon Jan 01 00:00:00 CST 2029
[IcalScheduleAgent]     SUMMARY: New Year's Eve
[IcalScheduleAgent] ... adding event: New Year's Eve | start=Sun Dec 31 00:00:00 CST 2028 | end=Mon Jan 01 00:00:00 CST 2029 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Mon Jan 15 00:00:00 CST 2029 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Tue Jan 16 00:00:00 CST 2029
[IcalScheduleAgent]     SUMMARY: Martin Luther King Jr. Day
[IcalScheduleAgent] ... adding event: Martin Luther King Jr. Day | start=Mon Jan 15 00:00:00 CST 2029 | end=Tue Jan 16 00:00:00 CST 2029 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Mon Dec 31 00:00:00 CST 2029 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Tue Jan 01 00:00:00 CST 2030
[IcalScheduleAgent]     SUMMARY: New Year's Eve
[IcalScheduleAgent] ... adding event: New Year's Eve | start=Mon Dec 31 00:00:00 CST 2029 | end=Tue Jan 01 00:00:00 CST 2030 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Thu Dec 24 00:00:00 CST 2020 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Fri Dec 25 00:00:00 CST 2020
[IcalScheduleAgent]     SUMMARY: Christmas Eve
[IcalScheduleAgent] ... adding event: Christmas Eve | start=Thu Dec 24 00:00:00 CST 2020 | end=Fri Dec 25 00:00:00 CST 2020 | allDay=true
[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Mon Oct 12 00:00:00 CDT 2020 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Tue Oct 13 00:00:00 CDT 2020
[IcalScheduleAgent]     SUMMARY: Columbus Day
```

### 📦 Imports (Workbench → Imports tab)

Add these (if they’re not already there):

- `java.util`
- `java.io`
- `java.net`
- `java.text`
- `javax.baja.status`
- `javax.baja.time`
- `com.tridium.program`

Do **not** paste them into the code window; they go in the **Imports** tab.

---

### ⚙️ Defaults

On `onStart()` the block auto-heals common config issues:

- If `icsFetchPeriodSeconds` is `NULL` or ≤ 0, it is set to **3600 seconds**.
- If `icsUrl` is empty, it is set to the public **Google US Holiday** feed:

  ```text
  https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics
````

This means you can drop the ProgramObject into a station, hit **Compile**, and
it will start behaving like a holiday-based Boolean schedule with zero
configuration.

---

### 🔁 How the loop behaves

Each `onExecute()`:

1. Keeps the **timer heartbeat** going (every 10s).
2. Decides whether to re-fetch the ICS:

   * If `updateNow == true` → fetch immediately.
   * Else if `now - lastDownload > icsFetchPeriodSeconds` → fetch.
   * Else if the cache is empty (first run) → fetch.
3. Uses the **cached events only** to compute:

   * `occupiedOut` (any event active now?)
   * `scheduleNextEventTime` / `scheduleNextValue` (next edge)
   * `statusTrace` (single debug line).

Because the heavy ICS parse runs infrequently and the fast loop uses only
in-memory data, this is very light weight for a JACE or Supervisor while still
giving **instant** schedule transitions.

---

### 💻 Program Source (full Java)

> Workbench auto-generates the class header and getters/setters; paste **only**
> the code below into the **Program Source** section.

```java
////////////////////////////////////////////////////////////////
// Program Source — iCal-Driven Boolean Schedule Replacement
////////////////////////////////////////////////////////////////

// ==========================
// Internal Types
// ==========================

class IcalEvent {
  long startMillis;
  long endMillis;
  String summary;
  boolean isAllDay;

  IcalEvent(long s, long e, String sum, boolean ad) {
    startMillis = s;
    endMillis   = e;
    summary     = (sum == null) ? "" : sum;
    isAllDay    = ad;
  }
}

class ParsedDate {
  long millis;
  boolean isAllDay;
  ParsedDate(long m, boolean ad) { millis = m; isAllDay = ad; }
}


// ==========================
// Class-Level State
// ==========================

private Clock.Ticket ticket;
private static final int EXEC_PERIOD_SEC = 10;   // Fast loop

private java.util.List<IcalEvent> eventCache =
    new java.util.ArrayList<IcalEvent>();

private java.text.SimpleDateFormat fmtUtc;
private java.text.SimpleDateFormat fmtAllDay;

private long lastDownload = 0L;


// ==========================
// onStart
// ==========================

public void onStart() throws Exception
{
  fmtUtc = new java.text.SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'");
  fmtUtc.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));

  fmtAllDay = new java.text.SimpleDateFormat("yyyyMMdd");
  fmtAllDay.setTimeZone(java.util.TimeZone.getDefault());

  // <---- NEW: apply defaults if those slots are empty/bad
  applyDefaultConfig();

  getStatusTrace().setValue("iCal Schedule Agent Started");
  updateTimer();
}



// ==========================
// onExecute
// ==========================

public void onExecute() throws Exception
{
  updateTimer();

  try {
    // ❌ If disabled: return NULL
    if (!safeBool(getEnable())) {
      forceNullOutputs("Disabled");
      return;
    }

    long now = System.currentTimeMillis();

    // ==========================================================
    // 1) SLOW LOOP — ICS DOWNLOAD
    // ==========================================================
    double fetchPeriod = 300; // default 5-minute fetch
    if (getIcsFetchPeriodSeconds().getStatus().isOk()) {
      fetchPeriod = Math.max(30, getIcsFetchPeriodSeconds().getValue());
    }

    boolean manual = safeBool(getUpdateNow());
    if (manual) {
      getUpdateNow().setValue(false);
      getUpdateNow().setStatus(BStatus.ok);
    }

    boolean expired = (now - lastDownload) > (long)(fetchPeriod * 1000);

    if (manual || expired || eventCache.isEmpty()) {
      fetchIcs();
    }

    // ==========================================================
    // 2) FAST LOOP — EVALUATE CURRENT & NEXT EVENT
    // ==========================================================
    evaluateSchedule(now);

  } catch (Exception e) {
    forceFaultOutputs("FAULT in onExecute: " + e.toString());
  }
}


// ==========================
// onStop
// ==========================

public void onStop() throws Exception
{
  if (ticket != null) {
    ticket.cancel();
    ticket = null;
  }
}


// ==========================
// Timer Helper
// ==========================

private void updateTimer()
{
  if (ticket != null) ticket.cancel();
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(EXEC_PERIOD_SEC),
      BProgram.execute,
      null
  );
}


// ==========================
// ICS Fetcher
// ==========================

private void fetchIcs()
{
  String urlStr = "";
  if (getIcsUrl().getStatus().isOk() &&
      getIcsUrl().getValue() != null) {
    urlStr = getIcsUrl().getValue().trim();
  }

  if (urlStr.length() == 0) {
    getStatusTrace().setValue("Config error: no ICS URL");
    log("Config error: no ICS URL");
    return;
  }

  java.util.List<IcalEvent> newEvents =
      new java.util.ArrayList<IcalEvent>();

  java.net.HttpURLConnection conn = null;
  java.io.BufferedReader reader = null;

  try {
    log("GET " + urlStr);
    java.net.URL url = new java.net.URL(urlStr);
    conn = (java.net.HttpURLConnection) url.openConnection();
    conn.setConnectTimeout(4000);
    conn.setReadTimeout(8000);
    conn.setRequestMethod("GET");

    int code = conn.getResponseCode();
    if (code != 200) {
      getStatusTrace().setValue("HTTP error: " + code);
      log("HTTP error: " + code);
      return;
    }

    reader = new java.io.BufferedReader(
        new java.io.InputStreamReader(conn.getInputStream(), "UTF-8"));

    boolean inEvent = false;
    String summary = null;
    long dtStart = -1L;
    long dtEnd = -1L;
    boolean isAllDay = false;

    String line;
    while ((line = reader.readLine()) != null) {
      line = line.trim();

      if (line.equals("BEGIN:VEVENT")) {
        inEvent = true;
        summary = null;
        dtStart = -1L;
        dtEnd = -1L;
        isAllDay = false;
        log("... BEGIN:VEVENT");
        continue;
      }

      if (line.equals("END:VEVENT")) {
        if (dtStart != -1L) {
          if (dtEnd == -1L) {
            dtEnd = isAllDay ?
              dtStart + 86400000L : dtStart + 3600000L;
          }
          log("... adding event: " + summary +
              " | start=" + new java.util.Date(dtStart) +
              " | end=" + new java.util.Date(dtEnd) +
              " | allDay=" + isAllDay);

          newEvents.add(new IcalEvent(dtStart, dtEnd, summary, isAllDay));
        } else {
          log("... skipping VEVENT (missing DTSTART)");
        }
        inEvent = false;
        continue;
      }

      if (!inEvent) continue;

      if (line.startsWith("SUMMARY:")) {
        summary = line.substring(8).trim();
        log("    SUMMARY: " + summary);
      }

      if (line.startsWith("DTSTART")) {
        ParsedDate p = parseDate(line);
        if (p != null) {
          dtStart  = p.millis;
          isAllDay = p.isAllDay;
          log("    DTSTART: " + new java.util.Date(dtStart) +
              (isAllDay ? " (ALL-DAY)" : ""));
        } else {
          log("    FAILED TO PARSE DTSTART: " + line);
        }
      }

      if (line.startsWith("DTEND")) {
        ParsedDate p = parseDate(line);
        if (p != null) {
          dtEnd = p.millis;
          log("    DTEND:   " + new java.util.Date(dtEnd));
        } else {
          log("    FAILED TO PARSE DTEND: " + line);
        }
      }
    }

    eventCache.clear();
    eventCache.addAll(newEvents);
    lastDownload = System.currentTimeMillis();

    getLastFetchTs().setValue(new java.util.Date(lastDownload).toString());
    getLastFetchTs().setStatus(BStatus.ok);

    log("parsed future events: " + newEvents.size());
    getStatusTrace().setValue("OK: fetched " + newEvents.size() + " events");

  } catch (Exception e) {
    String msg = "Fetch error: " + e.toString();
    getStatusTrace().setValue(msg);
    log(msg);
  }
  finally {
    try { if (reader != null) reader.close(); } catch(Exception e){}
    try { if (conn != null) conn.disconnect(); } catch(Exception e){}
  }
}


// ==========================
// Evaluation of Occupancy & Next Event
// ==========================

private void evaluateSchedule(long now)
{
  boolean occNow = false;
  String currentNames = "";

  long nextStart = Long.MAX_VALUE;
  long nextEnd   = Long.MAX_VALUE;

  // --- Scan all events ---
  synchronized (eventCache) {
    for (IcalEvent ev : eventCache) {
      boolean nowIn = (now >= ev.startMillis && now < ev.endMillis);

      if (nowIn) {
        occNow = true;

        if (currentNames.length() > 0) currentNames += ", ";
        currentNames += ev.summary;

        if (ev.endMillis < nextEnd) {
          nextEnd = ev.endMillis;
        }
      }
      else {
        if (ev.startMillis > now && ev.startMillis < nextStart) {
          nextStart = ev.startMillis;
        }
      }
    }
  }

  // --- Determine next change edge ---
  long    nextChange = -1L;
  boolean nextValue  = occNow;   // default if we don't find a change

  if (!occNow && nextStart != Long.MAX_VALUE) {
    // currently unoccupied, next change is becoming occupied
    nextChange = nextStart;
    nextValue  = true;
  }
  else if (occNow && nextEnd != Long.MAX_VALUE) {
    // currently occupied, next change is becoming unoccupied
    nextChange = nextEnd;
    nextValue  = false;
  }

  // ------------ Primary Outputs ------------

  // OccupiedOut → BooleanSchedule.in
  getOccupiedOut().setValue(occNow);
  getOccupiedOut().setStatus(BStatus.ok);

  // Optimal-start outputs
  if (nextChange > 0L) {
    getScheduleNextEventTime().setValue((double) nextChange);
    getScheduleNextEventTime().setStatus(BStatus.ok);

    getScheduleNextValue().setValue(nextValue);
    getScheduleNextValue().setStatus(BStatus.ok);
  }
  else {
    getScheduleNextEventTime().setValue(0.0);
    getScheduleNextEventTime().setStatus(BStatus.nullStatus);

    getScheduleNextValue().setValue(false);
    getScheduleNextValue().setStatus(BStatus.nullStatus);
  }

  // ------------ StatusTrace (single line) ------------

  String nowStr  = formatLocal(new java.util.Date(now));
  String nextStr = (nextChange > 0L)
      ? formatLocal(new java.util.Date(nextChange))
      : "none";

  String activeStr = occNow ? "ACTIVE" : "inactive";

  // If no current event name, just say "none"
  String eventNameStr =
      (currentNames != null && currentNames.length() > 0)
          ? currentNames
          : "none";

  int parsedCount;
  synchronized (eventCache) {
    parsedCount = eventCache.size();
  }

  String trace =
      "StationTime=" + nowStr +
      " | EventState=" + activeStr +
      " | EventName=" + eventNameStr +
      " | NextChange=" + nextStr +
      " | NextValue=" + nextValue +
      " | ParsedEvents=" + parsedCount;

  getStatusTrace().setValue(trace);
  getStatusTrace().setStatus(BStatus.ok);
}


// ==========================
// Helpers
// ==========================

private boolean safeBool(BStatusBoolean b)
{
  return b != null && b.getStatus().isOk() && b.getValue();
}

private void forceNullOutputs(String msg)
{
  getOccupiedOut().setValue(false);
  getOccupiedOut().setStatus(BStatus.nullStatus);

  getScheduleNextEventTime().setValue(0.0);
  getScheduleNextEventTime().setStatus(BStatus.nullStatus);

  getScheduleNextValue().setValue(false);
  getScheduleNextValue().setStatus(BStatus.nullStatus);

  getStatusTrace().setValue(msg);
}

private void forceFaultOutputs(String msg)
{
  getOccupiedOut().setValue(false);
  getOccupiedOut().setStatus(BStatus.fault);

  getScheduleNextEventTime().setValue(0.0);
  getScheduleNextEventTime().setStatus(BStatus.fault);

  getScheduleNextValue().setValue(false);
  getScheduleNextValue().setStatus(BStatus.fault);

  getStatusTrace().setValue(msg);
}


private ParsedDate parseDate(String line)
{
  try {
    if (line.contains("VALUE=DATE")) {
      int idx = line.lastIndexOf(":");
      if (idx > 0) {
        String v = line.substring(idx + 1);
        java.util.Date d = fmtAllDay.parse(v.substring(0,8));
        return new ParsedDate(d.getTime(), true);
      }
    } else {
      int idx = line.lastIndexOf(":");
      if (idx > 0) {
        String v = line.substring(idx + 1);
        if (v.endsWith("Z")) {
          java.util.Date d = fmtUtc.parse(v);
          return new ParsedDate(d.getTime(), false);
        } else {
          java.text.SimpleDateFormat f =
              new java.text.SimpleDateFormat("yyyyMMdd'T'HHmmss");
          f.setTimeZone(java.util.TimeZone.getDefault());
          java.util.Date d = f.parse(v.substring(0,15));
          return new ParsedDate(d.getTime(), false);
        }
      }
    }
  }
  catch (Exception ignore) {}
  return null;
}

private String formatLocal(java.util.Date d)
{
  java.text.SimpleDateFormat f =
      new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm");
  f.setTimeZone(java.util.TimeZone.getDefault());
  return f.format(d);
}

// Set sensible defaults if config slots are NULL / bad
private void applyDefaultConfig()
{
  // --- Default fetch period: 3600 seconds (1 hour) ---
  try {
    boolean badPeriod =
        (getIcsFetchPeriodSeconds() == null) ||
        !getIcsFetchPeriodSeconds().getStatus().isOk() ||
        getIcsFetchPeriodSeconds().getValue() <= 0.0;

    if (badPeriod) {
      getIcsFetchPeriodSeconds().setValue(3600.0);  // 1 hour
      getIcsFetchPeriodSeconds().setStatus(BStatus.ok);
    }
  }
  catch (Exception e) {
    // ignore – safest is to leave as-is
  }

  // --- Default ICS URL: Google US Holidays (public) ---
  try {
    String url = null;
    if (getIcsUrl() != null && getIcsUrl().getStatus().isOk()) {
      url = getIcsUrl().getValue();
    }

    if (url == null || url.trim().length() == 0) {
      getIcsUrl().setValue(
        "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics"
      );
      getIcsUrl().setStatus(BStatus.ok);
    }
  }
  catch (Exception e) {
    // ignore
  }
}

// Simple conditional logger controlled by logToConsole
private void log(String msg)
{
  try {
    if (getLogToConsole() != null &&
        getLogToConsole().getStatus().isOk() &&
        getLogToConsole().getValue())
    {
      System.out.println("[IcalScheduleAgent] " + msg);
    }
  } catch (Exception ignore) {
    // never let logging break the block
  }
}

```

</details>
```

