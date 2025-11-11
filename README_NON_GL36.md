# Non‑GL36 & Advanced Logic

This sub‑guide contains simplified resets and advanced logic that are **not** part of ASHRAE Guideline 36.  Here you will find alternative AHU resets, chiller plant chilled‑water temperature reset and the advanced per‑chiller duty‑cycle rotator.  All content is retained exactly from the original README.

<!-- Expand a summary below to reveal the full description and code. -->

<details>
<summary>🌀 Non-GL36 AHU Duct Static Pressure Reset (Simplified Logic)</summary>

This block provides a **simpler alternative** to ASHRAE Guideline 36’s T&R logic.  
Instead of field-level request counting, it floats the **duct static pressure setpoint** based directly on the **maximum VAV damper position** feedback.  

* ✅ Easier to configure — no special request logic at the VAV level.  
* ✅ Robust — falls back to max static pressure if inputs are invalid.  
* ⚙️ Typical thresholds: trims down when max VAV damper < 80%, floats up when > 90%.  

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/nonG36ahuDuctStaticResetSnip.png" alt="Non-G36 AHU Duct Static Pressure Reset Snip" width="700">
</p>

---

#### Developer Notes

* Set `IgnoreCount` for small vs large systems (ignore 0–2 high outliers).  
* Holds a startup setpoint until fan has been ON for the configured lag.  
* Uses **simple deadband and trim increment** to keep SP stable.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
Clock.Ticket ticket;

boolean fanWasOff = true;
long fanOnTimestamp = 0;
long lastMainLogicRun = 0;

public void onStart() throws Exception {
    getTrimRespVal().setValue(0.1);
    getDuctPressMin().setValue(0.5);
    getDuctPressMax().setValue(1.2);
    getStartupLagSeconds().setValue(600);
    getStartupAhuDuctPressSetpoint().setValue(0.5);
    getAhuDuctPressStpOut().setValue(1.2);
    getActiveUpdateInterval().setValue(300.0);
    getStatusTrace().setValue("Program started.");

    lastMainLogicRun = System.currentTimeMillis();
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();

    BStatusNumeric[] vavDprInputs = {
        getVavDprPos1(), getVavDprPos2(), getVavDprPos3(), getVavDprPos4(), getVavDprPos5(),
        getVavDprPos6(), getVavDprPos7(), getVavDprPos8(), getVavDprPos9(), getVavDprPos10(),
        getVavDprPos11(), getVavDprPos12(), getVavDprPos13(), getVavDprPos14(), getVavDprPos15(),
        getVavDprPos16(), getVavDprPos17(), getVavDprPos18(), getVavDprPos19(), getVavDprPos20(),
        getVavDprPos21(), getVavDprPos22(), getVavDprPos23(), getVavDprPos24(), getVavDprPos25(),
        getVavDprPos26(), getVavDprPos27(), getVavDprPos28(), getVavDprPos29(), getVavDprPos30()
    };

    for (int i = 0; i < vavDprInputs.length; i++) {
        if (getComponent().getLinks(getComponent().getSlot("vavDprPos" + (i + 1))).length == 0) {
            vavDprInputs[i].setValue(0);
            vavDprInputs[i].setStatus(BStatus.NULL);
        }
    }

    long now = System.currentTimeMillis();
    int intervalSec = 300;
    BStatusNumeric intervalInput = getUpdateIntervalSeconds();
    if (intervalInput.getStatus().isOk()) {
        double raw = intervalInput.getValue();
        intervalSec = (int) Math.max(10, Math.min(raw, 3600));
    }
    getActiveUpdateInterval().setValue(intervalSec);
    if ((now - lastMainLogicRun) / 1000 < intervalSec) return;
    lastMainLogicRun = now;

    int ignoreCount = 0;
    BStatusNumeric nInput = getIgnoreCount();
    if (nInput.getStatus().isOk()) {
        ignoreCount = (int) Math.max(0, Math.min(nInput.getValue(), 30));
    }

    double trimIncrement = Math.max(0.0, getTrimRespVal().getValue());
    double minPress = Math.max(0.0, Math.min(getDuctPressMin().getValue(), 10.0));
    double maxPress = Math.max(minPress, Math.min(getDuctPressMax().getValue(), 10.0));
    int lagSeconds = (int) Math.max(0, Math.min(getStartupLagSeconds().getValue(), 3600));

    ArrayList<Double> validValues = new ArrayList<>();
    for (BStatusNumeric input : vavDprInputs) {
        if (input.getStatus().isOk()) {
            validValues.add(input.getValue());
        }
    }

    if (validValues.isEmpty() || validValues.size() <= ignoreCount) {
        getVavDprFilteredMax().setValue(0.0);
        getVavDprFilteredAvg().setValue(0.0);
        getAhuDuctPressStpOut().setValue(maxPress);
        getStatusTrace().setValue("No valid VAV data → fallback to maxPress: " + round1(maxPress));
        return;
    }

    validValues.sort(Collections.reverseOrder());
    List<Double> filtered = validValues.subList(ignoreCount, validValues.size());

    double sum = 0.0;
    for (double val : filtered) sum += val;
    double vavAvg = sum / filtered.size();
    double vavMax = filtered.get(0);

    getVavDprFilteredMax().setValue(vavMax);
    getVavDprFilteredAvg().setValue(vavAvg);

    // Fan tracking
    BStatusBoolean fanStatus = getAhuFanStatus();
    boolean fanOn = fanStatus.getValue();
    
    double currentSP = getAhuDuctPressStpOut().getStatus().isOk()
        ? getAhuDuctPressStpOut().getValue()
        : maxPress;
    
    double startupPress = getStartupAhuDuctPressSetpoint().getStatus().isOk()
        ? getStartupAhuDuctPressSetpoint().getValue()
        : maxPress;
    
    double targetPress;
    
    if (!fanOn) {
        fanWasOff = true;
        fanOnTimestamp = 0;
        targetPress = startupPress;
        getStatusTrace().setValue("Fan OFF → waiting for building startup...  SP = " + round1(targetPress));
    } else if (fanWasOff) {
        fanWasOff = false;
        fanOnTimestamp = now;
        targetPress = startupPress;
        getStatusTrace().setValue("Fan ON → startup lag begins...  SP = " + round1(targetPress));
    } else if ((now - fanOnTimestamp) / 1000 < lagSeconds) {
        targetPress = startupPress;
        getStatusTrace().setValue("Startup lag active → holding SP = " + round1(targetPress));
    } else {
        if (vavMax >= 90.0) {
            targetPress = Math.min(currentSP + trimIncrement, maxPress);
            getStatusTrace().setValue("Trim ↑ Increase SP → VAV Max = " + round1(vavMax) + "  → SP = " + round1(targetPress));
        } else if (vavMax <= 80.0) {
            targetPress = Math.max(currentSP - trimIncrement, minPress);
            getStatusTrace().setValue("Trim ↓ Decrease SP → VAV Max = " + round1(vavMax) + "  → SP = " + round1(targetPress));
        } else {
            targetPress = currentSP;
            getStatusTrace().setValue("Deadband → Hold SP = " + round1(targetPress));
        }
    }
    getAhuDuctPressStpOut().setValue(targetPress);
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
}

public BComponent getProgram() {
    return (BComponent) getComponent();
}

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getProgram(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

// Round to 1 decimal place
double round1(double val) {
    return Math.round(val * 10.0) / 10.0;
}

```

---

</details>



<details>
<summary>🌡️ Non-GL36 AHU Supply Air Temperature Reset (Simplified Logic)</summary>

This block is a **simplified SAT reset** algorithm that avoids Guideline 36 request counting.
It drives the **supply air temperature setpoint** using only:

* Zone cooling demand (VAV valve positions)
* Outside air temperature lockouts
* Simple trim/float logic

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/nonG36ahuLeaveTempBlockSnip.png" alt="Non-G36 AHU Supply Air Temp Reset Snip" width="700">
</p>

---

#### Developer Notes

* Easier to deploy — just wire in VAV zone demand signals and OAT.
* Holds startup SAT until fan has been ON for the configured lag.
* Falls back to `satMax` if no valid data.
* Trims down when max zone demand is high; floats up when low.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java
Clock.Ticket ticket;

boolean fanWasOff = true;
long fanOnTimestamp = 0;
long lastMainLogicRun = 0;

public void onStart() throws Exception {
    getTrimRespVal().setValue(0.5);
    getSatMin().setValue(55.0);
    getSatMax().setValue(65.0);
    getOutTempConstSatMinStp().setValue(80.0);
    getStartupLagSeconds().setValue(600);
    getStartupAhuSATSetpoint().setValue(65.0);
    getAhuSATSetpointOut().setValue(65.0);
    getActiveUpdateInterval().setValue(300.0);
    getStatusTrace().setValue("Program started.");

    lastMainLogicRun = System.currentTimeMillis();
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();

    BStatusNumeric[] vavDemandInputs = {
        getVavZoneDemand1(), getVavZoneDemand2(), getVavZoneDemand3(), getVavZoneDemand4(), getVavZoneDemand5(),
        getVavZoneDemand6(), getVavZoneDemand7(), getVavZoneDemand8(), getVavZoneDemand9(), getVavZoneDemand10(),
        getVavZoneDemand11(), getVavZoneDemand12(), getVavZoneDemand13(), getVavZoneDemand14(), getVavZoneDemand15(),
        getVavZoneDemand16(), getVavZoneDemand17(), getVavZoneDemand18(), getVavZoneDemand19(), getVavZoneDemand20(),
        getVavZoneDemand21(), getVavZoneDemand22(), getVavZoneDemand23(), getVavZoneDemand24(), getVavZoneDemand25(),
        getVavZoneDemand26(), getVavZoneDemand27(), getVavZoneDemand28(), getVavZoneDemand29(), getVavZoneDemand30()
    };

    for (int i = 0; i < vavDemandInputs.length; i++) {
        if (getComponent().getLinks(getComponent().getSlot("vavZoneDemand" + (i + 1))).length == 0) {
            vavDemandInputs[i].setValue(0);
            vavDemandInputs[i].setStatus(BStatus.NULL);
        }
    }

    long now = System.currentTimeMillis();
    int intervalSec = 300;
    BStatusNumeric intervalInput = getUpdateIntervalSeconds();
    if (intervalInput.getStatus().isOk()) {
        double raw = intervalInput.getValue();
        intervalSec = (int) Math.max(10, Math.min(raw, 3600));
    }
    getActiveUpdateInterval().setValue(intervalSec);
    if ((now - lastMainLogicRun) / 1000 < intervalSec) return;
    lastMainLogicRun = now;

    int ignoreCount = 0;
    BStatusNumeric nInput = getIgnoreCount();
    if (nInput.getStatus().isOk()) {
        ignoreCount = (int) Math.max(0, Math.min(nInput.getValue(), 30));
    }

    double trimIncrement = Math.max(0.0, getTrimRespVal().getValue());
    double minSAT = Math.max(50.0, Math.min(getSatMin().getValue(), 65.0));
    double maxSAT = Math.max(minSAT, Math.min(getSatMax().getValue(), 70.0));
    int lagSeconds = (int) Math.max(0, Math.min(getStartupLagSeconds().getValue(), 3600));

    ArrayList<Double> validValues = new ArrayList<>();
    for (BStatusNumeric input : vavDemandInputs) {
        if (input.getStatus().isOk()) {
            validValues.add(input.getValue());
        }
    }

    if (validValues.isEmpty() || validValues.size() <= ignoreCount) {
        getVavZoneDemandFilteredMax().setValue(0.0);
        getVavZoneDemandFilteredAvg().setValue(0.0);
        getAhuSATSetpointOut().setValue(maxSAT);
        getStatusTrace().setValue("No valid VAV demand → fallback to maxSAT: " + round1(maxSAT));
        return;
    }

    validValues.sort(Collections.reverseOrder());
    List<Double> filtered = validValues.subList(ignoreCount, validValues.size());

    double sum = 0.0;
    for (double val : filtered) sum += val;
    double demandAvg = sum / filtered.size();
    double demandMax = filtered.get(0);

    getVavZoneDemandFilteredMax().setValue(demandMax);
    getVavZoneDemandFilteredAvg().setValue(demandAvg);

    // Fan tracking
    BStatusBoolean fanStatus = getAhuFanStatus();
    BStatusNumeric oat = getOutsideAirTemp();
    boolean fanOn = fanStatus.getValue();

    if (!fanOn) {
        fanWasOff = true;
        fanOnTimestamp = 0;
    }

    if (fanWasOff && fanOn) {
        fanWasOff = false;
        fanOnTimestamp = now;
    }

    double currentSP = getAhuSATSetpointOut().getStatus().isOk()
        ? getAhuSATSetpointOut().getValue()
        : maxSAT;

    double startupSAT = getStartupAhuSATSetpoint().getStatus().isOk()
        ? getStartupAhuSATSetpoint().getValue()
        : maxSAT;

    double targetSAT = currentSP;

    if (oat.getStatus().isOk() && oat.getValue() >= (getOutTempConstSatMinStp().getValue() + 1.0)) {
        targetSAT = minSAT;
        getStatusTrace().setValue("OA Temp high → lock to minSAT: SP = " + round1(minSAT));
    } else if (!fanOn) {
        targetSAT = startupSAT;
        getStatusTrace().setValue("Fan OFF → waiting for building startup...  SP = " + round1(targetSAT));
    } else if ((now - fanOnTimestamp) / 1000 < lagSeconds) {
        targetSAT = startupSAT;
        getStatusTrace().setValue("Fan ON → startup lag active...  SP = " + round1(targetSAT));
    } else {
        if (demandMax >= 30.0) {
            targetSAT = Math.max(currentSP - trimIncrement, minSAT);
            getStatusTrace().setValue("Trim ↓ Decrease SP → VAV Max = " + round1(demandMax) + "  → SP = " + round1(targetSAT));
        } else if (demandMax <= 10.0) {
            targetSAT = Math.min(currentSP + trimIncrement, maxSAT);
            getStatusTrace().setValue("Trim ↑ Increase SP → VAV Max = " + round1(demandMax) + "  → SP = " + round1(targetSAT));
        } else {
            targetSAT = currentSP;
            getStatusTrace().setValue("Deadband → Hold SP = " + round1(targetSAT));
        }
    }

    getAhuSATSetpointOut().setValue(targetSAT);
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
}

public BComponent getProgram() {
    return (BComponent) getComponent();
}

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getProgram(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

double round1(double val) {
    return Math.round(val * 10.0) / 10.0;
}

```

</details>



<details>
<summary>💧 Chiller Plant Chilled-Water Supply Temperature Reset</summary>

* TODO

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java

```

</details>



<details>

<summary>🧊 Advanced Chiller Rotator (Per-Chiller Duty Cycle)</summary>

This program block implements an advanced chiller staging and rotation strategy designed for high reliability and equipment protection. It calculates the total number of required chillers based on temperature, load, and critical room demands, and then intelligently enables chillers based on their individual availability and readiness.

This logic supersedes simpler staging methods by enforcing **per-chiller minimum run and off times**, ensuring that if the lead chiller in the rotation is not ready (e.g., has just shut off), the system will instantly **skip it** and bring on the next available unit to meet demand without delay.

> NOTE that this is just a concept idea that has not been fully tested.

🔗 [LinkedIn Article](https://www.linkedin.com/posts/activity-7334973935777652736-mrRk?utm_source=share&utm_medium=member_desktop&rcm=ACoAAA0kR5wBTiy3drJcr-0Nl_8MNQFMlHxnETU)


<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/chillerRotatorBlockSnip.png" alt="Chiller Rotator Wiresheet" width="800">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/chillerRotatorBlockLogs.png" alt="Chiller Rotator Console Logs" width="800">
  <br><em>Chiller Rotator wiresheet with corresponding console logs in the Platform Admin showing per-chiller timer status.</em>
</p>

---

### **Inputs**

| Slot | Type | Notes |
| :--- | :--- | :--- |
| `waterTemp` | `BStatusNumeric` | Current chilled water temperature. |
| `tempSetpoint` | `BStatusNumeric` | The desired water temperature setpoint. |
| `loadMW` | `BStatusNumeric` | The current cooling load in megawatts (MW). |
| `systemEnable` | `BStatusBoolean` | Master enable for the entire program. |
| `bladeRoom1Demand` | `BStatusBoolean` | `true` if Blade Room 1 requires a chiller. |
| `bladeRoom2Demand` | `BStatusBoolean` | `true` if Blade Room 2 requires a chiller. |
| `bladeRoom3Demand` | `BStatusBoolean` | `true` if Blade Room 3 requires a chiller. |
| `chillerXAvailable` | `BStatusBoolean` | Individual availability status for each chiller (1-8). |
| `currentDutyCycle` | `BStatusNumeric` | The active duty rotation sequence (1–8). |
| `tempStageUpDeadband` | `BStatusNumeric` | Temperature deadband to prevent staging on minor fluctuations. |
| `minChillerRunTimeMinutes` | `BStatusNumeric` | Minimum runtime before a chiller can be turned off. |
| `minChillerOffTimeMinutes` | `BStatusNumeric` | Minimum off-time before a chiller can be restarted. |
| `updateIntervalSeconds` | `BStatusNumeric` | Logic execution rate in seconds. |
| `printLogsToConsole` | `BStatusBoolean` | Enables verbose output to Niagara console when `true`. |

---

### **Outputs**

| Slot | Type | Description |
| :--- | :--- | :--- |
| `chillerXEnable` | `BStatusBoolean` | Run command for each chiller (1–8). |
| `currentSequence` | `BStatusNumeric` | Current duty rotation being followed. |
| `statusTraceSummary` | `BStatusString` | Displays number of chillers required vs enabled. |
| `statusTraceTemp` | `BStatusString` | Status message from temperature staging logic. |
| `statusTraceLoad` | `BStatusString` | Status message from load-based staging logic. |
| `statusTraceBlade` | `BStatusString` | Displays how many blade rooms are actively requesting cooling. |

---

### **Key Features**

- **Per-Chiller Timers:** Tracks `lastStartTime` and `lastStopTime` for every chiller to enforce individual run/off time constraints.
- **Instant Skip Logic:** If a chiller is unavailable or cooling down, the logic instantly skips to the next one in sequence.
- **Demand Aggregation:** Adds 1 chiller per blade room demand in addition to temperature/load-based requirements.
- **Minimum Chiller Guarantee:** Always enables at least 1 chiller (if any are available) for redundancy and flow.
- **Verbose Logging:** Use `printLogsToConsole = true` to display trace messages in the `Application Director Console`

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/**
 * REWRITTEN CHILLER ROTATOR LOGIC (June 2025, version 2)
 *
 * This program manages a chiller plant using advanced, per-chiller duty cycle logic.
 *
 * Staging Logic:
 * 1. A "base demand" is calculated from the maximum of Temperature Demand and Load Demand.
 * 2. Blade Room Demand is ADDITIVE, instantly adding to the base demand.
 * 3. A MINIMUM of one chiller is always required to run.
 * 4. A data structure now tracks the state of each individual chiller.
 * 5. The logic enforces a Minimum Run Time and Minimum Off Time on a PER-CHILLER basis.
 * 6. If the lead chiller in the duty cycle is not ready (e.g., in min-off-time),
 * the logic will instantly SKIP IT and enable the next available and ready chiller in the rotation.
 */

// An inner class to hold the individual state for each chiller.
static class ChillerState {
    long lastStartTime = 0; // Timestamp when the chiller was last started.
    long lastStopTime = 0;  // Timestamp when the chiller was last stopped.
}

// Member variables
private Clock.Ticket ticket;
private long lastMainLogicRun = 0;

// An array to hold the state objects for all 8 chillers.
private ChillerState[] chillerStates = new ChillerState[8];

// Static constants for load thresholds and duty rotations remain the same.
static final double[] LOAD_UP_THRESHOLDS = { 1.3, 2.6, 3.9, 5.2, 6.5, 7.8, 9.1, 10.4 };
static final double[] LOAD_DOWN_THRESHOLDS = { 1.2, 2.5, 3.8, 5.1, 6.4, 7.7, 9.0 };
static final int[][] DUTY_ROTATIONS = {
    { 0, 1, 2, 3, 4, 5, 6, 7 }, 
    { 1, 2, 3, 4, 5, 6, 7, 0 }, 
    { 2, 3, 4, 5, 6, 7, 0, 1 },
    { 3, 4, 5, 6, 7, 0, 1, 2 }, 
    { 4, 5, 6, 7, 0, 1, 2, 3 }, 
    { 5, 6, 7, 0, 1, 2, 3, 4 },
    { 6, 7, 0, 1, 2, 3, 4, 5 }, 
    { 7, 0, 1, 2, 3, 4, 5, 6 }
};

/**
 * Called once when the program starts. Initializes default values and the chiller state array.
 */
public void onStart() throws Exception {
    // --- Initialize Input Slots with Defaults ---
    if (getWaterTemp().isNull()) setWaterTemp(new BStatusNumeric(18.0));
    if (getTempSetpoint().isNull()) setTempSetpoint(new BStatusNumeric(18.0));
    if (getLoadMW().isNull()) setLoadMW(new BStatusNumeric(0.0));
    if (getUpdateIntervalSeconds().isNull()) setUpdateIntervalSeconds(new BStatusNumeric(15));
    if (getCurrentDutyCycle().isNull()) setCurrentDutyCycle(new BStatusNumeric(1));
    if (getTempStageUpDeadband().isNull()) setTempStageUpDeadband(new BStatusNumeric(0.5));
    if (getMinChillerRunTimeMinutes().isNull()) setMinChillerRunTimeMinutes(new BStatusNumeric(15.0));
    if (getMinChillerOffTimeMinutes().isNull()) setMinChillerOffTimeMinutes(new BStatusNumeric(10.0));
    if (getBladeRoom1Demand().isNull()) setBladeRoom1Demand(new BStatusBoolean(false));
    if (getBladeRoom2Demand().isNull()) setBladeRoom2Demand(new BStatusBoolean(false));
    if (getBladeRoom3Demand().isNull()) setBladeRoom3Demand(new BStatusBoolean(false));
    if (getPrintLogsToConsole().isNull()) setPrintLogsToConsole(new BStatusBoolean(false));

    // --- Initialize the state object for each chiller ---
    for (int i = 0; i < 8; i++) {
        chillerStates[i] = new ChillerState();
    }
    
    getStatusTraceSummary().setValue("Program started.");
    updateTimer();
}

/**
 * Main execution loop, completely rewritten for per-chiller logic.
 */
public void onExecute() throws Exception {
    updateTimer();

    long now = System.currentTimeMillis();
    if ((now - lastMainLogicRun) / 1000 < getUpdateIntervalSeconds().getValue()) {
        return;
    }
    lastMainLogicRun = now;

    if (!getSystemEnable().getValue()) {
        disableAllChillers();
        getStatusTraceSummary().setValue("System disabled. All chillers OFF.");
        return;
    }

    logDebug("--- [Cycle Start] ---");

    // --- 1. Demand Calculation ---
    int chillersByTemp = handleTemperatureStaging(getWaterTemp().getValue(), getTempSetpoint().getValue());
    int chillersByLoad = handleLoadStaging(getLoadMW().getValue());
    int chillersByBladeRooms = handleBladeRoomDemand();
    
    int baseDemand = Math.max(chillersByTemp, chillersByLoad);
    int requiredChillers = Math.min(8, Math.max(1, baseDemand + chillersByBladeRooms));
    logDebug(String.format("Demand -> Temp: %d, Load: %d, Blade: %d | Final Required: %d",
        chillersByTemp, chillersByLoad, requiredChillers - baseDemand, requiredChillers));

    // --- 2. Get Current State and Rotation ---
    int dutyIndex = (int) getCurrentDutyCycle().getValue() - 1;
    if (dutyIndex < 0 || dutyIndex >= DUTY_ROTATIONS.length) dutyIndex = 0;
    int[] rotationOrder = DUTY_ROTATIONS[dutyIndex];
    getCurrentSequence().setValue(dutyIndex + 1);

    boolean[] isAvailable = {
        getChiller1Available().getValue(), getChiller2Available().getValue(), getChiller3Available().getValue(), getChiller4Available().getValue(),
        getChiller5Available().getValue(), getChiller6Available().getValue(), getChiller7Available().getValue(), getChiller8Available().getValue()
    };
    boolean[] isRunning = new boolean[8];
    for(int i = 0; i < 8; i++) isRunning[i] = getChillerEnable(i+1).getValue();

    // --- 3. Determine Next Enable State with Per-Chiller Timers ---
    boolean[] nextEnableState = new boolean[8];
    int enabledCount = 0;
    long minRunTimeMillis = (long) (getMinChillerRunTimeMinutes().getValue() * 60 * 1000);
    long minOffTimeMillis = (long) (getMinChillerOffTimeMinutes().getValue() * 60 * 1000);

    // First, lock in any chillers that MUST keep running due to min-run-time.
    for (int i = 0; i < 8; i++) {
        if (isRunning[i] && (now - chillerStates[i].lastStartTime < minRunTimeMillis)) {
            nextEnableState[i] = true;
            enabledCount++;
        }
    }
    logDebug("Chillers locked by min-run time: " + enabledCount);

    // Now, iterate through the duty cycle to bring on additional chillers if needed.
    if (enabledCount < requiredChillers) {
        for (int chillerIndex : rotationOrder) {
            if (enabledCount >= requiredChillers) break;
            if (!nextEnableState[chillerIndex] && isAvailable[chillerIndex]) {
                if (now - chillerStates[chillerIndex].lastStopTime >= minOffTimeMillis) {
                    nextEnableState[chillerIndex] = true;
                    enabledCount++;
                } else {
                    logDebug("Skipping Chiller " + (chillerIndex + 1) + ": in min-off-time.");
                }
            }
        }
    }
    
    // --- 4. Set Final Outputs and Update State Timestamps ---
    StringBuilder enabledChillersStr = new StringBuilder();
    for (int i = 0; i < 8; i++) {
        boolean shouldBeRunning = nextEnableState[i];
        
        if (shouldBeRunning && !isRunning[i]) {
            chillerStates[i].lastStartTime = now;
            logDebug("Chiller " + (i+1) + " STARTING.");
        } 
        else if (!shouldBeRunning && isRunning[i]) {
            chillerStates[i].lastStopTime = now;
            logDebug("Chiller " + (i+1) + " STOPPING.");
        }

        setChillerEnable(i + 1, shouldBeRunning);
        if (shouldBeRunning) {
            enabledChillersStr.append("Chiller").append(i + 1).append(" ");
        }
    }
    logDebug("Final Enable Array: " + java.util.Arrays.toString(nextEnableState));
    
    // NEW: Log the individual run/off times for each chiller for better debugging.
    if (getPrintLogsToConsole().getStatus().isOk() && getPrintLogsToConsole().getValue()) {
        StringBuilder timerLog = new StringBuilder("-- Chiller Timers --\n");
        for (int i = 0; i < 8; i++) {
            if (nextEnableState[i]) {
                long runMillis = now - chillerStates[i].lastStartTime;
                timerLog.append(String.format(" Chiller %d: RUNNING for %.1f mins\n", i + 1, runMillis / 60000.0));
            } else {
                long offMillis = now - chillerStates[i].lastStopTime;
                if (chillerStates[i].lastStopTime > 0) {
                     timerLog.append(String.format(" Chiller %d: OFF for %.1f mins\n", i + 1, offMillis / 60000.0));
                } else {
                     timerLog.append(String.format(" Chiller %d: OFF (never run)\n", i + 1));
                }
            }
        }
        System.out.println(timerLog.toString().trim());
    }
    
    getStatusTraceSummary().setValue("Required: " + requiredChillers + " | Enabled: " + (enabledChillersStr.length() > 0 ? enabledChillersStr.toString().trim() : "None"));
}


/**
 * SIMPLIFIED load staging logic.
 */
private int handleLoadStaging(double load) {
    int targetChillers = 0;
    for (int i = 0; i < LOAD_UP_THRESHOLDS.length; i++) {
        if (load > LOAD_UP_THRESHOLDS[i]) {
            targetChillers = i + 1;
        }
    }
    targetChillers = Math.min(targetChillers, 8);
    getStatusTraceLoad().setValue("Load requires " + targetChillers + " chiller(s).");
    logDebug("[Load Calc] Load of " + round1(load) + " MW requires " + targetChillers + " chiller(s).");
    return targetChillers;
}


// --- Unchanged Methods ---

private int handleTemperatureStaging(double waterTemp, double setpoint) {
    double deadband = getTempStageUpDeadband().getValue();
    double delta = waterTemp - setpoint;
    if (delta <= deadband) {
        getStatusTraceTemp().setValue("Temp stable (" + round1(waterTemp) + "°C).");
        return 0;
    } else {
        int required = (int) Math.floor(delta - deadband);
        required = Math.min(required, 8);
        getStatusTraceTemp().setValue("Temp high (" + round1(waterTemp) + "°C). Staging " + required + " chiller(s).");
        return required;
    }
}

private int handleBladeRoomDemand() {
    int bladeRoomsDemanding = 0;
    if (getBladeRoom1Demand().getValue()) bladeRoomsDemanding++;
    if (getBladeRoom2Demand().getValue()) bladeRoomsDemanding++;
    if (getBladeRoom3Demand().getValue()) bladeRoomsDemanding++;
    getStatusTraceBlade().setValue(bladeRoomsDemanding + " blade room(s) requesting cooling.");
    return bladeRoomsDemanding;
}

private void logDebug(String message) {
    if (getPrintLogsToConsole().getStatus().isOk() && getPrintLogsToConsole().getValue()) {
        System.out.println(message);
    }
}

// Helper to get current enable state of a specific chiller
private BStatusBoolean getChillerEnable(int chillerNum) {
    switch (chillerNum) {
        case 1: return getChiller1Enable();
        case 2: return getChiller2Enable();
        case 3: return getChiller3Enable();
        case 4: return getChiller4Enable();
        case 5: return getChiller5Enable();
        case 6: return getChiller6Enable();
        case 7: return getChiller7Enable();
        case 8: return getChiller8Enable();
    }
    return null; // Should not happen
}

private void setChillerEnable(int chillerNum, boolean enable) {
    switch (chillerNum) {
        case 1: getChiller1Enable().setValue(enable); break;
        case 2: getChiller2Enable().setValue(enable); break;
        case 3: getChiller3Enable().setValue(enable); break;
        case 4: getChiller4Enable().setValue(enable); break;
        case 5: getChiller5Enable().setValue(enable); break;
        case 6: getChiller6Enable().setValue(enable); break;
        case 7: getChiller7Enable().setValue(enable); break;
        case 8: getChiller8Enable().setValue(enable); break;
    }
}

private void disableAllChillers() {
    for (int i = 1; i <= 8; i++) {
        setChillerEnable(i, false);
    }
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    int interval = 15;
    if (getUpdateIntervalSeconds().getStatus().isOk()) {
        interval = (int) getUpdateIntervalSeconds().getValue();
    }
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(interval), BProgram.execute, null);
}

private double round1(double val) {
    return Math.round(val * 10.0) / 10.0;
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

```

</details>


