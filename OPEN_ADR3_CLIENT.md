# Demand‑Side Management

This sub‑guide gathers together early work on **Demand Response (DR)** and **demand‑side management** for Niagara 4 projects. The theme is simple:

> **The BAS block should just be a clean “signal handoff” layer** (OpenADR → Niagara points).  
> The HVAC controls technician can implement whatever internal optimization / load‑shed algorithm they want downstream.

---

<details>
<summary>⚡ OpenADR 3.0 Client — “VEN Signal Handoff” ProgramObject</summary>

## What this is

A Niagara 4 `ProgramObject` that behaves like a lightweight **OpenADR 3.0 VEN client**:

- Connects to an OpenADR 3.0 **VTN** (server) over HTTPS
- Subscribes (pull or webhook) to *events / pricing / dispatch instructions*
- Normalizes those messages into **simple numeric + boolean outputs** that a BAS controls tech can wire into AHU/VAV/plant logic

OpenADR 3.0 is modern web tech (HTTP + JSON + OAuth) and organizes DR offerings around **Programs** with **Events** linked by IDs. fileciteturn1file2L11-L26

---

## Why this pattern works for BAS

In real buildings, the hardest part is *not* the load shed logic — it’s getting a **reliable, testable, vendor‑agnostic signal** into the BAS.

This block is intentionally “boring”:

- **No embedded “magic energy algorithm”**
- **No assumptions** about equipment type, sequences, or site strategy
- Outputs a stable, repeatable slot map that can feed *any* downstream logic

Think: **OpenADR in → Niagara slots out**.

---

## Typical California DR / pricing signals this block should support

The names below are intentionally generic because utilities/programs vary. The point is to cover the common patterns you see in CA programs:

### 1) Fast DR dispatch (shed now / reduce quickly)
- “Start event at time X”
- “Shed level” (0–3 or 0–100%)
- Optional “ramp” instructions
- “End event at time Y”

### 2) Building kW limit window (capacity constraint)
- A **kW cap** for a given time window (e.g., 200 kW from 4–9 PM)
- Or a **kW reduction target** relative to baseline
- Optional “must not exceed” alarm if measured kW > cap

### 3) Day‑ahead / next‑day hourly price signal
- 24 hourly prices (or 96x 15‑min) for tomorrow
- Sometimes paired with a recommended operating mode (normal / conserve / pre‑cool)

### 4) Simple “mode” programs
- Grid emergency / Flex Alert style: *conserve energy now*
- CPP‑style critical price period (binary “critical” flag)
- Spinning reserve / reliability style “be ready” notification

---

## Architecture (recommended)

### Option A — Pull model (simplest)
Niagara block polls the VTN on a fixed interval (e.g., every 60s–300s):

1. GET programs (or use preconfigured program IDs)
2. GET active events for those programs
3. Update Niagara output slots

### Option B — Subscription / webhook model (best UX)
OpenADR 3.0 supports **push via subscription** (bi‑directional data exchange via webhook). fileciteturn1file2L21-L25  
In this approach:

- The VTN pushes event updates to a small HTTP endpoint.
- Niagara either:
  - hosts a tiny endpoint (not always ideal), or
  - talks to a companion “edge gateway” container that receives webhooks and forwards to Niagara (MQTT/HTTP).

> **Practical Niagara pattern:** Use a small Docker edge service for webhook + token management, then the `ProgramObject` only reads that edge service.

---

## Slot Map (recommended “handoff contract”)

These slots are designed so a controls tech can treat OpenADR like any other BAS “external supervisory input”.

### Core event timing + state

| Slot | Type | Notes |
|---|---:|---|
| `adrActive` | boolean | True when an ADR event is active |
| `adrEventType` | string | e.g., `"FAST_DR"`, `"KW_CAP"`, `"PRICE_DA"`, `"CPP"`, `"TEST"` |
| `adrProgramName` | string | Human‑readable program label |
| `adrEventId` | string | For audit / troubleshooting |
| `adrPriority` | number | If multiple programs overlap, higher wins (VTN can offer multiple programs). fileciteturn1file2L25-L26 |
| `adrStartEpochSec` | number | Start timestamp (epoch seconds) |
| `adrEndEpochSec` | number | End timestamp (epoch seconds) |
| `adrMinutesToStart` | number | Convenience output (>= 0) |
| `adrMinutesRemaining` | number | Convenience output (>= 0) |

### Dispatch signal (fast DR / generic shed)

| Slot | Type | Notes |
|---|---:|---|
| `adrShedLevel` | number | 0–100% (normalized). Controls tech chooses mapping (e.g., SAT reset, static reset, KW cap strategy). |
| `adrShedKwRequest` | number | Requested kW reduction (if provided) |
| `adrRampMinutes` | number | Optional ramp time (0 if not used) |

### kW limit window (capacity constraint)

| Slot | Type | Notes |
|---|---:|---|
| `adrKwCap` | number | “Do not exceed” cap during the window |
| `adrKwBaseline` | number | Optional baseline used by the VTN/utility |
| `adrKwExceed` | boolean | Convenience: measured kW > cap (if you wire in meter kW) |

### Day‑ahead pricing (next day)

| Slot | Type | Notes |
|---|---:|---|
| `priceSignalValid` | boolean | True when price schedule is loaded for “next day” |
| `priceTimezone` | string | e.g., `America/Los_Angeles` |
| `priceDayStartEpochSec` | number | Midnight start of the price day |
| `priceHour0to23` | 24 numbers | Price in $/kWh (or a normalized 0–1) |
| `priceNow` | number | Current price (computed from schedule + clock) |
| `priceNextHour` | number | Next hour price |

> **Implementation note:** Niagara doesn’t love array slots. A common pattern is `priceH00 ... priceH23` as 24 separate numeric slots.

### Health / diagnostics

| Slot | Type | Notes |
|---|---:|---|
| `enabled` | boolean | Master enable |
| `pollSeconds` | number | Polling interval for pull model |
| `lastUpdateEpochSec` | number | When data last refreshed |
| `commStatus` | string | `"OK"`, `"AUTH_FAIL"`, `"TIMEOUT"`, `"PARSE_ERROR"`, etc. |
| `rawJsonSnippet` | string | Last raw message excerpt for troubleshooting |

---

## Minimal OpenADR 3.0 workflow (conceptual)

OpenADR 3.0 organizes objects (Program, Event, Report, Subscription, VEN, Resource). fileciteturn1file2L27-L36  
A simple “get events” flow looks like:

1. **Get program(s)** (or use configured program IDs)
2. **Get events** filtered by programID
3. Pick the “active” event (or highest priority)
4. Write the normalized outputs above

The spec uses CRUD‑like APIs (GET/PUT/DELETE) to manage these objects. fileciteturn1file1L14-L16

---

## Companion implementation ideas (outside Niagara)

This repo is Niagara‑centric, but a practical architecture is to keep the actual OpenADR client in a small service:

- Rust: `openleadr-rs` (OpenLEADR project)
- Python/Node: a simple OpenADR 3 client + webhook receiver
- Then Niagara just reads a local REST endpoint / MQTT topic and updates the slots.

Why? OAuth token handling and webhook hosting is simply easier outside the JACE.

---

## Next TODOs for this repo

1. **Define the slot table in Workbench** for the contract above.
2. Add a tiny “simulator” input mode:
   - a manual `adrActive` toggle
   - a manual `adrShedLevel` knob
   - a manual `adrKwCap` value
   - a manual day‑ahead price schedule loader (CSV / JSON paste)
3. Add a starter `.bog` wiresheet showing:
   - ADR shed level driving a **SAT reset bias**
   - ADR kW cap driving a **fan speed limit**
   - price signal driving a **pre‑cool window** (start earlier if price spike expected)

---

## Java scaffold (ProgramObject / component)

Paste this into your Niagara module source. It implements the slot contract below and includes a demo JSON payload so you can wire/test immediately.

```java
/*
 * OpenADR 3.0 VEN Signal Handoff (Niagara 4 ProgramObject)
 * =======================================================
 * Purpose:
 *   - Connect to an OpenADR 3.0 VTN (server) and normalize DR signals into BAS-friendly slots.
 *   - DO NOT implement HVAC control logic here. This is a "signal handoff" block only.
 *
 * Notes:
 *   - This is a best-effort scaffold. You'll replace the HTTP/OAuth implementation with
 *     your Niagara-supported HTTP client and token handling.
 *   - Slot names match the README "handoff contract" so Workbench wiresheets stay stable.
 *
 * Typical CA Program Shapes this supports:
 *   1) FAST_DR (dispatch/shed now): adrShedLevel (0-100), optional ramp minutes
 *   2) KW_CAP (capacity cap window): adrKwCap, optional adrKwBaseline
 *   3) PRICE_DA (day-ahead pricing): priceH00..priceH23 + priceNow/priceNextHour
 */

package com.bbartling.dsm.openadr3;

import javax.baja.nre.annotations.NiagaraType;
import javax.baja.sys.BComponent;
import javax.baja.sys.BString;
import javax.baja.sys.BBoolean;
import javax.baja.sys.BInteger;
import javax.baja.sys.BDouble;
import javax.baja.sys.Sys;
import javax.baja.time.Clock;

/**
 * ProgramObject-style component that polls an OpenADR 3.0 server (or a local gateway)
 * and publishes the normalized ADR "handoff contract" as slots.
 */
@NiagaraType
public final class BOpenAdr3VenSignalHandoff extends BComponent
{
  /*+ ------------ BEGIN BAJA AUTO GENERATED CODE ------------ +*/
  /*@ $com.bbartling.dsm.openadr3.BOpenAdr3VenSignalHandoff(235634947)1.0$ @*/
  /* Generated by ChatGPT scaffold. */
  /*+ ------------ END BAJA AUTO GENERATED CODE -------------- +*/

  // --------------------------------------------------------------------------
  // CONFIG (inputs)
  // --------------------------------------------------------------------------

  /** Master enable for comms + slot updates. */
  public boolean getEnabled() { return ((BBoolean)get("enabled")).getBoolean(); }
  public void setEnabled(boolean v) { set("enabled", BBoolean.make(v)); }

  /** VTN base URL (e.g. https://vtn.example.com) OR local gateway URL (recommended). */
  public String getVtnBaseUrl() { return ((BString)get("vtnBaseUrl")).getString(); }
  public void setVtnBaseUrl(String v) { set("vtnBaseUrl", BString.make(v)); }

  /** Polling interval in seconds (pull model). Use 60–300 typically. */
  public int getPollSeconds() { return ((BInteger)get("pollSeconds")).getInt(); }
  public void setPollSeconds(int v) { set("pollSeconds", BInteger.make(v)); }

  /** OAuth client id (if used). */
  public String getOauthClientId() { return ((BString)get("oauthClientId")).getString(); }
  public void setOauthClientId(String v) { set("oauthClientId", BString.make(v)); }

  /** OAuth client secret (if used). Store securely in real deployment. */
  public String getOauthClientSecret() { return ((BString)get("oauthClientSecret")).getString(); }
  public void setOauthClientSecret(String v) { set("oauthClientSecret", BString.make(v)); }

  /** Comma-separated list of program IDs (optional). */
  public String getProgramIdsCsv() { return ((BString)get("programIdsCsv")).getString(); }
  public void setProgramIdsCsv(String v) { set("programIdsCsv", BString.make(v)); }

  /** If true, keep last good values when comms fail; if false, reset outputs on error. */
  public boolean getHoldLastGoodOnError() { return ((BBoolean)get("holdLastGoodOnError")).getBoolean(); }
  public void setHoldLastGoodOnError(boolean v) { set("holdLastGoodOnError", BBoolean.make(v)); }

  // --------------------------------------------------------------------------
  // OUTPUTS (the BAS "handoff contract")
  // --------------------------------------------------------------------------

  // Core event
  public boolean getAdrActive() { return ((BBoolean)get("adrActive")).getBoolean(); }
  private void setAdrActive(boolean v) { set("adrActive", BBoolean.make(v)); }

  public String getAdrEventType() { return ((BString)get("adrEventType")).getString(); }
  private void setAdrEventType(String v) { set("adrEventType", BString.make(nullToEmpty(v))); }

  public String getAdrProgramName() { return ((BString)get("adrProgramName")).getString(); }
  private void setAdrProgramName(String v) { set("adrProgramName", BString.make(nullToEmpty(v))); }

  public String getAdrEventId() { return ((BString)get("adrEventId")).getString(); }
  private void setAdrEventId(String v) { set("adrEventId", BString.make(nullToEmpty(v))); }

  public double getAdrPriority() { return ((BDouble)get("adrPriority")).getDouble(); }
  private void setAdrPriority(double v) { set("adrPriority", BDouble.make(v)); }

  public double getAdrStartEpochSec() { return ((BDouble)get("adrStartEpochSec")).getDouble(); }
  private void setAdrStartEpochSec(double v) { set("adrStartEpochSec", BDouble.make(v)); }

  public double getAdrEndEpochSec() { return ((BDouble)get("adrEndEpochSec")).getDouble(); }
  private void setAdrEndEpochSec(double v) { set("adrEndEpochSec", BDouble.make(v)); }

  public double getAdrMinutesToStart() { return ((BDouble)get("adrMinutesToStart")).getDouble(); }
  private void setAdrMinutesToStart(double v) { set("adrMinutesToStart", BDouble.make(v)); }

  public double getAdrMinutesRemaining() { return ((BDouble)get("adrMinutesRemaining")).getDouble(); }
  private void setAdrMinutesRemaining(double v) { set("adrMinutesRemaining", BDouble.make(v)); }

  // Dispatch
  public double getAdrShedLevel() { return ((BDouble)get("adrShedLevel")).getDouble(); }
  private void setAdrShedLevel(double v) { set("adrShedLevel", BDouble.make(clamp(v, 0.0, 100.0))); }

  public double getAdrShedKwRequest() { return ((BDouble)get("adrShedKwRequest")).getDouble(); }
  private void setAdrShedKwRequest(double v) { set("adrShedKwRequest", BDouble.make(v)); }

  public double getAdrRampMinutes() { return ((BDouble)get("adrRampMinutes")).getDouble(); }
  private void setAdrRampMinutes(double v) { set("adrRampMinutes", BDouble.make(Math.max(0.0, v))); }

  // kW cap
  public double getAdrKwCap() { return ((BDouble)get("adrKwCap")).getDouble(); }
  private void setAdrKwCap(double v) { set("adrKwCap", BDouble.make(v)); }

  public double getAdrKwBaseline() { return ((BDouble)get("adrKwBaseline")).getDouble(); }
  private void setAdrKwBaseline(double v) { set("adrKwBaseline", BDouble.make(v)); }

  public boolean getAdrKwExceed() { return ((BBoolean)get("adrKwExceed")).getBoolean(); }
  private void setAdrKwExceed(boolean v) { set("adrKwExceed", BBoolean.make(v)); }

  // Pricing (H00..H23)
  public boolean getPriceSignalValid() { return ((BBoolean)get("priceSignalValid")).getBoolean(); }
  private void setPriceSignalValid(boolean v) { set("priceSignalValid", BBoolean.make(v)); }

  public String getPriceTimezone() { return ((BString)get("priceTimezone")).getString(); }
  private void setPriceTimezone(String v) { set("priceTimezone", BString.make(nullToEmpty(v))); }

  public double getPriceDayStartEpochSec() { return ((BDouble)get("priceDayStartEpochSec")).getDouble(); }
  private void setPriceDayStartEpochSec(double v) { set("priceDayStartEpochSec", BDouble.make(v)); }

  public double getPriceNow() { return ((BDouble)get("priceNow")).getDouble(); }
  private void setPriceNow(double v) { set("priceNow", BDouble.make(v)); }

  public double getPriceNextHour() { return ((BDouble)get("priceNextHour")).getDouble(); }
  private void setPriceNextHour(double v) { set("priceNextHour", BDouble.make(v)); }

  // Health
  public double getLastUpdateEpochSec() { return ((BDouble)get("lastUpdateEpochSec")).getDouble(); }
  private void setLastUpdateEpochSec(double v) { set("lastUpdateEpochSec", BDouble.make(v)); }

  public String getCommStatus() { return ((BString)get("commStatus")).getString(); }
  private void setCommStatus(String v) { set("commStatus", BString.make(nullToEmpty(v))); }

  public String getRawJsonSnippet() { return ((BString)get("rawJsonSnippet")).getString(); }
  private void setRawJsonSnippet(String v) { set("rawJsonSnippet", BString.make(trunc(nullToEmpty(v), 2000))); }

  // price hour slots (24 separate doubles)
  private void setPriceHour(int hour0to23, double v)
  {
    String slot = String.format("priceH%02d", hour0to23);
    set(slot, BDouble.make(v));
  }

  // --------------------------------------------------------------------------
  // RUNTIME
  // --------------------------------------------------------------------------

  private volatile long lastPollMs = 0L;

  @Override
  public void started()
  {
    super.started();
    setCommStatus("OK: started");
  }

  /**
   * Call this from an interval timer (or a ProgramObject onExecute wrapper),
   * or wire it to a kitControl schedule tick.
   */
  public void tick()
  {
    if (!getEnabled())
      return;

    long now = Sys.millis();
    int pollSec = getPollSeconds();
    if (pollSec <= 0) pollSec = 60;

    if ((now - lastPollMs) < (pollSec * 1000L))
      return;

    lastPollMs = now;

    try
    {
      // Replace this with real OpenADR 3.0 polling / subscription state.
      // Recommended practice: point this component at a LOCAL gateway URL
      // that already handles OAuth + webhook subscription, and returns a single JSON doc.

      String json = fakeGatewayResponseForDemo(); // TODO replace
      setRawJsonSnippet(json);

      AdrPayload p = AdrPayload.parse(json);

      // Apply to slots
      applyPayload(p);

      setLastUpdateEpochSec(now / 1000.0);
      setCommStatus("OK");
    }
    catch (Exception ex)
    {
      setCommStatus("ERR: " + ex.getMessage());

      if (!getHoldLastGoodOnError())
        resetOutputsToSafeDefaults();
    }
  }

  private void applyPayload(AdrPayload p)
  {
    // Core event
    setAdrActive(p.adrActive);
    setAdrEventType(p.adrEventType);
    setAdrProgramName(p.adrProgramName);
    setAdrEventId(p.adrEventId);
    setAdrPriority(p.adrPriority);
    setAdrStartEpochSec(p.adrStartEpochSec);
    setAdrEndEpochSec(p.adrEndEpochSec);

    // Convenience timing
    double nowSec = Sys.millis() / 1000.0;
    setAdrMinutesToStart(Math.max(0.0, (p.adrStartEpochSec - nowSec) / 60.0));
    setAdrMinutesRemaining(Math.max(0.0, (p.adrEndEpochSec - nowSec) / 60.0));

    // Dispatch / caps
    setAdrShedLevel(p.adrShedLevel);
    setAdrShedKwRequest(p.adrShedKwRequest);
    setAdrRampMinutes(p.adrRampMinutes);

    setAdrKwCap(p.adrKwCap);
    setAdrKwBaseline(p.adrKwBaseline);

    // Pricing
    setPriceSignalValid(p.priceSignalValid);
    setPriceTimezone(p.priceTimezone);
    setPriceDayStartEpochSec(p.priceDayStartEpochSec);

    for (int i = 0; i < 24; i++)
      setPriceHour(i, p.priceH[i]);

    // priceNow/nextHour (simple)
    int hr = currentHourLocal();
    setPriceNow(p.priceH[clampInt(hr, 0, 23)]);
    setPriceNextHour(p.priceH[clampInt(hr + 1, 0, 23)]);
  }

  private void resetOutputsToSafeDefaults()
  {
    setAdrActive(false);
    setAdrEventType("");
    setAdrProgramName("");
    setAdrEventId("");
    setAdrPriority(0.0);
    setAdrStartEpochSec(0.0);
    setAdrEndEpochSec(0.0);
    setAdrMinutesToStart(0.0);
    setAdrMinutesRemaining(0.0);

    setAdrShedLevel(0.0);
    setAdrShedKwRequest(0.0);
    setAdrRampMinutes(0.0);

    setAdrKwCap(0.0);
    setAdrKwBaseline(0.0);
    setAdrKwExceed(false);

    setPriceSignalValid(false);
    setPriceTimezone("");
    setPriceDayStartEpochSec(0.0);
    for (int i = 0; i < 24; i++) setPriceHour(i, 0.0);
    setPriceNow(0.0);
    setPriceNextHour(0.0);

    setLastUpdateEpochSec(0.0);
    setRawJsonSnippet("");
  }

  // --------------------------------------------------------------------------
  // DEMO JSON + PARSER (keep tiny; replace with real JSON library in module)
  // --------------------------------------------------------------------------

  /**
   * This is a deliberately simple "gateway JSON" shape:
   *   - One payload that already picked the "winning" event (priority resolved).
   *   - One next-day price schedule.
   *
   * In real life the OpenADR 3.0 gateway does:
   *   - OAuth, subscriptions/webhooks, program/event discovery, priority resolution, retries, logging.
   */
  private static String fakeGatewayResponseForDemo()
  {
    // Example: active FAST_DR with shed level, plus next-day prices.
    return "{"
      + "\"adrActive\":true,"
      + "\"adrEventType\":\"FAST_DR\","
      + "\"adrProgramName\":\"CA_FAST_DR\","
      + "\"adrEventId\":\"evt-123\","
      + "\"adrPriority\":10,"
      + "\"adrStartEpochSec\":" + ((Sys.millis()/1000L) - 60) + ","
      + "\"adrEndEpochSec\":" + ((Sys.millis()/1000L) + 3600) + ","
      + "\"adrShedLevel\":35.0,"
      + "\"adrShedKwRequest\":0.0,"
      + "\"adrRampMinutes\":10.0,"
      + "\"adrKwCap\":0.0,"
      + "\"adrKwBaseline\":0.0,"
      + "\"priceSignalValid\":true,"
      + "\"priceTimezone\":\"America/Los_Angeles\","
      + "\"priceDayStartEpochSec\":" + ((Sys.millis()/1000L) - 3600) + ","
      + "\"priceH\":[0.12,0.12,0.11,0.11,0.11,0.12,0.14,0.18,0.22,0.24,0.25,0.24,0.22,0.20,0.19,0.21,0.28,0.35,0.42,0.39,0.30,0.22,0.18,0.15]"
      + "}";
  }

  private static final class AdrPayload
  {
    boolean adrActive;
    String  adrEventType;
    String  adrProgramName;
    String  adrEventId;
    double  adrPriority;
    double  adrStartEpochSec;
    double  adrEndEpochSec;

    double  adrShedLevel;
    double  adrShedKwRequest;
    double  adrRampMinutes;

    double  adrKwCap;
    double  adrKwBaseline;

    boolean priceSignalValid;
    String  priceTimezone;
    double  priceDayStartEpochSec;
    double[] priceH = new double[24];

    static AdrPayload parse(String json)
    {
      // Minimal "good enough" parser for demo. Replace with real JSON parser in module.
      AdrPayload p = new AdrPayload();
      p.adrActive = getBool(json, "adrActive", false);
      p.adrEventType = getStr(json, "adrEventType", "");
      p.adrProgramName = getStr(json, "adrProgramName", "");
      p.adrEventId = getStr(json, "adrEventId", "");
      p.adrPriority = getNum(json, "adrPriority", 0.0);
      p.adrStartEpochSec = getNum(json, "adrStartEpochSec", 0.0);
      p.adrEndEpochSec = getNum(json, "adrEndEpochSec", 0.0);

      p.adrShedLevel = getNum(json, "adrShedLevel", 0.0);
      p.adrShedKwRequest = getNum(json, "adrShedKwRequest", 0.0);
      p.adrRampMinutes = getNum(json, "adrRampMinutes", 0.0);

      p.adrKwCap = getNum(json, "adrKwCap", 0.0);
      p.adrKwBaseline = getNum(json, "adrKwBaseline", 0.0);

      p.priceSignalValid = getBool(json, "priceSignalValid", false);
      p.priceTimezone = getStr(json, "priceTimezone", "");
      p.priceDayStartEpochSec = getNum(json, "priceDayStartEpochSec", 0.0);

      double[] arr = getNumArray24(json, "priceH");
      if (arr != null) p.priceH = arr;

      return p;
    }

    private static boolean getBool(String json, String key, boolean def)
    {
      String pat = "\"" + key + "\":";
      int i = json.indexOf(pat);
      if (i < 0) return def;
      int j = i + pat.length();
      String tail = json.substring(j).trim();
      if (tail.startsWith("true")) return true;
      if (tail.startsWith("false")) return false;
      return def;
    }

    private static String getStr(String json, String key, String def)
    {
      String pat = "\"" + key + "\":\"";
      int i = json.indexOf(pat);
      if (i < 0) return def;
      int j = i + pat.length();
      int k = json.indexOf('"', j);
      if (k < 0) return def;
      return json.substring(j, k);
    }

    private static double getNum(String json, String key, double def)
    {
      String pat = "\"" + key + "\":";
      int i = json.indexOf(pat);
      if (i < 0) return def;
      int j = i + pat.length();
      int k = j;
      while (k < json.length())
      {
        char c = json.charAt(k);
        if (!(Character.isDigit(c) || c=='-' || c=='.' || c=='e' || c=='E' || c=='+')) break;
        k++;
      }
      String s = json.substring(j, k).trim();
      if (s.isEmpty()) return def;
      try { return Double.parseDouble(s); } catch (Exception ex) { return def; }
    }

    private static double[] getNumArray24(String json, String key)
    {
      String pat = "\"" + key + "\":[";
      int i = json.indexOf(pat);
      if (i < 0) return null;
      int j = i + pat.length();
      int k = json.indexOf(']', j);
      if (k < 0) return null;
      String body = json.substring(j, k).trim();
      String[] parts = body.split(",");
      if (parts.length < 24) return null;
      double[] out = new double[24];
      for (int idx = 0; idx < 24; idx++)
      {
        try { out[idx] = Double.parseDouble(parts[idx].trim()); }
        catch (Exception ex) { out[idx] = 0.0; }
      }
      return out;
    }
  }

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------

  private static String nullToEmpty(String s) { return s == null ? "" : s; }

  private static String trunc(String s, int maxLen)
  {
    if (s == null) return "";
    if (s.length() <= maxLen) return s;
    return s.substring(0, maxLen);
  }

  private static double clamp(double v, double lo, double hi)
  {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
  }

  private static int clampInt(int v, int lo, int hi)
  {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
  }

  private static int currentHourLocal()
  {
    // Niagara station time hour (best effort)
    try
    {
      String t = Clock.clock().time().toString(); // "YYYY-MM-DDThh:mm:ss..."
      int th = t.indexOf('T');
      if (th >= 0 && t.length() >= th + 3)
        return Integer.parseInt(t.substring(th + 1, th + 3));
    }
    catch (Exception ignore) {}
    // fallback
    return 0;
  }
}

```

</details>



<details>
<summary>🧠 Intelligent Load Shedder — (future) “ILC‑style” supervisory coordinator</summary>

This is a placeholder for a higher‑level **Intelligent Load Control (ILC)** / load shedding coordinator inspired by PNNL work. fileciteturn1file0L19-L25

The long‑term idea:

- Consume the normalized OpenADR slots above
- Observe building state (meter kW, zone comfort, plant availability)
- Choose a load shed action plan (staged, reversible, safety‑aware)
- Emit **simple downstream commands** (e.g., static reset bias, SAT reset bias, max VFD %, chilled water SP bias, etc.)

This should be implemented as **a separate block** from the OpenADR client to keep responsibilities clean.

</details>
