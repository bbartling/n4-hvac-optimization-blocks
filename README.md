# niagara4-vibe-code-addict

![Leave Temp Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/vibecoder.png)


This repository provides ready-to-use **Java algorithm blocks for Niagara 4 `ProgramObjects`** (as `.bog` files) and this **README** itself, which serves as a *model context file* for Large Language Models (LLMs) such as ChatGPT or Gemini. Think of it as *the instruction manual the LLM reads before it writes code for you.*

> Ben is actively deploying and testing these `ProgramObjects` in the field, most notably the Guideline 36 algorithms, chiller demand-based start, and Optimal Start blocks built on PNNL’s latest research for energy-efficiency projects.


Also, feel free to skip the tutorials entirely and jump right into the [**Prebuilt Wiresheet Examples (.bog file format)**](https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/bog_files) for everything shown below.


---

<details>
<summary>⚙️ How to Use with AI</summary>

1. **Download this `README.md` file** directly from GitHub.  
2. **Open your LLM chat** (e.g., ChatGPT, Gemini, etc.).
3. **Upload the `README.md` file** from your downloads folder on your computer along with your idea in mind to try.  

   > Example in LLM Chat: “See this README — I want a ProgramObject that automates my chiller plant with rocket science. 🚀🤭”

4. Once the LLM confirms it understands the README, have it generate or edit your Niagara 4 `ProgramObject` code.
5. Paste the resulting Java code into Workbench’s Program Editor, make your slots for your block, and compile in the `ProgramObject` editor view.
6. **Screenshot any compile errors** using the Windows Snipping Tool and send them back into the LLM chat for review.
7. **Repeat as needed.**  ♻️ If the LLM starts generating bogus code (Gemini sometimes forgets that `ProgramObject` auto-handle imports), just remind it that Workbench generates those automatically and to reference the `README.md` file again!
8. **Simulate and test** ♻️ the logic thoroughly in your desktop office type enivornment.  When your `ProgramObject` behaves as expected, export the `.bog` file. ⚠️ **Important** ⚠️ Monitor the Application Director in Workbench for any errors.
9. **Import the tested Wiresheet** as the .bog containing the `ProgramObject` into the JACE for live field deployment.
10. Finally, **monitor JACE resources** ⚠️ **Important** ⚠️ See the section below JACE Resource Management – Best Practices for guidance on ensuring the JACE has sufficient free heap memory and acceptable CPU usage.

</details>

---

<details>
<summary>🧠 LLM Model Context Full</summary>

AI/LLM's section to read...not required by the human. This section provides a guide for interacting with AI and LLMs (like ChatGPT) to generate **Niagara 4 Program Object** Java code *safely and correctly*.

Niagara Workbench **auto-generates** important pieces of the Program Object code — do not generate or modify them manually.

Default imports are automatic, special packages for networking, I/O, or advanced scheduling (like java.net, java.io, java.time, or javax.baja.schedule) MUST be added manually to the Program Object's Imports tab. Snips are available to the human for reference this.

---

### **Key Rules for LLM and Human Collaboration**

#### **❌ Do Not Generate or Modify These**

> **LLMs must NOT generate:**
> * Do not insert emoji into code as it will error out the compiling process.
> * Class header and imports.
> * `public class ProgramImpl extends ProgramBase`.
> * Auto-generated slot getter and setter methods.
> * `/* Auto-generated ProgramImpl Code */` sections.

These are **automatically handled** by **Niagara Workbench** — no need to manually import or build the class boilerplate!

**Workbench generates this structure for you**:

```java
/* Auto-generated ProgramImpl Code */

import java.util.*;
import javax.baja.sys.*;
import javax.baja.status.*;
import com.tridium.program.*;

public class ProgramImpl extends ProgramBase {
  
  public void onStart() throws Exception {
    // startup code
  }

  public void onExecute() throws Exception {
    // execute code
  }

  public void onStop() throws Exception {
    // shutdown code
  }
}
```

On the Program Object’s Source tab (the auto-generated code base), the import statements—if configured correctly—should look similar to the example below. You can ask the human to show you the auto-generated source code (which cannot be modified) to verify that any required external packages or modules have been properly included.
```java
/* Auto-generated ProgramImpl Code */

import java.util.*;              /* java Predefined*/
import javax.baja.nre.util.*;    /* nre Predefined*/
import javax.baja.sys.*;         /* baja Predefined*/
import javax.baja.status.*;      /* baja Predefined*/
import javax.baja.util.*;        /* baja Predefined*/
import com.tridium.program.*;    /* program-rt Predefined*/
import javax.baja.schedule.*;    /* schedule-rt User Defined*/
import javax.baja.naming.*;      /* baja By Property*/

public class ProgramImpl
  extends com.tridium.program.ProgramBase
{
```

These are the methods that the human can modify only through AI-generated code. Adding packages and modules is done separately on the Imports tab of the Program Object, not programmatically within the source code.

```java
public void onStart() throws Exception
{
  // start up code here
}

public void onExecute() throws Exception
{
  // execute code (set executeOnChange flag on inputs)
}

public void onStop() throws Exception
{
  // shutdown code here
}

```

### When Additional Niagara Modules Are Needed in Program Objects

A **Program Object** runs in Niagara’s sandbox (“program-rt”), which only exposes safe core APIs (`javax.baja.sys`, `javax.baja.status`, `javax.baja.util`, etc.).
You must **add or require extra modules** when you reference classes outside this default set.

#### When a plain Program Object is enough

* You only use built-in Baja types (e.g., `BStatusNumeric`, `BDateTime`, `BBoolean`).
* You only call Java core packages like `java.net.*` or `java.util.*`.
* You work with Niagara components already on the station (e.g., schedules, points).
* You’re fine with limited privileges (no file I/O, threads, or external JARs).

#### When to add a module dependency

* You use types from another module (e.g., `javax.baja.schedule.*` → **schedule-rt**).
* You call APIs that aren’t whitelisted in program-rt.
* You want palette components, background threads, or long-running tasks.
* You depend on 3rd-party libraries (JSON, iCal, OAuth, MQTT, etc.).
* You need higher permissions, signed code, or access to histories/alarms.

#### Common module examples

| Purpose                        | Module Required                 |
| ------------------------------ | ------------------------------- |
| Calendar & schedules           | `schedule-rt`                   |
| Histories & trends             | `history-rt`                    |
| Alarms                         | `alarm-rt`                      |
| Weather & web calls            | `inet-rt`                       |
| BACnet / Modbus types          | Corresponding driver module     |
| JSON / XML parsing beyond core | Custom module with embedded JAR |

#### Rule of thumb

* **Small glue logic + existing modules → Program Object**
* **Anything needing new APIs, libraries, or long-lived behavior → Custom Module**

---

### **✅ What You *Can* Ask LLMs to Generate**

> **Only generate code inside:**
>
> * `onStart()`
> * `onExecute()`
> * `onStop()`
> * Small helper methods (at the class level)

**⚠️ Reminder:**

* Java does **NOT** allow nested methods.
* **Helper functions (like `addIfWired()`) must be at class level**, not inside `onExecute()`.

**Example of what NOT to do** — ❌ **Incorrect**

```java
public void onExecute() throws Exception {
  // this is invalid: 
  double addIfWired(BStatusNumeric input) { 
    ...
  }
}
```

**Correct** — ✅ **Move helper outside**

```java
// Class-level helper
int addIfWired(BStatusNumeric input) {
  if (input.getStatus().isOk()) {
    sum += input.getValue();
    return 1;
  }
  return 0;
}
```

---

### **Internal Timers in Niagara Program Objects**

> **Use Clock.schedule() with a BRelTime object inside a helper method.**

**Example (Correct Timer Logic):**

```java
Clock.Ticket ticket;

void updateTimer() {            
  if (ticket != null) {
    ticket.cancel();
  }  
  // Hardcoded 10-second update interval
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}
```

🚫 **Do NOT** expose a writable `executePeriod` slot unless truly necessary —
Just schedule internal periodic execution using `Clock.schedule()` directly!

---

### **Common Mistakes to Avoid**

| Mistake                              | Correction                                                                 |
| ------------------------------------ | -------------------------------------------------------------------------- |
| Generating class headers/imports     | ❌ Leave this to Workbench.                                                 |
| Writing slot getters/setters         | ❌ Workbench auto-generates them based on slot definitions.                 |
| Nesting helper methods               | ❌ Java doesn't allow methods inside methods — move helpers to class level. |
| Generating update intervals as slots | ❌ Hardcode your `BRelTime` interval unless you need configurable timing.   |

---

### **When Humans Provide Slot Names**

If the human provides slot names:

* Use them exactly.
* Access them via `getSlotName()`, e.g., `getIn1().getValue()`.

If no names are provided:

* LLM should propose **reasonable slot names** and show a table.

---

### **Example Slot Table if No Names Provided**

| Slot Name      | Type           | Writable | Description           |
| -------------- | -------------- | -------- | --------------------- |
| `in1`          | BStatusNumeric | Yes      | First numeric input   |
| `in2`          | BStatusNumeric | Yes      | Second numeric input  |
| `outAvg`       | BStatusNumeric | No       | Average value output  |
| `wiredInCount` | BStatusString  | No       | Count of wired inputs |

---

### **How to Work With LLMs**

1. Only paste **method bodies** (`onStart`, `onExecute`, `onStop`) into Workbench.
2. **Compile** the Program Object.
3. **If errors occur:**

   * Screenshot the **error** and **slot sheet**.
   * Share it back with the LLM for correction.

⚡ **Quick Debug Tip:**
Most compile errors come from:

* Slot names mismatching.
* Wrong assumptions about slot types or missing getter methods.

---

### **Good Example Output (Correct)**

```java
public void onStart() throws Exception {
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();
    
    sum = 0;
    int wiredCount = 0;

    wiredCount += addIfWired(getIn1());
    wiredCount += addIfWired(getIn2());
    
    getOut().setValue(sum);
    getWiredInCount().setValue("Wired Inputs: " + wiredCount);
}

public void onStop() throws Exception {
    if (ticket != null) {
        ticket.cancel();
    }
}

// ✅ Class-level helper function
int addIfWired(BStatusNumeric input) {
    if (input.getStatus().isOk()) {
        sum += input.getValue();
        return 1;
    }
    return 0;
}
```

---

### **Summary**

> **LLMs:**
>
> * ✅ Only generate *method* code (no imports/class headers).
> * ✅ Keep helper functions *outside* methods.
> * ✅ Use internal `Clock.schedule()` hardcoded intervals unless told otherwise.
>
> **Humans:**
>
> * ✅ Use Workbench to compile.
> * ✅ Screenshot and debug slot sheet + errors if issues arise.

</details>

---

## 📂 Additional Guides

To keep this README concise, the detailed tutorials and algorithm implementations have been moved into separate sub‑guides.  Use the links below to navigate to the appropriate document:

- [**Tutorials & Algorithms**](README_TUTORIALS_ALGORITHMS.md) — step‑by‑step examples and general algorithm blocks.
- [**GL36 Air Side Trim & Respond**](README_TRIM_RESPOND.md) — variable definitions tutorial, VAV box requests, and trim‑respond resets.
- [**GL36 Central Plant & AHU FDD**](README_GL36.md) — chiller plant enable logic, AHU fault detection, and other GL36‑compliant strategies.
- [**Non‑GL36 & Advanced Logic**](README_NON_GL36.md) — simplified resets and per‑chiller rotator for systems outside Guideline 36.
- [**APIs & Web Requests**](README_APIS.md) — examples for calling weather, holiday and iCalendar APIs or integrating external ML models.
- [**Optimal Start Algorithms**](README_OPT_START.md) — adaptive-tuning optimal start algorithms based on PNNL research, incorporating both the linear degree-per-minute model and polynomial regression.
- [**Demand‑Side Management**](README_DEMAND_SIDE_MANAGEMENT.md) — OpenADR client and PNNL‑inspired intelligent load shedding.
- [**Niagara AX Notes**](NIAGARA_AX_NOTES.md) — notes on creating `ProgramObjects` in legacy Niagara AX (earlier Java-based versions).

## 🔄 Future Plans

Someday future plans may include building a **full Niagara 4 module** for **ASHRAE Guideline 36 AHU Trim Respond**, **GL36 AHU Fault Detection**, and **Optimal Start** based off of lessons learned from implementation of these `ProgramObejcts` in the field — Stay Tuned! 🙌

Check for demonstrations on Vibe Coding on 📺
🎥 [**Talk Shop With Ben on YouTube**](https://www.youtube.com/@TalkShopWithBen)


## 💛 Support This Work

I’ve personally never donated to open-source software before — but hey, what the heck! If this project helped you build something neat or saved you at least 10× the man-hours on your Niagara BAS project with the help of AI and model context like this, and AND you’re feeling generous today, your support directly fuels Ben’s bad habits at Starbucks — but there’s absolutely no pressure.

| 💵 Option           | Link                                                                                                                                                                                                                                              |
| :------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 💖 **$20 fixed**    | [Donate $20](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&amount=20&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD) |
| ✨ **Custom amount** | [Choose any amount](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD)    |


[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD)


## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.