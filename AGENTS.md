# AGENTS.md — Niagara Vibe Coding (Completed Code Output)

## 1. 🎯 Core Mission & Agent Contract

### 1.1 Agent Task (Your Goal)

Given:
- the Niagara auto-generated `ProgramImpl` structure,
- the available slot getter/setter methods,
- and the user task description,

you must produce a **paste-ready completed Program Source code block**.

The returned code must be:
- complete
- copy/paste ready
- self-contained
- not chunked
- not pseudo-code
- not partial

The user works inside Niagara where imports, class, and slots already exist.

You MUST generate:
- stateful fields
- full onStart()
- full onExecute()
- full onStop()
- helper methods
- constants

---

## 1.2 Required Output Format

Return exactly ONE fenced Java block.

It must include:
- fields
- full method headers + bodies
- helpers

NO:
- TODOs
- placeholders
- chunked output
- explanations between code

---

## 2. ❗ Core Directives

### 2.1 Always Return Completed Code

Default behavior:
👉 FULL Program Source

Only return partial snippets if explicitly requested.

---

### 2.2 Respect Niagara Boundaries

DO NOT generate:
- imports
- class declaration
- getters/setters

DO generate:
- fields
- lifecycle methods
- helpers

---

### 2.3 Copy/Paste First Design

Optimize for:
- direct paste into Workbench
- compile-ready logic
- no assembly required

---

### 2.4 Vibe-Coder Rule

When unsure:
👉 choose FULL implementation over explanation

---

## 3. 📤 Final Output Spec

Return:

```java
// full program source
```

Must include:
1. fields
2. onStart
3. onExecute
4. onStop
5. helpers

---

## 4. 🚫 Forbidden Outputs

- chunked code
- method-only bodies (unless asked)
- pseudo-code
- explanations replacing code
- incomplete logic

---

## 5. ✅ Success Criteria

A user should be able to:
1. Copy
2. Paste into Niagara ProgramObject
3. Run

WITHOUT modifying structure
