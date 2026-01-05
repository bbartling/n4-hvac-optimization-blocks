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

### **Model 3 — Multi-Factor Weather-Compensated Model**

Model 3 blends **indoor temperature**, **outdoor air temperature**, and **historical learning** to estimate optimal start time.
It extends Model 1 by explicitly accounting for the interaction between indoor temperature deficit and outdoor conditions.

The model predicts start time as:

$$
t_{\text{pred}} = a_1(\Delta T) + a_2(\Delta T)(T_z - T_o) + a_3
$$

where:

* $\Delta T = (T_{\text{setpoint}} - T_{\text{zone,current}})$
* $T_o$ is outdoor air temperature
* $(a_1, a_2, a_3)$ are continuously self-tuned parameters learned from past day performance

Meaning:

* Larger zone deficit → longer start time
* Greater difference between zone temperature and outdoor temperature → adjusts runtime based on weather exposure
* The algorithm **self-biases** each day based on how accurate yesterday’s prediction was

This model is best for zones where both:

* Thermal mass matters, **and**
* Outdoor temperature strongly influences warm-up / cool-down behavior

---

### **Model 4 — First-Order Response / Physics-Driven Model**

Model 4 uses a **first-order thermal response model** derived from building physics instead of pure curve-fit regression.

It assumes the zone behaves like a **first-order system** and estimates the time needed to reach setpoint based on how temperature actually responds after unit startup.

Optimal start time is computed using:

$$
t_{\text{pred}} =
\frac{\ln\left(\frac{\alpha_{a}}{\alpha_{b}}\right)}
{\ln(\alpha_{c})}
$$

where:

* $\alpha_a$ – acceptable temperature tolerance band (deadband)
* $\alpha_b$ – **initial temperature difference** between zone and setpoint
* $\alpha_c$ – **dynamic system response factor**, continuously updated using least-squares learning from historical recovery curves

Interpretation:

* **Larger initial temperature gap → longer runtime**
* **Stronger system response → shorter runtime**
* Updates continuously as equipment and weather change

Model 4 is powerful because it:

* Adapts automatically to aging equipment
* Learns real thermal behavior
* Handles changing load patterns
* Requires less hand-tuning than pure regression

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


## Updated Model Readiness Table (Min Samples)

> Min Samples means number of completed runs (data points), which typically corresponds to days of data when optimal start runs once per day.

| Model   | Min Samples | Reasonable?                            |
| ------- | ----------- | -------------------------------------- |
| Model 0 | 1           | ✔ yes (EMA DPM learns immediately)     |
| Model 1 | 2           | ✔ yes (quadratic refit needs 2 points) |
| Model 2 | 1           | ✔ yes (baseline is “last good run”)    |
| Model 3 | 5           | ✔ yes (3-parameter regression)         |
| Model 4 | 3           | ✔ yes (log fit)                        |

---

## Slot Sheet (Property Dictionary) — Models 0–4 + Auto-Selection

Do not remove existing slots. This table defines the inputs, outputs, and expanded metric/tuning slots for every model.

### A. Configuration & Enable

| Slot Name                | Type             | Description                                                       |
| ------------------------ | ---------------- | ----------------------------------------------------------------- |
| `enableOptStart`         | `BStatusBoolean` | **Master enable**. If false/unusable → command forced `null`.     |
| `model1Enabled`          | `BStatusBoolean` | Enable Model 1 predictions + learning.                            |
| `model2Enabled`          | `BStatusBoolean` | Enable Model 2 predictions + learning.                            |
| `model3Enabled`          | `BStatusBoolean` | Enable Model 3 predictions + learning (needs OAT).                |
| `model4Enabled`          | `BStatusBoolean` | Enable Model 4 predictions + learning.                            |
| `maxMinutesAllowed`      | `BStatusNumeric` | Safety cap for runtime (default: 180 min).                        |
| `tempTolerance`          | `BStatusNumeric` | Acceptable deviation from setpoint (default: 0.5°).               |
| `historyDaysToRetain`    | `BStatusNumeric` | Max days of run samples to retain for Models 1/3/4 (default: 10). |
| `emaWeightingFactor`     | `BStatusNumeric` | EMA smoothing (0–1) for Model 0 learning.                         |
| `commandOffDelaySeconds` | `BStatusNumeric` | Off-delay if schedule drops while running.                        |
| `useImperialUnits`       | `BStatusBoolean` | `true`=°F ref temps; `false`=°C ref temps (Model 2).              |
| `autoModeStartDays`      | `BStatusNumeric` | Days of learning required before Auto-Selection is allowed.       |

**Model 4 Fit Controls (new / required for your code):**

| Slot Name               | Type             | Description                                    |
| ----------------------- | ---------------- | ---------------------------------------------- |
| `model4FitSteps`        | `BStatusNumeric` | Gradient steps per fit call (clamped 10–2000). |
| `model4LearningRateTau` | `BStatusNumeric` | Learning rate for τ updates.                   |
| `model4LearningRateK`   | `BStatusNumeric` | Learning rate for k updates.                   |

**Model 3 WF Reference Controls (already in your code):**

| Slot Name          | Type             | Description                          |
| ------------------ | ---------------- | ------------------------------------ |
| `model3WfRef_heat` | `BStatusNumeric` | WF normalization scalar for heating. |
| `model3WfRef_cool` | `BStatusNumeric` | WF normalization scalar for cooling. |

---

### B. Inputs (Sensors & Schedule)

| Slot Name                | Type             | Description                                                    |
| ------------------------ | ---------------- | -------------------------------------------------------------- |
| `zoneTemp`               | `BStatusNumeric` | Current zone temperature.                                      |
| `targetZoneTempSetpoint` | `BStatusNumeric` | Occupied target setpoint.                                      |
| `outdoorAirTemp`         | `BStatusNumeric` | Outdoor air temp (required for Model 2; required for Model 3). |
| `scheduleNextValue`      | `BStatusBoolean` | Next schedule value (`true` = occupied).                       |
| `scheduleNextEventTime`  | `BStatusNumeric` | Timestamp (Java ms) of next schedule change.                   |

---

### C. Outputs (Command & State)

| Slot Name                    | Type             | Description                                                 |
| ---------------------------- | ---------------- | ----------------------------------------------------------- |
| `equipmentStartCommand`      | `BStatusBoolean` | **The trigger**. `true` = run; `null` = idle.               |
| `currentModel`               | `BStatusNumeric` | Current selected best model index (0–4).                    |
| `currentModelPredictMinutes` | `BStatusNumeric` | Prediction from best model (used for start trigger).        |
| `isRunning`                  | `BStatusBoolean` | `true` while a run is active.                               |
| `currentRunElapsedMinutes`   | `BStatusNumeric` | Live elapsed minutes of the active run.                     |
| `statusLog`                  | `BStatusString`  | Human-readable last action / completion reason.             |
| `statusTrace`                | `BStatusString`  | Debug trace (validation failures, auto-select notes, etc.). |

---

### D. Per-Model Predicted Minutes (published during idle)

| Slot Name                    | Type             | Description                                  |
| ---------------------------- | ---------------- | -------------------------------------------- |
| `lastRunPredictedMinutes_m0` | `BStatusNumeric` | Model 0 predicted minutes (latest computed). |
| `lastRunPredictedMinutes_m1` | `BStatusNumeric` | Model 1 predicted minutes (latest computed). |
| `lastRunPredictedMinutes_m2` | `BStatusNumeric` | Model 2 predicted minutes (latest computed). |
| `lastRunPredictedMinutes_m3` | `BStatusNumeric` | Model 3 predicted minutes (latest computed). |
| `lastRunPredictedMinutes_m4` | `BStatusNumeric` | Model 4 predicted minutes (latest computed). |

---

### E. Per-Model Last-Run Performance Metrics (scored at run completion)

Same pattern for each model `m0..m4`:

| Slot Name                 | Type             | Description                                |
| ------------------------- | ---------------- | ------------------------------------------ |
| `lastRunActualMinutes_mX` | `BStatusNumeric` | Actual run duration in minutes.            |
| `lastRunErrorMinutes_mX`  | `BStatusNumeric` | (Predicted − Actual) minutes.              |
| `lastRunErrorPercent_mX`  | `BStatusNumeric` | % error relative to actual.                |
| `lastRunSquaredError_mX`  | `BStatusNumeric` | Squared error for last run.                |
| `avgSquaredError_mX`      | `BStatusNumeric` | Rolling EMA score used for Auto-Selection. |

Where `mX ∈ {m0,m1,m2,m3,m4}`.

---

### F. Learned Parameters (Model Coefficients / State)

**Model 0 (DPM):**

| Slot Name              | Type             | Description                             |
| ---------------------- | ---------------- | --------------------------------------- |
| `degreesPerMinuteHeat` | `BStatusNumeric` | Learned degrees/min for heating bucket. |
| `degreesPerMinuteCool` | `BStatusNumeric` | Learned degrees/min for cooling bucket. |

**Model 1 (Quadratic)** *(your code uses these renamed slots)*:

| Slot Name               | Type             | Description                             |
| ----------------------- | ---------------- | --------------------------------------- |
| `model2QuadraticA_heat` | `BStatusNumeric` | Quadratic A (heat): minutes = a·ΔT² + b |
| `model2QuadraticB_heat` | `BStatusNumeric` | Quadratic B (heat)                      |
| `model2QuadraticA_cool` | `BStatusNumeric` | Quadratic A (cool)                      |
| `model2QuadraticB_cool` | `BStatusNumeric` | Quadratic B (cool)                      |

**Model 2 (PNNL baseline memory):**

| Slot Name                   | Type             | Description                                                                                                         |
| --------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `model2HeatOatMinutesAdder` | `BStatusNumeric` | Optional “visual” minutes adjustment (heat). *(Your code zeros when disabled; actual baseline is internal memory.)* |
| `model2CoolOatMinutesAdder` | `BStatusNumeric` | Optional “visual” minutes adjustment (cool).                                                                        |

**Model 3 (Interaction regression coefficients):**

| Slot Name      | Type             | Description                           |
| -------------- | ---------------- | ------------------------------------- |
| `model3D_heat` | `BStatusNumeric` | Intercept d (heat).                   |
| `model3A_heat` | `BStatusNumeric` | Linear term a on ΔT (heat).           |
| `model3B_heat` | `BStatusNumeric` | Interaction term b on (ΔT·wf) (heat). |
| `model3D_cool` | `BStatusNumeric` | Intercept d (cool).                   |
| `model3A_cool` | `BStatusNumeric` | Linear term a on ΔT (cool).           |
| `model3B_cool` | `BStatusNumeric` | Interaction term b on (ΔT·wf) (cool). |

**Model 4 (Log fit parameters):**

| Slot Name        | Type             | Description                        |
| ---------------- | ---------------- | ---------------------------------- |
| `model4Tau_heat` | `BStatusNumeric` | τ (heat): minutes = τ·ln(1 + k·ΔT) |
| `model4K_heat`   | `BStatusNumeric` | k (heat)                           |
| `model4Tau_cool` | `BStatusNumeric` | τ (cool)                           |
| `model4K_cool`   | `BStatusNumeric` | k (cool)                           |

---




## 5. Java Code Implementation



```java
/*
============================================================
OptimalStartCombined — Models 0–4 (FINAL BLESSED VERSION)
============================================================
*/

// ==========================================================
// CONSTANTS
// ==========================================================
private static final double MIN_VALID_TEMP = -50.0;
private static final double MAX_VALID_TEMP = 250.0;
private static final long   MS_PER_DAY     = 86400000L;

// Model 1 (Quadratic) coefficient smoothing
private static final double EMA_ALPHA_M1 = 0.2;

// PNNL Model 2 reference temperatures (design conditions)
private static final double TREF_HEAT_IMP = -40.0;
private static final double TREF_HEAT_MET = -40.0;
private static final double TREF_COOL_IMP = 110.0;
private static final double TREF_COOL_MET = 43.33;

// Model 2 ratio clamps
private static final double RATIO_MIN = 0.2;
private static final double RATIO_MAX = 4.0;

// Model 3/4 history caps (bounded arrays)
private static final int MODEL3_MAX_HIST = 60;
private static final int MODEL4_MAX_HIST = 60;

// Model 3 numeric safety
private static final double DET_MIN     = 1e-9;
private static final double WF_REF_MIN = 0.1;

// Model 4 clamps
private static final double TAU_MIN = 1e-3;
private static final double K_MIN   = 1e-6;

// Rolling avg squared error EMA (same for all models)
private static final double SCORE_ALPHA = 0.1;

// Basic “good run” filter
private static final double MIN_GOOD_RUN_MINUTES = 5.0;
private static final double MIN_GOOD_RUN_DELTA_T = 1.0;

// ==========================================================
// STATE
// ==========================================================
private Clock.Ticket ticket;

// Run-state
private boolean isOptimalStartRunning = false;
private long    runStartTimestamp     = 0L;

// Start capture (per run)
private double  startZoneTemp         = 0.0;
private double  startSetpoint         = 0.0;
private double  deltaTAtStart         = 0.0;
private double  oatAtStart            = Double.NaN;
private boolean runModeHeatAtStart    = true;   // HEAT vs COOL decided at START only

// First run timestamp for “auto” day counting
private long firstRunTimestamp = 0L;

// Model selection
// 0..4
private int currentBestModelIndex = 0;

// Off-delay handling
private long scheduleDropTimestamp = 0L;

// ==========================================================
// MODEL 1 HISTORY (Quadratic regression) – lists
// ==========================================================
static class PerformanceRecord
{
  long   timestamp;
  double durationMinutes;
  double deltaT;

  PerformanceRecord(long ts, double mins, double dT)
  {
    this.timestamp        = ts;
    this.durationMinutes = mins;
    this.deltaT           = dT;
  }
}

private java.util.List heatHistory = new java.util.ArrayList();
private java.util.List coolHistory = new java.util.ArrayList();

// ==========================================================
// MODEL 2 “BASELINES” (memory)
// ==========================================================
private double lastHeatBaselineMinutes = 30.0;
private double lastHeatBaselineOat     = 20.0;
private double lastCoolBaselineMinutes = 30.0;
private double lastCoolBaselineOat     = 85.0;

// ==========================================================
// MODEL 3 HISTORY (bounded arrays)
// store (timestamp, dT, wf, minutes)
// ==========================================================
private int      m3HeatCount = 0;
private long[]   m3HeatTs    = new long[MODEL3_MAX_HIST];
private double[] m3HeatDT    = new double[MODEL3_MAX_HIST];
private double[] m3HeatWf    = new double[MODEL3_MAX_HIST];
private double[] m3HeatMin   = new double[MODEL3_MAX_HIST];

private int      m3CoolCount = 0;
private long[]   m3CoolTs    = new long[MODEL3_MAX_HIST];
private double[] m3CoolDT    = new double[MODEL3_MAX_HIST];
private double[] m3CoolWf    = new double[MODEL3_MAX_HIST];
private double[] m3CoolMin   = new double[MODEL3_MAX_HIST];

// ==========================================================
// MODEL 4 HISTORY (bounded arrays)
// store (timestamp, dT, minutes)
// ==========================================================
private int      m4HeatCount = 0;
private long[]   m4HeatTs    = new long[MODEL4_MAX_HIST];
private double[] m4HeatDT    = new double[MODEL4_MAX_HIST];
private double[] m4HeatMin   = new double[MODEL4_MAX_HIST];

private int      m4CoolCount = 0;
private long[]   m4CoolTs    = new long[MODEL4_MAX_HIST];
private double[] m4CoolDT    = new double[MODEL4_MAX_HIST];
private double[] m4CoolMin   = new double[MODEL4_MAX_HIST];

// ==========================================================
// LIFECYCLE
// ==========================================================
public void onStart() throws Exception
{
    isOptimalStartRunning = false;
    runStartTimestamp = 0L;
    scheduleDropTimestamp = 0L;
    
    // Ensure we start in a safe, non-commanding state
    forceCommandNull("Initialization");

    // Initialize the first run timer
    reschedule(15);
}

public void onExecute() throws Exception
{
    reschedule(15);

    // 1. Status Guard: Block on Fault/Down/Null/Disabled
    if (!isBoolUsable(getEnableOptStart()) || !getEnableOptStart().getValue()) {
        isOptimalStartRunning = false;
        forceCommandNull("Disabled");
        return;
    }

    if (!validateInputs()) {
        isOptimalStartRunning = false;
        forceCommandNull("Input Fault");
        return;
    }

    // 2. State Machine
    if (isOptimalStartRunning) {
        monitorActiveRun();
    } else {
        // Continuous Learning/Shadow Scoring Logic
        updateAllModelPredictionsIdle();
        updateAutoSelection();
        checkForStartTrigger();
    }
}

public void onStop() throws Exception
{
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
    forceCommandNull("Station Stop");
}

// ==========================================================
// TIMER
// ==========================================================
private void reschedule(int seconds)
{
  try
  {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(seconds), BProgram.execute, null);
  }
  catch (Exception e)
  {
    // do nothing – best effort
  }
}

// ==========================================================
// STATUS / VALIDATION HELPERS
// ==========================================================

/**
 * Shadow Scoring: Updates the squared error for ALL models
 * even if they aren't the 'winner'. This is how Auto-Mode works.
 */
private void updateMetrics(int modelIdx, double pred, double actual)
{
  double err   = pred - actual;
  double sqErr = err * err;
  double pct   = (actual > 0.0) ? (err / actual) * 100.0 : 0.0;

  // 1) Update Last Run Snapshots (Specific slots per model)
  if (modelIdx == 0)
  {
    setLastRunActualMinutes_m0(new BStatusNumeric(actual));
    setLastRunErrorMinutes_m0(new BStatusNumeric(err));
    setLastRunErrorPercent_m0(new BStatusNumeric(pct));
    setLastRunSquaredError_m0(new BStatusNumeric(sqErr));
  }
  else if (modelIdx == 1)
  {
    setLastRunActualMinutes_m1(new BStatusNumeric(actual));
    setLastRunErrorMinutes_m1(new BStatusNumeric(err));
    setLastRunErrorPercent_m1(new BStatusNumeric(pct));
    setLastRunSquaredError_m1(new BStatusNumeric(sqErr));
  }
  else if (modelIdx == 2)
  {
    setLastRunActualMinutes_m2(new BStatusNumeric(actual));
    setLastRunErrorMinutes_m2(new BStatusNumeric(err));
    setLastRunErrorPercent_m2(new BStatusNumeric(pct));
    setLastRunSquaredError_m2(new BStatusNumeric(sqErr));
  }
  else if (modelIdx == 3)
  {
    setLastRunActualMinutes_m3(new BStatusNumeric(actual));
    setLastRunErrorMinutes_m3(new BStatusNumeric(err));
    setLastRunErrorPercent_m3(new BStatusNumeric(pct));
    setLastRunSquaredError_m3(new BStatusNumeric(sqErr));
  }
  else if (modelIdx == 4)
  {
    setLastRunActualMinutes_m4(new BStatusNumeric(actual));
    setLastRunErrorMinutes_m4(new BStatusNumeric(err));
    setLastRunErrorPercent_m4(new BStatusNumeric(pct));
    setLastRunSquaredError_m4(new BStatusNumeric(sqErr));
  }

  // 2) Update Rolling Score (Auto-Selection Metric) using setters (Niagara-safe)
  double oldAvg = safeNum(getScoreSlot(modelIdx), 0.0);

  // Seeding logic: if oldAvg ~ 0, snap to current. Else EMA blend.
  double newAvg = (oldAvg <= 0.0001)
      ? sqErr
      : oldAvg + SCORE_ALPHA * (sqErr - oldAvg);

  setScoreSlot(modelIdx, newAvg);
}

// ==========================================================
// SCORE SLOT SETTER (Niagara-safe: do NOT mutate getter objects)
// ==========================================================
private void setScoreSlot(int idx, double v)
{
  BStatusNumeric bn = new BStatusNumeric(v);
  bn.setStatus(BStatus.ok);

  switch (idx)
  {
    case 1: setAvgSquaredError_m1(bn); break;
    case 2: setAvgSquaredError_m2(bn); break;
    case 3: setAvgSquaredError_m3(bn); break;
    case 4: setAvgSquaredError_m4(bn); break;
    default: setAvgSquaredError_m0(bn); break;
  }
}

private BStatusNumeric getScoreSlot(int idx) {
    switch(idx) {
        case 1: return getAvgSquaredError_m1();
        case 2: return getAvgSquaredError_m2();
        case 3: return getAvgSquaredError_m3();
        case 4: return getAvgSquaredError_m4();
        default: return getAvgSquaredError_m0();
    }
}

private void forceCommandNull(String reason) {
    getEquipmentStartCommand().setValue(false);
    getEquipmentStartCommand().setStatus(BStatus.nullStatus);
    setIsRunning(new BStatusBoolean(false));
    if (reason != null) setStatusTrace(new BStatusString("Idle: " + reason));
}

private void forceCommandTrue(String why)
{
  try
  {
    getEquipmentStartCommand().setValue(true);
    getEquipmentStartCommand().setStatus(BStatus.ok);
  }
  catch (Exception e) { /* ignore */ }

  setIsRunning(new BStatusBoolean(true));

  if (why != null && why.length() > 0)
  {
    setStatusLog(new BStatusString("equipmentStartCommand=TRUE (" + why + ")"));
  }
}

private double safeNum(BStatusNumeric s, double def) {
    return (s != null && s.getStatus().isOk()) ? s.getValue() : def;
}

private boolean isNumericUsable(BStatusNumeric n) {
    if (n == null) return false;
    BStatus s = n.getStatus();
    // Allow ALARM, block the rest
    return !(s.isFault() || s.isDown() || s.isNull() || s.isDisabled());
}

private boolean isBoolUsable(BStatusBoolean slot)
{
  if (slot == null) return false;
  BStatus s = slot.getStatus();
  if (s.isFault() || s.isDown() || s.isNull() || s.isDisabled()) return false;
  return true;
}

private double round1(double v)
{
  if (Double.isNaN(v)) return 0.0;
  return Math.round(v * 10.0) / 10.0;
}

private boolean isDataValid(BStatusNumeric slot, double min, double max)
{
  if (!isNumericUsable(slot)) return false;
  double v = slot.getValue();
  return !(v < min || v > max);
}

private void ensureNumericWiredOrNull(String slotName, BStatusNumeric point)
{
  try
  {
    if (point == null) return;
    Slot slot = getComponent().getSlot(slotName);
    if (slot == null) return;
    BLink[] links = getComponent().getLinks(slot);
    if (links == null || links.length == 0)
    {
      point.setValue(0);
      point.setStatus(BStatus.NULL);
    }
  }
  catch (Exception e)
  {
    // ignore – safety helper only
  }
}

private boolean validateInputs()
{
  // Required: zone + setpoint
  if (!isDataValid(getZoneTemp(), MIN_VALID_TEMP, MAX_VALID_TEMP))
  {
    setStatusTrace(new BStatusString("Fault: zoneTemp unusable."));
    return false;
  }
  if (!isDataValid(getTargetZoneTempSetpoint(), MIN_VALID_TEMP, MAX_VALID_TEMP))
  {
    setStatusTrace(new BStatusString("Fault: targetZoneTempSetpoint unusable."));
    return false;
  }

  // Required: schedule
  if (getScheduleNextEventTime() == null || getScheduleNextEventTime().getStatus().isNull())
  {
    setStatusTrace(new BStatusString("Fault: scheduleNextEventTime NULL"));
    return false;
  }
  if (getScheduleNextValue() == null || getScheduleNextValue().getStatus().isNull())
  {
    setStatusTrace(new BStatusString("Fault: scheduleNextValue NULL"));
    return false;
  }

  setStatusTrace(new BStatusString("OK"));
  return true;
}

// ==========================================================
// HEAT/COOL MODE DECISION (AT START ONLY)
// ==========================================================
private boolean decideHeatModeAtStart(double zone, double sp, double tol)
{
  // HEAT if zone is below setpoint minus tolerance
  if (zone < (sp - tol)) return true;

  // COOL if zone is above setpoint plus tolerance
  if (zone > (sp + tol)) return false;

  // inside tolerance — default to HEAT but caller should block start anyway
  return true;
}

// ==========================================================
// IDLE PREDICTIONS (compute all enabled model preds, then winner predicts)
// ==========================================================
private void updateAllModelPredictionsIdle()
{
  double zone = getZoneTemp().getValue();
  double sp   = getTargetZoneTempSetpoint().getValue();
  double tol  = safeNum(getTempTolerance(), 0.5);
  double maxM = safeNum(getMaxMinutesAllowed(), 180.0);

  // If within tolerance, everyone predicts 0
  if (Math.abs(sp - zone) <= tol)
  {
    setLastRunPredictedMinutes_m0(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m1(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m2(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m3(new BStatusNumeric(0.0));
    setLastRunPredictedMinutes_m4(new BStatusNumeric(0.0));
    setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
    return;
  }

  boolean isHeatNow = decideHeatModeAtStart(zone, sp, tol);
  double deltaT = Math.abs(sp - zone);

  // --- Model 0 (always available) ---
  double t0 = model0Predict(deltaT, isHeatNow);

  // --- Model 1 (Quadratic) ---
  double t1 = t0;
  if (isBoolUsable(getModel1Enabled()) && getModel1Enabled().getValue())
  {
    t1 = model1Predict(deltaT, isHeatNow);
  }

  // --- Model 2 (PNNL ratio) ---
  double t2 = t0;
  if (isBoolUsable(getModel2Enabled()) && getModel2Enabled().getValue())
  {
    double oatNow = getUsableOatOrNaN();
    t2 = model2Predict(deltaT, oatNow, isHeatNow, t0);
  }
  else
  {
    // keep “adder” visuals quiet if disabled
    setModel2HeatOatMinutesAdder(new BStatusNumeric(0.0));
    setModel2CoolOatMinutesAdder(new BStatusNumeric(0.0));
  }

  // --- Model 3 (interaction) ---
  double t3 = t0;
  if (isBoolUsable(getModel3Enabled()) && getModel3Enabled().getValue())
  {
    // requires OAT usable
    double oatNow = getUsableOatOrNaN();
    if (!Double.isNaN(oatNow))
    {
      t3 = model3Predict(deltaT, sp, oatNow, isHeatNow);
    }
    else
    {
      // no OAT => fallback to t0
      t3 = t0;
    }
  }

  // --- Model 4 (log) ---
  double t4 = t0;
  if (isBoolUsable(getModel4Enabled()) && getModel4Enabled().getValue())
  {
    t4 = model4Predict(deltaT, isHeatNow);
  }

  // clamp
  t0 = clamp(t0, 0.0, maxM);
  t1 = clamp(t1, 0.0, maxM);
  t2 = clamp(t2, 0.0, maxM);
  t3 = clamp(t3, 0.0, maxM);
  t4 = clamp(t4, 0.0, maxM);

  // publish to per-model predicted slots
  setLastRunPredictedMinutes_m0(new BStatusNumeric(t0));
  setLastRunPredictedMinutes_m1(new BStatusNumeric(t1));
  setLastRunPredictedMinutes_m2(new BStatusNumeric(t2));
  setLastRunPredictedMinutes_m3(new BStatusNumeric(t3));
  setLastRunPredictedMinutes_m4(new BStatusNumeric(t4));

  // winner chosen in updateAutoSelection(), but default if not called yet:
  double finalPred = pickPredictionByIndex(currentBestModelIndex, t0, t1, t2, t3, t4);

  setCurrentModel(new BStatusNumeric((double)currentBestModelIndex));
  setCurrentModelPredictMinutes(new BStatusNumeric(finalPred));
}

private double pickPredictionByIndex(int idx, double t0, double t1, double t2, double t3, double t4)
{
  if (idx == 1) return t1;
  if (idx == 2) return t2;
  if (idx == 3) return t3;
  if (idx == 4) return t4;
  return t0;
}

// ==========================================================
// AUTO SELECTION (based on avgSquaredError_mX)
// ==========================================================
private void updateAutoSelection()
{
  // Before any run, stick to Model 0
  if (firstRunTimestamp == 0L)
  {
    currentBestModelIndex = 0;
    setCurrentModel(new BStatusNumeric(0.0));
    return;
  }

  double daysNeeded = safeNum(getAutoModeStartDays(), 0.0);
  double daysActive = (System.currentTimeMillis() - firstRunTimestamp) / (double)MS_PER_DAY;

  // Not enough history yet => Model 0
  if (daysActive < daysNeeded)
  {
    currentBestModelIndex = 0;
    setCurrentModel(new BStatusNumeric(0.0));
    return;
  }

  // NULL/NotOK-safe reads: treat unusable scores as +infinity (not eligible)
  double bestScore = safeNum(getAvgSquaredError_m0(), Double.POSITIVE_INFINITY);
  int    bestIdx   = 0;

  if (isBoolUsable(getModel1Enabled()) && getModel1Enabled().getValue())
  {
    double s1 = safeNum(getAvgSquaredError_m1(), Double.POSITIVE_INFINITY);
    if (s1 < bestScore) { bestScore = s1; bestIdx = 1; }
  }

  if (isBoolUsable(getModel2Enabled()) && getModel2Enabled().getValue())
  {
    double s2 = safeNum(getAvgSquaredError_m2(), Double.POSITIVE_INFINITY);
    if (s2 < bestScore) { bestScore = s2; bestIdx = 2; }
  }

  if (isBoolUsable(getModel3Enabled()) && getModel3Enabled().getValue())
  {
    double s3 = safeNum(getAvgSquaredError_m3(), Double.POSITIVE_INFINITY);
    if (s3 < bestScore) { bestScore = s3; bestIdx = 3; }
  }

  if (isBoolUsable(getModel4Enabled()) && getModel4Enabled().getValue())
  {
    double s4 = safeNum(getAvgSquaredError_m4(), Double.POSITIVE_INFINITY);
    if (s4 < bestScore) { bestScore = s4; bestIdx = 4; }
  }

  currentBestModelIndex = bestIdx;
  setCurrentModel(new BStatusNumeric((double)bestIdx));

  // Optional trace for debugging
  setStatusTrace(new BStatusString(
    "AutoSelect: bestModel=" + bestIdx + " bestScore=" + round1(bestScore)
  ));
}


// ==========================================================
// RUN COMPLETION: score all models + train all models once
// (FIXED: train using deltaTAtStart)
// ==========================================================
private void completeRun(double actualMins, boolean success, String reason)
{
  isOptimalStartRunning = false;
  scheduleDropTimestamp = 0L;

  // Always drop command on completion
  forceCommandNull(success ? "Complete" : "Abort");

  if (!success)
  {
    setStatusLog(new BStatusString(
      "Run ended (no learn). reason=" + reason + " at " + round1(actualMins) + " min"
    ));
    return;
  }

  setStatusLog(new BStatusString(
    "Run complete. reason=" + reason + " actual=" + round1(actualMins) + " min. Scoring + training all models."
  ));

  // Snapshot the per-model predictions (best effort; these were published during idle)
  double p0 = safeNum(getLastRunPredictedMinutes_m0(), 0.0);
  double p1 = safeNum(getLastRunPredictedMinutes_m1(), 0.0);
  double p2 = safeNum(getLastRunPredictedMinutes_m2(), 0.0);
  double p3 = safeNum(getLastRunPredictedMinutes_m3(), 0.0);
  double p4 = safeNum(getLastRunPredictedMinutes_m4(), 0.0);

  // Score each model (squared error + rolling avg)
  updateMetrics(0, p0, actualMins);
  updateMetrics(1, p1, actualMins);
  updateMetrics(2, p2, actualMins);
  updateMetrics(3, p3, actualMins);
  updateMetrics(4, p4, actualMins);

  // IMPORTANT: Training uses deltaT AT START (stable / matches what the prediction was based on)
  double deltaTForLearn = deltaTAtStart;

  // Optional diagnostic only (not used for training)
  double endZoneTemp = getZoneTemp().getValue();
  double deltaTObserved = Math.abs(endZoneTemp - startZoneTemp);

  // Use mode at START only for bucketing (per your requirement)
  boolean isHeatBucket = runModeHeatAtStart;

  // Apply “good run” filter for learning
  boolean goodForLearn =
      (actualMins >= MIN_GOOD_RUN_MINUTES) &&
      (deltaTForLearn >= MIN_GOOD_RUN_DELTA_T);

  if (!goodForLearn)
  {
    setStatusTrace(new BStatusString(
      "Run scored but NOT learned (filter): actualMins=" + round1(actualMins) +
      " deltaTAtStart=" + round1(deltaTForLearn) +
      " deltaTObserved=" + round1(deltaTObserved)
    ));
    return;
  }

  // ----------------------------
  // Model 0 learn (degrees/min)
  // ----------------------------
  model0Learn(deltaTForLearn, actualMins, isHeatBucket);

  // ----------------------------
  // Model 1 learn (quadratic regression + EMA blend)
  // ----------------------------
  if (isBoolUsable(getModel1Enabled()) && getModel1Enabled().getValue())
  {
    model1AddAndRefit(deltaTForLearn, actualMins, isHeatBucket);
  }

  // ----------------------------
  // Model 2 learn (baseline minutes + OAT baseline)
  // ----------------------------
  if (isBoolUsable(getModel2Enabled()) && getModel2Enabled().getValue())
  {
    model2UpdateBaselines(actualMins, isHeatBucket, oatAtStart);
  }

  // ----------------------------
  // Model 3 learn (interaction regression)
  // ----------------------------
  if (isBoolUsable(getModel3Enabled()) && getModel3Enabled().getValue())
  {
    // needs OAT at start usable to compute wf
    if (!Double.isNaN(oatAtStart))
    {
      double wfObserved = model3ComputeWf(startSetpoint, oatAtStart, isHeatBucket);
      model3AddSample(System.currentTimeMillis(), isHeatBucket, deltaTForLearn, wfObserved, actualMins);
      model3PruneHistory();
      model3FitOnce(isHeatBucket);
    }
    else
    {
      setStatusTrace(new BStatusString("Model 3 learn skipped: OAT at start unusable."));
    }
  }

  // ----------------------------
  // Model 4 learn (log fit)
  // ----------------------------
  if (isBoolUsable(getModel4Enabled()) && getModel4Enabled().getValue())
  {
    model4AddSample(System.currentTimeMillis(), isHeatBucket, deltaTForLearn, actualMins);
    model4PruneHistory();
    model4FitOnce(isHeatBucket);
  }

  // Optional: let auto-selection re-evaluate immediately after learning
  updateAutoSelection();
}


// ==========================================================
// TRIGGER LOGIC
// ==========================================================
private void checkForStartTrigger()
{
  // must be “next schedule value = occupied”
  if (!isBoolUsable(getScheduleNextValue())) return;
  boolean nextIsOccupied = getScheduleNextValue().getValue();
  if (!nextIsOccupied) return;

  if (!isNumericUsable(getScheduleNextEventTime())) return;

  long nextTimeMs = (long)getScheduleNextEventTime().getValue();
  long nowMs      = System.currentTimeMillis();
  double minsUntil = (nextTimeMs - nowMs) / 60000.0;

  if (minsUntil < 0.0 || minsUntil > 1440.0) return;

  double predicted = safeNum(getCurrentModelPredictMinutes(), 0.0);

  if (predicted >= minsUntil)
  {
    startRun();
  }
}

private void startRun()
{
  double zone = getZoneTemp().getValue();
  double sp   = getTargetZoneTempSetpoint().getValue();
  double tol  = safeNum(getTempTolerance(), 0.5);

  // If we’re already basically there, do not start
  if (Math.abs(sp - zone) <= tol)
  {
    setStatusLog(new BStatusString("No start: within tolerance."));
    forceCommandNull("WithinTolerance");
    return;
  }

  isOptimalStartRunning = true;
  scheduleDropTimestamp = 0L;

  runStartTimestamp  = System.currentTimeMillis();
  startZoneTemp      = zone;
  startSetpoint      = sp;
  deltaTAtStart      = Math.abs(sp - zone);
  runModeHeatAtStart = decideHeatModeAtStart(zone, sp, tol);

  // Capture OAT at start if usable (ALARM ok, Fault/Down/Null/Disabled not)
  oatAtStart = getUsableOatOrNaN();

  if (firstRunTimestamp == 0L) firstRunTimestamp = runStartTimestamp;

  setStatusLog(new BStatusString(
    "Starting run. mode=" + (runModeHeatAtStart ? "HEAT" : "COOL") +
    " bestModel=" + currentBestModelIndex +
    " pred=" + round1(safeNum(getCurrentModelPredictMinutes(), 0.0)) + " min"
  ));

  forceCommandTrue("Start");
}

// ==========================================================
// ACTIVE RUN MONITORING + OFF-DELAY
// ==========================================================
private void monitorActiveRun()
{
  long now = System.currentTimeMillis();
  double elapsed = (now - runStartTimestamp) / 60000.0;
  setCurrentRunElapsedMinutes(new BStatusNumeric(elapsed));

  // If required points become Fault/Down/Null/Disabled mid-run => hard NULL
  if (!isDataValid(getZoneTemp(), MIN_VALID_TEMP, MAX_VALID_TEMP) ||
      !isDataValid(getTargetZoneTempSetpoint(), MIN_VALID_TEMP, MAX_VALID_TEMP))
  {
    completeRun(elapsed, false, "Mid-run input fault");
    return;
  }

  double sp   = getTargetZoneTempSetpoint().getValue();
  double zone = getZoneTemp().getValue();
  double tol  = safeNum(getTempTolerance(), 0.5);
  double dist = Math.abs(sp - zone);

  // Schedule off-delay behavior:
  // if scheduleNextValue is not usable or false while running => start delay timer, then shut down.
  if (!isBoolUsable(getScheduleNextValue()) || !getScheduleNextValue().getValue())
  {
    double offDelaySec = safeNum(getCommandOffDelaySeconds(), 0.0);
    if (offDelaySec <= 0.0)
    {
      completeRun(elapsed, false, "Schedule dropped (no delay)");
      return;
    }

    if (scheduleDropTimestamp == 0L)
    {
      scheduleDropTimestamp = now;
      setStatusTrace(new BStatusString("Schedule dropped: starting off-delay " + round1(offDelaySec) + "s"));
    }
    else
    {
      double secSinceDrop = (now - scheduleDropTimestamp) / 1000.0;
      if (secSinceDrop >= offDelaySec)
      {
        completeRun(elapsed, false, "Schedule dropped (delay elapsed)");
        return;
      }
    }
  }
  else
  {
    // schedule is good again, clear timer
    scheduleDropTimestamp = 0L;
  }

  // Success condition
  if (dist <= tol)
  {
    completeRun(elapsed, true, "Reached setpoint tolerance");
    return;
  }

  // Timeout condition
  if (elapsed >= safeNum(getMaxMinutesAllowed(), 180.0))
  {
    completeRun(elapsed, false, "Max minutes timeout");
    return;
  }
}

// ==========================================================
// MODEL 0 (Baseline DPM)
// ==========================================================
private double model0Predict(double deltaT, boolean isHeat)
{
  double rate = isHeat ? safeNum(getDegreesPerMinuteHeat(), 0.1) : safeNum(getDegreesPerMinuteCool(), 0.1);
  if (rate <= 0.001) rate = 0.1;
  return deltaT / rate;
}

private void model0Learn(double deltaTObserved, double actualMins, boolean isHeatBucket)
{
  if (actualMins <= 1.0 || deltaTObserved <= 0.1) return;

  double newRate = deltaTObserved / actualMins;
  double alpha   = safeNum(getEmaWeightingFactor(), 0.2);

  if (isHeatBucket)
  {
    double old = safeNum(getDegreesPerMinuteHeat(), 0.1);
    setDegreesPerMinuteHeat(new BStatusNumeric(old + alpha * (newRate - old)));
  }
  else
  {
    double old = safeNum(getDegreesPerMinuteCool(), 0.1);
    setDegreesPerMinuteCool(new BStatusNumeric(old + alpha * (newRate - old)));
  }
}

// ==========================================================
// MODEL 1 (Quadratic): t = a*(dT^2) + b
// NOTE: coefficients stored in your renamed slots: model2QuadraticA_*, model2QuadraticB_*
// ==========================================================
private double model1Predict(double deltaT, boolean isHeat)
{
  double a = isHeat ? safeNum(getModel2QuadraticA_heat(), 0.1) : safeNum(getModel2QuadraticA_cool(), 0.1);
  double b = isHeat ? safeNum(getModel2QuadraticB_heat(), 5.0) : safeNum(getModel2QuadraticB_cool(), 5.0);
  return (a * deltaT * deltaT) + b;
}

private void model1AddAndRefit(double deltaTObserved, double actualMins, boolean isHeatBucket)
{
  pruneHistoryLists();

  PerformanceRecord rec = new PerformanceRecord(System.currentTimeMillis(), actualMins, deltaTObserved);
  if (isHeatBucket) heatHistory.add(rec);
  else              coolHistory.add(rec);

  // Regress and EMA blend into slots
  double ema = EMA_ALPHA_M1;

  if (isHeatBucket && heatHistory.size() >= 2)
  {
    double[] obs = regressQuadratic(heatHistory); // [a,b]
    double curA = safeNum(getModel2QuadraticA_heat(), 0.1);
    double curB = safeNum(getModel2QuadraticB_heat(), 5.0);
    setModel2QuadraticA_heat(new BStatusNumeric(curA + ema * (obs[0] - curA)));
    setModel2QuadraticB_heat(new BStatusNumeric(curB + ema * (obs[1] - curB)));
  }

  if (!isHeatBucket && coolHistory.size() >= 2)
  {
    double[] obs = regressQuadratic(coolHistory);
    double curA = safeNum(getModel2QuadraticA_cool(), 0.1);
    double curB = safeNum(getModel2QuadraticB_cool(), 5.0);
    setModel2QuadraticA_cool(new BStatusNumeric(curA + ema * (obs[0] - curA)));
    setModel2QuadraticB_cool(new BStatusNumeric(curB + ema * (obs[1] - curB)));
  }

  // Optional: keep DPM “visual” aligned with retained history
  updateVisualRatesFromHistoryLists();
}

private double[] regressQuadratic(java.util.List hist)
{
  if (hist.size() < 2) return new double[] { 0.1, 5.0 };

  double n = hist.size();
  double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

  for (int i=0; i<n; i++)
  {
    PerformanceRecord r = (PerformanceRecord)hist.get(i);
    double x = r.deltaT * r.deltaT;
    double y = r.durationMinutes;
    sumX  += x;
    sumY  += y;
    sumXY += x * y;
    sumXX += x * x;
  }

  double denom = (n * sumXX) - (sumX * sumX);
  if (Math.abs(denom) < 1e-6) return new double[] { 0.1, 5.0 };

  double a = ((n * sumXY) - (sumX * sumY)) / denom;
  double b = (sumY - a * sumX) / n;

  return new double[] { a, b };
}

private void pruneHistoryLists()
{
  int maxDays = (int)safeNum(getHistoryDaysToRetain(), 10.0);
  if (maxDays <= 0) return;
  long cutoff = System.currentTimeMillis() - (maxDays * MS_PER_DAY);

  // Manual removeIf for basic java.util.List in older Java versions
  for(int i=heatHistory.size()-1; i>=0; i--) {
      PerformanceRecord r = (PerformanceRecord)heatHistory.get(i);
      if(r.timestamp < cutoff) heatHistory.remove(i);
  }
  for(int i=coolHistory.size()-1; i>=0; i--) {
      PerformanceRecord r = (PerformanceRecord)coolHistory.get(i);
      if(r.timestamp < cutoff) coolHistory.remove(i);
  }
}

private void updateVisualRatesFromHistoryLists()
{
  if (!heatHistory.isEmpty())
  {
    double totalDT = 0, totalT = 0;
    for (int i=0; i<heatHistory.size(); i++) { 
        PerformanceRecord r = (PerformanceRecord)heatHistory.get(i);
        totalDT += r.deltaT; totalT += r.durationMinutes; 
    }
    if (totalT > 0) setDegreesPerMinuteHeat(new BStatusNumeric(totalDT / totalT));
  }
  if (!coolHistory.isEmpty())
  {
    double totalDT = 0, totalT = 0;
    for (int i=0; i<coolHistory.size(); i++) { 
        PerformanceRecord r = (PerformanceRecord)coolHistory.get(i);
        totalDT += r.deltaT; totalT += r.durationMinutes; 
    }
    if (totalT > 0) setDegreesPerMinuteCool(new BStatusNumeric(totalDT / totalT));
  }
}

// ==========================================================
// MODEL 2 (PNNL ratio): minutes = baselineMinutes * ratio
// ratio = |Tref - oatBase| / |Tref - oatNow|, clamped
// ==========================================================
/**
 * Model 2: The PNNL 'OAT Ratio' Model
 * Predicted = BaselineMinutes * (|Tref - OAT_at_learning| / |Tref - OAT_now|)
 */
private double model2Predict(
    double deltaT,
    double oatNow,
    boolean isHeat,
    double linearFallback)
{
    // Read slot inline (no helper method needed)
    boolean useImp = true;
    if (getUseImperialUnits() != null && isBoolUsable(getUseImperialUnits()))
        useImp = getUseImperialUnits().getValue();

    // Pick correct PNNL reference temperature
    double tRef;
    if (isHeat)
        tRef = useImp ? TREF_HEAT_IMP : TREF_HEAT_MET;
    else
        tRef = useImp ? TREF_COOL_IMP : TREF_COOL_MET;

    double oatBase  = isHeat ? lastHeatBaselineOat     : lastCoolBaselineOat;
    double baseMins = isHeat ? lastHeatBaselineMinutes : lastCoolBaselineMinutes;

    // Guard rails
    if (Double.isNaN(oatNow) || Double.isNaN(oatBase))
        return linearFallback;

    double num = Math.abs(tRef - oatBase);
    double den = Math.abs(tRef - oatNow);
    if (den < 0.5) den = 0.5;

    double ratio = num / den;
    ratio = clamp(ratio, RATIO_MIN, RATIO_MAX);

    return baseMins * ratio;
}

private void model2UpdateBaselines(double actualMins, boolean isHeatBucket, double oatStart)
{
  if (isHeatBucket)
  {
    lastHeatBaselineMinutes = actualMins;
    if (!Double.isNaN(oatStart)) lastHeatBaselineOat = oatStart;
  }
  else
  {
    lastCoolBaselineMinutes = actualMins;
    if (!Double.isNaN(oatStart)) lastCoolBaselineOat = oatStart;
  }
}

// ==========================================================
// MODEL 3: t = d + a*dT + b*(dT*wf), wf=(sp-oat)/ref
// ==========================================================
private double model3Predict(double deltaT, double sp, double oat, boolean isHeat)
{
  double d = isHeat ? safeNum(getModel3D_heat(), 0.0) : safeNum(getModel3D_cool(), 0.0);
  double a = isHeat ? safeNum(getModel3A_heat(), 0.0) : safeNum(getModel3A_cool(), 0.0);
  double b = isHeat ? safeNum(getModel3B_heat(), 0.0) : safeNum(getModel3B_cool(), 0.0);

  double wf = model3ComputeWf(sp, oat, isHeat);

  return d + (a * deltaT) + (b * (deltaT * wf));
}

private double model3ComputeWf(double sp, double oat, boolean isHeat)
{
  double ref = isHeat ? safeNum(getModel3WfRef_heat(), 1.0) : safeNum(getModel3WfRef_cool(), 1.0);
  if (Math.abs(ref) < WF_REF_MIN) ref = 1.0;
  return (sp - oat) / ref;
}

private void model3AddSample(long ts, boolean isHeat, double deltaT, double wf, double minutes)
{
  if (deltaT <= 0.0 || minutes <= 0.0) return;

  if (isHeat)
  {
    if (m3HeatCount < MODEL3_MAX_HIST)
    {
      m3HeatTs[m3HeatCount]  = ts;
      m3HeatDT[m3HeatCount]  = deltaT;
      m3HeatWf[m3HeatCount]  = wf;
      m3HeatMin[m3HeatCount] = minutes;
      m3HeatCount++;
    }
    else
    {
      shiftM3HeatLeft();
      int i = MODEL3_MAX_HIST - 1;
      m3HeatTs[i] = ts; m3HeatDT[i] = deltaT; m3HeatWf[i] = wf; m3HeatMin[i] = minutes;
    }
  }
  else
  {
    if (m3CoolCount < MODEL3_MAX_HIST)
    {
      m3CoolTs[m3CoolCount]  = ts;
      m3CoolDT[m3CoolCount]  = deltaT;
      m3CoolWf[m3CoolCount]  = wf;
      m3CoolMin[m3CoolCount] = minutes;
      m3CoolCount++;
    }
    else
    {
      shiftM3CoolLeft();
      int i = MODEL3_MAX_HIST - 1;
      m3CoolTs[i] = ts; m3CoolDT[i] = deltaT; m3CoolWf[i] = wf; m3CoolMin[i] = minutes;
    }
  }
}

private void model3PruneHistory()
{
  int maxDays = (int)safeNum(getHistoryDaysToRetain(), 10.0);
  if (maxDays <= 0) return;

  long cutoff = System.currentTimeMillis() - (maxDays * MS_PER_DAY);

  // compact HEAT
  int wH = 0;
  for (int i = 0; i < m3HeatCount; i++)
  {
    if (m3HeatTs[i] >= cutoff)
    {
      m3HeatTs[wH]  = m3HeatTs[i];
      m3HeatDT[wH]  = m3HeatDT[i];
      m3HeatWf[wH]  = m3HeatWf[i];
      m3HeatMin[wH] = m3HeatMin[i];
      wH++;
    }
  }
  m3HeatCount = wH;

  // compact COOL
  int wC = 0;
  for (int i = 0; i < m3CoolCount; i++)
  {
    if (m3CoolTs[i] >= cutoff)
    {
      m3CoolTs[wC]  = m3CoolTs[i];
      m3CoolDT[wC]  = m3CoolDT[i];
      m3CoolWf[wC]  = m3CoolWf[i];
      m3CoolMin[wC] = m3CoolMin[i];
      wC++;
    }
  }
  m3CoolCount = wC;
}

private void model3FitOnce(boolean isHeat)
{
  // Simple gating using autoModeStartDays
  double minDays = safeNum(getAutoModeStartDays(), 0.0);
  if (minDays > 0.0 && firstRunTimestamp != 0L)
  {
    double daysAlive = (System.currentTimeMillis() - firstRunTimestamp) / (double)MS_PER_DAY;
    if (daysAlive < minDays) return;
  }

  int n = isHeat ? m3HeatCount : m3CoolCount;
  int minSamples = 5; 
  if (n < minSamples) return;

  double[][] xtx = new double[3][3];
  double[]   xty = new double[3];

  for (int i = 0; i < n; i++)
  {
    double dT = isHeat ? m3HeatDT[i]  : m3CoolDT[i];
    double wf = isHeat ? m3HeatWf[i]  : m3CoolWf[i];
    double y  = isHeat ? m3HeatMin[i] : m3CoolMin[i];

    double x0 = 1.0;
    double x1 = dT;
    double x2 = dT * wf;

    xtx[0][0] += x0*x0;  xtx[0][1] += x0*x1;  xtx[0][2] += x0*x2;
    xtx[1][0] += x1*x0;  xtx[1][1] += x1*x1;  xtx[1][2] += x1*x2;
    xtx[2][0] += x2*x0;  xtx[2][1] += x2*x1;  xtx[2][2] += x2*x2;

    xty[0] += x0*y;
    xty[1] += x1*y;
    xty[2] += x2*y;
  }

  double det = det3(xtx);
  if (Math.abs(det) < DET_MIN) return;

  double[][] inv = inv3(xtx, det);
  if (inv == null) return;

  double d = inv[0][0]*xty[0] + inv[0][1]*xty[1] + inv[0][2]*xty[2];
  double a = inv[1][0]*xty[0] + inv[1][1]*xty[1] + inv[1][2]*xty[2];
  double b = inv[2][0]*xty[0] + inv[2][1]*xty[1] + inv[2][2]*xty[2];

  if (isHeat)
  {
    setModel3D_heat(new BStatusNumeric(d));
    setModel3A_heat(new BStatusNumeric(a));
    setModel3B_heat(new BStatusNumeric(b));
  }
  else
  {
    setModel3D_cool(new BStatusNumeric(d));
    setModel3A_cool(new BStatusNumeric(a));
    setModel3B_cool(new BStatusNumeric(b));
  }
}

private void shiftM3HeatLeft()
{
  for (int i = 1; i < MODEL3_MAX_HIST; i++)
  {
    m3HeatTs[i-1]=m3HeatTs[i]; m3HeatDT[i-1]=m3HeatDT[i]; m3HeatWf[i-1]=m3HeatWf[i]; m3HeatMin[i-1]=m3HeatMin[i];
  }
}

private void shiftM3CoolLeft()
{
  for (int i = 1; i < MODEL3_MAX_HIST; i++)
  {
    m3CoolTs[i-1]=m3CoolTs[i]; m3CoolDT[i-1]=m3CoolDT[i]; m3CoolWf[i-1]=m3CoolWf[i]; m3CoolMin[i-1]=m3CoolMin[i];
  }
}

private double det3(double[][] m)
{
  return
    m[0][0]*(m[1][1]*m[2][2] - m[1][2]*m[2][1])
  - m[0][1]*(m[1][0]*m[2][2] - m[1][2]*m[2][0])
  + m[0][2]*(m[1][0]*m[2][1] - m[1][1]*m[2][0]);
}

private double[][] inv3(double[][] m, double det)
{
  if (Math.abs(det) < DET_MIN) return null;

  double[][] a = new double[3][3];

  a[0][0] =  (m[1][1]*m[2][2] - m[1][2]*m[2][1]) / det;
  a[0][1] = -(m[0][1]*m[2][2] - m[0][2]*m[2][1]) / det;
  a[0][2] =  (m[0][1]*m[1][2] - m[0][2]*m[1][1]) / det;

  a[1][0] = -(m[1][0]*m[2][2] - m[1][2]*m[2][0]) / det;
  a[1][1] =  (m[0][0]*m[2][2] - m[0][2]*m[2][0]) / det;
  a[1][2] = -(m[0][0]*m[1][2] - m[0][2]*m[1][0]) / det;

  a[2][0] =  (m[1][0]*m[2][1] - m[1][1]*m[2][0]) / det;
  a[2][1] = -(m[0][0]*m[2][1] - m[0][1]*m[2][0]) / det;
  a[2][2] =  (m[0][0]*m[1][1] - m[0][1]*m[1][0]) / det;

  return a;
}

// ==========================================================
// MODEL 4: t = tau * ln(1 + k*dT)  (fit tau,k via gradient steps)
// ==========================================================
private double model4Predict(double deltaT, boolean isHeat)
{
  double tau = isHeat ? safeNum(getModel4Tau_heat(), 25.0) : safeNum(getModel4Tau_cool(), 25.0);
  double k   = isHeat ? safeNum(getModel4K_heat(),   0.10) : safeNum(getModel4K_cool(),   0.10);

  if (tau < TAU_MIN) tau = TAU_MIN;
  if (k   < K_MIN)   k   = K_MIN;

  double z = 1.0 + k * deltaT;
  if (z < 1e-9) z = 1e-9;

  return tau * Math.log(z);
}

private void model4AddSample(long ts, boolean isHeat, double deltaT, double minutes)
{
  if (deltaT <= 0.0 || minutes <= 0.0) return;

  if (isHeat)
  {
    if (m4HeatCount < MODEL4_MAX_HIST)
    {
      m4HeatTs[m4HeatCount]  = ts;
      m4HeatDT[m4HeatCount]  = deltaT;
      m4HeatMin[m4HeatCount] = minutes;
      m4HeatCount++;
    }
    else
    {
      shiftM4HeatLeft();
      int i = MODEL4_MAX_HIST - 1;
      m4HeatTs[i]=ts; m4HeatDT[i]=deltaT; m4HeatMin[i]=minutes;
    }
  }
  else
  {
    if (m4CoolCount < MODEL4_MAX_HIST)
    {
      m4CoolTs[m4CoolCount]  = ts;
      m4CoolDT[m4CoolCount]  = deltaT;
      m4CoolMin[m4CoolCount] = minutes;
      m4CoolCount++;
    }
    else
    {
      shiftM4CoolLeft();
      int i = MODEL4_MAX_HIST - 1;
      m4CoolTs[i]=ts; m4CoolDT[i]=deltaT; m4CoolMin[i]=minutes;
    }
  }
}

private void model4PruneHistory()
{
  int maxDays = (int)safeNum(getHistoryDaysToRetain(), 10.0);
  if (maxDays <= 0) return;

  long cutoff = System.currentTimeMillis() - (maxDays * MS_PER_DAY);

  int wH = 0;
  for (int i = 0; i < m4HeatCount; i++)
  {
    if (m4HeatTs[i] >= cutoff)
    {
      m4HeatTs[wH]=m4HeatTs[i]; m4HeatDT[wH]=m4HeatDT[i]; m4HeatMin[wH]=m4HeatMin[i];
      wH++;
    }
  }
  m4HeatCount = wH;

  int wC = 0;
  for (int i = 0; i < m4CoolCount; i++)
  {
    if (m4CoolTs[i] >= cutoff)
    {
      m4CoolTs[wC]=m4CoolTs[i]; m4CoolDT[wC]=m4CoolDT[i]; m4CoolMin[wC]=m4CoolMin[i];
      wC++;
    }
  }
  m4CoolCount = wC;
}

private void model4FitOnce(boolean isHeat)
{
  // Shared day-gate using autoModeStartDays
  double minDays = safeNum(getAutoModeStartDays(), 0.0);
  if (minDays > 0.0 && firstRunTimestamp != 0L)
  {
    double daysAlive = (System.currentTimeMillis() - firstRunTimestamp) / (double)MS_PER_DAY;
    if (daysAlive < minDays) return;
  }

  int n = isHeat ? m4HeatCount : m4CoolCount;
  int minSamples = 3; 
  if (n < minSamples) return;

  int steps = (int)safeNum(getModel4FitSteps(), 60.0);
  if (steps < 10) steps = 10;
  if (steps > 2000) steps = 2000;

  double lrTau = safeNum(getModel4LearningRateTau(), 0.001);
  double lrK   = safeNum(getModel4LearningRateK(),   0.0005);
  if (lrTau <= 0.0) lrTau = 0.001;
  if (lrK   <= 0.0) lrK   = 0.0005;

  double tau = isHeat ? safeNum(getModel4Tau_heat(), 25.0) : safeNum(getModel4Tau_cool(), 25.0);
  double k   = isHeat ? safeNum(getModel4K_heat(),   0.10) : safeNum(getModel4K_cool(),   0.10);

  if (tau < TAU_MIN) tau = 25.0;
  if (k   < K_MIN)   k   = 0.10;

  final int patience = 10;
  final double minImproveAbs = 0.01;

  double bestRmse = Double.POSITIVE_INFINITY;
  double bestTau  = tau;
  double bestK    = k;
  int noImprove = 0;

  final double GRAD_CLAMP = 1e6;

  for (int step = 0; step < steps; step++)
  {
    double gradTau = 0.0, gradK = 0.0, sse = 0.0;

    for (int i = 0; i < n; i++)
    {
      double dT = isHeat ? m4HeatDT[i]  : m4CoolDT[i];
      double y  = isHeat ? m4HeatMin[i] : m4CoolMin[i];

      double z = 1.0 + k * dT;
      if (z < 1e-9) z = 1e-9;

      double yHat = tau * Math.log(z);
      double err  = yHat - y;

      sse += err * err;

      double dHat_dTau = Math.log(z);
      double dHat_dK   = tau * (dT / z);

      gradTau += 2.0 * err * dHat_dTau;
      gradK   += 2.0 * err * dHat_dK;
    }

    // clamp
    gradTau = clamp(gradTau, -GRAD_CLAMP, GRAD_CLAMP);
    gradK   = clamp(gradK,   -GRAD_CLAMP, GRAD_CLAMP);

    tau -= lrTau * gradTau;
    k   -= lrK   * gradK;

    if (tau < TAU_MIN) tau = TAU_MIN;
    if (k   < K_MIN)   k   = K_MIN;

    double rmse = Math.sqrt(sse / (double)n);

    if ((bestRmse - rmse) >= minImproveAbs)
    {
      bestRmse = rmse;
      bestTau  = tau;
      bestK    = k;
      noImprove = 0;
    }
    else
    {
      noImprove++;
      if (noImprove >= patience) break;
    }
  }

  tau = bestTau;
  k   = bestK;

  if (isHeat)
  {
    setModel4Tau_heat(new BStatusNumeric(tau));
    setModel4K_heat(new BStatusNumeric(k));
  }
  else
  {
    setModel4Tau_cool(new BStatusNumeric(tau));
    setModel4K_cool(new BStatusNumeric(k));
  }
}

private void shiftM4HeatLeft()
{
  for (int i = 1; i < MODEL4_MAX_HIST; i++)
  {
    m4HeatTs[i-1]=m4HeatTs[i]; m4HeatDT[i-1]=m4HeatDT[i]; m4HeatMin[i-1]=m4HeatMin[i];
  }
}

private void shiftM4CoolLeft()
{
  for (int i = 1; i < MODEL4_MAX_HIST; i++)
  {
    m4CoolTs[i-1]=m4CoolTs[i]; m4CoolDT[i-1]=m4CoolDT[i]; m4CoolMin[i-1]=m4CoolMin[i];
  }
}

private double getUsableOatOrNaN()
{
  if (getOutdoorAirTemp() == null) return Double.NaN;

  BStatus s = getOutdoorAirTemp().getStatus();
  if (s.isFault() || s.isDown() || s.isNull() || s.isDisabled()) return Double.NaN;

  return getOutdoorAirTemp().getValue();
}

private double clamp(double v, double lo, double hi)
{
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}
```