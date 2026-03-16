# The Ultimate HVAC Optimal Start Control


Inspired by the familiar `kitControl` Optimal Start block design, these Program Objects extend capability with self-tuning algorithms informed by recent PNNL HVAC research. The Quadratic Model (Model 1) is ideal for interior or thermally stable zones whose recovery time is largely independent of outdoor conditions, while the Linear Degree-Per-Minute Model (Model 2) is recommended for weather-sensitive zones, as it explicitly incorporates outdoor air temperature into its prediction logic.


* **Optimal Start Control for ACs and HPs (PNNL)** — `pdf/Optimal Start Control for ACs and HPs.pdf`
    👉 [https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf](https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf)


Check for demonstrations on Vibe Coding on 📺
🎥 [**Talk Shop With Ben on YouTube**](https://www.youtube.com/@TalkShopWithBen)


Check out the **new December 2025** [YouTube playlist](https://www.youtube.com/playlist?list=PLlNmfKmNxm1tOa8P7aBhj0zf34AIlS4CQ) on optimal start/stop math and algorithms, built from short daily AI-generated lessons, plus the complete [open-source GitHub repository](https://github.com/bbartling/hvac-optimal-start-math-playground) featuring Python examples and in-depth explorations of PNNL optimal start research.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/optimalStartSnip.png"  alt="Optimal Start Program Object" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/zoneRecoverySnip.png" alt="Recovery Trend Example" width="750">
  <br><em>Recovery trend illustrating learned cool-down rate&nbsp;≈ 0.15 °F /min</em>
</p>

---


## 🆚 Comparison: Why is this better than `kitControl`?

Niagara's standard `kitControl` Optimized Start/Stop block has been the industry workhorse for years probably dating back the AX days around the 2005 era. However, it was designed in an era of simpler, static schedules. Here is the mathematical breakdown of why this **EMA** block provides a slightly better performance.


### The Math: Arbitrary Multiplier vs. Tunable Memory

Both blocks use linear models to calculate recovery rates, but their method of "learning" from the past differs significantly. The new EMA block always weights the most recent data heaviest compared to any single past data point. The "Days" setting just controls how fast the influence of old data fades away. **EMA** stands for **Exponential Moving Average**.

* **"Moving"**: The calculation continuously moves forward in time. As new run data comes in, it is added to the calculation, and old data influence fades away.
* **"Average"**: It is fundamentally smoothing out noise. If one day the recovery takes 45 minutes and the next day it takes 47 minutes, the EMA finds the trend line between them rather than jumping erratically.
* **"Exponential"**: This refers to the weighting. The most recent run has the highest weight, the run before that has less, and the run 10 days ago has very little. The influence of past data decays *exponentially* over time.

**Standard `kitControl` Block (Weighted Average)**
The standard block uses a rigid "Old Parameter Multiplier" (default 2) to weight historical data against the new run.

* **The Problem:** A multiplier of "2" is arbitrary. It hard-codes the math to always value history at ~66% and the new day at ~33%. You cannot intuitively tune this to "remember the last 2 weeks" without doing complex reverse arithmetic.

**New EMA Block (Exponential Moving Average)**
This block uses a **tunable EMA** based on a user-friendly "Days of Memory" setting.

* **The Advantage:** The  (weighting factor) is automatically calculated as .
* Set **10 Days**  System learns slowly and ignores outliers.
* Set **3 Days**  System adapts quickly to changing seasons.


### Summary Comparison

| Feature | Standard `kitControl` Block | New EMA Block |
| --- | --- | --- |
| **Math Model** | Linear (Minutes per Degree) | Linear (Degrees per Minute) |
| **Learning Algorithm** | Fixed Weighted Average (Multiplier) | **Tunable EMA (Days of Memory)** |
| **Target Goal** | Static "Comfort Limits" (e.g., 68°F) | **Actual Setpoint** (Snapshot at start) |
| **Schedule Logic** | Continuous (Stops if schedule toggles) | **EMA** (Ignores schedule once fired) |
| **Tuning Capability** | Separate Heat/Cool (Hard to tune) | **Separate Heat/Cool (Intuitive Days)** |

---

## The "Days of Memory" Feature

The most unique feature of this block is how it handles history. You don't need to configure complex databases. You simply tell the block **how many days of history** you want it to consider.

### The User Setting

* **Slot:** `historyDaysToRetain`
* **Input:** Integer (e.g., `10`)

### The Under-the-Hood Math

The block automatically converts your "Days" setting into a mathematical weighting factor () using this formula:

* **10 Days**   (Stable, slow learning)
* **5 Days**   (Balanced)
* **1 Day**   (Reactive, learns instantly from yesterday)


---

## The Workflow: Predict vs. Tune

It is critical to understand that **Predicting** and **Tuning** happen at different times.

### 1. Predicting (Always Running)

* **Frequency:** Every 15 seconds.
* **Action:** The block looks at the *current* Zone Temp, the *current* Setpoint, and the *stored* Learned Rate.
* **Math:** $\text{Minutes} = (\text{Target} - \text{Current}) / \text{LearnedRate}$
* **Result:** This updates the `minutesToSetpoint` slot live on the wiresheet.

### 2. Tuning (Once per Run)

* **Frequency:** Once, strictly at the end of a successful warm-up.
* **Action:** It calculates how fast the zone *actually* recovered.
* **Math:** $\text{NewRate} = \text{OldRate} + \alpha \times (\text{CurrentRunRate} - \text{OldRate})$
* **Result:** It updates the `degreesPerMinute` slot. This is the only time the "Memory" changes.

---

## ⚡ Slot Definitions

### Configuration

| Slot Name | Description |
| --- | --- |
| `maxMinutesAllowed` | **Safety Cap.** The unit will never start earlier than this (e.g., 180 min), even if the math says it needs 5 hours. |
| `tempTolerance` | **Success Target.** How close to setpoint is "Close Enough"? (e.g., 0.5°). |
| `historyDaysToRetain` | **The Tuning Knob.** How many past runs affect the current prediction. Higher = Smoother; Lower = Faster. **Note:** This value is used to automatically calculate the EMA weighting factor () under the hood. |

### Live Inputs

| Slot Name | Description |
| --- | --- |
| `zoneTemp` | Current Zone Temperature. |
| `targetZoneTempSetpoint` | The Occupied Heating/Cooling Setpoint. |
| `scheduleNextEventTime` | The timestamp of when the building *will* be occupied. |
| `scheduleNextValue` | Must be `true` (Occupied) for the start logic to engage. |

### Learned Memory (Do Not Touch)

| Slot Name | Description |
| --- | --- |
| `degreesPerMinuteHeat` | The persistent "Brain" for heating mode. |
| `degreesPerMinuteCool` | The persistent "Brain" for cooling mode. |

### Outputs

| Slot Name | Description |
| --- | --- |
| `equipmentStartCommand` | **The Trigger.** Boolean `true` to start the unit. |
| `minutesToSetpoint` | The live prediction of how long recovery will take. |
| `statusLog` | Human-readable log of the last run's performance (Start Temp, Actual Time, Predicted Time). |

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