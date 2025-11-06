# AGENTS.md — Vibe Coding Agent Guide (Niagara 4 ProgramObject)

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

### Changelog
- **v0.1 (draft):** Initial agent guide for VIBE Coding Addict repo.
