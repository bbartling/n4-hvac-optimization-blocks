# 📅 Schedules & Programmatic Weekly Calendars



<details>
<summary>🎶 Niagara Platform Schedule Notes</summary>


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


</details>

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

<details>
<summary>📅 iCal Schedule Agent</summary>

This ProgramObject turns a remote **iCalendar (.ics) feed** into a live Boolean
schedule plus “next event” metadata used for **optimal start**, **holiday mode**,
and **cloud-driven BAS scheduling**.

It exposes:

- `occupiedOut` → **BooleanSchedule.in** (true when *any* event is active)
- `statusTrace` → human-readable debug string  
  `StationTime / EventState / EventName / NextChange / NextValue / ParsedEvents`
- Optimal-start signals:
  - `scheduleNextValue` → occupancy at the **next change edge** (true/false)
  - `scheduleNextEventTime` → Java **milliseconds timestamp** for that edge

Under the hood the agent runs with two distinct loops:

---

## 🐢 Slow loop – Fetch & parse ICS (network)

Runs only when:
- `updateNow` is pressed, **or**
- `icsFetchPeriodSeconds` has expired, **or**
- event cache is empty on startup.

This loop:

- Downloads the `.ics` file  
- Parses all `BEGIN:VEVENT` blocks  
- Builds a fresh `eventCache` list (typically a few hundred all-day + timed events)  
- Replaces the old cache to eliminate memory creep  
- Updates:
  - `lastFetchTs` (human-readable time)
  - `eventsAdded`
  - `statusTrace`
  - console logs when `logToConsole` is enabled

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalAxPropSheetSnip.png" alt="iCal AX / N4 Property Sheet" width="850">
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalSnip.png" alt="iCal Wiresheet Snip" width="850">
</p>

---

## ⚡ Fast loop – Evaluate schedule (no network)

Runs every `EXEC_PERIOD_SEC` seconds (default: **10s**).

It compares **Station Time** to the cached events:

- If `now` is between `startMillis` ≤ `now` < `endMillis`, then:
  - `occupiedOut = true`
  - `eventActive = true`
  - `nextEvent` = current event name(s)
- Determines the **next change edge**:
  - unoccupied → occupied (next event start)
  - occupied → unoccupied (current event end)
- Writes:
  - `occupiedOut`
  - `scheduleNextEventTime` (Java millis)
  - `scheduleNextValue` (true/false)
  - `statusTrace` (single, human-friendly debug line)

Because the fast loop never touches the network, outputs update **instantly**
when an event starts/stops—even if the ICS is fetched only once per hour.

---

## 🧩 Slots

Create these slots on your ProgramObject:

| Slot Name                 | Type             | Writable | Flags | Notes |
|---------------------------|------------------|----------|--------|-------|
| `enable`                  | `BStatusBoolean` | ✅        | `sL`   | Master enable; when false, all outputs go `NULL`. |
| `occupiedOut`             | `BStatusBoolean` | ❌        | `rs`   | **Output** to `BooleanSchedule.in`. |
| `statusTrace`             | `BStatusString`  | ❌        | `rs`   | One-line debug of state + next change. |
| `icsUrl`                  | `BStatusString`  | ✅        | `f`    | HTTPS URL of `.ics`. Defaults to Google Holidays if empty. |
| `icsFetchPeriodSeconds`   | `BStatusNumeric` | ✅        | `f`    | Slow loop fetch period. Defaults to **3600 seconds**. |
| `updateNow`               | `BStatusBoolean` | ✅        | `sX`   | Manual one-shot fetch trigger. Auto-resets. |
| `scheduleNextValue`       | `BStatusBoolean` | ❌        | `rs`   | Occupancy value at the next change boundary. |
| `scheduleNextEventTime`   | `BStatusNumeric` | ❌        | `rs`   | Java millis timestamp of next change. |
| `lastFetchTs`             | `BStatusString`  | ❌        | `rs`   | Timestamp of last successful ICS fetch. |
| `logToConsole`            | `BStatusBoolean` | ✅        | `s`    | Enables debug output to Application Director. |

**Basic wiring pattern:**

```

iCalAgent.occupiedOut → BooleanSchedule.in
BooleanSchedule.out → Downstream AHU/VAV logic

```

**Optimal-start wiring:**

```

iCalAgent.scheduleNextValue      → OptimalStart.scheduleNextValue
iCalAgent.scheduleNextEventTime  → OptimalStart.scheduleNextEventTime

```

---

## 📋 Application Director Logs (when `logToConsole = true`)

A sample of the ICS parse output:

```

[IcalScheduleAgent] ... BEGIN:VEVENT
[IcalScheduleAgent]     DTSTART: Tue Jul 04 00:00:00 CDT 2028 (ALL-DAY)
[IcalScheduleAgent]     DTEND:   Wed Jul 05 00:00:00 CDT 2028
[IcalScheduleAgent]     SUMMARY: Independence Day
[IcalScheduleAgent] ... adding event: Independence Day | start=Tue Jul 04 00:00:00 CDT 2028 | end=Wed Jul 05 00:00:00 CDT 2028 | allDay=true

```

These logs are intentionally lightweight and safe for Supervisor/JACE usage.

---

## ⚙️ Defaults (auto-healing on startup)

On `onStart()`:

- If `icsFetchPeriodSeconds` is `NULL` or invalid → set to **3600 sec**
- If `icsUrl` is empty → defaults to public Google US Holidays:

```

[https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics](https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics)

```

This makes the block **drop-in ready** even without configuration.

---

## 🛡️ Safety Engineering

This agent includes several critical real-world protections:

### 1️⃣ 45-Day Horizon  
Only events within “**now → now + 45 days**” are expanded.  
Prevents gaps on long weekends/holidays and ensures optimal start always has a next-change edge.

### 2️⃣ Circuit Breaker (max 500 expanded events)  
If a user accidentally creates bad recurring rules (e.g., “repeat every minute”), the .ics could explode to **60k+ events**.

The agent limits expansion:

```java
if (safetyCounter > 500) break;
````

Protects JACE memory and avoids lockups.

### 3️⃣ Wall-Clock Time (Floating Time)

ICS timezone identifiers are intentionally **ignored**.
All events run in **Station Time**, preventing DST drift and timezone mismatch between:

* Google/Outlook cloud servers
* Local JACE timezone settings

This prevents the classic “7am becomes 9am” error.

### 4️⃣ Fault Handling

If anything fails during parsing or network fetch:

* `occupiedOut` becomes **null or false** safely
* `scheduleNextValue` / `scheduleNextEventTime` are cleared
* `statusTrace` shows the fault string
* Agent auto-recovers on next successful fetch

---

## 🔁 Loop Behavior Summary

Every `onExecute()`:

1. Keeps the 10-second heartbeat
2. Conditionally re-fetches the ICS feed
3. Evaluates the cached event list
4. Produces new outputs immediately
5. Updates the `statusTrace`

Because heavy parsing happens rarely, runtime CPU usage on a JACE is negligible.

---


### 💻 Program Source (full Java)

> Workbench auto-generates the class header and getters/setters; paste **only**
> the code below into the **Program Source** section.

```java

////////////////////////////////////////////////////////////////
// Program Source — iCal-Driven Boolean Schedule Replacement
// Version: Recurrence-Aware with Conditional Logging
////////////////////////////////////////////////////////////////

// ==========================
// Internal Types
// ==========================

class IcalEvent {
  long startMillis;
  long endMillis;
  String summary;
  boolean isAllDay;
  String rrule; // Stores the raw recurrence rule

  IcalEvent(long s, long e, String sum, boolean ad, String rr) {
    startMillis = s;
    endMillis   = e;
    summary     = (sum == null) ? "" : sum;
    isAllDay    = ad;
    rrule       = rr;
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

private java.util.List eventCache = new java.util.ArrayList();

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

  // Apply defaults if slots are empty
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
// ICS Fetcher (with Logging & Recurrence)
// ==========================

private void fetchIcs()
{
  String urlStr = "";
  if (getIcsUrl().getStatus().isOk() && getIcsUrl().getValue() != null) {
    urlStr = getIcsUrl().getValue().trim();
  }

  // Fallback to Google Holidays if empty (as per original code)
  if (urlStr.length() == 0) return; 

  java.util.List rawEvents = new java.util.ArrayList();
  java.net.HttpURLConnection conn = null;
  java.io.BufferedReader reader = null;

  try {
    log("GET " + urlStr);
    java.net.URL url = new java.net.URL(urlStr);
    conn = (java.net.HttpURLConnection) url.openConnection();
    conn.setConnectTimeout(4000);
    conn.setReadTimeout(8000);
    
    // Google Calendar private address often rejects HEAD, use GET
    conn.setRequestMethod("GET"); 

    int code = conn.getResponseCode();
    if (code != 200) {
      String err = "HTTP error: " + code;
      getStatusTrace().setValue(err);
      log(err);
      return;
    }

    reader = new java.io.BufferedReader(
        new java.io.InputStreamReader(conn.getInputStream(), "UTF-8"));

    boolean inEvent = false;
    String summary = "";
    String rrule = null;
    long dtStart = -1L;
    long dtEnd = -1L;
    boolean isAllDay = false;

    String line;
    while ((line = reader.readLine()) != null) {
      line = line.trim();

      if (line.equals("BEGIN:VEVENT")) {
        inEvent = true;
        summary = "";
        rrule = null;
        dtStart = -1L;
        dtEnd = -1L;
        isAllDay = false;
        log("... BEGIN:VEVENT");
        continue;
      }

      if (line.equals("END:VEVENT")) {
        if (dtStart != -1L) {
          if (dtEnd == -1L) {
            // Default durations if DTEND missing
            dtEnd = isAllDay ? dtStart + 86400000L : dtStart + 3600000L;
          }
          // Store raw event
          rawEvents.add(new IcalEvent(dtStart, dtEnd, summary, isAllDay, rrule));
          log("... found raw: " + summary + " | RRULE: " + (rrule != null ? "YES" : "NO"));
        }
        inEvent = false;
        continue;
      }

      if (!inEvent) continue;

      if (line.startsWith("SUMMARY:")) summary = line.substring(8).trim();
      
      if (line.startsWith("RRULE:")) {
        rrule = line.substring(6).trim(); 
        log("    RRULE: " + rrule);
      }

      if (line.startsWith("DTSTART")) {
        ParsedDate p = parseDate(line);
        if (p != null) { dtStart = p.millis; isAllDay = p.isAllDay; }
      }
      if (line.startsWith("DTEND")) {
        ParsedDate p = parseDate(line);
        if (p != null) dtEnd = p.millis;
      }
    }

    // Expand Recurrences
    eventCache.clear();
    eventCache.addAll(expandRecurrences(rawEvents));
    
    lastDownload = System.currentTimeMillis();
    getLastFetchTs().setValue(new java.util.Date(lastDownload).toString());
    
    String msg = "OK: Fetched & Expanded " + eventCache.size() + " events";
    getStatusTrace().setValue(msg);
    log(msg);

  } catch (Exception e) {
    String err = "Fetch error: " + e.toString();
    getStatusTrace().setValue(err);
    log(err);
  } finally {
    try { if (reader != null) reader.close(); } catch(Exception e){}
    try { if (conn != null) conn.disconnect(); } catch(Exception e){}
  }
}

// ==========================
// Recurrence Expander
// ==========================

private java.util.List expandRecurrences(java.util.List rawEvents) {
    java.util.List expanded = new java.util.ArrayList();
    long now = System.currentTimeMillis();
    // Look ahead 45 days (limit memory usage)
    long horizon = now + (45L * 86400000L); 
    int safetyCounter = 0;
    
    for (int i=0; i<rawEvents.size(); i++) {
        IcalEvent ev = (IcalEvent) rawEvents.get(i);
        
        // Always add the original instance
        expanded.add(ev);
        
        // Only handle simple WEEKLY recurrence (M-F 8-5 pattern)
        if (ev.rrule != null && ev.rrule.contains("FREQ=WEEKLY")) {
            
            long duration = ev.endMillis - ev.startMillis;
            
            // 1. Determine days of week (MO,TU,WE...)
            java.util.List days = new java.util.ArrayList();
            if (ev.rrule.contains("BYDAY=")) {
                String byDay = ev.rrule.split("BYDAY=")[1].split(";")[0];
                if (byDay.contains("SU")) days.add(Integer.valueOf(java.util.Calendar.SUNDAY));
                if (byDay.contains("MO")) days.add(Integer.valueOf(java.util.Calendar.MONDAY));
                if (byDay.contains("TU")) days.add(Integer.valueOf(java.util.Calendar.TUESDAY));
                if (byDay.contains("WE")) days.add(Integer.valueOf(java.util.Calendar.WEDNESDAY));
                if (byDay.contains("TH")) days.add(Integer.valueOf(java.util.Calendar.THURSDAY));
                if (byDay.contains("FR")) days.add(Integer.valueOf(java.util.Calendar.FRIDAY));
                if (byDay.contains("SA")) days.add(Integer.valueOf(java.util.Calendar.SATURDAY));
            }
            
            // 2. Step forward day by day until horizon
            java.util.Calendar ptr = java.util.Calendar.getInstance();
            ptr.setTimeInMillis(ev.startMillis);
            
            // Prevent infinite loops if start is way in past, jump to 'now' minus 1 day
            if (ptr.getTimeInMillis() < now - 86400000L) {
                ptr.setTimeInMillis(now - 86400000L);
            }

            while (ptr.getTimeInMillis() < horizon) {
                ptr.add(java.util.Calendar.DAY_OF_YEAR, 1);
                
                int dow = ptr.get(java.util.Calendar.DAY_OF_WEEK);
                boolean match = false;
                
                // If BYDAY exists, check if today matches
                if (days.size() > 0) {
                    for(int d=0; d<days.size(); d++) {
                        if (((Integer)days.get(d)).intValue() == dow) match = true;
                    }
                } else {
                    // No BYDAY? It repeats every 7 days (Simple logic)
                    match = true; 
                }
                
                if (match) {
                    long newStart = ptr.getTimeInMillis();
                    long newEnd = newStart + duration;
                    // Log the creation of the ghost event
                    log("   -> Creating recurrence: " + new java.util.Date(newStart));
                    expanded.add(new IcalEvent(newStart, newEnd, ev.summary, ev.isAllDay, null));
                    
                    safetyCounter++;
                    if (safetyCounter > 500) {
                        log("WARN: Hit recurrence limit (500) - stopping expansion.");
                        break; 
                    }
                }
            }
        }
    }
    return expanded;
}


// ==========================
// Evaluation
// ==========================

private void evaluateSchedule(long now)
{
  boolean occNow = false;
  String currentNames = "";

  long nextStart = Long.MAX_VALUE;
  long nextEnd   = Long.MAX_VALUE;

  // --- Scan all events ---
  // Note: List iteration is fast for <1000 items
  for (int i=0; i<eventCache.size(); i++) {
    IcalEvent ev = (IcalEvent) eventCache.get(i);
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

  // --- Determine next change edge ---
  long    nextChange = -1L;
  boolean nextValue  = occNow;

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
  getOccupiedOut().setValue(occNow);
  getOccupiedOut().setStatus(BStatus.ok);

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

  String eventNameStr =
      (currentNames != null && currentNames.length() > 0)
          ? currentNames
          : "none";

  int parsedCount = eventCache.size();

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

// Safe Boolean Helper
private boolean safeBool(BStatusBoolean b)
{
  return b != null && b.getStatus().isOk() && b.getValue();
}

// Logging Helper - CHECKS SLOT FIRST
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

private void applyDefaultConfig()
{
  try {
    boolean badPeriod =
        (getIcsFetchPeriodSeconds() == null) ||
        !getIcsFetchPeriodSeconds().getStatus().isOk() ||
        getIcsFetchPeriodSeconds().getValue() <= 0.0;

    if (badPeriod) {
      getIcsFetchPeriodSeconds().setValue(3600.0);
      getIcsFetchPeriodSeconds().setStatus(BStatus.ok);
    }
  }
  catch (Exception e) {}

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
  catch (Exception e) {}
}

```

</details>
