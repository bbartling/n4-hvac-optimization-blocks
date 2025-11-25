# 📅 Schedules & Programmatic Weekly Calendars

* ***TODO NOT FINISHED!***

This sub-guide explains how Niagara scheduling works and how to build a generic **Monday–Friday 8-5 occupancy schedule** inside a **ProgramObject** — with full support for overriding a real BooleanSchedule using its **In** slot.

Written in the same friendly high-signal vibe as your other docs 📡

---

# 🚦 Types of Schedules

Niagara has **four** schedule component types. All share the same views, tabs, and workflow.

### 1️⃣ **Weekly Schedules**

Define repeating events by **day of week + time of day**.
They can also include **special events** such as holidays.

Four variants by datatype:

* `BooleanSchedule`
* `NumericSchedule`
* `EnumSchedule`
* `StringSchedule`

### 2️⃣ **Calendar Schedules**

Define specific **dates**, **date ranges**, or **recurring exceptions**.
Weekly schedules **reference** calendar schedules to override the normal week.

### 3️⃣ **Trigger Schedules**

Fire “topics” or actions at specific times.

Useful for:

* alarms
* reports
* scripting
* MQTT publishing
* digital events

### 4️⃣ **ScheduleSelector**

A dropdown allowing operators to choose between schedules.

---

# 🧠 Weekly Schedule Behavior

Each WeeklySchedule has two important slots:

| Slot    | Meaning                                                             |
| ------- | ------------------------------------------------------------------- |
| **Out** | The computed schedule output at this moment                         |
| **In**  | Optional override value (if non-null → *bypass all schedule logic*) |

### 🔺 Weekly Schedule Priority Stack

From highest to lowest:

1. **In override** → If `In` receives a non-null value, it **wins**
2. **Special event** (holiday, exception)
3. **Weekly event** (normal time-of-day block)
4. **Default output** (configured on Properties tab)

This means:

> If your ProgramObject writes to a BooleanSchedule’s **In**, you now own the schedule output completely.

---

# 🗓 Special Events

Weekly schedules allow one-time or recurring exceptions:

* Holidays
* Early release
* Late start
* Shutdown days

Special events sit **just below** the In override in the priority stack.

---

# 🏢 Master / Slave Schedules (Enterprise)

Niagara supports master/slave schedules across the driver layer.

Changing the master updates all slaves.

Great for:

* enterprise holiday calendars
* chain-wide store hours
* campus-wide occupancy patterns

---

# 🧰 Schedule Subsystem Internals (From the Decompiled Module)

The uploaded `scheduleModule.zip` contained the full internal scheduler classes.
Here’s a vibe-coder summary of the important ones:

| Java Class                                               | What It Does                                                          |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| **BIScheduleSnapshotHandler / BScheduleSnapshotHandler** | Takes UI edits → validates → writes back to live schedule objects     |
| **ScheduleUtil**                                         | Month/day arrays, deep-copy helpers, dynamic property ordering        |
| **ScheduleValidator**                                    | Validates date, time, weekday, date-range logic                       |
| **Chronometer**                                          | GregorianCalendar wrapper with Niagara types (`BAbsTime`, `BWeekday`) |
| **ExecutionQueue**                                       | Worker thread pool for schedule processing tasks                      |
| **ScheduleSpyManager**                                   | Debugger for scheduler threads + timing                               |
| **IntSet**                                               | Minimal integer set used for events                                   |
| **SimpleSortedSet**                                      | Lightweight sorted linked structure for event ordering                |

Most users never interact with these — but they explain why scheduling is deterministic, thread-safe, and able to calculate `NextTime` efficiently.

---

# 🧪 Programmatically Driving a Weekly Schedule

### *Using a ProgramObject to override a BooleanSchedule.In*

Use case:

* You want to bypass the schedule UI
* You want a computed schedule (e.g., ML model, occupancy prediction)
* You want a simple hard-coded 8–5 building hours

Just **link the ProgramObject output → BooleanSchedule.in**.

This is the recommended way to override a schedule.

---

# 🕒 Monday–Friday 8-5 Occupancy ProgramObject

### 🧩 Required Slots (create in Slot Sheet)

| Slot Name     | Type             | Purpose                                |
| ------------- | ---------------- | -------------------------------------- |
| `enable`      | `BStatusBoolean` | Master enable flag                     |
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

# 💻 ProgramObject Code (Clean Vibe-Coder Format)

### *No imports. No headers. No boilerplate. Just paste into Source.*

> **This version follows your rule:**
> ❌ No imports
> ❌ No class header
> ✔️ Only fields + methods inside ProgramImpl
> ✔️ Workbench creates getters/setters automatically

```java
////////////////////////////////////////////////////////////
// Class-level state
////////////////////////////////////////////////////////////

private Clock.Ticket ticket = null;

// Run every 60 seconds
private static final int EXEC_PERIOD_SEC = 60;

// Office hours (local station time)
private static final int START_HOUR = 8;   // 8:00 AM
private static final int END_HOUR   = 17;  // 5:00 PM (end exclusive)


////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////

public void onStart() throws Exception {
    updateTimer();
    getStatusTrace().setValue("8–5 weekly schedule ProgramObject started.");
}

public void onExecute() throws Exception {
    updateTimer();

    // If disabled → return NULL / FALSE
    if (!safeBool(getEnable())) {
        getOccupiedOut().setValue(false);
        getOccupiedOut().setStatus(BStatus.NULL);
        getStatusTrace().setValue("Disabled — output forced NULL/false");
        return;
    }

    // Current station time
    BAbsTime now = Clock.time();
    BDateTime dt = now.getDateTime(BRelTime.ZERO);
    BDate date   = dt.getDate();
    BTime time   = dt.getTime();

    int dow      = date.getDayOfWeek(); // 1=Mon ... 7=Sun
    int hour     = time.getHour();
    int minute   = time.getMinute();

    boolean isWeekday   = (dow >= 1 && dow <= 5);
    boolean inHourRange = 
           (hour > START_HOUR && hour < END_HOUR)
        || (hour == START_HOUR)
        || (hour == END_HOUR && minute == 0);

    boolean occ = isWeekday && inHourRange;

    getOccupiedOut().setValue(occ);
    getOccupiedOut().setStatus(BStatus.ok);

    getStatusTrace().setValue(
        "Now=" + dt.toString() + 
        " DOW=" + dow + 
        " occ=" + occ +
        " (M–F " + START_HOUR + ":00–" + END_HOUR + ":00)"
    );
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
    ticket = null;
    getStatusTrace().setValue("ProgramObject stopped.");
}


////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(
        getComponent(),
        BRelTime.makeSeconds(EXEC_PERIOD_SEC),
        BProgram.execute,
        null
    );
}

// Safe Boolean extraction
private boolean safeBool(BStatusBoolean b) {
    try {
        if (b == null || b.isNull()) return false;
        if (!b.getStatus().isOk())  return false;
        return b.getValue();
    }
    catch (Exception e) {
        return false;
    }
}
```

---

<details>
<summary>🗓️ iCal Integration</summary>

Use this block to **subscribe** to an online iCalendar (`.ics`) feed (e.g., shared Google/Outlook/Apple calendar URLs) and expose “next event” details inside Niagara for schedule logic (holiday/vacation shutdowns, special events, etc.). This is designed for a **Program Object**—the Java is already done; this section just documents how to set it up.

The iCal program makes an HTTP GET request to a URL specified in its icsUrl slot, fetching a raw text file in the iCalendar (.ics) format. It then processes this text by looping through each VEVENT block, parsing the SUMMARY, LOCATION, DESCRIPTION, and DTSTART tags to create a list of EventInfo Java objects. Finally, it accesses the target BCalendarSchedule component via its calendarOrd slot, locks it, and dynamically adds new BDateSchedule children, each populated with the specific Year, Month, and Day derived from the event's start time.

> Note this is a concept idea that only works with CalenderSchedules. Future TODO will be to overhaul with generic weekly schedules.

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalAxPropSheetSnip.png" alt="iCal AX / N4 Property Sheet" width="850">
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalSnip.png" alt="iCal Wiresheet Snip" width="850">
</p>

---

### ⚙️ Slot Sheet (suggested)
| Slot Name               | Type             | Writable | Notes |
| ---                     | ---              | ---      | --- |
| `calendarUrl`           | `BStatusString`  | ✅       | Full HTTPS URL to the **.ics** feed (public/share link). |
| `internalUpdateSeconds` | `BStatusNumeric` | ✅       | How often to refresh, seconds (e.g., `21600` = 6h). |
| `updateNow`             | `BStatusBoolean` | ✅       | Toggle `true` to force an immediate fetch (auto-resets `false`). |
| `statusTrace`           | `BStatusString`  | ❌       | Short “OK / ERROR: …” health text. |
| `lastRefreshTs`         | `BStatusString`  | ❌       | Timestamp of last successful refresh. |
| `nextEventsJson`        | `BStatusString`  | ❌       | JSON array of upcoming events (already normalized in code). |
| `etagCache` (optional)  | `BStatusString`  | ❌       | If-None-Match cache to reduce bandwidth (if your code uses it). |

> **Tip:** The slot formerly called `pollSeconds` was renamed to `internalUpdateSeconds` for clarity.

---

### ✅ How to use
1. **Set `calendarUrl`** to a public/subscribable `.ics` link (not a file import).  
   - Google Calendar: “**Settings → Integrate calendar → Secret address in iCal format**”.  
   - Outlook/Apple: share/publish the calendar and copy the iCal URL.
2. **(Optional) Enable trigger:** Check **Execute On Change** for `updateNow` so a **true** write runs the fetch immediately.
3. **Refresh cadence:** The program’s internal timer uses `internalUpdateSeconds` to re-pull the feed on a fixed schedule.
4. **Consume results:** Read `nextEventsJson` (stringified JSON) for your logic—e.g., “if any event today tagged Public/Bank Holiday → disable schedules”.

---

### 🔎 Practical notes
- **Subscribe vs. Import:** Use a **URL subscription** so clients stay in sync; avoid one-time calendar file imports.  
- **Throttling:** Most calendar hosts update **every few hours**. Avoid setting `internalUpdateSeconds` too low.  
- **Null-safety:** If URL is empty or fetch fails, `statusTrace` shows the error and outputs remain unchanged.
- **Filtering:** Your Program Object’s Java already normalizes and filters events; this doc just standardizes the slots/UI.

---

### 💻 Java Code

> Testing on next space flight ical: https://nextspaceflight.com/calendar/


```java
////////////////////////////////////////////////////////////////
// Program Source — ICS Subscriber (v3 - Concurrency Fix)
////////////////////////////////////////////////////////////////

// Runtime
private Clock.Ticket ticket;
private long lastFetchMs = 0L;

// Small record for parsed events
class EventInfo implements Comparable<EventInfo> {
  java.util.Date startTime;
  java.util.Date endTime;   
  String summary;
  String location;       
  String description;   

  EventInfo(java.util.Date start, java.util.Date end, String sum, String loc, String desc) {
    this.startTime = start;
    this.endTime = end;
    this.summary = sum;
    this.location = loc;
    this.description = desc;
  }

  // Null-safe comparison
  public int compareTo(EventInfo o) {
    if (this.startTime == null && o.startTime == null) return 0;
    if (this.startTime == null) return -1;
    if (o.startTime == null) return 1;
    return this.startTime.compareTo(o.startTime);
  }
}

// ================= Lifecycle =================

public void onStart() throws Exception {
  log("onStart");
  getStatusTrace().setValue("Program started.");
  scheduleHeartbeat();
}

public void onExecute() throws Exception {
  // 1) Manual/External fetch trigger
  try {
    if (getUpdateNow().getStatus().isOk() && getUpdateNow().getValue()) {
      log("updateNow=TRUE → fetching ICS once");
      fetchAndParseIcsOnce();
      try { setUpdateNow(new BStatusBoolean(false)); } catch (Exception ignore) {}
    }
  } catch (Exception ignore) {}

  // 2) Heartbeat: recompute eventActive (no network)
  try { computeEventActiveToday(); } catch (Exception e) { log("eventActive error: " + e.getMessage()); }

  scheduleHeartbeat();
}

public void onStop() throws Exception {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  log("onStop");
  getStatusTrace().setValue("Program stopped.");
}

// ================= Heartbeat (internalUpdateSeconds) =================

private void scheduleHeartbeat() {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  int secs = 10; // default 10s
  try {
    if (getInternalUpdateSeconds().getStatus().isOk())
      secs = (int)Math.max(2, Math.min(600, getInternalUpdateSeconds().getValue()));
    setInternalUpdateSeconds(new BStatusNumeric(secs));
  } catch (Exception ignore) {}
  // Use a shorter heartbeat (e.g., 60s) if you use the StringWritable
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(secs), BProgram.execute, null);
  log("next heartbeat in " + secs + "s");
}

// ================= Core: one-shot fetch + write =================

private void fetchAndParseIcsOnce() {
  long t0 = System.currentTimeMillis();

  String url = "https://calendar.google.com/calendar/ical/nextspaceflight.com_l328q9n2alm03mdukb05504c44%40group.calendar.google.com/public/basic.ics";
  try {
    if (getIcsUrl().getStatus().isOk() && !getIcsUrl().getValue().isEmpty())
      url = getIcsUrl().getValue();
    else
      setIcsUrl(new BStatusString(url));
  } catch (Exception ignore) {}

  BComponent calComp = resolveCalendar();
  if (calComp == null) {
    getStatusTrace().setValue("ERROR: calendarOrd does not resolve to a Calendar Schedule.");
    log("calendarOrd unresolved");
    return;
  } else {
    log("calendarOrd resolved → " + calComp.getType().toString());
  }

  java.net.HttpURLConnection conn = null;
  java.util.List<EventInfo> events = new java.util.ArrayList<>();
  try {
    log("GET " + url);
    java.net.URL u = new java.net.URL(url);
    conn = (java.net.HttpURLConnection)u.openConnection();
    conn.setRequestMethod("GET");
    conn.setConnectTimeout(10000);
    conn.setReadTimeout(10000);

    int code = conn.getResponseCode();
    java.io.InputStream is = (code >= 200 && code < 300) ? conn.getInputStream() : conn.getErrorStream();
    java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(is, "UTF-8"));

    events = parseIcsStream(r);
    r.close();

    if (code < 200 || code >= 300) throw new Exception("HTTP " + code);

    log("parsed future events: " + events.size());
  } catch (Exception e) {
    getStatusTrace().setValue("ERROR: fetch/parse " + e.getMessage());
    log("fetch error: " + e.getMessage());
    return;
  } finally {
    if (conn != null) conn.disconnect();
  }

  try {
    int added = updateCalendarChildren(calComp, events); // This is now thread-safe
    lastFetchMs = System.currentTimeMillis();

    getLastFetchTs().setValue(new java.util.Date(t0).toString());
    getEventsAdded().setValue(added);

    StringBuilder sb = new StringBuilder();
    if (!events.isEmpty()) {
      EventInfo next = events.get(0);
      String nextEventStr = next.summary + " @ " + next.startTime.toString();
      if (next.location != null && !next.location.isEmpty()) {
        nextEventStr += " (Loc: " + next.location + ")";
      }
      getNextEvent().setValue(nextEventStr);
      
      // Populate the string writable for ALL events
      for(EventInfo ev : events) {
        if(ev == null || ev.summary == null || ev.startTime == null) continue;
        sb.append("EVENT: ").append(ev.summary).append("\n");
        sb.append("  START: ").append(ev.startTime).append("\n");
        if(ev.endTime != null) sb.append("  END: ").append(ev.endTime).append("\n");
        if(ev.location != null) sb.append("  LOC: ").append(ev.location).append("\n");
        if(ev.description != null) sb.append("  DESC: ").append(ev.description).append("\n");
        sb.append("\n");
      }

    } else {
      getNextEvent().setValue("No upcoming events");
    }
    
    // Assuming you have a BStatusString slot named 'stringWritable'
    // getStringWritable().setValue(sb.toString());

    getStatusTrace().setValue("OK: Fetched " + events.size() + ", added " + added);
    log("update complete; added " + added);
  } catch (Exception e) {
    log("Niagara update error: " + e.getMessage());
    getStatusTrace().setValue("ERROR updating calendar: " + e.getMessage());
  }
}

// ================= ICS parse (Handles UTC DTSTART AND All-Day VALUE=DATE) =================
private java.util.List<EventInfo> parseIcsStream(java.io.BufferedReader reader) throws Exception {
  java.util.List<EventInfo> out = new java.util.ArrayList<>();
  
  java.text.SimpleDateFormat utcFormat = new java.text.SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'");
  utcFormat.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
  
  java.text.SimpleDateFormat allDayFormat = new java.text.SimpleDateFormat("yyyyMMdd");
  allDayFormat.setTimeZone(java.util.Calendar.getInstance().getTimeZone()); // Use JACE's local timezone
  
  long now = System.currentTimeMillis();
  String line; 
  boolean inVEvent=false; 
  
  String sum = null;
  java.util.Date start = null;
  java.util.Date end = null;
  String loc = null;
  String desc = null;

  while ((line = reader.readLine()) != null) {
    if ("BEGIN:VEVENT".equals(line)) { 
      inVEvent=true; 
      sum = null; start = null; end = null; loc = null; desc = null; // Reset for new event
      log("... found BEGIN:VEVENT");
      continue; 
    }
    
    if ("END:VEVENT".equals(line))   {
      if (inVEvent && sum != null && start != null && start.getTime() > now) {
        log("... adding event: " + sum + " @ " + start.toString());
        out.add(new EventInfo(start, end, sum, loc, desc)); 
      } else if (inVEvent) {
        log("... skipping event (missing summary/start, or is in the past)");
      }
      inVEvent=false; 
      continue;
    }
    
    if (!inVEvent) continue;
    
    if (line.startsWith("SUMMARY:")) {
      sum = line.substring(8);
      log("       SUMMARY: " + sum);
    }
    else if (line.startsWith("LOCATION:")) {
      loc = line.substring(9);
      log("      LOCATION: " + loc);
    }
    else if (line.startsWith("DESCRIPTION:")) {
      desc = line.substring(12); // Does not handle multi-line descriptions
      log("   DESCRIPTION: " + desc);
    }
    
    // --- DTSTART Parsers ---
    else if (line.startsWith("DTSTART;VALUE=DATE:")) {
      try {
        String dateStr = line.substring(line.indexOf(':') + 1).trim();
        if (dateStr.length() > 8) dateStr = dateStr.substring(0, 8); // Clean extra chars
        start = allDayFormat.parse(dateStr); 
        log("       DTSTART (All-Day): " + start.toString());
      } catch (java.text.ParseException pe) { 
        log("Failed to parse all-day date: " + line);
        start = null; 
      }
    }
    else if (line.startsWith("DTSTART:")) {
      try { 
        String timeStr = line.substring(line.indexOf(':') + 1).trim();
        start = utcFormat.parse(timeStr); 
        log("       DTSTART (UTC): " + start.toString());
      } catch (java.text.ParseException pe) { 
        log("Skipping non-UTC time format: " + line);
        start = null; 
      }
    }
    
    // --- DTEND Parsers ---
    else if (line.startsWith("DTEND;VALUE=DATE:")) {
      try {
        String dateStr = line.substring(line.indexOf(':') + 1).trim();
        if (dateStr.length() > 8) dateStr = dateStr.substring(0, 8);
        end = allDayFormat.parse(dateStr); 
        log("         DTEND (All-Day): " + end.toString());
      } catch (java.text.ParseException pe) { 
        log("Failed to parse all-day end date: " + line);
        end = null; 
      }
    }
    else if (line.startsWith("DTEND:")) {
      try { 
        String timeStr = line.substring(line.indexOf(':') + 1).trim();
        end = utcFormat.parse(timeStr); 
        log("         DTEND (UTC): " + end.toString());
      } catch (java.text.ParseException pe) { 
        log("Skipping non-UTC end time format: " + line);
        end = null; 
      }
    }
  }
  java.util.Collections.sort(out);
  return out;
}

// ================= Write BDateSchedule children (all-day markers) =================

private int updateCalendarChildren(BComponent parentCal, java.util.List<EventInfo> events) {
  String prefix = "";
  if (getNamePrefix().getStatus().isOk()) prefix = getNamePrefix().getValue();

  int max = 10;
  if (getMaxEvents().getStatus().isOk()) max = (int)getMaxEvents().getValue();

  log("Preparing to add events: parsed=" + events.size() + ", max=" + max + ", prefix='" + prefix + "'");

  int removed = 0;
  int added = 0;

  // Lock the calendar component to prevent race-condition crashes
  synchronized (parentCal) {
  
    // --- 1. Remove our prior children ---
    BComponent[] kids = parentCal.getChildComponents(); // Get a snapshot of children
    for (BComponent k : kids) {
      if (prefix.isEmpty() || k.getName().startsWith(prefix)) {
        try { 
          parentCal.remove(k.getName()); 
          removed++; 
        } catch (Exception ignore) {}
      }
    }
    log("Removed prior children with prefix: " + removed);

    // --- 2. Add new children ---
    java.util.Calendar cal = java.util.Calendar.getInstance(); // Use JACE's local timezone

    for (int i=0; i<events.size() && i<max; i++) {
      EventInfo ev = events.get(i);

      // --- Start of new/modified name logic ---
      
      // 1. Sanitize the summary (replace bad chars with _)
      String cleanSummary = ev.summary.replaceAll("[^a-zA-Z0-9_]", "_");
      
      // 2. Collapse multiple underscores (e.g., "___") into one
      cleanSummary = cleanSummary.replaceAll("__+", "_"); 
      
      // 3. Truncate the summary part to a shorter length
      int maxSummaryLength = 30; // <-- YOU CAN CHANGE THIS VALUE
      if (cleanSummary.length() > maxSummaryLength) {
        cleanSummary = cleanSummary.substring(0, maxSummaryLength);
      }
      
      // 4. Add the prefix (if any) and the unique index
      String nm = prefix + cleanSummary + "_" + (i+1);
      // --- End of new/modified name logic ---

      try {
        cal.setTime(ev.startTime); // Set calendar to the event's start time

        BDateSchedule ds = new BDateSchedule();
        ds.setYear(cal.get(java.util.Calendar.YEAR));
        ds.setMonth(BMonth.make(cal.get(java.util.Calendar.MONTH)));   // 0..11
        ds.setDay(cal.get(java.util.Calendar.DAY_OF_MONTH));

        parentCal.add(nm, ds);
        added++;
      } catch (Exception e) {
        log("add '" + nm + "' failed: " + e.getMessage());
      }
    }
    log("Added new children: " + added);
    
  } // --- End of synchronized block ---

  return added;
}

// ================= eventActive (today matches any BDateSchedule) =================

private void computeEventActiveToday() {
  BComponent cal = resolveCalendar();
  if (cal == null) return;

  java.util.Calendar now = java.util.Calendar.getInstance(); // Uses JACE's local timezone
  final int y = now.get(java.util.Calendar.YEAR);
  final int m = now.get(java.util.Calendar.MONTH);         // 0..11
  final int d = now.get(java.util.Calendar.DAY_OF_MONTH);  // 1..31

  boolean active = false;
  // We must also lock here when reading, to be fully thread-safe
  synchronized (cal) {
    for (BComponent c : cal.getChildComponents()) {
      try {
        if (c instanceof BDateSchedule) {
          BDateSchedule ds = (BDateSchedule) c;
          if (ds.getYear() == y && ds.getMonth() == m && ds.getDay() == d) {
            active = true; break;
          }
        }
      } catch (Exception ignore) {}
    }
  } // --- End of synchronized block ---

  try { setEventActive(new BStatusBoolean(active)); } catch (Exception ignore) {}
  if (active) try { getStatusTrace().setValue("OK: eventActive=true (today)"); } catch (Exception ignore) {}
}

// ================= Helpers =================

private BComponent resolveCalendar() {
  try {
    if (getCalendarOrd().isNull()) return null;
    BObject o = getCalendarOrd().resolve().get();
    if (o instanceof javax.baja.schedule.BCalendarSchedule) return (BComponent)o;
  } catch (Exception e) { log("resolve error: " + e.getMessage()); }
  return null;
}

private void log(String s) {
  try {
    if (getLogToConsole().getStatus().isOk() && getLogToConsole().getValue())
      System.out.println("[iCal_Program] " + s);
  } catch (Exception ignore) {}
}
```

</details>


