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
if (vavMax >= 90.0) {
    targetPress = Math.min(currentSP + trimIncrement, maxPress);
    getStatusTrace().setValue("Increase SP: VAV Max = " + round1(vavMax) + " → SP = " + round1(targetPress));
} else if (vavMax <= 80.0) {
    targetPress = Math.max(currentSP - trimIncrement, minPress);
    getStatusTrace().setValue("Decrease SP: VAV Max = " + round1(vavMax) + " → SP = " + round1(targetPress));
} else {
    getStatusTrace().setValue("Deadband... hold SP = " + round1(targetPress));
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
if (oat.getStatus().isOk() && oat.getValue() >= (getOutTempConstSatMinStp().getValue() + 1.0)) {
    targetSAT = minSAT;
    getStatusTrace().setValue("OA Temp high → lock to minSAT: " + round1(minSAT));
} else if (!fanOn) {
    targetSAT = startupSAT;
    getStatusTrace().setValue("Fan OFF → waiting for building startup... SP = " + round1(targetSAT));
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