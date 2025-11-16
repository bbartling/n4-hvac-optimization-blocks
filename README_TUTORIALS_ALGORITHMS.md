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
<summary>🔥 kitControl's Tstat but with a True `deadband` and not a `diff` or differential</summary>

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

--- 




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
<summary>⏱️ Linear Degree Per Minute Optimal Start Self-Tuning Block</summary>

This block implements a **self-learning Optimal Start/Stop algorithm** for zone recovery in Niagara 4.  
It continuously tunes heating & cooling rates with an Exponential Moving Average (EMA) so the zone reaches setpoint **just-in-time**—saving energy without sacrificing comfort.

The Optimal Start logic draws on the latest PNNL research for **Model 1**, which is detailed in the *Quadratic Regression Optimal Start Self-Tuning Block* section of this README. The linear model is a slightly simpler version.

See the included white paper:

- **Optimal Start Control for ACs and HPs (PNNL)** — `pdf/Optimal Start Control for ACs and HPs.pdf`  
  👉 https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/optimalStartSnip.png"  alt="Optimal Start Program Object" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/zoneRecoverySnip.png" alt="Recovery Trend Example" width="750">
  <br><em>Recovery trend illustrating learned cool-down rate&nbsp;≈ 0.15 °F /min</em>
</p>

---

### Inputs

| Slot | Type | Notes |
| :--- | :--- | :--- |
| `zoneTemp` | `BStatusNumeric` | Current zone temperature. |
| `targetZoneTempSetpoint` | `BStatusNumeric` | The desired occupied setpoint. |
| `outdoorAirTemp` | `BStatusNumeric` | Optional outdoor air temperature, used for logging performance history. |
| `scheduleNextValue` | `BStatusBoolean` | The occupancy value of the *next* schedule event (`true` if occupied). |
| `scheduleNextEventTime` | `BStatusNumeric` | The timestamp (in Java milliseconds) of the next schedule event. |
| `maxMinutesAllowed` | `BStatusNumeric` | Safety cap for the maximum calculated `minutesToSetpoint` (default = 180 min). |
| `tempTolerance` | `BStatusNumeric` | The acceptable temperature deviation from setpoint (e.g., 1.0°F, default = 0.5°F). |
| `historyDaysToRetain` | `BStatusNumeric` | The number of recent performance records to keep for learning (default = 10). |
| `emaWeightingFactor` | `BStatusNumeric` | The smoothing factor for the EMA learning algorithm (1-10, default = 2). |
| `commandOffDelaySeconds`| `BStatusNumeric`| Countdown delay in seconds that starts after the optimal start run ends to release to `null`. |
| `clearHistoryNow` | `BStatusBoolean` | A manual trigger to erase all learned performance history. |
| `printToConsoleLog` | `BStatusBoolean` | Set to `true` to enable detailed debug messages in the Niagara console. |

### Outputs

| Slot | Type | Description |
| :--- | :--- | :--- |
| `equipmentStartCommand` | `BStatusBoolean` | **The final output command; `true` when the equipment should run else `null`. **|
| `minutesToSetpoint` | `BStatusNumeric` | The last run actual time recorded to reach setpoint based on the learning model. |
| `degreesPerMinuteHeat` | `BStatusNumeric` | Active value used in the heating rate in °F / minute. |
| `degreesPerMinuteCool` | `BStatusNumeric` | Active value used in the cooling rate in °F / minute. |
| `currentHistoryRecordCount`| `BStatusNumeric` | The total number of HEAT and COOL performance records being stored. |
| `statusLog` | `BStatusString` | A timestamped log of the block's most recent major action. |
| `historyLog` | `BStatusString` | A multi-line string showing a dump of all performance history records. |
| `isRunning` | `BStatusBoolean` | `True` only when a learning run is actively in progress.** |
| `zoneAtTempTolerance` | `BStatusBoolean` | `True` if the current `zoneTemp` is within the tolerance of the `targetZoneTempSetpoint`. |
| `warmupTimeMinutes` | `BStatusNumeric` | A live stopwatch showing how many minutes the current run has been active. |
| `countdownToNullStatus`| `BStatusBoolean` | Returns `True` only when the off-delay countdown is active. |

### Key Features

* **Adaptive EMA learning** keeps separate heat / cool models and prunes history after _N_ days.  
* **Internal timer & off-delay**—no Execute-on-Change flag required.  
* **Automatic NULL handling** for outputs during countdown.  
* **Verbose console debugging** toggled via `printToConsoleLog`.  
* Designed to drop straight into a **Schedule → Optimal Start Block → Equipment Enable** chain.

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
// Developer Note: For the `historyLog` feature to work, please add a new
// BStatusString slot named "historyLog" to this Program Object in Workbench.

// A static inner class to hold detailed historical performance data.
static class PerformanceRecord {
    long timestamp;
    double rate; // degrees per minute
    String mode; // "HEAT" or "COOL"
    double zoneTempStart;
    double outdoorTempStart;

    PerformanceRecord(long timestamp, double rate, String mode, double zoneTempStart, double outdoorTempStart) {
        this.timestamp = timestamp;
        this.rate = rate;
        this.mode = mode;
        this.zoneTempStart = zoneTempStart;
        this.outdoorTempStart = outdoorTempStart;
    }
}

// Member variables
private Clock.Ticket ticket;
private long startTimestamp = 0;
private boolean isOptimalStartRunning = false;
private long lastStartTriggerTimestamp = 0; 
private static final double DEFAULT_RATE_DEG_PER_MIN = 0.1;
private boolean setpointWasMetDuringRun = false;
private double minutesToReachSetpoint = 0.0;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0;

// Two separate lists to store performance history for each mode.
private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();

/**
 * Called once when the program starts. Initializes defaults.
 */
public void onStart() throws Exception {
    // Set default values for configurable parameters
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    if (getEmaWeightingFactor().isNull()) setEmaWeightingFactor(new BStatusNumeric(2.0));
    
    // Initialize output/status slots
    setIsRunning(new BStatusBoolean(false));
    setMinutesToSetpoint(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    getEquipmentStartCommand().setValue(false); 
    getEquipmentStartCommand().setStatus(BStatus.NULL); 
    getStatusLog().setValue("[onStart] Optimal Start block initialized.");
    
    // Initialize history log and update model
    updateHistoryLog(); 
    updateModel();
    setZoneAtTempTolerance(new BStatusBoolean(false)); 
    
    updateTimer();
}

/**
 * Main execution loop, called periodically by the timer.
 * REVISED to act as a master state controller.
 */
public void onExecute() throws Exception {
    updateTimer(); 

    updateZoneAtTempTolerance();

    if (getClearHistoryNow().getValue()) {
        clearHistory();
        setClearHistoryNow(new BStatusBoolean(false));
    }

    // --- REVISED: Explicit State-Based Logic ---
    if (isOptimalStartRunning) {
        // STATE 1: ACTIVE RUN
        // The ONLY logic that can stop the run is inside monitorActiveRun.
        monitorActiveRun();

        // As a safeguard, force the command to stay ON during the run.
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);

    } else {
        // STATE 2: NOT RUNNING (Idle, Estimating, or in Off-Delay)
        // Only run the estimate and start-command logic when not in an active run.
        updateIdleEstimate();
        updateEquipmentStartCommand();
    }

    // Optional debug tracing remains the same
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Debug] ---");
        System.out.println("isOptimalStartRunning: " + isOptimalStartRunning);
        System.out.println("isOffDelayActive: " + isOffDelayActive);
        System.out.println("setpointWasMetDuringRun: " + setpointWasMetDuringRun);
        System.out.println("minutesToSetpoint (estimate): " + round1(getMinutesToSetpoint().getValue()));
        System.out.println("equipmentStartCommand: " + getEquipmentStartCommand().getValue() + " (Status: " + getEquipmentStartCommand().getStatus() + ")");
        System.out.println("-----------------");
    }
}

/**
 * Called once when the program is stopped.
 */
public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

/**
 * This method now ONLY handles starting a new run or managing the off-delay.
 * It is no longer called when a run is active.
 */
private void updateEquipmentStartCommand() {
    // --- Off-Delay Timer Management ---
    if (isOffDelayActive) {
        long elapsedSeconds = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delayDuration = 60; // Default 60s
        if (getCommandOffDelaySeconds().getStatus().isOk()) {
            delayDuration = (long) getCommandOffDelaySeconds().getValue();
        }

        if (elapsedSeconds >= delayDuration) {
            // Timer has expired.
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false); 
            setFormattedStatusLog("Off-delay expired. Command released to NULL.");
        } else {
            // Timer is still running.
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Command off-delay active. " + (delayDuration - elapsedSeconds) + "s remaining.");
        }
        return; // Skip all other logic while timer is active.
    }

    // --- Standard Start/Stop Logic (Sensor check removed as it's handled elsewhere) ---
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        getCountdownToNullStatus().setValue(false);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    boolean startConditionMet = false;

    // --- Start Condition Logic (is now only evaluated when a run is not active) ---
    if (isNextPeriodOccupied) { // No longer need !isOptimalStartRunning check here
        long currentTime = System.currentTimeMillis();
        long nextEventTime = (long) getScheduleNextEventTime().getValue();
        double timeToNextMinutes = (nextEventTime - currentTime) / 60000.0;
        if (timeToNextMinutes < 0) timeToNextMinutes = 0;
        
        double optimalStartMinutes = getMinutesToSetpoint().getValue();

        if (optimalStartMinutes >= timeToNextMinutes) {
            startConditionMet = true;
        }
    }

    // --- Final Command Output Logic ---
    if (startConditionMet) {
        // Start the equipment.
        startOptimalStartSequence();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);
    } else {
        // The command should be OFF. Start the countdown if needed.
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Entering command off-delay countdown...");
        } else {
            getCountdownToNullStatus().setValue(false);
        }
    }
}


/**
 * Starts a new warmup/cooldown sequence.
 */
private void startOptimalStartSequence() {
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Start] Skipping: Zone temp is already within tolerance.");
        setMinutesToSetpoint(new BStatusNumeric(0.0));
        return;
    }
    
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[ERROR] Cannot start: Zone Temp or Target Setpoint not available.");
        return;
    }

    // Reset state for the new run
    setpointWasMetDuringRun = false;
    minutesToReachSetpoint = 0.0;

    startTimestamp = System.currentTimeMillis();
    isOptimalStartRunning = true;
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    } else {
        setOutdoorTempAtStart(new BStatusNumeric(Double.NaN));
    }
    
    setFormattedStatusLog("[Start] Optimal Start sequence initiated.");
}

/**
 * Monitors an active warmup/cooldown run.
 */
private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsedMinutes = (now - startTimestamp) / 60000.0;

    // 1. Check if the setpoint has been met for the first time.
    if (getZoneAtTempTolerance().getValue() && !setpointWasMetDuringRun) {
        setpointWasMetDuringRun = true;
        minutesToReachSetpoint = elapsedMinutes;
        setFormattedStatusLog("[Monitor] Target met in " + round1(minutesToReachSetpoint) + " min. Stored value for final calculation.");
    }

    // 2. Handle a loss of sensor data as a hard stop.
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[Monitor] Run stopped: Lost Zone Temp or Target Setpoint.");
        stopAndRecordPerformance(elapsedMinutes);
        return;
    }

    // 3. The schedule changing state is the primary trigger to end the run.
    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    if (!isNextPeriodOccupied) {
        double finalPerformanceMinutes = setpointWasMetDuringRun ? minutesToReachSetpoint : elapsedMinutes;
        setFormattedStatusLog("[Monitor] Schedule occupied. Recording performance using " + round1(finalPerformanceMinutes) + " min.");
        stopAndRecordPerformance(finalPerformanceMinutes);
    }
    
    // This provides a live stopwatch for the user interface.
    setWarmupTimeMinutes(new BStatusNumeric(elapsedMinutes));
}

/**
 * Stops the run and records its performance.
 */
private void stopAndRecordPerformance(double actualMinutes) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));

    double zoneStart = getZoneTempAtStart().getValue();
    double zoneNow = getZoneTemp().getValue();
    double delta = Math.abs(zoneNow - zoneStart);
    
    if (actualMinutes > 0.1) {
        double rate = delta / actualMinutes;
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        double outdoorStart = getOutdoorTempAtStart().getStatus().isOk() ? getOutdoorTempAtStart().getValue() : Double.NaN;
        
        // ADDED BACK: Log the performance record details
        if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
            System.out.println("[Performance Record] Recording with duration: " + round1(actualMinutes) + " min, Rate: " + round1(rate) + " deg/min, Mode: " + mode);
        }
        
        PerformanceRecord newRecord = new PerformanceRecord(System.currentTimeMillis(), rate, mode, zoneStart, outdoorStart);

        if ("HEAT".equals(mode)) {
            heatHistory.add(newRecord);
        } else {
            coolHistory.add(newRecord);
        }
        setFormattedStatusLog("[" + mode + "] run recorded. Rate: " + round1(rate) + " deg/min.");
        updateModel();
    } else {
       setFormattedStatusLog("[Record] Run was too short. Performance not recorded.");
    }
}

/**
 * Updates the learned performance model using an EMA of historical data.
 */
private void updateModel() {
    pruneHistory();
    double heatRateEma = computeEmaForMode("HEAT");
    double coolRateEma = computeEmaForMode("COOL");
    setDegreesPerMinuteHeat(new BStatusNumeric(heatRateEma > 0.0 ? heatRateEma : DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(coolRateEma > 0.0 ? coolRateEma : DEFAULT_RATE_DEG_PER_MIN));
    
    // ADDED: Optional logging to show the data behind the EMA calculation
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Model Update] ---");

        // Build and print the HEAT history array
        StringBuilder heatRates = new StringBuilder("HEAT Rates (deg/min): [");
        if (heatHistory.isEmpty()) {
            heatRates.append("No history]");
        } else {
            for (int i = 0; i < heatHistory.size(); i++) {
                heatRates.append(round1(heatHistory.get(i).rate));
                if (i < heatHistory.size() - 1) {
                    heatRates.append(", ");
                }
            }
            heatRates.append("]");
        }
        System.out.println(heatRates.toString());
        System.out.println("New HEAT EMA: " + round1(heatRateEma));

        // Build and print the COOL history array
        StringBuilder coolRates = new StringBuilder("COOL Rates (deg/min): [");
        if (coolHistory.isEmpty()) {
            coolRates.append("No history]");
        } else {
            for (int i = 0; i < coolHistory.size(); i++) {
                coolRates.append(round1(coolHistory.get(i).rate));
                if (i < coolHistory.size() - 1) {
                    coolRates.append(", ");
                }
            }
            coolRates.append("]");
        }
        System.out.println(coolRates.toString());
        System.out.println("New COOL EMA: " + round1(coolRateEma));
        System.out.println("----------------------");
    }
    
    updateCurrentHistoryRecordCount();
    updateHistoryLog();
}

/**
 * Calculates and outputs the estimated time to reach setpoint when idle.
 */
private void updateIdleEstimate() {
    if (getZoneAtTempTolerance().getValue()) {
        setMinutesToSetpoint(new BStatusNumeric(0.0));
        return;
    }
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMinutes = getMaxMinutesAllowed().getValue();
    double estimatedMinutes = maxMinutes;
    
    if (zone < target) { // Heating needed
        double heatRate = getDegreesPerMinuteHeat().getValue();
        if (heatRate > 0.01) estimatedMinutes = delta / heatRate;
    } else { // Cooling needed
        double coolRate = getDegreesPerMinuteCool().getValue();
        if (coolRate > 0.01) estimatedMinutes = delta / coolRate;
    }
    setMinutesToSetpoint(new BStatusNumeric(Math.min(estimatedMinutes, maxMinutes)));
}

//================================================================
// --- Helper and Utility Methods ---
//================================================================

private void setFormattedStatusLog(String message) {
    String lastTriggerTimeStr = "never";
    if (lastStartTriggerTimestamp > 0) {
        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        lastTriggerTimeStr = sdf.format(new java.util.Date(lastStartTriggerTimestamp));
    }
    getStatusLog().setValue("[Last Trigger: " + lastTriggerTimeStr + "] " + message);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk() || getTempTolerance().isNull()) {
        setZoneAtTempTolerance(new BStatusBoolean(false));
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double tolerance = getTempTolerance().getValue();
    setZoneAtTempTolerance(new BStatusBoolean(Math.abs(zone - target) <= tolerance));
}

private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxRecords = (int) getHistoryDaysToRetain().getValue();
    while (heatHistory.size() > maxRecords) heatHistory.remove(0);
    while (coolHistory.size() > maxRecords) coolHistory.remove(0);
}

private void clearHistory() {
    heatHistory.clear();
    coolHistory.clear();
    updateModel();  
    setFormattedStatusLog("[History] All performance records have been cleared.");
}

private double computeEmaForMode(String mode) {
    java.util.List<PerformanceRecord> relevantHistory = "HEAT".equals(mode) ? heatHistory : coolHistory;
    if (relevantHistory.isEmpty()) return 0.0;
    double[] series = new double[relevantHistory.size()];
    for (int i = 0; i < relevantHistory.size(); i++) series[i] = relevantHistory.get(i).rate;
    return (series.length == 1) ? series[0] : computeEMA(series);
}

private double computeEMA(double[] series) {
    if (series.length == 0) return 0.0;
    double weightingFactor = 2.0;
    if (getEmaWeightingFactor().getStatus().isOk()) {
        weightingFactor = Math.max(1.0, Math.min(getEmaWeightingFactor().getValue(), 10.0));
    }
    double k = weightingFactor / (series.length + 1.0);
    double ema = series[0];
    for (int i = 1; i < series.length; i++) {
        ema = series[i] * k + ema * (1 - k);
    }
    return ema;
}

private void updateHistoryLog() {
    try {
        BStatusString historyLogSlot = (BStatusString)get("historyLog");
        if (historyLogSlot == null) return;
        StringBuilder sb = new StringBuilder();
        sb.append("--- HEAT History ---\n");
        if (heatHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : heatHistory) {
            sb.append(String.format("Rate: %.1f, ZS: %.1f, OAT: %s\n", r.rate, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        sb.append("\n--- COOL History ---\n");
        if (coolHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : coolHistory) {
            sb.append(String.format("Rate: %.1f, ZS: %.1f, OAT: %s\n", r.rate, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        historyLogSlot.setValue(sb.toString());
    } catch (Exception e) {
        System.out.println("[ERROR] Failed to update historyLog slot: " + e.getMessage());
    }
}

private void updateCurrentHistoryRecordCount() {
    setCurrentHistoryRecordCount(new BStatusNumeric(heatHistory.size() + coolHistory.size()));
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private double round1(double v) {
    if (Double.isNaN(v)) return 0.0;
    return Math.round(v * 10.0) / 10.0;
}

```


</details>



<details>
<summary>📊 Quadratic Regression Optimal Start Self-Tuning Block</summary>


Both Linear and Quadratic Regression Optimal Start Self-Tuning Block implement a **self-learning Optimal Start/Stop** algorithm designed to ensure the zone reaches its setpoint *just in time* for occupancy—saving runtime and energy while maintaining comfort.

They share the **exact same slot names and wiring**, so you can compile and drop either version into Niagara Workbench with zero rewiring.
Under the hood, only the math model differs.

This Optimal Start logic draws on the latest PNNL research for `Model 1` Quadratic Regression Optimal Start Self-Tuning Block. See the included white paper:

- **Optimal Start Control for ACs and HPs (PNNL)** — `pdf/Optimal Start Control for ACs and HPs.pdf`  
  👉 https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf

---

### 🧩 Slot & Naming Compatibility

The **Linear** and **Quadratic** blocks use the same I/O interface:

| Slot                     | Type             | Description                        |
| :----------------------- | :--------------- | :--------------------------------- |
| `zoneTemp`               | `BStatusNumeric` | Current zone temperature           |
| `targetZoneTempSetpoint` | `BStatusNumeric` | Desired occupied setpoint          |
| `outdoorAirTemp`         | `BStatusNumeric` | Optional, reference only           |   |
| `scheduleNextValue`      | `BStatusBoolean` | Next event occupancy flag          |
| `scheduleNextEventTime`  | `BStatusNumeric` | Timestamp of next schedule event   |
| `maxMinutesAllowed`      | `BStatusNumeric` | Safety cap on start time           |
| `tempTolerance`          | `BStatusNumeric` | Acceptable deviation from setpoint |
| `minutesToSetpoint`      | `BStatusNumeric` | Calculated time to reach setpoint  |

Because the slots are identical, **technicians can swap Linear ↔ Quadratic codebases freely** to test which model best fits the building.

> 🔄 *Recompile either version with Workbench to try both algorithms—no re-wiring, no slot edits required.*

---

### 🔹 Linear Model — the “Straight-Line” Lesson

The **Linear** model assumes a direct relationship between how far the zone is from setpoint and how long recovery will take.

$$
\text{RunTime} = (A \times \text{TempDiff}^2) + (B \times \text{TempDiff}) + C
$$

where:  
- **TempDiff** = TargetSetpoint − ZoneTemp  
- **A** and **B** = learned coefficients for curve shape  
- **C** = baseline offset  

> Note - Outside air temperature is included but for reference only at the moment until more advanced models are attemped like PNNL Model 3 from the White Paper.

* The block tracks both **heating and cooling recovery rates** over multiple days (N-day rolling history).
* Each recovery event records how quickly the zone temperature changes (°F per minute).
* An **Exponential Moving Average (EMA)** smooths these values—giving the **most recent recoveries the most weight**.
* This allows the block to automatically adapt to seasonal shifts, load changes, or mechanical performance drift.

In short: *it’s always learning, but it trusts recent days the most.*

---

### 🔸 Quadratic Model — the “Curved” Lesson

The **Quadratic** version is a smarter, drop-in upgrade that adds curvature for more realistic recovery behavior.

$$
\text{RunTime} = (A \times \text{TempDiff}^2) + (B \times \text{TempDiff}) + C
$$

This captures how systems heat or cool quickly at first but slow down as they approach setpoint (diminishing returns).

* **A** adds the curve — recovery slows as setpoint nears.  
* **B** adjusts the slope — the overall rate per degree of difference.  
* **C** is the baseline offset.  
* The **Quadratic block also maintains a similar N-day history** and uses those same stored records for self-tuning, just with a more complex regression model behind the scenes.

---


### ✅ Key Takeaways

* Both models share identical slots and naming conventions.
* Linear = simple straight-line rate; Quadratic = curved and more realistic.
* Both store N days of recovery data for heating & cooling modes.
* EMA weighting gives more importance to recent recoveries.
* You can safely recompile and test either version in the same station.

---


### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/*
 * =================================================================
 * Optimal Start/Stop Self-Tuning Block
 * REWRITE (v3) - Quadratic Model 1 - NO NEW SLOTS
 *
 * This version implements the quadratic model from the PNNL paper:
 * t_opt = alpha_a * (deltaT^2) + alpha_b
 *
 * It learns the 'alpha_a' and 'alpha_b' parameters and stores
 * them in private member variables (not slots).
 *
 * It still populates the EXISTING 'degreesPerMinute' slots
 * with an average rate for reference/diagnostics.
 *
 * You can paste-and-recompile this code without adding new slots.
 * =================================================================
 */

// A static inner class to hold raw historical performance data.
static class PerformanceRecord {
    long timestamp;
    double durationMinutes; // This is 't' (our y-value)
    double deltaT;          // This is 'deltaT' (used to calculate our x-value)
    String mode;            // "HEAT" or "COOL"
    double zoneTempStart;
    double outdoorTempStart;

    PerformanceRecord(long timestamp, double durationMinutes, double deltaT, String mode, double zoneTempStart, double outdoorTempStart) {
        this.timestamp = timestamp;
        this.durationMinutes = durationMinutes;
        this.deltaT = deltaT;
        this.mode = mode;
        this.zoneTempStart = zoneTempStart;
        this.outdoorTempStart = outdoorTempStart;
    }
}

// --- Member Variables ---
private Clock.Ticket ticket;
private long startTimestamp = 0;
private boolean isOptimalStartRunning = false;
private long lastStartTriggerTimestamp = 0; 
private boolean setpointWasMetDuringRun = false;
private double minutesToReachSetpoint = 0.0;
private boolean isOffDelayActive = false;
private long offDelayStartTime = 0;

// Default MODEL 1 parameters (if no history)
// t = 0.1 * (deltaT^2) + 5.0
private static final double DEFAULT_ALPHA_A = 0.1;
private static final double DEFAULT_ALPHA_B = 5.0;
private static final double DEFAULT_RATE_DEG_PER_MIN = 0.1; // For reference slot

// --- "Under the Hood" parameters (NOT slots) ---
private double learned_alpha_a_heat = DEFAULT_ALPHA_A;
private double learned_alpha_b_heat = DEFAULT_ALPHA_B;
private double learned_alpha_a_cool = DEFAULT_ALPHA_A;
private double learned_alpha_b_cool = DEFAULT_ALPHA_B;

// Two separate lists to store performance history for each mode.
private java.util.List<PerformanceRecord> heatHistory = new java.util.ArrayList<>();
private java.util.List<PerformanceRecord> coolHistory = new java.util.ArrayList<>();

/**
 * Called once when the program starts. Initializes defaults.
 */
public void onStart() throws Exception {
    // Set default values for configurable parameters
    if (getMaxMinutesAllowed().isNull()) setMaxMinutesAllowed(new BStatusNumeric(180.0));
    if (getTempTolerance().isNull()) setTempTolerance(new BStatusNumeric(0.5));
    if (getHistoryDaysToRetain().isNull()) setHistoryDaysToRetain(new BStatusNumeric(10.0));
    
    // Initialize output/status slots
    setIsRunning(new BStatusBoolean(false));
    setMinutesToSetpoint(new BStatusNumeric(getMaxMinutesAllowed().getValue()));
    
    // Initialize REFERENCE rate slots to default
    setDegreesPerMinuteHeat(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(DEFAULT_RATE_DEG_PER_MIN));

    getEquipmentStartCommand().setValue(false); 
    getEquipmentStartCommand().setStatus(BStatus.NULL); 
    getStatusLog().setValue("[onStart] Optimal Start block (Model 1 Quadratic) initialized.");
    
    updateHistoryLog(); 
    updateModel(); // Run once on start to learn from any persisted history
    setZoneAtTempTolerance(new BStatusBoolean(false)); 
    
    updateTimer();
}

/**
 * Main execution loop, called periodically by the timer.
 * This is the master state controller.
 */
public void onExecute() throws Exception {
    updateTimer(); 

    updateZoneAtTempTolerance();

    if (getClearHistoryNow().getValue()) {
        clearHistory();
        setClearHistoryNow(new BStatusBoolean(false));
    }

    if (isOptimalStartRunning) {
        // STATE 1: ACTIVE RUN
        monitorActiveRun();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);

    } else {
        // STATE 2: NOT RUNNING (Idle, Estimating, or in Off-Delay)
        updateIdleEstimate();
        updateEquipmentStartCommand();
    }

    // Optional debug tracing
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Debug Model 1] ---");
        System.out.println("isOptimalStartRunning: " + isOptimalStartRunning);
        System.out.println("isOffDelayActive: " + isOffDelayActive);
        System.out.println("minutesToSetpoint (estimate): " + round1(getMinutesToSetpoint().getValue()));
        System.out.println("equipmentStartCommand: " + getEquipmentStartCommand().getValue() + " (Status: " + getEquipmentStartCommand().getStatus() + ")");
        System.out.println("-----------------");
    }
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

/**
 * Handles starting a new run or managing the off-delay.
 */
private void updateEquipmentStartCommand() {
    // --- Off-Delay Timer Management ---
    if (isOffDelayActive) {
        long elapsedSeconds = (System.currentTimeMillis() - offDelayStartTime) / 1000;
        long delayDuration = 60; // Default 60s
        if (getCommandOffDelaySeconds().getStatus().isOk()) {
            delayDuration = (long) getCommandOffDelaySeconds().getValue();
        }

        if (elapsedSeconds >= delayDuration) {
            isOffDelayActive = false;
            getEquipmentStartCommand().setValue(false);
            getEquipmentStartCommand().setStatus(BStatus.NULL);
            getCountdownToNullStatus().setValue(false); 
            setFormattedStatusLog("Off-delay expired. Command released to NULL.");
        } else {
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Command off-delay active. " + (delayDuration - elapsedSeconds) + "s remaining.");
        }
        return; // Skip all other logic while timer is active.
    }

    // --- Standard Start/Stop Logic ---
    if (!getScheduleNextValue().getStatus().isOk() || !getScheduleNextEventTime().getStatus().isOk()) {
        getEquipmentStartCommand().setValue(false);
        getEquipmentStartCommand().setStatus(BStatus.NULL);
        getCountdownToNullStatus().setValue(false);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    boolean startConditionMet = false;

    if (isNextPeriodOccupied) {
        long currentTime = System.currentTimeMillis();
        long nextEventTime = (long) getScheduleNextEventTime().getValue();
        double timeToNextMinutes = (nextEventTime - currentTime) / 60000.0;
        if (timeToNextMinutes < 0) timeToNextMinutes = 0;
        
        double optimalStartMinutes = getMinutesToSetpoint().getValue();

        if (optimalStartMinutes >= timeToNextMinutes) {
            startConditionMet = true;
        }
    }

    // --- Final Command Output Logic ---
    if (startConditionMet) {
        startOptimalStartSequence();
        getEquipmentStartCommand().setValue(true);
        getEquipmentStartCommand().setStatus(BStatus.ok);
        getCountdownToNullStatus().setValue(false);
    } else {
        if (getEquipmentStartCommand().getValue()) {
            isOffDelayActive = true;
            offDelayStartTime = System.currentTimeMillis();
            getCountdownToNullStatus().setValue(true);
            setFormattedStatusLog("Entering command off-delay countdown...");
        } else {
            getCountdownToNullStatus().setValue(false);
        }
    }
}


/**
 * Starts a new warmup/cooldown sequence.
 */
private void startOptimalStartSequence() {
    if (getZoneAtTempTolerance().getValue()) {
        setFormattedStatusLog("[Start] Skipping: Zone temp is already within tolerance.");
        setMinutesToSetpoint(new BStatusNumeric(0.0));
        return;
    }
    
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[ERROR] Cannot start: Zone Temp or Target Setpoint not available.");
        return;
    }

    setpointWasMetDuringRun = false;
    minutesToReachSetpoint = 0.0;
    startTimestamp = System.currentTimeMillis();
    isOptimalStartRunning = true;
    lastStartTriggerTimestamp = System.currentTimeMillis();
    setIsRunning(new BStatusBoolean(true));
    setZoneTempAtStart(new BStatusNumeric(getZoneTemp().getValue()));
    
    if (getOutdoorAirTemp().getStatus().isOk()) {
        setOutdoorTempAtStart(new BStatusNumeric(getOutdoorAirTemp().getValue()));
    } else {
        setOutdoorTempAtStart(new BStatusNumeric(Double.NaN));
    }
    
    setFormattedStatusLog("[Start] Optimal Start sequence initiated.");
}

/**
 * Monitors an active warmup/cooldown run.
 */
private void monitorActiveRun() {
    long now = System.currentTimeMillis();
    double elapsedMinutes = (now - startTimestamp) / 60000.0;

    if (getZoneAtTempTolerance().getValue() && !setpointWasMetDuringRun) {
        setpointWasMetDuringRun = true;
        minutesToReachSetpoint = elapsedMinutes;
        setFormattedStatusLog("[Monitor] Target met in " + round1(minutesToReachSetpoint) + " min. Stored value.");
    }

    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        setFormattedStatusLog("[Monitor] Run stopped: Lost Zone Temp or Target Setpoint.");
        stopAndRecordPerformance(elapsedMinutes);
        return;
    }

    boolean isNextPeriodOccupied = getScheduleNextValue().getValue();
    if (!isNextPeriodOccupied) {
        double finalPerformanceMinutes = setpointWasMetDuringRun ? minutesToReachSetpoint : elapsedMinutes;
        setFormattedStatusLog("[Monitor] Schedule occupied. Recording performance using " + round1(finalPerformanceMinutes) + " min.");
        stopAndRecordPerformance(finalPerformanceMinutes);
    }
    
    setWarmupTimeMinutes(new BStatusNumeric(elapsedMinutes));
}

/**
 * Stops the run and records its performance.
 * THIS IS MODIFIED to store (t, deltaT)
 */
private void stopAndRecordPerformance(double actualMinutes) {
    isOptimalStartRunning = false;
    setIsRunning(new BStatusBoolean(false));

    double zoneStart = getZoneTempAtStart().getValue();
    double zoneNow = getZoneTemp().getValue();
    
    // THIS IS THE KEY: We record the duration (actualMinutes)
    // and the total temperature change achieved (deltaT).
    double deltaT_achieved = Math.abs(zoneNow - zoneStart);
    
    if (actualMinutes > 0.1 && deltaT_achieved > 0.1) {
        String mode = (zoneStart < getTargetZoneTempSetpoint().getValue()) ? "HEAT" : "COOL";
        double outdoorStart = getOutdoorTempAtStart().getStatus().isOk() ? getOutdoorTempAtStart().getValue() : Double.NaN;
        
        PerformanceRecord newRecord = new PerformanceRecord(
            System.currentTimeMillis(), 
            actualMinutes,  // t (duration)
            deltaT_achieved, // deltaT
            mode, 
            zoneStart, 
            outdoorStart
        );

        if ("HEAT".equals(mode)) {
            heatHistory.add(newRecord);
        } else {
            coolHistory.add(newRecord);
        }
        setFormattedStatusLog("[" + mode + "] run recorded (t=" + round1(actualMinutes) + ", dT=" + round1(deltaT_achieved) + ")");
        updateModel(); // Retune the model with the new data
    } else {
       setFormattedStatusLog("[Record] Run was too short or no temp change. Performance not recorded.");
    }
}

/**
 * Updates the learned performance model using LINEAR REGRESSION.
 * THIS IS THE NEW "BRAIN"
 */
private void updateModel() {
    pruneHistory();
    
    // --- 1. Tune Model 1 Parameters (Under the Hood) ---
    double[] heatAlphas = computeRegressionForMode("HEAT");
    double[] coolAlphas = computeRegressionForMode("COOL");
    
    // Store in private member variables
    this.learned_alpha_a_heat = heatAlphas[0]; // alpha_a
    this.learned_alpha_b_heat = heatAlphas[1]; // alpha_b
    this.learned_alpha_a_cool = coolAlphas[0]; // alpha_a
    this.learned_alpha_b_cool = coolAlphas[1]; // alpha_b

    // --- 2. Update EXISTING Reference Rate Slots (Visible) ---
    double avgHeatRate = computeAverageRate(heatHistory);
    double avgCoolRate = computeAverageRate(coolHistory);
    
    // Write to the slots that already exist
    setDegreesPerMinuteHeat(new BStatusNumeric(avgHeatRate > 0.0 ? avgHeatRate : DEFAULT_RATE_DEG_PER_MIN));
    setDegreesPerMinuteCool(new BStatusNumeric(avgCoolRate > 0.0 ? avgCoolRate : DEFAULT_RATE_DEG_PER_MIN));
    
    // --- 3. Logging ---
    if (getPrintToConsoleLog().getStatus().isOk() && getPrintToConsoleLog().getValue()) {
        System.out.println("--- [Model 1 Update] ---");
        System.out.println(String.format("HEAT Model: t = %.3f * (dT^2) + %.2f", this.learned_alpha_a_heat, this.learned_alpha_b_heat));
        System.out.println(String.format("COOL Model: t = %.3f * (dT^2) + %.2f", this.learned_alpha_a_cool, this.learned_alpha_b_cool));
        System.out.println(String.format("Writing to SLOT degreesPerMinuteHeat (Avg): %.3f", avgHeatRate));
        System.out.println(String.format("Writing to SLOT degreesPerMinuteCool (Avg): %.3f", avgCoolRate));
        System.out.println("-------------------------");
    }
    
    updateCurrentHistoryRecordCount();
    updateHistoryLog();
}

/**
 * Calculates and outputs the estimated time to reach setpoint when idle.
 * THIS IS MODIFIED to use the new quadratic model
 */
private void updateIdleEstimate() {
    if (getZoneAtTempTolerance().getValue()) {
        setMinutesToSetpoint(new BStatusNumeric(0.0));
        return;
    }
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk()) {
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double delta = Math.abs(target - zone);
    double maxMinutes = getMaxMinutesAllowed().getValue();
    double estimatedMinutes = maxMinutes;
    
    // --- THIS IS THE "FIX" ---
    // Use the quadratic equation from Model 1
    // t_opt = alpha_a * (delta^2) + alpha_b
    
    if (zone < target) { // Heating needed
        // Read from "under the hood" member variables
        double a_h = this.learned_alpha_a_heat;
        double b_h = this.learned_alpha_b_heat;
        estimatedMinutes = (a_h * (delta * delta)) + b_h;
        
    } else { // Cooling needed
        // Read from "under the hood" member variables
        double a_c = this.learned_alpha_a_cool;
        double b_c = this.learned_alpha_b_cool;
        estimatedMinutes = (a_c * (delta * delta)) + b_c;
    }
    // --- END OF THE "FIX" ---

    // Ensure estimated time is not negative and capped
    if (estimatedMinutes < 0) estimatedMinutes = 0.0;
    setMinutesToSetpoint(new BStatusNumeric(Math.min(estimatedMinutes, maxMinutes)));
}

//================================================================
// --- NEW: Regression and Rate Helpers ---
//================================================================

/**
 * Performs a Simple Linear Regression to find alpha_a and alpha_b.
 * Solves t = m*x + c, where:
 * y = t (durationMinutes)
 * x = deltaT^2
 * m = alpha_a
 * c = alpha_b
 * Returns [alpha_a, alpha_b]
 */
private double[] computeRegressionForMode(String mode) {
    java.util.List<PerformanceRecord> history = "HEAT".equals(mode) ? heatHistory : coolHistory;
    
    // Need at least 2 points to fit a line
    if (history.size() < 2) {
        return new double[] { DEFAULT_ALPHA_A, DEFAULT_ALPHA_B };
    }

    double n = history.size();
    double sum_x = 0, sum_y = 0, sum_xy = 0, sum_x_squared = 0;

    for (PerformanceRecord rec : history) {
        double x = rec.deltaT * rec.deltaT; // x = deltaT^2
        double y = rec.durationMinutes;     // y = t
        
        sum_x += x;
        sum_y += y;
        sum_xy += x * y;
        sum_x_squared += x * x;
    }

    double denominator = (n * sum_x_squared - sum_x * sum_x);
    
    // Avoid division by zero if all x values are the same
    if (Math.abs(denominator) < 0.001) {
        return new double[] { DEFAULT_ALPHA_A, DEFAULT_ALPHA_B };
    }

    // Calculate slope (alpha_a)
    double alpha_a = (n * sum_xy - sum_x * sum_y) / denominator;
    
    // Calculate intercept (alpha_b)
    double alpha_b = (sum_y - alpha_a * sum_x) / n;

    // Safety check: Don't allow negative parameters, as it makes no physical sense
    if (alpha_a < 0) alpha_a = DEFAULT_ALPHA_A;
    // A negative intercept (alpha_b) is physically possible (e.g., a time delay)
    // but we can cap it at 0.0 for safety.
    if (alpha_b < 0) alpha_b = 0.0; 

    return new double[] { alpha_a, alpha_b };
}

/**
 * Calculates the historical average rate (deg/min) for the reference slot.
 * Avg Rate = Total Degrees Changed / Total Minutes Run
 */
private double computeAverageRate(java.util.List<PerformanceRecord> history) {
    if (history.isEmpty()) {
        return 0.0;
    }
    
    double totalDeltaT = 0;
    double totalDuration = 0;
    
    for (PerformanceRecord rec : history) {
        totalDeltaT += rec.deltaT;
        totalDuration += rec.durationMinutes;
    }
    
    if (totalDuration < 0.01) {
        return 0.0; // Avoid division by zero
    }
    
    return totalDeltaT / totalDuration;
}


//================================================================
// --- Unchanged Helper and Utility Methods ---
//================================================================

private void setFormattedStatusLog(String message) {
    String lastTriggerTimeStr = "never";
    if (lastStartTriggerTimestamp > 0) {
        java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        lastTriggerTimeStr = sdf.format(new java.util.Date(lastStartTriggerTimestamp));
    }
    getStatusLog().setValue("[Last Trigger: " + lastTriggerTimeStr + "] " + message);
}

private void updateZoneAtTempTolerance() {
    if (!getZoneTemp().getStatus().isOk() || !getTargetZoneTempSetpoint().getStatus().isOk() || getTempTolerance().isNull()) {
        setZoneAtTempTolerance(new BStatusBoolean(false));
        return;
    }
    double zone = getZoneTemp().getValue();
    double target = getTargetZoneTempSetpoint().getValue();
    double tolerance = getTempTolerance().getValue();
    setZoneAtTempTolerance(new BStatusBoolean(Math.abs(zone - target) <= tolerance));
}

private void pruneHistory() {
    if (getHistoryDaysToRetain().isNull()) return;
    int maxRecords = (int) getHistoryDaysToRetain().getValue();
    while (heatHistory.size() > maxRecords) heatHistory.remove(0);
    while (coolHistory.size() > maxRecords) coolHistory.remove(0);
}

private void clearHistory() {
    heatHistory.clear();
    coolHistory.clear();
    updateModel();  
    setFormattedStatusLog("[History] All performance records have been cleared.");
}

/**
 * MODIFIED to log the new (t, deltaT) record format
 */
private void updateHistoryLog() {
    try {
        BStatusString historyLogSlot = (BStatusString)get("historyLog");
        if (historyLogSlot == null) return;
        StringBuilder sb = new StringBuilder();
        sb.append("--- HEAT History (t, dT) ---\n");
        if (heatHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : heatHistory) {
            sb.append(String.format("t: %.1f, dT: %.1f, ZS: %.1f, OAT: %s\n", r.durationMinutes, r.deltaT, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        sb.append("\n--- COOL History (t, dT) ---\n");
        if (coolHistory.isEmpty()) sb.append("No records.\n");
        for (PerformanceRecord r : coolHistory) {
            sb.append(String.format("t: %.1f, dT: %.1f, ZS: %.1f, OAT: %s\n", r.durationMinutes, r.deltaT, r.zoneTempStart, Double.isNaN(r.outdoorTempStart) ? "N/A" : String.valueOf(round1(r.outdoorTempStart))));
        }
        historyLogSlot.setValue(sb.toString());
    } catch (Exception e) {
        System.out.println("[ERROR] Failed to update historyLog slot: " + e.getMessage());
    }
}

private void updateCurrentHistoryRecordCount() {
    setCurrentHistoryRecordCount(new BStatusNumeric(heatHistory.size() + coolHistory.size()));
}

private void updateTimer() {
    if (ticket != null) ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(15), BProgram.execute, null);
}

private double round1(double v) {
    if (Double.isNaN(v)) return 0.0;
    return Math.round(v * 10.0) / 10.0;
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


---


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
