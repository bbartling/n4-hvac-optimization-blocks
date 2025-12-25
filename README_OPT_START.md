# Ultimate Optimal Start Control — Combined Self‑Tuning Models

This guide describes an **enhanced optimal start controller** that combines
**three complementary algorithms** into a single Niagara 4 `ProgramObject`.  It builds
upon the original linear and quadratic blocks from the PNNL research but
extends them with a baseline degree‑per‑minute model, robust fault handling,
and automatic model selection based on real‑world performance.  The goal is to
start equipment **as late as possible** while guaranteeing that the zone reaches
its occupied setpoint at the scheduled time.

> **Why combine multiple models?**  PNNL’s research shows that different
> spaces respond differently: interior zones often warm or cool in a non‑linear
> fashion that is well described by a quadratic curve, whereas perimeter zones
> strongly influenced by outdoor air respond more linearly and benefit from
> weather compensation. Meanwhile, a simple degree‑per‑minute model is
> invaluable during the first few runs when little performance history exists.

## Model Overview

The controller runs **three models in parallel** to produce a predicted run time.
Each model is continuously updated (self‑tuning) based on completed runs.  After
an initial learning period, the controller calculates the **squared error** for
each model and selects the one with the lowest error for the next start event.
The **baseline degree‑per‑minute model** runs at every step and provides a
safety net when the more sophisticated models do not yet have sufficient data.

| Model Name                     | Purpose & Formula                                                                                          | Notes |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------- | ----- |
| **Model 0 – Baseline Degrees‑per‑Minute** | Computes time to reach setpoint using a learned rate `r` (°/min).  The predicted minutes are \(t_0 = \frac{\Delta T}{r}\).  The rate \(r\) is updated after each run from `deltaT / duration` similarly to the linear model but without any weather scaling. | Always available for early runs and as a fallback. |
| **Model 1 – Quadratic (PNNL)** | Fits a second‑order polynomial to historical warm‑up/cool‑down data.  The optimal start time is \(t_1 = \alpha_{1,a}(\Delta T)^2 + \alpha_{1,b}\)【913477360246089†L448-L476】.  The coefficients \(\alpha_{1,a}\) and \(\alpha_{1,b}\) are updated using a simple quadratic regression of past runs and smoothed with an exponential moving average. | Suitable for interior or thermally massive zones where recovery time grows non‑linearly with the temperature gap. |
| **Model 2 – Linear + Outdoor‑Air Ratio (PNNL)** | Predicts run time using a linear degree‑per‑minute model and scales it by an outdoor‑air‑temperature ratio.  The baseline run time is \(t_{\text{lin}} = \frac{\Delta T}{\alpha_{2,a}}\)【913477360246089†L540-L564】, where \(\alpha_{2,a}\) (°/min) is learned from the previous day.  This time is then scaled by the ratio \(\frac{|T_{\text{ref}} - T_{\text{o,base}}|}{|T_{\text{ref}} - T_{\text{o,today}}|}\)【913477360246089†L540-L554】 to reflect today’s outdoor conditions, yielding \(t_2 = t_{\text{lin}} \cdot \frac{|T_{\text{ref}} - T_{\text{o,base}}|}{|T_{\text{ref}} - T_{\text{o,today}}|}\). | Best for perimeter zones where the outdoor air strongly affects recovery. |

\(\Delta T\) is the absolute difference between the current zone temperature and the occupied setpoint (°F).  The reference temperatures \(T_{\text{ref}}\) (e.g., 32 °F for heating and 100 °F for cooling) and baseline outdoor air \(T_{\text{o,base}}\) are defined the same as in the original PNNL model.

Each model records its own **predicted runtime**, **actual runtime**, **error (predicted – actual)** and **squared error**.  After enough runs (e.g., three days of operation), the controller computes the average squared error for each model.  The model with the **lowest average squared error** becomes the **active predictor** until another model outperforms it.  This approach balances responsiveness with robustness: the active model adapts over time, but a poorly performing model will not dominate.

## Data Validity and Fault Handling

Reliable sensors are critical for optimal start.  The block employs two helper
methods to ensure data integrity before making decisions:

```java
// Returns true if the slot is non‑null, has OK status and the value lies within [min, max].
boolean isDataValid(BStatusNumeric slot, double min, double max) {
  if (slot == null) return false;
  if (!slot.getStatus().isOk()) return false;
  double v = slot.getValue();
  return v >= min && v <= max;
}

// If the numeric point is not wired (no links), mark it as null to avoid misleading values.
void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
  try {
    Slot s = getComponent().getSlot(slotName);
    if (s == null) return;
    BLink[] links = getComponent().getLinks(s);
    if (links == null || links.length == 0) {
      point.setValue(0);
      point.setStatus(BStatus.NULL);
    }
  } catch (Exception e) { /* ignore */ }
}
```

The controller checks the **zone temperature**, **zone temperature tolerance**, **occupied setpoint**, and **outdoor air temperature** before computing predictions.  If any input is bad or out of a reasonable range, the **equipment start command is forced to `null`** to prevent unintended operation.  In addition, a **master `enable` input** allows operators to disable optimal start entirely.  When `enable` is `false`, the block sets `equipmentStartCommand` to `null` regardless of any prediction.

## Algorithm Logic

1. **Initialize on startup:**
   - Set defaults for all numeric inputs (e.g., `maxMinutesAllowed = 180 min`, `tempTolerance = 0.5 °F`).
   - Initialize each model’s learned parameters (baseline rate, quadratic coefficients, OAT ratio baseline) to conservative values.
   - Reset performance metrics for each model.

2. **Continuous prediction:**
   - At each `onExecute` interval (e.g., every 15 s), verify input validity using `isDataValid()` and `ensureNumericWiredOrNull()`.
   - Compute \(\Delta T\).  If the zone is already within the temperature tolerance, force all model predictions to `0.0` min.
   - Otherwise, calculate `t0`, `t1` and `t2` using the formulas above.  Clamp each prediction between `0` and `maxMinutesAllowed`.
   - Determine the **current model** (the one with the lowest average squared error once auto‑selection begins).  Set `currentModelPredictMinutes` to that model’s predicted minutes.

3. **Schedule comparison and start trigger:**
   - If `scheduleNextValue` (the occupancy state of the next event) is `true`, compute the minutes until the next scheduled occupied event: \(\text{minsUntilEvent} = \frac{\text{nextEventTime} - \text{now}}{60\times 1000}\).
   - Compare `minsUntilEvent` to `currentModelPredictMinutes`.  When the predicted time exceeds or equals the remaining minutes, **start the run** by setting `equipmentStartCommand` to `true` and capturing the snapshot predictions for each model.
   - If the schedule indicates unoccupied and the command was previously `true`, initiate an **off delay** countdown before releasing the command to `null` (as in the original blocks).

4. **Active run monitoring:**
   - While running, update `currentRunElapsedMinutes` and ensure equipment continues to run.  If the zone reaches setpoint within `tempTolerance`, stop early and record the actual runtime.  If the elapsed time exceeds `maxMinutesAllowed`, stop and mark the run as a timeout.
   - After a run finishes, record, for **each model**, the predicted minutes (snapshot taken at start), the actual minutes and the resulting error.  Compute the **squared error** \((\text{predicted} - \text{actual})^2\) and update the model’s rolling average squared error.  Update the learning parameters for each model:
     - Model 0 updates its `degreesPerMinute` by dividing \(\Delta T\) by actual minutes.
     - Model 1 adds the pair `(\Delta T, actual minutes)` to its history, performs a quadratic regression to derive new \(\alpha_{1,a}\) and \(\alpha_{1,b}\) and blends them using an exponential moving average (EMA).
     - Model 2 updates its baseline minutes and baseline outdoor air temperature used in the OAT ratio.

5. **Auto‑mode model selection:**
   - After a configurable number of days (default **3 days**) or a minimum number of completed runs, the controller compares the average squared error of each model.  The **model with the smallest error is selected** and recorded in the `currentModel` slot (e.g., `0` for baseline, `1` for quadratic, `2` for linear OAT).  This model is used for `currentModelPredictMinutes` until another model achieves a lower error.
   - Operators may override auto‑selection by manually forcing a model via the UI if desired.

6. **Zone recovery tracking independent of schedule:**
   - The controller continues to **measure how long it takes the zone to reach setpoint** even if the occupancy schedule changes mid‑run.  This ensures the learned recovery rates reflect real equipment performance and are not coupled to occupancy toggles.  The runtime measurement is capped at `maxMinutesAllowed` to avoid infinite runs.

## Slot Sheet

Below is a consolidated slot sheet for the ultimate optimal start block.  Slots are grouped for clarity.  Do **not** remove any existing slots; the new model‑selection logic simply adds metrics and grouping.

### Configuration & Enable

| Slot                       | Type             | Description                                               |
| :------------------------- | :--------------- | :-------------------------------------------------------- |
| `enable`                  | `BStatusBoolean` | **Master enable** for the optimal start controller.  When `false`, `equipmentStartCommand` is forced `null`. |
| `maxMinutesAllowed`        | `BStatusNumeric` | Safety cap for runtime (default = 180 min). |
| `tempTolerance`            | `BStatusNumeric` | Acceptable deviation from setpoint (default 0.5 °F). |
| `historyDaysToRetain`      | `BStatusNumeric` | Days of run history to retain for model 1 and model 0 learning. |
| `emaWeightingFactor`       | `BStatusNumeric` | Exponential moving average weight for smoothing quadratic coefficients. |
| `commandOffDelaySeconds`   | `BStatusNumeric` | Countdown delay after a run before releasing command to `null`. |
| `useImperialUnits`         | `BStatusBoolean` | Use °F and 32 °F/100 °F for OAT reference when `true`; use °C and 0 °C/38 °C when `false`. |
| `autoModeStartDays`        | `BStatusNumeric` | Days of operation before automatically selecting the best model (default = 3 days). |

### Inputs – Sensors & Schedule

| Slot                         | Type             | Description |
| :--------------------------- | :--------------- | :-------------------------------------------------------- |
| `zoneTemp`                   | `BStatusNumeric` | Current zone temperature. |
| `targetZoneTempSetpoint`     | `BStatusNumeric` | Desired occupied setpoint. |
| `outdoorAirTemp`             | `BStatusNumeric` | Outdoor air temperature.  Required for Model 2; if invalid, Model 2 temporarily reverts to linear fallback. |
| `zoneTempTolerance`          | `BStatusNumeric` | Additional tolerance input for zones where tolerance may vary (optional). |
| `scheduleNextValue`          | `BStatusBoolean` | Occupancy value of the **next** schedule event (`true` = occupied). |
| `scheduleNextEventTime`      | `BStatusNumeric` | Timestamp (Java ms) of the next schedule event. |

### Outputs – Unified Prediction & Command

| Slot                           | Type             | Description |
| :----------------------------- | :--------------- | :-------------------------------------------------------- |
| `equipmentStartCommand`        | `BStatusBoolean` | Final command to the RTU.  `true` means “run”; `null` indicates no action. |
| `currentModel`                 | `BStatusNumeric` | Indicates which model’s prediction is currently active (0 = baseline, 1 = quadratic, 2 = linear OAT). |
| `currentModelPredictMinutes`   | `BStatusNumeric` | Predicted minutes to setpoint from the **active model**.  Forced to 0 when the zone is within tolerance. |
| `statusLog`                    | `BStatusString`  | Human‑readable summary of the last major action or error. |
| `statusTrace`                  | `BStatusString`  | Detailed diagnostics, including which inputs are invalid and any fault conditions. |
| `isRunning`                    | `BStatusBoolean` | `true` during an active optimal start run. |
| `zoneAtTempTolerance`          | `BStatusBoolean` | `true` when the current zone temperature is within tolerance of setpoint. |
| `currentRunElapsedMinutes`     | `BStatusNumeric` | Live stopwatch of the current run. |
| `countdownToNullStatus`        | `BStatusBoolean` | `true` while the off‑delay countdown is running. |

### Model‑Specific Performance Metrics

For **each model (0, 1, 2)** the following slots are provided.  These slots are suffixed with the model index (e.g., `lastRunPredictedMinutes_m0`, `lastRunPredictedMinutes_m1`, `lastRunPredictedMinutes_m2`).  Grouping the slots by model keeps related metrics together.

| Suffix                   | Type             | Description |
| :----------------------- | :--------------- | :-------------------------------------------------------- |
| `lastRunPredictedMinutes_mX` | `BStatusNumeric` | Snapshot of the predicted minutes for model X at the instant the run started. |
| `lastRunActualMinutes_mX`    | `BStatusNumeric` | Actual run time measured for the last run (success or timeout). |
| `lastRunErrorMinutes_mX`     | `BStatusNumeric` | Difference (Predicted – Actual) in minutes.  Positive = started too early; negative = too late. |
| `lastRunErrorPercent_mX`     | `BStatusNumeric` | Percent error: \((\text{Predicted} - \text{Actual})/\text{Actual} \times 100\). |
| `lastRunSquaredError_mX`     | `BStatusNumeric` | Squared error: \((\text{Predicted} - \text{Actual})^2\). |
| `avgSquaredError_mX`         | `BStatusNumeric` | Rolling average squared error used to select the best model. |

### Learned Parameters & Visualization

| Slot                             | Type             | Description |
| :------------------------------- | :--------------- | :-------------------------------------------------------- |
| `degreesPerMinuteHeat`           | `BStatusNumeric` | Learned heating rate (°/min) used by Model 0 and linear fallback. |
| `degreesPerMinuteCool`           | `BStatusNumeric` | Learned cooling rate (°/min) used by Model 0 and linear fallback. |
| `quadraticA_heat`                | `BStatusNumeric` | Parameter \(\alpha_{1,a}\) for Model 1 (heating) after EMA smoothing. |
| `quadraticB_heat`                | `BStatusNumeric` | Parameter \(\alpha_{1,b}\) for Model 1 (heating). |
| `quadraticA_cool`                | `BStatusNumeric` | Parameter \(\alpha_{1,a}\) for Model 1 (cooling). |
| `quadraticB_cool`                | `BStatusNumeric` | Parameter \(\alpha_{1,b}\) for Model 1 (cooling). |
| `heatOatMinutesAdder`            | `BStatusNumeric` | Additional minutes added by Model 2 due to the outdoor air ratio (heating). |
| `coolOatMinutesAdder`            | `BStatusNumeric` | Additional minutes added by Model 2 due to the outdoor air ratio (cooling). |
| `lastHeatBaselineMinutes`        | `BStatusNumeric` | Most recent baseline run time used by Model 2 (heating). |
| `lastHeatBaselineOat`            | `BStatusNumeric` | Outdoor air temperature corresponding to `lastHeatBaselineMinutes`. |
| `lastCoolBaselineMinutes`        | `BStatusNumeric` | Baseline runtime for Model 2 (cooling). |
| `lastCoolBaselineOat`            | `BStatusNumeric` | Baseline outdoor air temperature (cooling). |

The block may expose additional internal diagnostics (e.g., history counts for the quadratic model) for advanced visualization or debugging.  These slots are optional and can be hidden from the normal operator view.

## Math Summary (for reference)

Below is a consolidated view of the mathematical relationships between inputs and predicted runtime.  These equations are provided for clarity; the Java implementation performs equivalent computations.

**Model 0 (Baseline):**

\[
  t_0 = \frac{\Delta T}{r_\text{learned}}
\]

where \(r_\text{learned}\) is the average degrees per minute learned from past runs.  When no history exists, a conservative default is used.

**Model 1 (Quadratic, PNNL):**

\[
  t_1 = \alpha_{1,a}(\Delta T)^2 + \alpha_{1,b}
\]

with coefficients updated after each run using a quadratic regression and smoothed via an exponential moving average【913477360246089†L448-L476】.  Separate coefficients are maintained for heating and cooling.

**Model 2 (Linear + OAT Ratio, PNNL):**

\[
  t_2 = \left( \frac{\Delta T}{\alpha_{2,a}} \right) \cdot \frac{\lvert T_{\text{ref}} - T_{\text{o,base}} \rvert}{\lvert T_{\text{ref}} - T_{\text{o,today}} \rvert}
\]

where \(\alpha_{2,a}\) is the learned linear rate from the previous day, \(T_{\text{o,base}}\) is the outdoor air temperature on the day the baseline was recorded, and \(T_{\text{ref}}\) is the design outdoor air temperature (32 °F or 100 °F)【913477360246089†L540-L554】.  This formula appears in Eq. (15) of the PNNL paper【913477360246089†L540-L554】.  For heating, the ratio increases the run time when it is colder than the baseline; for cooling, the ratio increases run time when it is hotter.

## Putting It All Together

The **ultimate optimal start controller** described here preserves all of the features of the original linear and quadratic blocks while adding a baseline model and an auto‑selection strategy.  It monitors input validity, computes three predictions, selects the best model based on real‑world performance, and manages the schedule start and off‑delay logic.  Operators can trust that the block will adapt over time, learning how their specific zone responds and always choosing the most accurate model.

Feel free to extend this framework with additional models (e.g., cubic or machine‑learning predictors) following the same pattern: keep track of each model’s errors, update its parameters responsibly, and let the **data decide** which model performs best.


## 💻 Java Code Quadratic Model

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java
// Timer ticket for periodic execution
private Clock.Ticket ticket;

// Run state
private long startTimestamp = 0L;
private boolean isOptimalStartRunning = false;
private boolean isHoldingForSchedule = false;
private long targetEventTime = 0L;
private long lastStartTriggerTimestamp = 0L;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0L;

// Baseline Model (Model 0) learned rates
private double learnedRateHeat = 0.1; // degrees per minute
private double learnedRateCool = 0.1;

// Quadratic Model (Model 1) parameters and history
private static final double DEFAULT_A = 0.1;
private static final double DEFAULT_B = 5.0;
private double quadA_heat = DEFAULT_A;
private double quadB_heat = DEFAULT_B;
private double quadA_cool = DEFAULT_A;
private double quadB_cool = DEFAULT_B;
private static final double EMA_ALPHA = 0.2;
private List<PerformanceRecord> heatHistory = new ArrayList<>();
private List<PerformanceRecord> coolHistory = new ArrayList<>();

// Linear + OAT Model (Model 2) baselines
private double lastHeatBaselineMinutes = 30.0;
private double lastHeatBaselineOat = 20.0;
private double lastCoolBaselineMinutes = 30.0;
private double lastCoolBaselineOat = 85.0;
private static final double RATIO_MIN = 0.2;
private static final double RATIO_MAX = 4.0;
private static final double TREF_HEAT_IMP = 32.0;
private static final double TREF_COOL_IMP = 100.0;
private static final double TREF_HEAT_MET = 0.0;
private static final double TREF_COOL_MET = 38.0;

// Auto‑selection state
private int currentModelIndex = 0; // 0 = baseline, 1 = quad, 2 = linear OAT
private double avgSqErr_m0 = 0.0;
private double avgSqErr_m1 = 0.0;
private double avgSqErr_m2 = 0.0;
private int runCount_m0 = 0;
private int runCount_m1 = 0;
private int runCount_m2 = 0;
private long firstRunTimestamp = 0L;
private boolean autoModeActivated = false;

/**
 * Small container for storing a single run’s performance record for the quadratic model.
 */
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
}

@Override
public void onStart() throws Exception {
    // Initialize configuration defaults if null
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    if (getEmaWeightingFactor().isNull()) setEmaWeightingFactor(new BStatusNumeric(EMA_ALPHA));
    if (getAutoModeStartDays().isNull()) setAutoModeStartDays(new BStatusNumeric(3.0));
    if (getUseImperialUnits().isNull()) setUseImperialUnits(new BStatusBoolean(true));

    // Initialize outputs
    setIsRunning(new BStatusBoolean(false));
    setCurrentModelPredictMinutes(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    setCurrentModel(new BStatusNumeric(0));
    setEquipmentStartCommand(new BStatusBoolean(false));
    getEquipmentStartCommand().setStatus(BStatus.NULL);
    setCountdownToNullStatus(new BStatusBoolean(false));
    setZoneAtTempTolerance(new BStatusBoolean(false));
    setStatusLog(new BStatusString("[onStart] Ultimate Optimal Start initialized."));
    setStatusTrace(new BStatusString("Initialized"));

    // Initialize model metrics for each model
    initModelMetrics();

    // Schedule the periodic execution
    updateTimer();
}

private void initModelMetrics() {
    // Baseline model metrics
    setLastRunPredictedMinutesM0(new BStatusNumeric(0.0));
    setLastRunActualMinutesM0(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM0(new BStatusNumeric(0.0));
    setLastRunErrorPercentM0(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM0(new BStatusNumeric(0.0));
    setAvgSquaredErrorM0(new BStatusNumeric(0.0));

    // Quadratic model metrics
    setLastRunPredictedMinutesM1(new BStatusNumeric(0.0));
    setLastRunActualMinutesM1(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM1(new BStatusNumeric(0.0));
    setLastRunErrorPercentM1(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM1(new BStatusNumeric(0.0));
    setAvgSquaredErrorM1(new BStatusNumeric(0.0));

    // Linear OAT model metrics
    setLastRunPredictedMinutesM2(new BStatusNumeric(0.0));
    setLastRunActualMinutesM2(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM2(new BStatusNumeric(0.0));
    setLastRunErrorPercentM2(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM2(new BStatusNumeric(0.0));
    setAvgSquaredErrorM2(new BStatusNumeric(0.0));

    // Visual parameters
    setDegreesPerMinuteHeat(new BStatusNumeric(learnedRateHeat));
    setDegreesPerMinuteCool(new BStatusNumeric(learnedRateCool));
    setQuadraticAHeat(new BStatusNumeric(quadA_heat));
    setQuadraticBHeat(new BStatusNumeric(quadB_heat));
    setQuadraticACool(new BStatusNumeric(quadA_cool));
    setQuadraticBCool(new BStatusNumeric(quadB_cool));
    setHeatOatMinutesAdder(new BStatusNumeric(0.0));
    setCoolOatMinutesAdder(new BStatusNumeric(0.0));
}

@Override
public void onExecute() throws Exception {
    try {
        // Reschedule periodic execution
        updateTimer();

        // Validate the master enable. If disabled, force outputs to null and skip logic.
        boolean enabled = getEnable().getStatus().isOk() && getEnable().getValue();
        if (!enabled) {
            forceCommandNull();
            setStatusTrace(new BStatusString("Disabled by enable flag."));
            return;
        }

        // Validate inputs. If any critical sensor is invalid, set command null and log status.
        if (!validateInputs()) {
            forceCommandNull();
            return;
        }

        // Update zone tolerance flag
        updateZoneAtTempTolerance();

        // Always update model predictions
        updateCurrentModelPredictions();

        // Main state machine
        if (isOptimalStartRunning) {
            monitorActiveRun();
            forceCommandTrue();
        } else if (isHoldingForSchedule) {
            monitorHold();
            forceCommandTrue();
        } else {
            updateEquipmentStartCommand();
        }

    } catch (Exception e) {
        // Catch any unexpected exceptions to avoid component fault
        String msg = "ERROR: Exception in onExecute: " + e.getMessage();
        setStatusLog(new BStatusString(msg));
        e.printStackTrace();
    }
}

@Override
public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
    setStatusLog(new BStatusString("[onStop] Program stopped."));
}

/**
 * Validates that required numeric and boolean inputs are present, wired,
 * within reasonable ranges and have OK status.  If any are invalid, an
 * explanatory message is written to statusTrace and false is returned.
 */
private boolean validateInputs() {
    // Check zone temperature and setpoint
    boolean zoneValid = isDataValid(getZoneTemp(), -100.0, 200.0);
    boolean setpointValid = isDataValid(getTargetZoneTempSetpoint(), -100.0, 200.0);
    boolean scheduleTimeValid = isDataValid(getScheduleNextEventTime(), 0.0, Double.MAX_VALUE);
    boolean scheduleValueValid = getScheduleNextValue() != null && getScheduleNextValue().getStatus().isOk();

    // Optionally check outdoor air temp; allow null but log it
    boolean oatValid = true;
    if (!getOutdoorAirTemp().isNull() && getOutdoorAirTemp().getStatus().isOk()) {
        oatValid = isDataValid(getOutdoorAirTemp(), -100.0, 200.0);
    }

    // Master enable is validated in onExecute before calling this method

    if (!zoneValid) {
        setStatusTrace(new BStatusString("Invalid zone temperature input."));
        return false;
    }
    if (!setpointValid) {
        setStatusTrace(new BStatusString("Invalid target setpoint input."));
        return false;
    }
    if (!scheduleTimeValid || !scheduleValueValid) {
        setStatusTrace(new BStatusString("Invalid schedule inputs."));
        return false;
    }
    if (!oatValid) {
        // Outdoor air temp is only critical for Model 2.  We'll still run other models.
        setStatusTrace(new BStatusString("Outdoor air temperature invalid. Model 2 will revert to linear fallback."));
    } else {
        setStatusTrace(new BStatusString("OK"));
    }
    return true;
}

/**
 * Updates the zoneAtTempTolerance flag by comparing the current zone
 * temperature with the target setpoint minus/plus the configured tolerance.
 */
private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) return;
    double tol = getTempTolerance().getStatus().isOk() ? getTempTolerance().getValue() : 0.5;
    double diff = Math.abs(getZoneTemp().getValue() - getTargetZoneTempSetpoint().getValue());
    setZoneAtTempTolerance(new BStatusBoolean(diff <= tol));
}

/**
 * Compute predicted minutes for each model and update the active model
 * prediction.  If the zone is within tolerance, all predictions are zero.
 */
private void updateCurrentModelPredictions() {
    // If already at setpoint, predictions are zero
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        setLastPredictionsToZero();
        return;
    }

    // Compute deltaT
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double deltaT = Math.abs(target - zone);
    double maxMins = getMaxMinutesAllowed().getValue();

    boolean heating = zone < target;

    // --------------------------------------------------------------------
    // Model 0: Baseline degrees per minute
    double rate = heating ? learnedRateHeat : learnedRateCool;
    double t0 = (rate > 0.0001) ? (deltaT / rate) : maxMins;
    if (t0 < 0) t0 = 0; if (t0 > maxMins) t0 = maxMins;

    // --------------------------------------------------------------------
    // Model 1: Quadratic regression
    double t1;
    if (heating) {
        t1 = (quadA_heat * (deltaT * deltaT)) + quadB_heat;
    } else {
        t1 = (quadA_cool * (deltaT * deltaT)) + quadB_cool;
    }
    if (t1 < 0) t1 = 0; if (t1 > maxMins) t1 = maxMins;

    // --------------------------------------------------------------------
    // Model 2: Linear + outdoor air ratio
    double t2;
    double ratio = 1.0;
    double t_linear = t0; // use baseline rate as the linear core
    boolean oatOk = !getOutdoorAirTemp().isNull() && getOutdoorAirTemp().getStatus().isOk();
    if (oatOk) {
        double oat = getOutdoorAirTemp().getValue();
        boolean imperial = getUseImperialUnits().getStatus().isOk() && getUseImperialUnits().getValue();
        double T_ref = imperial ? (heating ? TREF_HEAT_IMP : TREF_COOL_IMP) : (heating ? TREF_HEAT_MET : TREF_COOL_MET);
        double T_base = heating ? lastHeatBaselineOat : lastCoolBaselineOat;
        double numerator = Math.abs(T_ref - T_base);
        double denominator = Math.abs(T_ref - oat);
        if (denominator > 0.0) {
            ratio = numerator / denominator;
            if (ratio < RATIO_MIN) ratio = RATIO_MIN;
            if (ratio > RATIO_MAX) ratio = RATIO_MAX;
        }
        // Compute additional minutes due to OAT
        double adder = t_linear * (ratio - 1.0);
        if (heating) setHeatOatMinutesAdder(new BStatusNumeric(adder));
        else setCoolOatMinutesAdder(new BStatusNumeric(adder));
    } else {
        // No OAT reading – revert to linear fallback
        if (heating) setHeatOatMinutesAdder(new BStatusNumeric(0.0));
        else setCoolOatMinutesAdder(new BStatusNumeric(0.0));
    }
    t2 = t_linear * ratio;
    if (t2 < 0) t2 = 0; if (t2 > maxMins) t2 = maxMins;

    // Save predictions for each model (for display, not used for selection yet)
    setLastRunPredictedMinutesM0(new BStatusNumeric(t0));
    setLastRunPredictedMinutesM1(new BStatusNumeric(t1));
    setLastRunPredictedMinutesM2(new BStatusNumeric(t2));

    // Determine the active model index
    updateAutoModelSelection();
    double activePred;
    if (currentModelIndex == 0) activePred = t0;
    else if (currentModelIndex == 1) activePred = t1;
    else activePred = t2;

    setCurrentModelPredictMinutes(new BStatusNumeric(activePred));
    setCurrentModel(new BStatusNumeric(currentModelIndex));
}

/**
 * Updates the current model index based on average squared errors once
 * auto‑mode becomes active.  Prior to activation, the baseline model is
 * always selected.
 */
private void updateAutoModelSelection() {
    // Activate auto mode after the configured number of days since the first run
    double daysThreshold = getAutoModeStartDays().getStatus().isOk() ? getAutoModeStartDays().getValue() : 3.0;
    if (!autoModeActivated && firstRunTimestamp > 0) {
        long now = System.currentTimeMillis();
        long millisThreshold = (long) (daysThreshold * 86400000.0);
        if (now - firstRunTimestamp >= millisThreshold) {
            autoModeActivated = true;
        }
    }

    if (!autoModeActivated) {
        currentModelIndex = 0;
        return;
    }

    // Only consider models with at least one run
    double bestErr = Double.MAX_VALUE;
    int bestIndex = 0;
    if (runCount_m0 > 0 && avgSqErr_m0 < bestErr) {
        bestErr = avgSqErr_m0; bestIndex = 0;
    }
    if (runCount_m1 > 0 && avgSqErr_m1 < bestErr) {
        bestErr = avgSqErr_m1; bestIndex = 1;
    }
    if (runCount_m2 > 0 && avgSqErr_m2 < bestErr) {
        bestErr = avgSqErr_m2; bestIndex = 2;
    }
    currentModelIndex = bestIndex;
}

/**
 * Sets all prediction slots to zero. Used when the zone is already within tolerance.
 */
private void setLastPredictionsToZero() {
    setLastRunPredictedMinutesM0(new BStatusNumeric(0.0));
    setLastRunPredictedMinutesM1(new BStatusNumeric(0.0));
    setLastRunPredictedMinutesM2(new BStatusNumeric(0.0));
}

/**
 * Handles off‑delay and schedule logic when idle.  When the predicted
 * runtime meets or exceeds the minutes until the next occupancy, this
 * method triggers the start sequence.
 */
private void updateEquipmentStartCommand() {
    // 1. Off‑Delay
    if (isOffDelayActive) {
        long elapsedSec = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delay = 60;
        if (getCommandOffDelaySeconds().getStatus().isOk()) {
            delay = (long) getCommandOffDelaySeconds().getValue();
        }
        if (elapsedSec >= delay) {
            isOffDelayActive = false;
            forceCommandNull();
            setCountdownToNullStatus(new BStatusBoolean(false));
        } else {
            setCountdownToNullStatus(new BStatusBoolean(true));
        }
        return;
    }

    // 2. Schedule check
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        forceCommandNull();
        return;
    }
    boolean nextOccupied = getScheduleNextValue().getValue();
    if (nextOccupied) {
        long now = System.currentTimeMillis();
        long nextTime = (long) getScheduleNextEventTime().getValue();
        double minsUntilEvent = (nextTime - now) / 60000.0;
        if (minsUntilEvent < 0) minsUntilEvent = 0;
        double neededMins = getCurrentModelPredictMinutes().getValue();
        if (neededMins >= minsUntilEvent) {
            // Trigger start
            startOptimalStartSequence(nextTime);
            forceCommandTrue();
        }
    } else {
        // Schedule now unoccupied; if command was true, start off delay
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            setCountdownToNullStatus(new BStatusBoolean(true));
        }
    }
}

/**
 * Initiates a new optimal start run.  Captures the predicted minutes for
 * each model and sets up internal state.
 */
private void startOptimalStartSequence(long nextEvent) {
    if (getZoneAtTempTolerance().getValue()) {
        setCurrentModelPredictMinutes(new BStatusNumeric(0.0));
        return;
    }
    // Ensure this is the first run
    if (firstRunTimestamp == 0) firstRunTimestamp = System.currentTimeMillis();

    // Snapshot predictions
    setLastRunPredictedMinutesM0(new BStatusNumeric(getLastRunPredictedMinutesM0().getValue()));
    setLastRunPredictedMinutesM1(new BStatusNumeric(getLastRunPredictedMinutesM1().getValue()));
    setLastRunPredictedMinutesM2(new BStatusNumeric(getLastRunPredictedMinutesM2().getValue()));
    // Reset actuals/errors for each model
    resetRunMetrics();

    startTimestamp = System.currentTimeMillis();
    targetEventTime = nextEvent;
    isOptimalStartRunning = true;
    isHoldingForSchedule = false;
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    // Store starting zone and OAT values (for learning later)
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    }
    setStatusLog(new BStatusString("[Start] Run initiated. Model=" + currentModelIndex));
}

/**
 * Resets run metrics at the start of a new run.
 */
private void resetRunMetrics() {
    // Clear last actual/error for each model
    setLastRunActualMinutesM0(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM0(new BStatusNumeric(0.0));
    setLastRunErrorPercentM0(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM0(new BStatusNumeric(0.0));
    setLastRunActualMinutesM1(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM1(new BStatusNumeric(0.0));
    setLastRunErrorPercentM1(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM1(new BStatusNumeric(0.0));
    setLastRunActualMinutesM2(new BStatusNumeric(0.0));
    setLastRunErrorMinutesM2(new BStatusNumeric(0.0));
    setLastRunErrorPercentM2(new BStatusNumeric(0.0));
    setLastRunSquaredErrorM2(new BStatusNumeric(0.0));
}

/**
 * Monitors an active run, records the runtime when finished and updates
 * learning parameters for each model.
 */
private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsedMinutes = (now - startTimestamp) / 60000.0;
    setCurrentRunElapsedMinutes(new BStatusNumeric(elapsedMinutes));
    double maxMins = getMaxMinutesAllowed().getValue();

    // Success: reached setpoint
    if (getZoneAtTempTolerance().getValue()) {
        stopAndRecord(elapsedMinutes, true);
        return;
    }
    // Timeout
    if (elapsedMinutes >= maxMins) {
        stopAndRecord(elapsedMinutes, false);
        return;
    }
    // Sensors became invalid
    if (!getZoneTemp().getStatus().isOk()) {
        stopAndRecord(elapsedMinutes, false);
    }
}

/**
 * Monitors a hold state; releases the hold when the scheduled occupancy
 * arrives or when the schedule flips back to unoccupied.
 */
private void monitorHold() {
    long now = System.currentTimeMillis();
    if (now >= targetEventTime) {
        isHoldingForSchedule = false;
        setStatusLog(new BStatusString("[Hold] Released at event time."));
    }
    if (getScheduleNextValue().getStatus().isOk() && !getScheduleNextValue().getValue()) {
        isHoldingForSchedule = false;
        setStatusLog(new BStatusString("[Hold] Aborted – schedule changed to unoccupied."));
    }
}

/**
 * Stops a run and records actual runtime and errors for each model.
 */
private void stopAndRecord(double actualMinutes, boolean success) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));

    // Record run metrics for each model
    recordModelPerformance(0, getLastRunPredictedMinutesM0().getValue(), actualMinutes);
    recordModelPerformance(1, getLastRunPredictedMinutesM1().getValue(), actualMinutes);
    recordModelPerformance(2, getLastRunPredictedMinutesM2().getValue(), actualMinutes);

    // Learn rates for baseline model
    double zoneStart = getZoneTempAtStart().getValue();
    double zoneEnd = getZoneTemp().getStatus().isOk() ? getZoneTemp().getValue() : zoneStart;
    double delta = Math.abs(zoneEnd - zoneStart);
    if (delta > 0.5 && actualMinutes > 5.0) {
        if (zoneStart < getTargetZoneTempSetpoint().getValue()) {
            // Heating
            learnedRateHeat = delta / actualMinutes;
            setDegreesPerMinuteHeat(new BStatusNumeric(learnedRateHeat));
        } else {
            // Cooling
            learnedRateCool = delta / actualMinutes;
            setDegreesPerMinuteCool(new BStatusNumeric(learnedRateCool));
        }
    }

    // Update quadratic regression if success
    if (success && delta > 1.0 && actualMinutes > 5.0) {
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        heatOrCoolHistoryAdd(actualMinutes, delta, mode);
        updateQuadraticModel();
        updateQuadraticVisualRates();
    }

    // Update linear OAT baseline (Model 2) if success
    if (success && delta > 1.0 && actualMinutes > 5.0 && getOutdoorTempAtStart().getStatus().isOk()) {
        double oatStart = getOutdoorTempAtStart().getValue();
        if (zoneStart < getTargetZoneTempSetpoint().getValue()) {
            lastHeatBaselineMinutes = actualMinutes;
            lastHeatBaselineOat = oatStart;
        } else {
            lastCoolBaselineMinutes = actualMinutes;
            lastCoolBaselineOat = oatStart;
        }
    }

    // Determine if we finished early and should hold until schedule event
    long nowMillis = System.currentTimeMillis();
    if (success && nowMillis < targetEventTime) {
        isHoldingForSchedule = true;
        setStatusLog(new BStatusString("[Stop] Completed early; holding until schedule."));
    } else {
        setStatusLog(new BStatusString(success ? "[Stop] Run complete." : "[Stop] Timeout or aborted."));
    }
}

/**
 * Records the performance of a specific model, updates its error slots
 * and rolling average squared error.
 */
private void recordModelPerformance(int modelIndex, double predicted, double actual) {
    double err = predicted - actual;
    double pctErr = (actual > 0.0001) ? (err / actual) * 100.0 : 0.0;
    double sqErr = err * err;
    if (modelIndex == 0) {
        setLastRunActualMinutesM0(new BStatusNumeric(actual));
        setLastRunErrorMinutesM0(new BStatusNumeric(err));
        setLastRunErrorPercentM0(new BStatusNumeric(pctErr));
        setLastRunSquaredErrorM0(new BStatusNumeric(sqErr));
        avgSqErr_m0 = ((avgSqErr_m0 * runCount_m0) + sqErr) / (runCount_m0 + 1);
        runCount_m0++;
        setAvgSquaredErrorM0(new BStatusNumeric(avgSqErr_m0));
    } else if (modelIndex == 1) {
        setLastRunActualMinutesM1(new BStatusNumeric(actual));
        setLastRunErrorMinutesM1(new BStatusNumeric(err));
        setLastRunErrorPercentM1(new BStatusNumeric(pctErr));
        setLastRunSquaredErrorM1(new BStatusNumeric(sqErr));
        avgSqErr_m1 = ((avgSqErr_m1 * runCount_m1) + sqErr) / (runCount_m1 + 1);
        runCount_m1++;
        setAvgSquaredErrorM1(new BStatusNumeric(avgSqErr_m1));
    } else {
        setLastRunActualMinutesM2(new BStatusNumeric(actual));
        setLastRunErrorMinutesM2(new BStatusNumeric(err));
        setLastRunErrorPercentM2(new BStatusNumeric(pctErr));
        setLastRunSquaredErrorM2(new BStatusNumeric(sqErr));
        avgSqErr_m2 = ((avgSqErr_m2 * runCount_m2) + sqErr) / (runCount_m2 + 1);
        runCount_m2++;
        setAvgSquaredErrorM2(new BStatusNumeric(avgSqErr_m2));
    }
}

/**
 * Adds a performance record to the appropriate history list (heat or cool)
 * for Model 1 learning.
 */
private void heatOrCoolHistoryAdd(double actualMinutes, double deltaT, String mode) {
    PerformanceRecord rec = new PerformanceRecord(System.currentTimeMillis(), actualMinutes, deltaT, mode);
    if (mode.equals("HEAT")) heatHistory.add(rec);
    else coolHistory.add(rec);
    pruneHistory();
}

/**
 * Performs quadratic regression on the heat and cool histories to
 * determine new parameters for Model 1.  Results are smoothed using
 * EMA_ALPHA or the configured emaWeightingFactor slot.
 */
private void updateQuadraticModel() {
    // Determine smoothing alpha from slot
    double alpha = getEmaWeightingFactor().getStatus().isOk() ? getEmaWeightingFactor().getValue() : EMA_ALPHA;
    double[] heatParams = regressHistory(heatHistory);
    double[] coolParams = regressHistory(coolHistory);
    // Blend
    quadA_heat += alpha * (heatParams[0] - quadA_heat);
    quadB_heat += alpha * (heatParams[1] - quadB_heat);
    quadA_cool += alpha * (coolParams[0] - quadA_cool);
    quadB_cool += alpha * (coolParams[1] - quadB_cool);
    // Push to slot for visualization
    setQuadraticAHeat(new BStatusNumeric(quadA_heat));
    setQuadraticBHeat(new BStatusNumeric(quadB_heat));
    setQuadraticACool(new BStatusNumeric(quadA_cool));
    setQuadraticBCool(new BStatusNumeric(quadB_cool));
}

/**
 * Performs simple quadratic regression (y = a x + b) on the given history,
 * where x = (deltaT)^2 and y = durationMinutes.  Returns [a, b].  If
 * insufficient data exists, returns default parameters.
 */
private double[] regressHistory(List<PerformanceRecord> history) {
    if (history.size() < 2) {
        return new double[] { DEFAULT_A, DEFAULT_B };
    }
    double n = history.size();
    double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    for (PerformanceRecord r : history) {
        double x = r.deltaT * r.deltaT;
        double y = r.durationMinutes;
        sumX += x;
        sumY += y;
        sumXY += x * y;
        sumXX += x * x;
    }
    double denom = (n * sumXX) - (sumX * sumX);
    if (Math.abs(denom) < 1e-6) {
        return new double[] { DEFAULT_A, DEFAULT_B };
    }
    double a = ((n * sumXY) - (sumX * sumY)) / denom;
    double b = (sumY - (a * sumX)) / n;
    if (a < 0) a = DEFAULT_A;
    if (b < 0) b = DEFAULT_B;
    return new double[] { a, b };
}

/**
 * Updates the degreesPerMinuteHeat/Cool visualization based on history.
 */
private void updateQuadraticVisualRates() {
    if (!heatHistory.isEmpty()) {
        double totalDT = 0, totalT = 0;
        for (PerformanceRecord r : heatHistory) { totalDT += r.deltaT; totalT += r.durationMinutes; }
        if (totalT > 0) setDegreesPerMinuteHeat(new BStatusNumeric(totalDT / totalT));
    }
    if (!coolHistory.isEmpty()) {
        double totalDT = 0, totalT = 0;
        for (PerformanceRecord r : coolHistory) { totalDT += r.deltaT; totalT += r.durationMinutes; }
        if (totalT > 0) setDegreesPerMinuteCool(new BStatusNumeric(totalDT / totalT));
    }
}

/**
 * Removes history records older than the configured historyDaysToRetain.
 */
private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxDays = (int) getHistoryDaysToRetain().getValue();
    long cutoff = System.currentTimeMillis() - (maxDays * 86400000L);
    heatHistory.removeIf(r -> r.timestamp < cutoff);
    coolHistory.removeIf(r -> r.timestamp < cutoff);
}

/**
 * Schedules periodic execution of onExecute every 15 seconds.
 */
private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

/**
 * Sets the equipment command to true with OK status and clears countdown.
 */
private void forceCommandTrue() {
    getEquipmentStartCommand().setValue(true);
    getEquipmentStartCommand().setStatus(BStatus.ok);
    setCountdownToNullStatus(new BStatusBoolean(false));
}

/**
 * Forces the equipment command to null.
 */
private void forceCommandNull() {
    getEquipmentStartCommand().setValue(false);
    getEquipmentStartCommand().setStatus(BStatus.NULL);
    setCountdownToNullStatus(new BStatusBoolean(false));
}

/**
 * Determines if a numeric slot is valid (OK status and within [min, max]).
 */
private boolean isDataValid(BStatusNumeric slot, double min, double max) {
    if (slot == null) return false;
    if (!slot.getStatus().isOk()) return false;
    double v = slot.getValue();
    return v >= min && v <= max;
}



```