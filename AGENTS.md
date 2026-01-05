# AGENTS.md — Vibe Coding Agent (Niagara 4 ProgramObject) Directive

**Version:** 1.0
**Document Purpose:** This document is the **Standard Operating Procedure (SOP)** and technical directive for AI and human developer agents tasked with generating Java code for Niagara 4 `ProgramObject` components within this repository.

Its goal is to ensure that all generated code is **safe, efficient, robust, and compliant** with the Niagara Framework's execution model. This guide defines the non-negotiable rules, canonical patterns, and operational context required for code generation.

---

## 📚 Supporting Documentation

Before generating code, familiarize yourself with the available logic patterns and repository structure.

  * **Legacy Hardware/API:** [`NIAGARA_AX_NOTES.md`](https://www.google.com/search?q=./NIAGARA_AX_NOTES.md)
  * **Deployable Examples:** [`README.md`](https://www.google.com/search?q=./README.md) (Main BOG file index)

> **Note on Repository Structure:**
> The main README has been refactored for brevity. Detailed tutorials and algorithm-specific code examples are located in dedicated sub-guides. These guides serve as the **primary source of truth** for task-specific logic.

- [**Beginner Tutorials**](README_BEGINNER_TUTORIALS.md) — step‑by‑step examples and general algorithm blocks.
- [**GL36 Air Side Trim & Respond**](README_TRIM_RESPOND.md) — variable definitions tutorial, VAV box requests, and trim‑respond resets.
- **GL36 Air Side FDD** — coming soon! TODO.
- [**GL36 Central Plant**](README_GL36.md) — chiller plant enable logic, AHU fault detection, and other GL36‑compliant strategies.
- [**Non‑GL36 & Advanced Logic**](README_NON_GL36.md) — simplified resets and per‑chiller rotator for systems outside Guideline 36.
- [**APIs & Web Requests**](README_APIS.md) — examples for calling weather, holiday and iCalendar APIs or integrating external data science machine learning models running in docker containers.
- [**Optimal Start Algorithms**](README_OPT_START.md) — adaptive-tuning optimal start algorithms based on PNNL research, incorporating both the linear degree-per-minute model and polynomial regression.
- [**Demand‑Side Management**](README_DEMAND_SIDE_MANAGEMENT.md) — OpenADR client and PNNL‑inspired intelligent load shedding.
- [**Astronomical Clock**](README_ASTRONOMICAL_CLOCK.md) — Uses Station time and site coordinates to calculate the sun's Azimuth (compass direction) and Elevation (height in the sky).
- [**Niagara Schedules**](README_SCHEDULING.md) — for Niagara Scheduleing including icalender integeration.
- [**Niagara AX Notes**](NIAGARA_AX_NOTES.md) — notes on creating `ProgramObjects` in legacy Niagara AX (earlier Java-based versions).


---

## 1\. 🎯 Core Mission & Agent Contract

### 1.1. Agent Task (Your Goal)

Given a **slot table** and a **task description**, you will produce **only** the Java method bodies for `onStart()`, `onExecute()`, `onStop()`, and any necessary private helper methods or constants.

### 1.2. Agent Interaction Model (REVISED)
Deliverables You Must Return (The "Response"):

The Consolidated Code Block: You must return exactly one fenced Java code block containing the entire logic.

No Method Headers: Do not include the public void onStart() or public void onExecute() headers. Instead, use comments to separate the sections.

The "One-Shot" Format: The block must be structured as follows:

Stateful field declarations (e.g., Clock.Ticket ticket;).

The body of onStart().

The body of onExecute().

The body of onStop().

The helper methods block.

---

## 2\. ❗ Core Directives & Invariants (Non-Negotiable)

These rules are absolute. Violation can lead to component failure, thread starvation, or JACE instability.

1.  **Generate Method Bodies ONLY**

      * **ALLOWED:** The code *inside* `onStart()`, `onExecute()`, `onStop()`, and private helper methods at the class level (e.g., `private int clamp(...)`). Small `private static final` constants are also permitted.
      * **FORBIDDEN:** You **must not** generate any of the following:
          * `package ...;` or `import ...;` statements.
          * `public class ProgramImpl extends ProgramBase { ... }` (or any class definition).
          * Slot declarations (e.g., `public static final Property in1 = ...`).
          * Auto-generated getter/setter methods (e.g., `public BStatusNumeric getIn1() { ... }`).
          * `public static void main(String[] args)`.
          * Nested classes.
      * **Rationale:** The Niagara Workbench **auto-generates** all this boilerplate code. The human developer only pastes your method bodies into the pre-existing, non-editable `ProgramImpl.java` view. Generating forbidden code will cause a compile failure.

2.  **Slots are the Immutable API**

      * The slot table provided by the human is **canonical**.
      * You **must** use the slot names and types *exactly* as given.
      * **Do not** invent new slots, rename existing slots, or assume a different type.
      * **Rationale:** Slots are the public API of the component, defined visually in Workbench. The generated getter/setter methods (`getIn1()`, `setOut1()`) are based *exactly* on these names. A mismatch will fail to compile.

3.  **No Blocking Operations or Busy Loops**

      * You **must not** use `while(true)`, `Thread.sleep()`, or any other operation that blocks the execution thread.
      * All long-running or periodic tasks **must** use the asynchronous scheduling patterns defined in Section 5.
      * **Rationale:** `ProgramObject` methods execute on a shared, limited thread pool (the "Worker" thread). Blocking this thread will starve all other components, timers, and logic on the JACE, potentially leading to a catastrophic controller-wide freeze.

4.  **Strict Performance & Resource Limits**

      * Aim for `onExecute()` to complete in **\< 10ms**.
      * Avoid repeated large memory allocations (e.g., creating large `byte[]` arrays or `String` buffers inside `onExecute`).
      * If a buffer is needed, declare it as a private instance variable and reuse it.
      * **Rationale:** The JACE is an embedded, resource-constrained device. A single, inefficient component can consume disproportionate CPU and memory, degrading the performance of the entire station.

5.  **Network & Filesystem Policy**

      * Only perform network calls (HTTP/S) to endpoints **explicitly authorized** by the human's task.
      * **Do not** probe, discover, or call any other external service.
      * **Do not** attempt to read from or write to the JACE filesystem unless the task explicitly provides a safe, pre-approved path.
      * **Rationale:** Security and stability. Unauthorized network or file I/O is a significant security risk and can lead to JACE instability (e.g., filling the disk, network saturation).

6.  **Absolute Exception & Safety Discipline**

      * Your code **must never** throw an uncaught exception.
      * All primary logic (especially in `onExecute`) **must** be wrapped in a `try...catch (Exception e)` block.
      * If an error occurs, **log it** (if possible) and **set a status string** (e.g., `getApiResponse()`) with a concise error message.
      * **Rationale:** An uncaught exception in `onStart`, `onExecute`, or `onStop` will place the component into a fault state. This often requires a manual component/station restart to clear.

---

## 3\. ⚙️ Understanding the Niagara Environment

To write effective code, you must understand your execution context.

### 3.1. The `ProgramObject` Sandbox

Your code does not run like a normal Java application. It runs inside a secure sandbox called **`program-rt`**. This sandbox only grants access to a "whitelist" of safe, core Java and Niagara classes.

  * **Available by Default:** `javax.baja.sys.*`, `javax.baja.status.*`, `javax.baja.util.*`, `com.tridium.program.*`, and core `java.util.*` packages.
  * **NOT Available by Default:** Advanced APIs for scheduling, histories, alarms, or networking.

### 3.2. Module Dependencies

To use APIs *outside* the default sandbox, the human must **manually add a module dependency** to the `ProgramObject` in Workbench. Your code can then *assume* those classes are available.

| Purpose | Module Required | Example Classes/Imports |
| :--- | :--- | :--- |
| **Calendars & Schedules** | `schedule-rt` | `javax.baja.schedule.*` |
| **Histories & Trends** | `history-rt` | `javax.baja.history.*` |
| **Alarms** | `alarm-rt` | `javax.baja.alarm.*` |
| **Weather & Web Calls** | `inet-rt` | `javax.baja.inet.HttpURLConnection` |
| **BACnet / Modbus Types** | (Driver Module) | `com.tridium.bacnet.B...` |

**Your responsibility:** If a task requires (e.g.) writing to a calendar, you will write the code assuming `javax.baja.schedule.*` is available. You can and should **add a comment** notifying the human if a non-standard module is required.

### 3.3. The Auto-Generated Code Skeleton

Workbench generates a `ProgramImpl.java` file that looks conceptually like this. Your code only fills the commented sections.

```java
/* Auto-generated ProgramImpl Code */

// 1. Imports are added here (by Workbench, from Imports tab)
import java.util.*;
import javax.baja.sys.*;
import javax.baja.status.*;
import com.tridium.program.*;
import javax.baja.schedule.*; // <-- Manually added by human

public class ProgramImpl extends ProgramBase {

    /* 2. Slot definitions and getters/setters are auto-generated here */
    // ... public BStatusString getCountryCode() { ... }
    // ... public BOrd getCalendarOrd() { ... }

    /* 3. Your code is pasted here by the human */

    public void onStart() throws Exception {
        // AI-GENERATED onStart() BODY GOES HERE
    }

    public void onExecute() throws Exception {
        // AI-GENERATED onExecute() BODY GOES HERE
    }

    public void onStop() throws Exception {
        // AI-GENERATED onStop() BODY GOES HERE
    }

    /* 4. Your helper methods are pasted here */

    // AI-GENERATED HELPER METHODS GO HERE
    // private String normalizeCountry(String s) { ... }
}
```

---

## 4\. ✍️ Code Generation Standards & Patterns

Follow these patterns strictly for safety and consistency.

### 4.1. Reading from Slots (The "Status-Guard" Pattern)

**Never** access a slot's value directly. Always check its status first. Unwired or faulted slots will have a non-OK status (`isBad()`, `isFault()`, `isNull()`).

#### **BStatusNumeric / BStatusBoolean**

```java
// Preferred: Use a safe fallback value
double oatF = getOutsideAirTemp_F().getStatus().isOk()
    ? getOutsideAirTemp_F().getValue()
    : 70.0; // A reasonable default

boolean enabled = getEnable().getStatus().isOk()
    ? getEnable().getValue()
    : false; // Default to a 'safe' state
```

#### **BStatusString**

```java
// Preferred: Use a safe fallback, check for null/empty
String countryCode = "US"; // Default
if (getCountryCode().getStatus().isOk()) {
    String val = getCountryCode().getValue();
    if (val != null && !val.trim().isEmpty()) {
        countryCode = val.trim();
    }
}
// Now 'countryCode' is guaranteed to be a valid, non-null string
```

#### **BOrd (Object Resolution)**

This is a multi-step process:

1.  Check if the `BOrd` slot itself is OK.
2.  Resolve the ORD to a `BComponent`.
3.  Check if the resolved component is non-null.
4.  (Optional but recommended) Check if the component is the *type* you expect.

<!-- end list -->

```java
// Example: Resolving a Calendar target
BCalendarSchedule calendar = null;
if (getCalendarOrd().getStatus().isOk()) {
    try {
        // Try to resolve the ORD string
        BComponent component = (BComponent) getCalendarOrd().resolve(getContext()).get();
        
        // Check if it resolved and is the correct type
        if (component instanceof BCalendarSchedule) {
            calendar = (BCalendarSchedule) component;
        } else {
            // Resolved to something, but it's not a calendar
            getApiResponse().setValue("ERROR: ORD is not a CalendarSchedule");
        }
    } catch (Exception e) {
        // Failed to resolve (e.g., path is bad, component deleted)
        getApiResponse().setValue("ERROR: Cannot resolve calendarOrd: " + e.getMessage());
    }
} else {
    getApiResponse().setValue("ERROR: calendarOrd is unwired or in fault");
}

// *** CRITICAL ***
// If the target is required, stop all further execution
if (calendar == null) {
    return; // Stop processing in onExecute
}

// Now 'calendar' is safe to use
// ...
```

### 4.2. Writing to Slots

  * **Data Slots:** Set the value directly.
    `getOutValue().setValue(123.45);`
  * **Status Slots:** Be concise and informative. This is the primary debugging tool for the human.
      * **Success:** `getApiResponse().setValue("OK");`
      * **Success with data:** `getApiResponse().setValue("OK: 21 holidays imported");`
      * **Failure:** `getApiResponse().setValue("ERROR: HTTP 404 - Not Found");`
      * **Configuration Error:** `getApiResponse().setValue("ERROR: calendarOrd is null");`

### 4.3. State Management

  * **Stateless:** `onExecute()` should be stateless whenever possible. All data should come from input slots and all results written to output slots.
  * **Stateful:** If state *must* be preserved between executions (e.g., a timer ticket, a network client, a running total), use **private instance variables**.
      * **Do not** use `static` variables, as they will be shared by *all* instances of your Program Object on the JACE, leading to unpredictable behavior.

<!-- end list -->

```java
// CORRECT: Instance variable for state
private Clock.Ticket timerTicket;
private int executionCounter = 0;

// INCORRECT: Static variable
// private static Clock.Ticket timerTicket; // DANGEROUS!
```

---

## 5\. ⏱️ Execution & Scheduling Patterns

Choose one of these two patterns. **Never** invent a new one.

### Pattern A: Event-Driven (e.g., `updateNow` Trigger)

Used for one-shot actions triggered by a human or another component.

  * **Required Slots:** `updateNow` (BStatusBoolean, Writable)
  * **Logic:** The work is performed *inside* a `try...catch...finally` block. The `finally` block **guarantees** the `updateNow` trigger is reset to `false`, preventing re-execution loops.

<!-- end list -->

```java
// onStart
{
    // No startup logic needed for this pattern
}

// onExecute
{
    // Only run if the updateNow trigger is true and OK
    if (getUpdateNow().getStatus().isOk() && getUpdateNow().getValue()) {
        try {
            // ***************************
            // *** DO ALL WORK HERE ***
            // e.g., fetchHolidays();
            // ***************************

            getApiResponse().setValue("OK: Update complete");

        } catch (Exception e) {
            // Log and set error status
            log.error("Failed to execute update", e);
            getApiResponse().setValue("ERROR: " + shortMsg(e));

        } finally {
            // *** CRITICAL ***
            // Always reset the trigger to false, even if work failed
            getUpdateNow().setValue(false);
        }
    }
}

// onStop
{
    // No shutdown logic needed
}
```

### Pattern B: Time-Driven (Periodic Background Refresh)

Used for background tasks like polling an API or recalculating a complex value.

  * **Required Slots:** `refreshIntervalSeconds` (BStatusNumeric, Writable, Default e.g., 3600)
  * **State:** Requires a `private Clock.Ticket timerTicket;` instance variable.
  * **Logic:** `onStart` schedules the *first* execution. `onExecute` does the work and then **schedules the next** execution. `onStop` cancels the timer to prevent orphaned threads.

<!-- end list -->

```java
// --- Add to Helpers Block ---
private Clock.Ticket timerTicket;

private void scheduleNextRun() {
    // Always cancel any previous timer
    if (timerTicket != null) {
        timerTicket.cancel();
        timerTicket = null;
    }

    // 1. Get and clamp the interval from the slot
    double seconds = 3600.0; // Default: 1 hour
    if (getRefreshIntervalSeconds().getStatus().isOk()) {
        seconds = getRefreshIntervalSeconds().getValue();
    }
    // Clamp to safe bounds (e.g., 5 min to 1 day)
    seconds = Math.max(300.0, Math.min(86400.0, seconds));
    
    // 2. Schedule the next 'onExecute'
    BRelTime interval = BRelTime.makeSeconds(seconds);
    timerTicket = Clock.schedule(this, interval, BProgram.execute, null);
}
// --- End of Helpers Block ---


// onStart
{
    // Schedule the first run to happen immediately
    Clock.schedule(this, BRelTime.makeSeconds(1), BProgram.execute, null);
}

// onExecute
{
    try {
        // ***************************
        // *** DO ALL WORK HERE ***
        // e.g., fetchApiData();
        // ***************************

        getApiResponse().setValue("OK: Refresh complete");

    } catch (Exception e) {
        log.error("Failed to execute periodic refresh", e);
        getApiResponse().setValue("ERROR: " + shortMsg(e));
    } finally {
        // *** CRITICAL ***
        // Schedule the *next* run, regardless of success or failure
        scheduleNextRun();
    }
}

// onStop
{
    // *** CRITICAL ***
    // Clean up the timer to prevent leaks
    if (timerTicket != null) {
        timerTicket.cancel();
        timerTicket = null;
    }
}
```

---

## 6\. 🛡️ Robust Operations & Guardrails

### 6.1. Input & Parameter Clamping

Always assume user-configurable slots (`refreshIntervalSeconds`, `executePeriodSeconds`) will be set to unsafe values. **Clamp them** to sane defaults.

  * `executePeriodSeconds`: Clamp to `60..3600` (1 min - 1 hr)
  * `refreshIntervalSeconds`: Clamp to `3600..2592000` (1 hr - 30 days)
  * `maxEventsToImport`: Clamp to `1..1000`
  * **Rationale:** Prevents a user from setting a 1-second refresh on a remote API (Denial of Service) or a 1-second execute period (CPU starvation).

### 6.2. Network Operations

  * **Timeouts:** Always set connect and read timeouts.
    `httpConn.setConnectTimeout(5000); // 5 seconds`
    `httpConn.setReadTimeout(10000); // 10 seconds`
  * **Backoff:** On transient failures (HTTP 429, 503, 504), do not retry immediately. Use the periodic scheduling to try again later.
  * **Parsing:** All parsing (JSON, XML, .ics) must be resilient. Assume the data is malformed and wrap it in a `try...catch`.

### 6.3. Exception Handling & Status Reporting

Use this "Golden Pattern" inside `onExecute` for maximum safety.

```java
// onExecute
{
    try {
        // ...
        // All of your logic
        // ...

        // Set success status *at the end*
        getApiResponse().setValue("OK");

    } catch (Exception e) {
        // Log the full stack trace for debugging
        log.error("An error occurred during execution", e);
        
        // Set a concise, helpful error for the user
        getApiResponse().setValue("ERROR: " + shortMsg(e));
    }
}
```

---

## 7\. 📤 Final Output Specification

You **must** return your response as a series of fenced code blocks in this exact order.

```java
// ==========================================
// 1. STATEFUL FIELDS (Class Level)
// ==========================================
private Clock.Ticket ticket;
private long lastStepMillis = 0L;
private boolean wasEnabled = false;

// ==========================================
// 2. onStart() BODY
// ==========================================
// (Logic here - NO headers or extra braces)

// ==========================================
// 3. onExecute() BODY
// ==========================================
// (Logic here - NO headers or extra braces)

// ==========================================
// 4. onStop() BODY
// ==========================================
// (Logic here - NO headers or extra braces)

// ==========================================
// 5. HELPERS
// ==========================
private void updateTimer() { ... }
```

### 4\. Helpers (Optional)

```java
// Helpers
{
    // ... private helper methods and constants ...
    
    private static int clamp(int v, int lo, int hi) {
        return (v < lo) ? lo : (v > hi) ? hi : v;
    }

    private static String shortMsg(Throwable t) {
        if (t == null) return "null";
        String m = t.getMessage();
        return (m == null) ? t.getClass().getSimpleName() : (m.length() > 56 ? m.substring(0, 56)+"..." : m);
    }
}
```

---

## 8\.  Using `fault` as an exception-handling pattern

For algorithm blocks, **status is our exception channel**. Instead of throwing Java exceptions, we surface problems through:

- `BStatus.fault` on key outputs
- A dedicated `faultFlag` boolean
- A human-readable `statusTrace` string

This keeps the ProgramObject stable while still making it obvious something is wrong.

#### Canonical “fault-aware math block” pattern

**Slot expectations**

- `enable` → `BStatusBoolean` (master enable)
- `inValue` → `BStatusNumeric` (input)
- `faultIn` → `BStatusBoolean` (manual fault flag)
- `outValue` → `BStatusNumeric` (result)
- `outFaultFlag` → `BStatusBoolean` (TRUE when in fault)
- `statusTrace` → `BStatusString` (debug text)

**Method bodies**

```java
// ==========================
// Class-level state
// ==========================
Clock.Ticket ticket;
private static final int EXEC_PERIOD_SEC = 5; // run every 5 seconds

// ==========================
// Lifecycle
// ==========================
public void onStart() throws Exception
{
  // Initialize outputs as NULL so downstream logic knows it's not ready yet
  nullOutputs("Fault demo block started.");
  updateTimer();
}

public void onExecute() throws Exception
{
  try
  {
    updateTimer();

    // --- 0. Master enable guard ---
    if (!safeBool(getEnable()))
    {
      nullOutputs("Disabled via 'enable' flag.");
      return;
    }

    // --- 1. Handle unwired numeric input (optional) ---
    ensureNumericWiredOrNull("inValue", getInValue());

    BStatus inStatus    = getInValue().getStatus();
    boolean manualFault = safeBool(getFaultIn());

    // --- 2. If input is NULL, force outputs NULL + raise fault flag ---
    if (inStatus.isNull())
    {
      getOutValue().setValue(0);
      getOutValue().setStatus(BStatus.nullStatus);

      getOutFaultFlag().setValue(true);
      getOutFaultFlag().setStatus(BStatus.ok);

      getStatusTrace().setValue("inValue is NULL (unwired or cleared) → outputs forced NULL, faultFlag=TRUE.");
      return;
    }

    // --- 3. If input itself is not OK, treat that as a fault source ---
    boolean upstreamFault = !inStatus.isOk();

    // --- 4. Normal math: double the value ---
    double inVal = getInValue().getValue();
    double result = inVal * 2.0;

    getOutValue().setValue(result);

    // --- 5. Decide final fault state ---
    boolean effectiveFault = manualFault || upstreamFault;

    if (effectiveFault)
    {
      // Mark the numeric as "fault" so it shows yellow {fault}
      getOutValue().setStatus(BStatus.fault);

      getOutFaultFlag().setValue(true);
      getOutFaultFlag().setStatus(BStatus.ok);

      String reason = manualFault ? "manual faultIn=TRUE" : "upstream input status not OK";
      getStatusTrace().setValue("FAULT: " + reason + " | in=" + inVal + " → out=" + result);
    }
    else
    {
      getOutValue().setStatus(BStatus.ok);

      getOutFaultFlag().setValue(false);
      getOutFaultFlag().setStatus(BStatus.ok);

      getStatusTrace().setValue("OK: inValue=" + inVal + " → outValue=" + result);
    }
  }
  catch (Exception e)
  {
    // AGENTS rule: never let exceptions bubble out of onExecute
    getOutValue().setStatus(BStatus.nullStatus);
    getOutFaultFlag().setStatus(BStatus.nullStatus);
    getStatusTrace().setValue("Error in fault demo block: " + e.toString());
  }
}

public void onStop() throws Exception
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }
  nullOutputs("Fault demo block stopped.");
}

// ==========================
// Helpers
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

/** Treat any non-OK or NULL boolean as false */
private boolean safeBool(BStatusBoolean b)
{
  if (b == null) return false;
  if (!b.getStatus().isOk()) return false;
  return b.getValue();
}

/** If slot is unwired, mark it NULL so downstream logic can see it */
private void ensureNumericWiredOrNull(String slotName, BStatusNumeric point)
{
  try
  {
    if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0)
    {
      point.setValue(0);
      point.setStatus(BStatus.nullStatus);
    }
  }
  catch (Exception e)
  {
    // ignore – safest thing is to leave status as-is
  }
}

/** Convenience: clear outputs + set trace */
private void nullOutputs(String trace)
{
  getOutValue().setValue(0);
  getOutValue().setStatus(BStatus.nullStatus);

  getOutFaultFlag().setValue(false);
  getOutFaultFlag().setStatus(BStatus.nullStatus);

  getStatusTrace().setValue(trace);
}
```