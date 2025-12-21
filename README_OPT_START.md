# Optimal Start Logic


Inspired by the existing `kitControl` Optimal Start block look and feel, these program object blocks are enhanced with self-tuning algorithms based on the latest PNNL research for HVAC optimal start models; the Quadratic Model (Model 1) is best suited for interior zones and exterior zones whose recovery behavior is largely independent of outdoor air temperature, while the Linear Degree Per Minute (Model 2) is recommended for zones strongly influenced by outdoor conditions, since it directly incorporates OAT into its prediction.


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


### Quadratic Optimal Start Self-Tuning Block — PNNL Model 1

The **Model 1 (Quadratic)** block assumes that recovery time grows **non-linearly** with how far the zone is from setpoint. Instead of a straight line for long in minutes to takes for the zone to reach setpoint if data was plotted, it fits a curve of the form:



$$
t_{\text{minutes}} = a \cdot (\Delta T)^2 + b
$$


This shape is especially useful for **interior zones** or **heavy exterior zones** where a small temperature error recovers quickly, but large temperature gaps take disproportionately longer than a simple linear model would suggest.

Model 1 continuously updates its curve parameters by keeping a rolling history of completed runs (duration vs. ΔT), performing a quadratic regression, and then smoothing the result with an **Exponential Moving Average (EMA)** so the block reacts to recent behavior without throwing away its long-term memory.

* For **heating** if the `zoneTemp` prior to occupancy is less than `targetZoneTempSetpoint` - `tempTolerance`, the algorithm learns or tunes a pair of `alpha` math parameters `a_heat` and `a_heat` after each run.
* For **cooling** if the `zoneTemp` prior to occupancy is greater than `targetZoneTempSetpoint` + `tempTolerance`, the algorithm learns or tunes a pair of `alpha` math parameters  `a_cool` and `a_cool` after each run.

Both are updated only when a run is “good enough” to be considered learning-quality.

---

### Inputs (Model 1 – Quadratic)

> Inputs mirror the original linear block, but Model 1 **uses history + EMA** instead of a single learned rate.

| Slot                     | Type             | Notes                                                                                                   |
| :----------------------- | :--------------- | :------------------------------------------------------------------------------------------------------ |
| `zoneTemp`               | `BStatusNumeric` | Current zone temperature.                                                                               |
| `targetZoneTempSetpoint` | `BStatusNumeric` | Desired occupied setpoint.                                                                              |
| `outdoorAirTemp`         | `BStatusNumeric` | Optional. Logged at run start for operator visibility and analytics (not used in the Model 1 equation). |
| `scheduleNextValue`      | `BStatusBoolean` | Occupancy value of the *next* schedule event (`true` if occupied).                                      |
| `scheduleNextEventTime`  | `BStatusNumeric` | Timestamp (Java ms) of the next schedule event.                                                         |
| `maxMinutesAllowed`      | `BStatusNumeric` | Safety cap for runtime (default = 180 min).                                                             |
| `tempTolerance`          | `BStatusNumeric` | Acceptable deviation from setpoint (default 0.5°F).                                                     |
| `historyDaysToRetain`    | `BStatusNumeric` | How many days of past runs to keep in the HEAT/COOL histories. Old records are pruned.                  |
| `emaWeightingFactor`     | `BStatusNumeric` | Controls how aggressively the EMA blends new curve parameters into the existing ones.                   |
| `commandOffDelaySeconds` | `BStatusNumeric` | Countdown delay after a run ends before releasing the command to `null`.                                |
| `clearHistoryNow`        | `BStatusBoolean` | When `true`, clears all HEAT/COOL performance history and resets learning.                              |
| `printToConsoleLog`      | `BStatusBoolean` | Enables detailed debug logging to the Niagara console.                                                  |

---

### Outputs (Model 1 – Quadratic)

| Slot                         | Type             | Description                                                                                                                        |
| :--------------------------- | :--------------- | :--------------------------------------------------------------------------------------------------------------------------------- |
| `equipmentStartCommand`      | `BStatusBoolean` | Final command; `true` when equipment should run, otherwise `null`.                                                                 |
| `currentModelPredictMinutes` | `BStatusNumeric` | **Continuously updated quadratic prediction** of how many minutes recovery would take *if started now*. Drives the start decision. |
| `degreesPerMinuteHeat`       | `BStatusNumeric` | Effective average heating rate (°/min) **derived from history** and exposed mainly for visualization and sanity checking.          |
| `degreesPerMinuteCool`       | `BStatusNumeric` | Effective average cooling rate (°/min) derived from history (visual only).                                                         |
| `statusLog`                  | `BStatusString`  | Human-readable summary of last major action (start, stop, learning update, hold, or history clear).                                |
| `historyLog`                 | `BStatusString`  | Optional multi-line text dump of HEAT/COOL history (ΔT, duration, mode).                                                           |
| `isRunning`                  | `BStatusBoolean` | `true` during an active learning run (warm-up / cool-down).                                                                        |
| `zoneAtTempTolerance`        | `BStatusBoolean` | `true` when `zoneTemp` is within the configured tolerance of `targetZoneTempSetpoint`.                                             |
| `currentRunElapsedMinutes`   | `BStatusNumeric` | Live stopwatch of the current run.                                                                                                 |
| `countdownToNullStatus`      | `BStatusBoolean` | `true` while the off-delay countdown is in progress.                                                                               |
| `lastRunPredictedMinutes`    | `BStatusNumeric` | Snapshot of the quadratic prediction at the instant the run started.                                                               |
| `lastRunActualMinutes`       | `BStatusNumeric` | Final measured time for the last run (success or timeout).                                                                         |
| `lastRunErrorMinutes`        | `BStatusNumeric` | `Predicted − Actual`. Positive = started too early; negative = started too late.                                                   |
| `lastRunErrorPercent`        | `BStatusNumeric` | Percent error: `(Predicted − Actual) / Actual × 100`.                                                                              |
| `currentHistoryRecordCount`  | `BStatusNumeric` | Total count of HEAT + COOL performance records currently stored.                                                                   |

> Just like Model 2, `currentModelPredictMinutes` is forced to **0.0** when the zone is already within tolerance, so the block doesn’t start equipment unnecessarily.


<details>
<summary>💻 Java Code Quadratic Model</summary>

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java


// PNNL Quadratic Model 1
// ==========================================================
// MEMBER VARIABLES (State)
// ==========================================================
static class PerformanceRecord {
    long timestamp;
    double durationMinutes; 
    double deltaT;          
    String mode;            
    
    PerformanceRecord(long ts, double t, double dT, String m) {
        this.timestamp = ts;
        this.durationMinutes = t;
        this.deltaT = dT;
        this.mode = m;
    }
    
    public String toString() {
        return String.format("[%s] dT=%.1f, mins=%.1f", mode, deltaT, durationMinutes);
    }
}

private Clock.Ticket ticket;
private long startTimestamp = 0L;
private boolean isOptimalStartRunning = false;
private boolean isHoldingForSchedule = false; 
private long targetEventTime = 0L;            
private long lastStartTriggerTimestamp = 0L;

private boolean setpointWasMetDuringRun = false;
private double minutesToReachSetpoint = 0.0;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0L;

// Quadratic Model Parameters (y = ax^2 + b)
private double learned_alpha_a_heat = 0.1;
private double learned_alpha_b_heat = 5.0;
private double learned_alpha_a_cool = 0.1;
private double learned_alpha_b_cool = 5.0;

private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();
private static final double EMA_ALPHA = 0.2; 

public void onStart() throws Exception {
    // 1. Defaults
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    
    // 2. Init Outputs
    setIsRunning(new BStatusBoolean(false));
    setCurrentModelPredictMinutes(new BStatusNumeric(getMaxMinutesAllowed().getValue())); 
    
    // Init Reference Rate Slots (Visual only for Quad model)
    setDegreesPerMinuteHeat(new BStatusNumeric(0.1));
    setDegreesPerMinuteCool(new BStatusNumeric(0.1));

    getEquipmentStartCommand().setValue(false);
    getEquipmentStartCommand().setStatus(BStatus.NULL);
    
    // 3. Init Performance Metrics
    setLastRunPredictedMinutes(new BStatusNumeric(0.0));
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setLastRunErrorPercent(new BStatusNumeric(0.0));
    setCurrentRunElapsedMinutes(new BStatusNumeric(0.0));

    // 4. Init Logic
    setZoneAtTempTolerance(new BStatusBoolean(false));
    getStatusLog().setValue("[onStart] Quadratic Model 1 initialized.");
    debug("Block Started. Default Params Loaded: A_heat=" + learned_alpha_a_heat + ", B_heat=" + learned_alpha_b_heat);
    
    updateTimer();
}

public void onExecute() throws Exception {
    try {
        // 1) Heartbeat + Zone tolerance
        updateTimer();
        updateZoneAtTempTolerance();

        // 2) Handle Factory Reset (new)
        if (getResetBackToDefault().getStatus().isOk() &&
            getResetBackToDefault().getValue()) {

            resetQuadraticDefaults();
            setResetBackToDefault(new BStatusBoolean(false));
            debug("User requested factory reset. Quadratic model returned to defaults.");
        }

        // 3) Handle History Clear (legacy, but still useful)
        if (getClearHistoryNow().getStatus().isOk() &&
            getClearHistoryNow().getValue()) {

            heatHistory.clear();
            coolHistory.clear();
            setClearHistoryNow(new BStatusBoolean(false));
            setFormattedStatusLog("History cleared (records only; model coefficients preserved).");
            debug("User requested history clear. All performance records purged.");
        }

        // 4) ALWAYS Update Prediction (continuous Model 1 estimate)
        updateCurrentModelPrediction();

        // 5) MAIN STATE MACHINE
        if (isOptimalStartRunning) {
            // STATE 1: ACTIVE LEARNING RUN
            monitorActiveRun();
            forceCommandTrue();

        } else if (isHoldingForSchedule) {
            // STATE 2: HOLDING PATTERN (Finished early, waiting for schedule)
            monitorHold();
            forceCommandTrue();

        } else {
            // STATE 3: IDLE / MONITORING
            updateEquipmentStartCommand();
        }

    } catch (Exception e) {
        // ROBUST CRASH LOGGING
        if (getPrintToConsoleLog().getStatus().isOk() &&
            getPrintToConsoleLog().getValue()) {

            System.out.println("[OptStart-Quad] CRASH in onExecute: " + e.getMessage());
            e.printStackTrace();
        }
        getStatusLog().setValue("ERROR: Block crashed in onExecute. Check Application Director.");
    }
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
    debug("Block Stopped.");
}

// ==========================================================
// LOGIC METHODS
// ==========================================================

private void debug(String msg) {
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("[OptStart-Quad] " + msg);
    }
}

private void forceCommandTrue() {
    getEquipmentStartCommand().setValue(true);
    getEquipmentStartCommand().setStatus(BStatus.ok);
    getCountdownToNullStatus().setValue(false);
}

private void updateCurrentModelPrediction() {
    // If at setpoint, prediction is 0 
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }
    
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        return;
    }

    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMins = getMaxMinutesAllowed().getValue();
    double estimated = maxMins;

    // --- QUADRATIC MATH: t = a(dT^2) + b ---
    if (zone < target) { // Heat
        estimated = (learned_alpha_a_heat * (delta * delta)) + learned_alpha_b_heat;
    } else { // Cool
        estimated = (learned_alpha_a_cool * (delta * delta)) + learned_alpha_b_cool;
    }

    if (estimated < 0) estimated = 0;
    if (estimated > maxMins) estimated = maxMins;
    
    setCurrentModelPredictMinutes(new BStatusNumeric(estimated));
}

private void updateEquipmentStartCommand() {
    // 1. Off-Delay Logic
    if (isOffDelayActive) {
        long elapsed = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delay = 60; 
        if (getCommandOffDelaySeconds().getStatus().isOk()) delay = (long)getCommandOffDelaySeconds().getValue();

        if (elapsed >= delay) {
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false);
            debug("Off-delay finished. Command released to NULL.");
        } else {
            getCountdownToNullStatus().setValue(true);
        }
        return; 
    }

    // 2. Schedule Check
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        return;
    }

    boolean nextOccupied = getScheduleNextValue().getValue();
    
    if (nextOccupied) {
        long now = System.currentTimeMillis();
        long nextTime = (long)getScheduleNextEventTime().getValue();
        double minsUntilEvent = (nextTime - now) / 60000.0;
        if (minsUntilEvent < 0) minsUntilEvent = 0;

        double neededMins = getCurrentModelPredictMinutes().getValue();

        // TRIGGER START
        if (neededMins >= minsUntilEvent) {
            debug("Start Triggered! Need " + round1(neededMins) + " min, have " + round1(minsUntilEvent) + " min.");
            startOptimalStartSequence(nextTime); 
            forceCommandTrue();
        }
    } else {
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            debug("Schedule unoccupied. Entering Off-Delay.");
        }
    }
}

private void startOptimalStartSequence(long nextEventTime) {
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }
    
    // --- SNAPSHOT PREDICTION ---
    double pred = getCurrentModelPredictMinutes().getValue();
    setLastRunPredictedMinutes(new BStatusNumeric(pred));
    
    // Init Run Stats
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setLastRunErrorPercent(new BStatusNumeric(0.0));
    
    startTimestamp = System.currentTimeMillis();
    targetEventTime = nextEventTime; 
    isOptimalStartRunning = true;
    isHoldingForSchedule = false;
    
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    }

    setFormattedStatusLog("[Start] Quad Model running. Need " + round1(pred) + " min.");
    debug("Run Started. TargetEventTime=" + new java.util.Date(targetEventTime) + ", Predicted=" + round1(pred));
}

private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsed = (now - startTimestamp) / 60000.0;
    double maxMins = getMaxMinutesAllowed().getValue();
    
    setCurrentRunElapsedMinutes(new BStatusNumeric(elapsed));

    // A. STOP: Target Met (SUCCESS)
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Stop] Target met in " + round1(elapsed) + " min.");
        stopAndRecord(elapsed, true); 
        return;
    }

    // B. STOP: Timeout (FAILURE)
    if (elapsed >= maxMins) {
        setFormattedStatusLog("[Stop] Max Minutes (" + maxMins + ") exceeded.");
        stopAndRecord(elapsed, false);
        return;
    }

    // C. STOP: Sensors died
    if (!getZoneTemp().getStatus().isOk()) {
        stopAndRecord(elapsed, false);
    }
}

private void monitorHold() {
    long now = System.currentTimeMillis();
    
    if (now >= targetEventTime) {
        isHoldingForSchedule = false;
        setFormattedStatusLog("Schedule Event Time reached. Releasing to BAS.");
        debug("Hold Released: Event time arrived.");
    }
    
    if (getScheduleNextValue().getStatus().isOk() && !getScheduleNextValue().getValue()) {
        isHoldingForSchedule = false;
        setFormattedStatusLog("Schedule Next Value changed to Unoccupied. Aborting hold.");
        debug("Hold Aborted: Schedule flipped to unoccupied.");
    }
}

private void stopAndRecord(double actualMinutes, boolean success) {
    isOptimalStartRunning = false; 
    setIsRunning(new BStatusBoolean(false));
    
    // 1. Metrics
    setLastRunActualMinutes(new BStatusNumeric(actualMinutes));
    double predicted = getLastRunPredictedMinutes().getValue();
    double error = predicted - actualMinutes;
    setLastRunErrorMinutes(new BStatusNumeric(error));
    
    double pct = (actualMinutes > 0) ? (error / actualMinutes) * 100.0 : 0.0;
    setLastRunErrorPercent(new BStatusNumeric(pct));
    
    debug(String.format("Run Finished. Actual=%.1f, Pred=%.1f, Err=%.1f (%.1f%%). Success=%b", 
          actualMinutes, predicted, error, pct, success));
    
    // 2. Learning
    double zoneStart = getZoneTempAtStart().getValue();
    double zoneEnd = getZoneTemp().getValue();
    double deltaT = Math.abs(zoneEnd - zoneStart);

    if (success && actualMinutes > 5.0 && deltaT > 1.0) {
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        
        PerformanceRecord rec = new PerformanceRecord(
            System.currentTimeMillis(),
            actualMinutes,
            deltaT,
            mode
        );
        
        if (mode.equals("HEAT")) heatHistory.add(rec);
        else coolHistory.add(rec);
        
        debug("Learning: Added record [" + rec.toString() + "]");
        
        // --- QUADRATIC REGRESSION UPDATE ---
        updateModelRegression();
        
        setFormattedStatusLog("Learning updated (" + mode + "). Recalculated curve.");
        
        // 3. ENTER HOLD STATE if finished early
        long now = System.currentTimeMillis();
        if (now < targetEventTime) {
            isHoldingForSchedule = true;
            setFormattedStatusLog("Finished early. Holding Command until Schedule Event.");
            debug("Entering HOLD state. Waiting for event time...");
        }
        
    } else {
        setFormattedStatusLog("Run finished. No learning (Timeout or Short Run).");
        if (success && System.currentTimeMillis() < targetEventTime) {
             isHoldingForSchedule = true;
        }
    }
}

private void updateModelRegression() {
    pruneHistory();
    
    double[] heatParams = regress(heatHistory, "HEAT");
    this.learned_alpha_a_heat += EMA_ALPHA * (heatParams[0] - this.learned_alpha_a_heat);
    this.learned_alpha_b_heat += EMA_ALPHA * (heatParams[1] - this.learned_alpha_b_heat);
    
    double[] coolParams = regress(coolHistory, "COOL");
    this.learned_alpha_a_cool += EMA_ALPHA * (coolParams[0] - this.learned_alpha_a_cool);
    this.learned_alpha_b_cool += EMA_ALPHA * (coolParams[1] - this.learned_alpha_b_cool);
    
    debug(String.format("Regression Update | HEAT: a=%.4f, b=%.2f | COOL: a=%.4f, b=%.2f",
          learned_alpha_a_heat, learned_alpha_b_heat, learned_alpha_a_cool, learned_alpha_b_cool));
    
    updateVisualRates();
}

private double[] regress(java.util.List<PerformanceRecord> history, String modeLabel) {
    if (history.size() < 2) {
        return new double[] { 0.1, 5.0 }; 
    }
    
    double n = history.size();
    double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    
    for (PerformanceRecord r : history) {
        double x = r.deltaT * r.deltaT; 
        double y = r.durationMinutes;
        sumX += x;
        sumY += y;
        sumXY += (x*y);
        sumXX += (x*x);
    }
    
    double denom = (n * sumXX) - (sumX * sumX);
    if (Math.abs(denom) < 0.001) return new double[] { 0.1, 5.0 };
    
    double a = ((n * sumXY) - (sumX * sumY)) / denom;
    double b = (sumY - (a * sumX)) / n;
    
    if (a < 0) a = 0.1; 
    if (b < 0) b = 0;   
    
    debug(String.format("Regress(%s): n=%.0f, Raw A=%.4f, Raw B=%.2f", modeLabel, n, a, b));
    return new double[] { a, b };
}

private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxDays = (int) getHistoryDaysToRetain().getValue();
    long cutoff = System.currentTimeMillis() - (maxDays * 86400000L);
    
    heatHistory.removeIf(r -> r.timestamp < cutoff);
    coolHistory.removeIf(r -> r.timestamp < cutoff);
}

private void updateVisualRates() {
    if (!heatHistory.isEmpty()) {
        double totalDT = 0, totalT = 0;
        for(PerformanceRecord r : heatHistory) { totalDT += r.deltaT; totalT += r.durationMinutes; }
        if (totalT > 0) setDegreesPerMinuteHeat(new BStatusNumeric(totalDT/totalT));
    }
    if (!coolHistory.isEmpty()) {
        double totalDT = 0, totalT = 0;
        for(PerformanceRecord r : coolHistory) { totalDT += r.deltaT; totalT += r.durationMinutes; }
        if (totalT > 0) setDegreesPerMinuteCool(new BStatusNumeric(totalDT/totalT));
    }
}

private void resetQuadraticDefaults() {
    heatHistory.clear();
    coolHistory.clear();

    learned_alpha_a_heat = 0.1;
    learned_alpha_b_heat = 5.0;
    learned_alpha_a_cool = 0.1;
    learned_alpha_b_cool = 5.0;

    setDegreesPerMinuteHeat(new BStatusNumeric(0.1));
    setDegreesPerMinuteCool(new BStatusNumeric(0.1));

    setFormattedStatusLog("Quadratic Model reset to factory defaults.");
    debug("Factory Reset Performed for Quadratic Model 1.");
}


private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private void setFormattedStatusLog(String msg) {
    getStatusLog().setValue(msg);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) return;
    double tol = 0.5;
    if (getTempTolerance().getStatus().isOk()) tol = getTempTolerance().getValue();
    double diff = Math.abs(getZoneTemp().getValue() - getTargetZoneTempSetpoint().getValue());
    setZoneAtTempTolerance(new BStatusBoolean(diff <= tol));
}

private double round1(double v) { return Math.round(v * 10.0) / 10.0; }
```

</details>


---


### Linear Degree Per Minute Optimal Start Self-Tuning Block — PNNL Model 2

The **Model 2** block builds on the same self-tuning linear behavior but adds an **outdoor-air temperature (OAT) scaling** step using the PNNL “Model 2” ratio. Instead of assuming that every morning behaves the same, it remembers how long a previous successful warm-up or cool-down took at a specific OAT (the *baseline*), then scales that runtime up or down depending on today’s OAT relative to a reference temperature `T_ref` for heating or cooling.

Below, in the equation, `minutes_linear` is calculated using a linear degrees-per-minute approach that is continuously self-tuned on each learning run. The algorithm maintains separate performance records for **heating** and **cooling**, allowing it to refine both linear recovery rates over time.

$$
t_{\text{linear}} = \frac{\Delta T}{r_{\text{learned}}}
$$


Then, per the PNNL Model 2 definition, the outside air temperature is incorporated as a ratio that is also updated on each successful learning run to compute the final `minutes_total`. The additional time in minutes contributed by this ratio is likewise continuously tuned and exposed on the block for visibility as either `coolOatMinutesAdder` or `heatOatMinutesAdder`, depending on whether the algorithm is operating in cooling or heating mode.


$$
t_{\text{total}} = t_{\text{linear}}\frac{\left|T_{\text{ref}}-OAT_{\text{base}}\right|}{\left|T_{\text{ref}}-OAT_{\text{today}}\right|}
$$


---

### Inputs (Model 2)

> Most inputs are identical to the Linear block; only the differences and additions are highlighted here.

| Slot                     | Type             | Notes                                                                                                                     |
| :----------------------- | :--------------- | :------------------------------------------------------------------------------------------------------------------------ |
| `zoneTemp`               | `BStatusNumeric` | Current zone temperature.                                                                                                 |
| `targetZoneTempSetpoint` | `BStatusNumeric` | Desired occupied setpoint.                                                                                                |
| `outdoorAirTemp`         | `BStatusNumeric` | **Required for Model 2.** Used to compute the OAT ratio. If invalid, the block automatically reverts to the linear model. |
| `scheduleNextValue`      | `BStatusBoolean` | Occupancy of the *next* schedule event (`true` if occupied).                                                              |
| `scheduleNextEventTime`  | `BStatusNumeric` | Timestamp (Java ms) of the next schedule event.                                                                           |
| `maxMinutesAllowed`      | `BStatusNumeric` | Safety cap for runtime (default = 180 min).                                                                               |
| `tempTolerance`          | `BStatusNumeric` | Acceptable deviation from setpoint (default 0.5°F).                                                                       |
| `commandOffDelaySeconds` | `BStatusNumeric` | Countdown delay after a run ends before releasing to `null`.                                                              |
| `printToConsoleLog`      | `BStatusBoolean` | Enables detailed debug printing.                                                                                          |
| `useImperialUnits`       | `BStatusBoolean` | **(New)** Uses °F references (32°F / 100°F) if `true`, °C references (0°C / 38°C) if `false`.                             |
| `resetBackToDefault`     | `BStatusBoolean` | **(New)** Resets Model 2 learning back to factory defaults.                                                               |

> Model 2 does not require the older N-day history / EMA learning slots; its “memory” is the most recent successful baseline in each mode.

---

### Outputs (Model 2)

| Slot                         | Type             | Description                                                                                        |
| :--------------------------- | :--------------- | :------------------------------------------------------------------------------------------------- |
| `equipmentStartCommand`      | `BStatusBoolean` | Final command; `true` when equipment should run, otherwise `null`.                                 |
| `currentModelPredictMinutes` | `BStatusNumeric` | **Continuously updated live prediction** of how many minutes recovery would take *if started now*. |
| `degreesPerMinuteHeat`       | `BStatusNumeric` | Learned heating recovery rate (°/min) — used for **linear fallback**.                              |
| `degreesPerMinuteCool`       | `BStatusNumeric` | Learned cooling recovery rate (°/min) — used for **linear fallback**.                              |
| `heatOatMinutesAdder`        | `BStatusNumeric` | **(New)** Additional heating minutes due to today’s OAT vs. baseline.                              |
| `coolOatMinutesAdder`        | `BStatusNumeric` | **(New)** Additional cooling minutes due to today’s OAT vs. baseline.                              |
| `statusLog`                  | `BStatusString`  | Human-readable summary of last major action.                                                       |
| `isRunning`                  | `BStatusBoolean` | `true` only during an active learning run.                                                         |
| `zoneAtTempTolerance`        | `BStatusBoolean` | `true` when zone is within tolerance of setpoint.                                                  |
| `currentRunElapsedMinutes`   | `BStatusNumeric` | Live stopwatch of the current run.                                                                 |
| `countdownToNullStatus`      | `BStatusBoolean` | `true` while off-delay countdown is active.                                                        |
| `lastRunPredictedMinutes`    | `BStatusNumeric` | Predicted runtime snapshot taken at the instant the run started.                                   |
| `lastRunActualMinutes`       | `BStatusNumeric` | Actual measured runtime for the last event.                                                        |
| `lastRunErrorMinutes`        | `BStatusNumeric` | `Predicted − Actual`. Positive = too early; negative = too late.                                   |
| `lastRunErrorPercent`        | `BStatusNumeric` | **(New)** `(Predicted − Actual) / Actual × 100`.                                                   |

> When the zone is already within tolerance, `currentModelPredictMinutes` is forced to **0.0** so the block never triggers early unnecessarily.

---


<details>
<summary>💻 Java Code Linear Model</summary>

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java


// PNNL Linear Model 2
// ==========================================================
// MEMBER VARIABLES (State)
// ==========================================================
private Clock.Ticket ticket;
private long startTimestamp = 0L;
private boolean isOptimalStartRunning = false;
private boolean isHoldingForSchedule = false; 
private long targetEventTime = 0L;            
private long lastStartTriggerTimestamp = 0L;

// PNNL Model 2 Baselines (The "Memory")
private double lastHeatBaselineMinutes = 30.0; 
private double lastHeatBaselineOat     = 20.0; 
private double lastCoolBaselineMinutes = 30.0;
private double lastCoolBaselineOat     = 85.0;

// PNNL Reference Temperatures (Design Conditions)
private static final double TREF_HEAT_IMP = 32.0;   
private static final double TREF_HEAT_MET = 0.0;
private static final double TREF_COOL_IMP = 100.0;  
private static final double TREF_COOL_MET = 37.78;

// State Flags
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0L;

// Constants for Ratio Clamping 
private static final double RATIO_MIN = 0.2;
private static final double RATIO_MAX = 4.0;

public void onStart() throws Exception {
    // 1. Defaults
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    // Default to Imperial if null
    if (getUseImperialUnits().isNull()) setUseImperialUnits(new BStatusBoolean(true));

    // 2. Init Outputs
    setIsRunning(new BStatusBoolean(false));
    setCurrentModelPredictMinutes(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    
    // Initialize standard rate slots 
    if (getDegreesPerMinuteHeat().isNull()) setDegreesPerMinuteHeat(new BStatusNumeric(0.1));
    if (getDegreesPerMinuteCool().isNull()) setDegreesPerMinuteCool(new BStatusNumeric(0.1));

    getEquipmentStartCommand().setValue(false);
    getEquipmentStartCommand().setStatus(BStatus.NULL);

    // Initialize Metrics
    setLastRunPredictedMinutes(new BStatusNumeric(0.0));
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setLastRunErrorPercent(new BStatusNumeric(0.0));

    // Initialize Model 2 Visualizers
    setHeatOatMinutesAdder(new BStatusNumeric(0.0));
    setCoolOatMinutesAdder(new BStatusNumeric(0.0));
    
    if (getResetBackToDefault().isNull()) setResetBackToDefault(new BStatusBoolean(false));
    
    setZoneAtTempTolerance(new BStatusBoolean(false));
    
    // Log startup
    getStatusLog().setValue("[onStart] PNNL Model 2 (Adaptive OAT Ratio) initialized.");
    debug("Block Started. Default Baselines: Heat=" + lastHeatBaselineMinutes + "m, Cool=" + lastCoolBaselineMinutes + "m");
    
    updateTimer();
}

public void onExecute() throws Exception {
    try {
        updateTimer();
        updateZoneAtTempTolerance();

        // Handle Reset
        if (getResetBackToDefault().getStatus().isOk() && getResetBackToDefault().getValue()) {
            resetModelToDefaults();
            setResetBackToDefault(new BStatusBoolean(false));
            debug("User requested Factory Reset.");
        }

        // Always Predict (Live Math)
        updateCurrentModelPrediction();

        // --- MAIN STATE MACHINE (Unified Backbone) ---
        if (isOptimalStartRunning) {
            // STATE 1: ACTIVE LEARNING RUN
            monitorActiveRun();
            forceCommandTrue();
            
        } else if (isHoldingForSchedule) {
            // STATE 2: HOLDING PATTERN (Finished Early)
            monitorHold();
            forceCommandTrue();
            
        } else {
            // STATE 3: IDLE / MONITORING
            updateEquipmentStartCommand();
        }
    } catch (Exception e) {
        // ROBUST CRASH LOGGING
        if (getPrintToConsoleLog().getValue()) {
            System.out.println("[OptStart-PNNL] CRASH in onExecute: " + e.getMessage());
            e.printStackTrace();
        }
        getStatusLog().setValue("ERROR: Block crashed. Check Application Director.");
    }
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
    debug("Block Stopped.");
}

// ==========================================================
// LOGIC METHODS
// ==========================================================

private void debug(String msg) {
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("[OptStart-PNNL] " + msg);
    }
}

private void forceCommandTrue() {
    getEquipmentStartCommand().setValue(true);
    getEquipmentStartCommand().setStatus(BStatus.ok);
    getCountdownToNullStatus().setValue(false);
}

private void updateCurrentModelPrediction() {
    // If at setpoint, prediction is 0
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }

    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) return;

    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMins = getMaxMinutesAllowed().getValue();
    
    // Tiny delta check to prevent noise triggers
    if (delta <= 0.2) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }

    double oat = getOutdoorAirTemp().getStatus().isOk() ? getOutdoorAirTemp().getValue() : Double.NaN;
    double predMinutes = 0.0;

    if (zone < target) predMinutes = calculateModel2Minutes("HEAT", delta, oat);
    else predMinutes = calculateModel2Minutes("COOL", delta, oat);

    if (predMinutes < 0) predMinutes = 0;
    if (predMinutes > maxMins) predMinutes = maxMins;

    setCurrentModelPredictMinutes(new BStatusNumeric(predMinutes));
}

private double calculateModel2Minutes(String mode, double delta, double oatNow) {
    double tBase, oatBase, tRef, rateFallback;
    boolean imperial = getUseImperialUnits().getValue();
    
    if (mode.equals("HEAT")) {
        tBase = lastHeatBaselineMinutes;
        oatBase = lastHeatBaselineOat;
        // PNNL Constants: 32F / 0C
        tRef = imperial ? TREF_HEAT_IMP : TREF_HEAT_MET; 
        rateFallback = getDegreesPerMinuteHeat().getValue();
    } else {
        tBase = lastCoolBaselineMinutes;
        oatBase = lastCoolBaselineOat;
        // PNNL Constants: 100F / 37.78C
        tRef = imperial ? TREF_COOL_IMP : TREF_COOL_MET;
        rateFallback = getDegreesPerMinuteCool().getValue();
    }

    // 1. Fallback: If OAT is bad or missing, use simple Linear Model
    if (Double.isNaN(oatNow) || Double.isNaN(oatBase) || rateFallback <= 0.001) {
       return (rateFallback > 0) ? delta / rateFallback : 180.0;
    }

    // 2. PNNL Ratio Calculation
    // As OAT approaches T_ref (Capacity Limit), the denominator shrinks, Ratio grows, Time increases.
    double numerator   = Math.abs(tRef - oatBase);
    double denominator = Math.abs(tRef - oatNow);
    
    // Protect against divide by zero (if today is exactly design temp)
    if (denominator < 0.5) denominator = 0.5; 

    double ratio = numerator / denominator;
    
    // Clamp ratio to sane limits
    if (ratio < RATIO_MIN) ratio = RATIO_MIN;
    if (ratio > RATIO_MAX) ratio = RATIO_MAX;

    double predicted = tBase * ratio;
    
    // Update visual "Adder" slot
    double added = predicted - tBase;
    if (mode.equals("HEAT")) setHeatOatMinutesAdder(new BStatusNumeric(added));
    else setCoolOatMinutesAdder(new BStatusNumeric(added));

    return predicted;
}

private void updateEquipmentStartCommand() {
    // 1. Off-Delay Logic
    if (isOffDelayActive) {
        long elapsed = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delay = 60; 
        if (getCommandOffDelaySeconds().getStatus().isOk()) delay = (long)getCommandOffDelaySeconds().getValue();

        if (elapsed >= delay) {
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false);
            setFormattedStatusLog("Off-delay done. Command released.");
            debug("Off-delay finished.");
        } else {
            getCountdownToNullStatus().setValue(true);
        }
        return; 
    }

    // 2. Schedule Check
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        return;
    }

    boolean nextOccupied = getScheduleNextValue().getValue();
    
    if (nextOccupied) {
        long now = System.currentTimeMillis();
        long nextTime = (long)getScheduleNextEventTime().getValue();
        double minsUntilEvent = (nextTime - now) / 60000.0;
        if (minsUntilEvent < 0) minsUntilEvent = 0;

        double neededMins = getCurrentModelPredictMinutes().getValue();

        // TRIGGER START
        if (neededMins >= minsUntilEvent) {
            debug("Start Triggered! Need " + round1(neededMins) + "m, have " + round1(minsUntilEvent) + "m.");
            startOptimalStartSequence(nextTime); // Latch Target Time
            forceCommandTrue();
        }
    } else {
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            debug("Schedule unoccupied. Entering Off-Delay.");
        }
    }
}

private void startOptimalStartSequence(long nextEventTime) {
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }
    
    // --- SNAPSHOT PREDICTION ---
    double pred = getCurrentModelPredictMinutes().getValue();
    setLastRunPredictedMinutes(new BStatusNumeric(pred));
    
    // Init Run Stats
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setLastRunErrorPercent(new BStatusNumeric(0.0));
    
    startTimestamp = System.currentTimeMillis();
    targetEventTime = nextEventTime; 
    isOptimalStartRunning = true;
    isHoldingForSchedule = false;
    
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    }

    setFormattedStatusLog("[Start] PNNL Model running. Need " + round1(pred) + " min.");
    debug("Run Started. TargetTime=" + new java.util.Date(targetEventTime) + ", Pred=" + round1(pred));
}

private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsed = (now - startTimestamp) / 60000.0;
    double maxMins = getMaxMinutesAllowed().getValue();

    // A. STOP: Target Met (SUCCESS)
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Stop] Target met in " + round1(elapsed) + " min. Updating model.");
        stopAndRecord(elapsed, true);
        return;
    }

    // B. STOP: Timeout (FAILURE)
    if (elapsed >= maxMins) {
        setFormattedStatusLog("[Stop] Max Minutes (" + maxMins + ") exceeded.");
        stopAndRecord(elapsed, false);
        return;
    }

    // C. STOP: Sensors died
    if (!getZoneTemp().getStatus().isOk()) {
        stopAndRecord(elapsed, false);
    }
}

private void monitorHold() {
    long now = System.currentTimeMillis();
    
    if (now >= targetEventTime) {
        isHoldingForSchedule = false;
        setFormattedStatusLog("Schedule Event Time reached. Releasing to BAS.");
        debug("Hold Released: Event time arrived.");
    }
    
    if (getScheduleNextValue().getStatus().isOk() && !getScheduleNextValue().getValue()) {
        isHoldingForSchedule = false;
        setFormattedStatusLog("Schedule Next Value changed to Unoccupied. Aborting hold.");
        debug("Hold Aborted: Schedule flipped.");
    }
}

private void stopAndRecord(double actualMinutes, boolean success) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));
    
    // 1. Metrics
    setLastRunActualMinutes(new BStatusNumeric(actualMinutes));
    double predicted = getLastRunPredictedMinutes().getValue();
    double error = predicted - actualMinutes;
    setLastRunErrorMinutes(new BStatusNumeric(error));
    
    double pct = (actualMinutes > 0) ? (error / actualMinutes) * 100.0 : 0.0;
    setLastRunErrorPercent(new BStatusNumeric(pct));
    
    debug(String.format("Run Finished. Actual=%.1f, Pred=%.1f, Err=%.1f (%.1f%%). Success=%b", 
          actualMinutes, predicted, error, pct, success));
    
    // 2. Learning
    double zoneStart = getZoneTempAtStart().getValue();
    double zoneEnd = getZoneTemp().getValue();
    double tempChange = Math.abs(zoneEnd - zoneStart);
    double oatStart = getOutdoorTempAtStart().getValue();

    if (success && actualMinutes > 5.0 && tempChange > 1.0) {
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        double rate = tempChange / actualMinutes;

        // Update Baseline (Memory)
        if (mode.equals("HEAT")) {
            setDegreesPerMinuteHeat(new BStatusNumeric(rate));
            lastHeatBaselineMinutes = actualMinutes;
            if (!Double.isNaN(oatStart)) lastHeatBaselineOat = oatStart;
        } else {
            setDegreesPerMinuteCool(new BStatusNumeric(rate));
            lastCoolBaselineMinutes = actualMinutes;
            if (!Double.isNaN(oatStart)) lastCoolBaselineOat = oatStart;
        }
        setFormattedStatusLog("Learning updated. Mode: " + mode + ", New Baseline: " + round1(actualMinutes) + "m @ " + round1(oatStart) + "°");
        debug("Learning Saved: New Baseline established for " + mode);
        
        // 3. ENTER HOLD if finished early
        long now = System.currentTimeMillis();
        if (now < targetEventTime) {
            isHoldingForSchedule = true;
            setFormattedStatusLog("Finished early. Holding Command until Schedule Event.");
            debug("Entering HOLD state.");
        }
    } else {
        setFormattedStatusLog("Run finished. No learning (Timeout or Short Run).");
        // Safe Hold even if no learning
        if (success && System.currentTimeMillis() < targetEventTime) {
             isHoldingForSchedule = true;
        }
    }
}

private void resetModelToDefaults() {
    lastHeatBaselineMinutes = 30.0;
    lastHeatBaselineOat     = 20.0;
    lastCoolBaselineMinutes = 30.0;
    lastCoolBaselineOat     = 85.0;
    setDegreesPerMinuteHeat(new BStatusNumeric(0.1));
    setDegreesPerMinuteCool(new BStatusNumeric(0.1));
    setHeatOatMinutesAdder(new BStatusNumeric(0.0));
    setCoolOatMinutesAdder(new BStatusNumeric(0.0));
    setFormattedStatusLog("Model reset to factory defaults.");
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private void setFormattedStatusLog(String msg) {
    getStatusLog().setValue(msg);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) return;
    double tol = 0.5;
    if (getTempTolerance().getStatus().isOk()) tol = getTempTolerance().getValue();
    double diff = Math.abs(getZoneTemp().getValue() - getTargetZoneTempSetpoint().getValue());
    setZoneAtTempTolerance(new BStatusBoolean(diff <= tol));
}

private double round1(double v) {
    return Math.round(v * 10.0) / 10.0;
}
```


</details>


