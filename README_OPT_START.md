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

The Program Object source below is intentionally conservative in the learning path. The recovery/drift recording mechanism is the same style as Niagara `kitControl` optimized start/stop:

- capture `spaceTempAtBeginning` when the optimized start or stop run begins,
- wait until the zone crosses the same comfort boundary used by the built-in block, or until the schedule changes state,
- calculate `spaceTempChange`, `optimizedRuntimeMinutes`, and `observedMinutesPerDegree`,
- update the learned runtime/drift value with the same weighted blend:

```text
new = (old * oldParameterMultiplier + observedMinutesPerDegree) / (oldParameterMultiplier + 1)
```

No extra recovery filters, safety factors, minimum-run filters, artificial derates, or alternate zone-recovery math are used in the recording path.

The two-model layer only affects prediction/control lead time after data has been recorded. It does not change how recovery is recorded.

- **Default / Model 0:** the plain Niagara `kitControl` runtime/drift calculation. This is used for control until enough scored history exists.
- **Model 1:** quadratic learned prediction using completed kitControl-style run records: `minutes = a × deltaT² + b`.
- **Model 2:** PNNL-style OAT-ratio prediction using the same completed run records as its baseline memory.
- All three models are scored from the same completed runs. After enough scored runs exist, the lowest mean squared error model is selected for the next run. Selection is recalculated after every completed run, so the winner can keep switching as building behavior changes.

```java
// ==========================================================
// Niagara Program Object Source
// Optimal Start / Stop with kitControl-style recording
// plus two prediction models and MSE-based model selection.
//
// Paste into the Niagara Program Object source area.
// Assumes the slots/getters/setters already exist.
// Do not add imports or a class declaration in the Program Object editor.
// ==========================================================

// ==========================================================
// CONSTANTS
// ==========================================================
private static final boolean ACTIVE   = true;
private static final boolean INACTIVE = false;
private static final boolean START    = true;
private static final boolean STOP     = false;
private static final boolean ENABLED  = true;
private static final boolean DISABLED = false;

// Matches the kitControl heatCoolMode boolean facet convention:
// false = heating, true = cooling
private static final boolean HEATING = false;
private static final boolean COOLING = true;

private static final long TIME_00_01 = 60000L;

private static final int NO_CALCULATION     = 0;
private static final int START_CALCULATION  = 1;
private static final int START_IN_PROCESS   = 2;
private static final int STOP_CALCULATION   = 3;
private static final int STOP_IN_PROCESS    = 4;

private static final int MODEL_KITCONTROL = 0;
private static final int MODEL_1 = 1;
private static final int MODEL_2 = 2;

// "Enough data" gate before MSE winner is allowed to control.
// This does not affect recording; it only affects model selection.
private static final int MIN_SCORED_RUNS_FOR_MODEL_SELECTION = 3;

// OAT reference values for simple weather-ratio prediction.
// These are only used by Model 2 prediction, not by the kitControl-style recording path.
private static final double TREF_HEAT_F = -40.0;
private static final double TREF_COOL_F = 110.0;

// ==========================================================
// STATE
// ==========================================================
private Clock.Ticket ticket = null;

private boolean controlModeAtBeginning = HEATING;
private boolean startDone = false;
private boolean analysisComplete = false;

private float observedMinutesPerDegree = 0.0f;
private float spaceTempChange = 0.0f;

private int leadTime = 0;
private int optimizedRuntimeMinutes = 0;
private int lastProgramMode = NO_CALCULATION;

private BAbsTime now = BAbsTime.NULL;

// Prediction snapshots captured at the moment command starts.
// These are used only for MSE scoring after the run completes.
private double lastStartPredictionKitControl = 0.0;
private double lastStartPredictionModel1 = 0.0;
private double lastStartPredictionModel2 = 0.0;
private double lastStopPredictionKitControl = 0.0;
private double lastStopPredictionModel1 = 0.0;
private double lastStopPredictionModel2 = 0.0;

// Mean squared error tracking. This is arithmetic mean, not EMA.
private int startKitControlScoreCount = 0;
private int startModel1ScoreCount = 0;
private int startModel2ScoreCount = 0;
private double startKitControlMse = 0.0;
private double startModel1Mse = 0.0;
private double startModel2Mse = 0.0;

private int stopKitControlScoreCount = 0;
private int stopModel1ScoreCount = 0;
private int stopModel2ScoreCount = 0;
private double stopKitControlMse = 0.0;
private double stopModel1Mse = 0.0;
private double stopModel2Mse = 0.0;

// Default control path is the original Niagara kitControl calculation.
// Model 1 and Model 2 are not allowed to control until enough scored runs exist.
private int selectedStartModel = MODEL_KITCONTROL;
private int selectedStopModel = MODEL_KITCONTROL;

// Model 1 quadratic coefficient memory: minutes = a * deltaT^2 + b.
// These are prediction-only memories. They are trained only after the normal
// kitControl-style runtime/drift recording has completed.
private static final double MODEL1_ALPHA = 0.20;

static class PerformanceRecord
{
  long timestamp;
  double minutes;
  double deltaT;

  PerformanceRecord(long ts, double mins, double dT)
  {
    timestamp = ts;
    minutes = mins;
    deltaT = dT;
  }
}

private java.util.List startHeatHistory = new java.util.ArrayList();
private java.util.List startCoolHistory = new java.util.ArrayList();
private java.util.List stopHeatHistory = new java.util.ArrayList();
private java.util.List stopCoolHistory = new java.util.ArrayList();

private double model1StartHeatA = 0.10;
private double model1StartHeatB = 5.0;
private double model1StartCoolA = 0.10;
private double model1StartCoolB = 5.0;
private double model1StopHeatA = 0.10;
private double model1StopHeatB = 5.0;
private double model1StopCoolA = 0.10;
private double model1StopCoolB = 5.0;

// Model 2 baseline memory. These are intentionally simple.
// They are updated from the same observed run record, after the kitControl-style
// runtime/drift value has been recorded.
private double model2StartHeatBaselineMins = 30.0;
private double model2StartHeatBaselineOat = 20.0;
private double model2StartCoolBaselineMins = 30.0;
private double model2StartCoolBaselineOat = 85.0;

private double model2StopHeatBaselineMins = 30.0;
private double model2StopHeatBaselineOat = 20.0;
private double model2StopCoolBaselineMins = 30.0;
private double model2StopCoolBaselineOat = 85.0;

// ==========================================================
// LIFECYCLE
// ==========================================================
public void onStart() throws Exception
{
  startDone = false;
  analysisComplete = false;
  leadTime = 0;
  optimizedRuntimeMinutes = 0;
  observedMinutesPerDegree = 0.0f;
  spaceTempChange = 0.0f;
  lastProgramMode = NO_CALCULATION;
  selectedStartModel = MODEL_KITCONTROL;
  selectedStopModel = MODEL_KITCONTROL;

  setProgramMode(NO_CALCULATION);
  forceStartStopOutputsNull();
  initClockTicket();
}

public void onExecute() throws Exception
{
  now = Clock.time();

  // Reset start-done near midnight or when start is disabled,
  // matching the original kitControl daily reset behavior.
  if (getStartEnable().getValue() == DISABLED || now.getTimeOfDayMillis() < TIME_00_01)
  {
    startDone = false;
  }

  performStartStopAnalysis();
  performStartStopCalculation();
  performStartStopControl();
  updateControlOutput();

  lastProgramMode = getProgramMode();
}

public void onStop() throws Exception
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }

  setProgramMode(NO_CALCULATION);
  forceStartStopOutputsNull();
}

// ==========================================================
// TIMER
// ==========================================================
private void initClockTicket()
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }

  // Run once per minute, offset 15 seconds after top of minute.
  BAbsTime next = Clock.nextTopOfMinute().add(BRelTime.makeSeconds(15));
  ticket = Clock.schedulePeriodically(getComponent(), next, BRelTime.makeMinutes(1), BProgram.execute, null);
}

// ==========================================================
// CALCULATION
// ==========================================================
private void performStartStopCalculation()
{
  if (!inputsAreUsable())
  {
    setProgramMode(NO_CALCULATION);
    return;
  }

  // Only calculate when the next event is today.
  if (getNextEventTime().getDayOfYear() != now.getDayOfYear())
  {
    setProgramMode(NO_CALCULATION);
    return;
  }

  selectBestModelsIfReady();

  if (getNextEventValue().getValue() == ACTIVE)
  {
    performStartCalculation();
  }
  else
  {
    performStopCalculation();
  }
}

private void performStartCalculation()
{
  if (getStartEnable().getValue() == ENABLED && getScheduleStatus().getValue() != ACTIVE)
  {
    if (!startDone && getSpaceTemp().getStatus().isValid())
    {
      if (getProgramMode() != START_IN_PROCESS)
      {
        setProgramMode(START_CALCULATION);

        double deltaT = 0.0;
        boolean heatBucket = HEATING;

        if (getSpaceTemp().getValue() > getUpperComfortLimit())
        {
          deltaT = getSpaceTemp().getValue() - getUpperComfortLimit();
          heatBucket = COOLING;
        }
        else if (getSpaceTemp().getValue() < getLowerComfortLimit())
        {
          deltaT = getLowerComfortLimit() - getSpaceTemp().getValue();
          heatBucket = HEATING;
        }
        else
        {
          leadTime = 0;
          return;
        }

        leadTime = 1 + (int)selectStartControlPrediction(deltaT, heatBucket);
      }
    }
    else
    {
      leadTime = 0;
    }
  }
  else
  {
    setProgramMode(NO_CALCULATION);
  }
}

private void performStopCalculation()
{
  if (getStopEnable().getValue() == ENABLED && getScheduleStatus().getValue() != INACTIVE)
  {
    if (getSpaceTemp().getStatus().isValid() && getProgramMode() != STOP_IN_PROCESS)
    {
      setProgramMode(STOP_CALCULATION);

      controlModeAtBeginning = getHeatCoolMode().getValue();

      double deltaT = 0.0;

      if (controlModeAtBeginning == HEATING)
      {
        if (getSpaceTemp().getValue() > getLowerComfortLimit())
        {
          deltaT = getSpaceTemp().getValue() - getLowerComfortLimit();
        }
        else
        {
          leadTime = 0;
          return;
        }
      }
      else
      {
        if (getSpaceTemp().getValue() < getUpperComfortLimit())
        {
          deltaT = getUpperComfortLimit() - getSpaceTemp().getValue();
        }
        else
        {
          leadTime = 0;
          return;
        }
      }

      leadTime = (int)selectStopControlPrediction(deltaT, controlModeAtBeginning);
    }
    else
    {
      leadTime = 0;
    }
  }
  else
  {
    setProgramMode(NO_CALCULATION);
  }
}

// ==========================================================
// CONTROL HANDOFF
// ==========================================================
private void performStartStopControl()
{
  if (getProgramMode() != START_CALCULATION && getProgramMode() != STOP_CALCULATION)
  {
    setCalculatedCommandTime(BTime.make(getNextEventTime()));
    return;
  }

  long calcCmdTime = getNextEventTime().getTimeOfDayMillis() - ((long)leadTime * TIME_00_01);

  if (calcCmdTime < getEarliestStartTime().getTimeOfDayMillis())
  {
    calcCmdTime = getEarliestStartTime().getTimeOfDayMillis();
  }

  setCalculatedCommandTime(BTime.make(BRelTime.make(calcCmdTime)));

  if (getProgramMode() == STOP_CALCULATION && getCalculatedCommandTime().isBefore(getEarliestStopTime()))
  {
    setCalculatedCommandTime(getEarliestStopTime());
  }

  BTime currentTime = BTime.make(Clock.time());

  if (currentTime.isAfter(getCalculatedCommandTime()) || currentTime.isAfter(BTime.make(getNextEventTime())))
  {
    if (getProgramMode() == START_CALCULATION)
    {
      startDone = true;
      setProgramMode(START_IN_PROCESS);
      setLastStartTime(Clock.time());

      getSpaceTempAtBeginning().setValue(getSpaceTemp().getValue());
      getOutsideTempAtBeginning().setValue(getOutsideTemp().getValue());

      captureStartPredictions();

      startTimeTrigger();
      getMessage().setValue(
        "Optimized start for " + getNextEventTime() +
        " schedule time. Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
    else if (getProgramMode() == STOP_CALCULATION)
    {
      setProgramMode(STOP_IN_PROCESS);
      setLastStopTime(Clock.time());

      getSpaceTempAtBeginning().setValue(getSpaceTemp().getValue());
      getOutsideTempAtBeginning().setValue(getOutsideTemp().getValue());
      controlModeAtBeginning = getHeatCoolMode().getValue();

      captureStopPredictions();

      stopTimeTrigger();
      getMessage().setValue(
        "Optimized stop for " + getNextEventTime() +
        " schedule time. Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
  }
}

private void updateControlOutput()
{
  if (getProgramMode() == START_IN_PROCESS)
  {
    getStartTimeCommand().setValue(START);
    getStartTimeCommand().setStatusNull(false);

    getStopTimeCommand().setValue(STOP);
    getStopTimeCommand().setStatusNull(true);
  }
  else if (getProgramMode() == STOP_IN_PROCESS)
  {
    getStopTimeCommand().setValue(STOP);
    getStopTimeCommand().setStatusNull(false);

    getStartTimeCommand().setValue(STOP);
    getStartTimeCommand().setStatusNull(true);
  }
  else
  {
    forceStartStopOutputsNull();
    analysisComplete = false;
  }
}

private void forceStartStopOutputsNull()
{
  getStopTimeCommand().setValue(STOP);
  getStopTimeCommand().setStatusNull(true);

  getStartTimeCommand().setValue(STOP);
  getStartTimeCommand().setStatusNull(true);
}

// ==========================================================
// LEARNING / ANALYSIS
// This section intentionally matches kitControl-style recording.
// No extra safety factors, no minimum-run filters, and no alternate math
// are applied to the zone recovery/drift recording path.
// ==========================================================
private void performStartStopAnalysis()
{
  if (!getDynamicParameterAdjust()) return;
  if (analysisComplete) return;
  if (!getSpaceTemp().getStatus().isValid()) return;

  if (lastProgramMode == START_IN_PROCESS)
  {
    handleStartAnalysis();
  }
  else if (lastProgramMode == STOP_IN_PROCESS)
  {
    handleStopAnalysis();
  }
}

private void handleStartAnalysis()
{
  if (isCoolingStartAnalysis())
  {
    if (getSpaceTemp().getValue() < getSpaceTempAtBeginning().getValue() &&
        (getSpaceTemp().getValue() <= getUpperComfortLimit() || getScheduleStatus().getValue() == ACTIVE))
    {
      // Exact kitControl-style recording:
      // change in zone temp from start, actual runtime minutes, minutes per degree.
      spaceTempChange = (float)(getSpaceTempAtBeginning().getValue() - getSpaceTemp().getValue());
      optimizedRuntimeMinutes = getLastStartTime().delta(now).getMinutes();
      observedMinutesPerDegree = (float)optimizedRuntimeMinutes / spaceTempChange;

      setRuntimePerDegreeCooling(weightedBlend(getRuntimePerDegreeCooling(), observedMinutesPerDegree));

      scoreStartModels(optimizedRuntimeMinutes);
      trainStartModel1(optimizedRuntimeMinutes, spaceTempChange, COOLING);
      trainStartModel2(optimizedRuntimeMinutes, COOLING);
      selectBestModelsIfReady();

      analysisComplete = true;
      getMessage().setValue(
        "Optimized start analysis done at " + now +
        ". Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
  }
  else
  {
    if (getSpaceTemp().getValue() > getSpaceTempAtBeginning().getValue() &&
        (getSpaceTemp().getValue() >= getLowerComfortLimit() || getScheduleStatus().getValue() == ACTIVE))
    {
      // Exact kitControl-style recording:
      // change in zone temp from start, actual runtime minutes, minutes per degree.
      spaceTempChange = (float)(getSpaceTemp().getValue() - getSpaceTempAtBeginning().getValue());
      optimizedRuntimeMinutes = getLastStartTime().delta(now).getMinutes();
      observedMinutesPerDegree = (float)optimizedRuntimeMinutes / spaceTempChange;

      setRuntimePerDegreeHeating(weightedBlend(getRuntimePerDegreeHeating(), observedMinutesPerDegree));

      scoreStartModels(optimizedRuntimeMinutes);
      trainStartModel1(optimizedRuntimeMinutes, spaceTempChange, HEATING);
      trainStartModel2(optimizedRuntimeMinutes, HEATING);
      selectBestModelsIfReady();

      analysisComplete = true;
      getMessage().setValue(
        "Optimized start analysis done at " + now +
        ". Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
  }
}

private boolean isCoolingStartAnalysis()
{
  return getSpaceTempAtBeginning().getValue() > getUpperComfortLimit();
}

private void handleStopAnalysis()
{
  if (controlModeAtBeginning == HEATING)
  {
    if (getSpaceTemp().getValue() < getSpaceTempAtBeginning().getValue() &&
        (getSpaceTemp().getValue() <= getLowerComfortLimit() || getScheduleStatus().getValue() == INACTIVE))
    {
      // Exact kitControl-style recording for optimized stop drift:
      // change in zone temp from stop start, drift minutes, minutes per degree.
      spaceTempChange = (float)(getSpaceTempAtBeginning().getValue() - getSpaceTemp().getValue());
      optimizedRuntimeMinutes = getLastStopTime().delta(now).getMinutes();
      observedMinutesPerDegree = (float)optimizedRuntimeMinutes / spaceTempChange;

      setDrifttimePerDegreeHeating(weightedBlend(getDrifttimePerDegreeHeating(), observedMinutesPerDegree));

      scoreStopModels(optimizedRuntimeMinutes);
      trainStopModel1(optimizedRuntimeMinutes, spaceTempChange, HEATING);
      trainStopModel2(optimizedRuntimeMinutes, HEATING);
      selectBestModelsIfReady();

      analysisComplete = true;
      getMessage().setValue(
        "Optimized stop analysis done at " + now +
        ". Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
  }
  else
  {
    if (getSpaceTemp().getValue() > getSpaceTempAtBeginning().getValue() &&
        (getSpaceTemp().getValue() >= getUpperComfortLimit() || getScheduleStatus().getValue() == INACTIVE))
    {
      // Exact kitControl-style recording for optimized stop drift:
      // change in zone temp from stop start, drift minutes, minutes per degree.
      spaceTempChange = (float)(getSpaceTemp().getValue() - getSpaceTempAtBeginning().getValue());
      optimizedRuntimeMinutes = getLastStopTime().delta(now).getMinutes();
      observedMinutesPerDegree = (float)optimizedRuntimeMinutes / spaceTempChange;

      setDrifttimePerDegreeCooling(weightedBlend(getDrifttimePerDegreeCooling(), observedMinutesPerDegree));

      scoreStopModels(optimizedRuntimeMinutes);
      trainStopModel1(optimizedRuntimeMinutes, spaceTempChange, COOLING);
      trainStopModel2(optimizedRuntimeMinutes, COOLING);
      selectBestModelsIfReady();

      analysisComplete = true;
      getMessage().setValue(
        "Optimized stop analysis done at " + now +
        ". Space temp is " + formatNumeric(getSpaceTemp().getValue(), "#0.0") + "."
      );
    }
  }
}

private float weightedBlend(float oldValue, float observedValue)
{
  return (oldValue * (float)getOldParameterMultiplier() + observedValue) /
         (float)(getOldParameterMultiplier() + 1);
}

// ==========================================================
// MODEL PREDICTION
// Default / Model 0 is the original Niagara kitControl runtime/drift calculation.
// Model 1 is the quadratic learned model: minutes = a * deltaT^2 + b.
// Model 2 is the PNNL-style OAT-ratio model.
// None of these methods change the recovery recording mechanism.
// ==========================================================
private double predictStartModel1(double deltaT, boolean bucket)
{
  if (bucket == COOLING)
  {
    return (model1StartCoolA * deltaT * deltaT) + model1StartCoolB;
  }
  return (model1StartHeatA * deltaT * deltaT) + model1StartHeatB;
}

private double predictStopModel1(double deltaT, boolean bucket)
{
  if (bucket == COOLING)
  {
    return (model1StopCoolA * deltaT * deltaT) + model1StopCoolB;
  }
  return (model1StopHeatA * deltaT * deltaT) + model1StopHeatB;
}

private double predictStartModel2(double deltaT, boolean bucket)
{
  double fallback = predictStartFallback(deltaT, bucket);

  if (!getOutsideTemp().getStatus().isValid())
  {
    return fallback;
  }

  double oat = getOutsideTemp().getValue();
  double baselineMins = (bucket == COOLING) ? model2StartCoolBaselineMins : model2StartHeatBaselineMins;
  double baselineOat = (bucket == COOLING) ? model2StartCoolBaselineOat : model2StartHeatBaselineOat;
  double tref = (bucket == COOLING) ? TREF_COOL_F : TREF_HEAT_F;

  return baselineMins * weatherRatio(tref, baselineOat, oat);
}

private double predictStopModel2(double deltaT, boolean bucket)
{
  double fallback = predictStopFallback(deltaT, bucket);

  if (!getOutsideTemp().getStatus().isValid())
  {
    return fallback;
  }

  double oat = getOutsideTemp().getValue();
  double baselineMins = (bucket == COOLING) ? model2StopCoolBaselineMins : model2StopHeatBaselineMins;
  double baselineOat = (bucket == COOLING) ? model2StopCoolBaselineOat : model2StopHeatBaselineOat;
  double tref = (bucket == COOLING) ? TREF_COOL_F : TREF_HEAT_F;

  return baselineMins * weatherRatio(tref, baselineOat, oat);
}

// Fallbacks are for prediction only. They do not alter learned values.
private double predictStartFallback(double deltaT, boolean bucket)
{
  if (bucket == COOLING) return deltaT * getRuntimePerDegreeCooling();
  return deltaT * getRuntimePerDegreeHeating();
}

private double predictStopFallback(double deltaT, boolean bucket)
{
  if (bucket == COOLING) return deltaT * getDrifttimePerDegreeCooling();
  return deltaT * getDrifttimePerDegreeHeating();
}

private double selectStartControlPrediction(double deltaT, boolean bucket)
{
  if (selectedStartModel == MODEL_1)
  {
    return predictStartModel1(deltaT, bucket);
  }
  if (selectedStartModel == MODEL_2)
  {
    return predictStartModel2(deltaT, bucket);
  }
  return predictStartFallback(deltaT, bucket);
}

private double selectStopControlPrediction(double deltaT, boolean bucket)
{
  if (selectedStopModel == MODEL_1)
  {
    return predictStopModel1(deltaT, bucket);
  }
  if (selectedStopModel == MODEL_2)
  {
    return predictStopModel2(deltaT, bucket);
  }
  return predictStopFallback(deltaT, bucket);
}

private double weatherRatio(double tref, double baselineOat, double currentOat)
{
  double numerator = Math.abs(tref - baselineOat);
  double denominator = Math.abs(tref - currentOat);

  if (denominator < 0.5)
  {
    denominator = 0.5;
  }

  return numerator / denominator;
}

private void captureStartPredictions()
{
  double deltaT = Math.abs(getSpaceTemp().getValue() - (isCoolingStartAnalysis() ? getUpperComfortLimit() : getLowerComfortLimit()));
  boolean bucket = isCoolingStartAnalysis() ? COOLING : HEATING;

  lastStartPredictionKitControl = predictStartFallback(deltaT, bucket);
  lastStartPredictionModel1 = predictStartModel1(deltaT, bucket);
  lastStartPredictionModel2 = predictStartModel2(deltaT, bucket);
}

private void captureStopPredictions()
{
  boolean bucket = controlModeAtBeginning;
  double deltaT;

  if (bucket == HEATING)
  {
    deltaT = getSpaceTemp().getValue() - getLowerComfortLimit();
  }
  else
  {
    deltaT = getUpperComfortLimit() - getSpaceTemp().getValue();
  }

  lastStopPredictionKitControl = predictStopFallback(deltaT, bucket);
  lastStopPredictionModel1 = predictStopModel1(deltaT, bucket);
  lastStopPredictionModel2 = predictStopModel2(deltaT, bucket);
}

// ==========================================================
// MODEL SCORING / SELECTION
// Mean squared error is updated only after the run is recorded.
// ==========================================================
private void scoreStartModels(double actualMinutes)
{
  startKitControlScoreCount++;
  startModel1ScoreCount++;
  startModel2ScoreCount++;

  startKitControlMse = updateMeanSquaredError(startKitControlMse, startKitControlScoreCount, lastStartPredictionKitControl, actualMinutes);
  startModel1Mse = updateMeanSquaredError(startModel1Mse, startModel1ScoreCount, lastStartPredictionModel1, actualMinutes);
  startModel2Mse = updateMeanSquaredError(startModel2Mse, startModel2ScoreCount, lastStartPredictionModel2, actualMinutes);
}

private void scoreStopModels(double actualMinutes)
{
  stopKitControlScoreCount++;
  stopModel1ScoreCount++;
  stopModel2ScoreCount++;

  stopKitControlMse = updateMeanSquaredError(stopKitControlMse, stopKitControlScoreCount, lastStopPredictionKitControl, actualMinutes);
  stopModel1Mse = updateMeanSquaredError(stopModel1Mse, stopModel1ScoreCount, lastStopPredictionModel1, actualMinutes);
  stopModel2Mse = updateMeanSquaredError(stopModel2Mse, stopModel2ScoreCount, lastStopPredictionModel2, actualMinutes);
}

private double updateMeanSquaredError(double oldMse, int count, double predicted, double actual)
{
  double error = predicted - actual;
  double squaredError = error * error;
  return oldMse + ((squaredError - oldMse) / (double)count);
}

private void selectBestModelsIfReady()
{
  if (startKitControlScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION &&
      startModel1ScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION &&
      startModel2ScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION)
  {
    selectedStartModel = MODEL_KITCONTROL;
    double best = startKitControlMse;

    if (startModel1Mse < best)
    {
      best = startModel1Mse;
      selectedStartModel = MODEL_1;
    }

    if (startModel2Mse < best)
    {
      selectedStartModel = MODEL_2;
    }
  }
  else
  {
    selectedStartModel = MODEL_KITCONTROL;
  }

  if (stopKitControlScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION &&
      stopModel1ScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION &&
      stopModel2ScoreCount >= MIN_SCORED_RUNS_FOR_MODEL_SELECTION)
  {
    selectedStopModel = MODEL_KITCONTROL;
    double best = stopKitControlMse;

    if (stopModel1Mse < best)
    {
      best = stopModel1Mse;
      selectedStopModel = MODEL_1;
    }

    if (stopModel2Mse < best)
    {
      selectedStopModel = MODEL_2;
    }
  }
  else
  {
    selectedStopModel = MODEL_KITCONTROL;
  }
}

// ==========================================================
// MODEL 1 TRAINING
// Trained only after the kitControl-style runtime/drift value has been recorded.
// The completed run record is the same record: actual minutes and zone delta.
// ==========================================================
private void trainStartModel1(double actualMinutes, double deltaT, boolean bucket)
{
  PerformanceRecord rec = new PerformanceRecord(System.currentTimeMillis(), actualMinutes, deltaT);

  if (bucket == COOLING)
  {
    startCoolHistory.add(rec);
    double[] fit = regressQuadratic(startCoolHistory, model1StartCoolA, model1StartCoolB);
    model1StartCoolA = model1StartCoolA + MODEL1_ALPHA * (fit[0] - model1StartCoolA);
    model1StartCoolB = model1StartCoolB + MODEL1_ALPHA * (fit[1] - model1StartCoolB);
  }
  else
  {
    startHeatHistory.add(rec);
    double[] fit = regressQuadratic(startHeatHistory, model1StartHeatA, model1StartHeatB);
    model1StartHeatA = model1StartHeatA + MODEL1_ALPHA * (fit[0] - model1StartHeatA);
    model1StartHeatB = model1StartHeatB + MODEL1_ALPHA * (fit[1] - model1StartHeatB);
  }
}

private void trainStopModel1(double actualMinutes, double deltaT, boolean bucket)
{
  PerformanceRecord rec = new PerformanceRecord(System.currentTimeMillis(), actualMinutes, deltaT);

  if (bucket == COOLING)
  {
    stopCoolHistory.add(rec);
    double[] fit = regressQuadratic(stopCoolHistory, model1StopCoolA, model1StopCoolB);
    model1StopCoolA = model1StopCoolA + MODEL1_ALPHA * (fit[0] - model1StopCoolA);
    model1StopCoolB = model1StopCoolB + MODEL1_ALPHA * (fit[1] - model1StopCoolB);
  }
  else
  {
    stopHeatHistory.add(rec);
    double[] fit = regressQuadratic(stopHeatHistory, model1StopHeatA, model1StopHeatB);
    model1StopHeatA = model1StopHeatA + MODEL1_ALPHA * (fit[0] - model1StopHeatA);
    model1StopHeatB = model1StopHeatB + MODEL1_ALPHA * (fit[1] - model1StopHeatB);
  }
}

private double[] regressQuadratic(java.util.List hist, double fallbackA, double fallbackB)
{
  if (hist.size() < 2)
  {
    return new double[] { fallbackA, fallbackB };
  }

  double n = (double)hist.size();
  double sumX = 0.0;
  double sumY = 0.0;
  double sumXY = 0.0;
  double sumXX = 0.0;

  for (int i = 0; i < hist.size(); i++)
  {
    PerformanceRecord r = (PerformanceRecord)hist.get(i);
    double x = r.deltaT * r.deltaT;
    double y = r.minutes;

    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumXX += x * x;
  }

  double denom = (n * sumXX) - (sumX * sumX);

  if (Math.abs(denom) < 0.000001)
  {
    return new double[] { fallbackA, fallbackB };
  }

  double a = ((n * sumXY) - (sumX * sumY)) / denom;
  double b = (sumY - (a * sumX)) / n;

  return new double[] { a, b };
}

// ==========================================================
// MODEL 2 TRAINING
// This uses the same completed run record, after the kitControl-style
// learned runtime/drift update has already happened.
// ==========================================================
private void trainStartModel2(double actualMinutes, boolean bucket)
{
  if (!getOutsideTempAtBeginning().getStatus().isValid()) return;

  double oat = getOutsideTempAtBeginning().getValue();

  if (bucket == COOLING)
  {
    model2StartCoolBaselineMins = weightedBlendDouble(model2StartCoolBaselineMins, actualMinutes);
    model2StartCoolBaselineOat = weightedBlendDouble(model2StartCoolBaselineOat, oat);
  }
  else
  {
    model2StartHeatBaselineMins = weightedBlendDouble(model2StartHeatBaselineMins, actualMinutes);
    model2StartHeatBaselineOat = weightedBlendDouble(model2StartHeatBaselineOat, oat);
  }
}

private void trainStopModel2(double actualMinutes, boolean bucket)
{
  if (!getOutsideTempAtBeginning().getStatus().isValid()) return;

  double oat = getOutsideTempAtBeginning().getValue();

  if (bucket == COOLING)
  {
    model2StopCoolBaselineMins = weightedBlendDouble(model2StopCoolBaselineMins, actualMinutes);
    model2StopCoolBaselineOat = weightedBlendDouble(model2StopCoolBaselineOat, oat);
  }
  else
  {
    model2StopHeatBaselineMins = weightedBlendDouble(model2StopHeatBaselineMins, actualMinutes);
    model2StopHeatBaselineOat = weightedBlendDouble(model2StopHeatBaselineOat, oat);
  }
}

private double weightedBlendDouble(double oldValue, double observedValue)
{
  return (oldValue * (double)getOldParameterMultiplier() + observedValue) /
         (double)(getOldParameterMultiplier() + 1);
}

// ==========================================================
// SLOT CHANGE SUPPORT
// Optional: call this from a slot/property changed hook if available.
// Lets user-defined values reset the learned values just like kitControl.
// ==========================================================
public void onChanged(Property property, Context context) throws Exception
{
  boolean parameterReset = false;

  if (property.equals(drifttimePerDegreeCoolingUserDefined))
  {
    setDrifttimePerDegreeCooling(getDrifttimePerDegreeCoolingUserDefined());
    parameterReset = true;
  }
  else if (property.equals(drifttimePerDegreeHeatingUserDefined))
  {
    setDrifttimePerDegreeHeating(getDrifttimePerDegreeHeatingUserDefined());
    parameterReset = true;
  }
  else if (property.equals(runtimePerDegreeCoolingUserDefined))
  {
    setRuntimePerDegreeCooling(getRuntimePerDegreeCoolingUserDefined());
    parameterReset = true;
  }
  else if (property.equals(runtimePerDegreeHeatingUserDefined))
  {
    setRuntimePerDegreeHeating(getRuntimePerDegreeHeatingUserDefined());
    parameterReset = true;
  }

  if (parameterReset)
  {
    setParameterResetTime(Clock.time());
  }
}

// ==========================================================
// HELPERS
// ==========================================================
private boolean inputsAreUsable()
{
  if (getNextEventTime() == null || getNextEventTime().equals(BAbsTime.NULL)) return false;
  if (getNextEventValue() == null) return false;
  if (getScheduleStatus() == null) return false;
  if (getSpaceTemp() == null || !getSpaceTemp().getStatus().isValid()) return false;
  return true;
}

private String formatNumeric(double value, String pattern)
{
  DecimalFormat format = new DecimalFormat(pattern);
  return format.format(value);
}
```

---

## 6. Learning Formula Notes

The learning path intentionally stays close to Niagara’s built-in optimized start/stop behavior.

For optimized start cooling:

```text
spaceTempChange = spaceTempAtBeginning - currentSpaceTemp
optimizedRuntimeMinutes = lastStartTime.delta(now).getMinutes()
observedMinutesPerDegree = optimizedRuntimeMinutes / spaceTempChange
runtimePerDegreeCooling = (oldRuntimePerDegreeCooling * oldParameterMultiplier + observedMinutesPerDegree) / (oldParameterMultiplier + 1)
```

For optimized start heating:

```text
spaceTempChange = currentSpaceTemp - spaceTempAtBeginning
optimizedRuntimeMinutes = lastStartTime.delta(now).getMinutes()
observedMinutesPerDegree = optimizedRuntimeMinutes / spaceTempChange
runtimePerDegreeHeating = (oldRuntimePerDegreeHeating * oldParameterMultiplier + observedMinutesPerDegree) / (oldParameterMultiplier + 1)
```

For optimized stop heating drift:

```text
spaceTempChange = spaceTempAtBeginning - currentSpaceTemp
optimizedRuntimeMinutes = lastStopTime.delta(now).getMinutes()
observedMinutesPerDegree = optimizedRuntimeMinutes / spaceTempChange
drifttimePerDegreeHeating = (oldDrifttimePerDegreeHeating * oldParameterMultiplier + observedMinutesPerDegree) / (oldParameterMultiplier + 1)
```

For optimized stop cooling drift:

```text
spaceTempChange = currentSpaceTemp - spaceTempAtBeginning
optimizedRuntimeMinutes = lastStopTime.delta(now).getMinutes()
observedMinutesPerDegree = optimizedRuntimeMinutes / spaceTempChange
drifttimePerDegreeCooling = (oldDrifttimePerDegreeCooling * oldParameterMultiplier + observedMinutesPerDegree) / (oldParameterMultiplier + 1)
```

That is the clean recording mechanism: zone temperature delta, elapsed recovery/drift time, and the built-in weighted average. The two-model prediction logic is scored after the run finishes, but it does not replace or modify the runtime/drift recording calculation.

---

## 7. Final Field Check

This implementation intentionally keeps the fragile field behavior simple:

- No minimum recovery-time filter is used before recording the learned runtime/drift value.
- No minimum delta-T filter is used before recording the learned runtime/drift value.
- No artificial derate, boost, weather adder, or safety factor is mixed into the learned runtime/drift value.
- Optimized start and optimized stop both record the same way as the Niagara `kitControl` pattern.
- The original kitControl prediction, Model 1, and Model 2 are scored with mean squared error only after a completed run is recorded. Model 1 is quadratic; Model 2 is OAT-ratio.
- The default control model is the original kitControl runtime/drift prediction until all three models have at least `MIN_SCORED_RUNS_FOR_MODEL_SELECTION` scored runs.
- After that gate is satisfied, the lower-MSE winner among kitControl fallback, Model 1, and Model 2 is selected for the next run. The winner is recalculated after every completed run, so it can continuously switch as conditions change.
