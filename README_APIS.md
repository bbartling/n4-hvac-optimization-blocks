# APIs & Web Requests

This sub‑guide groups all of the examples that demonstrate how to interface Niagara with external services.  The sections include weather data via OpenWeatherMap, holiday checking and calendar integration via the Nager API and iCal, as well as a Docker‑based AI model example.  Each section remains untouched from the original README so you can reuse the code directly.

<!-- Click to expand a section and see its full details. -->

<details>
<summary>🌤️ OpenWeatherMap API — diy Web Weather OAT & RH </summary>


<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/openWeatherMapAPI.png" alt="OpenWeatherMap API Niagara ProgramObject Snip" width="900">
</p>

This ProgramObject polls **OpenWeatherMap Current Weather** and outputs **Outside Air Temperature (°F)** and **Relative Humidity (%)** on a 20-minute cadence using a simple HTTP GET and lightweight JSON parsing (no extra libs). Lat/Lon, units, language, and cadence are **baked in as defaults**; you only provide your **API key**.

Grab a free API key here (which can take up to a few hours for them to return one to you...):
* https://openweathermap.org/current

> NOTE: At the present moment (October 2025) it is free for `60 calls/minute (i.e. 1 call every ~1 second) up to a 1,000 calls/day` but I am only doing 1 call for an entire campus of building every 20 minutes or 1200 seconds.

### ⚙️ Slots

| Slot Name       | Type                 | Writable | Notes                                                 |
| --------------- | -------------------- | -------- | ----------------------------------------------------- |
| `apiKey`        | `baja:String`        | Yes      | Your OWM API key (the **only** thing you must enter). |
| `outTempF`      | `baja:StatusNumeric` | No       | Outside air temperature (°F).                         |
| `outHumidity`   | `baja:StatusNumeric` | No       | Outside air humidity (%RH).                           |
| `statusMessage` | `baja:StatusString`  | No       | Status or HTTP code for quick debugging.              |

---

### 🧠 Defaults

* Location: **Waldorf, MD** (`lat=38.6246`, `lon=-76.9391`)
* Units: **imperial** (°F)
* Language: **en**
* Poll interval: **1200 s** (20 minutes)

Adjust as necessary in the `ProgramObject` property sheet.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/openWeatherMapAPIPropSheet.png" alt="OpenWeatherMap API Niagara ProgramObject Snip" width="900">
</p>

> NOTE: Any change to defaults (location, units, cadence) requires **re-compiling the ProgramObject in Workbench** for it to take effect. ✔️

---

## 🌡️ `units` Parameter Options

| Value                  | Temperature     | Wind speed | Pressure | Description                                           |
| ---------------------- | --------------- | ---------- | -------- | ----------------------------------------------------- |
| `standard` *(default)* | Kelvin (K)      | meter/sec  | hPa      | No `&units` needed; omit it or use `&units=standard`. |
| `metric`               | Celsius (°C)    | meter/sec  | hPa      | Typical for international / SI users.                 |
| `imperial`             | Fahrenheit (°F) | miles/hour | hPa      | Default for U.S.-style unit systems.                  |

🧠 **Notes:**

* If `&units` is **not** specified, it defaults to **Kelvin** (standard).
* Example conversions from your Niagara block:

  * `&units=imperial` → °F and mph
  * `&units=metric` → °C and m/s
  * `&units=standard` → Kelvin and m/s

---

## 🌍 `lang` Parameter Options

The `lang` parameter controls the **language of weather descriptions** (like “clear sky”, “light rain”). It does **not** affect numeric data.

| Code    | Language              | Example                   |
| ------- | --------------------- | ------------------------- |
| `af`    | Afrikaans             | “helder lug”              |
| `al`    | Albanian              | “qiell i kthjellët”       |
| `ar`    | Arabic                | “سماء صافية”              |
| `az`    | Azerbaijani           | “açıq hava”               |
| `bg`    | Bulgarian             | “ясно небе”               |
| `ca`    | Catalan               | “cel clar”                |
| `cz`    | Czech                 | “jasná obloha”            |
| `da`    | Danish                | “klar himmel”             |
| `de`    | German                | “klarer Himmel”           |
| `el`    | Greek                 | “καθαρός ουρανός”         |
| `en`    | English *(default)*   | “clear sky”               |
| `eu`    | Basque                | “zeru garbi”              |
| `fa`    | Persian (Farsi)       | “آسمان صاف”               |
| `fi`    | Finnish               | “selkeä taivas”           |
| `fr`    | French                | “ciel dégagé”             |
| `gl`    | Galician              | “céu despexado”           |
| `he`    | Hebrew                | “שמיים בהירים”            |
| `hi`    | Hindi                 | “साफ आसमान”               |
| `hr`    | Croatian              | “vedro nebo”              |
| `hu`    | Hungarian             | “derült égbolt”           |
| `id`    | Indonesian            | “langit cerah”            |
| `it`    | Italian               | “cielo sereno”            |
| `ja`    | Japanese              | “晴天”                      |
| `kr`    | Korean                | “맑은 하늘”                   |
| `la`    | Latvian               | “skaidras debesis”        |
| `lt`    | Lithuanian            | “giedras dangus”          |
| `mk`    | Macedonian            | “ведро небо”              |
| `no`    | Norwegian             | “klar himmel”             |
| `nl`    | Dutch                 | “heldere lucht”           |
| `pl`    | Polish                | “bezchmurne niebo”        |
| `pt`    | Portuguese            | “céu limpo”               |
| `pt_br` | Portuguese (Brazil)   | “céu limpo”               |
| `ro`    | Romanian              | “cer senin”               |
| `ru`    | Russian               | “ясное небо”              |
| `sv`    | Swedish               | “klar himmel”             |
| `sk`    | Slovak                | “jasná obloha”            |
| `sl`    | Slovenian             | “jasno nebo”              |
| `es`    | Spanish               | “cielo despejado”         |
| `sr`    | Serbian               | “ведро небо”              |
| `th`    | Thai                  | “ท้องฟ้าแจ่มใส”           |
| `tr`    | Turkish               | “açık hava”               |
| `ua`    | Ukrainian             | “ясне небо”               |
| `vi`    | Vietnamese            | “bầu trời trong xanh”     |
| `zh_cn` | Chinese (Simplified)  | “晴朗”                      |
| `zh_tw` | Chinese (Traditional) | “晴朗”                      |
| `zu`    | Zulu                  | “isibhakabhaka esicacile” |

---

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
/* ===== Program Methods + Helpers (paste into ProgramImpl source) ===== */

////////////////////////////////////////
// Defaults (used if slots are blank/NULL)
////////////////////////////////////////
private static final double DEFAULT_LAT  = 38.6246;    // Waldorf, MD
private static final double DEFAULT_LON  = -76.9391;
private static final String DEFAULT_UNITS = "imperial"; // imperial|metric|standard
private static final String DEFAULT_LANG  = "en";
private static final int    DEFAULT_POLL  = 1200;       // 20 minutes
private static final String OWM_BASE      = "https://api.openweathermap.org/data/2.5/weather";

Clock.Ticket ticket;

public void onStart() throws Exception {
  log("onStart");
  fetchWeatherData();
  scheduleNext();
}

public void onExecute() throws Exception {
  // If user toggled updateNow true, fetch immediately and auto-reset.
  if (safeBool(getUpdateNow())) {
    log("Manual trigger via updateNow");
    fetchWeatherData();
    try { getUpdateNow().setValue(false); } catch (Exception ignore) {}
  } else {
    fetchWeatherData();
  }
  scheduleNext();
}

public void onStop() throws Exception {
  if (ticket != null) ticket.cancel();
  log("onStop");
  getStatusMessage().setValue("Stopped.");
}

private void scheduleNext() {
  if (ticket != null) ticket.cancel();
  int s = safeIntSeconds(getPollSeconds(), DEFAULT_POLL);
  // Clamp to 60–3600 seconds to avoid hammering the API
  s = Math.max(60, Math.min(s, 3600));
  log("Scheduling next fetch in " + s + "s");
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(s), BProgram.execute, null);
}

private void fetchWeatherData() {
  try {
    String key = getApiKey();
    if (key == null || key.trim().isEmpty()) {
      getStatusMessage().setValue("Config: API key missing");
      nullOutputs();
      return;
    }

    // Read coordinates / units / lang from slots with fallbacks
    double lat  = safeNumeric(getLat(),  DEFAULT_LAT);
    double lon  = safeNumeric(getLon(),  DEFAULT_LON);
    String units = safeString(getUnits(), DEFAULT_UNITS);
    String lang  = safeString(getLang(),  DEFAULT_LANG);

    String urlStr = OWM_BASE
      + "?lat="   + lat
      + "&lon="   + lon
      + "&appid=" + java.net.URLEncoder.encode(key, "UTF-8")
      + "&units=" + units
      + "&lang="  + lang;

    log("GET " + urlStr);

    URL url = new URL(urlStr);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    conn.setRequestMethod("GET");
    conn.setConnectTimeout(10000);
    conn.setReadTimeout(10000);
    conn.setRequestProperty("User-Agent", "Niagara-OpenWeather/1.0");

    int code = conn.getResponseCode();
    if (code == HttpURLConnection.HTTP_OK) {
      BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
      StringBuilder sb = new StringBuilder();
      String line; while ((line = in.readLine()) != null) sb.append(line);
      in.close();

      String json = sb.toString();

      // Core outputs
      double temp    = extractNumber(json, "\"temp\":");       // main.temp
      double humidPc = extractNumber(json, "\"humidity\":");   // main.humidity

      if (!Double.isNaN(temp))    { getOutTempF().setValue(temp);   getOutTempF().setStatus(BStatus.ok); }
      else                        { getOutTempF().setValue(0);      getOutTempF().setStatus(BStatus.NULL); }

      if (!Double.isNaN(humidPc)) { getOutHumidity().setValue(humidPc); getOutHumidity().setStatus(BStatus.ok); }
      else                        { getOutHumidity().setValue(0);       getOutHumidity().setStatus(BStatus.NULL); }

      // Enriched status string
      double feels    = extractNumber(json, "\"feels_like\":");
      double windSpd  = extractNumber(json, "\"speed\":");      // mph in imperial, m/s otherwise
      double gustSpd  = extractNumber(json, "\"gust\":");
      double windDeg  = extractNumber(json, "\"deg\":");
      double clouds   = extractNumber(json, "\"all\":");        // clouds.all %
      double pressure = extractNumber(json, "\"pressure\":");   // hPa
      double visM     = extractNumber(json, "\"visibility\":"); // meters
      String desc     = extractString(json, "\"description\":\"");
      String city     = extractString(json, "\"name\":\"");
      double rlat     = extractNumber(json, "\"lat\":");
      double rlon     = extractNumber(json, "\"lon\":");

      // Location sanity vs requested
      double milesOff = haversineMiles(lat, lon, rlat, rlon);
      String locNote  = (Double.isNaN(milesOff) || milesOff < 2.0)
                        ? city : city + String.format(" (%.1f mi off)", milesOff);

      // Units labels
      String tUnit = tempUnit(units);
      String vUnit = windUnit(units);

      StringBuilder nice = new StringBuilder();
      if (!isEmpty(locNote)) nice.append(locNote).append(" • ");
      if (!isEmpty(desc))    nice.append(cap(desc)).append(" • ");
      if (!Double.isNaN(feels))   nice.append(String.format("feels %.1f%s • ", feels, tUnit));
      if (!Double.isNaN(windSpd)) {
        String dir = windDir(windDeg);
        nice.append("wind ");
        if (!isEmpty(dir)) nice.append(dir).append(" ");
        nice.append(String.format("%.0f %s", windSpd, vUnit));
        if (!Double.isNaN(gustSpd)) nice.append(String.format(" (gust %.0f)", gustSpd));
        nice.append(" • ");
      }
      if (!Double.isNaN(clouds))   nice.append(String.format("clouds %.0f%% • ", clouds));
      if (!Double.isNaN(visM))     nice.append(String.format("vis %.1f mi • ", visM / 1609.34));
      if (!Double.isNaN(pressure)) nice.append(String.format("%.0f hPa • ", pressure));
      nice.append(new java.util.Date().toString());

      getStatusMessage().setValue(nice.toString());
      log("OK");
    } else {
      getStatusMessage().setValue("HTTP Error: " + code);  // 401 bad key, 404 bad coords, 429 rate-limit, etc.
      nullOutputs();
      log("HTTP Error " + code);
    }
  }
  catch (Exception e) {
    getStatusMessage().setValue("Error: " + e.getMessage());
    nullOutputs();
    log("Exception: " + e.getMessage());
  }
}

////////////////////////////////////////
// Helpers
////////////////////////////////////////

private double safeNumeric(javax.baja.status.BStatusNumeric s, double def) {
  try { return (s != null && s.getStatus().isOk()) ? s.getValue() : def; }
  catch (Exception e) { return def; }
}

private String safeString(String v, String def) {
  return (v != null && v.trim().length() > 0) ? v.trim() : def;
}

private boolean safeBool(javax.baja.status.BStatusBoolean b) {
  try { return (b != null && b.getStatus().isOk()) && b.getValue(); }
  catch (Exception e) { return false; }
}

private int safeIntSeconds(javax.baja.status.BStatusNumeric s, int def) {
  double v = safeNumeric(s, def);
  if (Double.isNaN(v)) return def;
  return (int)Math.round(v);
}

// crude numeric extractor
private double extractNumber(String json, String key) {
  try {
    int i = json.indexOf(key);
    if (i < 0) return Double.NaN;
    int s = i + key.length();
    int e = s;
    while (e < json.length()) {
      char c = json.charAt(e);
      if ((c >= '0' && c <= '9') || c == '.' || c == '-') e++;
      else break;
    }
    String raw = json.substring(s, e).replaceAll("[^0-9.\\-]", "");
    if (raw.length() == 0) return Double.NaN;
    return Double.parseDouble(raw);
  } catch (Exception ex) {
    return Double.NaN;
  }
}

// tiny string extractor: prefix like "\"name\":\""
private String extractString(String json, String keyPrefix) {
  try {
    int i = json.indexOf(keyPrefix);
    if (i < 0) return "";
    int s = i + keyPrefix.length();
    int e = json.indexOf("\"", s);
    if (e < 0) return "";
    return json.substring(s, e);
  } catch (Exception ex) {
    return "";
  }
}

private String tempUnit(String units) {
  String u = (units == null) ? "" : units.toLowerCase();
  if ("metric".equals(u)) return "°C";
  if ("standard".equals(u)) return "K";
  return "°F"; // imperial or anything else
}

private String windUnit(String units) {
  String u = (units == null) ? "" : units.toLowerCase();
  return "imperial".equals(u) ? "mph" : "m/s";
}

private String cap(String s) {
  if (s == null || s.isEmpty()) return "";
  return s.substring(0,1).toUpperCase() + s.substring(1);
}

private boolean isEmpty(String s) { return s == null || s.length() == 0; }

// wind cardinal from degrees
private String windDir(double deg) {
  if (Double.isNaN(deg)) return "";
  String[] dirs = {"N","NNE","NE","ENE","E","ESE","SE","SSE",
                   "S","SSW","SW","WSW","W","WNW","NW","NNW"};
  int idx = (int)Math.floor(((deg % 360) / 22.5) + 0.5) % 16;
  return dirs[idx];
}

// distance in miles (haversine)
private double haversineMiles(double lat1, double lon1, double lat2, double lon2) {
  if (Double.isNaN(lat2) || Double.isNaN(lon2)) return Double.NaN;
  double R = 3958.8; // miles
  double dLat = Math.toRadians(lat2 - lat1);
  double dLon = Math.toRadians(lon2 - lon1);
  double a = Math.sin(dLat/2)*Math.sin(dLat/2) +
             Math.cos(Math.toRadians(lat1))*Math.cos(Math.toRadians(lat2))*
             Math.sin(dLon/2)*Math.sin(dLon/2);
  double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

private void nullOutputs() {
  try { getOutTempF().setValue(0); getOutTempF().setStatus(BStatus.NULL); } catch (Exception ignore) {}
  try { getOutHumidity().setValue(0); getOutHumidity().setStatus(BStatus.NULL); } catch (Exception ignore) {}
}

// Console logger (enable via logToConsole slot)
private void log(String msg) {
  try {
    if (safeBool(getLogToConsole())) {
      System.out.println("[OpenWeatherMapAPI] " + msg);
    }
  } catch (Exception ignore) {}
}
```

#### 🧠 Java Imports Note

> NOTE: The block is available in the `bog_files` sub directory furnished as necessary, but due note this `ProgramObject` has two imports to make web requests. If you are creating a custom web request block you must import two Java packages under the **IMPORTS** tab in Workbench:

| Module | Package    | Type         |
| ------ | ---------- | ------------ |
| `java` | `java.net` | User Defined |
| `java` | `java.io`  | User Defined |

To add:

1. Open the **Program Object → Imports** tab.
2. Click **Import Package**.
3. Enter:

   * **Module:** `java`
   * **Package:** `java.net`
     *(Repeat for `java.io`)*
4. Press **OK**, then **Compile** the program.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/openWeatherMapAPIReqImports.png" alt="Niagara Workbench Imports Example" width="650">
</p>

</details>



<details>
<summary>🤖 AI Engineer Example (Niagara ↔ Docker ML Model)</summary>

This block is an example of what “AI engineering” actually looks like in a building automation system where a ProgramObject hits a Docker container with a machine learning model in it to predict electrical power. See this other repo for more details on running a Docker container and the machine learning app code downloaded from Kaggle which is a data science competition organization.

* https://github.com/bbartling/chiller-power-model-api

The ML Docker container can be ran on the same server as the Niagara Server, cloud, or somewhere on the OT LAN. You feed in this data via wire sheet to the ProgramObject: 

Inputs your model expects:

* Outside air temp (°F)
* Outside air RH (%)
* Hour of day
* Day of week
* Building cooling load (RT)
* Chilled water flow (L/s)
* Condenser water temp (°C)
* Timestamp (ms since epoch)

And the Docker container returns back JSON like:

```json
{
  "predicted_kw": 107.76,
  "model_version": "v0.1",
  "ok": true
}
```

Where then some custom controls engineering logic can be applied or whatever is required for the project.

---

<p align="center">
<img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/AiEngSnip.png" alt="Niagara AI Power Predictor Wiresheet" width="800">
<br><em>Niagara ProgramObject calling the local FastAPI model container and writing kW + status back into the station.</em>
</p>

---

### 🔌 Required Slots

| Slot Name             | Type             | Writable | Purpose                                                                                                     |
| --------------------- | ---------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| `updateNow`           | `BStatusBoolean` | Yes      | Trigger to call the model in docker container. **Must have Config Flag: Execute On Change.**                                    |
| `modelUrl`            | `BString`        | Yes      | API endpoint, like `http://127.0.0.1:8000/predict_power`. Can be retuned in the field without editing code. |
| `outsideAirTemp_F`    | `BStatusNumeric` | Yes      | Outside air temp (°F).                                                                                      |
| `outsideAirRH_Pct`    | `BStatusNumeric` | Yes      | Outside air relative humidity (%).                                                                          |
| `buildingLoad_RT`     | `BStatusNumeric` | Yes      | Plant load in refrigeration tons.                                                                           |
| `chwFlow_LPS`         | `BStatusNumeric` | Yes      | Chilled water flow (L/s).                                                                                   |
| `cwTemp_C`            | `BStatusNumeric` | Yes      | Condenser water temp (°C).                                                                                  |
| `predictedBuildingKW` | `BStatusNumeric` | No       | OUTPUT. The model’s predicted electrical power draw in kW.                                                  |
| `statusTrace`         | `BStatusString`  | No       | OUTPUT. Debug text like `OK predicted_kw=107.76`.                                                           |
| `lastCallTimestampMs` | `BStatusNumeric` | No       | OUTPUT. Milliseconds since epoch when call went out.                                                        |


---

### ✅ Java: ProgramObject logic


```java

public void onStart() throws Exception
{
    // nothing on start; this block is event-driven
    getStatusTrace().setValue("PowerPredictorFromModel ready.");
}

public void onExecute() throws Exception
{
    // only run logic if updateNow is true
    if (!getUpdateNow().getValue()) {
        return;
    }

    // --- Read inputs safely with defaults ---
    double oatF = getOutsideAirTemp_F().getStatus().isOk() ? getOutsideAirTemp_F().getValue() : 70.0;
    double rhPct = getOutsideAirRH_Pct().getStatus().isOk() ? getOutsideAirRH_Pct().getValue() : 50.0;
    
    // --- ADDED: Read new required plant inputs ---
    double loadRT = getBuildingLoad_RT().getStatus().isOk() ? getBuildingLoad_RT().getValue() : 100.0;
    double flowLPS = getChwFlow_LPS().getStatus().isOk() ? getChwFlow_LPS().getValue() : 20.0;
    double cwTempC = getCwTemp_C().getStatus().isOk() ? getCwTemp_C().getValue() : 28.0;

    String url = getModelUrl().getValue();
    if (url == null || url.trim().length() == 0) {
        url = "http://127.0.0.1:8000/predict_power"; // localhost Docker default fallback
    }

    // --- ADDED: Derive time features ---
    long nowMs = System.currentTimeMillis();
    java.util.Calendar cal = java.util.Calendar.getInstance();
    cal.setTimeInMillis(nowMs);
    int hourOfDay = cal.get(java.util.Calendar.HOUR_OF_DAY);
    
    // Map Java's Calendar (SUNDAY=1) to Python's (MONDAY=0)
    int javaDow = cal.get(java.util.Calendar.DAY_OF_WEEK);
    int modelDow = (javaDow == 1) ? 6 : (javaDow - 2); // (Java SUNDAY=1 -> Model SUNDAY=6), (Java MONDAY=2 -> Model MONDAY=0)

    getLastCallTimestampMs().setValue((double) nowMs);

    try {
        // --- ENHANCED: Build JSON body to match the model ---
        String jsonBody =
            "{"
            + "\"oat_f\":" + oatF + ","
            + "\"rh_pct\":" + rhPct + ","
            + "\"hour_of_day\":" + hourOfDay + ","
            + "\"day_of_week\":" + modelDow + ","
            + "\"building_load_rt\":" + loadRT + ","
            + "\"chw_flow_lps\":" + flowLPS + ","
            + "\"cw_temp_c\":" + cwTempC + ","
            + "\"timestamp_ms\":" + nowMs
            + "}";

        String resp = httpPostJson(url, jsonBody);

        // Parse "predicted_kw": <number>
        double kwVal = extractPredictedKw(resp);

        getPredictedBuildingKW().setValue(kwVal);
        getPredictedBuildingKW().setStatus(BStatus.ok);
        getStatusTrace().setValue("OK predicted_kw=" + kwVal);

    } catch (Exception e) {
        getPredictedBuildingKW().setValue(0.0);
        getPredictedBuildingKW().setStatus(BStatus.NULL);
        getStatusTrace().setValue("ERR calling model: " + e.getMessage());
    }

    // VERY IMPORTANT: reset trigger for next time
    setUpdateNow(new BStatusBoolean(false));
}

public void onStop() throws Exception
{
    // nothing to clean up
}

/**
 * Minimal HTTP POST helper.
 */
String httpPostJson(String urlStr, String body) throws Exception
{
    java.net.URL url = new java.net.URL(urlStr);
    java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
    conn.setRequestMethod("POST");
    conn.setConnectTimeout(5000);
    conn.setReadTimeout(5000);
    conn.setDoOutput(true);
    conn.setRequestProperty("Content-Type", "application/json");

    // write body
    java.io.OutputStream os = conn.getOutputStream();
    os.write(body.getBytes("UTF-8"));
    os.flush();
    os.close();

    int code = conn.getResponseCode();
    java.io.InputStream is;
    if (code >= 200 && code < 300) {
        is = conn.getInputStream();
    } else {
        is = conn.getErrorStream();
        if (is == null) {
            throw new Exception("Model HTTP " + code + " no body");
        }
    }

    java.io.BufferedReader br = new java.io.BufferedReader(new java.io.InputStreamReader(is, "UTF-8"));
    StringBuilder sb = new StringBuilder();
    String line;
    while ((line = br.readLine()) != null) {
        sb.append(line);
    }
    br.close();
    conn.disconnect();

    if (code < 200 || code >= 300) {
        throw new Exception("Model HTTP " + code + " resp=" + sb.toString());
    }

    return sb.toString();
}

/**
 * Extracts "predicted_kw": <number> from the JSON string.
 */
double extractPredictedKw(String resp) throws Exception
{
    String key = "\"predicted_kw\":";
    int idx = resp.indexOf(key);
    if (idx < 0) {
        throw new Exception("No predicted_kw in response: " + resp);
    }

    int startNum = idx + key.length();
    int endNum = startNum;
    while (endNum < resp.length()) {
        char c = resp.charAt(endNum);
        // Stop at the first non-numeric/decimal character
        if ((c < '0' || c > '9') && c != '.' && c != '-') {
            break;
        }
        endNum++;
    }

    String numStr = resp.substring(startNum, endNum).trim();
    return Double.parseDouble(numStr);
}

```

---

### 📚 Niagara Import Packages You MUST Add

In Workbench → Program Object → Imports tab, add:

* `java.net`
* `java.io`
* `java.util`

Those match what this block uses: `HttpURLConnection`, streams, and `Calendar`.


</details>



<details>
<summary>🗓️ Web Based Holiday Checker with the Nager API</summary>

Fetches **public holidays** from the free Nager.Date API and auto-drives a **CalendarSchedule** so your logic can treat holidays as “unoccupied”. 

* https://date.nager.at/API

The Nager API program makes an HTTP GET request to the Nager web service, building a URL with the specified country code and year to retrieve a list of public holidays in the JSON format. It processes this JSON text by scanning for specific keys to extract the "date" string (e.g., "2025-12-25") and the "localName" for each holiday, storing them in a HashMap. This program also uses its calendarOrd to find the target BCalendarSchedule component, where it then adds a new BDateSchedule child for each holiday, setting the required Year, Month, and Day properties by parsing the date string.

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/nagerApiSnip.png" alt="Nager API Holiday Checker wiresheet" width="820">
</p>

**What it does**
- Pulls holidays for **this year + next year** (cached in memory).
- Exposes `holidayToday` (bool), `holidayName`, and `nextHoliday` strings.
- Drives a **CalendarSchedule** so downstream schedules see holidays as `true`.
- Manual **country code** override (same vibe as the Weather Map country selection).

**Quick setup**
1. Drop the Program Object and wire an **Interval** trigger (or use its internal timer).
2. Set `countryCode` (e.g., `US`, `GB`, `CA`) on the ProgramObject Property Sheet.  
3. (Optional) Toggle `updateNow` to force an immediate refresh.
4. Wire the **CalendarSchedule** `Out` to any Boolean Schedule inputs you want to override on holidays.

**Imports tip (Workbench)**  
If you create a `CalendarSchedule` inside the Program’s *Imports* tab, add the **schedule** package:

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/scheduleImportsNoteSnip.png" alt="Schedule import note" width="720">
</p>

On the Program Object’s `Source` tab (the auto-generated code base), the import statements—if configured correctly—should look similar to the example below.
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

**Inputs & outputs (short list)**
- `countryCode` (writable `BStatusString`) – two-letter ISO code like `US`/`GB`.
- `updateNow` (writable `BStatusBoolean`) – set `true` to refresh now (auto-resets).
- `holidayToday` (`BStatusBoolean`) – `true` on a holiday.
- `holidayName`, `nextHoliday`, `statusTrace` (`BStatusString`) – for display/debug.
- `CalendarScheduleNagerApi` – auto-maintained **CalendarSchedule** reflecting holidays.

**Notes**
- Endpoint examples: `/PublicHolidays/2025/US`, `/PublicHolidays/2026/US`.
- Safe defaults + internal caching reduce API chatter.
- Use `logToConsole = true` for quick debugging in Application Director.
- Reference Country Codes here: https://date.nager.at/Country
- Ensure Holidays are populating on the equipment level schedules as shown below in the snip with proper referencing of the Calender Schedule on the Special Event Tab. 

<p align="center">
  <img src="snips\nagerApiSnipSchedule.png" alt="Note" width="720">
</p>

### 💻 Java Code

> Niagara auto-generates class headers, imports, and getters/setters. Paste **only** the methods below into the Program’s **Source** editor.

```java
////////////////////////////////////////////////////////////////
// Program Source  (paste inside ProgramImpl)
////////////////////////////////////////////////////////////////

// ========= Runtime state (not slots) =========
private Clock.Ticket ticket;
private int    cacheYearA    = -1;
private int    cacheYearB    = -1;
private String cacheCountry  = null;
private java.util.HashMap<String,String> holidayByDate = new java.util.HashMap<>();

// ========= Small utilities =========
private void log(String s) {
  try {
    boolean toConsole = getLogToConsole().getStatus().isOk() && getLogToConsole().getValue();
    if (toConsole) System.out.println("[HolidayProg] " + s);
  } catch (Exception ignore) {}
}

private void apiOk(String s)  {
  try {
    setApiResponse(new BStatusString(s, BStatus.ok));
    String ts = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date());
    getStatusTrace().setValue("OK: " + s + " @ " + ts);
  } catch (Exception ignore) {}
}

private void markOk(String s) {
  try {
    String ts = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date());
    getStatusTrace().setValue("OK: " + s + " @ " + ts);
  } catch (Exception ignore) {}
}

private void apiErr(String s) { try { setApiResponse(new BStatusString(s, BStatus.fault)); } catch (Exception ignore) {} }
private void traceErr(String where, String msg) {
  try { getStatusTrace().setValue("ERROR: " + where + " - " + msg); } catch (Exception ignore) {}
}
private void fail(String where, String msg) {
  traceErr(where, msg);
  apiErr(msg);
  log(where + ": " + msg);
}

private String cleanName(String raw, int y, int m0, int d) {
  if (raw == null || raw.trim().isEmpty()) raw = "Holiday";
  String cleaned = raw.replace("'", "")
                      .replace("`", "")
                      .replace("&", "And")
                      .replace("+", "Plus")
                      .replaceAll("[.,;:!?()\\[\\]{}]", "")
                      .replaceAll("[-/\\\\]", " ")
                      .trim();
  String[] words = cleaned.split("\\s+");
  StringBuilder sb = new StringBuilder();
  for (String w : words) {
    if (w.isEmpty()) continue;
    sb.append(Character.toUpperCase(w.charAt(0)));
    if (w.length() > 1) sb.append(w.substring(1).toLowerCase());
  }
  if (sb.length() == 0) sb.append("Holiday");
  return sb.toString();
}

// ========= Lifecycle =========
public void onStart() throws Exception {
  normalizeConfig(true);
  if (!pollOnce(true)) {
    traceErr("startup", "Initial fetch failed (see apiResponse/logs)");
  }
  scheduleNext();
  log("Started.");
}

public void onExecute() throws Exception {
  try {
    if (getUpdateNow().getStatus().isOk() && getUpdateNow().getValue()) {
      log("updateNow=TRUE -> forcing refresh");
      pollOnce(true);
      try { setUpdateNow(new BStatusBoolean(false)); } catch (Exception ignore) {}
      scheduleNext();
      return;
    }
  } catch (Exception ignore) {}

  pollOnce(false);
  scheduleNext();
}

public void onStop() throws Exception {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  log("Stopped.");
}

// ========= Scheduling =========
private void scheduleNext() {
  if (ticket != null) ticket.cancel();

  int period = 0;
  try {
    if (getExecutePeriodSeconds().getStatus().isOk())
      period = (int)getExecutePeriodSeconds().getValue();
  } catch (Exception ignore) {}

  if (period <= 0) {
    log("Heartbeat disabled (executePeriodSeconds <= 0).");
    return;
  }
  period = clampInt(period, 60, 3600);
  try { setExecutePeriodSeconds(new BStatusNumeric(period)); } catch (Exception ignore) {}

  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(period), BProgram.execute, null);
  log("Next execute in " + period + "s");
}

// ========= Core =========
private boolean pollOnce(boolean forceFetch) {
  try {
    normalizeConfig(false);
    javax.baja.schedule.BCalendarSchedule cal = resolveCalendar();
    if (cal == null) {
      fail("pollOnce", "calendarOrd does not resolve to a Calendar Schedule.");
      return false;
    }

    String cc = "US";
    if (getCountryCode().getStatus().isOk()) {
      String raw = getCountryCode().getValue();
      if (raw != null && !raw.trim().isEmpty()) cc = normalizeIso2(raw);
    }

    java.time.LocalDate today = java.time.LocalDate.now();
    int y1 = today.getYear();
    int y2 = y1 + 1;

    boolean needRefresh =
        forceFetch ||
        holidayByDate.isEmpty() ||
        cacheYearA != y1 || cacheYearB != y2 ||
        cacheCountry == null || !cacheCountry.equalsIgnoreCase(cc);

    if (needRefresh) {
      apiOk("Refreshing " + cc + " (" + y1 + "," + y2 + ")");
      java.util.HashMap<String,String> mapOut = new java.util.HashMap<>();
      fetchYearInto(cc, y1, mapOut);
      fetchYearInto(cc, y2, mapOut);
      int created = writeCalendarChildren(cal, mapOut);
      apiOk("Fetched " + mapOut.size() + " holidays; created/updated " + created);
      holidayByDate = mapOut;
      cacheYearA = y1; cacheYearB = y2; cacheCountry = cc;
      String ts = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date());
      getLastFetchTs().setValue(ts);
    } else {
      apiOk("Using cached holidays (" + cacheCountry + " " + cacheYearA + "," + cacheYearB + ")");
    }

    String todayIso = today.toString();
    String label = holidayByDate.get(todayIso);
    setHolidayToday(new BStatusBoolean(label != null));
    getHolidayName().setValue(label != null ? label : "");
    String next = computeNextHolidayString(today);
    getNextHoliday().setValue(next != null ? next : "N/A");
    return true;
  } catch (Exception e) {
    fail("pollOnce", e.getMessage());
    return false;
  }
}

// ========= Write to Calendar =========
private int writeCalendarChildren(javax.baja.schedule.BCalendarSchedule cal, java.util.Map<String,String> map) {
  int made = 0;
  if (!(cal instanceof BComponent)) return 0;
  BComponent comp = (BComponent)cal;
  for (java.util.Map.Entry<String,String> e : map.entrySet()) {
    String iso = e.getKey();    
    String name = e.getValue();
    String[] p = iso.split("-");
    if (p.length != 3) continue;
    int y = Integer.parseInt(p[0]);
    int m0= Integer.parseInt(p[1]) - 1;
    int d = Integer.parseInt(p[2]);
    String childName = cleanName(name, y, m0, d);
    try {
      try {
        BObject ex = comp.get(childName);
        if (ex != null) comp.remove(childName);
      } catch (Exception ignore) {}
      BDateSchedule ds = new BDateSchedule();
      ds.setYear(y);
      ds.setMonth(BMonth.make(m0));
      ds.setDay(d);
      comp.add(childName, ds);
      made++;
    } catch (Exception ex) {
      log("Create '" + childName + "' failed: " + ex.getMessage());
    }
  }
  return made;
}

// ========= HTTP + JSON Scan (final worldwide subdivision support) =========
private void fetchYearInto(String cc, int year, java.util.HashMap<String,String> out) throws Exception {
  String baseCc = cc.contains("-") ? cc.split("-")[0] : cc;
  String url = "https://date.nager.at/api/v3/PublicHolidays/" + year + "/" + baseCc;
  String json = httpGet(url);
  String filterSubdivision = cc.contains("-") ? cc.toUpperCase() : null;

  int i = 0;
  while (true) {
    int dIdx = json.indexOf("\"date\":\"", i);
    if (dIdx < 0) break;
    int dStart = dIdx + 8;
    int dEnd   = json.indexOf('"', dStart);
    if (dEnd < 0) break;
    String date = json.substring(dStart, dEnd);

    int nextHoliday = json.indexOf("\"date\":\"", dEnd + 1);
    if (nextHoliday < 0) nextHoliday = json.length();
    String block = json.substring(dEnd, nextHoliday).toUpperCase();

    boolean include = true;
    if (filterSubdivision != null) {
      int cIdx = block.indexOf("\"COUNTIES\":");
      if (cIdx >= 0) {
        int cEnd = block.indexOf("]", cIdx);
        if (cEnd > cIdx) {
          String counties = block.substring(cIdx, cEnd + 1);
          if (counties.contains("NULL")) {
            include = true;
          } else {
            include = counties.contains(filterSubdivision);
          }
        }
      }
    }

    if (include) {
      String local = extractJsonString(json, "\"localName\":\"", dEnd);
      String name  = extractJsonString(json, "\"name\":\"",      dEnd);
      String label = (local != null && !local.isEmpty()) ? local : (name != null ? name : "");
      if (date != null && !date.isEmpty() && label != null && !label.isEmpty()) {
        if (out.containsKey(date) && !out.get(date).equals(label)) {
          out.put(date, out.get(date) + " / " + label);
        } else {
          out.put(date, label);
        }
        if ("US".equalsIgnoreCase(baseCc) && label.toLowerCase().contains("thanksgiving")) {
          try {
            String[] p = date.split("-");
            int y = Integer.parseInt(p[0]);
            int m = Integer.parseInt(p[1]);
            int d = Integer.parseInt(p[2]) + 1;
            if (m == 11) {
              String bf = String.format("%04d-%02d-%02d", y, m, d);
              out.put(bf, "Black Friday");
            }
          } catch (Exception ignore) {}
        }
      }
    }
    i = dEnd + 1;
  }
}

// ========= HTTP Helper =========
private String httpGet(String urlStr) throws Exception {
  java.net.URL url = new java.net.URL(urlStr);
  java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
  conn.setRequestMethod("GET");
  conn.setConnectTimeout(10000);
  conn.setReadTimeout(10000);
  conn.setRequestProperty("Accept", "application/json");
  conn.setRequestProperty("User-Agent", "niagara-holiday-checker/1.0");
  int code = conn.getResponseCode();
  java.io.InputStream is = (code >= 200 && code < 300) ? conn.getInputStream() : conn.getErrorStream();
  java.io.BufferedReader br = new java.io.BufferedReader(new java.io.InputStreamReader(is, java.nio.charset.StandardCharsets.UTF_8));
  StringBuilder sb = new StringBuilder();
  String line;
  while ((line = br.readLine()) != null) sb.append(line);
  br.close();
  conn.disconnect();
  if (code < 200 || code >= 300) {
    String msg = "HTTP " + code + " " + urlStr;
    fail("httpGet", msg);
    throw new Exception(msg);
  }
  apiOk("HTTP 200, bytes=" + sb.length());
  return sb.toString();
}

// ========= JSON Extractor =========
private String extractJsonString(String json, String key, int fromIdx) {
  int k = json.indexOf(key, fromIdx);
  if (k < 0) return null;
  int s = k + key.length();
  StringBuilder sb = new StringBuilder();
  boolean esc = false;
  for (int i = s; i < json.length(); i++) {
    char c = json.charAt(i);
    if (esc) { esc = false; continue; }
    if (c == '\\') { esc = true; continue; }
    if (c == '"') break;
    sb.append(c);
  }
  return sb.toString();
}

// ========= Config & Helpers =========
private void normalizeConfig(boolean writeDefaultsIfNull) {
  try {
    if (writeDefaultsIfNull && getExecutePeriodSeconds().isNull())
      setExecutePeriodSeconds(new BStatusNumeric(0));
    else if (getExecutePeriodSeconds().getStatus().isOk() && getExecutePeriodSeconds().getValue() > 0) {
      int v = clampInt((int)getExecutePeriodSeconds().getValue(), 60, 3600);
      setExecutePeriodSeconds(new BStatusNumeric(v));
    }
  } catch (Exception ignore) {}

  try {
    if (writeDefaultsIfNull && (getCountryCode().isNull() || !getCountryCode().getStatus().isOk()))
      setCountryCode(new BStatusString("US"));
    String cc = "US";
    if (getCountryCode().getStatus().isOk()) {
      String raw = getCountryCode().getValue();
      if (raw != null && !raw.trim().isEmpty()) cc = normalizeIso2(raw);
    }
    setCountryCode(new BStatusString(cc));
  } catch (Exception ignore) {}

  try { if (writeDefaultsIfNull && (getUpdateNow().isNull() || !getUpdateNow().getStatus().isOk()))
          setUpdateNow(new BStatusBoolean(false)); } catch (Exception ignore) {}
  try { if (writeDefaultsIfNull && (getLogToConsole().isNull() || !getLogToConsole().getStatus().isOk()))
          setLogToConsole(new BStatusBoolean(false)); } catch (Exception ignore) {}
}

private int clampInt(int v, int lo, int hi) { return Math.max(lo, Math.min(hi, v)); }

private String normalizeIso2(String raw) {
  if (raw == null) return "US";
  String r = raw.trim();
  if (r.equalsIgnoreCase("UK"))  r = "GB";
  if (r.equalsIgnoreCase("USA")) r = "US";
  if (!r.matches("(?i)^[A-Z]{2,3}(-[A-Z]{2,3})?$")) {
    fail("countryCode", "Invalid countryCode '" + raw + "'. Using 'US'.");
    return "US";
  }
  String[] parts = r.split("-");
  String normalized = parts[0].toUpperCase();
  if (parts.length > 1) normalized += "-" + parts[1].toLowerCase();
  return normalized;
}

private String computeNextHolidayString(java.time.LocalDate fromDate) {
  if (holidayByDate.isEmpty()) return null;
  java.util.ArrayList<String> dates = new java.util.ArrayList<>(holidayByDate.keySet());
  java.util.Collections.sort(dates);
  String fromIso = fromDate.toString();
  for (String d : dates) {
    if (d.compareTo(fromIso) >= 0) {
      java.time.LocalDate target = java.time.LocalDate.parse(d);
      long days = java.time.temporal.ChronoUnit.DAYS.between(fromDate, target);
      String nm = holidayByDate.get(d);
      return d + " (" + nm + "; in " + days + " days)";
    }
  }
  return null;
}

private javax.baja.schedule.BCalendarSchedule resolveCalendar() {
  try {
    if (getCalendarOrd().isNull()) {
      fail("resolveCalendar", "calendarOrd is NULL. Set it to a Calendar Schedule.");
      return null;
    }
    BObject o = getCalendarOrd().resolve().get();
    if (o instanceof javax.baja.schedule.BCalendarSchedule) return (javax.baja.schedule.BCalendarSchedule)o;
    fail("resolveCalendar", "calendarOrd resolved to " + (o != null ? o.getType() : "null") + " (expected Calendar Schedule).");
  } catch (Exception e) {
    fail("resolveCalendar", "Resolve error: " + e.getMessage());
  }
  return null;
}


```

</details>



<details>
<summary>🗓️ iCal Integration</summary>

Use this block to **subscribe** to an online iCalendar (`.ics`) feed (e.g., shared Google/Outlook/Apple calendar URLs) and expose “next event” details inside Niagara for schedule logic (holiday/vacation shutdowns, special events, etc.). This is designed for a **Program Object**—the Java is already done; this section just documents how to set it up.

The iCal program makes an HTTP GET request to a URL specified in its icsUrl slot, fetching a raw text file in the iCalendar (.ics) format. It then processes this text by looping through each VEVENT block, parsing the SUMMARY, LOCATION, DESCRIPTION, and DTSTART tags to create a list of EventInfo Java objects. Finally, it accesses the target BCalendarSchedule component via its calendarOrd slot, locks it, and dynamically adds new BDateSchedule children, each populated with the specific Year, Month, and Day derived from the event's start time.

> Note this is a concept idea that only works with CalenderSchedules. Future TODO will be to overhaul with generic weekly schedules.

---

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalAxPropSheetSnip.png" alt="iCal AX / N4 Property Sheet" width="850">
</p>

<p align="center">
  <img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/icalSnip.png" alt="iCal Wiresheet Snip" width="850">
</p>

---

### ⚙️ Slot Sheet (suggested)
| Slot Name               | Type             | Writable | Notes |
| ---                     | ---              | ---      | --- |
| `calendarUrl`           | `BStatusString`  | ✅       | Full HTTPS URL to the **.ics** feed (public/share link). |
| `internalUpdateSeconds` | `BStatusNumeric` | ✅       | How often to refresh, seconds (e.g., `21600` = 6h). |
| `updateNow`             | `BStatusBoolean` | ✅       | Toggle `true` to force an immediate fetch (auto-resets `false`). |
| `statusTrace`           | `BStatusString`  | ❌       | Short “OK / ERROR: …” health text. |
| `lastRefreshTs`         | `BStatusString`  | ❌       | Timestamp of last successful refresh. |
| `nextEventsJson`        | `BStatusString`  | ❌       | JSON array of upcoming events (already normalized in code). |
| `etagCache` (optional)  | `BStatusString`  | ❌       | If-None-Match cache to reduce bandwidth (if your code uses it). |

> **Tip:** The slot formerly called `pollSeconds` was renamed to `internalUpdateSeconds` for clarity.

---

### ✅ How to use
1. **Set `calendarUrl`** to a public/subscribable `.ics` link (not a file import).  
   - Google Calendar: “**Settings → Integrate calendar → Secret address in iCal format**”.  
   - Outlook/Apple: share/publish the calendar and copy the iCal URL.
2. **(Optional) Enable trigger:** Check **Execute On Change** for `updateNow` so a **true** write runs the fetch immediately.
3. **Refresh cadence:** The program’s internal timer uses `internalUpdateSeconds` to re-pull the feed on a fixed schedule.
4. **Consume results:** Read `nextEventsJson` (stringified JSON) for your logic—e.g., “if any event today tagged Public/Bank Holiday → disable schedules”.

---

### 🔎 Practical notes
- **Subscribe vs. Import:** Use a **URL subscription** so clients stay in sync; avoid one-time calendar file imports.  
- **Throttling:** Most calendar hosts update **every few hours**. Avoid setting `internalUpdateSeconds` too low.  
- **Null-safety:** If URL is empty or fetch fails, `statusTrace` shows the error and outputs remain unchanged.
- **Filtering:** Your Program Object’s Java already normalizes and filters events; this doc just standardizes the slots/UI.

---

### 💻 Java Code

> Testing on next space flight ical: https://nextspaceflight.com/calendar/


```java
////////////////////////////////////////////////////////////////
// Program Source — ICS Subscriber (v3 - Concurrency Fix)
////////////////////////////////////////////////////////////////

// Runtime
private Clock.Ticket ticket;
private long lastFetchMs = 0L;

// Small record for parsed events
class EventInfo implements Comparable<EventInfo> {
  java.util.Date startTime;
  java.util.Date endTime;   
  String summary;
  String location;       
  String description;   

  EventInfo(java.util.Date start, java.util.Date end, String sum, String loc, String desc) {
    this.startTime = start;
    this.endTime = end;
    this.summary = sum;
    this.location = loc;
    this.description = desc;
  }

  // Null-safe comparison
  public int compareTo(EventInfo o) {
    if (this.startTime == null && o.startTime == null) return 0;
    if (this.startTime == null) return -1;
    if (o.startTime == null) return 1;
    return this.startTime.compareTo(o.startTime);
  }
}

// ================= Lifecycle =================

public void onStart() throws Exception {
  log("onStart");
  getStatusTrace().setValue("Program started.");
  scheduleHeartbeat();
}

public void onExecute() throws Exception {
  // 1) Manual/External fetch trigger
  try {
    if (getUpdateNow().getStatus().isOk() && getUpdateNow().getValue()) {
      log("updateNow=TRUE → fetching ICS once");
      fetchAndParseIcsOnce();
      try { setUpdateNow(new BStatusBoolean(false)); } catch (Exception ignore) {}
    }
  } catch (Exception ignore) {}

  // 2) Heartbeat: recompute eventActive (no network)
  try { computeEventActiveToday(); } catch (Exception e) { log("eventActive error: " + e.getMessage()); }

  scheduleHeartbeat();
}

public void onStop() throws Exception {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  log("onStop");
  getStatusTrace().setValue("Program stopped.");
}

// ================= Heartbeat (internalUpdateSeconds) =================

private void scheduleHeartbeat() {
  if (ticket != null) { ticket.cancel(); ticket = null; }
  int secs = 10; // default 10s
  try {
    if (getInternalUpdateSeconds().getStatus().isOk())
      secs = (int)Math.max(2, Math.min(600, getInternalUpdateSeconds().getValue()));
    setInternalUpdateSeconds(new BStatusNumeric(secs));
  } catch (Exception ignore) {}
  // Use a shorter heartbeat (e.g., 60s) if you use the StringWritable
  ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(secs), BProgram.execute, null);
  log("next heartbeat in " + secs + "s");
}

// ================= Core: one-shot fetch + write =================

private void fetchAndParseIcsOnce() {
  long t0 = System.currentTimeMillis();

  String url = "https://calendar.google.com/calendar/ical/nextspaceflight.com_l328q9n2alm03mdukb05504c44%40group.calendar.google.com/public/basic.ics";
  try {
    if (getIcsUrl().getStatus().isOk() && !getIcsUrl().getValue().isEmpty())
      url = getIcsUrl().getValue();
    else
      setIcsUrl(new BStatusString(url));
  } catch (Exception ignore) {}

  BComponent calComp = resolveCalendar();
  if (calComp == null) {
    getStatusTrace().setValue("ERROR: calendarOrd does not resolve to a Calendar Schedule.");
    log("calendarOrd unresolved");
    return;
  } else {
    log("calendarOrd resolved → " + calComp.getType().toString());
  }

  java.net.HttpURLConnection conn = null;
  java.util.List<EventInfo> events = new java.util.ArrayList<>();
  try {
    log("GET " + url);
    java.net.URL u = new java.net.URL(url);
    conn = (java.net.HttpURLConnection)u.openConnection();
    conn.setRequestMethod("GET");
    conn.setConnectTimeout(10000);
    conn.setReadTimeout(10000);

    int code = conn.getResponseCode();
    java.io.InputStream is = (code >= 200 && code < 300) ? conn.getInputStream() : conn.getErrorStream();
    java.io.BufferedReader r = new java.io.BufferedReader(new java.io.InputStreamReader(is, "UTF-8"));

    events = parseIcsStream(r);
    r.close();

    if (code < 200 || code >= 300) throw new Exception("HTTP " + code);

    log("parsed future events: " + events.size());
  } catch (Exception e) {
    getStatusTrace().setValue("ERROR: fetch/parse " + e.getMessage());
    log("fetch error: " + e.getMessage());
    return;
  } finally {
    if (conn != null) conn.disconnect();
  }

  try {
    int added = updateCalendarChildren(calComp, events); // This is now thread-safe
    lastFetchMs = System.currentTimeMillis();

    getLastFetchTs().setValue(new java.util.Date(t0).toString());
    getEventsAdded().setValue(added);

    StringBuilder sb = new StringBuilder();
    if (!events.isEmpty()) {
      EventInfo next = events.get(0);
      String nextEventStr = next.summary + " @ " + next.startTime.toString();
      if (next.location != null && !next.location.isEmpty()) {
        nextEventStr += " (Loc: " + next.location + ")";
      }
      getNextEvent().setValue(nextEventStr);
      
      // Populate the string writable for ALL events
      for(EventInfo ev : events) {
        if(ev == null || ev.summary == null || ev.startTime == null) continue;
        sb.append("EVENT: ").append(ev.summary).append("\n");
        sb.append("  START: ").append(ev.startTime).append("\n");
        if(ev.endTime != null) sb.append("  END: ").append(ev.endTime).append("\n");
        if(ev.location != null) sb.append("  LOC: ").append(ev.location).append("\n");
        if(ev.description != null) sb.append("  DESC: ").append(ev.description).append("\n");
        sb.append("\n");
      }

    } else {
      getNextEvent().setValue("No upcoming events");
    }
    
    // Assuming you have a BStatusString slot named 'stringWritable'
    // getStringWritable().setValue(sb.toString());

    getStatusTrace().setValue("OK: Fetched " + events.size() + ", added " + added);
    log("update complete; added " + added);
  } catch (Exception e) {
    log("Niagara update error: " + e.getMessage());
    getStatusTrace().setValue("ERROR updating calendar: " + e.getMessage());
  }
}

// ================= ICS parse (Handles UTC DTSTART AND All-Day VALUE=DATE) =================
private java.util.List<EventInfo> parseIcsStream(java.io.BufferedReader reader) throws Exception {
  java.util.List<EventInfo> out = new java.util.ArrayList<>();
  
  java.text.SimpleDateFormat utcFormat = new java.text.SimpleDateFormat("yyyyMMdd'T'HHmmss'Z'");
  utcFormat.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
  
  java.text.SimpleDateFormat allDayFormat = new java.text.SimpleDateFormat("yyyyMMdd");
  allDayFormat.setTimeZone(java.util.Calendar.getInstance().getTimeZone()); // Use JACE's local timezone
  
  long now = System.currentTimeMillis();
  String line; 
  boolean inVEvent=false; 
  
  String sum = null;
  java.util.Date start = null;
  java.util.Date end = null;
  String loc = null;
  String desc = null;

  while ((line = reader.readLine()) != null) {
    if ("BEGIN:VEVENT".equals(line)) { 
      inVEvent=true; 
      sum = null; start = null; end = null; loc = null; desc = null; // Reset for new event
      log("... found BEGIN:VEVENT");
      continue; 
    }
    
    if ("END:VEVENT".equals(line))   {
      if (inVEvent && sum != null && start != null && start.getTime() > now) {
        log("... adding event: " + sum + " @ " + start.toString());
        out.add(new EventInfo(start, end, sum, loc, desc)); 
      } else if (inVEvent) {
        log("... skipping event (missing summary/start, or is in the past)");
      }
      inVEvent=false; 
      continue;
    }
    
    if (!inVEvent) continue;
    
    if (line.startsWith("SUMMARY:")) {
      sum = line.substring(8);
      log("       SUMMARY: " + sum);
    }
    else if (line.startsWith("LOCATION:")) {
      loc = line.substring(9);
      log("      LOCATION: " + loc);
    }
    else if (line.startsWith("DESCRIPTION:")) {
      desc = line.substring(12); // Does not handle multi-line descriptions
      log("   DESCRIPTION: " + desc);
    }
    
    // --- DTSTART Parsers ---
    else if (line.startsWith("DTSTART;VALUE=DATE:")) {
      try {
        String dateStr = line.substring(line.indexOf(':') + 1).trim();
        if (dateStr.length() > 8) dateStr = dateStr.substring(0, 8); // Clean extra chars
        start = allDayFormat.parse(dateStr); 
        log("       DTSTART (All-Day): " + start.toString());
      } catch (java.text.ParseException pe) { 
        log("Failed to parse all-day date: " + line);
        start = null; 
      }
    }
    else if (line.startsWith("DTSTART:")) {
      try { 
        String timeStr = line.substring(line.indexOf(':') + 1).trim();
        start = utcFormat.parse(timeStr); 
        log("       DTSTART (UTC): " + start.toString());
      } catch (java.text.ParseException pe) { 
        log("Skipping non-UTC time format: " + line);
        start = null; 
      }
    }
    
    // --- DTEND Parsers ---
    else if (line.startsWith("DTEND;VALUE=DATE:")) {
      try {
        String dateStr = line.substring(line.indexOf(':') + 1).trim();
        if (dateStr.length() > 8) dateStr = dateStr.substring(0, 8);
        end = allDayFormat.parse(dateStr); 
        log("         DTEND (All-Day): " + end.toString());
      } catch (java.text.ParseException pe) { 
        log("Failed to parse all-day end date: " + line);
        end = null; 
      }
    }
    else if (line.startsWith("DTEND:")) {
      try { 
        String timeStr = line.substring(line.indexOf(':') + 1).trim();
        end = utcFormat.parse(timeStr); 
        log("         DTEND (UTC): " + end.toString());
      } catch (java.text.ParseException pe) { 
        log("Skipping non-UTC end time format: " + line);
        end = null; 
      }
    }
  }
  java.util.Collections.sort(out);
  return out;
}

// ================= Write BDateSchedule children (all-day markers) =================

private int updateCalendarChildren(BComponent parentCal, java.util.List<EventInfo> events) {
  String prefix = "";
  if (getNamePrefix().getStatus().isOk()) prefix = getNamePrefix().getValue();

  int max = 10;
  if (getMaxEvents().getStatus().isOk()) max = (int)getMaxEvents().getValue();

  log("Preparing to add events: parsed=" + events.size() + ", max=" + max + ", prefix='" + prefix + "'");

  int removed = 0;
  int added = 0;

  // Lock the calendar component to prevent race-condition crashes
  synchronized (parentCal) {
  
    // --- 1. Remove our prior children ---
    BComponent[] kids = parentCal.getChildComponents(); // Get a snapshot of children
    for (BComponent k : kids) {
      if (prefix.isEmpty() || k.getName().startsWith(prefix)) {
        try { 
          parentCal.remove(k.getName()); 
          removed++; 
        } catch (Exception ignore) {}
      }
    }
    log("Removed prior children with prefix: " + removed);

    // --- 2. Add new children ---
    java.util.Calendar cal = java.util.Calendar.getInstance(); // Use JACE's local timezone

    for (int i=0; i<events.size() && i<max; i++) {
      EventInfo ev = events.get(i);

      // --- Start of new/modified name logic ---
      
      // 1. Sanitize the summary (replace bad chars with _)
      String cleanSummary = ev.summary.replaceAll("[^a-zA-Z0-9_]", "_");
      
      // 2. Collapse multiple underscores (e.g., "___") into one
      cleanSummary = cleanSummary.replaceAll("__+", "_"); 
      
      // 3. Truncate the summary part to a shorter length
      int maxSummaryLength = 30; // <-- YOU CAN CHANGE THIS VALUE
      if (cleanSummary.length() > maxSummaryLength) {
        cleanSummary = cleanSummary.substring(0, maxSummaryLength);
      }
      
      // 4. Add the prefix (if any) and the unique index
      String nm = prefix + cleanSummary + "_" + (i+1);
      // --- End of new/modified name logic ---

      try {
        cal.setTime(ev.startTime); // Set calendar to the event's start time

        BDateSchedule ds = new BDateSchedule();
        ds.setYear(cal.get(java.util.Calendar.YEAR));
        ds.setMonth(BMonth.make(cal.get(java.util.Calendar.MONTH)));   // 0..11
        ds.setDay(cal.get(java.util.Calendar.DAY_OF_MONTH));

        parentCal.add(nm, ds);
        added++;
      } catch (Exception e) {
        log("add '" + nm + "' failed: " + e.getMessage());
      }
    }
    log("Added new children: " + added);
    
  } // --- End of synchronized block ---

  return added;
}

// ================= eventActive (today matches any BDateSchedule) =================

private void computeEventActiveToday() {
  BComponent cal = resolveCalendar();
  if (cal == null) return;

  java.util.Calendar now = java.util.Calendar.getInstance(); // Uses JACE's local timezone
  final int y = now.get(java.util.Calendar.YEAR);
  final int m = now.get(java.util.Calendar.MONTH);         // 0..11
  final int d = now.get(java.util.Calendar.DAY_OF_MONTH);  // 1..31

  boolean active = false;
  // We must also lock here when reading, to be fully thread-safe
  synchronized (cal) {
    for (BComponent c : cal.getChildComponents()) {
      try {
        if (c instanceof BDateSchedule) {
          BDateSchedule ds = (BDateSchedule) c;
          if (ds.getYear() == y && ds.getMonth() == m && ds.getDay() == d) {
            active = true; break;
          }
        }
      } catch (Exception ignore) {}
    }
  } // --- End of synchronized block ---

  try { setEventActive(new BStatusBoolean(active)); } catch (Exception ignore) {}
  if (active) try { getStatusTrace().setValue("OK: eventActive=true (today)"); } catch (Exception ignore) {}
}

// ================= Helpers =================

private BComponent resolveCalendar() {
  try {
    if (getCalendarOrd().isNull()) return null;
    BObject o = getCalendarOrd().resolve().get();
    if (o instanceof javax.baja.schedule.BCalendarSchedule) return (BComponent)o;
  } catch (Exception e) { log("resolve error: " + e.getMessage()); }
  return null;
}

private void log(String s) {
  try {
    if (getLogToConsole().getStatus().isOk() && getLogToConsole().getValue())
      System.out.println("[iCal_Program] " + s);
  } catch (Exception ignore) {}
}
```

</details>


