# Demand‑Side Management

This brief sub‑guide gathers together the early work on **demand‑side management**, including an OpenADR 3.0 client stub and a conceptual intelligent load shedder inspired by PNNL research.  These sections are provided verbatim from the original README.

---

### ⚠️ **IMPORTANT — Best Practice for Exception Handling in ProgramObjects**

Whenever you build Niagara algorithm blocks, **always reference the fault-handling patterns** documented in:

- 👉 [`AGENTS.md`](AGENTS.md) — _Core agent loop patterns, safety rules, and how to use `BStatus.fault` as an exception channel._  
- 👉 [`README_BEGINNER_TUTORIALS.md`](README_BEGINNER_TUTORIALS.md) — _Hands-on intro to status-aware programming and safe ProgramObject design._

These documents show the **correct, Niagara-native method** for handling runtime exceptions using **point status**, not Java exceptions.  
In ProgramObjects, throwing errors will break the station thread — therefore the recommended technique is:

- Detect invalid / unwired / bad inputs  
- Set outputs to **`BStatus.fault`** or **`BStatus.nullStatus`**  
- Publish human-readable diagnostics via a `statusTrace` string  
- Continue running without crashing Workbench or the station

This pattern is the **official best practice** and may not be present in the advanced algorithm tutorials (optimal start, GL-36 logic, DSM, FDD, solar, schedule agents, etc.).

Always follow this model when developing new logic — it ensures consistent behavior, safe evaluation cycles, and clean debugging inside the station.

---

<details>
<summary>⚡ OpenADR 3.0 Client</summary>


* TODO Demand response client app
* https://github.com/OpenLEADR/openleadr-rs


</details>



<details>
<summary>🧠 Intelligent Load Shedder</summary>


* TODO Inspired from VOLTTRONs ILC Agent made by PNNL to shed loads inside buildings for demand side power management strategies.
* https://www.pnnl.gov/intelligent-load-control

</details>


