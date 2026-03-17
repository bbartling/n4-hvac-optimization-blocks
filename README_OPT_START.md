# The Ultimate HVAC Optimal Start Control


Inspired by the familiar `kitControl` Optimal Start block design, this Program Objects extend capability with self-tuning algorithms informed by recent PNNL HVAC research.


<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/optimalStartSnip.png"  alt="Optimal Start Program Object" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/zoneRecoverySnip.png" alt="Recovery Trend Example" width="750">
  <br><em>Recovery trend illustrating learned cool-down rate&nbsp;≈ 0.15 °F /min</em>
</p>

---


## 🆚 Comparison: Why This Block Improves on Tridium `kitControl`

Niagara’s standard `kitControl` Optimized Start/Stop block has been a dependable industry workhorse for many years probably dating back to 2005 era of the advent of Niagara AX. It is proven and widely used, but it was built around an older style of schedule-centric control logic and a less intuitive learning model.

This custom block keeps the strengths of optimized start while making the math, tuning, and command handoff behavior easier to understand in the field.

Rather than claiming the standard block is “wrong,” a better way to say it is this:

**This custom block is more transparent, easier to tune, and better aligned with actual setpoint recovery behavior for modern HVAC control workflows.**

---

## The Math: Fixed Weighted Blend vs. Tunable Memory

Both approaches use a linear recovery concept, but they do not learn from history the same way.

### Standard Tridium `kitControl` Block

The standard block stores learned parameters such as runtime-per-degree and drift-time-per-degree, then updates them using a fixed weighted blend controlled by an **old parameter multiplier**.

That means the update behaves like:

```text
new = (old * multiplier + observed) / (multiplier + 1)
```

### Why that can be hard to tune

A multiplier like `2` or `3` works, but it is not very intuitive for a field technician.

- It does not naturally answer questions like:
  - “How many days of behavior am I really remembering?”
  - “How quickly will this adapt to a weather change?”
- It tends to feel abstract because the tuning knob is a math weight, not an operational concept.

---

## New Block: EMA-Style Learning with Tunable Memory

This custom block uses a **tunable memory** approach based on a user-friendly number of days.

EMA stands for **Exponential Moving Average**.

- **Moving** means the learning updates as new runs occur.
- **Average** means it smooths noisy day-to-day variation.
- **Exponential** means the most recent runs carry the most weight, and older runs fade out over time.

Instead of asking the user to tune an arbitrary multiplier, this block lets the user think in terms of **memory duration**.

### Practical meaning

- **10 Days** → slower, smoother adaptation
- **5 Days** → balanced adaptation
- **3 Days** → faster seasonal response
- **1 Day** → highly reactive

This makes the block easier to tune because the setting matches how technicians naturally think about building behavior.

---

## A More Useful Recovery Target

Another important difference is the target itself.

### Standard `kitControl`
The standard block is built around fixed comfort boundaries such as:

- `upperComfortLimit`
- `lowerComfortLimit`

### New Block
This custom block targets the **actual occupied setpoint** and latches that target at the beginning of the run.

That matters because:

- the recovery goal matches the real control target,
- mid-run schedule chatter does not distort the learning calculation,
- the run is evaluated against the same target it started with.

This makes the learning logic easier to explain and trend.

---

## Schedule Behavior and Command Handoff

This is one of the biggest operational improvements.

### Standard `kitControl`
The Tridium block is highly **schedule/event-driven**. Its output behavior is tightly tied to internal modes and schedule transitions.

### New Block
This custom block behaves more like a **latched ballistic run**:

1. It predicts required recovery time.
2. It starts when needed.
3. It latches the start temperature, target, and delta-T.
4. It continues learning until success or timeout.
5. It holds the start command `TRUE/OK` after learning is complete.
6. When occupancy begins, it waits for the configured off-delay.
7. It then releases command authority by handing off to `NULL`.

### Why this is useful

This handoff sequence is often easier to manage in real projects because:

- it is more explicit,
- it avoids command chatter,
- it cleanly returns control authority to downstream BAS logic,
- and it is easier to explain during commissioning.

---

## Predicting vs. Tuning

It is important to separate these two ideas.

### 1. Predicting
**Frequency:** every execution cycle

The block continuously predicts how long recovery should take based on:

- current zone temperature,
- current occupied setpoint,
- learned heating or cooling recovery rate.

Conceptually:

```text
predicted minutes = temperature difference / learned rate
```

This drives the live `minutesToSetpoint` output.

### 2. Tuning
**Frequency:** once per completed run

At the end of a successful recovery, the block calculates how fast the zone actually recovered and updates the learned rate.

Conceptually:

```text
newRate = oldRate + alpha * (currentRunRate - oldRate)
```

This is the only moment when the learned memory changes.

That separation makes the block easier to reason about:
- prediction happens continuously,
- learning happens once per run.

---

## Summary Comparison

| Feature | Standard `kitControl` Block | New EMA / Latched Block |
| --- | --- | --- |
| **Stored Learning Variable** | Runtime/drift time per degree | Degrees per minute |
| **Learning Method** | Fixed weighted average via multiplier | Tunable EMA-style memory |
| **Target Goal** | Fixed comfort limits | Actual occupied setpoint latched at run start |
| **Schedule Behavior** | Event/program-mode driven | Latched run with delayed handoff to `NULL` |
| **Command Output** | Tied to internal control mode | Explicit `TRUE/OK` then `NULL` handoff |
| **Tuning Feel** | Functional but less intuitive | More intuitive for field tuning |
| **Commissioning Clarity** | More internal/implicit | More transparent and easier to explain |

---

## The “Days of Memory” Feature

The most unique tuning feature of this block is that the user thinks in terms of **days of history**, not abstract weighting multipliers.

### User Setting

- **Slot:** `historyDaysToRetain`
- **Example values:** `10`, `5`, `3`, `1`

### Under the Hood

The block converts this memory setting into a weighting factor for the learning update.

In practical terms:

- higher days = slower, smoother learning
- lower days = faster adaptation to changing conditions

That gives the controls technician a tuning knob that maps directly to real-world expectations.

---

## Slot Definitions

### Configuration

| Slot Name | Description |
| --- | --- |
| `maxMinutesAllowed` | Safety cap. The unit will never start earlier than this limit. |
| `tempTolerance` | Defines how close to setpoint counts as success. |
| `historyDaysToRetain` | Main tuning knob for how much past behavior influences the learned rate. |
| `commandOffDelaySeconds` | Delay before handing off the command to `NULL` after occupancy begins. |

### Live Inputs

| Slot Name | Description |
| --- | --- |
| `zoneTemp` | Current zone temperature. |
| `targetZoneTempSetpoint` | Occupied target setpoint. |
| `scheduleNextEventTime` | Timestamp for the upcoming schedule transition. |
| `scheduleNextValue` | Must indicate the next occupied state for optimal start to trigger. |

### Learned Memory

| Slot Name | Description |
| --- | --- |
| `degreesPerMinuteHeat` | Learned heating recovery rate. |
| `degreesPerMinuteCool` | Learned cooling recovery rate. |

### Outputs

| Slot Name | Description |
| --- | --- |
| `equipmentStartCommand` | Start command output: asserted `TRUE/OK`, then released to `NULL`. |
| `minutesToSetpoint` | Live estimate of recovery time. |
| `statusLog` | Human-readable status of the latest run and learning result. |
| `isRunning` | Indicates whether the optimal start sequence is active. |
| `zoneAtTempTolerance` | Indicates whether the zone is within tolerance of the target. |
| `warmupTimeMinutes` | Elapsed learning time for the active run. |

---

## Bottom Line

Compared to Tridium’s standard `kitControl` optimized start/stop block, this custom block is not just different mathematically — it is easier to tune, easier to explain, and more explicit in how it starts, learns, holds command authority, and hands control back to the BAS.

That makes it especially useful for projects where commissioning clarity, modern setpoint-based recovery, and predictable command handoff matter as much as the learning math itself.


---

## 5. Java Code Implementation


```java
// ==========================================
// 1. STATEFUL FIELDS (Class Level)
// BUG FIXES 3/15/2026
// ==========================================
private Clock.Ticket ticket;
private long runStartTimestamp = 0L;

private boolean isOptimalStartRunning = false;
private boolean isLearningComplete = false;

private double latchedStartZoneTemp = 0.0;
private double latchedStartTarget = 0.0;
private double latchedDeltaT = 0.0;
private double latchedPredictedMins = 0.0;
private boolean lastRunWasHeat = true;

private boolean pendingNullRelease = false;
private long nullReleaseAtMillis = 0L;
private boolean hasReleasedToNullThisRun = false;

private static final double DEFAULT_RATE = 0.10;

// ==========================================
// 2. onStart() METHOD
// ==========================================
public void onStart() throws Exception 
{
    isOptimalStartRunning = false;
    isLearningComplete = false;
    runStartTimestamp = 0L;

    pendingNullRelease = false;
    nullReleaseAtMillis = 0L;
    hasReleasedToNullThisRun = false;

    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    if (getCommandOffDelaySeconds().isNull()) setCommandOffDelaySeconds(new BStatusNumeric(30.0));

    if (getDegreesPerMinuteHeat().getStatus().isNull() || getDegreesPerMinuteHeat().getValue() <= 0.001)
        setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));

    if (getDegreesPerMinuteCool().getStatus().isNull() || getDegreesPerMinuteCool().getValue() <= 0.001)
        setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));

    setMinutesToSetpoint(new BStatusNumeric(0.0));
    setWarmupTimeMinutes(new BStatusNumeric(0.0));
    setIsRunning(new BStatusBoolean(false));

    releaseEquipmentCommandToNull();

    log("Initialized. Waiting for schedule.");
    updateTimer();
}

// ==========================================
// 3. onExecute() METHOD
// ==========================================
public void onExecute() throws Exception 
{
    try
    {
        updateTimer();

        if (getStartTimerNow().getStatus().isOk() && getStartTimerNow().getValue())
        {
            setStartTimerNow(new BStatusBoolean(false));
            log("StartTimerNow triggered.");
        }

        if (getClearHistoryNow().getStatus().isOk() && getClearHistoryNow().getValue())
        {
            setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE));
            setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE));
            setClearHistoryNow(new BStatusBoolean(false));
            log("History Reset. Rates set to " + DEFAULT_RATE);
        }

        if (!validateSensors())
        {
            if (isOptimalStartRunning)
                abortRun("Sensor Failure.");

            setMinutesToSetpoint(new BStatusNumeric(0.0));
            releaseEquipmentCommandToNull();
            return;
        }

        updateZoneAtToleranceFlag();

        if (isOptimalStartRunning)
        {
            monitorActiveRun();      
        }
        else
        {
            updateIdleEstimate();    
            checkForStartTrigger();  
        }

        handleEquipmentCommand();

    }
    catch (Exception e)
    {
        log("Error: " + e.toString());
        abortRun("Exception in execute: " + e.getMessage());
    }
}

// ==========================================
// 4. onStop() METHOD
// ==========================================
public void onStop() throws Exception 
{
    if (ticket != null) ticket.cancel();

    isOptimalStartRunning = false;
    isLearningComplete = false;
    setIsRunning(new BStatusBoolean(false));

    pendingNullRelease = false;
    hasReleasedToNullThisRun = false;

    releaseEquipmentCommandToNull();
}

// ==========================================
// 5. HELPERS
// ==========================================
private void checkForStartTrigger()
{
    if (getScheduleNextEventTime().getStatus().isNull()) return;
    if (getScheduleNextValue().getStatus().isNull()) return;
    if (!getScheduleNextValue().getValue()) return;

    long nextTime = (long) getScheduleNextEventTime().getValue();
    double minsUntil = (nextTime - System.currentTimeMillis()) / 60000.0;

    if (minsUntil < 0 || minsUntil > 1440) return;

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

    if (Math.abs(z - t) <= getTempTolerance().getValue()) return;

    runStartTimestamp = System.currentTimeMillis();
    latchedStartZoneTemp = z;
    latchedStartTarget = t;
    latchedDeltaT = Math.abs(z - t);
    latchedPredictedMins = getMinutesToSetpoint().getValue();
    lastRunWasHeat = (z < t);

    pendingNullRelease = false;
    nullReleaseAtMillis = 0L;
    hasReleasedToNullThisRun = false;
    
    isLearningComplete = false;
    isOptimalStartRunning = true;
    setIsRunning(new BStatusBoolean(true));

    log(String.format("STARTED [%s]: StartT=%.1f | Target=%.1f | Pred=%.1fm | DeltaT=%.1f",
        (lastRunWasHeat ? "HEAT" : "COOL"),
        latchedStartZoneTemp,
        latchedStartTarget,
        latchedPredictedMins,
        latchedDeltaT));
}

private void monitorActiveRun()
{
    if (isLearningComplete) return; 

    double elapsedMins = (System.currentTimeMillis() - runStartTimestamp) / 60000.0;
    setWarmupTimeMinutes(new BStatusNumeric(elapsedMins));

    if (Math.abs(getZoneTemp().getValue() - latchedStartTarget) <= getTempTolerance().getValue())
    {
        completeRun(elapsedMins, true);
        return;
    }

    if (elapsedMins >= getMaxMinutesAllowed().getValue())
    {
        completeRun(elapsedMins, false);
        return;
    }
}

private void completeRun(double actualMins, boolean success)
{
    isLearningComplete = true;

    log(String.format("LEARNING ENDED [%s]: %s | Act=%.1fm | Pred=%.1fm | StartT=%.1f | Target=%.1f",
        (lastRunWasHeat ? "HEAT" : "COOL"),
        (success ? "Success" : "Timeout"),
        actualMins, latchedPredictedMins, latchedStartZoneTemp, latchedStartTarget));

    if (getActualMinutesToSetpoint() != null)
        setActualMinutesToSetpoint(new BStatusNumeric(actualMins));

    if (actualMins >= 5.0 && success)
    {
        double currentRunRate = latchedDeltaT / actualMins;

        BStatusNumeric rateSlot = lastRunWasHeat ? getDegreesPerMinuteHeat() : getDegreesPerMinuteCool();
        double oldRate = (rateSlot.getStatus().isNull() || rateSlot.getValue() <= 0.001)
            ? currentRunRate : rateSlot.getValue();

        double days = Math.max(1.0, Math.min(100.0, getHistoryDaysToRetain().getValue()));
        double alpha = 1.0 / days;

        double newRate = oldRate + alpha * (currentRunRate - oldRate);
        rateSlot.setValue(newRate);

        log(String.format("LEARN [%s]: old=%.3f | run=%.3f | new=%.3f",
            (lastRunWasHeat ? "HEAT" : "COOL"), oldRate, currentRunRate, newRate));
    }
    
    log("Learning complete. Holding command TRUE until schedule transitions.");
}

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

private void handleEquipmentCommand()
{
    long now = System.currentTimeMillis();

    if (hasReleasedToNullThisRun)
    {
        releaseEquipmentCommandToNull();
        return;
    }

    if (!isOptimalStartRunning)
    {
        releaseEquipmentCommandToNull();
        return;
    }

    if (!pendingNullRelease)
    {
        // When scheduleNextValue flips to false, it means the current state has flipped to Occupied
        if (getScheduleNextValue().getStatus().isOk() && !getScheduleNextValue().getValue())
        {
            double secs = getNullReleaseDelaySeconds();
            pendingNullRelease = true;
            nullReleaseAtMillis = now + (long)(secs * 1000.0);

            log("Schedule flipped to FALSE (occupied began). Handoff to NULL in " + (int)secs + "s.");
        }
    }

    if (pendingNullRelease && now >= nullReleaseAtMillis)
    {
        hasReleasedToNullThisRun = true;
        pendingNullRelease = false;
        
        isOptimalStartRunning = false;
        setIsRunning(new BStatusBoolean(false));

        log("EquipmentStartCommand handed off (NULL). Sequence complete.");
        releaseEquipmentCommandToNull();
        return;
    }

    assertEquipmentCommandTrue();
}

private double getNullReleaseDelaySeconds()
{
    double secs = 0.0;

    if (getCommandOffDelaySeconds().getStatus().isOk())
        secs = getCommandOffDelaySeconds().getValue();

    secs = Math.max(0.0, Math.min(3600.0, secs));
    return secs;
}

private void assertEquipmentCommandTrue()
{
    getEquipmentStartCommand().setValue(true);
    getEquipmentStartCommand().setStatus(BStatus.ok);
}

private void releaseEquipmentCommandToNull()
{
    getEquipmentStartCommand().setValue(false);
    getEquipmentStartCommand().setStatus(BStatus.nullStatus);
}

private void updateTimer()
{
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private boolean validateSensors()
{
    return getZoneTemp().getStatus().isOk() && getTargetZoneTempSetpoint().getStatus().isOk();
}

private void abortRun(String reason)
{
    isOptimalStartRunning = false;
    isLearningComplete = true;
    setIsRunning(new BStatusBoolean(false));

    pendingNullRelease = false;
    hasReleasedToNullThisRun = true;

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
    getStatusLog().setValue(msg);
}

```