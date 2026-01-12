# GL36 Trim & Respond

This sub‑guide focuses on the **Trim & Respond** methodology defined in ASHRAE Guideline 36.  It covers variable definitions, VAV box zone requests and supply/duct static pressure resets.  The sections below are copied verbatim from the original README.

---


## ⚠️ **Pre-Built GL36 AHU Trim and Respond Wiresheets** (see below)

> NOTE: Parameters must be updated if using metric units; the default units are imperial.


![Prebuilts](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/GL36_PreBuilt_WireSheet.png)

---

<details>
<summary>📘 GL36 Trim & Respond Variable Definitions</summary>

This section summarizes the **standard Guideline 36 (GL36) variable names and definitions** used across all Trim & Respond control blocks — including **AHU Supply Air Temperature Reset**, **Duct Static Pressure Reset**, and **Pump Differential Pressure Reset**.

Prebuilt Niagara `.bog` examples using these variables are available here:  
👉 [`bog_files/`](https://github.com/bbartling/n4-hvac-optimization-blocks/tree/develop/bog_files)

---

### Table 5.1.14.3 — Trim & Respond Variables

| Variable | Definition |
|-----------|-------------|
| **Device** | Associated device (e.g., fan, pump) |
| **SP₀** | Initial setpoint |
| **SPmin** | Minimum setpoint |
| **SPmax** | Maximum setpoint |
| **Td** | Delay timer |
| **T** | Time step |
| **I** | Number of ignored requests |
| **R** | Number of requests from zones or systems |
| **SPtrim** | Trim amount |
| **SPres** | Respond amount (must be opposite in sign to SPtrim) |
| **SPres-max** | Maximum response per time interval (same sign as SPres) |

> **Informative Note:** The number of ignored requests (**I**) should be set to zero for critical zones or air handlers.

---

These variables form the **core logic foundation** for all GL36-based supervisory reset sequences implemented in this repository.

</details>



<details>
<summary>🌬️ GL36 VAV Box Zone Request Generator</summary>

> This block typicall runs on a wire sheet for the VAV box points where then the output request count data is brought into the AHU JACE via the Niagara network.


![GL36 VAV Box Request Counter](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/gl36VavBoxReqCounter.png)

#### Slot Map (Guideline 36 → Niagara ProgramObject)

| G36 Variable | Description | Niagara Slot Name |
|---------------|--------------|-------------------|
| **ZoneTemp** | Zone temperature | *zoneTemp* |
| **ZoneCoolingSpt** | Zone cooling setpoint | *zoneCoolingSpt* |
| **ZoneDemand** | Cooling loop (terminal load %) | *zoneDemand* |
| **VavFlow** | Measured airflow | *vavFlow* |
| **VavFlowSpt** | Airflow setpoint | *vavFlowSpt* |
| **VavDamperCmd** | Damper command (%) | *vavDamperCmd* |
| **VavCoolRequests** | Cooling requests (0-3) | *vavCoolRequests* |
| **VavPressureRequests** | Pressure requests (0-3) | *vavPressureRequests* |
| **TempStatusTrace** | Cooling request debug trace | *tempStatusTrace* |
| **PressStatusTrace** | Pressure request debug trace | *pressStatusTrace* |
| **useImperial** | Unit toggle (°F/°C display) | *useImperial* |

#### Algorithm 

**Cooling SAT Requests**  
- If zone temp ≥ setpoint + 3 °C (5 °F) for 2 min → 3 requests  
- Else if zone temp ≥ setpoint + 2 °C (3 °F) for 2 min → 2 requests  
- Else if cooling loop > 95 % → 1 request (until < 85 %)  
- Else → 0 requests  

**Static Pressure Requests**  
- If flow < 50 % of setpoint and damper ≥ 95 % for 1 min → 3 requests  
- Else if flow < 70 % of setpoint and damper ≥ 95 % for 1 min → 2 requests  
- Else if damper ≥ 95 % → 1 request (until < 85 %)  
- Else → 0 requests  

Timers, hysteresis, and suppression logic follow the official Guideline 36 durations (1-minute persistence for pressure, 2-minute persistence for temperature).  
Both pressure and temperature loops run independently in the same ProgramObject.

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java

////////////////////////////////////////////////////////////
// Class-level fields & constants
////////////////////////////////////////////////////////////

Clock.Ticket ticket;

// ===== Global timing (shared period) =====
private static final int EXEC_PERIOD_SEC = 10;    // Program executes every 10 seconds

// ===== Pressure timing / thresholds (UNCHANGED ALGORITHM) =====
private static final int PRESS_PERSIST_SEC = 60; // 1 minute persistence
private static final double PRESS_RATIO_3REQ      = 0.50;
private static final double PRESS_DAMPER_3REQ_MIN = 95.0;
private static final double PRESS_RATIO_2REQ      = 0.70;
private static final double PRESS_DAMPER_2REQ_MIN = 95.0;
private static final double PRESS_DAMPER_1REQ_ON  = 95.0;
private static final double PRESS_DAMPER_1REQ_OFF = 85.0;

// ===== Temperature timing / thresholds (UNCHANGED ALGORITHM) =====
private static final double TEMP_HIGH_DIFF_C = 3.0;
private static final double TEMP_MED_DIFF_C  = 2.0;

private static final double TEMP_HIGH_DIFF_F = 5.0;
private static final double TEMP_MED_DIFF_F  = 3.0;

private static final int TEMP_PERSIST_SEC    = 120; // 2 minutes
private static final int TEMP_SUPPRESS_SEC   = 60;  // 1 minute

private static final double TEMP_LOOP_1REQ_ON  = 95.0;
private static final double TEMP_LOOP_1REQ_OFF = 85.0;

// ===== Sanity ranges (NEW) =====
// Pressure inputs
private static final double SANITY_DAMPER_MIN_PCT = -10.0;
private static final double SANITY_DAMPER_MAX_PCT = 110.0;
private static final double SANITY_FLOW_MIN       = -10.0;
private static final double SANITY_FLOW_MAX       = 100000.0;

// Temp inputs by unit system
private static final double SANITY_MIN_C = 0.0;
private static final double SANITY_MAX_C = 50.0;
private static final double SANITY_MIN_F = 32.0;
private static final double SANITY_MAX_F = 125.0;

// Zone demand special range (as requested)
private static final double DEMAND_SANITY_MIN  = -200.0;
private static final double DEMAND_SANITY_MAX  = 200.0;

// ===== Pressure timers and state =====
double pressHighTimerSec = 0.0;
double pressMedTimerSec  = 0.0;
int    lastPressureReq   = 0;
double lastPressDamperPct = 0.0;
double lastPressFlowRatio = 0.0;

// ===== Temperature timers and state =====
double tempHighTimerSec     = 0.0;
double tempMedTimerSec      = 0.0;
double tempSuppressTimerSec = 0.0;
int    lastTempReq          = 0;
double lastTempDiff         = 0.0;
double lastTempLoopPct      = 0.0;

////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////

void updateTimer() {
  if (ticket != null) {
    ticket.cancel();
  }
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(EXEC_PERIOD_SEC),
      BProgram.execute,
      null
  );
}

void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
  try {
    Slot slot = getComponent().getSlot(slotName);
    if (slot == null) return;
    BLink[] links = getComponent().getLinks(slot);
    if (links == null || links.length == 0) {
      point.setValue(0);
      point.setStatus(BStatus.NULL);
    }
  } catch (Exception e) { /* ignore */ }
}

int clampInt(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

double round1(double v) {
  return Math.round(v * 10.0) / 10.0;
}

// Data validity = Status.Ok AND within [min,max]
boolean isDataValid(BStatusNumeric slot, double min, double max) {
  if (slot == null) return false;
  if (!slot.getStatus().isOk()) return false;
  double val = slot.getValue();
  if (val < min) return false;
  if (val > max) return false;
  return true;
}

////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////

public void onStart() throws Exception {
  // Reset all internal timers and state variables
  pressHighTimerSec = 0.0;
  pressMedTimerSec  = 0.0;
  lastPressureReq   = 0;
  lastPressDamperPct = 0.0;
  lastPressFlowRatio = 0.0;

  tempHighTimerSec     = 0.0;
  tempMedTimerSec      = 0.0;
  tempSuppressTimerSec = 0.0;
  lastTempReq          = 0;
  lastTempDiff         = 0.0;
  lastTempLoopPct      = 0.0;

  // Initialize Unit System (Default to Metric/false if missing or NULL)
  try {
    if (getUseImperial() != null && getUseImperial().isNull()) {
      getUseImperial().setValue(false);
    }
  } catch (Exception e) { /* ignore */ }

  if (getPressStatusTrace() != null) {
    getPressStatusTrace().setValue("G36 VAV Pressure Request logic started.");
  }
  if (getTempStatusTrace() != null) {
    getTempStatusTrace().setValue("G36 VAV Temperature Request logic started.");
  }

  updateTimer();
}

public void onStop() throws Exception {
  if (ticket != null) {
    ticket.cancel();
    ticket = null;
  }
}

////////////////////////////////////////////////////////////
// Main Execute
////////////////////////////////////////////////////////////

public void onExecute() throws Exception {
  updateTimer();

  // Normalize unwired inputs → NULL (does NOT affect the tested algorithm)
  ensureNumericWiredOrNull("vavDamperCmd",   getVavDamperCmd());
  ensureNumericWiredOrNull("vavFlow",        getVavFlow());
  ensureNumericWiredOrNull("vavFlowSpt",     getVavFlowSpt());
  ensureNumericWiredOrNull("zoneCoolingSpt", getZoneCoolingSpt());
  ensureNumericWiredOrNull("zoneTemp",       getZoneTemp());
  ensureNumericWiredOrNull("zoneDemand",     getZoneDemand());

  // Determine Unit System (default metric)
  boolean isImperial = false;
  try {
    if (getUseImperial() != null && getUseImperial().getStatus().isOk()) {
      isImperial = getUseImperial().getValue();
    }
  } catch (Exception e) { /* ignore */ }

  // Advance temperature suppression timer (UNCHANGED behavior)
  if (tempSuppressTimerSec < TEMP_SUPPRESS_SEC) {
    tempSuppressTimerSec += EXEC_PERIOD_SEC;
    if (tempSuppressTimerSec > TEMP_SUPPRESS_SEC) {
      tempSuppressTimerSec = TEMP_SUPPRESS_SEC;
    }
  }

  // Compute requests independently (separate fail-safes)
  int pressReq = computePressureRequest();
  int coolReq  = computeTemperatureRequest(isImperial);

  // Clamp outputs
  pressReq = clampInt(pressReq, 0, 3);
  coolReq  = clampInt(coolReq, 0, 3);

  // Write outputs (no extra slots)
  getVavPressureRequests().setValue(pressReq);
  getVavCoolRequests().setValue(coolReq);

  // Save hysteresis state
  lastPressureReq = pressReq;
  lastTempReq     = coolReq;

  // Debug traces
  if (getPressStatusTrace() != null) {
    double flowPct = lastPressFlowRatio * 100.0;
    String pMsg = "Req=" + pressReq +
                  " Dmp=" + round1(lastPressDamperPct) + "%" +
                  " Flow/Stpt=" + round1(flowPct) + "%" +
                  " Tmr[Hi=" + (int)pressHighTimerSec + "s" +
                  "/Med=" + (int)pressMedTimerSec + "s]";
    getPressStatusTrace().setValue(pMsg);
  }

  if (getTempStatusTrace() != null) {
    String unit = isImperial ? "F" : "C";
    String tMsg = "Req=" + coolReq +
                  " dT=" + round1(lastTempDiff) + unit +
                  " Loop=" + round1(lastTempLoopPct) + "%" +
                  " Tmr[Hi=" + (int)tempHighTimerSec + "s" +
                  "/Med=" + (int)tempMedTimerSec + "s]";
    getTempStatusTrace().setValue(tMsg);
  }
}

////////////////////////////////////////////////////////////
// Pressure Request Logic (G36 algorithm preserved; adds sanity checks)
////////////////////////////////////////////////////////////

int computePressureRequest() {
  BStatusNumeric damperSlot = getVavDamperCmd();
  BStatusNumeric flowSlot   = getVavFlow();
  BStatusNumeric spSlot     = getVavFlowSpt();

  boolean damperOk = isDataValid(damperSlot, SANITY_DAMPER_MIN_PCT, SANITY_DAMPER_MAX_PCT);
  boolean flowOk   = isDataValid(flowSlot,   SANITY_FLOW_MIN,      SANITY_FLOW_MAX);
  boolean spOk     = isDataValid(spSlot,     SANITY_FLOW_MIN,      SANITY_FLOW_MAX);

  // Pressure fail-safe ONLY affects pressure
  if (!damperOk || !flowOk || !spOk) {
    pressHighTimerSec  = 0.0;
    pressMedTimerSec   = 0.0;
    lastPressDamperPct = 0.0;
    lastPressFlowRatio = 0.0;
    return 0;
  }

  double damper = damperSlot.getValue();
  double flow   = flowSlot.getValue();
  double sp     = spSlot.getValue();

  double ratio = 1.0;
  if (sp > 0.0) {
    ratio = flow / sp;
  } else {
    // If setpoint is zero/negative, treat as invalid for ratio-based requests
    pressHighTimerSec  = 0.0;
    pressMedTimerSec   = 0.0;
    lastPressDamperPct = damper;
    lastPressFlowRatio = 0.0;
    return 0;
  }

  lastPressDamperPct = damper;
  lastPressFlowRatio = ratio;

  // 3 requests (1-minute persistence)
  boolean cond3 = (ratio < PRESS_RATIO_3REQ) && (damper >= PRESS_DAMPER_3REQ_MIN);
  if (cond3) {
    pressHighTimerSec += EXEC_PERIOD_SEC;
  } else {
    pressHighTimerSec = 0.0;
  }
  if (pressHighTimerSec >= PRESS_PERSIST_SEC) {
    pressMedTimerSec = 0.0;
    return 3;
  }

  // 2 requests (1-minute persistence)
  boolean cond2 = (ratio < PRESS_RATIO_2REQ) && (damper >= PRESS_DAMPER_2REQ_MIN);
  if (cond2) {
    pressMedTimerSec += EXEC_PERIOD_SEC;
  } else {
    pressMedTimerSec = 0.0;
  }
  if (pressMedTimerSec >= PRESS_PERSIST_SEC) {
    return 2;
  }

  // 1 request with hysteresis
  if (damper > PRESS_DAMPER_1REQ_ON) {
    return 1;
  }
  if (lastPressureReq == 1 && damper >= PRESS_DAMPER_1REQ_OFF) {
    return 1;
  }

  return 0;
}

////////////////////////////////////////////////////////////
// Temperature Request Logic (G36 algorithm preserved; adds sanity checks)
////////////////////////////////////////////////////////////

int computeTemperatureRequest(boolean isImperial) {

  // Explicit constant selection (no ternary)
  double validMin;
  double validMax;
  double highDiff;
  double medDiff;

  if (isImperial) {
    validMin = SANITY_MIN_F;
    validMax = SANITY_MAX_F;
    highDiff = TEMP_HIGH_DIFF_F;
    medDiff  = TEMP_MED_DIFF_F;
  } else {
    validMin = SANITY_MIN_C;
    validMax = SANITY_MAX_C;
    highDiff = TEMP_HIGH_DIFF_C;
    medDiff  = TEMP_MED_DIFF_C;
  }

  BStatusNumeric spSlot     = getZoneCoolingSpt();
  BStatusNumeric tempSlot   = getZoneTemp();
  BStatusNumeric demandSlot = getZoneDemand();

  boolean spOk     = isDataValid(spSlot,     validMin, validMax);
  boolean tempOk   = isDataValid(tempSlot,   validMin, validMax);
  boolean demandOk = isDataValid(demandSlot, DEMAND_SANITY_MIN, DEMAND_SANITY_MAX);

  // Temp fail-safe ONLY affects temperature
  if (!spOk || !tempOk || !demandOk) {
    tempHighTimerSec = 0.0;
    tempMedTimerSec  = 0.0;
    lastTempDiff     = 0.0;
    lastTempLoopPct  = 0.0;
    return 0;
  }

  double sp     = spSlot.getValue();
  double tz     = tempSlot.getValue();
  double demand = demandSlot.getValue();

  double diff = tz - sp; // positive = too warm
  lastTempDiff    = diff;
  lastTempLoopPct = demand;

  // 3 & 2 requests only after suppression time has elapsed (UNCHANGED behavior)
  if (tempSuppressTimerSec >= TEMP_SUPPRESS_SEC) {
    if (diff >= highDiff) {
      tempHighTimerSec += EXEC_PERIOD_SEC;
      tempMedTimerSec   = 0.0;
    } else if (diff >= medDiff) {
      tempMedTimerSec  += EXEC_PERIOD_SEC;
      tempHighTimerSec  = 0.0;
    } else {
      tempHighTimerSec = 0.0;
      tempMedTimerSec  = 0.0;
    }

    if (tempHighTimerSec >= TEMP_PERSIST_SEC) return 3;
    if (tempMedTimerSec  >= TEMP_PERSIST_SEC) return 2;
  } else {
    // While suppressed, do not accumulate deviation timers
    tempHighTimerSec = 0.0;
    tempMedTimerSec  = 0.0;
  }

  // 1 request based on loop saturation with hysteresis (UNCHANGED)
  if (demand > TEMP_LOOP_1REQ_ON) {
    return 1;
  }
  if (lastTempReq == 1 && demand >= TEMP_LOOP_1REQ_OFF) {
    return 1;
  }

  return 0;
}



```

</details>



<details>
<summary>🌀 GL36 AHU Duct Static Pressure Reset (Trim & Respond)</summary>

![Duct Static Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/ahuDuctStaticResetSnip.png)

This ProgramObject implements **ASHRAE Guideline 36 – Section 5.1.14.4**, which defines the **Trim & Respond control strategy** for resetting AHU **duct static pressure setpoints**.  
The logic continuously adjusts the fan’s static pressure setpoint based on damper position requests from terminal units, minimizing fan energy use while maintaining occupant comfort.

---

### 📘 Guideline 36 – Table 5.1.14.4 Example Sequence T&R Variables

| Variable | Definition | Value / Typical Mapping |
|-----------|-------------|------------------------|
| **Device** | The device under control | *Supply Fan* |
| **SP₀** | Initial static pressure setpoint | **120 Pa (0.5 in. w.c.)** → `SP0` |
| **SPmin** | Minimum duct static pressure | **37 Pa (0.15 in. w.c.)** → `SPmin` |
| **SPmax** | Maximum duct static pressure | **370 Pa (1.50 in. w.c.)** → `SPmax` |
| **Td** | Delay before control starts (minutes) | **5 min** → `StartUpDelayMinutes` |
| **T** | Control interval between trim/respond actions | **2 min** → `UpdateMinutes` |
| **I** | Number of ignored requests | **2** → `Ignore` |
| **R** | Total number of VAV damper requests | `totalRequests` |
| **SPtrim** | Increment to **decrease** duct pressure setpoint each interval | **–10 Pa (–0.04 in. w.c.)** → `SPtrim` |
| **SPres** | Increment to **increase** duct pressure setpoint per request | **+15 Pa (+0.06 in. w.c.)** → `SPres` |
| **SPres-max** | Maximum cumulative pressure increase | **+37 Pa (+0.15 in. w.c.)** → `SPResMax` |

---

### 🧩 Niagara Slot Map

| G36 Variable | Description | Niagara Slot Name |
|---------------|-------------|-------------------|
| **Device** | Supply Fan Run Command | `fanRunCmd` |
| **SP₀** | Initial Static Pressure Setpoint | `SP0` |
| **SPmin** | Minimum Duct Static Pressure | `SPmin` |
| **SPmax** | Maximum Duct Static Pressure | `SPmax` |
| **Td** | Startup Delay (min) | `StartUpDelayMinutes` |
| **T** | Update Interval (min) | `UpdateMinutes` |
| **I** | Ignored Requests | `Ignore` |
| **R** | VAV Pressure Requests | `totalRequests` |
| **SPtrim** | Trim Increment | `SPtrim` |
| **SPres** | Respond Increment | `SPres` |
| **SPres-max** | Max Respond Limit | `SPResMax` |

---

### ⚙️ Functional Summary

- Lowers duct static pressure setpoint (“trim”) when few or no zones demand air.  
- Raises static pressure (“respond”) when multiple dampers approach full open.  
- Reduces fan energy by dynamically finding the lowest stable setpoint.  
- Executes every `T` minutes after an initial delay `Td`.  
- Supports ignored-request tolerance (`I`) to prevent oscillation.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java

/**
 * Duct Static Pressure Trim & Respond Program
 * Version 5.2 - Strict Status Semantics + Soft-Reboot on Bad Data (NO algorithm changes).
 *
 * Policy Updates (Status/Sanity ONLY):
 *  - If fanRunCmd is anything but {ok} -> SOFT REBOOT:
 *      * drive SP0
 *      * set output status = fault
 *      * reset internal timers/state (startup delay + cadence)
 *      * statusTrace explains why
 *  - If totalRequests is anything but {ok} when core logic is due -> SOFT REBOOT:
 *      * drive SP0
 *      * set output status = fault
 *      * reset internal timers/state (startup delay + cadence)
 *      * statusTrace explains why
 *  - Output status is set back to {ok} ONLY after a successful Trim/Respond step
 *    (i.e., R is valid, newSetpoint is computed and written).
 *
 * Maintained:
 *  - State machine, cadence timing, startup delay timing, trim/respond math.
 */

////////////////////////////////////////////////////////////
// Class-level state
////////////////////////////////////////////////////////////

Clock.Ticket ticket;

long lastMainLogicRunMs = 0;   // enforces UpdateMinutes cadence
long fanOnStableSinceMs = 0;   // enforces StartUpDelayMinutes true-for window
boolean lastFanRun = false;    // edge detect for fan ON

////////////////////////////////////////////////////////////
// onStart
////////////////////////////////////////////////////////////

public void onStart() throws Exception {
    getStatusTrace().setValue("sp-trim-and-respond: program started.");
    lastMainLogicRunMs = 0;
    fanOnStableSinceMs = 0;
    lastFanRun = false;
    updateTimer(); // 10s heartbeat
}

////////////////////////////////////////////////////////////
// onExecute (Main logic loop)
////////////////////////////////////////////////////////////

public void onExecute() throws Exception {
    updateTimer();
    long now = System.currentTimeMillis();

    // ---- Null-wire checker (inputs only) ----
    ensureNumericWiredOrNull("totalRequests", getTotalRequests());
    ensureBooleanWiredOrNull("fanRunCmd", getFanRunCmd());

    // ---- Read config with safe defaults ----
    double SP0      = numericOrDefault(getSP0(), 1.25);
    double SPmin    = numericOrDefault(getSPmin(), 0.40);
    double SPmax    = numericOrDefault(getSPmax(), 1.75);
    int TdSec       = minutesToSecondsSafe(getStartUpDelayMinutes(), 10);
    int TSec        = minutesToSecondsSafe(getUpdateMinutes(), 2);
    double Ignore   = numericOrDefault(getIgnore(), 6.0);
    double SPtrim   = numericOrDefault(getSPtrim(), -0.02);
    double SPres    = numericOrDefault(getSPres(), 0.04);
    double SPResMax = numericOrDefault(getSPResMax(), 0.08);

    // Determine current SP (fallback to SP0 if output isn't Ok)
    double currentSp = getDischargeAirPressureSp().getStatus().isOk()
        ? getDischargeAirPressureSp().getValue()
        : SP0;

    // ------------------------------------------------------------
    // REQUIRED INPUT #1: fanRunCmd must be {ok}
    // If not ok -> soft reboot to SP0 and restart state machine.
    // ------------------------------------------------------------
    if (!getFanRunCmd().getStatus().isOk()) {
        softRebootToSP0(now, SP0, SPmin, SPmax, "fanRunCmd not Ok");
        return;
    }

    boolean fanRun = getFanRunCmd().getValue();

    // --- State 1: Fan is OFF ---
    // Drive SP0. DO NOT clear status to OK here (strict semantics).
    if (!fanRun) {
        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0);

        if (lastFanRun) {
            getStatusTrace().setValue("Fan OFF -> driving SP0 = " + round3(sp0));
            getLastActionTs().setValue(new java.util.Date(now).toString());
        }

        fanOnStableSinceMs = 0;
        lastFanRun = false;
        return;
    }

    // --- State 2: Fan just turned ON (Edge Detection) ---
    // Begin startup delay window. Drive SP0. DO NOT clear status to OK here.
    if (!lastFanRun && fanRun) {
        fanOnStableSinceMs = now;
        lastFanRun = true;

        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0);

        getStatusTrace().setValue("Fan ON -> holding SP0 during startup delay...");
        getLastActionTs().setValue(new java.util.Date(now).toString());
        return;
    }

    // Ensure fan state is correct for the current cycle
    lastFanRun = true;

    // --- State 3: Fan is ON, but waiting for startup delay to complete ---
    // Hold SP0. DO NOT clear status to OK here.
    boolean isStartupDelayMet = (now - fanOnStableSinceMs) / 1000 >= TdSec;
    if (!isStartupDelayMet) {
        long remaining = TdSec - ((now - fanOnStableSinceMs) / 1000);

        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0);

        getStatusTrace().setValue("Waiting Td (" + remaining + "s left)... SP=" + round3(sp0));
        return;
    }

    // --- State 4: Waiting for T&R update cadence ---
    boolean isUpdateCadenceMet = (lastMainLogicRunMs == 0) || ((now - lastMainLogicRunMs) / 1000 >= TSec);
    if (!isUpdateCadenceMet) {
        // Safe return; previous cycle already set output
        return;
    }

    // --- State 5: Run Core Trim & Respond Logic ---
    // ------------------------------------------------------------
    // REQUIRED INPUT #2: totalRequests must be {ok} when core logic is due
    // If not ok -> soft reboot to SP0 and restart state machine.
    // ------------------------------------------------------------
    if (!getTotalRequests().getStatus().isOk()) {
        softRebootToSP0(now, SP0, SPmin, SPmax, "totalRequests not Ok");
        return;
    }

    double R = getTotalRequests().getValue();

    double newSetpoint;
    String action;

    // ===== CORE TRIM/RESPOND (UNCHANGED) =====
    if (R <= Ignore) {
        action = "trim";
        newSetpoint = clamp(currentSp + SPtrim, SPmin, SPmax);
    } else {
        action = "respond";
        double respondAmount = Math.min(SPres * (R - Ignore), SPResMax);
        newSetpoint = clamp(currentSp + respondAmount, SPmin, SPmax);
    }
    // =======================================

    // Successful T&R step: write value and ONLY NOW clear status to OK.
    getDischargeAirPressureSp().setValue(newSetpoint);
    getDischargeAirPressureSp().setStatus(BStatus.ok);

    lastMainLogicRunMs = now;

    String detail = "R=" + round3(R) + " -> " + action.toUpperCase() +
                    " SP: " + round3(currentSp) + " -> " + round3(newSetpoint);
    getStatusTrace().setValue(detail);
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

////////////////////////////////////////////////////////////
// onStop
////////////////////////////////////////////////////////////

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

////////////////////////////////////////////////////////////
// Helper Methods
////////////////////////////////////////////////////////////

void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

/**
 * Soft reboot behavior:
 *  - Drive SP0
 *  - Mark output FAULT
 *  - Reset all internal timers/state so startup delay and cadence restart cleanly
 *  - Message goes to statusTrace (not BStatus)
 */
void softRebootToSP0(long now, double SP0, double SPmin, double SPmax, String reason) {
    double sp0 = clamp(SP0, SPmin, SPmax);

    getDischargeAirPressureSp().setValue(sp0);
    getDischargeAirPressureSp().setStatus(BStatus.fault);

    // Reset internal state (true "reboot")
    lastMainLogicRunMs = 0;
    fanOnStableSinceMs = 0;
    lastFanRun = false;

    getStatusTrace().setValue("RESTART: " + reason + " -> driving SP0=" + round3(sp0) + " and re-running startup delay.");
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
    try {
        Slot slot = getComponent().getSlot(slotName);
        if (slot == null) return;
        BLink[] links = getComponent().getLinks(slot);
        if (links == null || links.length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL); // if this fails in your Niagara build, use BStatus.nullStatus
        }
    } catch (Exception e) { /* ignore */ }
}

void ensureBooleanWiredOrNull(String slotName, BStatusBoolean point) {
    try {
        Slot slot = getComponent().getSlot(slotName);
        if (slot == null) return;
        BLink[] links = getComponent().getLinks(slot);
        if (links == null || links.length == 0) {
            point.setValue(false);
            point.setStatus(BStatus.NULL); // if this fails in your Niagara build, use BStatus.nullStatus
        }
    } catch (Exception e) { /* ignore */ }
}

double clamp(double v, double lo, double hi) {
    return Math.max(lo, Math.min(v, hi));
}

int minutesToSecondsSafe(BStatusNumeric minsSlot, int defMin) {
    double m = defMin;
    if (minsSlot != null && minsSlot.getStatus().isOk()) {
        m = minsSlot.getValue();
    }
    m = Math.max(0.0, Math.min(m, 240.0)); // Clamp 0–240 min
    return (int)Math.round(m * 60.0);
}

double numericOrDefault(BStatusNumeric slot, double defVal) {
    if (slot != null && slot.getStatus().isOk()) {
        return slot.getValue();
    }
    return defVal;
}

double round3(double v) {
    return Math.round(v * 1000.0) / 1000.0;
}
```

</details>



<details>
<summary>🌡️ GL36 AHU Supply Air Temperature Reset (Trim & Respond)</summary>

![SAT Reset Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/ahuLeaveTempBlockSnip.png)


This ProgramObject implements **ASHRAE Guideline 36 – Trim & Respond**, which governs how the **AHU Supply Air Temperature (SAT)** setpoint resets based on cooling requests from zones served by the AHU.

The Trim & Respond algorithm continuously adjusts the SAT setpoint upward (“trim”) or downward (“respond”) depending on the number of active cooling requests, keeping supply air temperature as high as possible while still satisfying zone loads.

---

### 📘 Guideline 36 – Trim & Respond Variables

| Variable | Description | Value / Niagara Mapping |
|-----------|--------------|--------------------------|
| **Device** | The control device that implements the logic | *Supply Fan* |
| **SP₀** | Initial Setpoint before trim/respond logic begins | `SPmax` |
| **SPmin** | Minimum allowable cooling supply air temperature | `Min_ClgSAT` |
| **SPmax** | Maximum allowable cooling supply air temperature | `Max_ClgSAT` |
| **Td** | Delay time before control begins after startup | **10 minutes** (`StartUpDelayMinutes`) |
| **T** | Interval between trim/respond evaluations | **2 minutes** (`UpdateMinutes`) |
| **I** | Number of ignored requests before responding | **2** (`Ignore`) |
| **R** | Total number of active zone cooling requests | `totalRequests` |
| **SPtrim** | Amount SAT is raised (trimmed) per interval | **+0.1°C (+0.2°F)** (`SPtrim`) |
| **SPres** | Amount SAT is lowered (responded) per request | **–0.2°C (–0.3°F)** (`SPres`) |
| **SPres-max** | Maximum cumulative respond limit | **–0.6°C (–1.0°F)** (`SPResMax`) |

---

### 🌡️ Example Configuration

| Parameter | Typical Value | Description |
|------------|----------------|-------------|
| **Min_ClgSAT** | 12 °C (55 °F) | Lowest achievable SAT during full load |
| **Max_ClgSAT** | 18 °C (65 °F) | Highest SAT during minimal load |
| **OAT_Min** | 16 °C (60 °F) | Lower boundary for SAT reset curve |
| **OAT_Max** | 21 °C (70 °F) | Upper boundary for SAT reset curve |

The **diamond** in the G36 reference figure represents the target SAT (“T-max”) at 60 °F OAT, which varies between **SPmin** and **SPmax** based on the number of zone cooling requests.

---

### 🧩 Niagara Slot Map

| G36 Variable | Description | Niagara Slot Name |
|---------------|--------------|-------------------|
| **Device** | Supply Fan Run Command | `fanRunCmd` |
| **SP₀** | Initial Setpoint | `SP0` |
| **SPmin** | Minimum Cooling SAT | `SPmin` |
| **SPmax** | Maximum Cooling SAT | `SPmax` |
| **Td** | Startup Delay (min) | `StartUpDelayMinutes` |
| **T** | Update Interval (min) | `UpdateMinutes` |
| **I** | Ignored Requests | `Ignore` |
| **R** | Zone Cooling Requests | `totalRequests` |
| **SPtrim** | Trim Increment | `SPtrim` |
| **SPres** | Respond Increment | `SPres` |
| **SPres-max** | Max Respond Limit | `SPResMax` |

---

### ⚙️ Functional Summary

- Adjusts SAT based on **zone cooling demand intensity**.
- Maintains comfort while improving **compressor efficiency** by maximizing SAT when load is low.
- Responds faster when multiple cooling requests occur.
- Executes on a timed interval (`T`), after an initial delay (`Td`).

---


### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java

/**
 * AHU Supply Air Temperature (SAT) Trim & Respond Program
 * Version 8.1 - Strict Status Semantics + Soft-Reboot on Bad Data (NO algorithm changes).
 *
 * Adds (Status/Sanity ONLY):
 *  - If fanRunCmd is anything but {ok} -> SOFT REBOOT:
 *      * drive SP0 (and reset tMaxState to SP0)
 *      * set output status = fault
 *      * reset internal timers/state (startup delay + cadence)
 *      * statusTrace explains why
 *  - If outsideAirTemp is anything but {ok} -> SOFT REBOOT:
 *      * drive SP0 (and reset tMaxState to SP0)
 *      * set output status = fault
 *      * reset internal timers/state (startup delay + cadence)
 *      * statusTrace explains why
 *  - If totalRequests is anything but {ok} when core logic is due -> SOFT REBOOT:
 *      * drive SP0 (and reset tMaxState to SP0)
 *      * set output status = fault
 *      * reset internal timers/state (startup delay + cadence)
 *      * statusTrace explains why
 *  - Output status is set back to {ok} ONLY after a successful Trim/Respond step
 *    (i.e., R is valid, tMaxState updated, newSetpoint computed and written).
 *
 * Maintained:
 *  - State machine, cadence timing, startup delay timing
 *  - Interpolation shape/limits
 *  - Trim/respond math on tMaxState
 *  - Fan OFF behavior resetting SP and tMaxState to SP0 (your v8 fix remains)
 */

////////////////////////////////////////////////////////////
// Class-level state
////////////////////////////////////////////////////////////

// ===== Class-level state =====
Clock.Ticket ticket;

long lastMainLogicRunMs = 0;   // enforces UpdateMinutes cadence
long fanOnStableSinceMs = 0;   // enforces StartUpDelayMinutes true-for window
boolean lastFanRun = false;    // edge detect for fan ON
private double tMaxState = 70.0; // Private variable to hold tMax state

////////////////////////////////////////////////////////////
// onStart
////////////////////////////////////////////////////////////

public void onStart() throws Exception {
    getStatusTrace().setValue("sat-trim-and-respond: program started.");
    lastMainLogicRunMs = 0;
    fanOnStableSinceMs = 0;
    lastFanRun = false;

    // === G36 naming: SP0 / SPmax ===
    // SP0 is the initial setpoint. If it’s not wired/valid, fall back to SPmax.
    double sp0 = numericOrDefault(getSP0(),
                   numericOrDefault(getSPmax(), 70.0));
    this.tMaxState = sp0;

    updateTimer(); // 10s heartbeat
}

////////////////////////////////////////////////////////////
// onExecute (Main logic loop)
////////////////////////////////////////////////////////////

public void onExecute() throws Exception {
    updateTimer();
    long now = System.currentTimeMillis();

    // ---- Null-wire checker (inputs only) ----
    ensureNumericWiredOrNull("totalRequests", getTotalRequests());
    ensureBooleanWiredOrNull("fanRunCmd", getFanRunCmd());
    ensureNumericWiredOrNull("outsideAirTemp", getOutsideAirTemp());

    // ---- Read config with safe defaults (G36 names) ----
    double minSAT    = numericOrDefault(getSPmin(), 55.0);  // SPmin
    double maxSAT    = numericOrDefault(getSPmax(), 70.0);  // SPmax
    double minOAT    = numericOrDefault(getOatMin(), 60.0);
    double maxOAT    = numericOrDefault(getOatMax(), 70.0);
    int TdSec        = minutesToSecondsSafe(getStartUpDelayMinutes(), 10); // Td
    int TSec         = minutesToSecondsSafe(getUpdateMinutes(), 2);        // T
    double Ignore    = numericOrDefault(getIgnore(), 2.0);                 // I
    double trimVal   = numericOrDefault(getSPtrim(), 0.2);                 // SPtrim
    double respVal   = numericOrDefault(getSPres(), -0.3);                 // SPres
    double respMax   = numericOrDefault(getSPResMax(), -1.0);              // SPres-max

    // Compute SP0 using your existing fallback logic (SP0 -> SPmax -> maxSAT)
    double sp0 = numericOrDefault(getSP0(),
                   numericOrDefault(getSPmax(), maxSAT));
    sp0 = clamp(sp0, minSAT, maxSAT);

    // Determine current SP (fallback to maxSAT if output isn't Ok)
    double currentSp = getDischargeAirTempSp().getStatus().isOk()
                       ? getDischargeAirTempSp().getValue()
                       : maxSAT;

    // ------------------------------------------------------------
    // REQUIRED INPUT #1: fanRunCmd must be {ok}
    // If not ok -> soft reboot to SP0 and restart state machine.
    // ------------------------------------------------------------
    if (!getFanRunCmd().getStatus().isOk()) {
        softRebootToSP0(now, sp0, minSAT, maxSAT, "fanRunCmd not Ok");
        return;
    }

    // ------------------------------------------------------------
    // REQUIRED INPUT #2: outsideAirTemp must be {ok}
    // If not ok -> soft reboot to SP0 and restart state machine.
    // (We do NOT attempt to "fake" OAT if you want strict semantics)
    // ------------------------------------------------------------
    if (!getOutsideAirTemp().getStatus().isOk()) {
        softRebootToSP0(now, sp0, minSAT, maxSAT, "outsideAirTemp not Ok");
        return;
    }

    boolean fanRun = getFanRunCmd().getValue();
    double oat = getOutsideAirTemp().getValue();

    // --- State 1: Fan is OFF ---
    // (Your v8 FIX remains: reset both internal state and output SP to SP0)
    // Strict semantics: DO NOT clear status to OK here.
    if (!fanRun) {
        this.tMaxState = clamp(sp0, minSAT, maxSAT);
        getDischargeAirTempSp().setValue(this.tMaxState);

        if (lastFanRun) {
            getStatusTrace().setValue("Fan OFF -> resetting SP to SP0 = " + round1(this.tMaxState));
            getLastActionTs().setValue(new java.util.Date(now).toString());
        }

        fanOnStableSinceMs = 0;
        lastFanRun = false;
        return;
    }

    // --- State 2: Fan just turned ON (Edge Detection) ---
    // Begin startup delay window. Reinitialize tMaxState from SP0.
    // Strict semantics: DO NOT clear status to OK here.
    if (!lastFanRun && fanRun) {
        fanOnStableSinceMs = now;
        lastFanRun = true;

        this.tMaxState = clamp(sp0, minSAT, maxSAT);

        double newSetpoint = interpolate(oat, minOAT, this.tMaxState,
                                         maxOAT, minSAT, minSAT, maxSAT);
        getDischargeAirTempSp().setValue(newSetpoint);

        getStatusTrace().setValue("Fan ON -> holding initial SP during startup delay...");
        getLastActionTs().setValue(new java.util.Date(now).toString());
        return;
    }

    lastFanRun = true;

    // --- State 3: Fan is ON, but waiting for startup delay ---
    // Strict semantics: DO NOT clear status to OK here.
    boolean isStartupDelayMet = (now - fanOnStableSinceMs) / 1000 >= TdSec;
    if (!isStartupDelayMet) {
        long remaining = TdSec - ((now - fanOnStableSinceMs) / 1000);

        double newSetpoint = interpolate(oat, minOAT, this.tMaxState,
                                         maxOAT, minSAT, minSAT, maxSAT);
        getDischargeAirTempSp().setValue(newSetpoint);

        getStatusTrace().setValue("Waiting Td (" + remaining + "s left)... SP=" + round1(newSetpoint));
        return;
    }

    // --- State 4: Waiting for T&R update cadence ---
    boolean isUpdateCadenceMet = (lastMainLogicRunMs == 0) ||
                                 ((now - lastMainLogicRunMs) / 1000 >= TSec);
    if (!isUpdateCadenceMet) {
        return; // value already driven
    }

    // --- State 5: Run Core Trim & Respond Logic ---
    // ------------------------------------------------------------
    // REQUIRED INPUT #3: totalRequests must be {ok} when core logic is due
    // If not ok -> soft reboot to SP0 and restart state machine.
    // ------------------------------------------------------------
    if (!getTotalRequests().getStatus().isOk()) {
        softRebootToSP0(now, sp0, minSAT, maxSAT, "totalRequests not Ok");
        return;
    }

    double R = getTotalRequests().getValue();   // G36 R

    // ===== CORE TRIM/RESPOND (UNCHANGED) =====
    String action;
    if (R <= Ignore) {
        action = "trim";
        // T-max trim up toward SPmax when requests are low
        this.tMaxState = clamp(this.tMaxState + trimVal, minSAT, maxSAT);
    } else {
        action = "respond";
        double respondAmount = Math.max(respVal * (R - Ignore), respMax);
        this.tMaxState = clamp(this.tMaxState + respondAmount, minSAT, maxSAT);
    }
    // =======================================

    double newSetpoint = interpolate(oat, minOAT, this.tMaxState,
                                     maxOAT, minSAT, minSAT, maxSAT);
    getDischargeAirTempSp().setValue(newSetpoint);

    // Successful T&R step: ONLY NOW clear status to OK.
    getDischargeAirTempSp().setStatus(BStatus.ok);

    lastMainLogicRunMs = now;

    String detail = "R=" + round1(R) + " -> " + action.toUpperCase()
                    + " -> tMax=" + round1(this.tMaxState)
                    + " -> Final SP=" + round1(newSetpoint);
    getStatusTrace().setValue(detail);
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

////////////////////////////////////////////////////////////
// onStop
////////////////////////////////////////////////////////////

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

////////////////////////////////////////////////////////////
// Helper Methods (algorithm unchanged)
////////////////////////////////////////////////////////////

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

/**
 * Soft reboot behavior:
 *  - Drive SP0 directly (and reset tMaxState to SP0)
 *  - Mark output FAULT
 *  - Reset all internal timers/state so startup delay and cadence restart cleanly
 *  - Message goes to statusTrace (not BStatus)
 */
void softRebootToSP0(long now, double sp0, double minSAT, double maxSAT, String reason) {
    double safeSp0 = clamp(sp0, minSAT, maxSAT);

    // Reset internal state to SP0
    this.tMaxState = safeSp0;

    // Drive safe output and flag fault
    getDischargeAirTempSp().setValue(safeSp0);
    getDischargeAirTempSp().setStatus(BStatus.fault);

    // Reset internal timing/state (true "reboot")
    lastMainLogicRunMs = 0;
    fanOnStableSinceMs = 0;
    lastFanRun = false;

    getStatusTrace().setValue("RESTART: " + reason + " -> driving SP0=" + round1(safeSp0) + " and re-running startup delay.");
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL); // if this fails in your Niagara build, use BStatus.nullStatus
        }
    } catch (Exception e) { /* ignore */ }
}

void ensureBooleanWiredOrNull(String slotName, BStatusBoolean point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(false);
            point.setStatus(BStatus.NULL); // if this fails in your Niagara build, use BStatus.nullStatus
        }
    } catch (Exception e) { /* ignore */ }
}

double clamp(double v, double lo, double hi) {
    return Math.max(lo, Math.min(v, hi));
}

int minutesToSecondsSafe(BStatusNumeric minsSlot, int defMin) {
    double m = defMin;
    if (minsSlot.getStatus().isOk()) m = minsSlot.getValue();
    m = Math.max(0.0, Math.min(m, 240.0));
    return (int)Math.round(m * 60.0);
}

double numericOrDefault(BStatusNumeric slot, double defVal) {
    return slot.getStatus().isOk() ? slot.getValue() : defVal;
}

double round1(double v) {
    return Math.round(v * 10.0) / 10.0;
}

/**
 * Linear interpolation function. Calculates a Y value for a given X value
 * on a line defined by two points (x1, y1) and (x2, y2).
 * Also clamps the result within finalMin and finalMax.
 */
double interpolate(double currentX, double x1, double y1,
                   double x2, double y2,
                   double finalMin, double finalMax) {
    if (currentX <= x1) return y1;
    if (currentX >= x2) return y2;

    if (Math.abs(x1 - x2) < 0.001) return y1;

    double slope = (y2 - y1) / (x2 - x1);
    double result = y1 + slope * (currentX - x1);

    return clamp(result, finalMin, finalMax);
}

```

</details>

---

<details>
<summary>🧊 SIMPLE - GL36 Chiller Plant Enable Logic</summary>

![GL36 Logic Snip](https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/GL_Chiller_Plant_Enable_Snip.png)

This ProgramObject implements **ASHRAE Guideline 36 – Section 5.18.15.2, Chiller Plant Requests**, extended for **multiple AHUs** with built-in minimum ON/OFF times and request counting.

> **G36 Text (5.18.15.2)**  
> a. If the CHW valve position is greater than 95%, send 1 request until the CHW valve position is less than 10%.  
> b. Else if the CHW valve position is less than 95%, send 0 requests.

In this Niagara implementation:

- Each AHU cooling valve input is treated as a **CHW valve position**.  
- The ProgramObject counts how many AHUs are “requesting” and enforces minimum ON/OFF times before starting or stopping the chiller plant.

---

### 📘 Guideline 36 → Niagara Mapping

#### Per-AHU Inputs (CHW Valve Positions)

| G36 Concept | Description | Niagara Slot Name | Type |
|------------|-------------|-------------------|------|
| `CHWv₁` | AHU 1 CHW / cooling valve position (%) | `ahuClgVlv1` | `BStatusNumeric` |
| `CHWv₂` | AHU 2 CHW / cooling valve position (%) | `ahuClgVlv2` | `BStatusNumeric` |
| `CHWv₃` | AHU 3 CHW / cooling valve position (%) | `ahuClgVlv3` | `BStatusNumeric` |
| `CHWv₄` | AHU 4 CHW / cooling valve position (%) | `ahuClgVlv4` | `BStatusNumeric` |
| `CHWv₅` | AHU 5 CHW / cooling valve position (%) | `ahuClgVlv5` | `BStatusNumeric` |
| `CHWv₆` | AHU 6 CHW / cooling valve position (%) | `ahuClgVlv6` | `BStatusNumeric` |
| `CHWv₇` | AHU 7 CHW / cooling valve position (%) | `ahuClgVlv7` | `BStatusNumeric` |
| `CHWv₈` | AHU 8 CHW / cooling valve position (%) | `ahuClgVlv8` | `BStatusNumeric` |
| `CHWv₉` | AHU 9 CHW / cooling valve position (%) | `ahuClgVlv9` | `BStatusNumeric` |
| `CHWv₁₀` | AHU 10 CHW / cooling valve position (%) | `ahuClgVlv10` | `BStatusNumeric` |
| `CHWv₁₁` | AHU 11 CHW / cooling valve position (%) | `ahuClgVlv11` | `BStatusNumeric` |
| `CHWv₁₂` | AHU 12 CHW / cooling valve position (%) | `ahuClgVlv12` | `BStatusNumeric` |
| `CHWv₁₃` | AHU 13 CHW / cooling valve position (%) | `ahuClgVlv13` | `BStatusNumeric` |
| `CHWv₁₄` | AHU 14 CHW / cooling valve position (%) | `ahuClgVlv14` | `BStatusNumeric` |
| `CHWv₁₅` | AHU 15 CHW / cooling valve position (%) | `ahuClgVlv15` | `BStatusNumeric` |
| `CHWv₁₆` | AHU 16 CHW / cooling valve position (%) | `ahuClgVlv16` | `BStatusNumeric` |
| `CHWv₁₇` | AHU 17 CHW / cooling valve position (%) | `ahuClgVlv17` | `BStatusNumeric` |
| `CHWv₁₈` | AHU 18 CHW / cooling valve position (%) | `ahuClgVlv18` | `BStatusNumeric` |
| `CHWv₁₉` | AHU 19 CHW / cooling valve position (%) | `ahuClgVlv19` | `BStatusNumeric` |
| `CHWv₂₀` | AHU 20 CHW / cooling valve position (%) | `ahuClgVlv20` | `BStatusNumeric` |

Each of these inputs is evaluated against the **request** and **disable** thresholds below.

---

#### Thresholds, Timers & Request Counting

| G36 Concept | Description | Niagara Slot Name | Type | Notes |
|-------------|-------------|-------------------|------|-------|
| `> 95 %` request threshold | Valve % above which an AHU sends a plant request | `requestThresholdPct` | `BStatusNumeric` | Default 95 %, clamped to ≥ 30 % |
| `< 10 %` clear threshold | Valve % below which the request is cleared | `disableThresholdPct` | `BStatusNumeric` | Fixed at 10 %, treated as read-only |
| **Minimum ON time** | Minimum chiller run time before it may stop | `minOnTimeMinutes` | `BStatusNumeric` | Default 10 min, clamped to ≥ 10 min |
| **Minimum OFF time** | Minimum chiller off time before it may restart | `minOffTimeMinutes` | `BStatusNumeric` | Default 10 min, clamped to ≥ 10 min |
| **Required AHUs** | Number of AHUs that must be “requesting” | `numOfAhusReq` | `BStatusNumeric` | Default 2, clamped to ≥ 1 |
| Σ requests | Total AHUs currently in request state | `totalRequests` | `BStatusNumeric` | 0…20, updated every 10 s |
| Status text | Human-readable trace of logic state | `statusTrace` | `BStatusString` | Shows timers, counts, ON/OFF reason |

---

#### Outputs

| G36 Concept | Description | Niagara Slot Name | Type |
|-------------|-------------|-------------------|------|
| `PlantReq` | Chiller plant enable / request | `chillerEnableCommand` | `BStatusBoolean` |

`chillerEnableCommand == true` when:

- At least `numOfAhusReq` AHUs have valve > `requestThresholdPct`, **and**  
- The plant has been OFF for at least `minOffTimeMinutes`.

The command drops to `false` when:

- All AHU valves fall below `disableThresholdPct` (10 %) **and**  
- The plant has been ON for at least `minOnTimeMinutes`.

---


### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/*
 * GL36 Chiller Plant Enable Controller
 * This program enables a chiller plant based on a count of AHU
 * cooling valve requests. It includes logic to prevent short-cycling
 * by enforcing minimum on and off times.
 *
 * It is designed to count requests based on an adjustable threshold
 * (e.g., 95%) and enable the plant when a sufficient number of
 * AHUs are requesting.
 *
 * REFACTORED to use final constants for defaults and add safety clamps.
 */

// ===== Class-level state =====
Clock.Ticket ticket;
boolean chillerRunning = false; // Internal state of the chiller
int offTimeCounterSeconds = 0;  // Tracks OFF time in seconds
int onTimeCounterSeconds  = 0;  // Tracks ON time in seconds

// An array to store the "request" state for each AHU
// 0 = Off, 1 = Requesting
int[] ahuRequestStates = new int[20];

// ===== Default Constants =====
private static final double REQ_THRESH_DEFAULT = 95.0;
private static final double DIS_THRESH_DEFAULT = 10.0; // This is read-only
private static final double NUM_REQ_DEFAULT = 2.0;
private static final double MIN_ON_DEFAULT = 10.0;
private static final double MIN_OFF_DEFAULT = 10.0;

// ===== Clamping Minimums =====
private static final double REQ_THRESH_MIN = 30.0;
private static final double MIN_ON_OFF_CLAMP_MIN = 10.0; // 10 minute minimum


// ===== Lifecycle Methods =====

public void onStart() throws Exception {
    // Initialize all AHU request states to 0 (Off)
    for (int i = 0; i < 20; i++) {
        ahuRequestStates[i] = 0;
    }

    // Initialize outputs (defaults are now set in onExecute)
    try { getChillerEnableCommand().setValue(false); } catch (Exception e) {}
    try { getTotalRequests().setValue(0.0); } catch (Exception e) {}
    getStatusTrace().setValue("Program started. Awaiting inputs.");

    updateTimer(); // Schedule recurring execution
}

public void onExecute() throws Exception {
    updateTimer(); // Reschedule every 10 seconds

    // --- 1. Get Configuration with Safe Defaults & Clamps ---

    // --- Request Threshold (min 30.0) ---
    double reqThresh = numericOrDefault(getRequestThresholdPct(), REQ_THRESH_DEFAULT);
    if (reqThresh < REQ_THRESH_MIN) {
        reqThresh = REQ_THRESH_MIN;
        try { getRequestThresholdPct().setValue(REQ_THRESH_MIN); } catch (Exception e) {} // Write back clamped value
    }
    
    // --- Disable Threshold (read-only 10.0) ---
    double disThresh = DIS_THRESH_DEFAULT;
    try { getDisableThresholdPct().setValue(DIS_THRESH_DEFAULT); } catch (Exception e) {} // Ensure slot reflects read-only value
    
    // --- Number of AHUs Required ---
    double numReq = numericOrDefault(getNumOfAhusReq(), NUM_REQ_DEFAULT);
    if (numReq < 1.0) { // Ensure at least 1 request is needed
        numReq = 1.0;
        try { getNumOfAhusReq().setValue(1.0); } catch (Exception e) {}
    }

    // --- Min On Time (min 10.0) ---
    double minOnMinutes = numericOrDefault(getMinOnTimeMinutes(), MIN_ON_DEFAULT);
    if (minOnMinutes < MIN_ON_OFF_CLAMP_MIN) {
        minOnMinutes = MIN_ON_OFF_CLAMP_MIN;
        try { getMinOnTimeMinutes().setValue(MIN_ON_OFF_CLAMP_MIN); } catch (Exception e) {} // Write back clamped value
    }

    // --- Min Off Time (min 10.0) ---
    double minOffMinutes = numericOrDefault(getMinOffTimeMinutes(), MIN_OFF_DEFAULT);
    if (minOffMinutes < MIN_ON_OFF_CLAMP_MIN) {
        minOffMinutes = MIN_ON_OFF_CLAMP_MIN;
        try { getMinOffTimeMinutes().setValue(MIN_ON_OFF_CLAMP_MIN); } catch (Exception e) {} // Write back clamped value
    }

    // Convert to seconds for logic
    int minOnSec  = (int)(minOnMinutes * 60);
    int minOffSec = (int)(minOffMinutes * 60);


    // --- NEW: Null-wire checker for inputs ---
    ensureNumericWiredOrNull("ahuClgVlv1", getAhuClgVlv1());
    ensureNumericWiredOrNull("ahuClgVlv2", getAhuClgVlv2());
    ensureNumericWiredOrNull("ahuClgVlv3", getAhuClgVlv3());
    ensureNumericWiredOrNull("ahuClgVlv4", getAhuClgVlv4());
    ensureNumericWiredOrNull("ahuClgVlv5", getAhuClgVlv5());
    ensureNumericWiredOrNull("ahuClgVlv6", getAhuClgVlv6());
    ensureNumericWiredOrNull("ahuClgVlv7", getAhuClgVlv7());
    ensureNumericWiredOrNull("ahuClgVlv8", getAhuClgVlv8());
    ensureNumericWiredOrNull("ahuClgVlv9", getAhuClgVlv9());
    ensureNumericWiredOrNull("ahuClgVlv10", getAhuClgVlv10());
    ensureNumericWiredOrNull("ahuClgVlv11", getAhuClgVlv11());
    ensureNumericWiredOrNull("ahuClgVlv12", getAhuClgVlv12());
    ensureNumericWiredOrNull("ahuClgVlv13", getAhuClgVlv13());
    ensureNumericWiredOrNull("ahuClgVlv14", getAhuClgVlv14());
    ensureNumericWiredOrNull("ahuClgVlv15", getAhuClgVlv15());
    ensureNumericWiredOrNull("ahuClgVlv16", getAhuClgVlv16());
    ensureNumericWiredOrNull("ahuClgVlv17", getAhuClgVlv17());
    ensureNumericWiredOrNull("ahuClgVlv18", getAhuClgVlv18());
    ensureNumericWiredOrNull("ahuClgVlv19", getAhuClgVlv19());
    ensureNumericWiredOrNull("ahuClgVlv20", getAhuClgVlv20());
    // --- END NEW ---

    // --- 2. Count AHU Requests ---
    BStatusNumeric[] ahus = {
        getAhuClgVlv1(), getAhuClgVlv2(), getAhuClgVlv3(), getAhuClgVlv4(), getAhuClgVlv5(),
        getAhuClgVlv6(), getAhuClgVlv7(), getAhuClgVlv8(), getAhuClgVlv9(), getAhuClgVlv10(),
        getAhuClgVlv11(), getAhuClgVlv12(), getAhuClgVlv13(), getAhuClgVlv14(), getAhuClgVlv15(),
        getAhuClgVlv16(), getAhuClgVlv17(), getAhuClgVlv18(), getAhuClgVlv19(), getAhuClgVlv20()
    };

    int currentRequestCount = 0;
    int wiredInputCount = 0;

    for (int i = 0; i < 20; i++) {
        // This check now safely handles unwired slots set to NULL
        if (ahus[i].getStatus().isOk()) {
            wiredInputCount++;
            double valve = ahus[i].getValue();
            
            // ASHRAE G36 Logic:
            // - If valve > 95%, set request state to 1
            // - If valve < 10%, set request state to 0
            // - If between, hold last state
            if (valve >= reqThresh) {
                ahuRequestStates[i] = 1;
            } else if (valve <= disThresh) {
                ahuRequestStates[i] = 0;
            }
            // Add to the total count if this AHU is in a request state
            currentRequestCount += ahuRequestStates[i];
        } else {
            // Unwired or bad input, clear its request state
            ahuRequestStates[i] = 0;
        }
    }
    getTotalRequests().setValue(currentRequestCount);

    // --- 3. Handle System Enable/Disable Logic ---
    
    // If no AHUs are wired, force the chiller off.
    if (wiredInputCount == 0) {
        chillerRunning = false;
        onTimeCounterSeconds = 0;
        offTimeCounterSeconds = 0;
        getStatusTrace().setValue("No AHU inputs wired. Chiller forced OFF.");
        getChillerEnableCommand().setValue(false); // Use boolean
        return;
    }

    boolean enableCondition = (currentRequestCount >= numReq);
    boolean disableCondition = (currentRequestCount == 0); // Disable only when ALL requests are clear
    String trace = "";

    if (!chillerRunning) {
        // --- Chiller is OFF ---
        onTimeCounterSeconds = 0;
        offTimeCounterSeconds += 10; // Increment OFF timer

        if (enableCondition) {
            if (offTimeCounterSeconds >= minOffSec) {
                // START the chiller
                chillerRunning = true;
                offTimeCounterSeconds = 0;
                trace = "Status: STARTED | Wired: " + wiredInputCount + " | Req: " + currentRequestCount + "/" + (int)numReq + " | OffTimer: " + offTimeCounterSeconds + "s | Min Off Time met.";
            } else {
                trace = "Status: OFF | Wired: " + wiredInputCount + " | Req: " + currentRequestCount + "/" + (int)numReq + " | OffTimer: " + offTimeCounterSeconds + "s | Waiting for Min Off Time (" + (minOffSec - offTimeCounterSeconds) + "s left).";
            }
        } else {
            trace = "Status: OFF | Wired: " + wiredInputCount + " | Req: " + currentRequestCount + "/" + (int)numReq + " | OffTimer: " + offTimeCounterSeconds + "s | Waiting for requests.";
        }
        
    } else {
        // --- Chiller is ON ---
        offTimeCounterSeconds = 0;
        onTimeCounterSeconds += 10; // Increment ON timer

        if (disableCondition) {
            if (onTimeCounterSeconds >= minOnSec) {
                // STOP the chiller
                chillerRunning = false;
                onTimeCounterSeconds = 0;
                trace = "Status: STOPPED | Wired: " + wiredInputCount + " | Req: " + currentRequestCount + "/" + (int)numReq + " | OnTimer: " + onTimeCounterSeconds + "s | Min On Time met.";
            } else {
                // *** FIXED LINE HERE ***
                trace = "Status: ON | Wired: " + wiredInputCount
                      + " | Req: " + currentRequestCount + "/" + (int)numReq
                      + " | OnTimer: " + onTimeCounterSeconds + "s | Waiting for Min On Time ("
                      + (minOnSec - onTimeCounterSeconds) + "s left).";
            }
        } else {
            // Normal running
            trace = "Status: ON | Wired: " + wiredInputCount
                    + " | Req: " + currentRequestCount + "/" + (int)numReq
                    + " | OnTimer: " + onTimeCounterSeconds + "s | Running normally.";
        }
    }


    // --- 4. Update Final Outputs ---
    // Fixed to use boolean for the output
    getChillerEnableCommand().setValue(chillerRunning);
    getStatusTrace().setValue(trace);
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
}

// ===== Helper Methods =====

// Helper to run onExecute every 10 seconds
void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    ticket = Clock.schedule(
        getComponent(),
        BRelTime.makeSeconds(10),
        BProgram.execute,
        null
    );
}

// --- NEW: Helper to check for unwired inputs ---
void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL);
        }
    } catch (Exception e) { /* ignore */ }
}

// Helper to get numeric value or default
double numericOrDefault(BStatusNumeric slot, double defVal) {
    if (slot != null && slot.getStatus().isOk()) {
        return slot.getValue();
    }
    return defVal;
}

```

</details>


---

<details>
<summary>🍃 Central Plant AHU Request Counter (Heating + Cooling)</summary>

This block typically runs on an AHU wire sheet. Its outputs (`0…3` requests) are then networked to the Central Plant JACE and summed into a plant-level Trim & Respond loop.

### How the request counter works

Each mode (cooling/heating) produces an integer request level:

* **0** = satisfied (no request)
* **1** = saturated valve (coil “trying hard”)
* **2** = failing (moderate temperature error for long enough)
* **3** = critical (large temperature error for long enough)

### Error definitions

| Mode    | Error (°F)           |
| ------- | -------------------- |
| Cooling | `SAT − SAT_Setpoint` |
| Heating | `SAT_Setpoint − SAT` |

### Parallel timer behavior

This uses **parallel timers** so that a **critical** error also advances the **failing** timer. If the error drops from “massive” to “moderate,” the failing timer does **not** lose progress.

| Error band (abs magnitude)     | Req 3 Timer (Critical) | Req 2 Timer (Failing) | Resulting behavior                                 |
| ------------------------------ | ---------------------: | --------------------: | -------------------------------------------------- |
| **Critical** (≥ 10°F)          |              counts up |             counts up | builds toward Req=3, also preserves Req=2 progress |
| **Failing** (≥ 5°F and < 10°F) |            resets to 0 |             counts up | builds toward Req=2                                |
| **Satisfied** (< 5°F)          |            resets to 0 |           resets to 0 | clears both timers                                 |

### What each request level means

| Request | Meaning   | Trigger (summary)                                                         |
| ------: | --------- | ------------------------------------------------------------------------- |
|   **3** | Critical  | error ≥ 10°F for **10 min**                                               |
|   **2** | Failing   | error ≥ 5°F for **5 min** (with parallel accumulation from Critical band) |
|   **1** | Saturated | valve latched “ON” (≥95%) and not yet released (<85%)                     |
|   **0** | Satisfied | none of the above                                                         |

### Slot map (per AHU/FCU)

#### Inputs

| Slot Name               | Type             | Notes                                                                            |
| ----------------------- | ---------------- | -------------------------------------------------------------------------------- |
| `supplyAirTemp`         | `BStatusNumeric` | Supply/discharge temp after coils. Required.                                     |
| `supplyAirTempSetpoint` | `BStatusNumeric` | Active SAT setpoint. Required.                                                   |
| `coolValveCommand`      | `BStatusNumeric` | Optional. If null/unwired → cooling ladder disabled.                             |
| `heatValveCommand`      | `BStatusNumeric` | Optional. If null/unwired → heating ladder disabled.                             |
| `fanStatus`             | `BStatusBoolean` | If `false` → reset timers and force outputs to 0. Defaults to `true` if unwired. |

#### Outputs

| Slot Name            | Type             | Notes                                  |
| -------------------- | ---------------- | -------------------------------------- |
| `coolingRequests`    | `BStatusNumeric` | Integer 0…3 request level for cooling. |
| `heatingRequests`    | `BStatusNumeric` | Integer 0…3 request level for heating. |
| `coolingStatusTrace` | `BStatusString`  | Human-readable cooling ladder trace.   |
| `heatingStatusTrace` | `BStatusString`  | Human-readable heating ladder trace.   |

</details>


### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.



```java
// ==========================================
// 1. STATEFUL FIELDS (Class Level)
// ==========================================
/* * DEVELOPER MODIFICATION NOTE:
 * Modified per site requirements & technician recommendation (10yrs exp).
 * * CHANGES:
 * 1. Widened Error Thresholds: 
 * - Level 3 (Critical) now requires > 10.0 deg deviation (was 5.0)
 * - Level 2 (Failing)  now requires >  5.0 deg deviation (was 3.0)
 * * 2. Extended Timers (De-bouncing):
 * - Level 3 (Critical) delay increased to 10 MINUTES (was 2m/5m)
 * - Level 2 (Failing)  delay increased to  5 MINUTES (was 2m/5m)
 * * 3. Status Trace:
 * - Reformatted for better readability on graphics.
 */

private Clock.Ticket ticket;
private static final int EXEC_PERIOD_SEC = 10;
private long lastRunMillis = 0L; 

// --- Adjusted Thresholds (Wider) ---
private static final double COOL_ERR_CRITICAL = 10.0; // Level 3 Trigger
private static final double COOL_ERR_FAILING  =  5.0; // Level 2 Trigger
private static final double HEAT_ERR_CRITICAL = 10.0; // Level 3 Trigger
private static final double HEAT_ERR_FAILING  =  5.0; // Level 2 Trigger

// --- Adjusted Timers (Slower) ---
private static final int TIME_LIMIT_CRITICAL = 600; // 10 Minutes
private static final int TIME_LIMIT_FAILING  = 300; //  5 Minutes

private static final double VALVE_ON_PCT     = 95.0;
private static final double VALVE_OFF_PCT    = 85.0;

// Sanity Limits
private static final double SANITY_VALVE_MIN = -5.0;
private static final double SANITY_VALVE_MAX = 105.0;
private static final double SANITY_TEMP_MIN  = -50.0;
private static final double SANITY_TEMP_MAX  = 250.0;

// Internal State (Renamed for clarity)
private double  coolTimerCritical  = 0; 
private double  coolTimerFailing   = 0;
private boolean coolValveLatched   = false;

private double  heatTimerCritical  = 0;
private double  heatTimerFailing   = 0;
private boolean heatValveLatched   = false;

// ==========================================
// 2. LIFECYCLE METHODS
// ==========================================

public void onStart() throws Exception {
    lastRunMillis = System.currentTimeMillis(); 
    scheduleNextRun();
}

public void onExecute() throws Exception {
    try {
        long now = System.currentTimeMillis();
        // Time step calculation with clamp
        double stepSeconds = (now - lastRunMillis) / 1000.0;
        if (stepSeconds < 0.0) stepSeconds = EXEC_PERIOD_SEC; 
        if (stepSeconds > 60.0) stepSeconds = 60.0; 
        
        lastRunMillis = now;

        // 1) Master Gate: Fan Status
        boolean fanIsRunning = boolOrDefault(getFanStatus(), true);

        if (!fanIsRunning) {
            resetAllState();
            zeroOutputs("System Status: Fan OFF - Monitoring Disabled");
            return;
        }

        // 2) Fetch & Validate Inputs
        BStatusNumeric satSlot = getSupplyAirTemp();
        BStatusNumeric spSlot  = getSupplyAirTempSetpoint();

        boolean satValid = isDataValid(satSlot, SANITY_TEMP_MIN, SANITY_TEMP_MAX);
        boolean spValid  = isDataValid(spSlot,  SANITY_TEMP_MIN, SANITY_TEMP_MAX);

        BStatusNumeric coolVlvSlot = getCoolValveCommand();
        BStatusNumeric heatVlvSlot = getHeatValveCommand();

        boolean coolVlvOk = isNumericUnwiredOrValid(coolVlvSlot, SANITY_VALVE_MIN, SANITY_VALVE_MAX);
        boolean heatVlvOk = isNumericUnwiredOrValid(heatVlvSlot, SANITY_VALVE_MIN, SANITY_VALVE_MAX);

        // --- COOLING LOGIC ---
        int coolReq = 0;
        String coolTrace = "";

        if (!satValid || !spValid || !coolVlvOk) {
            coolReq = 0;
            resetCoolTimers();
            coolTrace = "Fault: Sensor or Valve Data Invalid";
        }
        else if (!isNumericWired(coolVlvSlot)) {
            coolReq = 0;
            resetCoolTimers();
            coolTrace = "Config: No Cooling Coil Wired";
        }
        else {
            double sat = satSlot.getValue();
            double sp  = spSlot.getValue();
            double vlv = coolVlvSlot.getValue();
            double err = sat - sp; 

            // Timer Logic
            if (err >= COOL_ERR_CRITICAL) {
                coolTimerCritical += stepSeconds;
                coolTimerFailing  += stepSeconds;
            }
            else if (err >= COOL_ERR_FAILING) {
                coolTimerCritical = 0;
                coolTimerFailing  += stepSeconds;
            }
            else {
                coolTimerCritical = 0;
                coolTimerFailing  = 0;
            }

            // Valve Latch
            if (vlv >= VALVE_ON_PCT)      coolValveLatched = true;
            else if (vlv < VALVE_OFF_PCT) coolValveLatched = false;

            // Decision Ladder
            if (coolTimerCritical >= TIME_LIMIT_CRITICAL) {
                coolReq = 3;
                coolTrace = String.format("CRITICAL (3): Temp +%.1f°F for %ds", err, (int)coolTimerCritical);
            }
            else if (coolTimerFailing >= TIME_LIMIT_FAILING) {
                coolReq = 2;
                coolTrace = String.format("FAILING (2): Temp +%.1f°F for %ds", err, (int)coolTimerFailing);
            }
            else if (coolValveLatched) {
                coolReq = 1;
                coolTrace = String.format("SATURATED (1): Valve %.0f%% > 95%%", vlv);
            }
            else {
                coolReq = 0;
                coolTrace = String.format("Satisfied: Error +%.1f°F", err);
            }
        }

        // --- HEATING LOGIC ---
        int heatReq = 0;
        String heatTrace = "";

        if (!satValid || !spValid || !heatVlvOk) {
            heatReq = 0;
            resetHeatTimers();
            heatTrace = "Fault: Sensor or Valve Data Invalid";
        }
        else if (!isNumericWired(heatVlvSlot)) {
            heatReq = 0;
            resetHeatTimers();
            heatTrace = "Config: No Heating Coil Wired";
        }
        else {
            double sat = satSlot.getValue();
            double sp  = spSlot.getValue();
            double vlv = heatVlvSlot.getValue();
            double err = sp - sat; 

            // Timer Logic
            if (err >= HEAT_ERR_CRITICAL) {
                heatTimerCritical += stepSeconds;
                heatTimerFailing  += stepSeconds;
            }
            else if (err >= HEAT_ERR_FAILING) {
                heatTimerCritical = 0;
                heatTimerFailing  += stepSeconds;
            }
            else {
                heatTimerCritical = 0;
                heatTimerFailing  = 0;
            }

            // Valve Latch
            if (vlv >= VALVE_ON_PCT)      heatValveLatched = true;
            else if (vlv < VALVE_OFF_PCT) heatValveLatched = false;

            // Decision Ladder
            if (heatTimerCritical >= TIME_LIMIT_CRITICAL) {
                heatReq = 3;
                heatTrace = String.format("CRITICAL (3): Temp -%.1f°F for %ds", err, (int)heatTimerCritical);
            }
            else if (heatTimerFailing >= TIME_LIMIT_FAILING) {
                heatReq = 2;
                heatTrace = String.format("FAILING (2): Temp -%.1f°F for %ds", err, (int)heatTimerFailing);
            }
            else if (heatValveLatched) {
                heatReq = 1;
                heatTrace = String.format("SATURATED (1): Valve %.0f%% > 95%%", vlv);
            }
            else {
                heatReq = 0;
                heatTrace = String.format("Satisfied: Error -%.1f°F", err);
            }
        }

        // Output
        getCoolingRequests().setValue(coolReq);
        getCoolingStatusTrace().setValue(coolTrace);

        getHeatingRequests().setValue(heatReq);
        getHeatingStatusTrace().setValue(heatTrace);

    } catch (Exception e) {
        String msg = "ERROR: " + e.toString();
        try { getCoolingStatusTrace().setValue(msg); } catch(Exception ex) {}
        try { getHeatingStatusTrace().setValue(msg); } catch(Exception ex) {}
    } finally {
        scheduleNextRun();
    }
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
}

// ==========================================
// 5. HELPERS
// ==========================================
private void scheduleNextRun() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(EXEC_PERIOD_SEC), BProgram.execute, null);
}

private void zeroOutputs(String msg) {
    getCoolingRequests().setValue(0);
    getCoolingStatusTrace().setValue(msg);
    getHeatingRequests().setValue(0);
    getHeatingStatusTrace().setValue(msg);
}

private void resetAllState() { resetCoolTimers(); resetHeatTimers(); }
private void resetCoolTimers() { coolTimerCritical = 0; coolTimerFailing = 0; coolValveLatched = false; }
private void resetHeatTimers() { heatTimerCritical = 0; heatTimerFailing = 0; heatValveLatched = false; }

// --- Sanity & Validation ---
private boolean isDataValid(BStatusNumeric slot, double min, double max) {
    if (slot == null) return false;
    if (slot.getStatus().isFault() || slot.getStatus().isDown() || 
        slot.getStatus().isNull() || slot.getStatus().isDisabled()) return false;
    double val = slot.getValue();
    return (val >= min && val <= max);
}

private boolean isNumericUnwiredOrValid(BStatusNumeric slot, double min, double max) {
    if (slot == null || slot.getStatus().isNull()) return true; 
    return isDataValid(slot, min, max);
}

private boolean isNumericWired(BStatusNumeric slot) {
    return slot != null && !slot.getStatus().isNull();
}

private boolean boolOrDefault(BStatusBoolean slot, boolean defVal) {
    if (slot != null && slot.getStatus().isOk()) return slot.getValue();
    return defVal;
}
```

</details>


<details>
<summary>🔥 Central Plant Hot Water Temperature Setpoint Trim & Respond</summary>

This block runs at the **central plant** and resets the **Hot Water Supply Temperature (HWST)** based on **aggregated heating requests** coming from AHUs, FCUs, or zones.

It implements a classic **Trim & Respond** loop per **ASHRAE Guideline 36 (Section 5.21.4.1)**.

---

## What this reset controls

* **Output:** Hot Water Supply Temperature Setpoint (HWST)
* **Goal:**
  Keep HWST **as low as possible** for efficiency,
  but **increase temperature quickly** when the building asks for heat.

---

## Operating assumptions (important)

* **SP0 is the safe starting point**

  * Typically the **design / maximum HWST** (e.g. 180°F)
  * Used whenever the plant is disabled, OFF, or in fault
* The plant **starts hot**, then trims down unless requests appear
* Units are **agnostic** (°F or °C) — user configures slot values

---

## Enable & safety gating

The reset is **active only when both conditions are true**:

| Condition              | Meaning                             |
| ---------------------- | ----------------------------------- |
| `enable = true`        | Supervisor allows reset logic       |
| `plantProvenOn = true` | Boilers/pumps are confirmed running |

If either condition is false:

* HWST snaps to **SP0**
* Effective request count resets to 0
* Status trace explains why

---

## Request processing

### Effective request calculation

The plant does **not** react to small or noisy demand.

```
Effective Requests = max(0, Total Requests − Ignored Requests)
```

| Term               | Meaning                               |
| ------------------ | ------------------------------------- |
| Total Requests     | Sum of AHU/FCU heating request levels |
| Ignored Requests   | Noise filter (typically 2)            |
| Effective Requests | What actually drives the reset        |

---

## Trim & Respond behavior

The reset runs on a fixed time step (typically **5 minutes**).

| Condition                  | Action        | Result        |
| -------------------------- | ------------- | ------------- |
| **Effective Requests > 0** | **Respond ↑** | Increase HWST |
| **No Requests**            | **Trim ↓**    | Decrease HWST |

### Respond (increase temperature)

* Increase amount scales with demand
* Capped to prevent overshoot

```
Increase = min(Effective Requests × Respond Amount, Respond Max)
```

### Trim (decrease temperature)

* Fixed decrement each step
* Usually a **negative value** (e.g. −2°F)

---

## Setpoint clamping

After Trim or Respond:

```
HWST = clamp(HWST, SP_Min, SP_Max)
```

| Slot    | Purpose                       |
| ------- | ----------------------------- |
| `spMin` | Lowest allowed HWST           |
| `spMax` | Highest allowed HWST (design) |

This prevents unsafe or unrealistic temperatures.

---

## Fault handling (fail-safe behavior)

If the **request input is bad** (faulted, null, out of range):

* HWST immediately snaps to **SP0**
* Output status is set to **FAULT**
* Effective request count = 0

This guarantees **maximum heating availability** during data loss.

---

## Slot map (central plant)

### Inputs

| Slot Name         | Type             | Notes                         |
| ----------------- | ---------------- | ----------------------------- |
| `enable`          | `BStatusBoolean` | Master enable for reset logic |
| `plantProvenOn`   | `BStatusBoolean` | Boilers/pumps proven running  |
| `totalHwResetReq` | `BStatusNumeric` | Aggregated heating requests   |
| `ignoredReq`      | `BStatusNumeric` | Requests ignored as noise     |
| `stepMinutes`     | `BStatusNumeric` | Step interval (Td and T)      |
| `sp0`             | `BStatusNumeric` | Safe / design HWST            |
| `spMin`           | `BStatusNumeric` | Minimum HWST                  |
| `spMax`           | `BStatusNumeric` | Maximum HWST                  |
| `spTrim`          | `BStatusNumeric` | Trim amount (negative)        |
| `spRespond`       | `BStatusNumeric` | Respond amount per request    |
| `spRespondMax`    | `BStatusNumeric` | Max increase per step         |

### Outputs

| Slot Name               | Type             | Notes                         |
| ----------------------- | ---------------- | ----------------------------- |
| `hwstSpOut`             | `BStatusNumeric` | Active HWST setpoint          |
| `effectiveRequestCount` | `BStatusNumeric` | Post-filter request count     |
| `statusTrace`           | `BStatusString`  | Human-readable decision trace |


## 💻 Java Code – Boiler HWST T&R (Plant Block)

```java
// ==============================================================================
//  GL36 BOILER HWST TRIM & RESPOND v3.4 (FINAL)
//  - Logic: ASHRAE G36-2021 Section 5.21.4.1
//  - Inputs: Total Heating Requests
//  - Output: Effective Setpoint
//  - Units: Agnostic (User sets defaults in Slots 5, 6, 7)
// ==============================================================================

// Class-level fields
private Clock.Ticket ticket;
private long lastStepMillis = 0L;
private boolean wasEnabled = false;
private boolean lastPlantOn = false;

// Standard execution period (internal check frequency)
private static final int EXEC_PERIOD_SEC = 60;

// Sanity Limits (Wide enough for F or C)
private static final double SANITY_VAL_MIN = -50.0;
private static final double SANITY_VAL_MAX = 250.0;
private static final double SANITY_REQ_MIN = 0.0;
private static final double SANITY_REQ_MAX = 999.0;

// ==============================================================================
//  LIFECYCLE
// ==============================================================================

public void onStart() throws Exception {
    lastStepMillis = System.currentTimeMillis();
    scheduleNextRun();
}

public void onExecute() throws Exception {
    try {
        long now = System.currentTimeMillis();

        // 1) Master Gate: Enabled + Plant Proven ON
        boolean enabled = boolOrDefault(getEnable(), false);
        boolean plantOn = boolOrDefault(getPlantProvenOn(), false);

        // Detect Rising-Edge of Activation
        boolean wasActive = (wasEnabled && lastPlantOn);
        boolean isActive  = (enabled && plantOn);
        boolean becameActive = (isActive && !wasActive);

        wasEnabled = enabled;
        lastPlantOn = plantOn;

        // G36: When device is OFF, setpoint shall be SP0
        if (!isActive) {
            resetToSafeSetpoint(!enabled ? "Disabled." : "Plant OFF -> SP0.");
            return;
        }

        // 2) Initialization on Rising Edge
        if (becameActive) {
            lastStepMillis = now; // Reset step timer
            
            // On start, revert to SP0 (Max/Design Temp)
            double sp0 = valOrDefault(getSp0(), 180.0, SANITY_VAL_MIN, SANITY_VAL_MAX);
            
            getHwstSpOut().setValue(sp0);
            getHwstSpOut().setStatus(BStatus.ok);
            getEffectiveRequestCount().setValue(0.0);
            getStatusTrace().setValue("Init: Plant Start -> Reset to SP0=" + round1(sp0));
            return;
        }

        // 3) Validate Critical Input (Requests)
        BStatusNumeric reqSlot = getTotalHwResetReq();
        if (!isDataValid(reqSlot, SANITY_REQ_MIN, SANITY_REQ_MAX)) {
            // FAILSAFE: If requests are unknown/bad, go to Max Heat (Safe)
            resetToSafeSetpoint("FAULT: Request Input Bad -> Holding SP0.");
            getHwstSpOut().setStatus(BStatus.fault);
            return;
        }

        // 4) Step Timing Guard
        // Uses 'stepMinutes' for both Td (Start Delay) and T (Step Interval)
        double stepMin = valOrDefault(getStepMinutes(), 5.0, 0.1, 120.0);
        if ((now - lastStepMillis) < (stepMin * 60000L)) {
            return; // Not time to step yet
        }
        lastStepMillis = now;

        // 5) Calculate Effective Requests
        // Formula: Effective = Max(0, Requests - Ignored)
        double R = reqSlot.getValue();
        double I = valOrDefault(getIgnoredReq(), 2.0, 0.0, 50.0);
        double effR = Math.max(0.0, R - I);
        
        getEffectiveRequestCount().setValue(effR);

        // 6) Load Loop Parameters
        // Defaults assume Fahrenheit. User must change slots if using Celsius.
        double spMin = valOrDefault(getSpMin(), 140.0, SANITY_VAL_MIN, SANITY_VAL_MAX);
        double spMax = valOrDefault(getSpMax(), 180.0, SANITY_VAL_MIN, SANITY_VAL_MAX);

        // Anti-Windup: Read off the actual output slot
        double curSp = getHwstSpOut().getValue();
        if (Double.isNaN(curSp) || curSp < SANITY_VAL_MIN || curSp > SANITY_VAL_MAX) {
             curSp = valOrDefault(getSp0(), 180.0, SANITY_VAL_MIN, SANITY_VAL_MAX);
        }

        double newSp = curSp;
        String action = "Hold";

        // 7) Trim & Respond Logic
        if (effR > 0) {
            // RESPOND (Increase Temp)
            double res  = valOrDefault(getSpRespond(), 3.0, 0.0, 50.0);
            double resM = valOrDefault(getSpRespondMax(), 7.0, 0.0, 100.0);
            
            double amt = Math.min(effR * res, resM);
            newSp = curSp + amt;
            action = "Respond ↑ " + round1(amt);
        } else {
            // TRIM (Decrease Temp)
            // Note: spTrim should be negative (e.g. -2.0)
            double trim = valOrDefault(getSpTrim(), -2.0, -50.0, 50.0);
            newSp = curSp + trim;
            action = "Trim ↓ " + round1(trim);
        }

        // 8) Clamp and Write Output
        newSp = Math.max(spMin, Math.min(spMax, newSp));
        
        getHwstSpOut().setValue(newSp);
        getHwstSpOut().setStatus(BStatus.ok);
        getStatusTrace().setValue(action + " | R=" + (int)R + ", I=" + (int)I + ", SP=" + round1(newSp));

    } catch (Exception e) {
        getStatusTrace().setValue("Error: " + e.toString());
    } finally {
        scheduleNextRun();
    }
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
}

// ==============================================================================
//  HELPERS
// ==============================================================================

private void scheduleNextRun() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(EXEC_PERIOD_SEC), BProgram.execute, null);
}

private void resetToSafeSetpoint(String msg) {
    // Defaults to 180.0 (F) / User should change SP0 slot for (C)
    double sp0 = valOrDefault(getSp0(), 180.0, SANITY_VAL_MIN, SANITY_VAL_MAX);
    
    getHwstSpOut().setValue(sp0);
    getHwstSpOut().setStatus(BStatus.ok);
    getEffectiveRequestCount().setValue(0.0);
    getStatusTrace().setValue(msg + " Holding SP0=" + round1(sp0));
}

private boolean isDataValid(BStatusNumeric slot, double min, double max) {
    if (slot == null) return false;
    BStatus s = slot.getStatus();
    if (s.isFault() || s.isDown() || s.isNull() || s.isDisabled()) return false;
    
    double val = slot.getValue();
    return (val >= min && val <= max);
}

private double valOrDefault(BStatusNumeric slot, double def, double min, double max) {
    return isDataValid(slot, min, max) ? slot.getValue() : def;
}

private boolean boolOrDefault(BStatusBoolean slot, boolean defVal) {
    if (slot != null && slot.getStatus().isOk()) return slot.getValue();
    return defVal;
}

private double round1(double v) { return Math.round(v * 10.0) / 10.0; }
```


</details>



<details>
<summary>🥶 Central Plant Chilled Water Temperature Setpoint Trim & Respond</summary>

This block runs at the **central plant** and resets **chilled water plant capacity** using a **single 0–100% Trim & Respond loop**.
That loop output is then mapped into **two physical resets**:

1. **Chilled Water Differential Pressure (DP)**
2. **Chilled Water Supply Temperature (CHWST)**

The logic follows **ASHRAE Guideline 36 (Section 5.20.5.2)**. (Page 199 in 2021 GL36 edition)

---

## What this reset controls

| Output                   | Purpose                                   |
| ------------------------ | ----------------------------------------- |
| `plantResetOut` (0–100%) | Internal Trim & Respond loop              |
| `chwDpSpOut`             | Chilled water DP setpoint                 |
| `chwstSpOut`             | Chilled water supply temperature setpoint |

---

## Core operating assumption (important)

### **The loop starts at 100% capacity and trims down**

* **SP0 = 100%** represents **maximum plant capability**:

  * **DP = Max**
  * **CHWST = Coldest (design)**
* The plant **starts “fully capable”**, then **earns efficiency** by trimming down **unless AHUs complain**.

This is intentional and is the key to understanding the reset.

> **The loop does *not* count AHUs or normalize by how many exist.**

It simply answers one question every step:

> *“Did anyone still need more cooling capacity?”*

---

## Why the reset does **not** need to know how many AHUs exist

The 0–100% loop value is **not a percentage of AHUs**.

It is a **self-balancing control signal** that:

* Responds upward when requests exist
* Trims downward when they do not

So when the loop crosses **50%**, that does **not** mean:

> “50% of AHUs are requesting”

It means:

> “We have used half of our allowed capacity adjustment range”

The plant naturally settles where **requests ≈ trims**, regardless of building size.

---

## Enable, startup, and safety behavior

### Activation logic

The reset becomes active when:

* `enable = true`

On activation:

* Loop snaps to **SP0 = 100%**
* Plant starts at **max DP + coldest CHWST**
* Startup delay (`Td`) is applied before trimming begins

### Fault behavior (fail-safe)

If the **cooling request input is bad**:

* Loop snaps to **SP0 (100%)**
* Plant runs at maximum cooling capacity
* Prevents accidental warm-water trim due to bad data

---

## Request processing

### Effective request calculation

Small or noisy demand is ignored.

```
Effective Requests = max(0, Total Requests − Ignored Requests)
```

| Term               | Meaning                           |
| ------------------ | --------------------------------- |
| Total Requests     | Sum of AHU cooling request levels |
| Ignored Requests   | Noise filter (typically 2)        |
| Effective Requests | What actually drives the loop     |

---

## Trim & Respond behavior

The loop steps at a fixed interval (typically **5 minutes**).

| Condition                  | Action        | Effect            |
| -------------------------- | ------------- | ----------------- |
| **Effective Requests > 0** | **Respond ↑** | Increase capacity |
| **No Requests**            | **Trim ↓**    | Reduce capacity   |

### Respond (increase capacity)

```
Increase = min(Effective Requests × Respond Amount, Respond Max)
```

This drives:

* Higher DP
* Colder CHWST (once DP is maxed)

### Trim (reduce capacity)

* Fixed negative decrement (e.g. −2%)
* Gradually warms water and lowers DP

---

## Capacity mapping (the 50% breakpoint)

The single 0–100% loop is mapped into **two stages**:

### Stage 1 — DP Reset (0–50%)

| Loop Value | DP     | CHWST   |
| ---------- | ------ | ------- |
| 0%         | DP Min | Warmest |
| 50%        | DP Max | Warmest |

Only pump energy is optimized in this range.

---

### Stage 2 — Temperature Reset (50–100%)

| Loop Value | DP     | CHWST   |
| ---------- | ------ | ------- |
| 50%        | DP Max | Warmest |
| 100%       | DP Max | Coldest |

Only chiller energy is optimized in this range.

---

## Slot map (central plant)

### Inputs

| Slot Name               | Type             | Notes                               |
| ----------------------- | ---------------- | ----------------------------------- |
| `enable`                | `BStatusBoolean` | Master enable                       |
| `totalChwResetRequests` | `BStatusNumeric` | Aggregated cooling requests         |
| `ignoredReq`            | `BStatusNumeric` | Noise filter                        |
| `stepMinutes`           | `BStatusNumeric` | Step interval (T)                   |
| `startDelayMinutes`     | `BStatusNumeric` | Startup delay (Td)                  |
| `sp0`                   | `BStatusNumeric` | Initial loop value (typically 100%) |
| `spTrim`                | `BStatusNumeric` | Trim amount (negative)              |
| `spRespond`             | `BStatusNumeric` | Respond per request                 |
| `spRespondMax`          | `BStatusNumeric` | Max increase per step               |
| `chwDpMin / chwDpMax`   | `BStatusNumeric` | DP reset range                      |
| `chwstMin / chwstMax`   | `BStatusNumeric` | CHWST reset range                   |

### Outputs

| Slot Name       | Type             | Notes                |
| --------------- | ---------------- | -------------------- |
| `plantResetOut` | `BStatusNumeric` | 0–100% loop output   |
| `chwDpSpOut`    | `BStatusNumeric` | DP setpoint          |
| `chwstSpOut`    | `BStatusNumeric` | CHWST setpoint       |
| `statusTrace`   | `BStatusString`  | Human-readable trace |


## 💻 Java Code – Chilled Water T&R (Plant Block)

```java
// ==============================================================================
//  GL36 CHW PLANT RESET (DP + CHWST) v1.3
//  - Logic: ASHRAE G36-2021 Section 5.20.5.2
//  - Inputs: Total Cooling Requests
//  - Output: 0-100% Loop -> Maps to DP and CHWST
// ==============================================================================

private Clock.Ticket ticket;
private long lastStepMillis = 0L;
private long enableStartMillis = 0L;
private boolean wasEnabled = false;

private static final int EXEC_PERIOD_SEC = 10;
private static final double LOOP_MIN = 0.0;
private static final double LOOP_MAX = 100.0;

public void onStart() throws Exception {
    lastStepMillis = System.currentTimeMillis();
    enableStartMillis = 0L;
    wasEnabled = false;
    scheduleNextRunSeconds(1);
}

public void onExecute() throws Exception {
    try {
        long now = System.currentTimeMillis();

        // 1. Inputs
        boolean plantEnabled = safeBool(getEnable(), false);
        
        // Safety Check: If requests are bad, default to SP0 (Max Capacity)
        // rather than 0.0 (which would trim the plant to minimum).
        if (getEnable().getValue() && !getTotalChwResetRequests().getStatus().isOk()) {
             double sp0 = clamp(safeNum(getSp0(), 100.0), LOOP_MIN, LOOP_MAX);
             updateSetpoints(sp0, "Input Fault (Req)");
             return;
        }
        double totalReq = safeNum(getTotalChwResetRequests(), 0.0);

        // 2. Detect Activation (Rising Edge)
        boolean becameActive = (plantEnabled && !wasEnabled);
        wasEnabled = plantEnabled;

        double sp0 = clamp(safeNum(getSp0(), 100.0), LOOP_MIN, LOOP_MAX);

        // 3. Disabled State
        if (!plantEnabled) {
            enableStartMillis = 0L;
            lastStepMillis = now;
            // G36: When OFF, setpoint shall be SP0
            updateSetpoints(sp0, "Disabled"); 
            return;
        }

        // 4. Initialization
        if (becameActive) {
            enableStartMillis = now;
            lastStepMillis = now;
            updateSetpoints(sp0, "Start/Init");
            return;
        }

        // 5. Startup Delay (Td)
        double tdMin = safeNum(getStartDelayMinutes(), 15.0);
        long tdMs = (long)(tdMin * 60000.0);
        long elapsedTd = now - enableStartMillis;

        if (elapsedTd < tdMs) {
            double remainingMin = (tdMs - elapsedTd) / 60000.0;
            // During delay, hold current value (or SP0)
            double holdVal = clamp(safeNum(getPlantResetOut(), sp0), LOOP_MIN, LOOP_MAX);
            
            // Just update trace, don't change outputs
            getStatusTrace().setValue(
                "Holding Td (" + round1(remainingMin) + "m) @ " + round1(holdVal) + "%"
            );
            return; 
        }

        // 6. Step Interval (T)
        double stepMin = safeNum(getStepMinutes(), 5.0);
        if ((now - lastStepMillis) < (long)(stepMin * 60000.0)) {
            return; // Not time to step
        }
        lastStepMillis = now;

        // 7. Trim & Respond Logic
        double currentLoop = clamp(safeNum(getPlantResetOut(), sp0), LOOP_MIN, LOOP_MAX);
        double ignore = clamp(safeNum(getIgnoredReq(), 2.0), 0.0, 1000.0);
        
        // Effective Requests (R - I)
        double effReq = Math.max(0.0, totalReq - ignore);

        double spTrimVal   = safeNum(getSpTrim(), -2.0);
        double spResVal    = safeNum(getSpRespond(), 3.0);
        double spResMaxVal = safeNum(getSpRespondMax(), 7.0);

        double delta;
        String action;

        if (effReq > 0.0) {
            // RESPOND: Increase Capacity (Higher DP, Colder Water)
            delta = Math.min(effReq * spResVal, spResMaxVal);
            action = "Respond ↑";
        } else {
            // TRIM: Decrease Capacity (Lower DP, Warmer Water)
            delta = spTrimVal; 
            action = "Trim ↓";
        }

        double newLoop = clamp(currentLoop + delta, LOOP_MIN, LOOP_MAX);
        
        // 8. Update Outputs
        updateSetpoints(newLoop, action + " (R=" + (int)totalReq + ")");

    } catch (Exception e) {
        getStatusTrace().setValue("Error: " + shortMsg(e));
    } finally {
        scheduleNextRunSeconds(EXEC_PERIOD_SEC);
    }
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
}

// ==============================================================================
//  HELPERS
// ==============================================================================

private void updateSetpoints(double loopVal, String action) {
    loopVal = clamp(loopVal, LOOP_MIN, LOOP_MAX);

    // Read Scaling Parameters
    double dpMin = safeNum(getChwDpMin(), 10.0);
    double dpMax = safeNum(getChwDpMax(), 25.0);
    double stMin = safeNum(getChwstMin(), 42.0); // Coldest (Design/Max Cap)
    double stMax = safeNum(getChwstMax(), 55.0); // Warmest (Min Cap)

    // Sanity Swap (Ensure Max > Min for math)
    if (dpMax < dpMin) { double t = dpMin; dpMin = dpMax; dpMax = t; }
    // Note: For Temp, Min is Cold (100% loop) and Max is Warm (0% loop)
    // We keep stMin as the lower number and stMax as the higher number.

    double finalDp;
    double finalSt;
    String stage;

    // G36 5.20.5.2 Logic Mapping:
    if (loopVal <= 50.0) {
        // STAGE 1 (0-50%): Reset DP from Min to Max
        // CHWST held at Max (Warmest)
        double r = loopVal / 50.0; // 0.0 to 1.0
        finalDp = dpMin + (r * (dpMax - dpMin));
        finalSt = stMax; 
        stage = "Stg1 (DP Reset)";
    } else {
        // STAGE 2 (50-100%): Reset CHWST from Max (Warm) to Min (Cold)
        // DP held at Max
        double r = (loopVal - 50.0) / 50.0; // 0.0 to 1.0
        finalDp = dpMax;
        // As loop goes UP, Temp goes DOWN (towards stMin)
        finalSt = stMax - (r * (stMax - stMin)); 
        stage = "Stg2 (Temp Reset)";
    }

    // Write to Slots
    getPlantResetOut().setValue(loopVal);
    getChwDpSpOut().setValue(finalDp);
    getChwstSpOut().setValue(finalSt);

    getStatusTrace().setValue(
        action + " | Loop=" + round1(loopVal) + "% | " + stage +
        " | DP=" + round1(finalDp) + " | ST=" + round1(finalSt)
    );
}

private void scheduleNextRunSeconds(int seconds) {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(seconds), BProgram.execute, null);
}

private double safeNum(BStatusNumeric slot, double def) {
    if (slot == null || !slot.getStatus().isOk()) return def;
    double v = slot.getValue();
    return Double.isNaN(v) ? def : v;
}

private boolean safeBool(BStatusBoolean slot, boolean def) {
    if (slot == null || !slot.getStatus().isOk()) return def;
    return slot.getValue();
}

private double clamp(double v, double lo, double hi) {
    return (v < lo) ? lo : (v > hi) ? hi : v;
}

private double round1(double v) {
    return Math.round(v * 10.0) / 10.0;
}

private String shortMsg(Throwable t) {
    if (t == null) return "Unknown Error";
    String m = t.getMessage();
    return (m != null && !m.isEmpty()) ? m : t.getClass().getSimpleName();
}
```


</details>