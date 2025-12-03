# ☀️ Solar Position & Astronomical Clock

This Program Object acts as a mathematically precise **Astronomical Clock**. Instead of relying on internet weather services or physical photocells (which get dirty, covered in snow, or break), this block uses the JACE's internal clock and site coordinates (Latitude/Longitude) to calculate the exact position of the sun.

It runs entirely **offline** and provides the two critical data points needed for advanced HVAC and lighting control:

1.  **Azimuth:** The compass direction of the sun (0° N, 90° E, 180° S, 270° W).
2.  **Elevation:** How high the sun is in the sky (0° = horizon, 90° = directly overhead).

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

## 🧠 Why use this on a BAS?

### 1\. Automated Shade & Blind Control

[Image of solar azimuth vs elevation diagram]

Standard "sun sensors" only tell you if it's bright. This block tells you **where** the sun is.

  * **Glare Control:** If Elevation is low (\< 25°) and Azimuth aligns with a window, force blinds closed to prevent glare on computer screens.
  * **View Maximization:** Once the sun passes a façade (e.g., moves to the West), automatically open East-facing blinds to give occupants a view.

### 2\. Passive Solar & HVAC "Feed-Forward"

[Image of passive solar building design diagram]

Thermostats are reactive; this logic is proactive.

  * **Morning Warm-up:** If the system calculates clear solar potential (High Elevation) on a cold morning, you can delay boiler enabling to utilize passive solar heat gain.
  * **Zonal Bias:** If the sun is beating down on the **East** façade (Azimuth 60°–120°), the BAS can proactively lower discharge air setpoints or increase airflow to those specific zones *before* the room temperature spikes.

### 3\. Bulletproof Exterior Lighting

Replace unreliable photocells. Link the `isDaylight` boolean to your parking lot lights.

  * **Reliability:** Math doesn't get covered in bird droppings or snow.
  * **Accuracy:** It handles dawn/dusk perfectly based on your exact geographic location.

-----

## ⚙️ Slot Sheet Map

Create these slots on your Program Object. Ensure **Flags** are set correctly so users can configure the block from the Property Sheet.

| Slot Name | Type | Flags | Default | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Config / Inputs** | | | | |
| `enable` | `BStatusBoolean` | Config | `true` | Master enable. False = all outputs NULL. |
| `latitudeDeg` | `BStatusNumeric` | Config | `0.0` | **Required.** Site Latitude (e.g., 43.0 for WI). |
| `longitudeDeg` | `BStatusNumeric` | Config | `0.0` | **Required.** Site Longitude (e.g., -89.0). |
| `azimuthOffsetDeg` | `BStatusNumeric` | Config | `0.0` | Rotates the building frame (0 = True North). |
| `updateIntervalSeconds`| `BStatusNumeric` | Config | `60.0` | Calculation frequency (Clamped 10s–900s). |
| `timeOffsetMs`| `BStatusNumeric` | Config | `0.0` | Epoch offset in milliseconds (simulation) |

| **Outputs** | | | | |
| `solarAzimuthDeg` | `BStatusNumeric` | Summary | *ReadOnly* | 0–360° (0=N, 90=E, 180=S, 270=W). |
| `solarElevationDeg` | `BStatusNumeric` | Summary | *ReadOnly* | -90° to +90° (\>0 = Sun is UP). |
| `isDaylight` | `BStatusBoolean` | Summary | *ReadOnly* | True when Elevation \> 0°. |
| `statusTrace` | `BStatusString` | Summary | *ReadOnly* | Debug text (e.g., "Solar az=135.2..."). |
| `nextDawnAzimuthDeg` | `BStatusString` | Summary | *ReadOnly* | Azimuth at next civil dawn (north-based). |

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockSnip.png"  alt="Astro Snip 1" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockPropSheetSnip.png" alt="Astro Snip 2" width="750">
  <br><em>AX Prop Sheet View to input settings for block</em>
</p>

---

## 🖼️ Additional Graphics to show azimuth data on charts

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockSnipGraphic1.png"  alt="Astro Snip 1" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockSnipGraphic2.png" alt="Astro Snip 2" width="750">
  <br><em>AX Prop Sheet View to input settings for block</em>
</p>

---

## 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

### 1\. Class Level & Helpers

*Paste this at the top of the class, before `onStart`.*

```java
// ======================================
// Class-level state
// ======================================
private Clock.Ticket ticket = null;


// ======================================
// Math & Utilities
// ======================================
private double clamp(double v, double min, double max) {
  return Math.max(min, Math.min(v, max));
}
private double normalizeDegrees(double deg) {
  double d = deg % 360.0;
  if (d < 0.0) d += 360.0;
  return d;
}
private double round1(double v) {
  return Math.round(v * 10.0) / 10.0;
}
private double safeNumericOrNaN(BStatusNumeric num) {
  if (num == null || !num.getStatus().isOk()) return Double.NaN;
  return num.getValue();
}
private double safeNumericOrDefault(BStatusNumeric num, double fallback) {
  if (num == null || !num.getStatus().isOk()) return fallback;
  return num.getValue();
}
private boolean safeBool(BStatusBoolean b, boolean fallback) {
  if (b == null || !b.getStatus().isOk()) return fallback;
  return b.getValue();
}
private void updateStatus(String msg) {
  try {
    BAbsTime now = BAbsTime.now();
    String full = now.toString() + " — " + msg;
    System.out.println("[SolarPosition] " + full);
    BStatusString s = getStatusTrace();
    if (s != null) s.setValue(full);
  } catch (Exception ignore) {}
}
private void setOutputsNull(String reason) {
  try { getSolarAzimuthDeg().setStatus(BStatus.NULL); } catch (Exception e) {}
  try { getSolarElevationDeg().setStatus(BStatus.NULL); } catch (Exception e) {}
  try { getIsDaylight().setStatus(BStatus.NULL); } catch (Exception e) {}
  try { getNextDawnAzimuthDeg().setStatus(BStatus.NULL); } catch (Exception e) {}
  updateStatus(reason);
}
private long resolveNowEpochMs() {
  // Apply ms offset from slot (can be negative/positive)
  long off = (long) safeNumericOrDefault(getTimeOffsetMs(), 0.0);
  return System.currentTimeMillis() + off;
}


// ======================================
// Core Solar Position (NOAA-style)
// Returns [azimuthDeg (clockwise from TRUE NORTH), elevationDeg]
// ======================================
private double[] computeSolarPositionAtEpoch(double latitudeDeg, double longitudeDeg, long epochMs) {
  // Europe/London tz for Liverpool (UTC in winter, BST in summer)
  java.util.TimeZone tz = java.util.TimeZone.getTimeZone("Europe/London");
  java.util.Calendar cal = java.util.Calendar.getInstance(tz);
  cal.setTimeInMillis(epochMs);


  int dayOfYear = cal.get(java.util.Calendar.DAY_OF_YEAR);
  int hour      = cal.get(java.util.Calendar.HOUR_OF_DAY);
  int minute    = cal.get(java.util.Calendar.MINUTE);
  int second    = cal.get(java.util.Calendar.SECOND);


  double localMinutes  = hour * 60.0 + minute + (second / 60.0);
  double tzOffsetHours = tz.getOffset(epochMs) / 3600000.0;


  // Fractional year (gamma)
  double gamma = 2.0 * Math.PI / 365.0 *
      (dayOfYear - 1 + (localMinutes - 720.0) / 1440.0);


  // Equation of time (minutes)
  double eqTime =
      229.18 * (0.000075
          + 0.001868 * Math.cos(gamma)
          - 0.032077 * Math.sin(gamma)
          - 0.014615 * Math.cos(2.0 * gamma)
          - 0.040849 * Math.sin(2.0 * gamma));


  // Declination (radians)
  double decl =
      0.006918
          - 0.399912 * Math.cos(gamma)
          + 0.070257 * Math.sin(gamma)
          - 0.006758 * Math.cos(2.0 * gamma)
          + 0.000907 * Math.sin(2.0 * gamma)
          - 0.002697 * Math.cos(3.0 * gamma)
          + 0.001480 * Math.sin(3.0 * gamma);


  // Time offset (minutes); NOTE longitudeDeg is +EAST, tzOffsetHours is hours from UTC
  double timeOffset = eqTime + 4.0 * longitudeDeg - 60.0 * tzOffsetHours;


  // True Solar Time (minutes), wrap 0..1440
  double tst = localMinutes + timeOffset;
  while (tst < 0.0) tst += 1440.0;
  while (tst >= 1440.0) tst -= 1440.0;


  // Hour angle
  double hourAngleDeg = tst / 4.0 - 180.0;
  double hourAngle    = Math.toRadians(hourAngleDeg);


  // Zenith
  double latRad = Math.toRadians(latitudeDeg);
  double cosZenith =
      Math.sin(latRad) * Math.sin(decl)
          + Math.cos(latRad) * Math.cos(decl) * Math.cos(hourAngle);


  cosZenith = clamp(cosZenith, -1.0, 1.0);
  double zenith = Math.acos(cosZenith);


  // Elevation
  double elevationRad = (Math.PI / 2.0) - zenith;
  double elevationDeg = Math.toDegrees(elevationRad);


  // Azimuth robust via atan2, then convert to NORTH-based, clockwise
  double sinZenith = Math.sin(zenith);
  double azimuthDeg;
  if (sinZenith < 1e-6) {
    azimuthDeg = 0.0; // undefined at zenith; pick 0 for stability
  } else {
    // PV-style south-based azimuth:
    // az_south = atan2( sin(H), cos(H)*sin(lat) - tan(dec)*cos(lat) )
    double num   = Math.sin(hourAngle);
    double denom = Math.cos(hourAngle) * Math.sin(latRad) - Math.tan(decl) * Math.cos(latRad);
    double azSouthRad = Math.atan2(num, denom);


    // Convert South-based → North-based (NOAA/NREL convention): add 180°
    azimuthDeg = normalizeDegrees(Math.toDegrees(azSouthRad) + 180.0);
  }


  return new double[] { azimuthDeg, elevationDeg };
}


// Helper: elevation only
private double elevationAtEpochMs(double latitudeDeg, double longitudeDeg, long epochMs) {
  return computeSolarPositionAtEpoch(latitudeDeg, longitudeDeg, epochMs)[1];
}


// ======================================
// Next Civil Dawn Finder (Sun elevation = -6° ascending)
// Returns dawn epochMs or -1 if not found in 00:00..12:00
// ======================================
private long findCivilDawnEpochMs(double latitudeDeg, double longitudeDeg, long midnightLocalEpochMs) {
  final double threshold = -6.0;           // civil dawn
  final long   step      = 10L * 60L * 1000L;  // coarse 10 min
  final long   end       = midnightLocalEpochMs + 12L * 60L * 60L * 1000L; // noon window


  long low = midnightLocalEpochMs;
  double eLow = elevationAtEpochMs(latitudeDeg, longitudeDeg, low);


  for (long t = low + step; t <= end; t += step) {
    double eHigh = elevationAtEpochMs(latitudeDeg, longitudeDeg, t);
    // look for crossing from below to above threshold
    if (eLow < threshold && eHigh >= threshold) {
      // bisection refine to ~1 minute
      long a = t - step;
      long b = t;
      while ((b - a) > 60L * 1000L) {
        long m = (a + b) / 2L;
        double em = elevationAtEpochMs(latitudeDeg, longitudeDeg, m);
        if (em < threshold) a = m; else b = m;
      }
      return b; // first time elevation >= threshold
    }
    eLow = eHigh;
  }
  return -1L;
}


// Build local midnight epoch for a given day offset (0=today, +1=tomorrow)
private long localMidnightEpochMs(java.util.TimeZone tz, long baseEpochMs, int dayOffset) {
  java.util.Calendar cal = java.util.Calendar.getInstance(tz);
  cal.setTimeInMillis(baseEpochMs);
  // move to requested day (today/tomorrow) and clamp to midnight
  cal.add(java.util.Calendar.DAY_OF_YEAR, dayOffset);
  cal.set(java.util.Calendar.HOUR_OF_DAY, 0);
  cal.set(java.util.Calendar.MINUTE, 0);
  cal.set(java.util.Calendar.SECOND, 0);
  cal.set(java.util.Calendar.MILLISECOND, 0);
  return cal.getTimeInMillis();
}


// Compute next dawn azimuth (north-based, clockwise); returns NaN if not found
private double computeNextDawnAzimuth(double latitudeDeg, double longitudeDeg, long nowEpochMs) {
  java.util.TimeZone tz = java.util.TimeZone.getTimeZone("Europe/London");


  long todayMidnight = localMidnightEpochMs(tz, nowEpochMs, 0);
  long dawnToday     = findCivilDawnEpochMs(latitudeDeg, longitudeDeg, todayMidnight);


  long targetDawn = dawnToday;


  if (dawnToday == -1L) {
    // fallback: try tomorrow
    long tomorrowMidnight = localMidnightEpochMs(tz, nowEpochMs, 1);
    long dawnTomorrow     = findCivilDawnEpochMs(latitudeDeg, longitudeDeg, tomorrowMidnight);
    targetDawn = dawnTomorrow;
  } else {
    // If dawn already passed today, use tomorrow's
    if (nowEpochMs > dawnToday) {
      long tomorrowMidnight = localMidnightEpochMs(tz, nowEpochMs, 1);
      long dawnTomorrow     = findCivilDawnEpochMs(latitudeDeg, longitudeDeg, tomorrowMidnight);
      targetDawn = dawnTomorrow;
    }
  }


  if (targetDawn == -1L) return Double.NaN;


  // Azimuth at dawn (north-based, clockwise)
  return computeSolarPositionAtEpoch(latitudeDeg, longitudeDeg, targetDawn)[0];
}


// ======================================
// Lifecycle Methods
// ======================================
private void scheduleNext() {
  try {
    if (ticket != null) { ticket.cancel(); ticket = null; }
    int seconds = 60;
    try {
      BStatusNumeric cfg = getUpdateIntervalSeconds();
      if (cfg != null && cfg.getStatus().isOk()) {
        double raw = cfg.getValue();
        seconds = (int)Math.max(10.0, Math.min(raw, 900.0));
      }
    } catch (Exception ignore) {}
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(seconds), BProgram.execute, null);
  } catch (Exception e) {
    updateStatus("scheduleNext error: " + e.getMessage());
  }
}


public void onStart() throws Exception {
  try {
    // Defaults: Liverpool, UK
    getLatitudeDeg().setValue(53.41);
    getLongitudeDeg().setValue(-2.99);


    // Behavior
    getEnable().setValue(true);
    getAzimuthOffsetDeg().setValue(0.0);
    getUpdateIntervalSeconds().setValue(60.0);


    // New: ms epoch offset (default 0)
    getTimeOffsetMs().setValue(0.0);


    // New: next dawn azimuth output starts NULL until first compute
    getNextDawnAzimuthDeg().setStatus(BStatus.NULL);
  } catch (Exception ignore) {}


  updateStatus("SolarPosition block initialized (Liverpool defaults, Europe/London tz).");
  scheduleNext();
}


public void onExecute() throws Exception {
  scheduleNext(); // heartbeat


  if (!safeBool(getEnable(), true)) {
    setOutputsNull("Disabled by 'enable' input.");
    return;
  }


  double latDeg    = safeNumericOrNaN(getLatitudeDeg());
  double lonDeg    = safeNumericOrNaN(getLongitudeDeg());
  double offsetDeg = safeNumericOrDefault(getAzimuthOffsetDeg(), 0.0);


  if (Double.isNaN(latDeg) || Double.isNaN(lonDeg)) {
    setOutputsNull("Latitude/Longitude not set or NULL.");
    return;
  }


  // Current position using (now + timeOffsetMs)
  long nowEpoch = resolveNowEpochMs();
  double[] pos  = computeSolarPositionAtEpoch(latDeg, lonDeg, nowEpoch);
  double azimuthDeg   = normalizeDegrees(pos[0] + offsetDeg);
  double elevationDeg = pos[1];
  boolean daylight    = elevationDeg > 0.0;


  try {
    getSolarAzimuthDeg().setValue(azimuthDeg);
    getSolarAzimuthDeg().setStatus(BStatus.ok);


    getSolarElevationDeg().setValue(elevationDeg);
    getSolarElevationDeg().setStatus(BStatus.ok);


    getIsDaylight().setValue(daylight);
    getIsDaylight().setStatus(BStatus.ok);
  } catch (Exception ignore) {}


  // Compute next civil dawn azimuth (north-based, clockwise)
  double dawnAz = computeNextDawnAzimuth(latDeg, lonDeg, nowEpoch);
  try {
    if (Double.isNaN(dawnAz)) {
      getNextDawnAzimuthDeg().setStatus(BStatus.NULL);
    } else {
      getNextDawnAzimuthDeg().setValue(dawnAz);
      getNextDawnAzimuthDeg().setStatus(BStatus.ok);
    }
  } catch (Exception ignore) {}


  String msg = "Loc=" + round1(latDeg) + "/" + round1(lonDeg) +
               " : Az=" + round1(azimuthDeg) +
               "°, El=" + round1(elevationDeg) +
               "°, NextDawnAz=" + (Double.isNaN(dawnAz) ? "null" : round1(dawnAz)) +
               "°, Day=" + daylight;
  updateStatus(msg);
}


public void onStop() throws Exception {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  updateStatus("SolarPosition block stopped.");
}

```

</details>


