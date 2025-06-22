# open plc

Notes to make open PLC work
---

## 🧊 OpenPLC Structured Text Cheat Sheet: Chiller Staging Logic

This is a working example of how to stage a chiller using a TON (On-Delay Timer) block in **OpenPLC** using **Structured Text (ST)**. It demonstrates key differences between OpenPLC (MatIEC) and tools like Codesys.

---

### ✅ Final Working Program

```pascal
(* ---------- Chiller test logic ---------- *)

(* 1) Simulate cooling demand *)
CoolingDemand := RoomTemp > (Setpoint + 1.0);

(* 2) Ton-delay timer call *)
ChillerDelay( IN := CoolingDemand AND NOT ChillerOn,
              PT := DelayTime );

(* 3) Copy timer outputs to normal BOOL/TIME vars *)
ChillerDelay_Q  := ChillerDelay.Q;
ChillerDelay_ET := ChillerDelay.ET;

(* 4) Final chiller staging decision *)
IF CoolingDemand AND ChillerDelay_Q THEN
    ChillerOn := TRUE;
ELSIF NOT CoolingDemand THEN
    ChillerOn := FALSE;
END_IF;
```

---

### 🛠 Variable Table (Required)

You must define all of the following variables in the **OpenPLC Editor’s variable table**, not inside your code.

| Name              | Type | Initial Value | Notes                           |
| ----------------- | ---- | ------------- | ------------------------------- |
| `CoolingDemand`   | BOOL | FALSE         | Simulated logic condition       |
| `ChillerOn`       | BOOL | FALSE         | Final chiller output            |
| `ChillerDelay`    | TON  | —             | TON block instance              |
| `ChillerDelay_Q`  | BOOL | FALSE         | Output `Q` of timer             |
| `ChillerDelay_ET` | TIME | T#0s          | Output `ET` of timer (optional) |
| `Setpoint`        | REAL | `72.0` ✅      | Must have `.0`                  |
| `RoomTemp`        | REAL | `78.0` ✅      | Must have `.0`                  |
| `DelayTime`       | TIME | T#30s         | Delay before chiller stages     |

---

### ⚠ Key OpenPLC-Specific Rules (MatIEC Compiler)

#### 1. **Use `(* ... *)` for comments only**

* `//` and `/* ... */` are **not allowed**
* Valid: `(* This is a comment *)`

#### 2. **Do NOT include `VAR ... END_VAR` in ST code**

* OpenPLC auto-generates the variable block from the top table
* Including it manually causes **double declaration errors**

#### 3. **TON (and other FBs) must be called using output assignment**

* You **must call** `TON(...)` directly with inputs
* You **must separately access** `.Q` and `.ET` *after* the call

✅ Correct:

```pascal
ChillerDelay( IN := ..., PT := ... );
SomeBool := ChillerDelay.Q;
```

❌ Invalid (works in Codesys, but **not in OpenPLC**):

```pascal
ChillerDelay.IN := ...;        // ❌ Not allowed
TON(ChillerDelay);             // ❌ Not supported
```

#### 4. **REAL values must include a decimal**

* `72` is **invalid** for a `REAL`
* ✅ Use `72.0`, `78.5`, etc.

---

### 💡 Why This Is Different From Codesys

OpenPLC uses the [**MatIEC compiler**](https://github.com/thiagoralves/OpenPLC_v3/tree/master/webserver/core/matiec), which has stricter adherence to certain IEC 61131 rules and lacks some of the syntactic sugar supported by Codesys.

* Codesys allows block-style access like `Timer1.IN := TRUE` and `Timer1(…)` with outputs routed internally.
* OpenPLC does **not** allow dot-assignment for function block I/O. You must **assign outputs manually** into declared variables like `ChillerDelay_Q`.

---

### ✅ What You Learned

* How to properly use a `TON` block in OpenPLC ST
* Why variable declarations **must be in the table**
* Why `REAL` initial values need `.0`
* Why `(* ... *)` is the only accepted comment format
* Why OpenPLC is different from Codesys — and how to work with it

---


