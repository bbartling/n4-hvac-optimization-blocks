# Niagara AX vs N4 Program Objects: Technical Comparison

This document compares **Niagara AX** and **Niagara 4 (N4)** `Program` objects from a practical development and commissioning perspective. It focuses on core differences for developers, integrators, and control engineers.

---

## 🔄 High-Level Comparison

| Feature / Behavior              | **Niagara AX (Java 1.4/1.5)**        | **Niagara 4 (Java 1.8+)**                      |
|--------------------------------|--------------------------------------|------------------------------------------------|
| Java Platform                  | Java 1.4 / 1.5                       | Java 1.8+ (e.g., N4.10+)                        |
| API / SDK                      | `com.tridium.sys.*`                 | `javax.baja.*` (BAJA 4)                         |
| Code Structure                 | Manual boilerplate                  | Auto-generated slot accessors, cleaner methods |
| Component Meta Model           | Static slot definitions             | Dynamic slot annotations, facets               |
| Memory / GC                    | Manual, tighter constraints         | More modern memory handling                    |
| Timer Logic                    | `Clock.schedule()` only             | `Clock.schedule()` + `executeOnChange`         |
| Development Workflow           | Slow compile, minimal feedback      | Syntax highlighting, better compile-time checks|
| Program Editor                 | Plain editor                        | Enhanced UI with debug, history, linting       |
| Debugging                      | Console/manual                      | Application Director, live logs                |
| Security Model                 | Basic certificate trust             | Signed modules, sandboxing                     |
| Serialization / Backup         | Simpler .bog                        | Robust JSON + metadata handling                |

---

## 🧠 Program Object Differences

### 1. Slot Access
- **AX:**
  ```java
  getIn1().getValue();
  getComponent().getLinks(getComponent().getSlot("in1"));
  ```
- **N4:**
  - Same access pattern, but supports helper annotations and improved validation.

---

### 2. Timer Logic
- **AX:**
  ```java
  Clock.schedule(getComponent(), BRelTime.makeSeconds(5), BProgram.execute, null);
  ```
- **N4:**
  - Same, but adds `executeOnChange` flag on slots for event-driven logic.

---

### 3. Deployment
- **AX:** Requires copying `.bog` files or direct in-station programming.
- **N4:** Supports module packaging, Git versioning, and Workbench-friendly imports.

---

### 4. Language Features
- **AX:** Java 1.4 → no generics, no lambdas, no streams.
- **N4:** Java 8 → modern syntax, `List<>`, lambdas, `Optional`, `Streams`.

---

### 5. Memory and Performance
- **AX:** Lower memory footprint but less resilient.
- **N4:** Larger but more fault-tolerant and optimized GC.

---

### 6. Debugging and Logs
- **AX:** Requires `System.out.println()` or viewing logs manually.
- **N4:** Has `Application Director` with structured logs, error traces, timestamps.

---

### 7. Security
- **AX:** Runs everything as trusted. Little to no sandboxing.
- **N4:** Modules must be signed. App sandboxing improves protection.

---

## ✅ Example Null Check in Both Platforms

```java
if (getComponent().getLinks(getComponent().getSlot("in1")).length == 0) {
    getIn1().setValue(0);
    getIn1().setStatus(BStatus.NULL);
}
```
> ✅ This works in both AX and N4, but in N4 you can wrap this as a helper for reuse.

---

## 🚀 Upgrade Summary
If you're upgrading from AX to N4:
- Your Program logic will mostly **port 1:1**
- Expect faster debugging, better code clarity, and safer deployment
- You can clean up your logic using Java 8 features and smarter timers

---

## Want More?
Ask for side-by-side examples (e.g., chiller staging, rolling averages) to compare AX vs N4 best practices.


## Adder tester

```java
Clock.Ticket ticket;

public void onStart() throws Exception {
    // Schedule the logic to run every 5 seconds
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(5), BProgram.execute, null);
}

public void onExecute() throws Exception {
    double sum = 0;
    int count = 0;

    // Handle in1
    if (getComponent().getLinks(getComponent().getSlot("in1")).length == 0) {
        getIn1().setValue(0);
        getIn1().setStatus(BStatus.NULL);
    } else if (getIn1().getStatus().isOk()) {
        sum += getIn1().getValue();
        count++;
    }

    // Handle in2
    if (getComponent().getLinks(getComponent().getSlot("in2")).length == 0) {
        getIn2().setValue(0);
        getIn2().setStatus(BStatus.NULL);
    } else if (getIn2().getStatus().isOk()) {
        sum += getIn2().getValue();
        count++;
    }

    // Output result
    getOut().setValue(sum);
    getWiredCount().setValue("Wired Inputs: " + count);
}

public void onStop() throws Exception {
    // Cancel the timer when the program stops
    if (ticket != null) {
        ticket.cancel();
    }
}

```