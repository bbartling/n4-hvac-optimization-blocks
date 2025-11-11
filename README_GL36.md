# ASHRAE Guideline 36

This sub‑guide consolidates the Niagara 4 ProgramObjects and explanations specific to **ASHRAE Guideline 36** (GL36).  It includes logic for chiller plant enable, AHU fault detection and other GL36‑compliant control strategies.  Each section remains unchanged from the original README to preserve code fidelity.

<!-- Expand the sections below to view full descriptions and code samples. -->

<details>
<summary>🧊 GL36 Chiller Plant Enable Logic</summary>

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
<summary>⏰ GL36 AHU Fault Detection</summary>

* TODO

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java

```

</details>


