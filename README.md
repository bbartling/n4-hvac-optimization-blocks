# n4-hvac-optimization-blocks

![Leave Temp Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/vibecoder.png)

This repo provides **Java-based optimization logic** for Niagara 4 (N4) control systems. All vibe coded designed and tested by Ben, the logic is modeled after **ASHRAE Guideline 36** strategies with enhancements for practical deployments.

---

## 📦 Available Optimization Blocks

This repository includes drop-in Java algorithm blocks for Niagara 4. All logic is implemented in the `bensCustomPallette.pallette` file as `bog` wire sheet views. Download this repo as a zip file or use git directly.

To use:

1. Navigate to your **Workbench → User Home** directory.
2. Copy the `.bog` file from the GitHub repo into this folder.
3. Open the `.bog` file inside Niagara, copy its contents into a running station.
4. Wire in your HVAC input/output points.

---

<details>
<summary>📘 AHU Duct Static Pressure Reset (Trim & Respond)</summary>

**Purpose:** Save supply fan energy by resetting duct static pressure based on VAV damper positions.

![Duct Static Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/ahuDuctStaticResetSnip.png)

#### ✅ Logic Summary:

* Every update interval, the logic reads connected VAV damper positions (up to 30).
* **Trim up** if max VAV ≥ 90%, **trim down** if max VAV ≤ 80%.
* Neutral zone in between (hold pressure steady).
* During **AHU OFF** or **Startup Lag**, hold a defined **Startup Duct Pressure Setpoint**.
* One or more rogue zones (e.g. wide open damper) can be excluded using **Ignore Count**.
* Values are clamped between `ductPressMin` and `ductPressMax`.

#### 🧠 Developer Notes:

* Uses internal `Clock.schedule()` 10s loop for responsive updates.
* Status debug messages written to `statusTrace` (e.g., "Trim up", "Deadband").
* Output written to: `ahuDuctPressStpOut`.

#### 📄 Example Code:

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

</details>

---

<details>
<summary>📗 AHU Supply Air Temperature Reset (Trim & Respond)</summary>

**Purpose:** Reset discharge air temp based on VAV zone demand values.

![Leave Temp Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/ahuLeaveTempBlockSnip.png)

#### ✅ Logic Summary:

* Every update interval, reads demand values from up to 30 zones.
* **Trim colder** if max VAV demand ≥ 30%, **trim warmer** if ≤ 10%.
* If outside air temp is very high (OAT > threshold), **lock to minSAT** to prevent humidity issues.
* Handles **Startup Lag** and **Fan OFF** by forcing SAT to `startupAhuSATSetpoint`.
* Ignores highest `N` values defined by **Ignore Count** to avoid rogue zones.

#### 🧠 Developer Notes:

* Works with demand signals from zone controllers.
* Uses internal 10s clock timer for status refresh.
* Debug strings written to `statusTrace` (e.g., "Startup lag", "Lock to minSAT").

#### 📄 Example Code:

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

---

<details>
<summary>🧊 Full Java Code for Chiller Rotator</summary>

[Linkedin Article](https://www.linkedin.com/posts/activity-7334973935777652736-mrRk?utm_source=share&utm_medium=member_desktop&rcm=ACoAAA0kR5wBTiy3drJcr-0Nl_8MNQFMlHxnETU)

```java
// Full Java code starts here

Clock.Ticket ticket;
long lastMainLogicRun = 0;

// Temperature staging variables
int chillersStagedByTemp = 0;
long tempHighStartTime = 0;
boolean tempHighActive = false;

// Load staging variables
int chillersStagedByLoad = 0;
long loadChangeStartTime = 0;
boolean loadIncreasePending = false;
boolean loadDecreasePending = false;

// Blade Room Demand
static final double[] loadUpThresholds = { 1.3, 2.6, 3.9, 5.2, 6.5, 7.8, 9.1, 10.4 };
static final double[] loadDownThresholds = { 1.2, 2.5, 3.8, 5.1, 6.4, 7.7, 9.0 };

// Chiller weekly rotation schedule
static final int[][] DUTY_ROTATIONS = {
    { 0, 1, 2, 3, 4, 5, 6, 7 }, 
    { 1, 2, 3, 4, 5, 6, 7, 0 },
    { 2, 3, 4, 5, 6, 7, 0, 1 },
    { 3, 4, 5, 6, 7, 0, 1, 2 },
    { 4, 5, 6, 7, 0, 1, 2, 3 },
    { 5, 6, 7, 0, 1, 2, 3, 4 },
    { 6, 7, 0, 1, 2, 3, 4, 5 },
    { 7, 0, 1, 2, 3, 4, 5, 6 },
    { 0, 1, 2, 3, 4, 5, 6, 7 }
};

public void onStart() throws Exception {
    // Initialization code
    safeSetNumeric("waterTemp", 18.0);
    safeSetNumeric("tempSetpoint", 18.0);
    safeSetNumeric("loadMW", 0.0);
    safeSetNumeric("updateIntervalSeconds", 15);
    safeSetNumeric("currentDutyCycle", 1);

    safeSetBoolean("systemEnable", true);
    safeSetBoolean("bladeRoom1Demand", false);
    safeSetBoolean("bladeRoom2Demand", false);
    safeSetBoolean("bladeRoom3Demand", false);

    for (int i = 1; i <= 8; i++) {
        safeSetBoolean("chiller" + i + "Available", true);
    }

    getStatusTraceSummary().setValue("Program started.");
    lastMainLogicRun = System.currentTimeMillis();
    updateTimer();
}

// Safe setters
void safeSetNumeric(String slotName, double value) { /*...*/ }
void safeSetBoolean(String slotName, boolean value) { /*...*/ }

public void onExecute() throws Exception {
    updateTimer();

    long now = System.currentTimeMillis();
    if (getComponent() == null) return;

    double intervalSec = ((BStatusNumeric) getComponent().get("updateIntervalSeconds")).getValue();
    if ((now - lastMainLogicRun) / 1000 < intervalSec) return;
    lastMainLogicRun = now;

    boolean systemEnable = ((BStatusBoolean) getComponent().get("systemEnable")).getValue();
    if (!systemEnable) {
        disableAllChillers();
        getStatusTraceSummary().setValue("System disabled. All chillers OFF.");
        return;
    }

    double waterTemp = ((BStatusNumeric) getComponent().get("waterTemp")).getValue();
    double tempSet = ((BStatusNumeric) getComponent().get("tempSetpoint")).getValue();
    double load = ((BStatusNumeric) getComponent().get("loadMW")).getValue();

    int chillersByTemp = handleTemperatureStaging(waterTemp, tempSet);
    int chillersByLoad = handleLoadStaging(load);
    int chillersByBladeRooms = handleBladeRoomDemand();

    int minRequiredChillers = chillersByBladeRooms;
    int calculatedChillers = Math.max(chillersByTemp, chillersByLoad);
    int requiredChillers = Math.max(minRequiredChillers, calculatedChillers);

    int dutyScheduleIndex = (int) (((BStatusNumeric) getComponent().get("currentDutyCycle")).getValue()) - 1;
    if (dutyScheduleIndex < 0 || dutyScheduleIndex >= DUTY_ROTATIONS.length) dutyScheduleIndex = 0;

    boolean[] chillerAvailable = new boolean[8];
    for (int i = 0; i < 8; i++) {
        chillerAvailable[i] = ((BStatusBoolean) getComponent().get("chiller" + (i + 1) + "Available")).getValue();
    }

    boolean[] chillerEnable = new boolean[8];
    int enabledCount = 0;
    int[] rotationOrder = DUTY_ROTATIONS[dutyScheduleIndex];

    for (int i = 0; i < 8 && enabledCount < requiredChillers; i++) {
        int chillerIdx = rotationOrder[i];
        if (chillerAvailable[chillerIdx]) {
            chillerEnable[chillerIdx] = true;
            enabledCount++;
        }
    }

    for (int i = 0; i < 8; i++) {
        ((BStatusBoolean) getComponent().get("chiller" + (i + 1) + "Enable")).setValue(chillerEnable[i]);
    }

    ((BStatusNumeric) getComponent().get("currentSequence")).setValue(dutyScheduleIndex + 1);
    getStatusTraceSummary().setValue("Running. Enabled: " + enabledCount + " chillers.");
}

// Temperature staging logic
int handleTemperatureStaging(double waterTemp, double tempSet) { /*...*/ }

// Load staging logic
int handleLoadStaging(double load) { /*...*/ }

// Blade Room Demand logic
int handleBladeRoomDemand() { /*...*/ }

// Timer and helper methods
void updateTimer() { /*...*/ }
void disableAllChillers() { /*...*/ }

// Rounding helper
double round1(double val) {
    return Math.round(val * 10.0) / 10.0;
}
```

</details>

---

<details>
<summary>📊 JACE Resource Management – Best Practices</summary>

To avoid Niagara runtime issues, monitor JACE system health:

![Resource Usage](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/resource_management.png)

#### Guidelines:

* **CPU Usage:** Try to keep < 80% on average. Spikes are okay if brief.
* **Heap Usage:** Keep `heap.used` < 75% of `heap.total`.

**What to Watch:**

| Metric                       | Limit                                                 |
| ---------------------------- | ----------------------------------------------------- |
| `heap.used`                  | < 75%                                                 |
| `CPU %`                      | Avg < 80%                                             |
| `resources.category.program` | Avoid frequent `Clock.schedule()` or unbounded loops. |

</details>

---

## 🔄 Future Plans

* Chiller optimization blocks
* Tutorials for how to push ChatGPT in program object block development


---


## 📜 License
This repo is released under the **MIT License**, ensuring it remains free and accessible for all.
---

【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.