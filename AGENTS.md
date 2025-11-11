# AGENTS.md — Vibe Coding Agent Guide (Niagara 4 ProgramObject)

This document serves as the **operating manual for developer and AI agents** working within this repository. It defines how Niagara 4 Program Objects, logic agents, and future driver-integrated processes should be structured and extended.

For hardware or legacy API references, see [`NIAGARA_AX_NOTES.md`](./NIAGARA_AX_NOTES.md).
For live algorithm definitions and ready‑to‑deploy `.bog` examples, see [`README.md`](./README.md).

> **Note:** The main README has been reorganized to keep it concise.  Detailed tutorials and code examples have been moved into separate sub‑guides:

- [**Tutorials & Algorithms**](README_TUTORIALS_ALGORITHMS.md) — step‑by‑step examples and general algorithm blocks.
- [**GL36 Air Side Trim & Respond**](README_TRIM_RESPOND.md) — variable definitions tutorial, VAV box requests, and trim‑respond resets.
- [**GL36 Central Plant & AHU FDD**](README_GL36.md) — chiller plant enable logic, AHU fault detection, and other GL36‑compliant strategies.
- [**Non‑GL36 & Advanced Logic**](README_NON_GL36.md) — simplified resets and per‑chiller rotator for systems outside Guideline 36.
- [**APIs & Web Requests**](README_APIS.md) — examples for calling weather, holiday and iCalendar APIs or integrating external ML models.
- [**Optimal Start Algorithms**](README_OPT_START.md) — adaptive-tuning optimal start algorithms based on PNNL research, incorporating both the linear degree-per-minute model and polynomial regression.
- [**Demand‑Side Management**](README_DEMAND_SIDE_MANAGEMENT.md) — OpenADR client and PNNL‑inspired intelligent load shedding.
- [**Niagara AX Notes**](NIAGARA_AX_NOTES.md) — notes on creating `ProgramObjects` in legacy Niagara AX (earlier Java-based versions).


These sub‑guides mirror the original README content exactly, so feel free to consult them when generating code for a specific category.

**Audience:** Coding agents (and power users) that will auto-generate **method bodies** for Niagara 4 `Program` objects inside `ProgramImpl.java`.

**Goal:** Given a slot table and a task, produce **only** the Java bodies for `onStart`, `onExecute`, `onStop`, plus any small helper methods or constants **inside** the class — no headers/imports/getters/setters. The human will paste results into Workbench and compile.

---

## 0) Hard Rules (Non‑Negotiable)

1. **Generate method bodies only:**
   - Allowed: `onStart(...)`, `onExecute(...)`, `onStop(...)`, private helpers inside the class (e.g., `private String normalizeCountry(String s) { ... }`), small `static final` constants.
   - **Forbidden:** package/import lines, class headers, field/slot declarations, getters/setters, `main`, nested classes, project files.

2. **Slot names/types are canonical.**
   - Assume the properties (slots) already exist per the user’s table. **Do not** rename, add, or remove slots.
   - When reading a slot, always check status (OK/GOOD) before using the value. Provide a safe fallback.

3. **No busy loops or blocking waits.**
   - Use Workbench’s scheduler/timer patterns (e.g., `Clock.schedule(...)` or the repo’s standard scheduling helper). Never `while(true)` or sleep loops.

4. **Resource limits (JACE‑safe):**
   - Keep total execution light (aim for < 10 ms per `onExecute`).
   - Avoid repeated allocations; reuse buffers when feasible.
   - Rate‑limit network calls; default refresh windows: 1h+ for external APIs unless the human requests otherwise.

5. **Networking policy:**
   - Only call HTTP(S) endpoints explicitly mentioned by the human (e.g., Nager.Date, NextSpaceflight). No discovery probes. Respect timeouts and backoff.

6. **Error handling & safety:**
   - Never throw uncaught exceptions. Catch/log and set a status string (e.g., `apiResponse`) with concise context (`"OK"`, `"ERROR: message"`).
   - If inputs are NULL/BAD, skip work and set status to a helpful message rather than crashing.

7. **Output structure for the human:**
   - Return three fenced code blocks in this order: `onStart`, `onExecute`, `onStop`. Include any helper methods in a fourth block titled **Helpers**.
   - Keep comments short and focused on what the code is doing in Niagara terms.

---

## 1) Minimal Contract You Must Follow

**Inputs you will receive from the human (or repo examples):**
- A **slot table** describing writable/readonly slots (names & types) that already exist on the Program object.
- A **task** (e.g., “Fetch Nager holidays and populate a Calendar schedule,” or “Parse generic `.ics` and map to Special Events”).

**Outputs you must return:**
- **Only method bodies** for `onStart`, `onExecute`, `onStop` (and optional small helpers).
- If you need constants (e.g., default intervals), declare them `private static final` **inside** the class and keep them tiny.

**Never**: change slot names, introduce new public properties, or emit full classes/imports.

---

## 2) Canonical Slot‑IO Patterns

When reading a slot that may be unwired or NULL, use the **status‑guard** pattern:

```java
// Example for a numeric slot
double oatF = getOutsideAirTemp_F().getStatus().isOk()
    ? getOutsideAirTemp_F().getValue()
    : 70.0; // safe fallback
```

When writing status back to a string/numeric slot, **normalize** values and keep concise:

```java
getApiResponse().setValue("OK"); // or "ERROR: <short reason>"
```

When updating a **Calendar/Special Event** target via an Ord, always:
- Validate the `BOrd` resolves (non‑NULL).
- Handle missing ord gracefully (set status; return).

---

## 3) Scheduling Patterns (Use These, Don’t Invent New)

### A) Execute‑on‑Change (preferred for one‑shot triggers)
- Triggered by a boolean slot like `updateNow`.
- Immediately perform action, then **auto‑reset** the trigger to `false`.

Pseudocode flow for `onExecute`:
1. If `updateNow` is not `true`, `return`.
2. Do work (e.g., fetch holidays).
3. Write concise status and **set `updateNow=false`**.

### B) Timed Refresh (preferred for background)
- Use a writable numeric slot like `refreshIntervalSeconds` (clamp to sane bounds, e.g., 3600..2592000).
- Schedule the next run using the platform clock helper and **no busy loops**.
- Keep network I/O bounded and resilient (timeouts, minimal retries, exponential backoff).

---

## 4) Networking & Parsing Recipes

### A) HTTP GET (Nager.Date, JSON)
- Respect `countryCode` normalization (e.g., `UK→GB`, `USA→US`).
- Build URL: `https://date.nager.at/api/v3/PublicHolidays/{year}/{cc}` (and optionally `{year+1}`).
- Parse JSON safely; empty list is acceptable (set status `"OK: 0 holidays"`).

### B) HTTP GET (Generic `.ics`)
- Download `.ics` text and parse **VEVENT** blocks.
- Extract `DTSTART`, `DTEND`, `SUMMARY` (fallbacks allowed).
- Convert to internal Calendar/Special Event entries.

**Always**: clamp number of imported events (e.g., max 1000 per run) and de‑dup on UID if present.

---

## 5) Guardrails & Clamps (Good Defaults)

- `executePeriodSeconds`: clamp to `60..3600` seconds.
- `refreshIntervalSeconds`: clamp to `3600..2592000` (1h..30d).
- Max events per import: `1000`.
- HTTP timeouts: connect 5s, read 10s.
- Backoff: 2× up to 3 tries on transient failures (HTTP 429/5xx).

---

## 6) Validation & Status Discipline

After every meaningful step, keep `apiResponse` short:
- `"OK"` when successful.
- `"OK: 213 events"` on bulk loads.
- `"ERROR: timeout"` or `"ERROR: bad ord"` (≤ 60 chars).

If a slot is misconfigured (e.g., null `calendarOrd`), **do not** proceed — set `"ERROR: calendar ord null"` and return.

---

## 7) Output Format (What You Must Return)

Return **four** blocks in this order. Only the first three are required; Helpers is optional.

```java
// onStart
{ ...body only... }
```

```java
// onExecute
{ ...body only... }
```

```java
// onStop
{ ...body only... }
```

```java
// Helpers (optional)
{ private String normalizeCountry(String s) { ... } }
```

Keep each block self‑contained and paste‑ready for Workbench’s `ProgramImpl.java`.

---

## 8) Prompt Starters (Agent‑Facing)

**Holiday Fetcher (Nager.Date)**
> Slots: `countryCode` (str, writable), `refreshIntervalSeconds` (num, writable), `updateNow` (bool, writable), `apiResponse` (str), `calendarOrd` (BOrd). Implement: on change of `updateNow`, fetch {thisYear, nextYear}, map to calendar special events via `calendarOrd`, set `apiResponse` with result. Clamp intervals and auto‑reset `updateNow=false`.

**Generic iCal Importer**
> Slots: `icsUrl` (str, writable), `refreshIntervalSeconds` (num, writable), `updateNow` (bool, writable), `calendarOrd` (BOrd), `apiResponse` (str). On `updateNow` or timer, GET `.ics`, parse VEVENTs, import as special events, de‑dup by UID if available, set concise status.

---

## 9) Small Code Patterns You Can Reuse

**Clamp helper (inline allowed in Helpers block):**
```java
private static int clamp(int v, int lo, int hi) {
    return (v < lo) ? lo : (v > hi) ? hi : v;
}
```

**Auto‑reset toggle after work:**
```java
if (getUpdateNow().getValue()) {
    try {
        // ...do work...
        getApiResponse().setValue("OK");
    } catch (Exception ex) {
        getApiResponse().setValue("ERROR: " + shortMsg(ex));
    } finally {
        getUpdateNow().setValue(false);
    }
}
```

**Short exception message:**
```java
private static String shortMsg(Throwable t) {
    String m = t.getMessage();
    return (m == null) ? t.getClass().getSimpleName() : (m.length() > 56 ? m.substring(0, 56) : m);
}
```

---

## 10) Review Checklist (Run Before Returning Code)

- [ ] No imports or class headers included
- [ ] Only method bodies + optional tiny helpers
- [ ] Slots referenced exactly as provided (names/types)
- [ ] Status‑guards on every external read
- [ ] No busy loops; only timer/trigger patterns
- [ ] Intervals clamped; network timeouts set
- [ ] `apiResponse` set to short, meaningful string
- [ ] `updateNow` auto‑resets to false if used
- [ ] Event counts/limits respected
- [ ] Methods paste‑ready into `ProgramImpl.java`

---

<details>
<summary>🧠 LLM Model Context Full</summary>

AI/LLM's section to read...not required by the human. This section provides a guide for interacting with AI and LLMs (like ChatGPT) to generate **Niagara 4 Program Object** Java code *safely and correctly*.

Niagara Workbench **auto-generates** important pieces of the Program Object code — do not generate or modify them manually.

Default imports are automatic, special packages for networking, I/O, or advanced scheduling (like java.net, java.io, java.time, or javax.baja.schedule) MUST be added manually to the Program Object's Imports tab. Snips are available to the human for reference this.

---

### **Key Rules for LLM and Human Collaboration**

#### **❌ Do Not Generate or Modify These**

> **LLMs must NOT generate:**
> * Do not insert emoji into code as it will error out the compiling process.
> * Class header and imports.
> * `public class ProgramImpl extends ProgramBase`.
> * Auto-generated slot getter and setter methods.
> * `/* Auto-generated ProgramImpl Code */` sections.

These are **automatically handled** by **Niagara Workbench** — no need to manually import or build the class boilerplate!

**Workbench generates this structure for you**:

```java
/* Auto-generated ProgramImpl Code */

import java.util.*;
import javax.baja.sys.*;
import javax.baja.status.*;
import com.tridium.program.*;

public class ProgramImpl extends ProgramBase {
  
  public void onStart() throws Exception {
    // startup code
  }

  public void onExecute() throws Exception {
    // execute code
  }

  public void onStop() throws Exception {
    // shutdown code
  }
}
```

On the Program Object’s Source tab (the auto-generated code base), the import statements—if configured correctly—should look similar to the example below. You can ask the human to show you the auto-generated source code (which cannot be modified) to verify that any required external packages or modules have been properly included.
```java
/* Auto-generated ProgramImpl Code */

import java.util.*;              /* java Predefined*/
import javax.baja.nre.util.*;    /* nre Predefined*/
import javax.baja.sys.*;         /* baja Predefined*/
import javax.baja.status.*;      /* baja Predefined*/
import javax.baja.util.*;        /* baja Predefined*/
import com.tridium.program.*;    /* program-rt Predefined*/
import javax.baja.schedule.*;    /* schedule-rt User Defined*/
import javax.baja.naming.*;      /* baja By Property*/

public class ProgramImpl
  extends com.tridium.program.ProgramBase
{
```

These are the methods that the human can modify only through AI-generated code. Adding packages and modules is done separately on the Imports tab of the Program Object, not programmatically within the source code.

```java
public void onStart() throws Exception
{
  // start up code here
}

public void onExecute() throws Exception
{
  // execute code (set executeOnChange flag on inputs)
}

public void onStop() throws Exception
{
  // shutdown code here
}

```

### When Additional Niagara Modules Are Needed in Program Objects

A **Program Object** runs in Niagara’s sandbox (“program-rt”), which only exposes safe core APIs (`javax.baja.sys`, `javax.baja.status`, `javax.baja.util`, etc.).
You must **add or require extra modules** when you reference classes outside this default set.

#### When a plain Program Object is enough

* You only use built-in Baja types (e.g., `BStatusNumeric`, `BDateTime`, `BBoolean`).
* You only call Java core packages like `java.net.*` or `java.util.*`.
* You work with Niagara components already on the station (e.g., schedules, points).
* You’re fine with limited privileges (no file I/O, threads, or external JARs).

#### When to add a module dependency

* You use types from another module (e.g., `javax.baja.schedule.*` → **schedule-rt**).
* You call APIs that aren’t whitelisted in program-rt.
* You want palette components, background threads, or long-running tasks.
* You depend on 3rd-party libraries (JSON, iCal, OAuth, MQTT, etc.).
* You need higher permissions, signed code, or access to histories/alarms.

#### Common module examples

| Purpose                        | Module Required                 |
| ------------------------------ | ------------------------------- |
| Calendar & schedules           | `schedule-rt`                   |
| Histories & trends             | `history-rt`                    |
| Alarms                         | `alarm-rt`                      |
| Weather & web calls            | `inet-rt`                       |
| BACnet / Modbus types          | Corresponding driver module     |
| JSON / XML parsing beyond core | Custom module with embedded JAR |

#### Rule of thumb

* **Small glue logic + existing modules → Program Object**
* **Anything needing new APIs, libraries, or long-lived behavior → Custom Module**

---

### **✅ What You *Can* Ask LLMs to Generate**

> **Only generate code inside:**
>
> * `onStart()`
> * `onExecute()`
> * `onStop()`
> * Small helper methods (at the class level)

**⚠️ Reminder:**

* Java does **NOT** allow nested methods.
* **Helper functions (like `addIfWired()`) must be at class level**, not inside `onExecute()`.

**Example of what NOT to do** — ❌ **Incorrect**

```java
public void onExecute() throws Exception {
  // this is invalid: 
  double addIfWired(BStatusNumeric input) { 
    ...
  }
}
```

**Correct** — ✅ **Move helper outside**

```java
// Class-level helper
int addIfWired(BStatusNumeric input) {
  if (input.getStatus().isOk()) {
    sum += input.getValue();
    return 1;
  }
  return 0;
}
```

---

### **Internal Timers in Niagara Program Objects**

> **Use Clock.schedule() with a BRelTime object inside a helper method.**

**Example (Correct Timer Logic):**

```java
Clock.Ticket ticket;

void updateTimer() {            
  if (ticket != null) {
    ticket.cancel();
  }  
  // Hardcoded 10-second update interval
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}
```

🚫 **Do NOT** expose a writable `executePeriod` slot unless truly necessary —
Just schedule internal periodic execution using `Clock.schedule()` directly!

---

### **Common Mistakes to Avoid**

| Mistake                              | Correction                                                                 |
| ------------------------------------ | -------------------------------------------------------------------------- |
| Generating class headers/imports     | ❌ Leave this to Workbench.                                                 |
| Writing slot getters/setters         | ❌ Workbench auto-generates them based on slot definitions.                 |
| Nesting helper methods               | ❌ Java doesn't allow methods inside methods — move helpers to class level. |
| Generating update intervals as slots | ❌ Hardcode your `BRelTime` interval unless you need configurable timing.   |

---

### **When Humans Provide Slot Names**

If the human provides slot names:

* Use them exactly.
* Access them via `getSlotName()`, e.g., `getIn1().getValue()`.

If no names are provided:

* LLM should propose **reasonable slot names** and show a table.

---

### **Example Slot Table if No Names Provided**

| Slot Name      | Type           | Writable | Description           |
| -------------- | -------------- | -------- | --------------------- |
| `in1`          | BStatusNumeric | Yes      | First numeric input   |
| `in2`          | BStatusNumeric | Yes      | Second numeric input  |
| `outAvg`       | BStatusNumeric | No       | Average value output  |
| `wiredInCount` | BStatusString  | No       | Count of wired inputs |

---

### **How to Work With LLMs**

1. Only paste **method bodies** (`onStart`, `onExecute`, `onStop`) into Workbench.
2. **Compile** the Program Object.
3. **If errors occur:**

   * Screenshot the **error** and **slot sheet**.
   * Share it back with the LLM for correction.

⚡ **Quick Debug Tip:**
Most compile errors come from:

* Slot names mismatching.
* Wrong assumptions about slot types or missing getter methods.

---

### **Good Example Output (Correct)**

```java
public void onStart() throws Exception {
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();
    
    sum = 0;
    int wiredCount = 0;

    wiredCount += addIfWired(getIn1());
    wiredCount += addIfWired(getIn2());
    
    getOut().setValue(sum);
    getWiredInCount().setValue("Wired Inputs: " + wiredCount);
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

// ✅ Class-level helper function
int addIfWired(BStatusNumeric input) {
    if (input.getStatus().isOk()) {
        sum += input.getValue();
        return 1;
    }
    return 0;
}
```

---

### **Summary**

> **LLMs:**
>
> * ✅ Only generate *method* code (no imports/class headers).
> * ✅ Keep helper functions *outside* methods.
> * ✅ Use internal `Clock.schedule()` hardcoded intervals unless told otherwise.
>
> **Humans:**
>
> * ✅ Use Workbench to compile.
> * ✅ Screenshot and debug slot sheet + errors if issues arise.

</details>

### Changelog
- **v0.1 (draft):** Initial agent guide for VIBE Coding Addict repo.
