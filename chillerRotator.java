import java.time.Clock;

Clock.Ticket ticket;
long lastMainLogicRun = 0;

// Temperature staging timer variables
long tempHighStartTime = 0;
boolean tempHighActive = false;

static final int[][] DUTY_ROTATIONS = {
        { 0, 1, 2, 3, 4, 5, 6, 7 }, // Rotation 1
        { 1, 2, 3, 4, 5, 6, 7, 0 }, // Rotation 2
        { 2, 3, 4, 5, 6, 7, 0, 1 }, // Rotation 3
        { 3, 4, 5, 6, 7, 0, 1, 2 }, // Rotation 4
        { 4, 5, 6, 7, 0, 1, 2, 3 }, // Rotation 5
        { 5, 6, 7, 0, 1, 2, 3, 4 }, // Rotation 6
        { 6, 7, 0, 1, 2, 3, 4, 5 }, // Rotation 7
        { 7, 0, 1, 2, 3, 4, 5, 6 }, // Rotation 8
        { 0, 1, 2, 3, 4, 5, 6, 7 } // Rotation 9 (reset to 1)
};

public void onStart() throws Exception {
    // Set safe and reasonable defaults for Metric units (°C and MW)
    ((BStatusNumeric) getComponent().get("waterTemp")).setValue(12.0); // °C
    ((BStatusNumeric) getComponent().get("tempSetpoint")).setValue(18.0); // °C
    ((BStatusNumeric) getComponent().get("loadMW")).setValue(0.0); // MW
    ((BStatusNumeric) getComponent().get("updateIntervalSeconds")).setValue(300.0); // seconds (5 minutes)
    ((BStatusNumeric) getComponent().get("currentDutyCycle")).setValue(1); // Start with Duty 1

    ((BStatusBoolean) getComponent().get("systemEnable")).setValue(false); // Default off

    ((BStatusBoolean) getComponent().get("bladeRoom1Demand")).setValue(false);
    ((BStatusBoolean) getComponent().get("bladeRoom2Demand")).setValue(false);
    ((BStatusBoolean) getComponent().get("bladeRoom3Demand")).setValue(false);

    // Default all chillers available
    for (int i = 1; i <= 8; i++) {
        ((BStatusBoolean) getComponent().get("chiller" + i + "Available")).setValue(true);
    }

    lastMainLogicRun = System.currentTimeMillis();
    updateTimer();
}

public void onExecute() throws Exception {
    updateTimer();

    long now = System.currentTimeMillis();
    if (getComponent() == null)
        return;

    // NULL check for all inputs (every 10s)
    String[] inputs = {
            "waterTemp", "tempSetpoint", "loadMW",
            "systemEnable", "currentDutyCycle",
            "bladeRoom1Demand", "bladeRoom2Demand", "bladeRoom3Demand",
            "chiller1Available", "chiller2Available", "chiller3Available", "chiller4Available",
            "chiller5Available", "chiller6Available", "chiller7Available", "chiller8Available"
    };

    for (String inputName : inputs) {
        if (getComponent().getLinks(getComponent().getSlot(inputName)).length == 0) {
            if (getComponent().get(inputName) instanceof BStatusNumeric) {
                ((BStatusNumeric) getComponent().get(inputName)).setValue(0);
                ((BStatusNumeric) getComponent().get(inputName)).setStatus(BStatus.NULL);
            } else if (getComponent().get(inputName) instanceof BStatusBoolean) {
                ((BStatusBoolean) getComponent().get(inputName)).setValue(false);
                ((BStatusBoolean) getComponent().get(inputName)).setStatus(BStatus.NULL);
            }
        }
    }

    // Main logic: only every updateIntervalSeconds (default 300s)
    double intervalSec = ((BStatusNumeric) getComponent().get("updateIntervalSeconds")).getValue();
    if ((now - lastMainLogicRun) / 1000 < intervalSec)
        return;
    lastMainLogicRun = now;

    // Proceed with logic only if system is enabled
    boolean systemEnable = ((BStatusBoolean) getComponent().get("systemEnable")).getValue();
    if (!systemEnable) {
        disableAllChillers();
        return;
    }

    double waterTemp = ((BStatusNumeric) getComponent().get("waterTemp")).getValue();
    double tempSet = ((BStatusNumeric) getComponent().get("tempSetpoint")).getValue();
    double load = ((BStatusNumeric) getComponent().get("loadMW")).getValue();

    int chillersByTemp = handleTemperatureStaging(waterTemp, tempSet);
    int chillersByLoad = handleLoadStaging(load);
    int chillersByBladeRooms = handleBladeRoomDemand();

    int requiredChillers = Math.max(chillersByTemp, chillersByLoad) + chillersByBladeRooms;

    // Use Enum point for rotation
    int dutyScheduleIndex = (int) (((BStatusNumeric) getComponent().get("currentDutyCycle")).getValue()) - 1;
    if (dutyScheduleIndex < 0 || dutyScheduleIndex >= DUTY_ROTATIONS.length) {
        dutyScheduleIndex = 0; // Fallback to Rotation 1
    }

    boolean[] chillerAvailable = new boolean[8];
    for (int i = 0; i < 8; i++) {
        chillerAvailable[i] = ((BStatusBoolean) getComponent().get("chiller" + (i + 1) + "Available")).getValue();
    }

    // Enable chillers based on availability and duty rotation
    boolean[] chillerEnable = new boolean[8];
    int enabledCount = 0;
    int[] rotationOrder = DUTY_ROTATIONS[dutyScheduleIndex];

    for (int i = 0; i < 8 && enabledCount < requiredChillers; i++) {
        int chillerIdx = rotationOrder[i];
        if (chillerAvailable[chillerIdx]) {
            chillerEnable[chillerIdx] = true;
            enabledCount++;
        }
    }

    for (int i = 0; i < 8; i++) {
        ((BStatusBoolean) getComponent().get("chiller" + (i + 1) + "Enable")).setValue(chillerEnable[i]);
    }

    ((BStatusNumeric) getComponent().get("currentSequence")).setValue(dutyScheduleIndex + 1); // Show 1 to 9
}

public void onStop() throws Exception {
    if (ticket != null)
        ticket.cancel();
}

void updateTimer() {
    if (ticket != null)
        ticket.cancel();
    ticket = Clock.schedule(getComponent(), BRelTime.makeSeconds(10), BProgram.execute, null);
}

void disableAllChillers() {
    for (int i = 1; i <= 8; i++) {
        ((BStatusBoolean) getComponent().get("chiller" + i + "Enable")).setValue(false);
    }
}

// ------------------- SCENARIO 1 — Temperature Staging -------------------
int handleTemperatureStaging(double waterTemp, double tempSet) {
    if (waterTemp >= tempSet + 2.0) {
        return 8; // Immediate max chillers
    } else if (waterTemp >= tempSet + 1.0) {
        if (!tempHighActive) {
            tempHighActive = true;
            tempHighStartTime = System.currentTimeMillis();
        } else {
            long elapsed = (System.currentTimeMillis() - tempHighStartTime) / 1000;
            if (elapsed >= 600) {
                return 1; // After 10 min, stage one more chiller
            }
        }
    } else {
        tempHighActive = false;
        tempHighStartTime = 0;
    }
    return 0;
}

// ------------------- SCENARIO 2 — Load Staging -------------------
int handleLoadStaging(double load) {
    double[] thresholds = { 1.3, 2.6, 3.9, 5.2, 6.5, 7.8, 9.1, 10.4 };
    int chillersRequired = 1;
    for (int i = thresholds.length - 1; i >= 0; i--) {
        if (load > thresholds[i]) {
            chillersRequired = i + 2;
            break;
        }
    }
    return chillersRequired;
}

// ------------------- SCENARIO 3 — BladeRoom Demand -------------------
int handleBladeRoomDemand() {
    int bladeRoomsDemanding = 0;
    if (((BStatusBoolean) getComponent().get("bladeRoom1Demand")).getValue())
        bladeRoomsDemanding++;
    if (((BStatusBoolean) getComponent().get("bladeRoom2Demand")).getValue())
        bladeRoomsDemanding++;
    if (((BStatusBoolean) getComponent().get("bladeRoom3Demand")).getValue())
        bladeRoomsDemanding++;
    return bladeRoomsDemanding;
}
