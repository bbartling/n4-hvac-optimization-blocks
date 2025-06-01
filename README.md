# n4-hvac-optimization-blocks

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
<summary> Chiller Rotator</summary>

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

Oh yes — **absolutely possible and highly recommended**! ✅

---

### 🔥 **Why Break Up into Separate Functions?**

* Makes the code **modular** and **readable**.
* Each function only handles **one scenario**.
* Easier to **test**, **debug**, and **maintain**.
* Easier for another engineer (or future-you) to understand which logic is which.

---

### ✅ **Plan — Breakup**

| Scenario | New Function Name            | Description                                        |
| -------- | ---------------------------- | -------------------------------------------------- |
| 1        | `handleTemperatureStaging()` | Temperature control based on flow temp vs setpoint |
| 2        | `handleLoadStaging()`        | Load staging based on load MW                      |
| 3        | `handleBladeRoomDemand()`    | Add chillers based on BladeRoom demand inputs      |

---

### 🧩 **Sketch of New Function Structure**

```java
int handleTemperatureStaging(double waterTemp, double tempSet)
{
    // Logic for temperature-based chiller staging (Scenario 1)
}

int handleLoadStaging(double load)
{
    // Logic for load-based chiller staging (Scenario 2)
}

int handleBladeRoomDemand()
{
    // Logic for BladeRoom additional chiller requirement (Scenario 3)
}
```

And then in `onExecute()` or `determineChillersToRun()`:

```java
int chillersByTemp = handleTemperatureStaging(waterTemp, tempSet);
int chillersByLoad = handleLoadStaging(load);
int chillersByBladeRooms = handleBladeRoomDemand();

int requiredChillers = Math.max(chillersByTemp, chillersByLoad) + chillersByBladeRooms;
```

💡 **Why `Math.max`?**

* If temperature says "5 chillers" and load says "3 chillers," we obey the **highest** demand.
* Plus any **extra chillers** for the BladeRoom demand.

---

### 📝 **Example of Full Function Breakup**

#### 🔹 **Scenario 1 — Temperature Staging**

```java
long tempHighStartTime = 0;
boolean tempHighActive = false;

int handleTemperatureStaging(double waterTemp, double tempSet)
{
    if (waterTemp >= tempSet + 2.0) {
        return 8; // Immediate max chillers
    } else if (waterTemp >= tempSet + 1.0) {
        if (!tempHighActive) {
            tempHighActive = true;
            tempHighStartTime = System.currentTimeMillis();
        } else {
            long elapsed = (System.currentTimeMillis() - tempHighStartTime) / 1000;
            if (elapsed >= 600) {
                return 1; // After 10 min, stage one more chiller
            }
        }
    } else {
        // Reset timer if temperature falls
        tempHighActive = false;
        tempHighStartTime = 0;
    }
    return 0;
}
```

---

#### 🔹 **Scenario 2 — Load Staging**

```java
int handleLoadStaging(double load)
{
    double[] thresholds = {1.3, 2.6, 3.9, 5.2, 6.5, 7.8, 9.1, 10.4};
    int chillersRequired = 1;
    for (int i = thresholds.length - 1; i >= 0; i--) {
        if (load > thresholds[i]) {
            chillersRequired = i + 2;
            break;
        }
    }
    return chillersRequired;
}
```

---

#### 🔹 **Scenario 3 — BladeRoom Demand**

```java
int handleBladeRoomDemand()
{
    int bladeRoomsDemanding = 0;
    if (((BStatusBoolean) getComponent().get("bladeRoom1Demand")).getValue()) bladeRoomsDemanding++;
    if (((BStatusBoolean) getComponent().get("bladeRoom2Demand")).getValue()) bladeRoomsDemanding++;
    if (((BStatusBoolean) getComponent().get("bladeRoom3Demand")).getValue()) bladeRoomsDemanding++;

    return bladeRoomsDemanding;
}
```

---

### 🏗️ **Putting It Together in `onExecute()`**

---

### 🚀 **Full Updated Java Code**

```java
Clock.Ticket ticket;
long lastMainLogicRun = 0;
int dutyScheduleIndex = 0;

// Temperature staging timer variables
long tempHighStartTime = 0;
boolean tempHighActive = false;

static final int[][] DUTY_ROTATIONS = {
  {0, 1, 2, 3, 4, 5, 6, 7},  // Rotation 1
  {1, 2, 3, 4, 5, 6, 7, 0},  // Rotation 2
  {2, 3, 4, 5, 6, 7, 0, 1},  // Rotation 3
  {3, 4, 5, 6, 7, 0, 1, 2},  // Rotation 4
  {4, 5, 6, 7, 0, 1, 2, 3},  // Rotation 5
  {5, 6, 7, 0, 1, 2, 3, 4},  // Rotation 6
  {6, 7, 0, 1, 2, 3, 4, 5},  // Rotation 7
  {7, 0, 1, 2, 3, 4, 5, 6},  // Rotation 8
  {0, 1, 2, 3, 4, 5, 6, 7}   // Rotation 9 (reset to 1)
};

public void onStart() throws Exception
{
  // Set safe and reasonable defaults for Metric units (°C and MW)
  ((BStatusNumeric) getComponent().get("waterTemp")).setValue(12.0); // °C
  ((BStatusNumeric) getComponent().get("tempSetpoint")).setValue(18.0); // °C
  ((BStatusNumeric) getComponent().get("loadMW")).setValue(0.0); // MW
  ((BStatusNumeric) getComponent().get("updateIntervalSeconds")).setValue(300.0); // seconds (5 minutes)

  ((BStatusBoolean) getComponent().get("systemEnable")).setValue(false); // Default off
  ((BStatusBoolean) getComponent().get("rotateNow")).setValue(false); // Default no rotation

  ((BStatusBoolean) getComponent().get("bladeRoom1Demand")).setValue(false);
  ((BStatusBoolean) getComponent().get("bladeRoom2Demand")).setValue(false);
  ((BStatusBoolean) getComponent().get("bladeRoom3Demand")).setValue(false);

  // Default all chillers available
  ((BStatusBoolean) getComponent().get("chiller1Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller2Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller3Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller4Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller5Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller6Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller7Available")).setValue(true);
  ((BStatusBoolean) getComponent().get("chiller8Available")).setValue(true);

  lastMainLogicRun = System.currentTimeMillis();
  updateTimer();
}

public void onExecute() throws Exception
{
  updateTimer();

  long now = System.currentTimeMillis();
  if (getComponent() == null) return;

  // Always check rotateNow first (every 10s)
  boolean rotateRequest = ((BStatusBoolean) getComponent().get("rotateNow")).getValue();
  if (rotateRequest) {
    rotateDuty();
    ((BStatusBoolean) getComponent().get("rotateNow")).setValue(false);  // Auto-reset after rotation
  }

  // NULL check for all inputs (every 10s)
  String[] inputs = {
    "waterTemp", "tempSetpoint", "loadMW", 
    "systemEnable", "rotateNow",
    "bladeRoom1Demand", "bladeRoom2Demand", "bladeRoom3Demand",
    "chiller1Available", "chiller2Available", "chiller3Available", "chiller4Available",
    "chiller5Available", "chiller6Available", "chiller7Available", "chiller8Available"
  };

  for (String inputName : inputs) {
    if (getComponent().getLinks(getComponent().getSlot(inputName)).length == 0) {
      if (getComponent().get(inputName) instanceof BStatusNumeric) {
        ((BStatusNumeric) getComponent().get(inputName)).setValue(0);
        ((BStatusNumeric) getComponent().get(inputName)).setStatus(BStatus.NULL);
      } else if (getComponent().get(inputName) instanceof BStatusBoolean) {
        ((BStatusBoolean) getComponent().get(inputName)).setValue(false);
        ((BStatusBoolean) getComponent().get(inputName)).setStatus(BStatus.NULL);
      }
    }
  }

  // Main logic: only every updateIntervalSeconds (default 300s)
  double intervalSec = ((BStatusNumeric) getComponent().get("updateIntervalSeconds")).getValue();
  if ((now - lastMainLogicRun) / 1000 < intervalSec) return;
  lastMainLogicRun = now;

  // Proceed with logic only if system is enabled
  boolean systemEnable = ((BStatusBoolean) getComponent().get("systemEnable")).getValue();
  if (!systemEnable) {
    disableAllChillers();
    return;
  }

  double waterTemp = ((BStatusNumeric) getComponent().get("waterTemp")).getValue();
  double tempSet = ((BStatusNumeric) getComponent().get("tempSetpoint")).getValue();
  double load = ((BStatusNumeric) getComponent().get("loadMW")).getValue();

  int chillersByTemp = handleTemperatureStaging(waterTemp, tempSet);
  int chillersByLoad = handleLoadStaging(load);
  int chillersByBladeRooms = handleBladeRoomDemand();

  int requiredChillers = Math.max(chillersByTemp, chillersByLoad) + chillersByBladeRooms;

  boolean[] chillerAvailable = {
    ((BStatusBoolean) getComponent().get("chiller1Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller2Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller3Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller4Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller5Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller6Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller7Available")).getValue(),
    ((BStatusBoolean) getComponent().get("chiller8Available")).getValue()
  };

  // Enable chillers based on availability and duty rotation
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

  ((BStatusBoolean) getComponent().get("chiller1Enable")).setValue(chillerEnable[0]);
  ((BStatusBoolean) getComponent().get("chiller2Enable")).setValue(chillerEnable[1]);
  ((BStatusBoolean) getComponent().get("chiller3Enable")).setValue(chillerEnable[2]);
  ((BStatusBoolean) getComponent().get("chiller4Enable")).setValue(chillerEnable[3]);
  ((BStatusBoolean) getComponent().get("chiller5Enable")).setValue(chillerEnable[4]);
  ((BStatusBoolean) getComponent().get("chiller6Enable")).setValue(chillerEnable[5]);
  ((BStatusBoolean) getComponent().get("chiller7Enable")).setValue(chillerEnable[6]);
  ((BStatusBoolean) getComponent().get("chiller8Enable")).setValue(chillerEnable[7]);

  ((BStatusNumeric) getComponent().get("currentSequence")).setValue(dutyScheduleIndex + 1);  // Show 1 to 9
}

public void onStop() throws Exception
{
  if (ticket != null) ticket.cancel();
}

void updateTimer()
{
  if (ticket != null) ticket.cancel();
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

void disableAllChillers()
{
  for (int i = 1; i <= 8; i++) {
    ((BStatusBoolean) getComponent().get("chiller" + i + "Enable")).setValue(false);
  }
}

void rotateDuty()
{
  dutyScheduleIndex++;
  if (dutyScheduleIndex >= DUTY_ROTATIONS.length) {
    dutyScheduleIndex = 0;
  }
}

// ------------------- SCENARIO 1 — Temperature Staging -------------------
int handleTemperatureStaging(double waterTemp, double tempSet)
{
  if (waterTemp >= tempSet + 2.0) {
    return 8; // Immediate max chillers
  } else if (waterTemp >= tempSet + 1.0) {
    if (!tempHighActive) {
      tempHighActive = true;
      tempHighStartTime = System.currentTimeMillis();
    } else {
      long elapsed = (System.currentTimeMillis() - tempHighStartTime) / 1000;
      if (elapsed >= 600) {
        return 1; // After 10 min, stage one more chiller
      }
    }
  } else {
    tempHighActive = false;
    tempHighStartTime = 0;
  }
  return 0;
}

// ------------------- SCENARIO 2 — Load Staging -------------------
int handleLoadStaging(double load)
{
  double[] thresholds = {1.3, 2.6, 3.9, 5.2, 6.5, 7.8, 9.1, 10.4};
  int chillersRequired = 1;
  for (int i = thresholds.length - 1; i >= 0; i--) {
    if (load > thresholds[i]) {
      chillersRequired = i + 2;
      break;
    }
  }
  return chillersRequired;
}

// ------------------- SCENARIO 3 — BladeRoom Demand -------------------
int handleBladeRoomDemand()
{
  int bladeRoomsDemanding = 0;
  if (((BStatusBoolean) getComponent().get("bladeRoom1Demand")).getValue()) bladeRoomsDemanding++;
  if (((BStatusBoolean) getComponent().get("bladeRoom2Demand")).getValue()) bladeRoomsDemanding++;
  if (((BStatusBoolean) getComponent().get("bladeRoom3Demand")).getValue()) bladeRoomsDemanding++;
  return bladeRoomsDemanding;
}
```



---

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