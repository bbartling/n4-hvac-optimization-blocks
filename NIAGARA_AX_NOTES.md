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
 * OPTIMAL START ALGORITHM EMA — NIAGARA AX (MATCHES YOUR AUTO-GENERATED SLOTS)
 * --------------------------------------------------------------------------
 * Ballistic learning run:
 *  - Latch ΔT at start (start temp vs target).
 *  - Track elapsed time from runStartTimestamp.
 *  - Stop ONLY when setpoint reached (within tolerance) OR maxMinutesAllowed timeout.
 *  - Schedule changes must NOT change timing or ΔT calculations.
 *
 * Output handoff:
 *  - equipmentStartCommand ONLY:
 *      a) TRUE + OK status  (assert start)
 *      b) NULL status       (released to BAS)
 *  - NEVER publish FALSE with OK status.
 *
 * Handoff behavior:
 *  - When scheduleNextValue flips to FALSE during a run,
 *    arm delayed release-to-NULL using commandOffDelaySeconds.
 *  - Learning continues even if command is released to NULL.
 *
 * Notes:
 *  - EMA learning guard:
 *      - Only update if run lasted >= 5 minutes
 *      - And latchedDeltaT > tempTolerance
 */

// =============================================================
// 1) STATEFUL FIELDS (AX OK)
// =============================================================
private Clock.Ticket ticket;

// Ballistic run state
private boolean isOptimalStartRunning = false;
private long runStartTimestamp = 0L;

// Latched learning values
private double latchedStartZoneTemp = 0.0;
private double latchedStartTarget = 0.0;
private double latchedDeltaT = 0.0;
private double latchedPredictedMins = 0.0;
private boolean lastRunWasHeat = true;

// Output handoff state (separate from learning)
private boolean pendingNullRelease = false;
private long nullReleaseAtMillis = 0L;
private boolean hasReleasedToNullThisRun = false;

private static final double DEFAULT_RATE = 0.10; // deg/min fallback

// =============================================================
// 2) onStart()
// =============================================================
public void onStart() throws Exception
{
  isOptimalStartRunning = false;
  runStartTimestamp = 0L;

  pendingNullRelease = false;
  nullReleaseAtMillis = 0L;
  hasReleasedToNullThisRun = false;

  // Defaults if NULL
  if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
  if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
  if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));

  // Your station has emaWeightingFactor slot; default it if NULL.
  // If you want days-based alpha instead, leave this unused.
  if (getEmaWeightingFactor().isNull()) setEmaWeightingFactor(new BStatusNumeric(0.10));

  // commandOffDelaySeconds slot exists; default if NULL
  if (getCommandOffDelaySeconds().isNull()) setCommandOffDelaySeconds(new BStatusNumeric(30.0));

  // Initialize learned rates if invalid
  if (getDegreesPerMinuteHeat().getStatus().isNull() || getDegreesPerMinuteHeat().getValue() <= 0.001)
    setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));

  if (getDegreesPerMinuteCool().getStatus().isNull() || getDegreesPerMinuteCool().getValue() <= 0.001)
    setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));

  // Reset indicators
  setMinutesToSetpoint(new BStatusNumeric(0.0));
  setWarmupTimeMinutes(new BStatusNumeric(0.0));
  setIsRunning(new BStatusBoolean(false));
  setZoneAtTempTolerance(new BStatusBoolean(false));
  setCountdownToNullStatus(new BStatusBoolean(false));

  // Release output on startup
  releaseEquipmentCommandToNull();

  log("Initialized. Waiting for schedule.");
  updateTimer();
}

// =============================================================
// 3) onExecute()
// =============================================================
public void onExecute() throws Exception
{
  try
  {
    updateTimer();

    // Clear History Trigger
    if (getClearHistoryNow().getStatus().isOk() && getClearHistoryNow().getValue())
    {
      setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));
      setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));
      setClearHistoryNow(new BStatusBoolean(false));
      log("History Reset. Rates set to " + DEFAULT_RATE);
    }

    // Validate required sensors
    if (!validateSensors())
    {
      if (isOptimalStartRunning) abortRun("Sensor Failure.");
      setMinutesToSetpoint(new BStatusNumeric(0.0));
      releaseEquipmentCommandToNull();
      return;
    }

    // Keep this updated
    updateZoneAtToleranceFlag();

    // ------------------------------
    // BALLISTIC RUN (learning)
    // ------------------------------
    if (isOptimalStartRunning)
    {
      monitorActiveRun();      // may call completeRun()
    }
    else
    {
      updateIdleEstimate();    // predicts minutesToSetpoint
      checkForStartTrigger();  // may call startOptimalStartSequence()
    }

    // ------------------------------
    // OUTPUT HANDOFF (separate)
    // ------------------------------
    handleEquipmentCommand();
  }
  catch (Exception e)
  {
    log("Error: " + e.toString());
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));
    releaseEquipmentCommandToNull();
  }
}

// =============================================================
// 4) START TRIGGER
// =============================================================
private void checkForStartTrigger()
{
  if (getScheduleNextEventTime().getStatus().isNull()) return;
  if (getScheduleNextValue().getStatus().isNull()) return;

  // Only consider if next schedule value is TRUE (occupied upcoming)
  if (!getScheduleNextValue().getValue()) return;

  long nextTime = (long) getScheduleNextEventTime().getValue();
  double minsUntil = (nextTime - System.currentTimeMillis()) / 60000.0;

  if (minsUntil < 0.0) return;
  if (minsUntil > 1440.0) return;

  double predicted = getMinutesToSetpoint().getValue();
  double maxMins = getMaxMinutesAllowed().getValue();
  double neededMins = Math.min(predicted, maxMins);

  if (neededMins >= minsUntil)
    startOptimalStartSequence();
}

private void startOptimalStartSequence()
{
  double z = getZoneTemp().getValue();
  double t = getTargetZoneTempSetpoint().getValue();

  // If already at target within tolerance, do nothing
  if (Math.abs(z - t) <= getTempTolerance().getValue()) return;

  // Latch learning values
  runStartTimestamp = System.currentTimeMillis();
  latchedStartZoneTemp = z;
  latchedStartTarget = t;
  latchedDeltaT = Math.abs(z - t);
  latchedPredictedMins = getMinutesToSetpoint().getValue();
  lastRunWasHeat = (z < t);

  // Persist some start values to slots you already have (nice for trending)
  setZoneTempAtStart(new BStatusNumeric(latchedStartZoneTemp));
  if (getOutdoorAirTemp().getStatus().isOk())
    setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));

  // Reset handoff state
  pendingNullRelease = false;
  nullReleaseAtMillis = 0L;
  hasReleasedToNullThisRun = false;
  setCountdownToNullStatus(new BStatusBoolean(false));

  isOptimalStartRunning = true;
  setIsRunning(new BStatusBoolean(true));

  log("STARTED [" + (lastRunWasHeat ? "HEAT" : "COOL") + "]: StartT=" + round1(latchedStartZoneTemp) +
      " | Target=" + round1(latchedStartTarget) +
      " | Pred=" + round1(latchedPredictedMins) + "m" +
      " | DeltaT=" + round1(latchedDeltaT));
}

// =============================================================
// 5) ACTIVE RUN MONITORING (BALLISTIC)
// =============================================================
private void monitorActiveRun()
{
  double elapsedMins = (System.currentTimeMillis() - runStartTimestamp) / 60000.0;
  setWarmupTimeMinutes(new BStatusNumeric(elapsedMins));

  // Success uses latched target
  if (Math.abs(getZoneTemp().getValue() - latchedStartTarget) <= getTempTolerance().getValue())
  {
    completeRun(elapsedMins, true);
    return;
  }

  // Timeout
  if (elapsedMins >= getMaxMinutesAllowed().getValue())
  {
    completeRun(elapsedMins, false);
    return;
  }
}

private void completeRun(double actualMins, boolean success)
{
  isOptimalStartRunning = false;
  setIsRunning(new BStatusBoolean(false));

  log("ENDED [" + (lastRunWasHeat ? "HEAT" : "COOL") + "]: " + (success ? "Success" : "Timeout") +
      " | Act=" + round1(actualMins) + "m" +
      " | Pred=" + round1(latchedPredictedMins) + "m" +
      " | StartT=" + round1(latchedStartZoneTemp) +
      " | Target=" + round1(latchedStartTarget));

  // EMA update (guardrails)
  if (actualMins >= 5.0 && latchedDeltaT > getTempTolerance().getValue())
  {
    double currentRunRate = latchedDeltaT / actualMins;

    BStatusNumeric rateSlot = lastRunWasHeat ? getDegreesPerMinuteHeat() : getDegreesPerMinuteCool();
    double oldRate = (rateSlot.getStatus().isNull() || rateSlot.getValue() <= 0.001)
        ? currentRunRate
        : rateSlot.getValue();

    // You have emaWeightingFactor slot. Use it if sane, otherwise fallback to days-based alpha.
    double alpha = 0.0;
    if (getEmaWeightingFactor().getStatus().isOk())
      alpha = getEmaWeightingFactor().getValue();

    // Clamp alpha
    if (alpha <= 0.0 || alpha > 1.0)
    {
      // Fallback alpha = 1/days
      double days = getHistoryDaysToRetain().getValue();
      days = Math.max(1.0, Math.min(100.0, days));
      alpha = 1.0 / days;
    }

    double newRate = oldRate + alpha * (currentRunRate - oldRate);
    rateSlot.setValue(newRate);

    log("LEARN [" + (lastRunWasHeat ? "HEAT" : "COOL") + "]: old=" + round3(oldRate) +
        " | run=" + round3(currentRunRate) + " | new=" + round3(newRate) + " | a=" + round3(alpha));
  }

  // End-of-run: release immediately
  pendingNullRelease = false;
  hasReleasedToNullThisRun = true;
  setCountdownToNullStatus(new BStatusBoolean(false));
  releaseEquipmentCommandToNull();
}

// =============================================================
// 6) IDLE ESTIMATE
// =============================================================
private void updateIdleEstimate()
{
  double z = getZoneTemp().getValue();
  double t = getTargetZoneTempSetpoint().getValue();
  double delta = Math.abs(z - t);

  if (delta <= getTempTolerance().getValue())
  {
    setMinutesToSetpoint(new BStatusNumeric(0.0));
    return;
  }

  double rate = (z < t) ? getDegreesPerMinuteHeat().getValue() : getDegreesPerMinuteCool().getValue();
  rate = Math.max(0.01, rate);

  double predictedMins = delta / rate;
  predictedMins = Math.min(predictedMins, getMaxMinutesAllowed().getValue());

  setMinutesToSetpoint(new BStatusNumeric(predictedMins));
}

// =============================================================
// 7) OUTPUT HANDOFF (TRUE/OK or NULL only)
// =============================================================
private void handleEquipmentCommand()
{
  long now = System.currentTimeMillis();

  // Already released for this run? Keep released.
  if (hasReleasedToNullThisRun)
  {
    releaseEquipmentCommandToNull();
    return;
  }

  // Not running? Always released.
  if (!isOptimalStartRunning)
  {
    releaseEquipmentCommandToNull();
    return;
  }

  // Running: default TRUE/OK unless we arm/execute NULL release
  if (!pendingNullRelease)
  {
    // Arm delayed NULL release when scheduleNextValue flips FALSE
    if (getScheduleNextValue().getStatus().isOk() && !getScheduleNextValue().getValue())
    {
      double secs = getNullReleaseDelaySeconds();
      pendingNullRelease = true;
      nullReleaseAtMillis = now + (long)(secs * 1000.0);

      setCountdownToNullStatus(new BStatusBoolean(true));
      log("Schedule flipped FALSE. Handoff to NULL in " + (int)secs + "s.");
    }
  }

  // Expired -> release to NULL but keep learning run alive
  if (pendingNullRelease && now >= nullReleaseAtMillis)
  {
    hasReleasedToNullThisRun = true;
    pendingNullRelease = false;

    setCountdownToNullStatus(new BStatusBoolean(false));
    log("EquipmentStartCommand released to NULL (handoff). Learning continues.");
    releaseEquipmentCommandToNull();
    return;
  }

  // Otherwise assert TRUE/OK
  assertEquipmentCommandTrue();
}

private double getNullReleaseDelaySeconds()
{
  double secs = 0.0;

  if (getCommandOffDelaySeconds().getStatus().isOk())
    secs = getCommandOffDelaySeconds().getValue();

  // clamp
  if (secs < 0.0) secs = 0.0;
  if (secs > 3600.0) secs = 3600.0;

  return secs;
}

private void assertEquipmentCommandTrue()
{
  getEquipmentStartCommand().setValue(true);
  getEquipmentStartCommand().setStatus(BStatus.ok);
}

private void releaseEquipmentCommandToNull()
{
  // Never publish FALSE/OK.
  getEquipmentStartCommand().setValue(false);

  // AX variant: if this fails, replace with BStatus.NULL
  getEquipmentStartCommand().setStatus(BStatus.nullStatus);
}

// =============================================================
// 8) HELPERS
// =============================================================
public void onStop() throws Exception
{
  if (ticket != null) ticket.cancel();

  isOptimalStartRunning = false;
  setIsRunning(new BStatusBoolean(false));

  pendingNullRelease = false;
  hasReleasedToNullThisRun = false;
  setCountdownToNullStatus(new BStatusBoolean(false));

  releaseEquipmentCommandToNull();
}

private void updateTimer()
{
  if (ticket != null) ticket.cancel();
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private boolean validateSensors()
{
  // Only slots you have in auto-generated code
  return getZoneTemp().getStatus().isOk() && getTargetZoneTempSetpoint().getStatus().isOk();
}

private void abortRun(String reason)
{
  isOptimalStartRunning = false;
  setIsRunning(new BStatusBoolean(false));

  pendingNullRelease = false;
  hasReleasedToNullThisRun = true;
  setCountdownToNullStatus(new BStatusBoolean(false));

  releaseEquipmentCommandToNull();
  log("ABORTED: " + reason);
}

private void updateZoneAtToleranceFlag()
{
  double z = getZoneTemp().getValue();
  double t = getTargetZoneTempSetpoint().getValue();
  boolean atTol = (Math.abs(z - t) <= getTempTolerance().getValue());
  setZoneAtTempTolerance(new BStatusBoolean(atTol));
}

private void log(String msg)
{
  setStatusLog(new BStatusString(msg));

  // Optional: also print to console if you toggle slot printToConsoleLog
  if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue())
    System.out.println(msg);
}

private double round1(double v)
{
  return Math.round(v * 10.0) / 10.0;
}

private double round3(double v)
{
  return Math.round(v * 1000.0) / 1000.0;
}

```