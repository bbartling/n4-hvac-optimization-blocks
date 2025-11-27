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
| **Outputs** | | | | |
| `solarAzimuthDeg` | `BStatusNumeric` | Summary | *ReadOnly* | 0–360° (0=N, 90=E, 180=S, 270=W). |
| `solarElevationDeg` | `BStatusNumeric` | Summary | *ReadOnly* | -90° to +90° (\>0 = Sun is UP). |
| `isDaylight` | `BStatusBoolean` | Summary | *ReadOnly* | True when Elevation \> 0°. |
| `statusTrace` | `BStatusString` | Summary | *ReadOnly* | Debug text (e.g., "Solar az=135.2..."). |


<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockSnip.png"  alt="Astro Snip 1" width="550">
  <br><em>Program Object wiring sheet</em>
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/astroClockPropSheetSnip.png" alt="Astro Snip 2" width="750">
  <br><em>AX Prop Sheet View to input settings for block</em>
</p>

-----

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

/**
 * Core solar position math – returns [azimuthDeg, elevationDeg].
 */
private double[] computeSolarPositionNow(double latitudeDeg, double longitudeDeg) {
  // Local time + timezone
  java.util.TimeZone tz = java.util.TimeZone.getDefault();
  java.util.Calendar cal = java.util.Calendar.getInstance(tz);

  int dayOfYear = cal.get(java.util.Calendar.DAY_OF_YEAR);
  int hour      = cal.get(java.util.Calendar.HOUR_OF_DAY);
  int minute    = cal.get(java.util.Calendar.MINUTE);
  int second    = cal.get(java.util.Calendar.SECOND);

  // Local minutes since midnight
  double localMinutes = hour * 60.0 + minute + (second / 60.0);

  // Time zone offset from UTC in hours (includes DST)
  double tzOffsetHours = tz.getOffset(cal.getTimeInMillis()) / 3600000.0;

  // Fractional year (gamma) in radians – NOAA style
  double gamma = 2.0 * Math.PI / 365.0 *
      (dayOfYear - 1 + (localMinutes - 720.0) / 1440.0);

  // Equation of time in minutes
  double eqTime =
      229.18 * (0.000075
          + 0.001868 * Math.cos(gamma)
          - 0.032077 * Math.sin(gamma)
          - 0.014615 * Math.cos(2.0 * gamma)
          - 0.040849 * Math.sin(2.0 * gamma));

  // Solar declination (radians)
  double decl =
      0.006918
          - 0.399912 * Math.cos(gamma)
          + 0.070257 * Math.sin(gamma)
          - 0.006758 * Math.cos(2.0 * gamma)
          + 0.000907 * Math.sin(2.0 * gamma)
          - 0.002697 * Math.cos(3.0 * gamma)
          + 0.00148  * Math.sin(3.0 * gamma);

  // Time offset (minutes)
  double timeOffset = eqTime + 4.0 * longitudeDeg - 60.0 * tzOffsetHours;

  // True solar time (minutes)
  double tst = localMinutes + timeOffset;
  while (tst < 0.0)   tst += 1440.0;
  while (tst >= 1440.0) tst -= 1440.0;

  // Hour angle
  double hourAngleDeg = tst / 4.0 - 180.0;
  double hourAngle    = Math.toRadians(hourAngleDeg);

  double latRad = Math.toRadians(latitudeDeg);

  // Zenith
  double cosZenith =
      Math.sin(latRad) * Math.sin(decl)
          + Math.cos(latRad) * Math.cos(decl) * Math.cos(hourAngle);

  cosZenith = clamp(cosZenith, -1.0, 1.0);
  double zenith = Math.acos(cosZenith);

  // Elevation
  double elevationRad = (Math.PI / 2.0) - zenith;
  double elevationDeg = Math.toDegrees(elevationRad);

  // Azimuth from North, eastward
  double sinZenith = Math.sin(zenith);
  double azimuthDeg;

  if (sinZenith < 1e-6) {
    // Sun at/near zenith or below horizon → azimuth undefined, pick 0°
    azimuthDeg = 0.0;
  } else {
    double cosAz =
        (Math.sin(latRad) * Math.cos(zenith) - Math.sin(decl)) /
        (Math.cos(latRad) * sinZenith);

    cosAz = clamp(cosAz, -1.0, 1.0);
    double az = Math.acos(cosAz); // 0..π

    // Disambiguate using hour angle: afternoon vs morning
    if (hourAngle > 0.0) {
      az = 2.0 * Math.PI - az;
    }
    azimuthDeg = Math.toDegrees(az);
  }

  return new double[] { normalizeDegrees(azimuthDeg), elevationDeg };
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

private void setOutputsNull(String reason) {
  try { getSolarAzimuthDeg().setStatus(BStatus.NULL); } catch (Exception e) {}
  try { getSolarElevationDeg().setStatus(BStatus.NULL); } catch (Exception e) {}
  try { getIsDaylight().setStatus(BStatus.NULL); } catch (Exception e) {}
  updateStatus(reason);
}

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

// ======================================
// Lifecycle Methods
// ======================================

public void onStart() throws Exception {
  try {
    // --- DEFAULTS: CHICAGO, IL ---
    // If slots are NULL (purple/empty), set these values.
    // Note: If slots are 0.00 {ok}, right-click and 'Set Null' to trigger this.
    getLatitudeDeg().setValue(41.88);
    getLongitudeDeg().setValue(-87.63);
    
    // Other defaults
    getEnable().setValue(true);
    getAzimuthOffsetDeg().setValue(0.0);
    getUpdateIntervalSeconds().setValue(60.0);
  } catch (Exception ignore) {}

  updateStatus("SolarPosition block initialized.");
  scheduleNext();
}

public void onExecute() throws Exception {
  scheduleNext(); // Maintain cadence

  boolean enabled = safeBool(getEnable(), true);
  if (!enabled) {
    setOutputsNull("Disabled by 'enable' input.");
    return;
  }

  double latDeg = safeNumericOrNaN(getLatitudeDeg());
  double lonDeg = safeNumericOrNaN(getLongitudeDeg());
  double offsetDeg = safeNumericOrDefault(getAzimuthOffsetDeg(), 0.0);

  if (Double.isNaN(latDeg) || Double.isNaN(lonDeg)) {
    setOutputsNull("Latitude/Longitude not set or NULL.");
    return;
  }

  double[] pos = computeSolarPositionNow(latDeg, lonDeg);
  double azimuthDeg  = normalizeDegrees(pos[0] + offsetDeg);
  double elevationDeg = pos[1];
  boolean daylight = elevationDeg > 0.0;

  try {
    getSolarAzimuthDeg().setValue(azimuthDeg);
    getSolarAzimuthDeg().setStatus(BStatus.ok);
    
    getSolarElevationDeg().setValue(elevationDeg);
    getSolarElevationDeg().setStatus(BStatus.ok);
    
    getIsDaylight().setValue(daylight);
    getIsDaylight().setStatus(BStatus.ok);
  } catch (Exception ignore) {}

  // *** TRACE UPDATE ***
  // Includes Lat/Lon in the status message
  String msg = "Loc=" + round1(latDeg) + "/" + round1(lonDeg) + 
               " : Az=" + round1(azimuthDeg) + 
               "°, El=" + round1(elevationDeg) + 
               "°, Day=" + daylight;
               
  updateStatus(msg);
}

public void onStop() throws Exception {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  updateStatus("SolarPosition block stopped.");
}

```

</details>


