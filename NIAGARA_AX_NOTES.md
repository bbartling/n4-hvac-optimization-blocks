# Niagara AX vs N4 Program Objects: Technical Comparison

This document compares **Niagara AX** and **Niagara 4 (N4)** `Program` objects from a practical development and commissioning perspective. It focuses on core differences for developers, integrators, and control engineers.

---

## 🔄 High-Level Comparison

| Feature / Behavior              | **Niagara AX (Java 1.4/1.5)**        | **Niagara 4 (Java 1.8+)**                      |
|--------------------------------|--------------------------------------|------------------------------------------------|
| Java Platform                  | Java 1.4 / 1.5                       | Java 1.8+ (e.g., N4.10+)                        |
| API / SDK                      | `com.tridium.sys.*`                 | `javax.baja.*` (BAJA 4)                         |
| Code Structure                 | Manual boilerplate                  | Auto-generated slot accessors, cleaner methods |
| Component Meta Model           | Static slot definitions             | Dynamic slot annotations, facets               |
| Memory / GC                    | Manual, tighter constraints         | More modern memory handling                    |
| Timer Logic                    | `Clock.schedule()` only             | `Clock.schedule()` + `executeOnChange`         |
| Development Workflow           | Slow compile, minimal feedback      | Syntax highlighting, better compile-time checks|
| Program Editor                 | Plain editor                        | Enhanced UI with debug, history, linting       |
| Debugging                      | Console/manual                      | Application Director, live logs                |
| Security Model                 | Basic certificate trust             | Signed modules, sandboxing                     |
| Serialization / Backup         | Simpler .bog                        | Robust JSON + metadata handling                |

---

## 🧠 Program Object Differences

### 1. Slot Access
- **AX:**
  ```java
  getIn1().getValue();
  getComponent().getLinks(getComponent().getSlot("in1"));
  ```
- **N4:**
  - Same access pattern, but supports helper annotations and improved validation.

---

### 2. Timer Logic
- **AX:**
  ```java
  Clock.schedule(getComponent(), BRelTime.makeSeconds(5), BProgram.execute, null);
  ```
- **N4:**
  - Same, but adds `executeOnChange` flag on slots for event-driven logic.

---

### 3. Deployment
- **AX:** Requires copying `.bog` files or direct in-station programming.
- **N4:** Supports module packaging, Git versioning, and Workbench-friendly imports.

---

### 4. Language Features
- **AX:** Java 1.4 → no generics, no lambdas, no streams.
- **N4:** Java 8 → modern syntax, `List<>`, lambdas, `Optional`, `Streams`.

---

### 5. Memory and Performance
- **AX:** Lower memory footprint but less resilient.
- **N4:** Larger but more fault-tolerant and optimized GC.

---

### 6. Debugging and Logs
- **AX:** Requires `System.out.println()` or viewing logs manually.
- **N4:** Has `Application Director` with structured logs, error traces, timestamps.

---

### 7. Security
- **AX:** Runs everything as trusted. Little to no sandboxing.
- **N4:** Modules must be signed. App sandboxing improves protection.

---

## ✅ Example Null Check in Both Platforms

```java
if (getComponent().getLinks(getComponent().getSlot("in1")).length == 0) {
    getIn1().setValue(0);
    getIn1().setStatus(BStatus.NULL);
}
```
> ✅ This works in both AX and N4, but in N4 you can wrap this as a helper for reuse.

---

## 🚀 Upgrade Summary
If you're upgrading from AX to N4:
- Your Program logic will mostly **port 1:1**
- Expect faster debugging, better code clarity, and safer deployment
- You can clean up your logic using Java 8 features and smarter timers

---

## Want More?
Ask for side-by-side examples (e.g., chiller staging, rolling averages) to compare AX vs N4 best practices.


## Adder tester

```java
Clock.Ticket ticket;

public void onStart() throws Exception {
    // Schedule the logic to run every 5 seconds
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(5), BProgram.execute, null);
}

public void onExecute() throws Exception {
    double sum = 0;
    int count = 0;

    // Handle in1
    if (getComponent().getLinks(getComponent().getSlot("in1")).length == 0) {
        getIn1().setValue(0);
        getIn1().setStatus(BStatus.NULL);
    } else if (getIn1().getStatus().isOk()) {
        sum += getIn1().getValue();
        count++;
    }

    // Handle in2
    if (getComponent().getLinks(getComponent().getSlot("in2")).length == 0) {
        getIn2().setValue(0);
        getIn2().setStatus(BStatus.NULL);
    } else if (getIn2().getStatus().isOk()) {
        sum += getIn2().getValue();
        count++;
    }

    // Output result
    getOut().setValue(sum);
    getWiredCount().setValue("Wired Inputs: " + count);
}

public void onStop() throws Exception {
    // Cancel the timer when the program stops
    if (ticket != null) {
        ticket.cancel();
    }
}

```

## Niagara AX Version of the Opt Start


### Inputs (read-only to the algorithm)

| Slot name                | Type                                 | Meaning                                            | Used in                                        |
| ------------------------ | ------------------------------------ | -------------------------------------------------- | ---------------------------------------------- |
| `ZoneTemp`               | `BStatusNumeric`                     | Current zone/space temperature                     | validateSensors, idle estimate, run stop check |
| `TargetZoneTempSetpoint` | `BStatusNumeric`                     | Target setpoint the zone should reach by occupancy | idle estimate, run stop check                  |
| `ScheduleNextValue`      | `BStatusBoolean`                     | Next scheduled occupancy value (true = occupied)   | start trigger                                  |
| `ScheduleNextEventTime`  | `BStatusNumeric` (or time-as-number) | Epoch ms timestamp for next schedule transition    | start trigger                                  |
| `ClearHistoryNow`        | `BStatusBoolean`                     | Manual one-shot reset of learned rates             | onExecute                                      |

> Note: In your reference code you check `getScheduleNextEventTime().getStatus().isNull()` — so this needs to be a slot that can go NULL and carries a numeric “ms since epoch” value.

---

### Tunables (user-configurable parameters)

| Slot name             | Type             | Default | Meaning                                            |
| --------------------- | ---------------- | ------: | -------------------------------------------------- |
| `MaxMinutesAllowed`   | `BStatusNumeric` | `180.0` | Hard ceiling for any optimal start run             |
| `TempTolerance`       | `BStatusNumeric` |   `0.5` | “At setpoint” when `abs(zone-target) <= tolerance` |
| `HistoryDaysToRetain` | `BStatusNumeric` |  `10.0` | EMA memory window; `alpha = 1/days`                |

---

### Learned Memory (persistent across runs)

| Slot name              | Type             | Default | Meaning                                            |
| ---------------------- | ---------------- | ------: | -------------------------------------------------- |
| `DegreesPerMinuteHeat` | `BStatusNumeric` |   `0.1` | Learned warm-up rate (deg/min) used when heating   |
| `DegreesPerMinuteCool` | `BStatusNumeric` |   `0.1` | Learned cool-down rate (deg/min) used when cooling |

These are the “EMA memory” slots. Clearing history sets both back to `DEFAULT_RATE`.

---

### Outputs / Status (what operators will look at)

| Slot name               | Type             | Meaning                                                                    |
| ----------------------- | ---------------- | -------------------------------------------------------------------------- |
| `EquipmentStartCommand` | `BStatusBoolean` | Command output: **true/ok** while running; **false/null** when not running |
| `MinutesToSetpoint`     | `BStatusNumeric` | Predicted minutes needed right now (idle estimate)                         |
| `WarmupTimeMinutes`     | `BStatusNumeric` | Elapsed minutes since this run started (while running)                     |
| `IsRunning`             | `BStatusBoolean` | Latched “algorithm currently running” indicator                            |
| `StatusLog`             | `BStatusString`  | Most recent status message                                                 |

---

## Slot naming notes (important for avoiding AX pain)

* Keep names exactly aligned with your `getX()` / `setX()` accessors (Workbench auto-generates those).
* Prefer **BStatusNumeric** for numeric inputs/params so you can safely `isNull()` + `getValue()`.
* For schedule time, store **epoch milliseconds** (long) in a numeric slot (double-backed is fine as long as you cast to long).

---

### Java Code Base

```java

/*
 * OPTIMAL START ALGORITHM (EMA / BALLISTIC)
 * - EMA learns deg/min in DegreesPerMinuteHeat/Cool slots
 * - Ballistic: once started, ignore schedule changes
 * - Stop only when setpoint met OR max minutes exceeded
 */

// =================================================================
// 1. STATEFUL FIELDS
// =================================================================

private Clock.Ticket ticket;
private boolean isOptimalStartRunning = false;
private long runStartTimestamp = 0L;

private double latchedStartZoneTemp = 0.0;
private double latchedStartTarget = 0.0;
private double latchedDeltaT = 0.0;
private double latchedPredictedMins = 0.0;
private boolean lastRunWasHeat = true;

private static final double DEFAULT_RATE = 0.1;

// =================================================================
// 2. onStart()
// =================================================================
public void onStart() throws Exception {
  isOptimalStartRunning = false;
  runStartTimestamp = 0L;

  if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
  if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
  if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));

  forceCommandNull();
  setMinutesToSetpoint(new BStatusNumeric(0.0));

  if (getDegreesPerMinuteHeat().getValue() <= 0.001) setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));
  if (getDegreesPerMinuteCool().getValue() <= 0.001) setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));

  log("Initialized. Waiting for schedule.");
  updateTimer();
}

// =================================================================
// 3. onExecute()
// =================================================================
public void onExecute() throws Exception {
  try {
    updateTimer();

    // --- Clear History Trigger ---
    if (getClearHistoryNow().getValue()) {
      setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));
      setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));
      setClearHistoryNow(new BStatusBoolean(false));
      log("History Reset. Rates set to " + DEFAULT_RATE);
    }

    if (!validateSensors()) {
      if (isOptimalStartRunning) abortRun("Sensor Failure.");
      setMinutesToSetpoint(new BStatusNumeric(0.0));
      return;
    }

    if (isOptimalStartRunning) {
      // Ballistic run: ignore schedule changes here
      monitorActiveRun();
      getEquipmentStartCommand().setValue(true);
      getEquipmentStartCommand().setStatus(BStatus.ok);
    } else {
      updateIdleEstimate();
      checkForStartTrigger();
    }

  } catch (Exception e) {
    log("Error: " + e.toString());
    isOptimalStartRunning = false;
    forceCommandNull();
  }
}

// =================================================================
// 4. CORE LOGIC
// =================================================================

private void checkForStartTrigger() {
  if (getScheduleNextEventTime().getStatus().isNull() || getScheduleNextValue().getStatus().isNull()) return;
  if (!getScheduleNextValue().getValue()) return;

  long nextTime = (long) getScheduleNextEventTime().getValue();
  double minsUntil = (nextTime - System.currentTimeMillis()) / 60000.0;

  if (minsUntil < 0 || minsUntil > 1440) return;

  double neededMins = Math.min(getMinutesToSetpoint().getValue(), getMaxMinutesAllowed().getValue());

  if (neededMins >= minsUntil) {
    startOptimalStartSequence();
  }
}

private void startOptimalStartSequence() {
  double z = getZoneTemp().getValue();
  double t = getTargetZoneTempSetpoint().getValue();

  if (Math.abs(z - t) <= getTempTolerance().getValue()) return;

  runStartTimestamp = System.currentTimeMillis();
  latchedStartZoneTemp = z;
  latchedStartTarget = t;
  latchedDeltaT = Math.abs(z - t);
  latchedPredictedMins = getMinutesToSetpoint().getValue();
  lastRunWasHeat = (z < t);

  isOptimalStartRunning = true;
  setIsRunning(new BStatusBoolean(true));

  // Avoid String.format in AX if it’s picky; simple concat is safest
  log("STARTED [" + (lastRunWasHeat ? "HEAT" : "COOL") + "]: StartT=" + round1(latchedStartZoneTemp) +
      " | Pred=" + round1(latchedPredictedMins) + "m | DeltaT=" + round1(latchedDeltaT));
}

private void monitorActiveRun() {
  double elapsed = (System.currentTimeMillis() - runStartTimestamp) / 60000.0;
  setWarmupTimeMinutes(new BStatusNumeric(elapsed));

  if (Math.abs(getZoneTemp().getValue() - latchedStartTarget) <= getTempTolerance().getValue()) {
    completeRun(elapsed, true);
  } else if (elapsed >= getMaxMinutesAllowed().getValue()) {
    completeRun(elapsed, false);
  }
}

private void completeRun(double actualMins, boolean success) {
  isOptimalStartRunning = false;
  forceCommandNull();
  setIsRunning(new BStatusBoolean(false));

  log("ENDED [" + (lastRunWasHeat ? "HEAT" : "COOL") + "]: " + (success ? "Success" : "Timeout") +
      " | Act=" + round1(actualMins) + "m | Pred=" + round1(latchedPredictedMins) + "m | StartT=" + round1(latchedStartZoneTemp));

  // Tune only if meaningful run
  if (actualMins > 10.0 && latchedDeltaT > 1.0) {
    double currentRunRate = latchedDeltaT / actualMins;

    BStatusNumeric rateSlot = lastRunWasHeat ? getDegreesPerMinuteHeat() : getDegreesPerMinuteCool();
    double oldRate = (rateSlot.getValue() <= 0.001) ? currentRunRate : rateSlot.getValue();

    double days = Math.max(1.0, Math.min(100.0, getHistoryDaysToRetain().getValue()));
    double alpha = 1.0 / days;

    rateSlot.setValue(oldRate + alpha * (currentRunRate - oldRate));
  }
}

private void updateIdleEstimate() {
  double delta = Math.abs(getZoneTemp().getValue() - getTargetZoneTempSetpoint().getValue());
  if (delta <= getTempTolerance().getValue()) {
    setMinutesToSetpoint(new BStatusNumeric(0.0));
    return;
  }

  double rate = (getZoneTemp().getValue() < getTargetZoneTempSetpoint().getValue())
      ? getDegreesPerMinuteHeat().getValue()
      : getDegreesPerMinuteCool().getValue();

  double mins = delta / Math.max(0.01, rate);
  setMinutesToSetpoint(new BStatusNumeric(Math.min(mins, getMaxMinutesAllowed().getValue())));
}

// =================================================================
// 5. HELPERS
// =================================================================

public void onStop() throws Exception {
  if (ticket != null) ticket.cancel();
  isOptimalStartRunning = false;
  forceCommandNull();
}

private void updateTimer() {
  if (ticket != null) ticket.cancel();
  // Clock.schedule is the standard heartbeat pattern in AX :contentReference[oaicite:1]{index=1}
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private void forceCommandNull() {
  getEquipmentStartCommand().setValue(false);
  getEquipmentStartCommand().setStatus(BStatus.nullStatus); // if this fails, swap to BStatus.NULL
}

private boolean validateSensors() {
  return getZoneTemp().getStatus().isOk() && getTargetZoneTempSetpoint().getStatus().isOk();
}

private void abortRun(String reason) {
  isOptimalStartRunning = false;
  forceCommandNull();
  log("ABORTED: " + reason);
}

private void log(String msg) {
  getStatusLog().setValue(msg);
}

private double round1(double v) {
  return Math.round(v * 10.0) / 10.0;
}

```