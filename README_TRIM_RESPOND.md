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

**Purpose:**  
Implements ASHRAE Guideline 36 zone-level request logic for each VAV box.  
Each zone generates **Pressure** and **Cooling (SAT)** requests based on its local damper, airflow, and temperature.  
These individual zone requests are totalized at the AHU level and used by Trim & Respond algorithms for duct static pressure and supply air temperature reset.

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


<details>
<summary>🍃 NOT TESTED YET - AHU/FCU → Central Plant Request Counter (Heating + Cooling)</summary>

For **each AHU/FCU**, build a small “Plant Reset Request Generator” `ProgramObject` that can:

* Generate **CHW reset requests** (for chilled-water plant trim & respond)
* Generate **HW reset requests** (for boiler HWST trim & respond)

Both request ladders follow the same Guideline-36 style as the VAV box:
integer **0–3** requests, with persistence timers, hysteresis on valve
position, and optional fan-gating.

Crucially, this AHU block is designed to be **coil-agnostic**:

* If the **cooling coil** is not present (no CHW valve / cooling SAT SP wired),
  the **CHW logic is bypassed** → `chwResetRequests = 0`
* If the **heating coil** is not present (no HW valve / heating SAT SP wired),
  the **HW logic is bypassed** → `hwResetRequests = 0`

This lets one ProgramObject serve:

* Heat-only AHUs  
* Cool-only AHUs  
* AHUs with **both** coils  
* FCUs / DOAS units that only have one active coil


### Slot Map (per AHU/FCU)

#### Inputs

| Slot Name        | Type             | Notes                                                                 |
|------------------|------------------|-----------------------------------------------------------------------|
| `sat`            | `BStatusNumeric` | Supply (discharge) air temperature off coils (°F or °C)              |
| `coolSatSp`      | `BStatusNumeric` | Cooling SAT setpoint (used for CHW requests). Optional.             |
| `heatSatSp`      | `BStatusNumeric` | Heating SAT setpoint (used for HW requests). Optional.              |
| `chwValvePct`    | `BStatusNumeric` | CHW valve position (%) – 0–100. Optional (cool-only).               |
| `hwValvePct`     | `BStatusNumeric` | HW valve position (%) – 0–100. Optional (heat-only).                |
| `fanAtMaxCool`   | `BStatusBoolean` | Optional fan-gating for CHW requests (e.g. “fan at max cool speed”). |
| `fanAtMaxHeat`   | `BStatusBoolean` | Optional fan-gating for HW requests (e.g. “fan at max heat speed”).  |

> **Important:**  
> If `coolSatSp` *and* `chwValvePct` are NULL/unwired → the **CHW ladder is disabled**.  
> If `heatSatSp` *and* `hwValvePct` are NULL/unwired → the **HW ladder is disabled**.

#### Outputs

| Slot Name          | Type             | Notes                                           |
|--------------------|------------------|-------------------------------------------------|
| `chwResetRequests` | `BStatusNumeric` | 0…3 integer CHW reset requests                  |
| `hwResetRequests`  | `BStatusNumeric` | 0…3 integer HW reset requests                   |
| `coolStatusTrace`  | `BStatusString`  | Debug trace for cooling / CHW ladder            |
| `heatStatusTrace`  | `BStatusString`  | Debug trace for heating / HW ladder             |


### Algorithms

#### Cooling / CHW Reset Requests (per AHU)

Same ladder you described from the CHW plant section:

* If `SAT ≥ coolSatSp + 10°F` for **5 min** → `3` CHW reset requests  
* Else if `SAT ≥ coolSatSp + 5°F` for **5 min** → `2` CHW reset requests  
* Else if `chwValvePct ≥ 95%` (latched until `< 85%`) → `1` CHW reset request  
* Else → `0` CHW reset requests  

Optional fan gating:

* If `fanAtMaxCool == false` (and wired) → **suppress all CHW requests**, reset timers

If the **cooling coil is not present**, identified by both `coolSatSp`
and `chwValvePct` being NULL/unwired, then:

* Timers are cleared
* `chwResetRequests = 0`
* `coolStatusTrace` tells you “cooling coil not present / not wired”

#### Heating / HW Reset Requests (per AHU)

Mirror image for heating:

* If `SAT ≤ heatSatSp − 30°F` for **5 min** → `3` HW reset requests  
* Else if `SAT ≤ heatSatSp − 15°F` for **5 min** → `2` HW reset requests  
* Else if `hwValvePct ≥ 95%` (latched until `< 85%`) → `1` HW reset request  
* Else → `0` HW reset requests  

Optional fan gating:

* If `fanAtMaxHeat == false` (and wired) → **suppress all HW requests**, reset timers

If the **heating coil is not present**, identified by both `heatSatSp`
and `hwValvePct` being NULL/unwired, then:

* Timers are cleared
* `hwResetRequests = 0`
* `heatStatusTrace` tells you “heating coil not present / not wired”


### Java Code – AHU/FCU Heating + Cooling Request Counter

> Niagara auto-generates headers/imports/getters/setters.  
> Paste **only** the methods below into the Program’s **Source** editor.

```java
////////////////////////////////////////////////////////////////
// Class-level fields
////////////////////////////////////////////////////////////////

Clock.Ticket ticket;

private static final int EXEC_PERIOD_SEC = 10;    // Run every 10 s
private static final int PERSIST_SEC     = 300;   // 5 min persistence

// Cooling thresholds (°F)
private static final double COOL_ERR_3REQ_F   = 10.0;  // SAT ≥ SP + 10°F
private static final double COOL_ERR_2REQ_F   = 5.0;   // SAT ≥ SP + 5°F
private static final double CHW_VALVE_ON_PCT  = 95.0;
private static final double CHW_VALVE_OFF_PCT = 85.0;

// Heating thresholds (°F)
// Use positive "overcool" diff = (heatSatSp - SAT)
private static final double HEAT_ERR_3REQ_F   = 30.0;  // SAT ≤ SP - 30°F
private static final double HEAT_ERR_2REQ_F   = 15.0;  // SAT ≤ SP - 15°F
private static final double HW_VALVE_ON_PCT   = 95.0;
private static final double HW_VALVE_OFF_PCT  = 85.0;

// Cooling timers / latch
int    coolHigh10Sec = 0;
int    coolHigh5Sec  = 0;
boolean chwValveLatched = false;

// Heating timers / latch
int    heatLow30Sec = 0;
int    heatLow15Sec = 0;
boolean hwValveLatched = false;

////////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////////

public void onStart() throws Exception {
    updateTimer();
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
}

public BComponent getProgram() {
    return (BComponent) getComponent();
}

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getProgram(), BRelTime.makeSeconds(EXEC_PERIOD_SEC),
                            BProgram.execute, null);
}

////////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////////

boolean isNumericValid(BStatusNumeric slot) {
    return slot != null && slot.getStatus().isOk();
}

double numericOrDefault(BStatusNumeric slot, double defVal) {
    return (slot != null && slot.getStatus().isOk()) ? slot.getValue() : defVal;
}

boolean boolOrDefault(BStatusBoolean slot, boolean defVal) {
    return (slot != null && slot.getStatus().isOk()) ? slot.getValue() : defVal;
}

String boolStatus(BStatusBoolean b) {
    if (b == null || !b.getStatus().isOk()) return "NULL";
    return Boolean.toString(b.getValue());
}

int clampInt(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

////////////////////////////////////////////////////////////////
// Main execute
////////////////////////////////////////////////////////////////

public void execute() throws Exception {
    // Shared SAT
    double sat = numericOrDefault(getSat(), 55.0);

    // Inputs
    BStatusNumeric coolSpSlot = getCoolSatSp();
    BStatusNumeric heatSpSlot = getHeatSatSp();
    BStatusNumeric chwVlvSlot = getChwValvePct();
    BStatusNumeric hwVlvSlot  = getHwValvePct();
    BStatusBoolean fanCoolSlot = getFanAtMaxCool();
    BStatusBoolean fanHeatSlot = getFanAtMaxHeat();

    // Coil presence detection
    boolean hasCoolingCoil = isNumericValid(coolSpSlot) || isNumericValid(chwVlvSlot);
    boolean hasHeatingCoil = isNumericValid(heatSpSlot) || isNumericValid(hwVlvSlot);

    // Optional fan gating:
    // - If wired → use its value
    // - If unwired → default true (no gating)
    boolean fanAtMaxCool = boolOrDefault(fanCoolSlot, true);
    boolean fanAtMaxHeat = boolOrDefault(fanHeatSlot, true);

    int chwReq = 0;
    int hwReq  = 0;

    ////////////////////////////////////////////////////////////
    // COOLING / CHW REQUESTS
    ////////////////////////////////////////////////////////////
    String coolTrace;

    if (!hasCoolingCoil) {
        // No cooling coil wired → fully bypass CHW logic
        coolHigh10Sec = 0;
        coolHigh5Sec  = 0;
        chwValveLatched = false;
        chwReq = 0;
        coolTrace = "Cooling coil not present/not wired → CHW reset requests = 0.";
    }
    else if (!fanAtMaxCool && fanCoolSlot != null && fanCoolSlot.getStatus().isOk()) {
        // Fan gating is wired AND false → suppress CHW requests
        coolHigh10Sec = 0;
        coolHigh5Sec  = 0;
        chwValveLatched = false;
        chwReq = 0;
        coolTrace = "fanAtMaxCool = FALSE → suppress CHW reset requests (0).";
    }
    else {
        double coolSp = numericOrDefault(coolSpSlot, sat); // avoid big err if SP missing
        double chwVlv = numericOrDefault(chwVlvSlot, 0.0);

        // Cooling error: SAT - SP (positive = too warm)
        double coolErr = sat - coolSp;

        // Persistence timers
        if (coolErr >= COOL_ERR_3REQ_F) {
            coolHigh10Sec += EXEC_PERIOD_SEC;
            coolHigh5Sec  += EXEC_PERIOD_SEC;
        } else if (coolErr >= COOL_ERR_2REQ_F) {
            coolHigh10Sec = 0;
            coolHigh5Sec  += EXEC_PERIOD_SEC;
        } else {
            coolHigh10Sec = 0;
            coolHigh5Sec  = 0;
        }

        boolean coolHigh10 = (coolHigh10Sec >= PERSIST_SEC);
        boolean coolHigh5  = (coolHigh5Sec  >= PERSIST_SEC);

        // Valve latch
        if (chwVlv >= CHW_VALVE_ON_PCT) {
            chwValveLatched = true;
        } else if (chwVlv < CHW_VALVE_OFF_PCT) {
            chwValveLatched = false;
        }

        // Request ladder
        if (coolHigh10) {
            chwReq = 3;
            coolTrace = "SAT ≥ coolSp + 10°F for ≥5 min → 3 CHW reset requests.";
        } else if (coolHigh5) {
            chwReq = 2;
            coolTrace = "SAT ≥ coolSp + 5°F for ≥5 min → 2 CHW reset requests.";
        } else if (chwValveLatched) {
            chwReq = 1;
            coolTrace = "CHW valve ≥ 95% (latched until < 85%) → 1 CHW reset request.";
        } else {
            chwReq = 0;
            coolTrace = "Within cooling band and CHW valve < 95% → 0 CHW reset requests.";
        }

        coolTrace += " [sat=" + sat + "°F, coolSp=" + coolSp + "°F, err="
                   + (sat - coolSp) + "°F, chwVlv=" + chwVlv + "%, fanAtMaxCool="
                   + boolStatus(fanCoolSlot) + "]";
    }

    chwReq = clampInt(chwReq, 0, 3);
    getChwResetRequests().setValue(chwReq);
    getCoolStatusTrace().setValue(coolTrace);

    ////////////////////////////////////////////////////////////
    // HEATING / HW REQUESTS
    ////////////////////////////////////////////////////////////
    String heatTrace;

    if (!hasHeatingCoil) {
        // No heating coil wired → fully bypass HW logic
        heatLow30Sec = 0;
        heatLow15Sec = 0;
        hwValveLatched = false;
        hwReq = 0;
        heatTrace = "Heating coil not present/not wired → HW reset requests = 0.";
    }
    else if (!fanAtMaxHeat && fanHeatSlot != null && fanHeatSlot.getStatus().isOk()) {
        // Fan gating is wired AND false → suppress HW requests
        heatLow30Sec = 0;
        heatLow15Sec = 0;
        hwValveLatched = false;
        hwReq = 0;
        heatTrace = "fanAtMaxHeat = FALSE → suppress HW reset requests (0).";
    }
    else {
        double heatSp = numericOrDefault(heatSpSlot, sat);
        double hwVlv  = numericOrDefault(hwVlvSlot, 0.0);

        // Heating error: SP - SAT (positive = too cold)
        double heatErr = heatSp - sat;

        // Persistence timers
        if (heatErr >= HEAT_ERR_3REQ_F) {
            heatLow30Sec += EXEC_PERIOD_SEC;
            heatLow15Sec += EXEC_PERIOD_SEC;
        } else if (heatErr >= HEAT_ERR_2REQ_F) {
            heatLow30Sec = 0;
            heatLow15Sec += EXEC_PERIOD_SEC;
        } else {
            heatLow30Sec = 0;
            heatLow15Sec = 0;
        }

        boolean heatLow30 = (heatLow30Sec >= PERSIST_SEC);
        boolean heatLow15 = (heatLow15Sec >= PERSIST_SEC);

        // Valve latch
        if (hwVlv >= HW_VALVE_ON_PCT) {
            hwValveLatched = true;
        } else if (hwVlv < HW_VALVE_OFF_PCT) {
            hwValveLatched = false;
        }

        // Request ladder
        if (heatLow30) {
            hwReq = 3;
            heatTrace = "SAT ≤ heatSp - 30°F for ≥5 min → 3 HW reset requests.";
        } else if (heatLow15) {
            hwReq = 2;
            heatTrace = "SAT ≤ heatSp - 15°F for ≥5 min → 2 HW reset requests.";
        } else if (hwValveLatched) {
            hwReq = 1;
            heatTrace = "HW valve ≥ 95% (latched until < 85%) → 1 HW reset request.";
        } else {
            hwReq = 0;
            heatTrace = "Within heating band and HW valve < 95% → 0 HW reset requests.";
        }

        heatTrace += " [sat=" + sat + "°F, heatSp=" + heatSp + "°F, err="
                   + (heatSp - sat) + "°F, hwVlv=" + hwVlv + "%, fanAtMaxHeat="
                   + boolStatus(fanHeatSlot) + "]";
    }

    hwReq = clampInt(hwReq, 0, 3);
    getHwResetRequests().setValue(hwReq);
    getHeatStatusTrace().setValue(heatTrace);
}
```

</details>



<details>
<summary>🔥 NOT TESTED YET - Hot Water Temp Setpoint Trim & Respond </summary>

## 🔧 Slot Sheet 

Create a ProgramObject with these slots (names can be tweaked, but keep them consistent with the code):

### Inputs / Config

| Slot Name           | Type             | Writable | Notes                                                        |
| ------------------- | ---------------- | -------- | ------------------------------------------------------------ |
| `enable`            | `BStatusBoolean` | Yes      | Master enable for the reset logic.                           |
| `totalHwResetReq`   | `BStatusNumeric` | Yes      | Sum of all AHU hot-water reset requests (0…N).               |
| `sp0`               | `BStatusNumeric` | Config   | Initial HWST setpoint (starting value).                      |
| `spMin`             | `BStatusNumeric` | Config   | Minimum HWST (e.g., 90°F condensing, 155°F non-cond).        |
| `spMax`             | `BStatusNumeric` | Config   | Maximum HWST (e.g., 180–190°F).                              |
| `ignoredReq` (`I`)  | `BStatusNumeric` | Config   | Number of requests to ignore (GL-36 variable **I**).         |
| `stepMinutes` (`T`) | `BStatusNumeric` | Config   | Time step between T&R actions (default 5 min).               |
| `spTrim`            | `BStatusNumeric` | Config   | **SPtrim** – trim step (e.g., –2°F).                         |
| `spRes`             | `BStatusNumeric` | Config   | **SPres** – respond step per effective request (e.g., +3°F). |
| `spResMax`          | `BStatusNumeric` | Config   | **SPres-max** – max response per step (e.g., +7°F).          |

*(You can add `tdMinutes` later if you want a GL-36 style delay **Td**; this first version keeps it simple.)*

### Outputs

| Slot Name     | Type             | Writable | Notes                                     |
| ------------- | ---------------- | -------- | ----------------------------------------- |
| `hwstSpOut`   | `BStatusNumeric` | No       | Final HWST setpoint to send to boiler(s). |
| `activeR`     | `BStatusNumeric` | No       | Clamped, effective `R` used by the loop.  |
| `statusTrace` | `BStatusString`  | No       | Human-readable trace of last T&R action.  |

---

## 💻 Java Code – Boiler HWST T&R (Plant Block)

> Niagara auto-generates headers/imports/getters/setters.
> Paste **only** the code below into the Program’s **Source** editor.

```java
////////////////////////////////////////////////////////////
// Class-level fields
////////////////////////////////////////////////////////////

Clock.Ticket ticket;

long lastStepMillis = 0L;
boolean wasEnabled = false;

////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////

public void onStart() throws Exception {
  // Initialize last step time
  lastStepMillis = System.currentTimeMillis();

  // Set sensible GL-36-style defaults if config slots are NULL
  ensureDefault(getSpTrim(),   -2.0);  // °F per step down
  ensureDefault(getSpRes(),     3.0);  // °F per request up
  ensureDefault(getSpResMax(),  7.0);  // °F per step max up
  ensureDefault(getStepMinutes(), 5.0); // T = 5 minutes
  ensureDefault(getIgnoredReq(), 0.0);  // I = 0 by default

  // HWST bounds – adjust to your plant type
  // (90°F for condensing/hybrid SPmin, 155°F for non-condensing per G36) 
  ensureDefault(getSpMin(),  120.0);     
  ensureDefault(getSpMax(),  180.0);     
  ensureDefault(getSp0(),    150.0);     

  // Initialize output SP
  double initSp = safeNumeric(getHwstSpOut(), getSp0(), getSpMin(), getSpMax());
  getHwstSpOut().setValue(initSp);
  getStatusTrace().setValue("Boiler HWST T&R started. Init SP = " + round1(initSp));
  getActiveR().setValue(0.0);

  updateTimer();
}

public void onExecute() throws Exception {
  updateTimer();

  boolean enabled = safeBool(getEnable());
  long now = System.currentTimeMillis();

  // If just transitioned to enabled, reset the step timer
  if (enabled && !wasEnabled) {
    lastStepMillis = now;
    getStatusTrace().setValue("T&R enabled; waiting for first step.");
  }
  wasEnabled = enabled;

  // If disabled, hold SP at sp0 (or last good) and exit
  if (!enabled) {
    double holdSp = safeNumeric(getHwstSpOut(), getSp0(), getSpMin(), getSpMax());
    getHwstSpOut().setValue(holdSp);
    getStatusTrace().setValue("T&R disabled → holding SP = " + round1(holdSp));
    return;
  }

  // Step timing
  int stepMin = (int) clampDouble(
      safeNumeric(getStepMinutes(), null, null, null),
      1.0, 60.0
  );
  long stepMs = stepMin * 60L * 1000L;

  if ((now - lastStepMillis) < stepMs) {
    // Not time yet – just exit quietly
    return;
  }
  lastStepMillis = now;

  // Read total requests R and clamp to a sane range
  int R = (int) clampDouble(
      getTotalHwResetReq().getStatus().isOk() ? getTotalHwResetReq().getValue() : 0.0,
      0.0, 999.0
  );

  int I = (int) clampDouble(
      getIgnoredReq().getStatus().isOk() ? getIgnoredReq().getValue() : 0.0,
      0.0, 50.0
  );

  getActiveR().setValue(R);

  double spMin  = getSpMin().getStatus().isOk() ? getSpMin().getValue() : 120.0;
  double spMax  = getSpMax().getStatus().isOk() ? getSpMax().getValue() : 180.0;
  double spTrim = getSpTrim().getStatus().isOk() ? getSpTrim().getValue() : -2.0;
  double spRes  = getSpRes().getStatus().isOk()  ? getSpRes().getValue()  :  3.0;
  double spResMax = getSpResMax().getStatus().isOk() ? getSpResMax().getValue() : 7.0;

  double currentSp = safeNumeric(getHwstSpOut(), getSp0(), getSpMin(), getSpMax());
  double newSp = currentSp;

  StringBuilder trace = new StringBuilder();
  trace.append("R=").append(R).append(", I=").append(I)
       .append(", oldSP=").append(round1(currentSp)).append(" → ");

  if (R > I) {
    // Respond UP: SP += min( SPres * (R−I), SPres-max )
    int effR = R - I;
    double rawResp = spRes * effR;
    double limitedResp = (spResMax > 0.0)
        ? Math.min(rawResp, spResMax)
        : rawResp;

    newSp = currentSp + limitedResp;
    trace.append("Respond ↑ by ").append(round1(limitedResp));
  }
  else if (R == 0) {
    // Trim DOWN: SP += SPtrim (typically negative)
    newSp = currentSp + spTrim;
    trace.append("Trim ").append(spTrim < 0 ? "↓" : "↑")
         .append(" by ").append(round1(spTrim));
  }
  else {
    // 0 < R ≤ I → hold
    trace.append("Hold (0 < R ≤ I)");
  }

  // Clamp to SPmin/SPmax
  newSp = clampDouble(newSp, spMin, spMax);
  getHwstSpOut().setValue(newSp);

  trace.append(" → newSP=").append(round1(newSp))
       .append(" [spMin=").append(round1(spMin))
       .append(", spMax=").append(round1(spMax)).append("]");

  getStatusTrace().setValue(trace.toString());
}

public void onStop() throws Exception {
  if (ticket != null) {
    ticket.cancel();
  }
  getStatusTrace().setValue("Boiler HWST T&R stopped.");
}

////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////

void updateTimer() {
  if (ticket != null) {
    ticket.cancel();
  }
  // Execute every 60 s, internal logic only acts every stepMinutes
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(60),
      BProgram.execute,
      null
  );
}

boolean safeBool(BStatusBoolean b) {
  try {
    return b.getStatus().isOk() && b.getValue();
  } catch (Exception e) {
    return false;
  }
}

/**
 * If primary is bad/NULL, fall back to sp0, then midpoint(spMin, spMax).
 */
double safeNumeric(BStatusNumeric primary,
                   BStatusNumeric sp0,
                   BStatusNumeric spMinSlot,
                   BStatusNumeric spMaxSlot) {
  if (primary != null && primary.getStatus().isOk()) {
    return primary.getValue();
  }

  if (sp0 != null && sp0.getStatus().isOk()) {
    return sp0.getValue();
  }

  double lo = 120.0;
  double hi = 180.0;

  if (spMinSlot != null && spMinSlot.getStatus().isOk()) {
    lo = spMinSlot.getValue();
  }
  if (spMaxSlot != null && spMaxSlot.getStatus().isOk()) {
    hi = spMaxSlot.getValue();
  }
  if (hi < lo) {
    double tmp = lo;
    lo = hi;
    hi = tmp;
  }
  return (lo + hi) / 2.0;
}

void ensureDefault(BStatusNumeric slot, double defVal) {
  if (slot == null) return;
  if (!slot.getStatus().isOk()) {
    slot.setValue(defVal);
  }
}

double clampDouble(double v, double lo, double hi) {
  if (!Double.isFinite(v)) return lo;
  if (lo > hi) {
    double tmp = lo;
    lo = hi;
    hi = tmp;
  }
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

double round1(double v) {
  return Math.round(v * 10.0) / 10.0;
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


<details>
<summary>🥶 NOT TESTED YET - Chilled Water Temp Setpoint Trim & Respond</summary>


## 2️⃣ ProgramObject: CHW Plant Trim & Respond (DP + CHWST)

Now we mimic the **plant reset loop** you quoted:

From the G36 CHW Plant Reset section: 

* A single T&R loop outputs **0–100%**.
* **0–50%** of that output is mapped to **CHW pump DP setpoint** (min → max).
* **50–100%** is mapped to **CHWST setpoint** (max → min).
* T&R parameters:

  * `SP0 = 100 %`
  * `SPmin = 0 %`
  * `SPmax = 100 %`
  * `Td = 15 min`
  * `T = 5 min`
  * `I = 2` ignored requests
  * `R = Cooling CHWST Reset Requests` (your summed requests)
  * `SPtrim = –2 %`
  * `SPres = +3 %`
  * `SPres-max = +7 %`

### Slot Map (Plant Reset Block)

**Inputs**

* `plantEnabled` – plant enable / run status – `BStatusBoolean`
* `totalChwResetRequests` – sum of all AHU/FCU CHW reset requests – `BStatusNumeric`
* `SP0` – Initial loop output (%) – `BStatusNumeric` (default 100)
* `SPmin` – Min loop output (%) – `BStatusNumeric` (default 0)
* `SPmax` – Max loop output (%) – `BStatusNumeric` (default 100)
* `TdMinutes` – Delay before T&R starts (default 15)
* `TMinutes` – T&R evaluation interval (default 5)
* `Ignore` – number of ignored requests (I = 2)
* `SPtrim` – trim amount per interval (default –2)
* `SPres` – respond amount per request (default +3)
* `SPresMax` – max respond per interval (default +7)
* `chwDpMin` – minimum CHW pump DP setpoint (e.g. 30 ft or kPa)
* `chwDpMax` – maximum CHW pump DP setpoint
* `chwstMin` – minimum CHW supply temp (coldest)
* `chwstMax` – maximum CHW supply temp (warmest)

**Outputs**

* `plantResetOut` – 0…100 % loop output – `BStatusNumeric`
* `chwDpSpOut` – CHW pump DP setpoint – `BStatusNumeric`
* `chwstSpOut` – CHWST setpoint – `BStatusNumeric`
* `statusTrace` – `BStatusString`

---

### Java Code – CHW Plant T&R Reset

```java
////////////////////////////////////////////////////////////////
// Class-level fields
////////////////////////////////////////////////////////////////

Clock.Ticket ticket;

private static final int EXEC_PERIOD_SEC = 10;

// Internal
double loopSp = 100.0;   // 0–100 % reset loop output
long plantEnableTimestamp = 0L;
long lastUpdateTimestamp  = 0L;

////////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////////

public void onStart() throws Exception {
    // Initialize SP from slot
    loopSp = numericOrDefault(getSP0(), 100.0);
    updateTimer();
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
}

public BComponent getProgram() {
    return (BComponent) getComponent();
}

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getProgram(), BRelTime.makeSeconds(EXEC_PERIOD_SEC),
                            BProgram.execute, null);
}

////////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////////

double numericOrDefault(BStatusNumeric slot, double defVal) {
    return slot.getStatus().isOk() ? slot.getValue() : defVal;
}

boolean boolOrFalse(BStatusBoolean slot) {
    return slot.getStatus().isOk() && slot.getValue();
}

double clamp(double v, double lo, double hi) {
    return Math.max(lo, Math.min(v, hi));
}

int minutesToSecondsSafe(BStatusNumeric minsSlot, int defMin) {
    double m = defMin;
    if (minsSlot.getStatus().isOk()) {
        m = minsSlot.getValue();
    }
    m = clamp(m, 0.0, 240.0);   // 0–4 hours
    return (int)Math.round(m * 60.0);
}

double round1(double v) {
    return Math.round(v * 10.0) / 10.0;
}

////////////////////////////////////////////////////////////////
// Main execute
////////////////////////////////////////////////////////////////

public void execute() throws Exception {
    long nowMs = Clock.time().getMillis();

    // Inputs
    boolean plantEnabled = boolOrFalse(getPlantEnabled());
    double totalReq = numericOrDefault(getTotalChwResetRequests(), 0.0);

    // T&R params (with defaults from G36)
    double spMin    = numericOrDefault(getSPmin(), 0.0);
    double spMax    = numericOrDefault(getSPmax(), 100.0);
    double spTrim   = numericOrDefault(getSPtrim(), -2.0);  // trim (usually negative)
    double spRes    = numericOrDefault(getSPres(), 3.0);    // respond per req (positive)
    double spResMax = numericOrDefault(getSPresMax(), 7.0); // max respond per interval
    double ignore   = numericOrDefault(getIgnore(), 2.0);   // I

    int TdSec = minutesToSecondsSafe(getTdMinutes(), 15);
    int TSec  = minutesToSecondsSafe(getTMinutes(), 5);

    // Plant enable tracking
    if (!plantEnabled) {
        plantEnableTimestamp = 0L;
        lastUpdateTimestamp  = 0L;
        // You might choose to hold last loopSp or snap to SP0 here
    } else if (plantEnableTimestamp == 0L) {
        plantEnableTimestamp = nowMs;
        lastUpdateTimestamp  = 0L;
    }

    String trace;

    // If plant not enabled, just map outputs from current loopSp for visibility
    if (!plantEnabled) {
        trace = "Plant disabled → holding last reset output (" + round1(loopSp) + " %).";
    } else {
        long enabledSec = (nowMs - plantEnableTimestamp) / 1000;

        // Wait Td before first update
        if (enabledSec < TdSec) {
            trace = "Td delay active (" + enabledSec + "/" + TdSec + " s) → holding SP = "
                    + round1(loopSp) + " %.";
        } else {
            long sinceLastUpdateSec = (nowMs - lastUpdateTimestamp) / 1000;

            if (lastUpdateTimestamp == 0L || sinceLastUpdateSec >= TSec) {
                // === Trim & Respond update ===
                double effectiveReq = Math.max(0.0, totalReq - ignore);

                double respondThisStep = spRes * effectiveReq;
                if (respondThisStep > spResMax) {
                    respondThisStep = spResMax;
                }

                double delta;
                if (effectiveReq <= 0.0) {
                    // No effective requests → trim
                    delta = spTrim;
                } else {
                    // Some requests → respond
                    delta = respondThisStep;
                }

                loopSp = clamp(loopSp + delta, spMin, spMax);
                lastUpdateTimestamp = nowMs;

                trace = "T&R update: totalReq=" + totalReq
                        + " (ignore=" + ignore + ", eff=" + effectiveReq + ")"
                        + ", delta=" + round1(delta)
                        + " → loopSp=" + round1(loopSp) + " %.";
            } else {
                trace = "Waiting for next T interval (" + sinceLastUpdateSec + "/" + TSec
                        + " s) → loopSp=" + round1(loopSp) + " %.";
            }
        }
    }

    // ========= Map loopSp → DP SP and CHWST SP =========
    double dpMin   = numericOrDefault(getChwDpMin(), 50.0);
    double dpMax   = numericOrDefault(getChwDpMax(), 90.0);
    double chwstMin = numericOrDefault(getChwstMin(), 42.0);
    double chwstMax = numericOrDefault(getChwstMax(), 48.0);

    double dpSp;
    double chwstSp;

    if (loopSp <= 50.0) {
        // Stage 1: DP reset only (0–50 %)
        double frac = loopSp / 50.0; // 0–1
        dpSp = dpMin + frac * (dpMax - dpMin);
        chwstSp = chwstMax; // no temp reset yet
        trace += "  Stage 1 (DP only): dpSp=" + round1(dpSp) + ", chwstSp=" + round1(chwstSp);
    } else {
        // Stage 2: DP at max; CHWST reset (50–100 %)
        dpSp = dpMax;
        double frac = (loopSp - 50.0) / 50.0; // 0–1
        // Map 0→chwstMax, 1→chwstMin
        chwstSp = chwstMax + frac * (chwstMin - chwstMax);
        trace += "  Stage 2 (CHWST reset): dpSp=" + round1(dpSp) + ", chwstSp=" + round1(chwstSp);
    }

    // Write outputs
    getPlantResetOut().setValue(loopSp);
    getChwDpSpOut().setValue(dpSp);
    getChwstSpOut().setValue(chwstSp);
    getStatusTrace().setValue(trace);
}
```


</details>