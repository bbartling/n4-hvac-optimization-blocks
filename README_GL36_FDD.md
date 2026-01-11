# ASHRAE Guideline 36 FDD




<details>
<summary>⏰ GL36 AHU Fault Detection</summary>

* TODO NOT TEST YET

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/*
 * GL36 AHU Fault Detection Program
 *
 * This Niagara ProgramObject implements multiple air‐handling unit (AHU)
 * fault conditions drawn from the OpenFDD project and ASHRAE Guideline 36.
 * Each fault condition evaluates live point data (temperatures, pressures,
 * damper commands, fan speeds, etc.) and drives a boolean output when the
 * fault persists for a defined number of consecutive samples.  A rolling
 * counter is used instead of full trend data to remain efficient on
 * embedded controllers.  In addition to the rolling fault flags, this
 * program counts AHU operating state changes in the last hour to detect
 * controller “hunting”.  A timer schedules periodic execution and ensures
 * that the station thread is never blocked.
 *
 * Required slots (inputs – all baja:StatusNumeric unless otherwise noted):
 *   enable               — baja:StatusBoolean  master enable; disables logic
 *   ductStatic           — supply duct static pressure (inches)
 *   ductStaticSetpoint   — duct static pressure setpoint (inches)
 *   supplyVfdSpeed       — supply fan VFD speed (0–100 % or fraction 0–1)
 *   mixedAirTemp         — mixed air temperature (°F)
 *   returnAirTemp        — return air temperature (°F)
 *   outsideAirTemp       — outside air temperature (°F)
 *   supplyAirTemp        — supply air temperature (°F)
 *   heatingSignal        — heating coil control signal (0–100 %)
 *   coolingSignal        — cooling coil control signal (0–100 %)
 *   economizerSignal     — outside air damper command (0–100 %)
 *   supplyFanAirVolume   — supply fan airflow volume (cfm)
 *
 * Required slots (configuration parameters – baja:StatusNumeric):
 *   ductStaticErrThres     — allowable static pressure error (inches)
 *   vfdSpeedPercentMax     — max VFD speed for FC1 (percentage)
 *   vfdSpeedErrThres       — allowable VFD speed error (percentage)
 *   mixTempErrThres        — allowable mixed air temp error (°F)
 *   outdoorTempErrThres    — allowable outdoor air temp error (°F)
 *   returnTempErrThres     — allowable return air temp error (°F)
 *   deltaOsMax             — max OS transitions per hour (integer)
 *   ahuMinOaDpr            — minimum outdoor air damper position (fraction)
 *   supplyTempErrThres     — allowable supply air temp error (°F)
 *   deltaTSupplyFan        — temperature rise across supply fan (°F)
 *   airflowErrThres        — allowable OA fraction error (fraction)
 *   ahuMinOaCfmDesign      — design minimum outdoor air flow (cfm)
 *   oatRatDeltaMin         — minimum ∆T between outside and return air (°F)
 *   rollingWindowSize      — number of consecutive samples required to flag
 *
 * Required slots (outputs – all baja:StatusBoolean):
 *   fc1Flag … fc6Flag     — true when the corresponding fault condition is
 *                            active for the configured rolling window
 *   fc4Flag                — hunting fault (transition count beyond limit)
 *   statusMessage         — baja:StatusString human readable diagnostics
 *
 * NOTE: Only the method bodies and helper methods are provided.  Workbench
 *       auto‐generates class definitions, imports and slot getters/setters.
 */

// -----------------------------------------------------------------------------
// Class state
// -----------------------------------------------------------------------------
Clock.Ticket ticket;
private static final int EXEC_PERIOD_SEC = 60;    // run every minute

// Rolling counters for consecutive fault occurrences
private int fc1Count = 0;
private int fc2Count = 0;
private int fc3Count = 0;
private int fc5Count = 0;
private int fc6Count = 0;

// Rolling window size (updated each execute from slot)
private int rollingWindowSize = 5;

// Hunting detection (OS changes)
private final int[] osChangeHistory = new int[60]; // 60 samples ≈ one hour at 1 min interval
private int osIndex = 0;
private int osSum = 0;
private String prevOsState = "";

// -----------------------------------------------------------------------------
// Lifecycle methods
// -----------------------------------------------------------------------------
public void onStart() throws Exception
{
  // Initialize outputs to NULL or false so downstream logic knows the block
  // hasn’t yet produced a meaningful result.
  nullOutputs("AHU FDD program started.");
  // Prime the timer
  updateTimer();
}

public void onExecute() throws Exception
{
  try
  {
    updateTimer();

    // 0. Master enable guard – if disable flag is not OK/true, clear outputs
    if (!safeBool(getEnable(), false))
    {
      nullOutputs("Disabled via enable flag.");
      return;
    }

    // 1. Handle unwired numeric inputs – mark NULL for proper status detection
    ensureNumericWiredOrNull("ductStatic",      getDuctStatic());
    ensureNumericWiredOrNull("ductStaticSetpoint", getDuctStaticSetpoint());
    ensureNumericWiredOrNull("supplyVfdSpeed",    getSupplyVfdSpeed());
    ensureNumericWiredOrNull("mixedAirTemp",      getMixedAirTemp());
    ensureNumericWiredOrNull("returnAirTemp",     getReturnAirTemp());
    ensureNumericWiredOrNull("outsideAirTemp",    getOutsideAirTemp());
    ensureNumericWiredOrNull("supplyAirTemp",     getSupplyAirTemp());
    ensureNumericWiredOrNull("heatingSignal",     getHeatingSignal());
    ensureNumericWiredOrNull("coolingSignal",     getCoolingSignal());
    ensureNumericWiredOrNull("economizerSignal",  getEconomizerSignal());
    ensureNumericWiredOrNull("supplyFanAirVolume",getSupplyFanAirVolume());

    // 2. Read configuration parameters with safe fallbacks
    int rwSlot = (int)safeDouble(getRollingWindowSize(), 5);
    rollingWindowSize = rwSlot > 0 ? rwSlot : 5;

    double ductStaticErrThres   = safeDouble(getDuctStaticErrThres(),   0.0);
    double vfdPercentMax        = safeDouble(getVfdSpeedPercentMax(),   100.0);
    double vfdPercentErrThres   = safeDouble(getVfdSpeedErrThres(),     0.0);
    double mixTempErrThres      = safeDouble(getMixTempErrThres(),      0.0);
    double outdoorTempErrThres  = safeDouble(getOutdoorTempErrThres(),  0.0);
    double returnTempErrThres   = safeDouble(getReturnTempErrThres(),   0.0);
    int    deltaOsMax           = (int)safeDouble(getDeltaOsMax(),      7.0);
    double ahuMinOaDpr          = safeDouble(getAhuMinOaDpr(),          0.2);
    double supplyTempErrThres   = safeDouble(getSupplyTempErrThres(),   0.0);
    double deltaTSupplyFan      = safeDouble(getDeltaTSupplyFan(),      0.0);
    double airflowErrThres      = safeDouble(getAirflowErrThres(),      0.3);
    double ahuMinOaCfmDesign    = safeDouble(getAhuMinOaCfmDesign(),    2500.0);
    double oatRatDeltaMin       = safeDouble(getOatRatDeltaMin(),       10.0);

    // 3. Read inputs and convert units as needed
    // Each safeDouble call returns the numeric value if status is OK, or
    // returns the provided default.  Percent values above 1 are assumed to
    // represent 0–100 % and are scaled to 0–1.
    double ductStatic        = safeDouble(getDuctStatic(),        0.0);
    double ductStaticSetpt   = safeDouble(getDuctStaticSetpoint(),0.0);
    double vfdSpeedRaw       = safeDouble(getSupplyVfdSpeed(),    0.0);
    double vfdSpeed          = vfdSpeedRaw > 1.0 ? vfdSpeedRaw / 100.0 : vfdSpeedRaw;
    double mat               = safeDouble(getMixedAirTemp(),      0.0);
    double rat               = safeDouble(getReturnAirTemp(),     0.0);
    double oat               = safeDouble(getOutsideAirTemp(),    0.0);
    double sat               = safeDouble(getSupplyAirTemp(),     0.0);
    double heatSigRaw        = safeDouble(getHeatingSignal(),     0.0);
    double heatSig           = heatSigRaw > 1.0 ? heatSigRaw / 100.0 : heatSigRaw;
    double coolSigRaw        = safeDouble(getCoolingSignal(),     0.0);
    double coolSig           = coolSigRaw > 1.0 ? coolSigRaw / 100.0 : coolSigRaw;
    double econSigRaw        = safeDouble(getEconomizerSignal(),  0.0);
    double econSig           = econSigRaw > 1.0 ? econSigRaw / 100.0 : econSigRaw;
    double supplyAirVolume   = safeDouble(getSupplyFanAirVolume(),0.0);

    // 4. Evaluate Fault Condition 1 – Low duct static pressure while fan is near max
    boolean fc1Cond = false;
    {
      double vfdMax = vfdPercentMax > 1.0 ? vfdPercentMax / 100.0 : vfdPercentMax;
      double vfdErr = vfdPercentErrThres > 1.0 ? vfdPercentErrThres / 100.0 : vfdPercentErrThres;
      boolean staticLow = ductStatic < (ductStaticSetpt - ductStaticErrThres);
      boolean fanHigh   = vfdSpeed >= (vfdMax - vfdErr);
      fc1Cond = staticLow && fanHigh;
      // Update rolling counter
      fc1Count = fc1Cond ? fc1Count + 1 : 0;
      boolean fc1Flag = fc1Count >= rollingWindowSize;
      // Write output
      setBooleanStatus(getFc1Flag(), fc1Flag);
    }

    // 5. Evaluate Fault Condition 2 – Mixed air too cold
    boolean fc2Cond = false;
    {
      // Only valid when the fan is running (>1 % duty)
      boolean fanRunning = vfdSpeed > 0.01;
      double matAdj = mat - mixTempErrThres;
      double ratAdj = rat - returnTempErrThres;
      double oatAdj = oat - outdoorTempErrThres;
      double minRef = Math.min(ratAdj, oatAdj);
      fc2Cond = fanRunning && (matAdj < minRef);
      fc2Count = fc2Cond ? fc2Count + 1 : 0;
      boolean fc2Flag = fc2Count >= rollingWindowSize;
      setBooleanStatus(getFc2Flag(), fc2Flag);
    }

    // 6. Evaluate Fault Condition 3 – Mixed air too hot
    boolean fc3Cond = false;
    {
      boolean fanRunning = vfdSpeed > 0.01;
      double matAdj = mat - mixTempErrThres;
      double ratAdj = rat + returnTempErrThres;
      double oatAdj = oat + outdoorTempErrThres;
      double maxRef = Math.max(ratAdj, oatAdj);
      fc3Cond = fanRunning && (matAdj > maxRef);
      fc3Count = fc3Cond ? fc3Count + 1 : 0;
      boolean fc3Flag = fc3Count >= rollingWindowSize;
      setBooleanStatus(getFc3Flag(), fc3Flag);
    }

    // 7. Evaluate Fault Condition 4 – Excessive operating state changes (hunting)
    boolean fc4Flag;
    {
      // Determine current operating state
      String osState;
      boolean econActive  = econSig > 0.0;
      boolean heating     = heatSig > 0.0;
      boolean cooling     = coolSig > 0.0;
      if (econActive && cooling)      osState = "econ+cool";
      else if (econActive)            osState = "econ";
      else if (heating)               osState = "heating";
      else if (cooling)               osState = "cooling";
      else if (vfdSpeed > ahuMinOaDpr)osState = "minOA";
      else                            osState = "off";

      // Detect a change from the previous state
      int changed = (prevOsState.equals(osState) ? 0 : 1);
      prevOsState = osState;
      // Rolling 60‑sample buffer: subtract the value being overwritten
      osSum -= osChangeHistory[osIndex];
      osChangeHistory[osIndex] = changed;
      osSum += changed;
      osIndex = (osIndex + 1) % osChangeHistory.length;
      // Fault if the number of changes in the last hour exceeds the threshold
      fc4Flag = osSum > deltaOsMax;
      setBooleanStatus(getFc4Flag(), fc4Flag);
    }

    // 8. Evaluate Fault Condition 5 – SAT too low in heating mode
    boolean fc5Cond = false;
    {
      boolean heatingMode = heatSig > 0.01;
      boolean fanRunning  = vfdSpeed > 0.01;
      double satAdj = sat + supplyTempErrThres;
      double matRef = mat - mixTempErrThres + deltaTSupplyFan;
      fc5Cond = heatingMode && fanRunning && (satAdj <= matRef);
      fc5Count = fc5Cond ? fc5Count + 1 : 0;
      boolean fc5Flag = fc5Count >= rollingWindowSize;
      setBooleanStatus(getFc5Flag(), fc5Flag);
    }

    // 9. Evaluate Fault Condition 6 – Outdoor air fraction discrepancy
    boolean fc6Cond = false;
    {
      // Only evaluate when fan is running
      boolean fanRunning = vfdSpeed > 0.0;
      if (fanRunning)
      {
        double ratMinusOat = Math.abs(rat - oat);
        // percent OA calculation; if denom is zero use 0
        double denom = (oat - rat);
        double percentOaCalc = 0.0;
        if (Math.abs(denom) > 0.0)
        {
          percentOaCalc = (mat - rat) / denom;
          if (percentOaCalc < 0.0) percentOaCalc = 0.0;
        }
        double percOaMin = 0.0;
        if (supplyAirVolume > 0.0)
        {
          percOaMin = ahuMinOaCfmDesign / supplyAirVolume;
        }
        double oaError = Math.abs(percentOaCalc - percOaMin);
        boolean os1HtgMode = (ratMinusOat >= oatRatDeltaMin) && (oaError > airflowErrThres)
                              && (heatSig > 0.0) && (vfdSpeed > 0.0);
        boolean os4ClgMode = (ratMinusOat >= oatRatDeltaMin) && (oaError > airflowErrThres)
                              && (heatSig == 0.0) && (coolSig > 0.0)
                              && (vfdSpeed > 0.0) && (Math.abs(econSig - ahuMinOaDpr) < 0.0001);
        fc6Cond = os1HtgMode || os4ClgMode;
      }
      fc6Count = fc6Cond ? fc6Count + 1 : 0;
      boolean fc6Flag = fc6Count >= rollingWindowSize;
      setBooleanStatus(getFc6Flag(), fc6Flag);
    }

    // 10. Build a status message summarising current faults
    String trace = "fc1=" + (getFc1Flag().getValue() ? "1" : "0") +
                   ", fc2=" + (getFc2Flag().getValue() ? "1" : "0") +
                   ", fc3=" + (getFc3Flag().getValue() ? "1" : "0") +
                   ", fc4=" + (getFc4Flag().getValue() ? "1" : "0") +
                   ", fc5=" + (getFc5Flag().getValue() ? "1" : "0") +
                   ", fc6=" + (getFc6Flag().getValue() ? "1" : "0");
    updateStatus(trace);
  }
  catch (Exception e)
  {
    // Never allow exceptions to propagate — mark outputs NULL and log error
    nullOutputs("Error in AHU FDD program: " + e.toString());
  }
}

public void onStop() throws Exception
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }
  nullOutputs("AHU FDD program stopped.");
}

// -----------------------------------------------------------------------------
// Helper methods
// -----------------------------------------------------------------------------

/**
 * Schedule the next execution after EXEC_PERIOD_SEC seconds.  Any existing
 * ticket is cancelled before scheduling a new one.  This function must be
 * called on every onStart and onExecute invocation to maintain periodic
 * operation.  The scheduling pattern follows the Niagara examples in the
 * beginner tutorial and ensures no busy loop is used.
 */
private void updateTimer()
{
  if (ticket != null) ticket.cancel();
  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(EXEC_PERIOD_SEC),
      BProgram.execute,
      null
  );
}

/**
 * Safely read a numeric slot.  If the status is not OK, return the provided
 * fallback value.  This helper prevents null pointer exceptions and allows
 * algorithm continuity when upstream data is invalid.  A status of NULL
 * indicates the point is unwired or has been forced to null via
 * ensureNumericWiredOrNull().
 */
private double safeDouble(BStatusNumeric num, double fallback)
{
  if (num == null) return fallback;
  BStatus st = num.getStatus();
  if (st == null || !st.isOk()) return fallback;
  return num.getValue();
}

/**
 * Safely read a boolean slot.  If the status is not OK, return the fallback
 * value.  This helper is used for the master enable and other flags.
 */
private boolean safeBool(BStatusBoolean b, boolean fallback)
{
  if (b == null) return fallback;
  BStatus st = b.getStatus();
  if (st == null || !st.isOk()) return fallback;
  return b.getValue();
}

/**
 * Mark a numeric slot as NULL if it is unwired.  This mirrors the pattern
 * shown in the fault‑aware math example in the beginner tutorials where
 * unlinked inputs are detected via getLinks() and forced to NULL so that
 * downstream logic can clearly see the missing data.  Exceptions thrown
 * during inspection are ignored to avoid breaking the logic.
 */
private void ensureNumericWiredOrNull(String slotName, BStatusNumeric point)
{
  try
  {
    if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0)
    {
      point.setValue(0);
      point.setStatus(BStatus.nullStatus);
    }
  }
  catch (Exception ignore)
  {
    // safest is to leave status as‐is
  }
}

/**
 * Convenience method to write a boolean output with OK status.  A boolean
 * output is considered faulted only when its status is not OK; here we
 * explicitly set it to OK to avoid inheriting upstream statuses.  The
 * value is updated regardless of its prior state.
 */
private void setBooleanStatus(BStatusBoolean out, boolean value)
{
  try
  {
    out.setValue(value);
    out.setStatus(BStatus.ok);
  }
  catch (Exception ignore)
  {
    // ignore failures when outputs are unwired
  }
}

/**
 * Write a human‑readable string to the statusMessage slot and print to
 * Application Director.  Using the timestamp helps correlate log entries
 * across components.  This method is modelled on the History Min/Max
 * tutorial’s updateStatus() helper.
 */
private void updateStatus(String msg)
{
  String stamp = BAbsTime.now().toString();
  String full  = stamp + " — " + msg;
  // Console output
  System.out.println("[AhuFdd] " + full);
  try
  {
    getStatusMessage().setValue(full);
  }
  catch (Exception ignore)
  {
    // ignore if statusMessage slot is missing
  }
}

/**
 * Clear all fault flags and set their statuses to NULL.  A common
 * practice in Niagara program objects is to set outputs to NULL when
 * disabled or faulted so that downstream components recognise the
 * absence of valid data.  The trace string is recorded via updateStatus().
 */
private void nullOutputs(String trace)
{
  setBooleanStatus(getFc1Flag(), false);
  getFc1Flag().setStatus(BStatus.nullStatus);
  setBooleanStatus(getFc2Flag(), false);
  getFc2Flag().setStatus(BStatus.nullStatus);
  setBooleanStatus(getFc3Flag(), false);
  getFc3Flag().setStatus(BStatus.nullStatus);
  setBooleanStatus(getFc4Flag(), false);
  getFc4Flag().setStatus(BStatus.nullStatus);
  setBooleanStatus(getFc5Flag(), false);
  getFc5Flag().setStatus(BStatus.nullStatus);
  setBooleanStatus(getFc6Flag(), false);
  getFc6Flag().setStatus(BStatus.nullStatus);
  updateStatus(trace);
}
```

</details>


