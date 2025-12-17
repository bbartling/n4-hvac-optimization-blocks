# Non‑GL36 & Advanced Logic

This sub‑guide contains simplified resets and advanced logic that are **not** part of ASHRAE Guideline 36.  Here you will find alternative AHU resets, chiller plant chilled‑water temperature reset and the advanced per‑chiller duty‑cycle rotator.  All content is retained exactly from the original README.

---

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




