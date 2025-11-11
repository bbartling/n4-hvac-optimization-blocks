# GL36 Trim & Respond

This sub‑guide focuses on the **Trim & Respond** methodology defined in ASHRAE Guideline 36.  It covers variable definitions, VAV box zone requests and supply/duct static pressure resets.  The sections below are copied verbatim from the original README.

<!-- Click on each summary to expand the corresponding section. -->

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

////////////////////////////////////////////////////////////////
// Class-level fields & constants
////////////////////////////////////////////////////////////////

Clock.Ticket ticket;

// ===== Global timing (shared period) =====
private static final int EXEC_PERIOD_SEC = 10;    // Program executes every 10 seconds

// ===== Pressure timing / thresholds =====
private static final int PRESS_PERSIST_SEC = 60; // 1 minute persistence
private static final double PRESS_RATIO_3REQ      = 0.50;
private static final double PRESS_DAMPER_3REQ_MIN = 95.0;
private static final double PRESS_RATIO_2REQ      = 0.70;
private static final double PRESS_DAMPER_2REQ_MIN = 95.0;
private static final double PRESS_DAMPER_1REQ_ON  = 95.0;
private static final double PRESS_DAMPER_1REQ_OFF = 85.0;

// Pressure timers and state
double pressHighTimerSec = 0.0;
double pressMedTimerSec  = 0.0;
int    lastPressureReq   = 0;
double lastPressDamperPct    = 0.0;
double lastPressFlowRatio    = 0.0;


// ===== Temperature timing / thresholds =====

// *** NEW: Constants for both unit systems ***
// Metric (Celsius)
private static final double TEMP_HIGH_DIFF_C = 3.0;
private static final double TEMP_MED_DIFF_C  = 2.0;

// Imperial (Fahrenheit)
private static final double TEMP_HIGH_DIFF_F = 5.0;
private static final double TEMP_MED_DIFF_F  = 3.0;
// *** END NEW ***

// Persistence/Suppression (unchanged)
private static final int TEMP_PERSIST_SEC    = 120; // 2 minutes
private static final int TEMP_SUPPRESS_SEC   = 60;  // 1 minute

// Cooling loop (unchanged)
private static final double TEMP_LOOP_1REQ_ON  = 95.0;
private static final double TEMP_LOOP_1REQ_OFF = 85.0;

// Temperature timers and state (independent from pressure)
double tempHighTimerSec     = 0.0;
double tempMedTimerSec      = 0.0;
double tempSuppressTimerSec = 0.0;
int    lastTempReq          = 0;
double lastTempDiff         = 0.0;
double lastTempLoopPct      = 0.0;

////////////////////////////////////////////////////////////////
// Helpers
////////////////////////////////////////////////////////////////

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
  }
  catch (Exception e) { /* ignore */ }
}

int clampInt(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

double round1(double v) {
  return Math.round(v * 10.0) / 10.0;
}

////////////////////////////////////////////////////////////////
// Lifecycle
////////////////////////////////////////////////////////////////

public void onStart() throws Exception {
  // Initialize all timers and last-request states
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

  // *** NEW: Initialize the unit toggle ***
  try {
      if (getUseImperial().isNull()) {
          getUseImperial().setValue(false); // Default to Metric (false)
      }
  } catch (Exception e) {
      System.out.println("[G36_VAV_Req] WARN: 'useImperial' slot not found. Add BStatusBoolean slot. Defaulting to Metric.");
  }
  // *** END NEW ***

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

////////////////////////////////////////////////////////////////
// Main Execute
////////////////////////////////////////////////////////////////

public void onExecute() throws Exception {
  updateTimer();

  // Normalize unwired inputs → NULL
  ensureNumericWiredOrNull("vavDamperCmd",   getVavDamperCmd());
  ensureNumericWiredOrNull("vavFlow",        getVavFlow());
  ensureNumericWiredOrNull("vavFlowSpt",     getVavFlowSpt());
  ensureNumericWiredOrNull("zoneCoolingSpt", getZoneCoolingSpt());
  ensureNumericWiredOrNull("zoneTemp",       getZoneTemp());
  ensureNumericWiredOrNull("zoneDemand",     getZoneDemand());

  // Advance temperature suppression timer
  if (tempSuppressTimerSec < TEMP_SUPPRESS_SEC) {
    tempSuppressTimerSec += EXEC_PERIOD_SEC;
    if (tempSuppressTimerSec > TEMP_SUPPRESS_SEC) {
      tempSuppressTimerSec = TEMP_SUPPRESS_SEC;
    }
  }

  // *** NEW: Get Unit System ***
  boolean isImperial = false; // Default to Metric
  try {
      if (getUseImperial().getStatus().isOk()) {
          isImperial = getUseImperial().getValue();
      }
  } catch (Exception e) { /* Slot doesn't exist, use default */ }

  // Set diff thresholds based on unit system
  final double tempHighDiff;
  final double tempMedDiff;

  if (isImperial) {
      tempHighDiff = TEMP_HIGH_DIFF_F;
      tempMedDiff  = TEMP_MED_DIFF_F;
  } else {
      tempHighDiff = TEMP_HIGH_DIFF_C;
      tempMedDiff  = TEMP_MED_DIFF_C;
  }
  // *** END NEW ***

  // Call compute functions
  int pressReq = computePressureRequest();
  // Pass the dynamic diffs to the compute function
  int coolReq  = computeTemperatureRequest(tempHighDiff, tempMedDiff); 

  pressReq = clampInt(pressReq, 0, 3);
  coolReq  = clampInt(coolReq, 0, 3);

  getVavPressureRequests().setValue(pressReq);
  getVavCoolRequests().setValue(coolReq);

  lastPressureReq = pressReq;
  lastTempReq     = coolReq;

  // ------------ Pressure status trace (Corrected) ------------
  if (getPressStatusTrace() != null) {
      double flowPct = lastPressFlowRatio * 100.0;
      String pMsg =
          "Req=" + pressReq +
          " damper=" + round1(lastPressDamperPct) + "%, flow%Sp=" + round1(flowPct) +
          ", timers[high=" + pressHighTimerSec + "s/" + PRESS_PERSIST_SEC +
          ", med=" + pressMedTimerSec + "s/" + PRESS_PERSIST_SEC + "]";
      getPressStatusTrace().setValue(pMsg);
  }

  // ------------ Temperature status trace (Corrected & Enhanced) ------------
  if (getTempStatusTrace() != null) {
      // *** MODIFIED TRACE ***
      // Add the unit and the dynamic diff values
      String unit = isImperial ? "F" : "C";
      String tMsg =
          "Req=" + coolReq +
          " dT=" + round1(lastTempDiff) + unit + // Added unit
          ", loop=" + round1(lastTempLoopPct) + "%, timers[high=" + tempHighTimerSec +
          "s/" + TEMP_PERSIST_SEC + " (>" + round1(tempHighDiff) + unit + "), med=" + tempMedTimerSec + // Added threshold
          "s/" + TEMP_PERSIST_SEC + " (>" + round1(tempMedDiff) + unit + "), sup=" + tempSuppressTimerSec + // Added threshold
          "s/" + TEMP_SUPPRESS_SEC + "]";
      // *** END MODIFIED TRACE ***

      getTempStatusTrace().setValue(tMsg);
  }
}

////////////////////////////////////////////////////////////////
// Pressure Request Logic
// (This logic was correct and is unchanged)
////////////////////////////////////////////////////////////////

int computePressureRequest() {
  BStatusNumeric damperSlot = getVavDamperCmd();
  BStatusNumeric flowSlot   = getVavFlow();
  BStatusNumeric spSlot     = getVavFlowSpt();

  if (!damperSlot.getStatus().isOk() ||
      !flowSlot.getStatus().isOk()   ||
      !spSlot.getStatus().isOk()) {
    pressHighTimerSec   = 0.0;
    pressMedTimerSec    = 0.0;
    lastPressDamperPct  = 0.0;
    lastPressFlowRatio  = 0.0;
    return 0;
  }

  double damper = damperSlot.getValue();
  double flow   = flowSlot.getValue();
  double sp     = spSlot.getValue();

  double ratio;
  if (sp > 0.0) {
    ratio = flow / sp;
  } else {
    ratio = 1.0;
    pressHighTimerSec = 0.0;
    pressMedTimerSec  = 0.0;
  }

  lastPressDamperPct = damper;
  lastPressFlowRatio = (sp > 0.0) ? ratio : 0.0;

  // 3 REQUESTS
  boolean cond3 = (sp > 0.0) &&
                  (ratio < PRESS_RATIO_3REQ) &&
                  (damper >= PRESS_DAMPER_3REQ_MIN);
  if (cond3) {
    pressHighTimerSec += EXEC_PERIOD_SEC;
  } else {
    pressHighTimerSec = 0.0;
  }
  if (pressHighTimerSec >= PRESS_PERSIST_SEC) {
    pressMedTimerSec = 0.0;
    return 3;
  }

  // 2 REQUESTS
  boolean cond2 = (sp > 0.0) &&
                  (ratio < PRESS_RATIO_2REQ) &&
                  (damper >= PRESS_DAMPER_2REQ_MIN);
  if (cond2) {
    pressMedTimerSec += EXEC_PERIOD_SEC;
  } else {
    pressMedTimerSec = 0.0;
  }
  if (pressMedTimerSec >= PRESS_PERSIST_SEC) {
    return 2;
  }

  // 1 REQUEST
  int req;
  if (damper > PRESS_DAMPER_1REQ_ON) {
    req = 1;
  }
  else {
    if (lastPressureReq == 1 && damper >= PRESS_DAMPER_1REQ_OFF) {
      req = 1;
    } else {
      req = 0;
    }
  }
  return req;
}

////////////////////////////////////////////////////////////////
// Temperature Request Logic
// (*** THIS IS THE MODIFIED FUNCTION ***)
////////////////////////////////////////////////////////////////

// *** MODIFIED SIGNATURE: Now accepts diff thresholds ***
int computeTemperatureRequest(double highDiff, double medDiff) {
    boolean suppressDone = (tempSuppressTimerSec >= TEMP_SUPPRESS_SEC);

    // ---- Read inputs (safe status checks) ----
    BStatusNumeric spSlot = getZoneCoolingSpt();
    BStatusNumeric tempSlot = getZoneTemp();
    BStatusNumeric loopSlot = getZoneDemand();

    boolean haveTempData = spSlot.getStatus().isOk() && tempSlot.getStatus().isOk();

    double sp = 0.0;
    double tz = 0.0;
    double diff = 0.0;

    if (haveTempData) {
        sp = spSlot.getValue();
        tz = tempSlot.getValue();
        diff = tz - sp; // positive = too warm
    }

    lastTempDiff = diff; // store for trace

    // ---------- 3 & 2 REQUESTS: temp overshoot with persistence ----------
    if (!haveTempData || !suppressDone) {
        tempHighTimerSec = 0.0;
        tempMedTimerSec = 0.0;
    } else {
        // *** MODIFIED LOGIC ***
        // Use the arguments 'highDiff' and 'medDiff'
        boolean condHigh = (diff >= highDiff);
        boolean condMed = (diff >= medDiff);
        // *** END OF MODIFIED LOGIC ***

        if (condHigh) {
            tempHighTimerSec += EXEC_PERIOD_SEC;
            tempMedTimerSec = 0.0;
        } else if (condMed) {
            tempMedTimerSec += EXEC_PERIOD_SEC;
            tempHighTimerSec = 0.0;
        } else {
            tempHighTimerSec = 0.0;
            tempMedTimerSec = 0.0;
        }

        // Check persistence
        if (tempHighTimerSec >= TEMP_PERSIST_SEC) {
            return 3;
        }
        if (tempMedTimerSec >= TEMP_PERSIST_SEC) {
            return 2;
        }
    }

    // ---------- 1 REQUEST based on cooling loop (zoneDemand) ----------
    double loop = 0.0;
    boolean haveLoop = loopSlot.getStatus().isOk();

    if (haveLoop) {
        loop = loopSlot.getValue();
    }

    lastTempLoopPct = haveLoop ? loop : 0.0;

    int req;
    if (haveLoop && loop > TEMP_LOOP_1REQ_ON) {
        req = 1;
    } else {
        if (lastTempReq == 1 && haveLoop && loop >= TEMP_LOOP_1REQ_OFF) {
            req = 1;
        } else {
            req = 0;
        }
    }
    return req;
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
 * Version 5 - Final Robust Version.
 * This program resets duct static pressure based on VAV damper requests,
 * inspired by ASHRAE Guideline 36 and the Normal Framework implementation.
 * This version ensures the output setpoint is ALWAYS driven to a known state
 * in every possible logic path within onExecute().
 */

// ===== Class-level state =====
Clock.Ticket ticket;

long lastMainLogicRunMs = 0;   // enforces UpdateMinutes cadence
long fanOnStableSinceMs = 0;   // enforces StartUpDelayMinutes true-for window
boolean lastFanRun = false;    // edge detect for fan ON

// ===== onStart =====
public void onStart() throws Exception {
    // Initialize state variables and start the timer.
    // The onExecute() method is responsible for all output driving.
    getStatusTrace().setValue("sp-trim-and-respond: program started.");
    lastMainLogicRunMs = 0;
    fanOnStableSinceMs = 0;
    lastFanRun = false;

    updateTimer(); // 10s heartbeat
}

// ===== onExecute (Main logic loop) =====
public void onExecute() throws Exception {
    updateTimer(); // Reschedule the next execution
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

    boolean fanRun = getFanRunCmd().getStatus().isOk() && getFanRunCmd().getValue();
    double currentSp = getDischargeAirPressureSp().getStatus().isOk()
        ? getDischargeAirPressureSp().getValue()
        : SP0;

    // --- State 1: Fan is OFF ---
    // Unconditionally drive the output to the initial setpoint (SP0).
    if (!fanRun) {
        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0);

        if (lastFanRun) { // Log only on the transition from ON to OFF
            getStatusTrace().setValue("Fan OFF -> driving SP0 = " + round3(sp0));
            getLastActionTs().setValue(new java.util.Date(now).toString());
        }
        
        fanOnStableSinceMs = 0; // Reset startup timer
        lastFanRun = false;     // Set state for next edge detection
        return;
    }

    // --- State 2: Fan just turned ON (Edge Detection) ---
    // Explicitly set the setpoint to SP0 to begin the startup delay period.
    if (!lastFanRun && fanRun) {
        fanOnStableSinceMs = now;
        lastFanRun = true;
        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0); // Explicitly drive output
        getStatusTrace().setValue("Fan ON -> holding SP0 during startup delay...");
        getLastActionTs().setValue(new java.util.Date(now).toString());
        return;
    }
    
    // Ensure fan state is correct for the current cycle
    lastFanRun = true;

    // --- State 3: Fan is ON, but waiting for startup delay to complete ---
    boolean isStartupDelayMet = (now - fanOnStableSinceMs) / 1000 >= TdSec;
    if (!isStartupDelayMet) {
        long remaining = TdSec - ((now - fanOnStableSinceMs) / 1000);
        double sp0 = clamp(SP0, SPmin, SPmax);
        getDischargeAirPressureSp().setValue(sp0); // Explicitly hold output at SP0
        getStatusTrace().setValue("Waiting Td (" + remaining + "s left)... SP=" + round3(sp0));
        return;
    }
    
    // --- State 4: Waiting for T&R update cadence ---
    boolean isUpdateCadenceMet = (lastMainLogicRunMs == 0) || ((now - lastMainLogicRunMs) / 1000 >= TSec);
    if (!isUpdateCadenceMet) {
        // It is safe to return here, as the previous T&R cycle already set the value.
        // The status trace is not updated to prevent log spam.
        return;
    }

    // --- State 5: Run Core Trim & Respond Logic ---
    if (!getTotalRequests().getStatus().isOk()) {
        getStatusTrace().setValue("Missing totalRequests -> no T&R action this cycle.");
        return;
    }
    double R = getTotalRequests().getValue();

    double newSetpoint;
    String action;

    if (R <= Ignore) {
        action = "trim";
        newSetpoint = clamp(currentSp + SPtrim, SPmin, SPmax);
    } else {
        action = "respond";
        double respondAmount = Math.min(SPres * (R - Ignore), SPResMax);
        newSetpoint = clamp(currentSp + respondAmount, SPmin, SPmax);
    }

    getDischargeAirPressureSp().setValue(newSetpoint);
    lastMainLogicRunMs = now;

    String detail = "R=" + round3(R) + " -> " + action.toUpperCase() + " SP: " + round3(currentSp) + " -> " + round3(newSetpoint);
    getStatusTrace().setValue(detail);
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

// ===== onStop =====
public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

// ===== Helper Methods =====
void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL);
        }
    } catch (Exception e) { /* ignore */ }
}

void ensureBooleanWiredOrNull(String slotName, BStatusBoolean point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(false);
            point.setStatus(BStatus.NULL);
        }
    } catch (Exception e) { /* ignore */ }
}

double clamp(double v, double lo, double hi) {
    return Math.max(lo, Math.min(v, hi));
}

int minutesToSecondsSafe(BStatusNumeric minsSlot, int defMin) {
    double m = defMin;
    if (minsSlot.getStatus().isOk()) {
        m = minsSlot.getValue();
    }
    m = Math.max(0.0, Math.min(m, 240.0)); // Clamp 0–240 min
    return (int)Math.round(m * 60.0);
}

double numericOrDefault(BStatusNumeric slot, double defVal) {
    return slot.getStatus().isOk() ? slot.getValue() : defVal;
}

double round3(double v) {
    return Math.round(v * 1000.0) / 1000.0;
}
```

</details>



<details>
<summary>🌡️ GL36 AHU Supply Air Temperature Reset (Trim & Respond)</summary>

![SAT Reset Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/ahuLeaveTempBlockSnip.png)


This ProgramObject implements **ASHRAE Guideline 36 – Section 5.16.2.2 Trim & Respond**, which governs how the **AHU Supply Air Temperature (SAT)** setpoint resets based on cooling requests from zones served by the AHU.

The Trim & Respond algorithm continuously adjusts the SAT setpoint upward (“trim”) or downward (“respond”) depending on the number of active cooling requests, keeping supply air temperature as high as possible while still satisfying zone loads.

---

### 📘 Guideline 36 – Table 5.16.2.2 Trim & Respond Variables

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

### 🌡️ Example Configuration (from G36 Figure 5.16.2.2)

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
 * Version 8 - FIX - Corrected Fan OFF logic to reset setpoint and tMaxState to SP0.
 * This program resets the SAT setpoint based on zone requests and outside air temp,
 * inspired by ASHRAE Guideline 36.
 */

// ===== Class-level state =====
Clock.Ticket ticket;

long lastMainLogicRunMs = 0;   // enforces UpdateMinutes cadence
long fanOnStableSinceMs = 0;   // enforces StartUpDelayMinutes true-for window
boolean lastFanRun = false;    // edge detect for fan ON
private double tMaxState = 70.0; // Private variable to hold tMax state

// ===== onStart =====
public void onStart() throws Exception {
    // Initialize state variables and start the timer.
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

// ===== onExecute (Main logic loop) =====
public void onExecute() throws Exception {
    updateTimer(); // Reschedule the next execution
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

    boolean fanRun = getFanRunCmd().getStatus().isOk() && getFanRunCmd().getValue();
    double oat = getOutsideAirTemp().getStatus().isOk()
                 ? getOutsideAirTemp().getValue()
                 : minOAT;

    double currentSp = getDischargeAirTempSp().getStatus().isOk()
                       ? getDischargeAirTempSp().getValue()
                       : maxSAT;

    // --- State 1: Fan is OFF ---
    if (!fanRun) {
        // --- FIX START ---
        // On fan OFF, reset both the internal state (tMaxState) and the
        // output setpoint (DischargeAirTempSp) back to the initial setpoint (SP0).
        double sp0 = numericOrDefault(getSP0(),
                       numericOrDefault(getSPmax(), maxSAT));
        
        this.tMaxState = clamp(sp0, minSAT, maxSAT); // Reset internal state to SP0
        getDischargeAirTempSp().setValue(this.tMaxState); // Set output directly to SP0
        // --- FIX END ---


        if (lastFanRun) { // Log only on the transition from ON to OFF
            // --- FIX START ---
            // Updated status trace to reflect the change
            getStatusTrace().setValue("Fan OFF -> resetting SP to SP0 = " + round1(this.tMaxState));
            // --- FIX END ---
            getLastActionTs().setValue(new java.util.Date(now).toString());
        }

        fanOnStableSinceMs = 0;
        lastFanRun = false;
        return;
    }

    // --- State 2: Fan just turned ON (Edge Detection) ---
    if (!lastFanRun && fanRun) {
        fanOnStableSinceMs = now;
        lastFanRun = true;

        // On fan start, reinitialize T-max from SP0 (fall back to SPmax if needed)
        // This logic was already correct and uses the value we just set in State 1.
        double sp0 = numericOrDefault(getSP0(),
                       numericOrDefault(getSPmax(), maxSAT));
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
    if (!getTotalRequests().getStatus().isOk()) {
        getStatusTrace().setValue("Missing totalRequests -> no T&R action this cycle.");
        return;
    }
    double R = getTotalRequests().getValue();   // G36 R

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

    double newSetpoint = interpolate(oat, minOAT, this.tMaxState,
                                     maxOAT, minSAT, minSAT, maxSAT);
    getDischargeAirTempSp().setValue(newSetpoint);
    lastMainLogicRunMs = now;

    String detail = "R=" + round1(R) + " -> " + action.toUpperCase()
                    + " -> tMax=" + round1(this.tMaxState)
                    + " -> Final SP=" + round1(newSetpoint);
    getStatusTrace().setValue(detail);
    getLastActionTs().setValue(new java.util.Date(now).toString());
}

// ===== onStop =====
public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

// ===== Helper Methods (unchanged) =====
void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

void ensureNumericWiredOrNull(String slotName, BStatusNumeric point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL);
        }
    } catch (Exception e) { /* ignore */ }
}

void ensureBooleanWiredOrNull(String slotName, BStatusBoolean point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(false);
            point.setStatus(BStatus.NULL);
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


