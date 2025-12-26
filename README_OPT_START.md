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


## Mathematical Models


### **Model 0 — Adaptive Linear Recovery (EMA-Smoothed)**

Model 0 assumes the zone recovers at an approximately linear rate
(measured in **degrees per minute**). After each completed run, a new rate
measurement is computed:

$$
r_{\text{new}} = \frac{\left|T_{\text{zone,start}} - T_{\text{setpoint}}\right|}{t_{\text{actual}}}
$$

To avoid noisy predictions and allow the system to “learn” over time,
the recovery rate is updated using an **Exponential Moving Average** (EMA):

$$
r_{\text{EMA}}(k) = \alpha \cdot r_{\text{new}} + (1-\alpha)\cdot r_{\text{EMA}}(k-1)
$$

where:

* $\alpha$ is the learning weight (tunable)
* larger $\alpha$ → faster learning
* smaller $\alpha$ → more stability

The predicted optimal start time is then:

$$
t_{\text{pred}} = \frac{\left|T_{\text{zone,current}} - T_{\text{setpoint}}\right|}{r_{\text{EMA}}}
$$

---

### **Model 1 — Quadratic Recovery Model (Interior / Stable Zones)**

For thermally stable or interior zones, recovery behavior often follows
a **non-linear** curve. PNNL recommends fitting a quadratic model of the form:

$$
t = a\cdot(\Delta T)^2 + b\cdot(\Delta T) + c
$$

where:

* * $t = a(\Delta T)^2 + b(\Delta T) + c$
* (a, b, c) are continuously self-tuned regression coefficients
  learned from historical runs.

Thus, optimal start time becomes:

$$
t_{\text{pred}} = a\cdot(\Delta T)^2 + b\cdot(\Delta T) + c
$$

This model works best when outdoor temperature has **minimal influence**
on warm-up or cool-down behavior.

---

### **Model 2 — Weather-Sensitive Linear Model (Exterior / OAT-Driven Zones)**

For exterior or weather-exposed zones, recovery rate changes
significantly with outdoor air temperature (OAT).
Model 2 begins with a baseline Model-0 prediction:

$$
t_{\text{base}} = \frac{\left|T_{\text{zone,current}} - T_{\text{setpoint}}\right|}{r_{\text{EMA}}}
$$

Then applies a learned **OAT sensitivity ratio**:

$$
t_{\text{pred}} = t_{\text{base}} \cdot R(T_{\text{OAT}})
$$

Where the ratio function is self-tuned over time, commonly modeled as:

$$
R(T_{\text{OAT}}) = m\cdot T_{\text{OAT}} + b
$$

meaning:

* colder weather → longer recovery
* hotter weather → shorter (cooling) or longer (heating), depending on mode
* automatically adapts based on historical runtime error

---

### **Model Selection Logic**

At runtime, models are continuously evaluated and compared based on
historical prediction error:

$$
\text{Error} = t_{\text{pred}} - t_{\text{actual}}
$$

and the system dynamically favors whichever model shows superior accuracy
over recent runs.


---

## Slot Sheet (Property Dictionary)

Do not remove existing slots. This table defines the inputs, outputs, and the explicitly expanded metric slots for every model.

### A. Configuration & Enable

| Slot Name | Type | Description |
| --- | --- | --- |
| `enable` | `BStatusBoolean` | **Master enable**. If `false`, command is forced to null. |
| `maxMinutesAllowed` | `BStatusNumeric` | Safety cap for runtime (default: 180 min). |
| `tempTolerance` | `BStatusNumeric` | Acceptable deviation from setpoint (default: 0.5°). |
| `historyDaysToRetain` | `BStatusNumeric` | How many days of run data to keep for regression (default: 10). |
| `emaWeightingFactor` | `BStatusNumeric` | Smoothing factor (0.0–1.0) for learning updates. |
| `commandOffDelaySeconds` | `BStatusNumeric` | Delay before turning off command if schedule drops. |
| `useImperialUnits` | `BStatusBoolean` | `true` = °F (32/100 ref); `false` = °C (0/38 ref). |
| `autoModeStartDays` | `BStatusNumeric` | Days of learning required before Auto-Selection activates. |

### B. Inputs (Sensors & Schedule)

| Slot Name | Type | Description |
| --- | --- | --- |
| `zoneTemp` | `BStatusNumeric` | Current Zone Temperature. |
| `targetZoneTempSetpoint` | `BStatusNumeric` | Occupied Setpoint Target. |
| `outdoorAirTemp` | `BStatusNumeric` | Outdoor Air Temperature (Critical for Model 2). |
| `scheduleNextValue` | `BStatusBoolean` | The value of the *next* schedule block (true = occupied). |
| `scheduleNextEventTime` | `BStatusNumeric` | Timestamp (Java ms) of the next schedule change. |

### C. Outputs (Command & Status)

| Slot Name | Type | Description |
| --- | --- | --- |
| `equipmentStartCommand` | `BStatusBoolean` | **The Trigger.** `true` = Run; `null` = Idle. |
| `currentModel` | `BStatusNumeric` | The currently selected "Best" model (0, 1, or 2). |
| `currentModelPredictMinutes` | `BStatusNumeric` | The prediction from the "Best" model (used for trigger). |
| `statusLog` | `BStatusString` | Human-readable log of last action. |
| `statusTrace` | `BStatusString` | Debugging trace (input validation/faults). |
| `isRunning` | `BStatusBoolean` | `true` while the optimal start run is active. |
| `currentRunElapsedMinutes` | `BStatusNumeric` | Live counter of current run duration. |

### D. Model 0 (Baseline) Performance Metrics

*Hard-coded slots for the Baseline Degree-Per-Minute Model.*

| Slot Name | Type | Description |
| --- | --- | --- |
| `lastRunPredictedMinutes_m0` | `BStatusNumeric` | What Model 0 predicted for the last run. |
| `lastRunActualMinutes_m0` | `BStatusNumeric` | Actual duration of the last run. |
| `lastRunErrorMinutes_m0` | `BStatusNumeric` | Difference (Predicted - Actual). |
| `lastRunErrorPercent_m0` | `BStatusNumeric` | % Error relative to actual duration. |
| `lastRunSquaredError_m0` | `BStatusNumeric` | The squared error (used for scoring). |
| `avgSquaredError_m0` | `BStatusNumeric` | **The Score.** Rolling average of squared error. |

### E. Model 1 (Quadratic) Performance Metrics

*Hard-coded slots for the PNNL Quadratic Model.*

| Slot Name | Type | Description |
| --- | --- | --- |
| `lastRunPredictedMinutes_m1` | `BStatusNumeric` | What Model 1 predicted for the last run. |
| `lastRunActualMinutes_m1` | `BStatusNumeric` | Actual duration of the last run. |
| `lastRunErrorMinutes_m1` | `BStatusNumeric` | Difference (Predicted - Actual). |
| `lastRunErrorPercent_m1` | `BStatusNumeric` | % Error relative to actual duration. |
| `lastRunSquaredError_m1` | `BStatusNumeric` | The squared error (used for scoring). |
| `avgSquaredError_m1` | `BStatusNumeric` | **The Score.** Rolling average of squared error. |

### F. Model 2 (Linear + OAT) Performance Metrics

*Hard-coded slots for the Weather Compensated Model.*

| Slot Name | Type | Description |
| --- | --- | --- |
| `lastRunPredictedMinutes_m2` | `BStatusNumeric` | What Model 2 predicted for the last run. |
| `lastRunActualMinutes_m2` | `BStatusNumeric` | Actual duration of the last run. |
| `lastRunErrorMinutes_m2` | `BStatusNumeric` | Difference (Predicted - Actual). |
| `lastRunErrorPercent_m2` | `BStatusNumeric` | % Error relative to actual duration. |
| `lastRunSquaredError_m2` | `BStatusNumeric` | The squared error (used for scoring). |
| `avgSquaredError_m2` | `BStatusNumeric` | **The Score.** Rolling average of squared error. |

### G. Learned Parameters (Internal Math)

| Slot Name | Type | Description |
| --- | --- | --- |
| `degreesPerMinuteHeat` | `BStatusNumeric` | Learned rate for Model 0 (Heating). |
| `degreesPerMinuteCool` | `BStatusNumeric` | Learned rate for Model 0 (Cooling). |
| `quadraticA_heat` | `BStatusNumeric` | Model 1 Coefficient A (Heating). |
| `quadraticB_heat` | `BStatusNumeric` | Model 1 Coefficient B (Heating). |
| `quadraticA_cool` | `BStatusNumeric` | Model 1 Coefficient A (Cooling). |
| `quadraticB_cool` | `BStatusNumeric` | Model 1 Coefficient B (Cooling). |
| `heatOatMinutesAdder` | `BStatusNumeric` | Minutes added/subtracted by OAT ratio (Heat). |
| `coolOatMinutesAdder` | `BStatusNumeric` | Minutes added/subtracted by OAT ratio (Cool). |

---

## 5. Java Code Implementation



```java
// ==========================================================
// CONSTANTS
// ==========================================================
private static final double MIN_VALID_TEMP = -50.0;
private static final double MAX_VALID_TEMP = 250.0;
private static final long   MS_PER_DAY      = 86400000L;

// Quadratic Model 1 EMA
private static final double EMA_ALPHA = 0.2;

// PNNL Model 2 reference temperatures (design conditions)
private static final double TREF_HEAT_IMP = -40.0;
private static final double TREF_HEAT_MET = -40.0;
private static final double TREF_COOL_IMP = 110.0;
private static final double TREF_COOL_MET = 43.33;

// PNNL Model 2 ratio clamps
private static final double RATIO_MIN = 0.2;
private static final double RATIO_MAX = 4.0;

// ==========================================================
// STATE
// ==========================================================
private Clock.Ticket ticket;

// Run-state
private boolean isOptimalStartRunning = false;
private long    runStartTimestamp     = 0L;
private double  startZoneTemp         = 0.0;
private double  deltaTAtStart         = 0.0;
private double  oatAtStart            = Double.NaN;
private boolean lastRunWasHeat        = true;

// Auto-mode / model selection
private long    firstRunTimestamp     = 0L;   // ms since epoch of first learning run
// 0 = Model 0 (baseline), 1 = Model 1 (quadratic), 2 = Model 2 (linear + OAT ratio)
private int     currentBestModelIndex = 0;
private boolean autoModeActive        = false;

// ==========================================================
// PNNL Quadratic Model 1 state
// ==========================================================
static class PerformanceRecord {
    long   timestamp;        // when the run finished
    double durationMinutes;  // actual warm-up minutes (y)
    double deltaT;           // |setpoint - startZoneTemp| (for this run)
    String mode;             // "HEAT" or "COOL"

    PerformanceRecord(long ts, double t, double dT, String m) {
        this.timestamp       = ts;
        this.durationMinutes = t;
        this.deltaT          = dT;
        this.mode            = m;
    }

    public String toString() {
        return String.format("[%s] dT=%.1f, mins=%.1f", mode, deltaT, durationMinutes);
    }
}

private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();

// ==========================================================
// PNNL Model 2 baselines (the "memory")
// ==========================================================
private double lastHeatBaselineMinutes = 30.0;
private double lastHeatBaselineOat     = 20.0;
private double lastCoolBaselineMinutes = 30.0;
private double lastCoolBaselineOat     = 85.0;


public void onStart() throws Exception {
  // Reset run state
  isOptimalStartRunning = false;
  runStartTimestamp     = 0L;
  startZoneTemp         = 0.0;
  deltaTAtStart         = 0.0;
  oatAtStart            = Double.NaN;

  // Initialize model metrics / slots as you already do elsewhere...
  // (avg errors, last-run mins, etc.)

  // MOST IMPORTANT: start in NULL
  forceCommandNull();

  // Start timer
  if (ticket != null) {
    ticket.cancel();
  }
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(15),   // or your cadence
      BProgram.execute,
      null
  );
}



public void onExecute() throws Exception {
  // Keep timer alive
  if (ticket != null) {
    ticket.cancel();
  }
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(15),
      BProgram.execute,
      null
  );

  // 1) Normalize unwired numeric inputs → NULL
  ensureNumericWiredOrNull("zoneTemp",              getZoneTemp());
  ensureNumericWiredOrNull("targetZoneTempSetpoint", getTargetZoneTempSetpoint());
  ensureNumericWiredOrNull("outdoorAirTemp",        getOutdoorAirTemp());

  // 2) Block enable guard (whatever your enable slot is named)
  if (getEnableOptStart() != null &&
      getEnableOptStart().getStatus().isOk() &&
      !getEnableOptStart().getValue())
  {
      // Disabled → command should disappear from the world
      isOptimalStartRunning = false;
      forceCommandNull();
      return;
  }

  // 3) Validate required inputs
  if (!validateInputs()) {
    // Bad/missing schedule or temps → NO opt start, NO hard false
    isOptimalStartRunning = false;
    forceCommandNull();

    // Optional: zero out predictions so block reads as idle
    setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m0(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m1(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m2(new BStatusNumeric(0.0));
    return;
  }

  // 4) Normal operation
  if (isOptimalStartRunning) {
    monitorActiveRun();
  } else {
    updateModelPredictions();
    checkForStartTrigger();
  }
}



// ============================================================
// Validation / wiring helpers
// ============================================================

private boolean isDataValid(BStatusNumeric slot, double min, double max)
{
  if (slot == null) return false;
  if (!slot.getStatus().isOk()) return false;
  double val = slot.getValue();
  if (val < min) return false;
  if (val > max) return false;
  return true;
}

private void ensureNumericWiredOrNull(String slotName, BStatusNumeric point)
{
  try {
    if (point == null) return;
    Slot slot = getComponent().getSlot(slotName);
    if (slot == null) return;
    BLink[] links = getComponent().getLinks(slot);
    if (links == null || links.length == 0) {
      point.setValue(0);
      point.setStatus(BStatus.NULL);
    }
  }
  catch (Exception e) {
    // ignore – safety helper only
  }
}

private boolean validateInputs()
{
  if (!isDataValid(getZoneTemp(), MIN_VALID_TEMP, MAX_VALID_TEMP)) {
    setStatusTrace(new BStatusString("Fault: Zone Temp invalid"));
    return false;
  }

  if (!isDataValid(getTargetZoneTempSetpoint(), MIN_VALID_TEMP, MAX_VALID_TEMP)) {
    setStatusTrace(new BStatusString("Fault: Setpoint invalid"));
    return false;
  }

  if (getScheduleNextEventTime() == null ||
      getScheduleNextEventTime().getStatus().isNull())
  {
    setStatusTrace(new BStatusString("Fault: scheduleNextEventTime NULL"));
    return false;
  }

  if (getScheduleNextValue() == null ||
      getScheduleNextValue().getStatus().isNull())
  {
    setStatusTrace(new BStatusString("Fault: scheduleNextValue NULL"));
    return false;
  }

  // OAT optional – just note if bad
  if (getOutdoorAirTemp() != null &&
      !getOutdoorAirTemp().getStatus().isOk())
  {
    setStatusTrace(new BStatusString("Outdoor air temp invalid – Model 2 uses linear fallback."));
  }
  else {
    setStatusTrace(new BStatusString("OK"));
  }
  return true;
}

private void forceCommandNull()
{
  getEquipmentStartCommand().setValue(false);
  getEquipmentStartCommand().setStatus(BStatus.NULL);
  setIsRunning(new BStatusBoolean(false));
}

private void forceCommandTrue()
{
  getEquipmentStartCommand().setValue(true);
  getEquipmentStartCommand().setStatus(BStatus.ok);
  setIsRunning(new BStatusBoolean(true));
}

// ============================================================
// 3-Model prediction + auto selection
// ============================================================
private void updateModelPredictions()
{
  double zone = getZoneTemp().getValue();
  double sp   = getTargetZoneTempSetpoint().getValue();
  double tol  = getTempTolerance().getValue();
  double deltaT = Math.abs(sp - zone);
  double maxMins = getMaxMinutesAllowed().getValue();

  // If within tolerance, everyone predicts 0
  if (deltaT <= tol) {
    setLastRunPredictedMinutes_m0(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m1(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m2(new BStatusNumeric(0.0));
    setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
    return;
  }

  boolean isHeat = zone < sp;

  // -------------------------------------------------
  // Model 0: baseline degrees-per-minute
  // t0 = ΔT / r
  // -------------------------------------------------
  double rate0 = isHeat ? getDegreesPerMinuteHeat().getValue()
                        : getDegreesPerMinuteCool().getValue();
  if (rate0 <= 0.001) rate0 = 0.1; // safety fallback

  double t0 = deltaT / rate0;

  // -------------------------------------------------
  // Model 1: Quadratic (PNNL)
  // t1 = a * (ΔT^2) + b
  // -------------------------------------------------
  double a1 = isHeat ? getQuadraticA_heat().getValue()
                     : getQuadraticA_cool().getValue();
  double b1 = isHeat ? getQuadraticB_heat().getValue()
                     : getQuadraticB_cool().getValue();

  double t1 = (a1 * deltaT * deltaT) + b1;

  // -------------------------------------------------
  // Model 2: PNNL Linear + OAT ratio
  // minutes = baselineMinutes * OAT_ratio
  // where OAT_ratio = |Tref - OAT_base| / |Tref - OAT_now|
  //
  // We REUSE t0 as the "linearMinutes" fallback
  // if OAT/baselines are not usable.
  // -------------------------------------------------
  double oatNow = (getOutdoorAirTemp() != null &&
                   getOutdoorAirTemp().getStatus().isOk())
                  ? getOutdoorAirTemp().getValue()
                  : Double.NaN;

  double t2 = calculateModel2Minutes(
      isHeat ? "HEAT" : "COOL",
      deltaT,
      oatNow,
      t0    // linear fallback
  );

  // Clamp each model to [0, maxMinutesAllowed]
  t0 = Math.min(maxMins, Math.max(0.0, t0));
  t1 = Math.min(maxMins, Math.max(0.0, t1));
  t2 = Math.min(maxMins, Math.max(0.0, t2));

  // Push into the slots
  setLastRunPredictedMinutes_m0(new BStatusNumeric(t0));
  setLastRunPredictedMinutes_m1(new BStatusNumeric(t1));
  setLastRunPredictedMinutes_m2(new BStatusNumeric(t2));

  // Let auto-selection decide which one is "best"
  updateAutoSelection();

  double finalPred;
  if      (currentBestModelIndex == 1) finalPred = t1;
  else if (currentBestModelIndex == 2) finalPred = t2;
  else                                 finalPred = t0;

  setCurrentModel(new BStatusNumeric(currentBestModelIndex));
  setCurrentModelPredictMinutes(new BStatusNumeric(finalPred));
}

private void updateAutoSelection()
{
  if (firstRunTimestamp == 0L) return;

  double daysNeeded = getAutoModeStartDays().getValue();
  double daysActive = (System.currentTimeMillis() - firstRunTimestamp) / 86400000.0;

  if (daysActive < daysNeeded) {
    currentBestModelIndex = 0;
    return;
  }

  double e0 = getAvgSquaredError_m0().getValue();
  double e1 = getAvgSquaredError_m1().getValue();
  double e2 = getAvgSquaredError_m2().getValue();

  if (e1 < e0 && e1 < e2)      currentBestModelIndex = 1;
  else if (e2 < e0 && e2 < e1) currentBestModelIndex = 2;
  else                         currentBestModelIndex = 0;
}

// ============================================================
// Trigger logic – compare predicted vs time to next occupancy
// ============================================================
private void checkForStartTrigger()
{
  if (getScheduleNextValue() == null ||
      !getScheduleNextValue().getStatus().isOk())
    return;

  boolean nextIsOccupied = getScheduleNextValue().getValue();
  if (!nextIsOccupied) return;

  if (getScheduleNextEventTime() == null ||
      !getScheduleNextEventTime().getStatus().isOk())
    return;

  long nextTimeMs = (long)getScheduleNextEventTime().getValue();
  long nowMs      = System.currentTimeMillis();
  double minsUntil = (nextTimeMs - nowMs) / 60000.0;

  if (minsUntil < 0.0 || minsUntil > 1440.0) return;

  double predicted = getCurrentModelPredictMinutes().getValue();

  if (predicted >= minsUntil) {
    startRun();
  }
}

private void startRun() {
    isOptimalStartRunning = true;
    runStartTimestamp     = System.currentTimeMillis();

    // Capture start zone temp and ΔT sign
    startZoneTemp = getZoneTemp().getValue();
    double sp     = getTargetZoneTempSetpoint().getValue();
    deltaTAtStart = Math.abs(sp - startZoneTemp);
    lastRunWasHeat = (startZoneTemp < sp);

    // Capture OAT at start (for Model 2 learning)
    if (getOutdoorAirTemp() != null && getOutdoorAirTemp().getStatus().isOk()) {
        oatAtStart = getOutdoorAirTemp().getValue();
    } else {
        oatAtStart = Double.NaN;
    }

    if (firstRunTimestamp == 0L) {
        firstRunTimestamp = runStartTimestamp;
    }

    setStatusLog(new BStatusString(
      "Starting optimal start run. Model=" + currentBestModelIndex +
      " Pred=" + getCurrentModelPredictMinutes().getValue() + " min"
    ));

    forceCommandTrue();
}



// ============================================================
// Active run monitoring & learning
// ============================================================
private void monitorActiveRun()
{
  long now = System.currentTimeMillis();
  double elapsed = (now - runStartTimestamp) / 60000.0;
  setCurrentRunElapsedMinutes(new BStatusNumeric(elapsed));

  double sp   = getTargetZoneTempSetpoint().getValue();
  double zone = getZoneTemp().getValue();
  double tol  = getTempTolerance().getValue();
  double dist = Math.abs(sp - zone);

  if (dist <= tol) {
    completeRun(elapsed, true);
    return;
  }

  if (elapsed >= getMaxMinutesAllowed().getValue()) {
    completeRun(elapsed, false);
    return;
  }
}


// ============================================================
// Active run monitoring & learning
// ============================================================
private void completeRun(double actualMins, boolean success)
{
  isOptimalStartRunning = false;
  forceCommandNull();

  if (!success) {
    setStatusLog(new BStatusString("Run timeout after " + actualMins + " min."));
    return;
  }

  setStatusLog(new BStatusString("Run complete in " + actualMins + " min. Updating models."));

  // Snapshot the three model predictions used for this run
  double p0 = getLastRunPredictedMinutes_m0().getValue();
  double p1 = getLastRunPredictedMinutes_m1().getValue();
  double p2 = getLastRunPredictedMinutes_m2().getValue();

  // Update squared-error metrics for each model
  updateMetrics(0, p0, actualMins, getAvgSquaredError_m0());
  updateMetrics(1, p1, actualMins, getAvgSquaredError_m1());
  updateMetrics(2, p2, actualMins, getAvgSquaredError_m2());

  // --- Common run stats used by all models ---
  double endZoneTemp = getZoneTemp().getValue();
  double deltaT      = Math.abs(endZoneTemp - startZoneTemp);
  boolean isHeat     = (startZoneTemp < endZoneTemp);

  // -------------------------------------------------
  // Model 0: degrees-per-minute learning
  // -------------------------------------------------
  if (actualMins > 1.0 && deltaT > 0.1) {
    double newRate = deltaT / actualMins;
    double alpha   = getEmaWeightingFactor().getValue();

    if (isHeat) {
      double old = getDegreesPerMinuteHeat().getValue();
      setDegreesPerMinuteHeat(new BStatusNumeric(old + alpha * (newRate - old)));
    } else {
      double old = getDegreesPerMinuteCool().getValue();
      setDegreesPerMinuteCool(new BStatusNumeric(old + alpha * (newRate - old)));
    }
  }

  // -------------------------------------------------
  // Model 1: full quadratic regression learning
  // -------------------------------------------------
  if (actualMins > 5.0 && deltaT > 1.0) {
    String mode = isHeat ? "HEAT" : "COOL";

    PerformanceRecord rec = new PerformanceRecord(
      System.currentTimeMillis(),
      actualMins,
      deltaT,
      mode
    );

    if (mode.equals("HEAT")) heatHistory.add(rec);
    else                     coolHistory.add(rec);

    // Refit curves and EMA-blend into A/B slots
    updateModelRegression();

    setStatusLog(new BStatusString(
      "Learning updated (" + mode + "). Recalculated quadratic curve."));
  }

  // -------------------------------------------------
  // Model 2: baseline minutes + OAT baseline learning
  // (same “good run” filter as Model 1)
  // -------------------------------------------------
  if (actualMins > 5.0 && deltaT > 1.0) {
    if (isHeat) {
      lastHeatBaselineMinutes = actualMins;
      if (!Double.isNaN(oatAtStart)) {
        lastHeatBaselineOat = oatAtStart;
      }
    } else {
      lastCoolBaselineMinutes = actualMins;
      if (!Double.isNaN(oatAtStart)) {
        lastCoolBaselineOat = oatAtStart;
      }
    }
  }
}



// ============================================================
// Metrics update (squared error per model)
// ============================================================
private void updateMetrics(int modelIdx, double pred, double actual, BStatusNumeric avgSlot)
{
  double err   = pred - actual;
  double sqErr = err * err;
  double pct   = (actual > 0.0) ? (err / actual) * 100.0 : 0.0;

  if (modelIdx == 0) {
    setLastRunActualMinutes_m0 (new BStatusNumeric(actual));
    setLastRunErrorMinutes_m0  (new BStatusNumeric(err));
    setLastRunErrorPercent_m0  (new BStatusNumeric(pct));
    setLastRunSquaredError_m0  (new BStatusNumeric(sqErr));
  }
  else if (modelIdx == 1) {
    setLastRunActualMinutes_m1 (new BStatusNumeric(actual));
    setLastRunErrorMinutes_m1  (new BStatusNumeric(err));
    setLastRunErrorPercent_m1  (new BStatusNumeric(pct));
    setLastRunSquaredError_m1  (new BStatusNumeric(sqErr));
  }
  else {
    setLastRunActualMinutes_m2 (new BStatusNumeric(actual));
    setLastRunErrorMinutes_m2  (new BStatusNumeric(err));
    setLastRunErrorPercent_m2  (new BStatusNumeric(pct));
    setLastRunSquaredError_m2  (new BStatusNumeric(sqErr));
  }

  double oldAvg = avgSlot.getValue();
  double newAvg = oldAvg + 0.1 * (sqErr - oldAvg);
  avgSlot.setValue(newAvg);
}

// ============================================================
// Quadratic regression engine (Model 1)
// ============================================================
private void updateModelRegression()
{
  pruneHistory();

  double ema = getEmaWeightingFactor().getValue();
  if (ema <= 0.0 || ema > 1.0) ema = 0.2;

  // HEAT curve
  if (heatHistory.size() >= 2) {
    double[] heatParams = regress(heatHistory);
    double aHeat = getQuadraticA_heat().getValue();
    double bHeat = getQuadraticB_heat().getValue();
    aHeat = aHeat + ema * (heatParams[0] - aHeat);
    bHeat = bHeat + ema * (heatParams[1] - bHeat);
    setQuadraticA_heat(new BStatusNumeric(aHeat));
    setQuadraticB_heat(new BStatusNumeric(bHeat));
  }

  // COOL curve
  if (coolHistory.size() >= 2) {
    double[] coolParams = regress(coolHistory);
    double aCool = getQuadraticA_cool().getValue();
    double bCool = getQuadraticB_cool().getValue();
    aCool = aCool + ema * (coolParams[0] - aCool);
    bCool = bCool + ema * (coolParams[1] - bCool);
    setQuadraticA_cool(new BStatusNumeric(aCool));
    setQuadraticB_cool(new BStatusNumeric(bCool));
  }

  updateVisualRates();
}

// Ordinary least squares for y = a*x + b with x = (ΔT²)
private double[] regress(java.util.List<PerformanceRecord> history)
{
  if (history.size() < 2) return new double[] { 0.1, 5.0 };

  double n = history.size();
  double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

  for (PerformanceRecord r : history) {
    double x = r.deltaT * r.deltaT;  // ΔT²
    double y = r.durationMinutes;
    sumX  += x;
    sumY  += y;
    sumXY += x * y;
    sumXX += x * x;
  }

  double denom = (n * sumXX) - (sumX * sumX);
  if (Math.abs(denom) < 1e-6) {
    return new double[] { 0.1, 5.0 };
  }

  double a = ((n * sumXY) - (sumX * sumY)) / denom;
  double b = (sumY - a * sumX) / n;

  return new double[] { a, b };
}

private void pruneHistory()
{
  if (getHistoryDaysToRetain().isNull()) return;
  int maxDays = (int) getHistoryDaysToRetain().getValue();
  if (maxDays <= 0) return;

  long cutoff = System.currentTimeMillis() - (maxDays * 86400000L);

  heatHistory.removeIf(r -> r.timestamp < cutoff);
  coolHistory.removeIf(r -> r.timestamp < cutoff);
}

// Keep DPM slots roughly aligned with observed history
private void updateVisualRates()
{
  if (!heatHistory.isEmpty()) {
    double totalDT = 0, totalT = 0;
    for (PerformanceRecord r : heatHistory) {
      totalDT += r.deltaT;
      totalT  += r.durationMinutes;
    }
    if (totalT > 0) {
      setDegreesPerMinuteHeat(new BStatusNumeric(totalDT / totalT));
    }
  }

  if (!coolHistory.isEmpty()) {
    double totalDT = 0, totalT = 0;
    for (PerformanceRecord r : coolHistory) {
      totalDT += r.deltaT;
      totalT  += r.durationMinutes;
    }
    if (totalT > 0) {
      setDegreesPerMinuteCool(new BStatusNumeric(totalDT / totalT));
    }
  }
}

// ==========================================================
// PNNL Model 2: minutes = baselineMinutes * OAT_ratio
// OAT_ratio = |Tref - OAT_base| / |Tref - OAT_now|
// with clamping to [RATIO_MIN, RATIO_MAX]
// ==========================================================
private double calculateModel2Minutes(String mode, double delta, double oatNow, double linearMinutes) {
    boolean imperial = getUseImperialUnits().getValue();

    double tBase;
    double oatBase;
    double tRef;
    double rateFallback;

    if ("HEAT".equals(mode)) {
        tBase        = lastHeatBaselineMinutes;
        oatBase      = lastHeatBaselineOat;
        tRef         = imperial ? TREF_HEAT_IMP : TREF_HEAT_MET;
        rateFallback = getDegreesPerMinuteHeat().getValue();
    } else {
        tBase        = lastCoolBaselineMinutes;
        oatBase      = lastCoolBaselineOat;
        tRef         = imperial ? TREF_COOL_IMP : TREF_COOL_MET;
        rateFallback = getDegreesPerMinuteCool().getValue();
    }

    // Fallback: missing baselines or OAT → use simple linear model (Model 0)
    if (Double.isNaN(oatNow) || Double.isNaN(oatBase) || rateFallback <= 0.001) {
        double fallback = (linearMinutes > 0.0)
            ? linearMinutes
            : (rateFallback > 0.0 ? delta / rateFallback : 180.0);

        // Visual adder slots go to 0.0 when we’re not using OAT
        if ("HEAT".equals(mode)) setHeatOatMinutesAdder(new BStatusNumeric(0.0));
        else                     setCoolOatMinutesAdder(new BStatusNumeric(0.0));

        return fallback;
    }

    // PNNL ratio: as OAT_now approaches Tref, denominator shrinks and minutes grow
    double numerator   = Math.abs(tRef - oatBase);
    double denominator = Math.abs(tRef - oatNow);

    // Protect against divide-by-zero when today ≈ design temp
    if (denominator < 0.5) denominator = 0.5;

    double ratio = numerator / denominator;

    // Clamp ratio to sane limits
    if (ratio < RATIO_MIN) ratio = RATIO_MIN;
    if (ratio > RATIO_MAX) ratio = RATIO_MAX;

    double predicted = tBase * ratio;

    // Update visual “adder” slots
    double added = predicted - tBase;
    if ("HEAT".equals(mode)) setHeatOatMinutesAdder(new BStatusNumeric(added));
    else                     setCoolOatMinutesAdder(new BStatusNumeric(added));

    return predicted;
}
```