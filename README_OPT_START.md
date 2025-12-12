# Optimal Start Logic

Inspired by the existing `kitControl` Optimal Start, this block is enhanced with a self-tuning algorithm based on the latest PNNL research.

The quadratic model further below draws on PNNL's research for the `Model 1` using Quadratic Regression, as detailed in the included white paper:

* **Optimal Start Control for ACs and HPs (PNNL)** — `pdf/Optimal Start Control for ACs and HPs.pdf`
    👉 [https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf](https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf)


Check for demonstrations on Vibe Coding on 📺
🎥 [**Talk Shop With Ben on YouTube**](https://www.youtube.com/@TalkShopWithBen)


Check out the **new December 2025** [YouTube playlist](https://www.youtube.com/playlist?list=PLlNmfKmNxm1tOa8P7aBhj0zf34AIlS4CQ) on optimal start/stop math and algorithms, built from short daily AI-generated lessons, plus the complete [open-source GitHub repository](https://github.com/bbartling/hvac-optimal-start-math-playground) featuring Python examples and in-depth explorations of PNNL optimal start research.

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


### Linear Degree Per Minute Optimal Start Self-Tuning Block

The linear model continuously self-tunes its heating and cooling recovery rates—specifically the learned degrees-per-minute values used to calculate how many “minutes” the system needs to condition the zone. After each successful warm-up or cool-down event, the block computes a new effective recovery rate and stores it in an N-day rolling history. These values are then blended using an Exponential Moving Average (EMA), which gives greater weight to the most recent recovery performance while still retaining long-term memory. The model evaluates whether the zone currently requires heating or cooling and automatically selects the appropriate EMA-smoothed learned rate for use in the runtime calculation.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/optimalStartSnip.png"  alt="Optimal Start Program Object" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/zoneRecoverySnip.png" alt="Recovery Trend Example" width="750">
  <br><em>Recovery trend illustrating learned cool-down rate&nbsp;≈ 0.15 °F /min</em>
</p>

---

### Inputs

| Slot | Type | Notes |
| :--- | :--- | :--- |
| `zoneTemp` | `BStatusNumeric` | Current zone temperature. |
| `targetZoneTempSetpoint` | `BStatusNumeric` | The desired occupied setpoint. |
| `outdoorAirTemp` | `BStatusNumeric` | Optional outdoor air temperature, used for logging performance history. |
| `scheduleNextValue` | `BStatusBoolean` | The occupancy value of the *next* schedule event (`true` if occupied). |
| `scheduleNextEventTime` | `BStatusNumeric` | The timestamp (in Java milliseconds) of the next schedule event. |
| `maxMinutesAllowed` | `BStatusNumeric` | Safety cap for the maximum calculated `minutesToSetpointPredicted` (default = 180 min). |
| `tempTolerance` | `BStatusNumeric` | The acceptable temperature deviation from setpoint (e.g., 1.0°F, default = 0.5°F). |
| `historyDaysToRetain` | `BStatusNumeric` | The number of recent performance records to keep for learning (default = 10). |
| `emaWeightingFactor` | `BStatusNumeric` | **(Linear Model Only)** The smoothing factor for the EMA learning algorithm (1-10, default = 2). |
| `commandOffDelaySeconds`| `BStatusNumeric`| Countdown delay in seconds that starts after the optimal start run ends to release to `null`. |
| `clearHistoryNow` | `BStatusBoolean` | A manual trigger to erase all learned performance history. |
| `printToConsoleLog` | `BStatusBoolean` | Set to `true` to enable detailed debug messages in the Niagara console. |

### Outputs

| Slot | Type | Description |
| :--- | :--- | :--- |
| `equipmentStartCommand` | `BStatusBoolean` | **The final output command; `true` when the equipment should run else `null`. **|
| `minutesToSetpointPredicted` | `BStatusNumeric` | The **live calculated prediction** of how many minutes the *next* run will take. |
| `degreesPerMinuteHeat` | `BStatusNumeric` | Active learned heating rate in °F / minute (or average rate for Quadratic). |
| `degreesPerMinuteCool` | `BStatusNumeric` | Active learned cooling rate in °F / minute (or average rate for Quadratic). |
| `currentHistoryRecordCount`| `BStatusNumeric` | The total number of HEAT and COOL performance records being stored. |
| `statusLog` | `BStatusString` | A timestamped log of the block's most recent major action. |
| `historyLog` | `BStatusString` | A multi-line string showing a dump of all performance history records. |
| `isRunning` | `BStatusBoolean` | `True` only when a learning run is actively in progress.** |
| `zoneAtTempTolerance` | `BStatusBoolean` | `True` if the current `zoneTemp` is within the tolerance of the `targetZoneTempSetpoint`. |
| `currentRunElapsedMinutes` | `BStatusNumeric` | A **live stopwatch** showing how many minutes the current run has been active. |
| `countdownToNullStatus`| `BStatusBoolean` | Returns `True` only when the off-delay countdown is active. |
| `lastRunPredictedMinutes` | `BStatusNumeric` | **(New)** The predicted time that was snapshotted at the *start* of the last run. |
| `lastRunActualMinutes` | `BStatusNumeric` | **(New)** The final, actual time it took to reach setpoint during the *last* run. |
| `lastRunErrorMinutes` | `BStatusNumeric` | **(New)** The calculated error (`Predicted - Actual`) from the *last* run. |

---

### 🔹 Linear Model — the “Straight-Line” Lesson

The **Linear** model assumes a direct relationship between how far the zone is from setpoint and how long recovery will take, based on a learned rate.

$$
\( \text{RunTime} = \frac{\text{TempDiff}}{\text{LearnedRate}_{EMA(N\text{ days})}} \)
$$

where:
* **TempDiff** = TargetSetpoint − ZoneTemp
* **LearnedRate** = The learned recovery rate (e.g., 0.15 °F / min)

---


<details>
<summary>💻 Java Code Linear Model</summary>

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
// Developer Note: For the `historyLog` feature to work, please add a new
// BStatusString slot named "historyLog" to this Program Object in Workbench.

// A static inner class to hold detailed historical performance data.
static class PerformanceRecord {
    long timestamp;
    double rate; // degrees per minute
    String mode; // "HEAT" or "COOL"
    double zoneTempStart;
    double outdoorTempStart;

    PerformanceRecord(long timestamp, double rate, String mode, double zoneTempStart, double outdoorTempStart) {
        this.timestamp = timestamp;
        this.rate = rate;
        this.mode = mode;
        this.zoneTempStart = zoneTempStart;
        this.outdoorTempStart = outdoorTempStart;
    }
}

// Member variables
private Clock.Ticket ticket;
private long startTimestamp = 0;
private boolean isOptimalStartRunning = false;
private long lastStartTriggerTimestamp = 0; 
private static final double DEFAULT_RATE_DEG_PER_MIN = 0.1;
private boolean setpointWasMetDuringRun = false;
private double minutesToReachSetpoint = 0.0;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0;

// Two separate lists to store performance history for each mode.
private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();

/**
 * Called once when the program starts. Initializes defaults.
 */
public void onStart() throws Exception {
    // Set default values for configurable parameters
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    if (getEmaWeightingFactor().isNull()) setEmaWeightingFactor(new BStatusNumeric(2.0));
    
    // Initialize output/status slots
    setIsRunning(new BStatusBoolean(false));
    // *** RENAMED ***
    setMinutesToSetpointPredicted(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    getEquipmentStartCommand().setValue(false); 
    getEquipmentStartCommand().setStatus(BStatus.NULL); 
    getStatusLog().setValue("[onStart] Optimal Start block initialized.");
    
    // *** ADDED: Initialize new slots ***
    setLastRunPredictedMinutes(new BStatusNumeric(0.0));
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setCurrentRunElapsedMinutes(new BStatusNumeric(0.0));
    
    // Initialize history log and update model
    updateHistoryLog(); 
    updateModel();
    setZoneAtTempTolerance(new BStatusBoolean(false)); 
    
    updateTimer();
}

/**
 * Main execution loop, called periodically by the timer.
 * REVISED to act as a master state controller.
 */
public void onExecute() throws Exception {
    updateTimer(); 

    updateZoneAtTempTolerance();

    if (getClearHistoryNow().getValue()) {
        clearHistory();
        setClearHistoryNow(new BStatusBoolean(false));
    }

    // --- REVISED: Explicit State-Based Logic ---
    if (isOptimalStartRunning) {
        // STATE 1: ACTIVE RUN
        // The ONLY logic that can stop the run is inside monitorActiveRun.
        monitorActiveRun();

        // As a safeguard, force the command to stay ON during the run.
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);

    } else {
        // STATE 2: NOT RUNNING (Idle, Estimating, or in Off-Delay)
        // Only run the estimate and start-command logic when not in an active run.
        updateIdleEstimate();
        updateEquipmentStartCommand();
    }

    // Optional debug tracing remains the same
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Debug] ---");
        System.out.println("isOptimalStartRunning: " + isOptimalStartRunning);
        System.out.println("isOffDelayActive: " + isOffDelayActive);
        System.out.println("setpointWasMetDuringRun: " + setpointWasMetDuringRun);
        // *** RENAMED ***
        System.out.println("minutesToSetpointPredicted (estimate): " + round1(getMinutesToSetpointPredicted().getValue()));
        System.out.println("equipmentStartCommand: " + getEquipmentStartCommand().getValue() + " (Status: " + getEquipmentStartCommand().getStatus() + ")");
        System.out.println("-----------------");
    }
}

/**
 * Called once when the program is stopped.
 */
public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

/**
 * This method now ONLY handles starting a new run or managing the off-delay.
 * It is no longer called when a run is active.
 */
private void updateEquipmentStartCommand() {
    // --- Off-Delay Timer Management ---
    if (isOffDelayActive) {
        long elapsedSeconds = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delayDuration = 60; // Default 60s
        if (getCommandOffDelaySeconds().getStatus().isOk()) {
            delayDuration = (long) getCommandOffDelaySeconds().getValue();
        }

        if (elapsedSeconds >= delayDuration) {
            // Timer has expired.
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false); 
            setFormattedStatusLog("Off-delay expired. Command released to NULL.");
        } else {
            // Timer is still running.
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Command off-delay active. " + (delayDuration - elapsedSeconds) + "s remaining.");
        }
        return; // Skip all other logic while timer is active.
    }

    // --- Standard Start/Stop Logic (Sensor check removed as it's handled elsewhere) ---
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        getCountdownToNullStatus().setValue(false);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    boolean startConditionMet = false;

    // --- Start Condition Logic (is now only evaluated when a run is not active) ---
    if (isNextPeriodOccupied) { // No longer need !isOptimalStartRunning check here
        long currentTime = System.currentTimeMillis();
        long nextEventTime = (long) getScheduleNextEventTime().getValue();
        double timeToNextMinutes = (nextEventTime - currentTime) / 60000.0;
        if (timeToNextMinutes < 0) timeToNextMinutes = 0;
        
        // *** RENAMED ***
        double optimalStartMinutes = getMinutesToSetpointPredicted().getValue();

        if (optimalStartMinutes >= timeToNextMinutes) {
            startConditionMet = true;
        }
    }

    // --- Final Command Output Logic ---
    if (startConditionMet) {
        // Start the equipment.
        startOptimalStartSequence();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);
    } else {
        // The command should be OFF. Start the countdown if needed.
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Entering command off-delay countdown...");
        } else {
            getCountdownToNullStatus().setValue(false);
        }
    }
}


/**
 * Starts a new warmup/cooldown sequence.
 */
private void startOptimalStartSequence() {
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Start] Skipping: Zone temp is already within tolerance.");
        // *** RENAMED ***
        setMinutesToSetpointPredicted(new BStatusNumeric(0.0));
        return;
    }
    
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[ERROR] Cannot start: Zone Temp or Target Setpoint not available.");
        return;
    }

    // *** ADDED: Snapshot the prediction and clear last run data ***
    double prediction = getMinutesToSetpointPredicted().getValue();
    setLastRunPredictedMinutes(new BStatusNumeric(prediction));
    setLastRunActualMinutes(new BStatusNumeric(0.0)); // Clear old value
    setLastRunErrorMinutes(new BStatusNumeric(0.0));  // Clear old value

    // Reset state for the new run
    setpointWasMetDuringRun = false;
    minutesToReachSetpoint = 0.0;

    startTimestamp = System.currentTimeMillis();
    isOptimalStartRunning = true;
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    } else {
        setOutdoorTempAtStart(new BStatusNumeric(Double.NaN));
    }
    
    setFormattedStatusLog("[Start] Optimal Start sequence initiated. Predicted: " + round1(prediction) + " min.");
}

/**
 * Monitors an active warmup/cooldown run.
 */
private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsedMinutes = (now - startTimestamp) / 60000.0;

    // 1. Check if the setpoint has been met for the first time.
    if (getZoneAtTempTolerance().getValue() && !setpointWasMetDuringRun) {
        setpointWasMetDuringRun = true;
        minutesToReachSetpoint = elapsedMinutes;
        setFormattedStatusLog("[Monitor] Target met in " + round1(minutesToReachSetpoint) + " min. Stored value for final calculation.");
    }

    // 2. Handle a loss of sensor data as a hard stop.
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[Monitor] Run stopped: Lost Zone Temp or Target Setpoint.");
        stopAndRecordPerformance(elapsedMinutes);
        return;
    }

    // 3. The schedule changing state is the primary trigger to end the run.
    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    if (!isNextPeriodOccupied) {
        double finalPerformanceMinutes = setpointWasMetDuringRun ? minutesToReachSetpoint : elapsedMinutes;
        setFormattedStatusLog("[Monitor] Schedule occupied. Recording performance using " + round1(finalPerformanceMinutes) + " min.");
        stopAndRecordPerformance(finalPerformanceMinutes);
    }
    
    // This provides a live stopwatch for the user interface.
    // *** RENAMED ***
    setCurrentRunElapsedMinutes(new BStatusNumeric(elapsedMinutes));
}

/**
 * Stops the run and records its performance.
 */
private void stopAndRecordPerformance(double actualMinutes) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));

    // *** ADDED: Set final "stopwatch" and error values ***
    setCurrentRunElapsedMinutes(new BStatusNumeric(actualMinutes)); // Set final stopwatch value
    setLastRunActualMinutes(new BStatusNumeric(actualMinutes));     // Store final actual time

    // Calculate and store error
    double lastPrediction = 0.0;
    if (getLastRunPredictedMinutes().getStatus().isOk()) {
        lastPrediction = getLastRunPredictedMinutes().getValue();
    }
    double error = lastPrediction - actualMinutes;
    setLastRunErrorMinutes(new BStatusNumeric(error));


    double zoneStart = getZoneTempAtStart().getValue();
    double zoneNow = getZoneTemp().getValue();
    double delta = Math.abs(zoneNow - zoneStart);
    
    if (actualMinutes > 0.1) {
        double rate = delta / actualMinutes;
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        double outdoorStart = getOutdoorTempAtStart().getStatus().isOk() ? getOutdoorTempAtStart().getValue() : Double.NaN;
        
        // ADDED BACK: Log the performance record details
        if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
            System.out.println("[Performance Record] Recording with duration: " + round1(actualMinutes) + " min, Rate: " + round1(rate) + " deg/min, Mode: " + mode);
        }
        
        PerformanceRecord newRecord = new PerformanceRecord(System.currentTimeMillis(), rate, mode, zoneStart, outdoorStart);

        if ("HEAT".equals(mode)) {
            heatHistory.add(newRecord);
        } else {
            coolHistory.add(newRecord);
        }
        // *** MODIFIED: Log now includes the error ***
        setFormattedStatusLog("[" + mode + "] run recorded. Rate: " + round1(rate) + " deg/min (Err=" + round1(error) + "m)");
        updateModel();
    } else {
       setFormattedStatusLog("[Record] Run was too short. Performance not recorded.");
    }
}

/**
 * Updates the learned performance model using an EMA of historical data.
 */
private void updateModel() {
    pruneHistory();
    double heatRateEma = computeEmaForMode("HEAT");
    double coolRateEma = computeEmaForMode("COOL");
    setDegreesPerMinuteHeat(new BStatusNumeric(heatRateEma > 0.0 ? heatRateEma : DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(coolRateEma > 0.0 ? coolRateEma : DEFAULT_RATE_DEG_PER_MIN));
    
    // ADDED: Optional logging to show the data behind the EMA calculation
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Model Update] ---");

        // Build and print the HEAT history array
        StringBuilder heatRates = new StringBuilder("HEAT Rates (deg/min): [");
        if (heatHistory.isEmpty()) {
            heatRates.append("No history]");
        } else {
            for (int i = 0; i < heatHistory.size(); i++) {
                heatRates.append(round1(heatHistory.get(i).rate));
                if (i < heatHistory.size() - 1) {
                    heatRates.append(", ");
                }
            }
            heatRates.append("]");
        }
        System.out.println(heatRates.toString());
        System.out.println("New HEAT EMA: " + round1(heatRateEma));

        // Build and print the COOL history array
        StringBuilder coolRates = new StringBuilder("COOL Rates (deg/min): [");
        if (coolHistory.isEmpty()) {
            coolRates.append("No history]");
        } else {
            for (int i = 0; i < coolHistory.size(); i++) {
                coolRates.append(round1(coolHistory.get(i).rate));
                if (i < coolHistory.size() - 1) {
                    coolRates.append(", ");
                }
            }
            coolRates.append("]");
        }
        System.out.println(coolRates.toString());
        System.out.println("New COOL EMA: " + round1(coolRateEma));
        System.out.println("----------------------");
    }
    
    updateCurrentHistoryRecordCount();
    updateHistoryLog();
}

/**
 * Calculates and outputs the estimated time to reach setpoint when idle.
 */
private void updateIdleEstimate() {
    if (getZoneAtTempTolerance().getValue()) {
        // *** RENAMED ***
        setMinutesToSetpointPredicted(new BStatusNumeric(0.0));
        return;
    }
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMinutes = getMaxMinutesAllowed().getValue();
    double estimatedMinutes = maxMinutes;
    
    if (zone < target) { // Heating needed
        double heatRate = getDegreesPerMinuteHeat().getValue();
        if (heatRate > 0.01) estimatedMinutes = delta / heatRate;
    } else { // Cooling needed
        double coolRate = getDegreesPerMinuteCool().getValue();
        if (coolRate > 0.01) estimatedMinutes = delta / coolRate;
    }
    // *** RENAMED ***
    setMinutesToSetpointPredicted(new BStatusNumeric(Math.min(estimatedMinutes, maxMinutes)));
}

//================================================================
// --- Helper and Utility Methods ---
//================================================================

private void setFormattedStatusLog(String message) {
    String lastTriggerTimeStr = "never";
    if (lastStartTriggerTimestamp > 0) {
        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        lastTriggerTimeStr = sdf.format(new java.util.Date(lastStartTriggerTimestamp));
    }
    getStatusLog().setValue("[Last Trigger: " + lastTriggerTimeStr + "] " + message);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk() || getTempTolerance().isNull()) {
        setZoneAtTempTolerance(new BStatusBoolean(false));
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    
    // Read the base tolerance from the slot
    double baseTolerance = getTempTolerance().getValue(); 
    
    // Add your fixed 0.1 value to it
    double effectiveTolerance = baseTolerance + 0.1; 
    
    // Use the *effective* tolerance in the logic
    setZoneAtTempTolerance(new BStatusBoolean(Math.abs(zone - target) <= effectiveTolerance));
}

private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxRecords = (int) getHistoryDaysToRetain().getValue();
    while (heatHistory.size() > maxRecords) heatHistory.remove(0);
    while (coolHistory.size() > maxRecords) coolHistory.remove(0);
}

private void clearHistory() {
    heatHistory.clear();
    coolHistory.clear();
    updateModel();  
    setFormattedStatusLog("[History] All performance records have been cleared.");
}

private double computeEmaForMode(String mode) {
    java.util.List<PerformanceRecord> relevantHistory = "HEAT".equals(mode) ? heatHistory : coolHistory;
    if (relevantHistory.isEmpty()) return 0.0;
    double[] series = new double[relevantHistory.size()];
    for (int i = 0; i < relevantHistory.size(); i++) series[i] = relevantHistory.get(i).rate;
    return (series.length == 1) ? series[0] : computeEMA(series);
}

private double computeEMA(double[] series) {
    if (series.length == 0) return 0.0;
    double weightingFactor = 2.0;
    if (getEmaWeightingFactor().getStatus().isOk()) {
        weightingFactor = Math.max(1.0, Math.min(getEmaWeightingFactor().getValue(), 10.0));
    }
    double k = weightingFactor / (series.length + 1.0);
    double ema = series[0];
    for (int i = 1; i < series.length; i++) {
        ema = series[i] * k + ema * (1 - k);
    }
    return ema;
}

private void updateHistoryLog() {
    try {
        BStatusString historyLogSlot = (BStatusString)get("historyLog");
        if (historyLogSlot == null) return;
        StringBuilder sb = new StringBuilder();
        sb.append("--- HEAT History ---\n");
        if (heatHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : heatHistory) {
            sb.append(String.format("Rate: %.1f, ZS: %.1f, OAT: %s\n", r.rate, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        sb.append("\n--- COOL History ---\n");
        if (coolHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : coolHistory) {
            sb.append(String.format("Rate: %.1f, ZS: %.1f, OAT: %s\n", r.rate, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        historyLogSlot.setValue(sb.toString());
    } catch (Exception e) {
        System.out.println("[ERROR] Failed to update historyLog slot: " + e.getMessage());
    }
}

private void updateCurrentHistoryRecordCount() {
    setCurrentHistoryRecordCount(new BStatusNumeric(heatHistory.size() + coolHistory.size()));
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private double round1(double v) {
    if (Double.isNaN(v)) return 0.0;
    return Math.round(v * 10.0) / 10.0;
}
```


</details>


---


### 📊 Quadratic Regression Optimal Start Self-Tuning Block

The quadratic model below (PNNL Model 1 from white paper) predicts recovery time using a curved relationship between temperature difference and required runtime, expressed as a fitted quadratic equation of the form ( t = A(\Delta T^2) + B(\Delta T) + C ). When the system has little or no historical data, the block begins with default (A), (B), and (C) coefficients to provide a stable baseline. As the building completes successful warm-up or cool-down cycles, the block stores these recovery records in an N-day history and performs a quadratic regression across that dataset to continuously compute new learned coefficients. This regression process allows the model to capture diminishing-returns behavior—fast recovery when far from setpoint and slower recovery as the zone approaches target—and adapt its predictions as equipment performance, seasons, and building loads evolve. Although the internal math differs from the linear version, both models use the same slot names and wiring, making them drop-in interchangeable within Niagara Workbench.

---

### 🔸 Quadratic Model — the “Curved” Lesson

The **Quadratic** version is a smarter, drop-in upgrade that adds curvature for more realistic recovery behavior.

$$
\( \text{RunTime} = (A \times \text{TempDiff}^2) + (B \times \text{TempDiff}) + C \)
$$

This captures how systems heat or cool quickly at first but slow down as they approach setpoint (diminishing returns).

* **A** adds the curve — recovery slows as setpoint nears.  
* **B** adjusts the slope — the overall rate per degree of difference.  
* **C** is the baseline offset.  
* The **Quadratic block also maintains a similar N-day history** and uses those same stored records for self-tuning, just with a more complex regression model behind the scenes.


---


<details>
<summary>💻 Java Code Quadratic Model</summary>

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java

/*
 * =================================================================
 * Optimal Start/Stop Self-Tuning Block
 * REWRITE (v4) - Quadratic Model 1 - WITH ERROR LOGGING SLOTS
 *
 * This version implements the quadratic model from the PNNL paper:
 * t_opt = alpha_a * (deltaT^2) + alpha_b
 *
 * It learns the 'alpha_a' and 'alpha_b' parameters and stores
 * them in private member variables (not slots).
 *
 * RENAMED SLOTS for clarity:
 * - minutesToSetpoint -> minutesToSetpointPredicted
 * - warmupTimeMinutes -> currentRunElapsedMinutes
 *
 * ADDED SLOTS for performance tracking:
 * - lastRunPredictedMinutes
 * - lastRunActualMinutes
 * - lastRunErrorMinutes
 * =================================================================
 */

// A static inner class to hold raw historical performance data.
static class PerformanceRecord {
    long timestamp;
    double durationMinutes; // This is 't' (our y-value)
    double deltaT;          // This is 'deltaT' (used to calculate our x-value)
    String mode;            // "HEAT" or "COOL"
    double zoneTempStart;
    double outdoorTempStart;

    PerformanceRecord(long timestamp, double durationMinutes, double deltaT, String mode, double zoneTempStart, double outdoorTempStart) {
        this.timestamp = timestamp;
        this.durationMinutes = durationMinutes;
        this.deltaT = deltaT;
        this.mode = mode;
        this.zoneTempStart = zoneTempStart;
        this.outdoorTempStart = outdoorTempStart;
    }
}

// --- Member Variables ---
private Clock.Ticket ticket;
private long startTimestamp = 0;
private boolean isOptimalStartRunning = false;
private long lastStartTriggerTimestamp = 0; 
private boolean setpointWasMetDuringRun = false;
private double minutesToReachSetpoint = 0.0;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0;

// Default MODEL 1 parameters (if no history)
// t = 0.1 * (deltaT^2) + 5.0
private static final double DEFAULT_ALPHA_A = 0.1;
private static final double DEFAULT_ALPHA_B = 5.0;
private static final double DEFAULT_RATE_DEG_PER_MIN = 0.1; // For reference slot

// --- "Under the Hood" parameters (NOT slots) ---
private double learned_alpha_a_heat = DEFAULT_ALPHA_A;
private double learned_alpha_b_heat = DEFAULT_ALPHA_B;
private double learned_alpha_a_cool = DEFAULT_ALPHA_A;
private double learned_alpha_b_cool = DEFAULT_ALPHA_B;

// Two separate lists to store performance history for each mode.
private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();

/**
 * Called once when the program starts. Initializes defaults.
 */
public void onStart() throws Exception {
    // Set default values for configurable parameters
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    
    // Initialize output/status slots
    setIsRunning(new BStatusBoolean(false));
    // *** RENAMED ***
    setMinutesToSetpointPredicted(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    
    // Initialize REFERENCE rate slots to default
    setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));

    getEquipmentStartCommand().setValue(false); 
    getEquipmentStartCommand().setStatus(BStatus.NULL); 
    getStatusLog().setValue("[onStart] Optimal Start block (Model 1 Quadratic) initialized.");
    
    // *** ADDED: Initialize new slots ***
    setLastRunPredictedMinutes(new BStatusNumeric(0.0));
    setLastRunActualMinutes(new BStatusNumeric(0.0));
    setLastRunErrorMinutes(new BStatusNumeric(0.0));
    setCurrentRunElapsedMinutes(new BStatusNumeric(0.0));
    
    updateHistoryLog(); 
    updateModel(); // Run once on start to learn from any persisted history
    setZoneAtTempTolerance(new BStatusBoolean(false)); 
    
    updateTimer();
}

/**
 * Main execution loop, called periodically by the timer.
 * This is the master state controller.
 */
public void onExecute() throws Exception {
    updateTimer(); 

    updateZoneAtTempTolerance();

    if (getClearHistoryNow().getValue()) {
        clearHistory();
        setClearHistoryNow(new BStatusBoolean(false));
    }

    if (isOptimalStartRunning) {
        // STATE 1: ACTIVE RUN
        monitorActiveRun();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);

    } else {
        // STATE 2: NOT RUNNING (Idle, Estimating, or in Off-Delay)
        updateIdleEstimate();
        updateEquipmentStartCommand();
    }

    // Optional debug tracing
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Debug Model 1] ---");
        System.out.println("isOptimalStartRunning: " + isOptimalStartRunning);
        System.out.println("isOffDelayActive: " + isOffDelayActive);
        // *** RENAMED ***
        System.out.println("minutesToSetpointPredicted (estimate): " + round1(getMinutesToSetpointPredicted().getValue()));
        System.out.println("equipmentStartCommand: " + getEquipmentStartCommand().getValue() + " (Status: " + getEquipmentStartCommand().getStatus() + ")");
        System.out.println("-----------------");
    }
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

/**
 * Handles starting a new run or managing the off-delay.
 */
private void updateEquipmentStartCommand() {
    // --- Off-Delay Timer Management ---
    if (isOffDelayActive) {
        long elapsedSeconds = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delayDuration = 60; // Default 60s
        if (getCommandOffDelaySeconds().getStatus().isOk()) {
            delayDuration = (long) getCommandOffDelaySeconds().getValue();
        }

        if (elapsedSeconds >= delayDuration) {
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false); 
            setFormattedStatusLog("Off-delay expired. Command released to NULL.");
        } else {
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Command off-delay active. " + (delayDuration - elapsedSeconds) + "s remaining.");
        }
        return; // Skip all other logic while timer is active.
    }

    // --- Standard Start/Stop Logic ---
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        getCountdownToNullStatus().setValue(false);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    boolean startConditionMet = false;

    if (isNextPeriodOccupied) {
        long currentTime = System.currentTimeMillis();
        long nextEventTime = (long) getScheduleNextEventTime().getValue();
        double timeToNextMinutes = (nextEventTime - currentTime) / 60000.0;
        if (timeToNextMinutes < 0) timeToNextMinutes = 0;
        
        // *** RENAMED ***
        double optimalStartMinutes = getMinutesToSetpointPredicted().getValue();

        if (optimalStartMinutes >= timeToNextMinutes) {
            startConditionMet = true;
        }
    }

    // --- Final Command Output Logic ---
    if (startConditionMet) {
        startOptimalStartSequence();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);
    } else {
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Entering command off-delay countdown...");
        } else {
            getCountdownToNullStatus().setValue(false);
        }
    }
}


/**
 * Starts a new warmup/cooldown sequence.
 */
private void startOptimalStartSequence() {
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Start] Skipping: Zone temp is already within tolerance.");
        // *** RENAMED ***
        setMinutesToSetpointPredicted(new BStatusNumeric(0.0));
        return;
    }
    
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[ERROR] Cannot start: Zone Temp or Target Setpoint not available.");
        return;
    }

    // *** ADDED: Snapshot the prediction and clear last run data ***
    double prediction = getMinutesToSetpointPredicted().getValue();
    setLastRunPredictedMinutes(new BStatusNumeric(prediction));
    setLastRunActualMinutes(new BStatusNumeric(0.0)); // Clear old value
    setLastRunErrorMinutes(new BStatusNumeric(0.0));  // Clear old value

    setpointWasMetDuringRun = false;
    minutesToReachSetpoint = 0.0;
    startTimestamp = System.currentTimeMillis();
    isOptimalStartRunning = true;
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    } else {
        setOutdoorTempAtStart(new BStatusNumeric(Double.NaN));
    }
    
    setFormattedStatusLog("[Start] Optimal Start sequence initiated. Predicted: " + round1(prediction) + " min.");
}

/**
 * Monitors an active warmup/cooldown run.
 */
private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsedMinutes = (now - startTimestamp) / 60000.0;

    if (getZoneAtTempTolerance().getValue() && !setpointWasMetDuringRun) {
        setpointWasMetDuringRun = true;
        minutesToReachSetpoint = elapsedMinutes;
        setFormattedStatusLog("[Monitor] Target met in " + round1(minutesToReachSetpoint) + " min. Stored value.");
    }

    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[Monitor] Run stopped: Lost Zone Temp or Target Setpoint.");
        stopAndRecordPerformance(elapsedMinutes);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    if (!isNextPeriodOccupied) {
        double finalPerformanceMinutes = setpointWasMetDuringRun ? minutesToReachSetpoint : elapsedMinutes;
        setFormattedStatusLog("[Monitor] Schedule occupied. Recording performance using " + round1(finalPerformanceMinutes) + " min.");
        stopAndRecordPerformance(finalPerformanceMinutes);
    }
    
    // *** RENAMED ***
    setCurrentRunElapsedMinutes(new BStatusNumeric(elapsedMinutes));
}

/**
 * Stops the run and records its performance.
 * THIS IS MODIFIED to store (t, deltaT)
 */
private void stopAndRecordPerformance(double actualMinutes) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));

    // *** ADDED: Set final "stopwatch" and error values ***
    setCurrentRunElapsedMinutes(new BStatusNumeric(actualMinutes)); // Set final stopwatch value
    setLastRunActualMinutes(new BStatusNumeric(actualMinutes));     // Store final actual time

    // Calculate and store error
    double lastPrediction = 0.0;
    if (getLastRunPredictedMinutes().getStatus().isOk()) {
        lastPrediction = getLastRunPredictedMinutes().getValue();
    }
    double error = lastPrediction - actualMinutes;
    setLastRunErrorMinutes(new BStatusNumeric(error));


    double zoneStart = getZoneTempAtStart().getValue();
    double zoneNow = getZoneTemp().getValue();
    
    // THIS IS THE KEY: We record the duration (actualMinutes)
    // and the total temperature change achieved (deltaT).
    double deltaT_achieved = Math.abs(zoneNow - zoneStart);
    
    if (actualMinutes > 0.1 && deltaT_achieved > 0.1) {
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        double outdoorStart = getOutdoorTempAtStart().getStatus().isOk() ? getOutdoorTempAtStart().getValue() : Double.NaN;
        
        PerformanceRecord newRecord = new PerformanceRecord(
            System.currentTimeMillis(), 
            actualMinutes,  // t (duration)
            deltaT_achieved, // deltaT
            mode, 
            zoneStart, 
            outdoorStart
        );

        if ("HEAT".equals(mode)) {
            heatHistory.add(newRecord);
        } else {
            coolHistory.add(newRecord);
        }
        setFormattedStatusLog("[" + mode + "] run recorded (t=" + round1(actualMinutes) + ", dT=" + round1(deltaT_achieved) + ", Err=" + round1(error) + "m)");
        updateModel(); // Retune the model with the new data
    } else {
       setFormattedStatusLog("[Record] Run was too short or no temp change. Performance not recorded.");
    }
}

/**
 * Updates the learned performance model using LINEAR REGRESSION.
 * THIS IS THE NEW "BRAIN"
 */
private void updateModel() {
    pruneHistory();
    
    // --- 1. Tune Model 1 Parameters (Under the Hood) ---
    double[] heatAlphas = computeRegressionForMode("HEAT");
    double[] coolAlphas = computeRegressionForMode("COOL");
    
    // Store in private member variables
    this.learned_alpha_a_heat = heatAlphas[0]; // alpha_a
    this.learned_alpha_b_heat = heatAlphas[1]; // alpha_b
    this.learned_alpha_a_cool = coolAlphas[0]; // alpha_a
    this.learned_alpha_b_cool = coolAlphas[1]; // alpha_b

    // --- 2. Update EXISTING Reference Rate Slots (Visible) ---
    double avgHeatRate = computeAverageRate(heatHistory);
    double avgCoolRate = computeAverageRate(coolHistory);
    
    // Write to the slots that already exist
    setDegreesPerMinuteHeat(new BStatusNumeric(avgHeatRate > 0.0 ? avgHeatRate : DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(avgCoolRate > 0.0 ? avgCoolRate : DEFAULT_RATE_DEG_PER_MIN));
    
    // --- 3. Logging ---
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Model 1 Update] ---");
        System.out.println(String.format("HEAT Model: t = %.3f * (dT^2) + %.2f", this.learned_alpha_a_heat, this.learned_alpha_b_heat));
        System.out.println(String.format("COOL Model: t = %.3f * (dT^2) + %.2f", this.learned_alpha_a_cool, this.learned_alpha_b_cool));
        System.out.println(String.format("Writing to SLOT degreesPerMinuteHeat (Avg): %.3f", avgHeatRate));
        System.out.println(String.format("Writing to SLOT degreesPerMinuteCool (Avg): %.3f", avgCoolRate));
        System.out.println("-------------------------");
    }
    
    updateCurrentHistoryRecordCount();
    updateHistoryLog();
}

/**
 * Calculates and outputs the estimated time to reach setpoint when idle.
 * THIS IS MODIFIED to use the new quadratic model
 */
private void updateIdleEstimate() {
    if (getZoneAtTempTolerance().getValue()) {
        // *** RENAMED ***
        setMinutesToSetpointPredicted(new BStatusNumeric(0.0));
        return;
    }
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMinutes = getMaxMinutesAllowed().getValue();
    double estimatedMinutes = maxMinutes;
    
    // --- THIS IS THE "FIX" ---
    // Use the quadratic equation from Model 1
    // t_opt = alpha_a * (delta^2) + alpha_b
    
    if (zone < target) { // Heating needed
        // Read from "under the hood" member variables
        double a_h = this.learned_alpha_a_heat;
        double b_h = this.learned_alpha_b_heat;
        estimatedMinutes = (a_h * (delta * delta)) + b_h;
        
    } else { // Cooling needed
        // Read from "under the hood" member variables
        double a_c = this.learned_alpha_a_cool;
        double b_c = this.learned_alpha_b_cool;
        estimatedMinutes = (a_c * (delta * delta)) + b_c;
    }
    // --- END OF THE "FIX" ---

    // Ensure estimated time is not negative and capped
    if (estimatedMinutes < 0) estimatedMinutes = 0.0;
    // *** RENAMED ***
    setMinutesToSetpointPredicted(new BStatusNumeric(Math.min(estimatedMinutes, maxMinutes)));
}

//================================================================
// --- NEW: Regression and Rate Helpers ---
//================================================================

/**
 * Performs a Simple Linear Regression to find alpha_a and alpha_b.
 * Solves t = m*x + c, where:
 * y = t (durationMinutes)
 * x = deltaT^2
 * m = alpha_a
 * c = alpha_b
 * Returns [alpha_a, alpha_b]
 */
private double[] computeRegressionForMode(String mode) {
    java.util.List<PerformanceRecord> history = "HEAT".equals(mode) ? heatHistory : coolHistory;
    
    // Need at least 2 points to fit a line
    if (history.size() < 2) {
        return new double[] { DEFAULT_ALPHA_A, DEFAULT_ALPHA_B };
    }

    double n = history.size();
    double sum_x = 0, sum_y = 0, sum_xy = 0, sum_x_squared = 0;

    for (PerformanceRecord rec : history) {
        double x = rec.deltaT * rec.deltaT; // x = deltaT^2
        double y = rec.durationMinutes;     // y = t
        
        sum_x += x;
        sum_y += y;
        sum_xy += x * y;
        sum_x_squared += x * x;
    }

    double denominator = (n * sum_x_squared - sum_x * sum_x);
    
    // Avoid division by zero if all x values are the same
    if (Math.abs(denominator) < 0.001) {
        return new double[] { DEFAULT_ALPHA_A, DEFAULT_ALPHA_B };
    }

    // Calculate slope (alpha_a)
    double alpha_a = (n * sum_xy - sum_x * sum_y) / denominator;
    
    // Calculate intercept (alpha_b)
    double alpha_b = (sum_y - alpha_a * sum_x) / n;

    // Safety check: Don't allow negative parameters, as it makes no physical sense
    if (alpha_a < 0) alpha_a = DEFAULT_ALPHA_A;
    // A negative intercept (alpha_b) is physically possible (e.g., a time delay)
    // but we can cap it at 0.0 for safety.
    if (alpha_b < 0) alpha_b = 0.0; 

    return new double[] { alpha_a, alpha_b };
}

/**
 * Calculates the historical average rate (deg/min) for the reference slot.
 * Avg Rate = Total Degrees Changed / Total Minutes Run
 */
private double computeAverageRate(java.util.List<PerformanceRecord> history) {
    if (history.isEmpty()) {
        return 0.0;
    }
    
    double totalDeltaT = 0;
    double totalDuration = 0;
    
    for (PerformanceRecord rec : history) {
        totalDeltaT += rec.deltaT;
        totalDuration += rec.durationMinutes;
    }
    
    if (totalDuration < 0.01) {
        return 0.0; // Avoid division by zero
    }
    
    return totalDeltaT / totalDuration;
}


//================================================================
// --- Unchanged Helper and Utility Methods ---
//================================================================

private void setFormattedStatusLog(String message) {
    String lastTriggerTimeStr = "never";
    if (lastStartTriggerTimestamp > 0) {
        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        lastTriggerTimeStr = sdf.format(new java.util.Date(lastStartTriggerTimestamp));
    }
    getStatusLog().setValue("[Last Trigger: " + lastTriggerTimeStr + "] " + message);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk() || getTempTolerance().isNull()) {
        setZoneAtTempTolerance(new BStatusBoolean(false));
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    
    // Read the base tolerance from the slot
    double baseTolerance = getTempTolerance().getValue(); 
    
    // Add your fixed 0.1 value to it
    double effectiveTolerance = baseTolerance + 0.1; 
    
    // Use the *effective* tolerance in the logic
    setZoneAtTempTolerance(new BStatusBoolean(Math.abs(zone - target) <= effectiveTolerance));
}

private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxRecords = (int) getHistoryDaysToRetain().getValue();
    while (heatHistory.size() > maxRecords) heatHistory.remove(0);
    while (coolHistory.size() > maxRecords) coolHistory.remove(0);
}

private void clearHistory() {
    heatHistory.clear();
    coolHistory.clear();
    updateModel();  
    setFormattedStatusLog("[History] All performance records have been cleared.");
}

/**
 * MODIFIED to log the new (t, deltaT) record format
 */
private void updateHistoryLog() {
    try {
        BStatusString historyLogSlot = (BStatusString)get("historyLog");
        if (historyLogSlot == null) return;
        StringBuilder sb = new StringBuilder();
        sb.append("--- HEAT History (t, dT) ---\n");
        if (heatHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : heatHistory) {
            sb.append(String.format("t: %.1f, dT: %.1f, ZS: %.1f, OAT: %s\n", r.durationMinutes, r.deltaT, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        sb.append("\n--- COOL History (t, dT) ---\n");
        if (coolHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : coolHistory) {
            sb.append(String.format("t: %.1f, dT: %.1f, ZS: %.1f, OAT: %s\n", r.durationMinutes, r.deltaT, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        historyLogSlot.setValue(sb.toString());
    } catch (Exception e) {
        System.out.println("[ERROR] Failed to update historyLog slot: " + e.getMessage());
    }
}

private void updateCurrentHistoryRecordCount() {
    setCurrentHistoryRecordCount(new BStatusNumeric(heatHistory.size() + coolHistory.size()));
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private double round1(double v) {
    if (Double.isNaN(v)) return 0.0;
    return Math.round(v * 10.0) / 10.0;
}
```

</details>

