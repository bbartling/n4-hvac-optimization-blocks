# Tutorials & Algorithms

This sub‑guide contains all of the tutorial content and general algorithm blocks from the main repository.  Each section below is preserved exactly as originally published so you can follow along step‑by‑step or copy/paste code into your own Niagara ProgramObjects without modification.

<!-- The following sections are collapsed using `<details>` tags for readability.  Click a summary to expand the full description and code. -->

<details>
<summary>🧮 Simple Adder Block (Getting Started Tutorial)</summary>

This program block is a simple **Adder** example designed to help you get comfortable coding your first Niagara **Program Object** blocks in Java. It sums up to 4 numeric inputs (`in1`, `in2`, `in3`, `in4`) and outputs the result.

It also counts how many inputs are *actually wired* and writes the number to a `wiredInCount` slot for debugging or diagnostics.

While this could easily be done with basic Niagara Wire Sheet logic, it’s a perfect first step to move into **Java coding** for Niagara!

---

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/adderBlockSnip.png" alt="Simple Adder Block Snip" width="500">
</p>

---

### ⚙️ **Inputs**

| Input          | Description                                       | Units                            |
| -------------- | ------------------------------------------------- | -------------------------------- |
| `in1`          | First number to add                               | Numeric (real number)            |
| `in2`          | Second number to add                              | Numeric                          |
| `in3`          | Third number to add                               | Numeric                          |
| `in4`          | Fourth number to add                              | Numeric                          |
| `wiredInCount` | *Status output* showing how many inputs are wired | String (e.g., `Wired Inputs: 3`) |

---

### **Calculation**

1. **Sum the Inputs:**

```
sum = in1 + in2 + in3 + in4
```

2. **Count Wired Inputs:**

It uses `getComponent().getLinks(getComponent().getSlot("inX")).length` to count if something is wired to each input. If not wired, the input is cleared to `NULL`.

---

### **Output**

| Output         | Description                      | Units        |
| -------------- | -------------------------------- | ------------ |
| `out`          | The sum of all wired inputs      | Numeric      |
| `wiredInCount` | Number of inputs currently wired | StatusString |

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
Clock.Ticket ticket;  

long lastOnExecuteTicks;

public void onStart() throws Exception {
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer(); 

    double sum = 0;
    int wiredCount = 0;

    if (getInitOnDelink()) {
        if (getComponent().getLinks(getComponent().getSlot("in1")).length == 0) { 
            getIn1().setValue(0);
            getIn1().setStatus(BStatus.NULL);
        } else {
            wiredCount++;
        }

        if (getComponent().getLinks(getComponent().getSlot("in2")).length == 0) { 
            getIn2().setValue(0);
            getIn2().setStatus(BStatus.NULL);
        } else {
            wiredCount++;
        }

        if (getComponent().getLinks(getComponent().getSlot("in3")).length == 0) { 
            getIn3().setValue(0);
            getIn3().setStatus(BStatus.NULL);
        } else {
            wiredCount++;
        }

        if (getComponent().getLinks(getComponent().getSlot("in4")).length == 0) { 
            getIn4().setValue(0);
            getIn4().setStatus(BStatus.NULL);
        } else {
            wiredCount++;
        }
    }  

    sum = getIn1().getValue() + getIn2().getValue() + getIn3().getValue() + getIn4().getValue();
    
    getOut().setValue(sum);

    getWiredInCount().setValue("Wired Inputs: " + wiredCount);
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

void updateTimer() {            
    if (ticket != null) {
        ticket.cancel();
    }  
    
    ticket = Clock.schedule(getComponent(), getExecutePeriod(), BProgram.execute, null);
}
```

---

#### **Developer Notes**

* `wiredInCount` can help in debug mode to show if anything is connected.
* If a point is **not wired**, it is forcefully set to `NULL` to avoid invalid sums.
* A great **starter block** before moving into more advanced HVAC control logic like Trim & Respond or Chiller Sequencing!

</details>



<details>
<summary>📘 Min Max Avg Rolling Block (Another easier Getting Started Tutorial)</summary>

This program block provides a **rolling statistical analysis** of up to four numeric inputs. It differs from the standard `kitControl` Min/Max/Average block in that it samples input data every 10 seconds and stores these samples in memory. After the defined `updateIntervalSeconds` elapses, the block calculates the minimum, maximum, and average values based on the collected samples.

Additionally, it computes a rolling average over a user-defined window of time specified by `rollingAvgMinutes`. This rolling average is calculated over the most recent samples, providing a smoothed view of the input trends.

In contrast, the `kitControl` Min/Max/Average block performs calculations using only the instantaneous input values with a slot sheet setting ✅ execute on change, without maintaining any history of past samples. As a result, this block offers a more robust and stable analysis of input trends by filtering out short-term fluctuations and providing both interval-based and rolling statistical summaries.


* **Minimum**, **Maximum**, and **Average** values over a user-configurable interval.
* **Rolling Average** over a longer trailing window for smoother trend analysis.

Unlike simpler examples, this block keeps separate data buffers for:

* Interval-based calculations (`updateIntervalSeconds`)
* Long-term rolling average (`rollingAvgMinutes`)

This dual-buffer approach gives you real-time interval statistics *and* a trailing smoothed average for better control decisions!

---

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/MinMaxAveRollingSnip.png" alt="Min Max Avg Rolling Block Snip" width="600">
</p>

---

### ⚙️ **Inputs**

| Input                   | Description                                   | Units                       |
| ----------------------- | --------------------------------------------- | --------------------------- |
| `in1`                   | First numeric input                           | Numeric                     |
| `in2`                   | Second numeric input                          | Numeric                     |
| `in3`                   | Third numeric input                           | Numeric                     |
| `in4`                   | Fourth numeric input                          | Numeric                     |
| `updateIntervalSeconds` | Interval in seconds to compute Min/Max/Avg    | Seconds (30-3600, writable) |
| `rollingAvgMinutes`     | Rolling window in minutes for Rolling Average | Minutes (1-60, writable)    |

---

### ⚙️ **Outputs**

| Output          | Description                             | Units   |
| --------------- | --------------------------------------- | ------- |
| `outMin`        | Minimum value over the interval         | Numeric |
| `outMax`        | Maximum value over the interval         | Numeric |
| `outAvg`        | Average value over the interval         | Numeric |
| `rollingAvgOut` | Rolling average over the past X minutes | Numeric |

---

### **Algorithm Overview**

* Every **10 seconds** (`executePeriod`), the block:

  * Samples all wired inputs.
  * Calculates the current tick’s `min`, `max`, and `avg`.
  * Stores these samples in two buffers:

    * `intervalBuffer` — used for Min/Max/Avg every `updateIntervalSeconds`.
    * `rollingBuffer` — stores trailing samples for `rollingAvgMinutes`.

* Every `updateIntervalSeconds`:

  * **Interval Buffer** is processed:

    * Min of the min samples
    * Max of the max samples
    * Average of the average samples
  * Buffers are cleared for the next interval.

* **Rolling Average**:

  * Calculated by averaging the last *N* samples in the `rollingBuffer`, where *N* is based on `rollingAvgMinutes`.
  * `rollingBuffer` prunes itself to ~60 minutes of data to ensure memory safety.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
Clock.Ticket ticket;
long lastInternalTickTime;
ArrayList<Double> intervalMinBuffer;
ArrayList<Double> intervalMaxBuffer;
ArrayList<Double> intervalAvgBuffer;
ArrayList<Double> rollingAvgBuffer;

public void onStart() throws Exception {
    intervalMinBuffer = new ArrayList<>();
    intervalMaxBuffer = new ArrayList<>();
    intervalAvgBuffer = new ArrayList<>();
    rollingAvgBuffer = new ArrayList<>();
    lastInternalTickTime = System.currentTimeMillis();
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();
    // (Omitted for brevity: NULL checks and sampling logic)
    
    if (!currentValues.isEmpty()) {
        double currentMin = Collections.min(currentValues);
        double currentMax = Collections.max(currentValues);
        double currentAvg = currentValues.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

        intervalMinBuffer.add(currentMin);
        intervalMaxBuffer.add(currentMax);
        intervalAvgBuffer.add(currentAvg);
        rollingAvgBuffer.add(currentAvg);

        // Prune rolling buffer to last 60 min of samples
        int samplesPerMinute = (int)(60.0 / getExecutePeriod().getSeconds());
        int maxRollingSamples = 60 * samplesPerMinute;
        if (rollingAvgBuffer.size() > maxRollingSamples) {
            rollingAvgBuffer = new ArrayList<>(rollingAvgBuffer.subList(rollingAvgBuffer.size() - maxRollingSamples, rollingAvgBuffer.size()));
        }
    }

    long now = System.currentTimeMillis();
    int updateIntervalSec = 300; // Default 5 minutes

    if (getUpdateIntervalSeconds().getStatus().isOk()) {
        updateIntervalSec = (int) Math.max(30, Math.min(getUpdateIntervalSeconds().getValue(), 3600));
    }

    if ((now - lastInternalTickTime) / 1000 >= updateIntervalSec) {
        // Calculate Min, Max, Avg over interval
        double minVal = Collections.min(intervalMinBuffer);
        double maxVal = Collections.max(intervalMaxBuffer);
        double avgVal = intervalAvgBuffer.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

        getOutMin().setValue(minVal);
        getOutMax().setValue(maxVal);
        getOutAvg().setValue(avgVal);

        // Rolling Avg Calculation
        if (!rollingAvgBuffer.isEmpty()) {
            int rollingMinutes = 5; // Default
            if (getRollingAvgMinutes().getStatus().isOk()) {
                rollingMinutes = (int) Math.max(1, Math.min(getRollingAvgMinutes().getValue(), 60));
            }

            int samplesPerMinute = (int)(60.0 / getExecutePeriod().getSeconds());
            int rollingSampleCount = rollingMinutes * samplesPerMinute;

            int startIdx = Math.max(0, rollingAvgBuffer.size() - rollingSampleCount);
            List<Double> rollingWindow = rollingAvgBuffer.subList(startIdx, rollingAvgBuffer.size());
            double rollingAvg = rollingWindow.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);

            getRollingAvgOut().setValue(rollingAvg);
        }

        // Clear interval buffer only
        intervalMinBuffer.clear();
        intervalMaxBuffer.clear();
        intervalAvgBuffer.clear();
        lastInternalTickTime = now;
    }
}

public void onStop() throws Exception {
    if (ticket != null) ticket.cancel();
}

void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), getExecutePeriod(), BProgram.execute, null);
}
```

---

#### **Developer Notes**

* Separate buffers avoid polluting rolling average data with interval resets.
* Rolling average is clamped to 1–60 minutes.
* `updateIntervalSeconds` clamps between 30 and 3600 seconds.
* Buffers are pruned to protect memory footprint.

</details>



<details>
<summary>⚡️ Execute on Change (Trigger-Based Logic)</summary>

This program block demonstrates how to use the **Execute on Change** flag to create highly efficient, trigger-based logic. Instead of using an internal `Clock.schedule()` timer that runs constantly, the program's `onExecute()` method will only run when the `updateNow` boolean slot changes value (e.g., from false to true).

This is the most resource-friendly way to handle actions that only need to happen in response to a specific event.

---

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/executeOnChangeSnip.png" alt="Execute on Change Wiresheet" width="600">
</p>

---

### ⚙️ **Key Configuration**

The magic happens in the **Slot Sheet**. For the `updateNow` boolean slot, you must open the **Config Flags** and check the **Execute On Change** box. This tells Niagara to execute the program component whenever this specific slot's value is written to.

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/executeOnChangeCheckSip.png" alt="Execute on Change Flag" width="600">
</p>

---

### **Inputs & Outputs**

| Slot Name | Description | Type | Writable |
| --- | --- | --- | --- |
| `updateNow` | A boolean that triggers the calculation. | BStatusBoolean | Yes |
| `inputA` | The first number to add. | BStatusNumeric | Yes |
| `inputB` | The second number to add. | BStatusNumeric | Yes |
| `sum` | The calculated sum of `inputA` and `inputB`. | BStatusNumeric | No |

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor. Notice the absence of any timer logic. The `onExecute()` is lean and only runs when needed.

```java
public void onStart() throws Exception
{
  // Nothing needed here for trigger-based logic
}

public void onExecute() throws Exception
{
  // Only run the logic if the updateNow trigger is true
  if (getUpdateNow().getValue()) {
    double a = getInputA().getValue();
    double b = getInputB().getValue();
    double result = a + b;

    // Set the output value
    setSum(new BStatusNumeric(result));

    // IMPORTANT: Reset the trigger back to false
    // This makes it ready for the next trigger event.
    setUpdateNow(new BStatusBoolean(false));
  }
}

public void onStop() throws Exception
{
  // Nothing needed here
}
```

---

#### **Developer Notes**

  * **Efficiency:** This method is far more efficient than a timed loop if your logic only needs to run occasionally. It consumes zero CPU resources while idle.
  * **Resetting the Trigger:** It is critical to set the trigger (`updateNow`) back to `false` within the `onExecute()` method. If you don't, it won't be able to trigger again on the next false-to-true change.

</details>



<details>
<summary>🏗️ Top 5 of 15 Algorithm</summary>

This logic block continuously ranks up to **15 numeric inputs**, filters out any **`NULL` or unwired sources**, and publishes the **top 5 highest values** after an optional drop count (e.g., ignore the top N).  

Every execution cycle (running automatically **once per second**) performs the following:
- Checks each input wire for a valid `OK` status — if a point is `NULL` or not linked, it’s safely ignored.  
- Sorts all valid inputs in descending order.  
- Drops the specified number of top values (`dropCount`) and reports the **next highest as `filteredMax`**.  
- Updates `rank1 → rank5` and `usedCount` for downstream logic.  
- Clears any outputs when all inputs are `NULL` or invalid.  

This ensures the block continuously adapts to real-time input changes, self-heals when points drop offline, and never outputs stale or invalid data.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/top5Of15Snip.png" width="700">
</p>

---

### Slots

| Slot Name | Description                         | Type           | Writable |
|-----------|-------------------------------------|----------------|----------|
| in1..in15 | Up to 15 numeric sources to rank    | BStatusNumeric | Yes      |
| dropCount | Number of top values to ignore (N)  | BStatusNumeric | Yes      |

**Outputs**

| Slot Name    | Description                                                             | Type           |
|--------------|-------------------------------------------------------------------------|----------------|
| filteredMax  | Highest value **after** dropping the top `dropCount` items              | BStatusNumeric |
| rank1        | 1st highest from the filtered list                                      | BStatusNumeric |
| rank2        | 2nd highest from the filtered list                                      | BStatusNumeric |
| rank3        | 3rd highest from the filtered list                                      | BStatusNumeric |
| rank4        | 4th highest from the filtered list                                      | BStatusNumeric |
| rank5        | 5th highest from the filtered list                                      | BStatusNumeric |
| usedCount    | Count of inputs used after dropping (and after ignoring any NULL/unwired) | BStatusNumeric |
| statusTrace  | Debug string with inputs, dropCount, used, filteredMax, and ranks       | BStatusString  |


---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/* ===== Simple Top-N with dynamic dropCount and wire-checking ===== */
Clock.Ticket ticket;

void scheduleNext() {
  if (ticket != null) ticket.cancel();
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(2), BProgram.execute, null);
}

void setNull(BStatusNumeric n){ if (n != null) n.setStatus(BStatus.NULL); }

void setOk(BStatusNumeric n, double v){
  if (n == null) return;
  n.setValue(v);
  n.setStatus(BStatus.ok); // Corrected
}

/**
 * NEW HELPER: Checks if a slot has an incoming link. If not, sets it to NULL.
 * This pattern is based on the README.md examples.
 */
void checkWireStatus(String slotName, BStatusNumeric point) {
    try {
        if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
            point.setValue(0);
            point.setStatus(BStatus.NULL);
        }
    } catch (Exception e) { /* ignore error if slot not found */ }
}

/* convenience getters (existing slots) */
BStatusNumeric in(int i){ return (BStatusNumeric)get("in"+i); }
BStatusNumeric rank(int i){ return (BStatusNumeric)get("rank"+i); }
BStatusNumeric filtered(){ return (BStatusNumeric)get("filteredMax"); }
BStatusNumeric used(){ return (BStatusNumeric)get("usedCount"); }
BStatusNumeric drop(){ return (BStatusNumeric)get("dropCount"); } 
BStatusString trace(){
  try { return (BStatusString)get("statusTrace"); } catch (Exception e){ return null; }
}

/* ===== Lifecycle ===== */
public void onStart() throws Exception {
  // clear outputs on boot
  setNull(filtered());
  for (int i=1;i<=5;i++) setNull(rank(i));
  if (used()!=null) used().setValue(0);
  if (trace()!=null) trace().setValue("Top5 (dropCount) started.");
  scheduleNext();
}

public void onExecute() throws Exception {
  scheduleNext();

  // ### NEW SECTION: Check for disconnected wires ###
  // This loop will set any unwired 'in' slot to NULL
  for (int i=1; i<=15; i++) {
    checkWireStatus("in" + i, in(i));
  }
  // ### END NEW SECTION ###


  // 1) collect OK inputs
  java.util.ArrayList<Double> vals = new java.util.ArrayList<Double>(15);
  for (int i=1;i<=15;i++){
    BStatusNumeric s = in(i);
    // This logic now correctly skips slots that were just set to NULL
    if (s != null && s.getStatus().isOk()) {
        vals.add(s.getValue());
    }
  }
  int originalInputCount = vals.size(); // Store for trace

  if (vals.isEmpty()){
    setNull(filtered());
    for (int i=1;i<=5;i++) setNull(rank(i));
    if (used()!=null) used().setValue(0);
    if (trace()!=null) trace().setValue("No valid inputs; outputs NULL.");
    return;
  }

  // 2) sort descending (highest first)
  java.util.Collections.sort(vals, java.util.Collections.reverseOrder());

  // 3) drop the top N based on the slot value
  int dropN = 0;
  try {
    BStatusNumeric dropSlot = drop();
    if (dropSlot != null && dropSlot.getStatus().isOk()){
      dropN = (int)Math.max(0, Math.round(dropSlot.getValue()));
    }
  } catch (Exception e) {
    if (trace()!=null) trace().setValue("ERROR: 'dropCount' slot missing or invalid.");
    return; 
  }
  
  int actualDropCount = Math.min(dropN, vals.size());

  // remove first 'actualDropCount' items
  for (int i=0; i < actualDropCount && !vals.isEmpty(); i++) {
    vals.remove(0);
  }

  // 4) nothing left after drop?
  if (vals.isEmpty()){
    setNull(filtered());
    for (int i=1;i<=5;i++) setNull(rank(i));
    if (used()!=null) used().setValue(0);
    if (trace()!=null) trace().setValue("dropCount(" + actualDropCount + ") removed all " + originalInputCount + " values; outputs NULL.");
    return;
  }

  // 5) write filteredMax (force OK)
  setOk(filtered(), vals.get(0));

  // 6) ranks (Top 5 from remaining list)
  for (int i=1;i<=5;i++){
    if (i-1 < vals.size()) setOk(rank(i), vals.get(i-1));
    else setNull(rank(i));
  }

  // 7) usedCount + statusTrace
  if (used()!=null) used().setValue(vals.size());
  if (trace()!=null){
    int show = Math.min(5, vals.size());
    double[] preview = new double[show];
    for (int i=0;i<show;i++) preview[i] = vals.get(i);
    
    trace().setValue(
      "inputs=" + originalInputCount
      + ", dropCount=" + actualDropCount
      + ", used=" + vals.size()
      + ", filteredMax=" + vals.get(0)
      + ", ranks=" + java.util.Arrays.toString(preview)
    );
  }
}

public void onStop() throws Exception {
  if (ticket != null) ticket.cancel();
}
```

</details>



<details>
<summary>🏓 Ping-Pong Algorithm</summary>

This block generates a **continuous oscillation** between a defined **lower** and **upper limit**, stepping at each update interval.  

Every cycle (executed automatically **once per second**) performs:
- A boundary check to ensure values never exceed the defined limits.  
- A direction reversal (“ping-pong”) once the limit is reached.  
- A delayed start using `StartupDelaySeconds` before normal operation.  
- Smooth ramping defined by the adjustable `Step` size and `UpdateIntervalSeconds`.  
- Continuous enable control — when disabled, the value holds steady.  

This simple, robust pattern is perfect for **testing analog control loops**, **simulated demand profiles**, or **exercise routines** in a BAS environment.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/pingPongAlgorithmSnip.png" width="700">
</p>

---

### Slots

| Slot Name             | Description                                        | Type             | Writable |
|-----------------------|----------------------------------------------------|------------------|----------|
| Enable                | Enable/disable oscillation                         | BStatusBoolean   | Yes      |
| InitialValue          | Starting value before ramping                      | BStatusNumeric   | Yes      |
| LowerLimit            | Minimum bound of the oscillation                   | BStatusNumeric   | Yes      |
| UpperLimit            | Maximum bound of the oscillation                   | BStatusNumeric   | Yes      |
| StartupDelaySeconds   | Delay before the first update                      | BStatusNumeric   | Yes      |
| Step                  | Increment/decrement applied each update            | BStatusNumeric   | Yes      |
| UpdateIntervalSeconds | Update period (s); internal timer uses this value  | BStatusNumeric   | Yes      |

**Outputs**

| Slot Name    | Description                                  | Type           |
|--------------|----------------------------------------------|----------------|
| OutputValue  | Current value after ping-pong update          | BStatusNumeric |


---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/*
 * ================================================================
 * Ping Pong Algorithm for Niagara 4 ProgramObject
 *
 * This algorithm generates a "ping pong" (triangle wave) signal.
 * When Enabled, it waits for a startup delay, then counts from
 * InitialValue up to UpperLimit, then down to LowerLimit,
 * and repeats.
 * ================================================================
 */

// ========= Class-level state variables =========

// Manages the internal timer
Clock.Ticket ticket;

// Tracks the current counting direction
// true = counting up, false = counting down
boolean isIncreasing = true;

// Stores the end time for the startup delay
long startupDelayEndTime = 0;

// Flag to track if the startup delay has completed
boolean isDelayOver = false;

// ========= Lifecycle Methods (onStart, onExecute, onStop) =========

public void onStart() throws Exception
{
  // When the program starts, reset to the initial state
  resetToInitial();
  
  // Start the timer
  updateTimer();
}

public void onExecute() throws Exception
{
  // Always reschedule the timer for the next execution
  updateTimer();

  // --- 1. Check if Enabled ---
  // If the 'Enable' slot is not OK or is false,
  // reset to the initial value and stop further execution.
  if (!getEnable().getStatus().isOk() || !getEnable().getValue())
  {
    resetToInitial();
    return;
  }

  // --- 2. Handle Startup Delay ---
  // This logic only runs if the block is Enabled.
  if (!isDelayOver)
  {
    // If this is the first time running since being enabled,
    // calculate the end time for the delay.
    if (startupDelayEndTime == 0)
    {
      double delaySec = 1.0; // Default 1 second
      if (getStartupDelaySeconds().getStatus().isOk())
      {
        delaySec = getStartupDelaySeconds().getValue();
      }
      startupDelayEndTime = System.currentTimeMillis() + (long)(delaySec * 1000);
    }

    // If we are still within the delay period, do nothing.
    // Just hold the initial value and wait.
    if (System.currentTimeMillis() < startupDelayEndTime)
    {
      return;
    }
    
    // The delay period is over.
    isDelayOver = true;
  }

  // --- 3. Get Parameters with Safe Defaults ---
  // Read the current value from our output slot
  double currentValue = getOutputValue().getValue();
  
  // Read parameters, providing defaults if slots are unwired
  double step = 1.0;
  if (getStep().getStatus().isOk())
  {
    step = getStep().getValue();
  }

  double lower = 0.0;
  if (getLowerLimit().getStatus().isOk())
  {
    lower = getLowerLimit().getValue();
  }

  double upper = 100.0;
  if (getUpperLimit().getStatus().isOk())
  {
    upper = getUpperLimit().getValue();
  }
  
  // Ensure upper is always greater than lower
  if (upper < lower)
  {
      double temp = upper;
      upper = lower;
      lower = temp;
  }


  // --- 4. Core Ping Pong Logic ---
  if (isIncreasing)
  {
    // We are counting up
    currentValue += step;
    
    // Check if we've hit or passed the upper limit
    if (currentValue >= upper)
    {
      currentValue = upper; // Clamp to the limit
      isIncreasing = false; // Change direction
    }
  }
  else
  {
    // We are counting down
    currentValue -= step;
    
    // Check if we've hit or passed the lower limit
    if (currentValue <= lower)
    {
      currentValue = lower; // Clamp to the limit
      isIncreasing = true; // Change direction
    }
  }

  // --- 5. Set the Output ---
  getOutputValue().setValue(currentValue);
}

public void onStop() throws Exception
{
  // When the program stops, cancel the timer
  if (ticket != null)
  {
    ticket.cancel();
  }
}

// ========= Helper Methods =========

/**
 * Resets the algorithm to its initial state.
 * Sets the output to the InitialValue and resets state flags.
 */
void resetToInitial()
{
  double initialVal = 0.0;
  if (getInitialValue().getStatus().isOk())
  {
    initialVal = getInitialValue().getValue();
  }

  // Set the output and internal value
  getOutputValue().setValue(initialVal);
  
  // Reset state flags
  isIncreasing = true;
  isDelayOver = false;
  startupDelayEndTime = 0;
}

/**
 * Cancels any existing timer and schedules the next execution
 * based on the 'UpdateIntervalSeconds' slot.
 */
void updateTimer()
{
  if (ticket != null)
  {
    ticket.cancel();
  }

  double intervalSec = 1.0; // Default 1 second
  if (getUpdateIntervalSeconds().getStatus().isOk())
  {
    intervalSec = getUpdateIntervalSeconds().getValue();
  }

  // Safety clamp to prevent program from running too fast
  intervalSec = Math.max(0.2, intervalSec); 
  
  // --- THE FIX ---
  // We must convert the 'intervalSec' double to milliseconds (long)
  // for the Clock.schedule() method.
  long intervalMillis = (long)(intervalSec * 1000);
  
  ticket = Clock.schedule(getComponent(), BRelTime.make(intervalMillis), BProgram.execute, null);
}
```

</details>



<details>
<summary>🔥 kitControl's Tstat but with a True deadband and not a diff or differential</summary>

This ProgramObject is a **simple thermostat** that implements a **true deadband** around a single space temperature setpoint.

> The diff property on Niagara’s kitControl BTstat block isn’t a “deadband” in the strict sense—it’s actually the differential or hysteresis band used to determine when the thermostat changes state.

The kitControl BTstat is basically a single-setpoint, two-sided thermostat that creates a band around sp using diff/2 and then remembers its last output. When cv rises above sp + diff/2 it turns “on”, when it falls below sp - diff/2 it turns “off”, and while cv is inside that band it just holds whatever state it was previously in (and can even mark the output as NULL when “in control”), which is why the deadband feels a bit odd compared to a simple true-deadband that forces both outputs off in the middle.

---

![True Deadband Tstat Snip](https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/tstatSnip.png)

---

### Slot Map (Niagara ProgramObject)

| Slot Name     | Display Name | Type               | Role / Description                          |
|---------------|--------------|--------------------|---------------------------------------------|
| `setpoint`    | setpoint     | `baja:StatusNumeric` | Desired space temperature setpoint          |
| `cv`          | cv           | `baja:StatusNumeric` | Current value (room temperature feedback)   |
| `deadband`    | deadband     | `baja:StatusNumeric` | Total deadband width around setpoint        |
| `coolOut`     | coolOut      | `baja:StatusBoolean` | Command to enable **cooling**               |
| `heatOut`     | heatOut      | `baja:StatusBoolean` | Command to enable **heating**               |
| `statusString`| statusString | `baja:StatusString`  | Human-readable status / debug trace         |

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters.  
> Paste **only** the logic methods (onStart, onExecute, onStop, helpers) into the Program’s **Source** editor.

```java
/*
 * ================================================================
 * True Deadband Thermostat
 * ================================================================
 */

// ========= Class-level state variables =========

Clock.Ticket ticket;
private static final int UPDATE_INTERVAL_SEC = 5;

// ========= Lifecycle Methods (onStart, onExecute, onStop) =========

public void onStart() throws Exception
{
  nullOutputs("Program started. Awaiting inputs.");
  updateTimer();
}

public void onExecute() throws Exception
{
  updateTimer();

  // --- 0. Null-wire checker (like GL36 chiller block) ---
  ensureNumericWiredOrNull("cv",        getCv());
  ensureNumericWiredOrNull("setpoint",  getSetpoint());
  ensureNumericWiredOrNull("deadband",  getDeadband());

  // Grab statuses once AFTER wiring check
  BStatus cvStatus = getCv().getStatus();
  BStatus spStatus = getSetpoint().getStatus();
  BStatus dbStatus = getDeadband().getStatus();

  // If any input is NULL → outputs go NULL + OFF
  if (cvStatus.isNull() || spStatus.isNull() || dbStatus.isNull())
  {
    nullOutputs("One or more inputs are NULL (unwired). Forcing outputs to NULL.");
    return;
  }

  // --- 1. Check Input Status (valid / fault) ---
  boolean cvOk = cvStatus.isOk();
  boolean spOk = spStatus.isOk();
  boolean dbOk = dbStatus.isOk();

  if (!cvOk || !spOk || !dbOk)
  {
    String error = "Input Error: ";
    if (!cvOk) error += "Check 'cv'. ";
    if (!spOk) error += "Check 'setpoint'. ";
    if (!dbOk) error += "Check 'deadband'. ";
    setOutputs(false, false, error);
    return;
  }

  // --- 2. Get Values ---
  double currentCv = getCv().getValue();
  double sp        = getSetpoint().getValue();
  double db        = getDeadband().getValue();

  db = Math.max(0.0, db);

  // --- 3. Calculate Deadband Edges ---
  double coolOn = sp + (db / 2.0);
  double heatOn = sp - (db / 2.0);

  // --- 4. Core Tstat Logic ---
  if (currentCv > coolOn)
  {
    setOutputs(false, true,
        String.format("Cooling (CV: %.1f > SP_Cool: %.1f)", currentCv, coolOn));
  }
  else if (currentCv < heatOn)
  {
    setOutputs(true, false,
        String.format("Heating (CV: %.1f < SP_Heat: %.1f)", currentCv, heatOn));
  }
  else
  {
    setOutputs(false, false,
        String.format("Deadband (SP_Heat: %.1f <= CV: %.1f <= SP_Cool: %.1f)",
                      heatOn, currentCv, coolOn));
  }
}

public void onStop() throws Exception
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }
  nullOutputs("Program stopped.");
}

// ========= Helper Methods =========

void setOutputs(boolean heat, boolean cool, String trace)
{
  getHeatOut().setValue(heat);
  getCoolOut().setValue(cool);

  // When actively controlling, clear NULL and mark OK
  getHeatOut().setStatus(BStatus.ok);
  getCoolOut().setStatus(BStatus.ok);

  getStatusString().setValue(trace);
}

void nullOutputs(String trace)
{
  getHeatOut().setValue(false);
  getCoolOut().setValue(false);

  // Mark outputs as NULL so downstream logic can ignore them
  getHeatOut().setStatus(BStatus.nullStatus);
  getCoolOut().setStatus(BStatus.nullStatus);

  getStatusString().setValue(trace);
}

void updateTimer()
{
  if (ticket != null)
  {
    ticket.cancel();
  }

  ticket = Clock.schedule(
      getComponent(),
      BRelTime.makeSeconds(UPDATE_INTERVAL_SEC),
      BProgram.execute,
      null
  );
}

/**
 * Helper to mimic GL36 chiller-style null-wiring behavior.
 * If the slot has no links, force it to NULL so status.isNull() works.
 */
void ensureNumericWiredOrNull(String slotName, BStatusNumeric point)
{
  try
  {
    if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0)
    {
      point.setValue(0);
      point.setStatus(BStatus.nullStatus); // or BStatus.NULL in your station, if that's what you use
    }
  }
  catch (Exception e)
  {
    // ignore
  }
}

```

</details>


<details>
<summary>⏳ Custom Off Delay Block with Countdown (Trigger-Based Logic)</summary>

This program block implements a flexible **AND-style logic gate** with a **custom off delay**. When *all wired inputs are `true`*, the output immediately becomes `true`. If any input turns `false`, the output stays `true` for a configurable number of seconds before resetting to `NULL`. This is useful for *avoiding short cycling* or *holding ON states* briefly after a logic condition drops out.

Unlike traditional AND logic, this block:

* **Ignores disconnected inputs**
* **Supports countdown-to-null behavior**
* **Includes status trace logs for easy debugging**

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/customOffDelaySnip.png" alt="Custom Off Delay Block Wiresheet" width="800">
</p>

---

### **Use Case: Optimal Start Logic**

In this example, the block is used to hold an `EquipmentRunPoint` active for a fixed delay even after `OptStartTimerRunning` ends or the schedule changes. This prevents flickering or premature shutoff of HVAC systems during transitions.

---

### **Inputs & Outputs**

| Slot Name      | Description                                      | Type             | Writable |
| -------------- | ------------------------------------------------ | ---------------- | -------- |
| `in1`–`in4`    | Logic inputs — only wired ones are evaluated     | `BStatusBoolean` | Yes      |
| `delaySeconds` | Countdown duration after dropout (1–300 seconds) | `BStatusNumeric` | Yes      |
| `output`       | Output of block — `true` or `NULL`               | `BStatusBoolean` | No       |
| `statusTrace`  | Debug string showing logic state                 | `BStatusString`  | No       |

---

### **Logic Flow**

| Condition                     | Output             | Notes                                         |
| ----------------------------- | ------------------ | --------------------------------------------- |
| All *wired* inputs = `true`   | `true` immediately | Cancels any running countdown                 |
| Any input becomes `false`     | Begin countdown    | Holds output `true` for `delaySeconds`        |
| Countdown expires             | `NULL`             | Output is cleared safely using `.setStatus()` |
| All inputs `NULL` (not wired) | `NULL`             | Treated as inactive                           |

---

### **Features**

* ✅ **Safe NULL handling** — uses `.setStatus(BStatus.NULL)`
* ✅ **Automatic wire detection** — `checkWireStatus()` clears unused inputs
* ✅ **Built-in 1s update timer** — doesn't rely on `Execute On Change`
* ✅ **Status trace** — shows `"Countdown active → 5s remaining"` or `"All inputs TRUE → Output = true"`

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
Clock.Ticket ticket;
long delayStartTime = 0;
boolean outputActive = false;
boolean inCountdown = false;


public void onStart() throws Exception {
    getOutput().setStatus(BStatus.NULL);
    getStatusTrace().setValue("AND Delay block started.");
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();

    // Always check for disconnected wires
    checkWireStatus("in1", getIn1());
    checkWireStatus("in2", getIn2());
    checkWireStatus("in3", getIn3());
    checkWireStatus("in4", getIn4());

    // ✅ If countdown is active, do NOT evaluate inputs — wait until timer expires
    if (inCountdown) {
        int delay = getDelayValue();
        long elapsed = (System.currentTimeMillis() - delayStartTime) / 1000;
        int remaining = (int) (delay - elapsed);

        if (remaining < 1) {
            getOutput().setStatus(BStatus.NULL);
            outputActive = false;
            delayStartTime = 0;
            inCountdown = false;
            cancelTimer();
            getStatusTrace().setValue("Delay expired → Output = NULL");
        } else {
            getStatusTrace().setValue("Countdown active → " + remaining + "s remaining");
        }
        return; // ⛔ Do NOT evaluate inputs while counting down
    }

    // Evaluate current input states
    BStatusBoolean[] inputs = { getIn1(), getIn2(), getIn3(), getIn4() };
    boolean allTrue = true;
    int validInputs = 0;

    for (BStatusBoolean input : inputs) {
        if (input.getStatus().isOk()) {
            validInputs++;
            if (!input.getValue()) {
                allTrue = false;
                break;
            }
        }
    }

    // No valid inputs → null output immediately
    if (validInputs == 0) {
        getOutput().setStatus(BStatus.NULL);
        outputActive = false;
        delayStartTime = 0;
        inCountdown = false;
        getStatusTrace().setValue("No inputs wired → Output = NULL");
        return;
    }

    // ✅ If all true and not in countdown → set output TRUE
    if (allTrue) {
        setOutput(new BStatusBoolean(true));
        outputActive = true;
        delayStartTime = 0;
        inCountdown = false;
        cancelTimer();
        getStatusTrace().setValue("All inputs TRUE → Output = true");
    } 
    // ✅ If any input is false and output was active → start countdown
    else if (outputActive) {
        delayStartTime = System.currentTimeMillis();
        inCountdown = true;
        getStatusTrace().setValue("Entering countdown mode...");
    } 
    // If output was not active and inputs not all true → null
    else {
        getOutput().setStatus(BStatus.NULL);
        inCountdown = false;
        getStatusTrace().setValue("Inputs not all TRUE → Output = NULL");
    }
}

public void onStop() throws Exception {
    cancelTimer();
}

void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(1), BProgram.execute, null);
}

// Check wire status, only clears to NULL if no wire is connected
void checkWireStatus(String slotName, BStatusBoolean point) {
    if (getComponent().getLinks(getComponent().getSlot(slotName)).length == 0) {
        point.setValue(false);
        point.setStatus(BStatus.NULL);
    }
}

void cancelTimer() {
    if (ticket != null) {
        ticket.cancel();
        ticket = null;
    }
}

int getDelayValue() {
    int delay = 10;
    if (getDelaySeconds().getStatus().isOk()) {
        delay = (int) Math.max(1, Math.min(300, getDelaySeconds().getValue()));
    }
    return delay;
}

```

---

### **Developer Notes**

* Only count **connected inputs**. Unwired slots are `NULL` and ignored.
* Any logic dropout starts countdown **only if output was active**.
* Designed for control logic where short-term dropouts shouldn't immediately reset the system.

</details>



<details>
<summary>❄️ Cooling Capacity Calculation</summary>

This program block is a simple, practical example for anyone learning how to develop Niagara Program Object blocks. It calculates the Cooling Capacity of a chiller plant based on flow rate, fluid properties, and the measured temperature difference across the system.

While this logic can easily be built using standard Wire Sheet blocks, it's a great starting point for experimenting with AI-assisted Java coding in Niagara. Once you're comfortable with basic examples like this, you can confidently move on to building more advanced control logic — some examples are shown below!

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/unitConverterBlockSnip.png" alt="Cooling Capacity Snip" width="600">
</p>

---

### **Inputs**

| Input                   | Description                         | Metric Units (SI)                               | Imperial Units (IP)                      |
| ----------------------- | ----------------------------------- | ----------------------------------------------- | ---------------------------------------- |
| `flowRate`              | Flow rate of the chilled water      | m³/s (cubic meters per second)                  | GPM (gallons per minute)                 |
| `specificHeat`          | Specific heat capacity of the fluid | J/kg°C (joules per kilogram per degree Celsius) | 500 (BTU/hr·gal·°F) — constant for water |
| `returnTemp`            | Return water temperature            | °C (degrees Celsius)                            | °F (degrees Fahrenheit)                  |
| `supplyTemp`            | Supply water temperature            | °C (degrees Celsius)                            | °F (degrees Fahrenheit)                  |
| `updateIntervalSeconds` | Interval to update calculation      | seconds (s)                                     | seconds (s)                              |

---

### **Calculation**

1. **Temperature Difference (ΔT):**

```
ΔT = returnTemp - supplyTemp
ΔT = 28.0°C - 17.0°C = 11.0°C
```

---

2. **Cooling Capacity Formula:**

The math is burried inside the Java code as `coolingCapacity = (flowRateVal * specificHeatVal * temperatureDiffVal);` see if you can find it below!

**Metric:**

```
Cooling Capacity (W) = flowRate (m³/s) × specificHeat (J/kg°C) × ΔT (°C)
Cooling Capacity = 1.5 × 4184 × 11.0 = 69,036 Watts
Cooling Capacity = 69.036 kW
```

**Imperial:**

```
Cooling Capacity (BTU/hr) = flowRate (GPM) × 500 × ΔT (°F)
Cooling Capacity = 500 × 500 × 11.0 = 2,750,000 BTU/hr
```

---

### 📄 **Example**

**Metric Example:**

```
flowRate = 1.5 m³/s
specificHeat = 4184 J/kg°C
returnTemp = 28.0°C
supplyTemp = 17.0°C

ΔT = 28.0 - 17.0 = 11.0°C

Cooling Capacity = 1.5 × 4184 × 11.0 = 69,036 Watts
= 69.036 kW
```

**Imperial Example:**

```
flowRate = 500 GPM
specificHeat = 500 (BTU/hr·gal·°F)
returnTemp = 55.0°F
supplyTemp = 44.0°F

ΔT = 55.0 - 44.0 = 11.0°F

Cooling Capacity = 500 × 500 × 11.0 = 2,750,000 BTU/hr
```

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
Clock.Ticket ticket;

long lastMainLogicRun = 0;

public void onStart() throws Exception {
    lastMainLogicRun = System.currentTimeMillis();
    updateTimer();
    System.out.println("CoolingCapacityCalculator started. Initial ticks (ms): " + lastMainLogicRun);
}

public void onExecute() throws Exception {
    updateTimer();

    long now = System.currentTimeMillis();
    
    int intervalSec = 10; // Default interval 10 seconds

    BStatusNumeric intervalInput = getExecutePeriod(); // Interval input (seconds)

    if (intervalInput.getStatus().isOk()) {
        double raw = intervalInput.getValue();
        intervalSec = (int) Math.max(5, Math.min(raw, 3600)); // Clamp between 5s and 3600s
    }
    
    if ((now - lastMainLogicRun) / 1000 < intervalSec) {
        System.out.println("Skipping update. Waiting for interval: " + intervalSec + " seconds.");
        return;
    }
    
    lastMainLogicRun = now;
    System.out.println("Updating cooling capacity calculation...");

    double coolingCapacity = 0;

    if (getComponent().getLinks(getComponent().getSlot("flowRate")).length == 0) { 
        getFlowRate().setValue(0);
        getFlowRate().setStatus(BStatus.NULL);
        System.out.println("flowRate input missing. Set to NULL.");
    }

    if (getComponent().getLinks(getComponent().getSlot("specificHeat")).length == 0) { 
        getSpecificHeat().setValue(0);
        getSpecificHeat().setStatus(BStatus.NULL);
        System.out.println("specificHeat input missing. Set to NULL.");
    }

    if (getComponent().getLinks(getComponent().getSlot("temperatureDifference")).length == 0) { 
        getTemperatureDifference().setValue(0);
        getTemperatureDifference().setStatus(BStatus.NULL);
        System.out.println("temperatureDifference input missing. Set to NULL.");
    }

    double flowRateVal = getFlowRate().getValue();
    double specificHeatVal = getSpecificHeat().getValue();
    double temperatureDiffVal = getTemperatureDifference().getValue();

    coolingCapacity = (flowRateVal * specificHeatVal * temperatureDiffVal);

    getCoolingCapacity().setValue(coolingCapacity);

    System.out.println("Calculated coolingCapacity (kW): " + coolingCapacity);
    System.out.println("Values used -> flowRate: " + flowRateVal + ", specificHeat: " + specificHeatVal + ", temperatureDifference: " + temperatureDiffVal);
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
        System.out.println("CoolingCapacityCalculator stopped and timer cancelled.");
    }
}

void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}
```

</details>

<details>
<summary>🕒 Epoch → Niagara Time Converter</summary>

The **Epoch → Niagara Time Converter** translates a Unix epoch timestamp (in milliseconds) into Niagara 4’s `BAbsTime` format. It accepts a numeric `daysOffset` input—positive or negative—to shift the base epoch time before generating multiple formatted outputs, including full timestamp, date-only, and weekday strings. The logic runs on a one-second refresh interval and uses Niagara-specific classes such as `BAbsTime`, `BRelTime`, `Clock`, and `BStatus` to manage timing, slot updates, and null-state handling through `getUnixTime()`, `getDaysOffset()`, `getNiagaraTimeOut()`, and related component accessors.

> Thank you [Andrew McCourt](https://www.linkedin.com/in/andrew-m-309556285/) Field Engineer @ Concord Environmental Prescot, England, United Kingdom for contributing this block.

### Slots

**Inputs & Parameters**

| Slot Name    | Description                                             | Type           | Writable |
|--------------|---------------------------------------------------------|----------------|----------|
| unixTime     | Unix epoch time in **milliseconds** (e.g. from API)     | BStatusNumeric | Yes      |
| daysOffset   | Offset in days to add/subtract from the epoch time      | BStatusNumeric | Yes      |

**Outputs**

| Slot Name        | Description                                                        | Type           |
|------------------|--------------------------------------------------------------------|----------------|
| unixTimeOffset   | Epoch time in ms **after** applying `daysOffset`                   | BStatusNumeric |
| niagaraTimeOut   | Full formatted timestamp (e.g. `dd-MMM-yyyy hh:mm:ss a z`)         | BStatusString  |
| dateOnlyOut      | Date-only string (format auto-adjusted for timezone / region)      | BStatusString  |
| weekdayOut       | Weekday + date formatted string (e.g. `Tuesday, 04 March 2025`)    | BStatusString  |
| statusTrace      | Status/log message for debugging conversion and timezone handling  | BStatusString  |

---

**🕒 Example Inputs & Outputs**

| unixTime (ms)      | daysOffset | niagaraTimeOut (CST)           | dateOnlyOut | weekdayOut                | unixTimeOffset (ms) |
|--------------------|-------------|--------------------------------|--------------|----------------------------|----------------------|
| 1736448000000      | 0.0         | 10-Jan-2025 12:00:00 AM CST    | 01-10-2025   | Friday, 10 January 2025    | 1736448000000        |
| 1736448000000      | -1.0        | 09-Jan-2025 12:00:00 AM CST    | 01-09-2025   | Thursday, 09 January 2025  | 1736361600000        |
| 1736448000000      | +2.0        | 12-Jan-2025 12:00:00 AM CST    | 01-12-2025   | Sunday, 12 January 2025    | 1736620800000        |

This block updates automatically **every second**, performing null-handling checks on each refresh.  
If the input wire is not connected or returns a null value, the outputs are cleared and the status trace reports `"Input not wired or NULL."`.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/unixTimeConvertSnip.png" width="700">
</p>


### 💻 Java Code


```java

Clock.Ticket ticket;


public void onStart() throws Exception {
    getStatusTrace().setValue("Epoch → Niagara time converter started (1 s refresh).");
    updateTimer();
}


public void onExecute() throws Exception {
    updateTimer();
    
    final long MILLIS_PER_DAY = 24L * 60 * 60 * 1000;


    // Check for unwired or NULL primary input slot
    if (!getUnixTime().getStatus().isOk()) {
        getNiagaraTimeOut().setValue("");
        getDateOnlyOut().setValue("");
        getWeekdayOut().setValue("");
        // Ensure new output slot is also cleared
        getUnixTimeOffset().setValue(0.0); 
        getStatusTrace().setValue("Input not wired or NULL.");
        return;
    }


    try {
        // 1. Get the current epoch time from the input slot
        long baseEpochMillis = (long) getUnixTime().getValue();
        
        // 2. Determine the day offset (Read from the new BDouble slot)
        double daysOffset = 0.0;
        if (getDaysOffset().getStatus().isOk()) {
            daysOffset = getDaysOffset().getValue();
        }


        // 3. Calculate the new epoch time with offset
        long offsetMillis = (long) (daysOffset * MILLIS_PER_DAY);
        long epochMillis = baseEpochMillis + offsetMillis; 
        
        // 4. Set the new raw epoch output slot
        // Casting long to double for BDouble slot compatibility.
        getUnixTimeOffset().setValue((double)epochMillis);


        // 5. Timezone and Formatting Logic
        java.util.TimeZone tz = java.util.TimeZone.getDefault();


        // ---- Full timestamp format (Original format) ----
        java.text.SimpleDateFormat fullFmt = new java.text.SimpleDateFormat("dd-MMM-yyyy hh:mm:ss a z");
        fullFmt.setTimeZone(tz);
        String fullFormatted = fullFmt.format(new java.util.Date(epochMillis));


        // ---- Date-only formatting (Original logic) ----
        String tzID = tz.getID().toUpperCase();
        boolean isUS = tzID.contains("AMERICA/");
        boolean isGMT = tzID.contains("GMT") || tzID.contains("UTC");


        String datePattern;
        if (isUS) {
            datePattern = "MM-dd-yyyy";
        } else if (isGMT) {
            datePattern = "dd-MM-yyyy";
        } else {
            datePattern = "dd-MM-yyyy";
        }


        java.text.SimpleDateFormat dateFmt = new java.text.SimpleDateFormat(datePattern);
        dateFmt.setTimeZone(tz);
        String dateOnly = dateFmt.format(new java.util.Date(epochMillis));


        // ---- Weekday, dd Month yyyy format (Original format) ----
        java.text.SimpleDateFormat weekdayFmt = new java.text.SimpleDateFormat("EEEE, dd MMMM yyyy");
        weekdayFmt.setTimeZone(tz);
        String weekdayOnly = weekdayFmt.format(new java.util.Date(epochMillis));


        // ---- Formatted Outputs ----
        getNiagaraTimeOut().setValue(fullFormatted);
        getDateOnlyOut().setValue(dateOnly);
        getWeekdayOut().setValue(weekdayOnly);
        getStatusTrace().setValue("Updated (" + tz.getID() + ", Offset: " + daysOffset + "d): " + fullFormatted);


    } catch (Exception e) {
        // Handle conversion errors
        getStatusTrace().setValue("Error converting time: " + e.getMessage());
        getNiagaraTimeOut().setValue("");
        getDateOnlyOut().setValue("");
        getWeekdayOut().setValue("");
        getUnixTimeOffset().setValue(0.0);
    }
}


public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
    getStatusTrace().setValue("Epoch → Niagara converter stopped.");
}


void updateTimer() {
    if (ticket != null) {
        ticket.cancel();
    }
    // Run every 1 second (Niagara-safe)
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(1), BProgram.execute, null);
}

```

</details>



<details>
<summary>📄 CSV File Reader + Console Logger (ProgramObject Tutorial)</summary>

Create a CSV file with simple headers, for example:  

```sql
name,address
EdgeLite01,10.10.1.11
EdgeLite02,10.10.1.12
CampusN4,10.10.1.50

```

In the AX Property Sheet view set the `Ord` for the CSV file in the Stations `Files` directory. In Workbench I navigated into my C drive and manually copied the CSV file into the Station.  


<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/CsvParserSnip.png" alt="history tutorial" width="600">
</p>


See logs prints in the Application director as well as athe program uses `System.out.println`.  

```java
  System.out.println("CSV Parser >>> " + msg);
  System.out.println("-------------------------------");
```

---

## 🔧 **Required Imports**

Your ProgramObject must import:

* `java.io.*` 
* `javax.baja.file.*`

Workbench on the ProgramObject auto generated code it should look like this below with proper imports set:

```java
import java.util.*;              /* java Predefined*/
import javax.baja.nre.util.*;    /* nre Predefined*/
import javax.baja.sys.*;         /* baja Predefined*/
import javax.baja.status.*;      /* baja Predefined*/
import javax.baja.util.*;        /* baja Predefined*/
import com.tridium.program.*;    /* program-rt Predefined*/
import javax.baja.file.*;        /* baja User Defined*/
import java.io.*;                /* java User Defined*/
import javax.baja.naming.*;      /* baja By Property*/
```


### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java
// ===============================
// Utility for writing status + console print
// ===============================
private void updateStatus(String msg)
{
  getStatusMessage().setValue(msg);

  // Print to Application Director console
  System.out.println("CSV Parser >>> " + msg);
  System.out.println("-------------------------------");
}

// ===============================
// onStart
// ===============================
public void onStart() throws Exception
{
  updateStatus("CSV Parser: ready.");
}

// ===============================
// onExecute
// ===============================
public void onExecute() throws Exception
{
  try
  {
    // --- 1) Resolve CSV ---
    BOrd fileOrd = getFileOrd();
    if (fileOrd == null)
    {
      updateStatus("Error: fileOrd is null.");
      return;
    }

    BIFile file = (BIFile) fileOrd.getOrd().resolve().get();
    if (file == null)
    {
      updateStatus("Error: fileOrd did not resolve to a BIFile.");
      return;
    }

    // --- 2) Read file ---
    InputStreamReader reader = new InputStreamReader(file.getInputStream());
    String[] rows = FileUtil.readLines(reader);

    if (rows == null || rows.length == 0)
    {
      updateStatus("CSV is empty.");
      return;
    }

    updateStatus(rows.length + " rows found.");

    // --- 3) Parse lines + print to console ---
    for (int i = 0; i < rows.length; i++)
    {
      String line = rows[i];
      if (line == null || line.trim().length() == 0)
        continue;

      String[] fields = TextUtil.splitAndTrim(line, ',');

      // Print in your requested style
      System.out.println("-----------------");
      System.out.println("Row " + i);
      for (int j = 0; j < fields.length; j++)
      {
        System.out.println("  [" + fields[j] + "]");
      }
    }

    updateStatus("CSV parsing complete. See Application Director.");
  }
  catch (Exception e)
  {
    updateStatus("Error: " + e.toString());
    throw e;
  }
}

// ===============================
// onStop
// ===============================
public void onStop() throws Exception
{
  updateStatus("CSV Parser: stopped.");
}

```

</details>


<details>
<summary>📈 History Min/Max via BQL + Application Director Logging</summary>

This tutorial walks you through building a **Niagara 4 ProgramObject** that pull trend histories and finds the min and max values.


<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/historyMinMaxSnip.png" alt="history tutorial" width="600">
</p>

In the AX Property Sheet view set the `Ord` for the CSV file in the Stations `Files` directory. In Workbench I navigated into my C drive and manually copied the CSV file into the Station.  

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/historyMinMaxAxPropSheetSnip.png" alt="history tutorial prop sheet" width="600">
</p>

---

## 🔧 **Required Imports**

Your ProgramObject must import:

* `javax.baja.history.*` (history access + BITable)
* `javax.baja.collection.*` (cursor + column utilities)
* `javax.baja.naming.*` (BOrd)
* `javax.baja.status.*` (StatusEnum, StatusNumeric, StatusString)

Workbench on the ProgramObject auto generated code it should look like this below with proper imports set:

```java
import java.util.*;              /* java Predefined*/
import javax.baja.nre.util.*;    /* nre Predefined*/
import javax.baja.sys.*;         /* baja Predefined*/
import javax.baja.status.*;      /* baja Predefined*/
import javax.baja.util.*;        /* baja Predefined*/
import com.tridium.program.*;    /* program-rt Predefined*/
import javax.baja.collection.*;  /* baja User Defined*/
import javax.baja.history.*;     /* history-rt User Defined*/
import javax.baja.naming.*;      /* baja By Property*/
```

---

## 🧩 **Configuring the Time-Range Enum (VERY IMPORTANT)**


👉 Your code uses **enum tags**, so configure your Enum like:

```java
today
yesterday
last7days
thisMonth
previousMonth
last24hours
```



---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.


```java
// ------------------------------
// Human-friendly rounding
// ------------------------------
private String fmt2(double v)
{
  return String.format("%.2f", v);
}

// ------------------------------
// Unified logging (console + StatusString)
// ------------------------------
private void updateStatus(String msg)
{
  BAbsTime now = BAbsTime.now();
  String stamp = now.toString();

  String full = stamp + " — " + msg;

  // Console output
  System.out.println("[HistoryMinMax] " + full);

  // StatusString slot
  try {
    BStatusString s = getStatusMessage();
    if (s != null) s.setValue(full);
  }
  catch (Exception ignore) {}
}

// Map selected enum to a BQL period= parameter
private String resolvePeriodTag()
{
  BStatusEnum en = getTimeRange();
  if (en == null || en.getValue() == null)
    return "today";

  BEnum v = en.getValue();
  String tag = v.getTag();

  if (tag != null && tag.length() > 0 && !tag.equals("0"))
    return tag.toLowerCase();

  // fallback by ordinal
  switch (v.getOrdinal())
  {
    case 0: return "today";
    case 1: return "yesterday";
    case 2: return "last7days";
    case 3: return "thisMonth";
    case 4: return "previousMonth";
    case 5: return "last24hours";
    default: return "today";
  }
}

public void onStart() throws Exception
{
  updateStatus("HistoryMinMax: ready.");
}

public void onExecute() throws Exception
{
  updateStatus("Starting execution...");

  BOrd baseOrd = getHistoryOrd();
  if (baseOrd == null)
  {
    updateStatus("History ORD is not set.");
    return;
  }

  // Find BQL period tag
  String period = resolvePeriodTag();
  updateStatus("Using time range: " + period);

  String bqlOrdString = baseOrd.toString()
      + "?period=" + period
      + "|bql:select min(value), max(value)";

  updateStatus("Constructed BQL ORD: " + bqlOrdString);

  // Resolve and query
  BITable table;
  try {
    table = (BITable) BOrd.make(bqlOrdString).resolve().get();
    updateStatus("BQL resolved successfully.");
  }
  catch (Exception e) {
    updateStatus("Failed to resolve BQL ORD: " + e.getMessage());
    return;
  }

  ColumnList cols = table.getColumns();
  if (cols.size() < 2)
  {
    updateStatus("Unexpected BQL result format.");
    return;
  }

  TableCursor cur = table.cursor();
  if (cur.next())
  {
    double min = ((BNumber) cur.cell(cols.get(0))).getDouble();
    double max = ((BNumber) cur.cell(cols.get(1))).getDouble();

    updateStatus("Min: " + fmt2(min) + ", Max: " + fmt2(max));

    // Write into baja:StatusNumeric slots
    getMinValue().setValue(min);
    getMaxValue().setValue(max);
  }
  else
  {
    updateStatus("No data returned for selected time range.");
  }
}

public void onStop() throws Exception
{
  updateStatus("HistoryMinMax: stopped.");
}
```

</details>



<details>
<summary>🚨 Fault-Aware Math Block (Status & Exception Handling)</summary>

This ProgramObject is a **fault-aware math demo** that shows how to:

* Safely read `baja:StatusNumeric` and `baja:StatusBoolean` inputs  
* Use **`BStatus.fault`** and **`BStatus.nullStatus`** as an “exception channel”  
* Expose a simple `outFaultFlag` and `statusTrace` string to explain what went wrong  

It takes a single numeric input, doubles it, and publishes the result — **unless** it detects a problem.  
If the input is `NULL`, unwired, or in a non-OK status, the block marks its output as `{fault}` and raises a boolean flag.

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/faultTutorialSnip.png" alt="Fault-Aware Math Block Snip" width="650">
</p>

---

### ⚙️ Slots (Niagara ProgramObject)

| Slot Name      | Type               | Role / Description                                           |
|----------------|--------------------|--------------------------------------------------------------|
| `enable`       | `baja:StatusBoolean` | Master enable; when not OK/true, outputs are forced to NULL |
| `inValue`      | `baja:StatusNumeric` | Main numeric input to be processed                          |
| `faultIn`      | `baja:StatusBoolean` | Manual fault injection (forces block into FAULT)            |
| `outValue`     | `baja:StatusNumeric` | Output value (`inValue * 2`) with status `{ok}` or `{fault}`|
| `outFaultFlag` | `baja:StatusBoolean` | `true` when block is in fault; `false` when healthy         |
| `statusTrace`  | `baja:StatusString`  | Human-readable trace message for debugging                  |

**Timer**  
The block uses an internal timer (`Clock.schedule`) to execute every **5 seconds**.

---

### 🧠 Under the Hood

This block treats **status as its exception mechanism**:

1. **Enable guard**  
   * If `enable` is not OK/true, the block calls `nullOutputs()` and exits.  
   * This clears outputs to `BStatus.nullStatus` and writes a reason into `statusTrace`.

2. **Unwired / NULL input handling**  
   * `ensureNumericWiredOrNull("inValue", getInValue())` checks if `inValue` has a link.  
   * If not wired, it forces `inValue` to `0` with `BStatus.nullStatus`, so `inStatus.isNull()` becomes true.

3. **Auto fault rules**  
   * If `inValue` is `NULL` → outputs forced `NULL`, `outFaultFlag = true`.  
   * If `inValue.status` is non-OK or `faultIn == true` → `outValue.status = BStatus.fault`, `outFaultFlag = true`.  
   * Otherwise, `outValue.status = BStatus.ok` and `outFaultFlag = false`.

4. **Exception safety**  
   * `onExecute()` is wrapped in a `try/catch`.  
   * If anything throws, the block sets outputs to `nullStatus` and writes the error to `statusTrace` instead of crashing the station.

This pattern is a great template for any **algorithm block** where you want robust, inspectable fault behavior.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters.  
> Paste **only** the methods below into the Program’s **Source** editor for your `Fault Demo` ProgramObject.

```java
// ==========================
// Class-level state
// ==========================
Clock.Ticket ticket;
private static final int EXEC_PERIOD_SEC = 5; // run every 5 seconds

// ==========================
// Lifecycle
// ==========================
public void onStart() throws Exception
{
  // Initialize outputs as NULL so downstream logic knows it's not ready yet
  nullOutputs("Fault demo block started.");
  updateTimer();
}

public void onExecute() throws Exception
{
  try
  {
    updateTimer();

    // --- 0. Master enable guard ---
    if (!safeBool(getEnable()))
    {
      nullOutputs("Disabled via 'enable' flag.");
      return;
    }

    // --- 1. Handle unwired numeric input (optional) ---
    ensureNumericWiredOrNull("inValue", getInValue());

    BStatus inStatus    = getInValue().getStatus();
    boolean manualFault = safeBool(getFaultIn());

    // --- 2. If input is NULL, force outputs NULL + raise fault flag ---
    if (inStatus.isNull())
    {
      getOutValue().setValue(0);
      getOutValue().setStatus(BStatus.nullStatus);

      getOutFaultFlag().setValue(true);
      getOutFaultFlag().setStatus(BStatus.ok);

      getStatusTrace().setValue("inValue is NULL (unwired or cleared) → outputs forced NULL, faultFlag=TRUE.");
      return;
    }

    // --- 3. If input itself is not OK, treat that as a fault source ---
    boolean upstreamFault = !inStatus.isOk();

    // --- 4. Normal math: double the value ---
    double inVal = getInValue().getValue();
    double result = inVal * 2.0;

    getOutValue().setValue(result);

    // --- 5. Decide final fault state ---
    boolean effectiveFault = manualFault || upstreamFault;

    if (effectiveFault)
    {
      // Mark the numeric as "fault" so it shows yellow {fault}
      getOutValue().setStatus(BStatus.fault);

      getOutFaultFlag().setValue(true);
      getOutFaultFlag().setStatus(BStatus.ok);

      String reason = manualFault ? "manual faultIn=TRUE" : "upstream input status not OK";
      getStatusTrace().setValue("FAULT: " + reason + " | in=" + inVal + " → out=" + result);
    }
    else
    {
      getOutValue().setStatus(BStatus.ok);

      getOutFaultFlag().setValue(false);
      getOutFaultFlag().setStatus(BStatus.ok);

      getStatusTrace().setValue("OK: inValue=" + inVal + " → outValue=" + result);
    }
  }
  catch (Exception e)
  {
    // Never let exceptions bubble out of onExecute
    getOutValue().setStatus(BStatus.nullStatus);
    getOutFaultFlag().setStatus(BStatus.nullStatus);
    getStatusTrace().setValue("Error in fault demo block: " + e.toString());
  }
}

public void onStop() throws Exception
{
  if (ticket != null)
  {
    ticket.cancel();
    ticket = null;
  }
  nullOutputs("Fault demo block stopped.");
}

// ==========================
// Helpers
// ==========================
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

/** Treat any non-OK or NULL boolean as false */
private boolean safeBool(BStatusBoolean b)
{
  if (b == null) return false;
  if (!b.getStatus().isOk()) return false;
  return b.getValue();
}

/** If slot is unwired, mark it NULL so downstream logic can see it */
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
  catch (Exception e)
  {
    // ignore – safest thing is to leave status as-is
  }
}

/** Convenience: clear outputs + set trace */
private void nullOutputs(String trace)
{
  getOutValue().setValue(0);
  getOutValue().setStatus(BStatus.nullStatus);

  getOutFaultFlag().setValue(false);
  getOutFaultFlag().setStatus(BStatus.nullStatus);

  getStatusTrace().setValue(trace);
}
```