# 🧠 OptimalStartModel – API Usage Guide

This cheat sheet describes how to use the `OptimalStartModel` class to simulate a self-tuning optimal start controller in Python.

---

### 🔧 1. Setup for each AHU

```python
from py_opt_start import OptimalStartModel

# Create and initialize the model
model = OptimalStartModel()
model.start()
```

---

### 🔁 2. Execution

Call `.execute()` each timestep (e.g., every minute) to evaluate whether the unit should start and to update learning.

```python
model.execute()
```

---


### ✅ 3. Input Slots (Setters)

| Method | Type | Description |
| :--- | :--- | :--- |
| `set_zone_temp(value)` | `float` | Current zone temperature (°F) |
| `set_target_zone_temp_setpoint(value)` | `float` | Occupied setpoint (°F) |
| `set_schedule_next_value(value)` | `bool` | Whether the next schedule event is occupied |
| `set_schedule_next_event_time(value)` | `int` | Future event timestamp in ms (e.g., `time.time() * 1000 + 600_000`) |
| `set_clear_history_now(value)` | `bool` | Set to `True` to reset performance history |
| `set_max_minutes_allowed(value)` | `float` | Max allowed runtime for a start sequence |
| `set_temp_tolerance(value)` | `float` | Acceptable deviation from setpoint (e.g., `1.0`) |
| **`set_command_off_delay_seconds(value)`** | `float` | **🆕 Countdown delay in seconds that starts after the optimal start run ends.** |


### ✅ 4. Output Slots (Getters)

| Method | Returns | Description |
| :--- | :--- | :--- |
| **`get_minutes_to_setpoint()`** | `float` | **🆕 Estimated time** required to reach setpoint based on the learning model. |
| `get_equipment_start_command()` | `bool/None` | `True` to start, `None` for idle |
| `get_is_running()` | `bool` | `True` if a learning run is active (from start until schedule is occupied). |
| `get_zone_at_temp_tolerance()` | `bool` | `True` if zone is within the setpoint tolerance. |
| `get_degrees_per_minute_heat()` | `float` | Learned heating rate (°F / min). |
| `get_degrees_per_minute_cool()` | `float` | Learned cooling rate (°F / min). |
| `get_status_log()` | `str` | Recent status message with timestamp. |
| **`get_countdown_to_null_status()`** | `bool` | **🆕 Returns `True` only when the off-delay countdown is active.** |
| **`get_warmup_time_minutes()`** | `float` | **🆕 A live stopwatch of how long the current run has been active.** |
| **`get_current_history_record_count()`**| `int` | **🆕 The total number of HEAT and COOL performance records being stored.** |


