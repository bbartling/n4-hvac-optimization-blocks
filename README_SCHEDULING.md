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
<summary>📅 iCal Schedule Block (Multi-Zone, Cloud-Driven Scheduling)</summary>

This block converts a standard **iCalendar (.ics)** URL into a **multi-zone occupancy schedule** inside Niagara.
You can map **up to 10 BAS zones** to event names in Google Calendar (or Outlook, Apple Calendar, SchoolDude, etc.), and the block will compute:

* Zone occupied / unoccupied
* Next change time
* Next value at that time
* A human-readable `statusTrace`
* Diagnostic information for troubleshooting
* Optional console logs

All scheduling is evaluated in **station local time**, not cloud server timezones.

---

# 🧠 1. What is iCal, for BAS Developers?

iCalendar (**iCal**, extension `.ics`) is the world’s standard for exchanging calendar events.
Every major calendar tool uses it:

* Google Calendar
* Outlook / Office 365
* Apple Calendar
* School calendars
* Public events / holiday feeds

### **The important BAS-friendly description:**

> **An iCal feed is just a plain-text file served by HTTP GET.
> No POST. No API tokens. No JSON.
> You download text and interpret the events.**

This single file contains many lines like:

```
BEGIN:VEVENT
DTSTART:20251201T140000Z
DTEND:20251201T150000Z
SUMMARY:gym
END:VEVENT
```

A BAS does not need the full RFC spec — the block only needs the handful of fields used to express:

* start time
* end time
* event name
* recurring events

---

# 🌐 2. How the BAS Uses an iCal URL

You give the ProgramObject your `.ics` URL:

```
https://calendar.google.com/calendar/ical/.../basic.ics
```

The Niagara station simply performs:

```
HTTP GET https://...
```

and receives **text/calendar** content.

There is **no REST POST**, no bidirectional communication.
The block *pulls* text → parses it → creates a cached event list.

---

# 🏫 3. The Real World Use Case: School or Office Schedules

Below is your actual example month:
(Events like "gym", "offices", "classrooms", "cafe" repeating daily)

And the event configuration screen that generates an iCal payload:

Finally, the actual iCal URL shown in Google calendar settings:

These events become *zone-level BAS occupancy*.

---

# 🧩 4. Block Overview (10 Zones)

The block contains slots for **10 independent zone name mappings**, like:

* gym
* offices
* classrooms
* cafe
* etc.

Each event in the calendar (SUMMARY:…) is matched against these names **case-insensitive**.

Output slots are produced per zone:

| For each zone   | Example         | Meaning                                  |
| --------------- | --------------- | ---------------------------------------- |
| `zoneNOcc`      | `zone1Occ`      | Whether the zone is currently occupied   |
| `zoneNNextVal`  | `zone1NextVal`  | The next occupancy value (true/false)    |
| `zoneNNextTime` | `zone1NextTime` | Java-millis timestamp of the next change |

There are **30 zone outputs** total.

---

# 🏎 5. Two Internal Loops

### 🐢 **Slow Loop** — ICS Fetching

Runs only when:

* `updateNow` is pressed
* the fetch period expires
* station first starts
* the event cache is empty

Slow loop does:

* GET the `.ics` file
* Parse all VEVENT blocks
* Expand recurring rules
* Store a safe 45-day window
* Log debug info
* Update `lastFetchTs`

### ⚡ **Fast Loop** — Schedule Evaluation

Runs every **10 seconds**, with no network activity.

Evaluates:

* Station Time
* Every event
* Every configured zone

Writes:

* `zoneNOcc`
* `zoneNNextVal`
* `zoneNNextTime`
* `statusTrace`

This makes the schedule **responsive and low-CPU** even on a JACE.

---

# 🛠 6. Slot Table (Clean, Updated)

Below is the simplified and cleaned-up slot table:

| Slot                  | Type           | Writable | Purpose                                     |
| --------------------- | -------------- | -------- | ------------------------------------------- |
| enable                | BStatusBoolean | YES      | Master enable; when false, all outputs Null |
| testFault             | BStatusBoolean | YES      | Force all outputs to Fault (test mode)      |
| icsUrl                | BStatusString  | YES      | iCal `.ics` URL                             |
| icsFetchPeriodSeconds | BStatusNumeric | YES      | Slow loop download period                   |
| updateNow             | BStatusBoolean | YES      | One-shot manual fetch trigger               |
| logToConsole          | BStatusBoolean | YES      | Print all events to Application Director    |
| statusTrace           | BStatusString  | NO       | Human-friendly live state                   |
| zoneName1…zoneName10  | BStatusString  | YES      | Event names linked to zones                 |
| zoneNOcc              | BStatusBoolean | NO       | Current occupancy for zone N                |
| zoneNNextVal          | BStatusBoolean | NO       | Next occupancy value for zone N             |
| zoneNNextTime         | BStatusNumeric | NO       | Millis timestamp for next change            |

This gives operators **full transparency**.

---

# 🧰 7. How to Wire It in Niagara

Typical pattern:

```
iCalBlock.zone1Occ → HVAC_SCHEDULE1.in
iCalBlock.zone2Occ → HVAC_SCHEDULE2.in
…
```

Or link multiple zones into an AHU-level occupancy selector:

```
(Zone1Occ OR Zone2Occ OR Zone3Occ) → AHU_Occupied
```

The `NextTime` and `NextValue` outputs can drive:

* **optimal start blocks**
* **early-close logic**
* **preheat/pre-cool predictors**
* **GEB / load-shaping strategies**

---

# 🔍 8. Troubleshooting Guide

### **❌ The BAS shows everything as NULL**

Likely causes:

* `enable = false`
* All 10 zone names are empty
* ICS URL is empty
* ICS fetch failed (check `statusTrace`)

### **❌ All outputs show FAULT**

Cause:

* `testFault = true`
* ICS download error
* ICS not reachable

### **❌ Times are off by 1–2 hours**

Usually caused by:

* Google Calendar user in different timezone
* But block forces local station timezone → safe behavior
* Look at `formatLocal()` in `statusTrace`

### **❌ Repeating events not expanding**

Check:

* RRULE has FREQ=WEEKLY
* Does not hit safety rule of >500 expanded events

### **❌ Events not matching zones**

Check:

* Event SUMMARY matches zone name exactly (case-insensitive)
* Example: SUMMARY: gym → zoneName1 = gym

---

# 📘 9. Basic Tutorial (for Beginners)

### **Step 1 — Make a Google Calendar**

Add events like:

* 6am gym
* 8am offices
* 10am classrooms

### **Step 2 — Get the iCal URL**

Google Calendar → Settings → “Secret address in iCal format”

### **Step 3 — Paste URL into the block**

Slot: `icsUrl`

### **Step 4 — Enter zone names**

Example:

| zoneName1 | gym |
| zoneName2 | offices |
| zoneName3 | classrooms |
| zoneName4 | cafe |

### **Step 5 — Link outputs to your BAS logic**

Link zone occupancy to your AHU/VAV/Schedule.

### **Step 6 — Watch `statusTrace`**

Shows:

```
Time=2025-12-01 06:01 | ActiveZones=2 | CachedEvents=120
```

---

# 🎯 10. Why This Block Is Powerful

* Integrates **cloud calendars → BAS control**
* Allows teachers / admins to control rooms by updating a calendar
* Works on JACE / Supervisor
* No cloud API keys
* Pure GET text — ultra-safe, ultra-lightweight
* Totally vendor-neutral
* Works with occupancy prediction / optimal start

And with your new 10-zone implementation, it’s the most capable iCal scheduling block in the BAS world.



---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalAxPropSheetSnip.png" alt="iCal AX / N4 Property Sheet" width="850">
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalSnip.png" alt="iCal Wiresheet Snip" width="850">
</p>

---



```java

////////////////////////////////////////////////////////////////
// Program Source — iCal Pure Zone Agent (10 Zones)
// Version: Production Safety Edition (Test Fault + Nulling)
////////////////////////////////////////////////////////////////

// ==========================
// Internal Types
// ==========================

class IcalEvent {
  long startMillis;
  long endMillis;
  String summary;
  boolean isAllDay;
  String rrule;

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

  applyDefaultConfig();

  getStatusTrace().setValue("iCal Zone Agent Started");
  updateTimer();
}


// ==========================
// onExecute
// ==========================

public void onExecute() throws Exception
{
  updateTimer();

  try {
    // 1. SAFETY CHECK: Enable
    // If disabled, force EVERYTHING to Null (release control)
    if (!safeBool(getEnable())) {
      forceNullOutputs("Disabled (Enable=false)");
      return;
    }

    // 2. SAFETY CHECK: Manual Test Fault
    // If operator is testing failure modes, force EVERYTHING to Fault (Yellow)
    if (safeBool(getTestFault())) {
      forceFaultOutputs("Manual Test Fault Triggered");
      return;
    }

    long now = System.currentTimeMillis();

    // ==========================================================
    // 3) SLOW LOOP — ICS DOWNLOAD
    // ==========================================================
    double fetchPeriod = 3600; 
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
    // 4) FAST LOOP — EVALUATE ZONES
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
  if (getIcsUrl().getStatus().isOk() && getIcsUrl().getValue() != null) {
    urlStr = getIcsUrl().getValue().trim();
  }

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
        continue;
      }

      if (line.equals("END:VEVENT")) {
        if (dtStart != -1L) {
          if (dtEnd == -1L) {
            dtEnd = isAllDay ? dtStart + 86400000L : dtStart + 3600000L;
          }
          rawEvents.add(new IcalEvent(dtStart, dtEnd, summary, isAllDay, rrule));
          log("Raw Event: " + summary + " (" + (rrule != null ? "Recurring" : "Single") + ")");
        }
        inEvent = false;
        continue;
      }

      if (!inEvent) continue;

      if (line.startsWith("SUMMARY:")) summary = line.substring(8).trim();
      if (line.startsWith("RRULE:")) rrule = line.substring(6).trim(); 
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
    // If fetch fails, we trigger FAULT outputs so system knows data is stale/bad
    forceFaultOutputs(err);
    log(err);
  } finally {
    try { if (reader != null) reader.close(); } catch(Exception e){}
    try { if (conn != null) conn.disconnect(); } catch(Exception e){}
  }
}

// ==========================
// Recurrence Logic
// ==========================

private java.util.List expandRecurrences(java.util.List rawEvents) {
    java.util.List expanded = new java.util.ArrayList();
    long now = System.currentTimeMillis();
    long horizon = now + (45L * 86400000L); 
    int safetyCounter = 0;
    
    for (int i=0; i<rawEvents.size(); i++) {
        IcalEvent ev = (IcalEvent) rawEvents.get(i);
        expanded.add(ev); 
        
        if (ev.rrule != null && ev.rrule.contains("FREQ=WEEKLY")) {
            long duration = ev.endMillis - ev.startMillis;
            
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
            
            java.util.Calendar ptr = java.util.Calendar.getInstance();
            ptr.setTimeInMillis(ev.startMillis);
            
            if (ptr.getTimeInMillis() < now - 86400000L) {
                ptr.setTimeInMillis(now - 86400000L);
            }

            while (ptr.getTimeInMillis() < horizon) {
                ptr.add(java.util.Calendar.DAY_OF_YEAR, 1);
                int dow = ptr.get(java.util.Calendar.DAY_OF_WEEK);
                boolean match = false;
                
                if (days.size() > 0) {
                    for(int d=0; d<days.size(); d++) {
                        if (((Integer)days.get(d)).intValue() == dow) match = true;
                    }
                } else { match = true; }
                
                if (match) {
                    long newStart = ptr.getTimeInMillis();
                    long newEnd = newStart + duration;
                    expanded.add(new IcalEvent(newStart, newEnd, ev.summary, ev.isAllDay, null));
                    
                    safetyCounter++;
                    if (safetyCounter > 500) {
                        log("WARN: Recurrence limit hit (500).");
                        break; 
                    }
                }
            }
        }
    }
    return expanded;
}


// ==========================
// Pure Multi-Zone Evaluation
// ==========================

private void evaluateSchedule(long now)
{
  // 1. Snapshot Zone Config (Slots 1-10)
  String[] zoneCfg = new String[10];
  zoneCfg[0] = safeString(getZoneName1());
  zoneCfg[1] = safeString(getZoneName2());
  zoneCfg[2] = safeString(getZoneName3());
  zoneCfg[3] = safeString(getZoneName4());
  zoneCfg[4] = safeString(getZoneName5());
  zoneCfg[5] = safeString(getZoneName6());
  zoneCfg[6] = safeString(getZoneName7());
  zoneCfg[7] = safeString(getZoneName8());
  zoneCfg[8] = safeString(getZoneName9());
  zoneCfg[9] = safeString(getZoneName10());

  // 2. Initialize State Arrays
  boolean[] zOcc = new boolean[10];
  long[] zNextStart = new long[10];
  long[] zNextEnd = new long[10];
  int activeZoneCount = 0;
  
  for(int k=0; k<10; k++) {
    zNextStart[k] = Long.MAX_VALUE;
    zNextEnd[k]   = Long.MAX_VALUE;
    zOcc[k] = false;
  }

  // 3. SCAN EVENTS
  for (int i=0; i<eventCache.size(); i++) {
    IcalEvent ev = (IcalEvent) eventCache.get(i);
    boolean nowIn = (now >= ev.startMillis && now < ev.endMillis);

    for (int z=0; z<10; z++) {
       // Only process if zone name is configured
       if (zoneCfg[z] != null && ev.summary.equalsIgnoreCase(zoneCfg[z])) {
           if (nowIn) {
               zOcc[z] = true;
               if (ev.endMillis < zNextEnd[z]) zNextEnd[z] = ev.endMillis;
           } else {
               if (ev.startMillis > now && ev.startMillis < zNextStart[z]) {
                   zNextStart[z] = ev.startMillis;
               }
           }
       }
    }
  }

  // 4. Count active zones for Trace
  for(int z=0; z<10; z++) { if(zOcc[z]) activeZoneCount++; }

  // 5. Compute & Write Zone Outputs
  writeZoneOut(0, zoneCfg[0], zOcc, zNextStart, zNextEnd, getZone1Occ(), getZone1NextVal(), getZone1NextTime());
  writeZoneOut(1, zoneCfg[1], zOcc, zNextStart, zNextEnd, getZone2Occ(), getZone2NextVal(), getZone2NextTime());
  writeZoneOut(2, zoneCfg[2], zOcc, zNextStart, zNextEnd, getZone3Occ(), getZone3NextVal(), getZone3NextTime());
  writeZoneOut(3, zoneCfg[3], zOcc, zNextStart, zNextEnd, getZone4Occ(), getZone4NextVal(), getZone4NextTime());
  writeZoneOut(4, zoneCfg[4], zOcc, zNextStart, zNextEnd, getZone5Occ(), getZone5NextVal(), getZone5NextTime());
  writeZoneOut(5, zoneCfg[5], zOcc, zNextStart, zNextEnd, getZone6Occ(), getZone6NextVal(), getZone6NextTime());
  writeZoneOut(6, zoneCfg[6], zOcc, zNextStart, zNextEnd, getZone7Occ(), getZone7NextVal(), getZone7NextTime());
  writeZoneOut(7, zoneCfg[7], zOcc, zNextStart, zNextEnd, getZone8Occ(), getZone8NextVal(), getZone8NextTime());
  writeZoneOut(8, zoneCfg[8], zOcc, zNextStart, zNextEnd, getZone9Occ(), getZone9NextVal(), getZone9NextTime());
  writeZoneOut(9, zoneCfg[9], zOcc, zNextStart, zNextEnd, getZone10Occ(), getZone10NextVal(), getZone10NextTime());

  // 6. Trace
  String nowStr  = formatLocal(new java.util.Date(now));
  String trace = "Time=" + nowStr + " | ActiveZones=" + activeZoneCount + " | CachedEvents=" + eventCache.size();

  getStatusTrace().setValue(trace);
  getStatusTrace().setStatus(BStatus.ok);
}

// Helper to write a single zone's data. 
// If cfgName is null, force outputs to NULL.
private void writeZoneOut(int idx, String cfgName, boolean[] zOcc, long[] zStart, long[] zEnd, 
                          BStatusBoolean occSlot, BStatusBoolean nextValSlot, BStatusNumeric nextTimeSlot) 
{
    // If Zone Name is empty/null, mark outputs as NULL
    if (cfgName == null) {
        occSlot.setValue(false);        occSlot.setStatus(BStatus.nullStatus);
        nextValSlot.setValue(false);    nextValSlot.setStatus(BStatus.nullStatus);
        nextTimeSlot.setValue(0.0);     nextTimeSlot.setStatus(BStatus.nullStatus);
        return;
    }

    boolean occ = zOcc[idx];
    long change = -1L;
    boolean nextVal = occ;
    
    if (!occ && zStart[idx] != Long.MAX_VALUE) {
        change = zStart[idx];
        nextVal = true;
    } else if (occ && zEnd[idx] != Long.MAX_VALUE) {
        change = zEnd[idx];
        nextVal = false;
    }
    
    occSlot.setValue(occ);
    occSlot.setStatus(BStatus.ok);
    
    if (change > 0L) {
        nextTimeSlot.setValue((double) change);
        nextTimeSlot.setStatus(BStatus.ok);
        nextValSlot.setValue(nextVal);
        nextValSlot.setStatus(BStatus.ok);
    } else {
        nextTimeSlot.setValue(0.0);
        nextTimeSlot.setStatus(BStatus.nullStatus);
        nextValSlot.setValue(false);
        nextValSlot.setStatus(BStatus.nullStatus);
    }
}


// ==========================
// Helpers
// ==========================

private boolean safeBool(BStatusBoolean b) {
  return b != null && b.getStatus().isOk() && b.getValue();
}

private String safeString(BStatusString s) {
    if (s != null && s.getStatus().isOk() && s.getValue() != null) {
        String v = s.getValue().trim();
        return (v.length() > 0) ? v : null;
    }
    return null;
}

private void log(String msg) {
  try {
    if (getLogToConsole() != null && getLogToConsole().getStatus().isOk() && getLogToConsole().getValue()) {
      System.out.println("[IcalZoneAgent] " + msg);
    }
  } catch (Exception ignore) {}
}

private void forceNullOutputs(String msg) {
  getStatusTrace().setValue(msg);
  // Force all 30 slots to NULL explicitly
  // Zone 1
  getZone1Occ().setValue(false); getZone1Occ().setStatus(BStatus.nullStatus);
  getZone1NextVal().setValue(false); getZone1NextVal().setStatus(BStatus.nullStatus);
  getZone1NextTime().setValue(0.0); getZone1NextTime().setStatus(BStatus.nullStatus);
  // Zone 2
  getZone2Occ().setValue(false); getZone2Occ().setStatus(BStatus.nullStatus);
  getZone2NextVal().setValue(false); getZone2NextVal().setStatus(BStatus.nullStatus);
  getZone2NextTime().setValue(0.0); getZone2NextTime().setStatus(BStatus.nullStatus);
  // Zone 3
  getZone3Occ().setValue(false); getZone3Occ().setStatus(BStatus.nullStatus);
  getZone3NextVal().setValue(false); getZone3NextVal().setStatus(BStatus.nullStatus);
  getZone3NextTime().setValue(0.0); getZone3NextTime().setStatus(BStatus.nullStatus);
  // Zone 4
  getZone4Occ().setValue(false); getZone4Occ().setStatus(BStatus.nullStatus);
  getZone4NextVal().setValue(false); getZone4NextVal().setStatus(BStatus.nullStatus);
  getZone4NextTime().setValue(0.0); getZone4NextTime().setStatus(BStatus.nullStatus);
  // Zone 5
  getZone5Occ().setValue(false); getZone5Occ().setStatus(BStatus.nullStatus);
  getZone5NextVal().setValue(false); getZone5NextVal().setStatus(BStatus.nullStatus);
  getZone5NextTime().setValue(0.0); getZone5NextTime().setStatus(BStatus.nullStatus);
  // Zone 6
  getZone6Occ().setValue(false); getZone6Occ().setStatus(BStatus.nullStatus);
  getZone6NextVal().setValue(false); getZone6NextVal().setStatus(BStatus.nullStatus);
  getZone6NextTime().setValue(0.0); getZone6NextTime().setStatus(BStatus.nullStatus);
  // Zone 7
  getZone7Occ().setValue(false); getZone7Occ().setStatus(BStatus.nullStatus);
  getZone7NextVal().setValue(false); getZone7NextVal().setStatus(BStatus.nullStatus);
  getZone7NextTime().setValue(0.0); getZone7NextTime().setStatus(BStatus.nullStatus);
  // Zone 8
  getZone8Occ().setValue(false); getZone8Occ().setStatus(BStatus.nullStatus);
  getZone8NextVal().setValue(false); getZone8NextVal().setStatus(BStatus.nullStatus);
  getZone8NextTime().setValue(0.0); getZone8NextTime().setStatus(BStatus.nullStatus);
  // Zone 9
  getZone9Occ().setValue(false); getZone9Occ().setStatus(BStatus.nullStatus);
  getZone9NextVal().setValue(false); getZone9NextVal().setStatus(BStatus.nullStatus);
  getZone9NextTime().setValue(0.0); getZone9NextTime().setStatus(BStatus.nullStatus);
  // Zone 10
  getZone10Occ().setValue(false); getZone10Occ().setStatus(BStatus.nullStatus);
  getZone10NextVal().setValue(false); getZone10NextVal().setStatus(BStatus.nullStatus);
  getZone10NextTime().setValue(0.0); getZone10NextTime().setStatus(BStatus.nullStatus);
}

private void forceFaultOutputs(String msg) {
  getStatusTrace().setValue(msg);
  // Force all 30 slots to FAULT status explicitly
  getZone1Occ().setStatus(BStatus.fault);
  getZone1NextVal().setStatus(BStatus.fault);
  getZone1NextTime().setStatus(BStatus.fault);

  getZone2Occ().setStatus(BStatus.fault);
  getZone2NextVal().setStatus(BStatus.fault);
  getZone2NextTime().setStatus(BStatus.fault);

  getZone3Occ().setStatus(BStatus.fault);
  getZone3NextVal().setStatus(BStatus.fault);
  getZone3NextTime().setStatus(BStatus.fault);

  getZone4Occ().setStatus(BStatus.fault);
  getZone4NextVal().setStatus(BStatus.fault);
  getZone4NextTime().setStatus(BStatus.fault);

  getZone5Occ().setStatus(BStatus.fault);
  getZone5NextVal().setStatus(BStatus.fault);
  getZone5NextTime().setStatus(BStatus.fault);

  getZone6Occ().setStatus(BStatus.fault);
  getZone6NextVal().setStatus(BStatus.fault);
  getZone6NextTime().setStatus(BStatus.fault);

  getZone7Occ().setStatus(BStatus.fault);
  getZone7NextVal().setStatus(BStatus.fault);
  getZone7NextTime().setStatus(BStatus.fault);

  getZone8Occ().setStatus(BStatus.fault);
  getZone8NextVal().setStatus(BStatus.fault);
  getZone8NextTime().setStatus(BStatus.fault);

  getZone9Occ().setStatus(BStatus.fault);
  getZone9NextVal().setStatus(BStatus.fault);
  getZone9NextTime().setStatus(BStatus.fault);

  getZone10Occ().setStatus(BStatus.fault);
  getZone10NextVal().setStatus(BStatus.fault);
  getZone10NextTime().setStatus(BStatus.fault);
}

private ParsedDate parseDate(String line) {
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
          java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("yyyyMMdd'T'HHmmss");
          f.setTimeZone(java.util.TimeZone.getDefault());
          java.util.Date d = f.parse(v.substring(0,15));
          return new ParsedDate(d.getTime(), false);
        }
      }
    }
  } catch (Exception ignore) {}
  return null;
}

private String formatLocal(java.util.Date d) {
  java.text.SimpleDateFormat f = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm");
  f.setTimeZone(java.util.TimeZone.getDefault());
  return f.format(d);
}

private void applyDefaultConfig() {
  try {
    boolean badPeriod = (getIcsFetchPeriodSeconds() == null) || !getIcsFetchPeriodSeconds().getStatus().isOk() || getIcsFetchPeriodSeconds().getValue() <= 0.0;
    if (badPeriod) {
      getIcsFetchPeriodSeconds().setValue(3600.0);
      getIcsFetchPeriodSeconds().setStatus(BStatus.ok);
    }
  } catch (Exception e) {}
  try {
    String url = null;
    if (getIcsUrl() != null && getIcsUrl().getStatus().isOk()) url = getIcsUrl().getValue();
    if (url == null || url.trim().length() == 0) {
      getIcsUrl().setValue("https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics");
      getIcsUrl().setStatus(BStatus.ok);
    }
  } catch (Exception e) {}
}

```

</details>
