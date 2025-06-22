# 🧠 OptimalStartModel – API Usage Guide

This cheat sheet describes how to use the `OptimalStartModel` class to simulate a self-tuning optimal start controller in Python.

---

### 🔧 1. Initialization

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

### 🔽 3. Input Slots (Setters)

| Method                                 | Type    | Description                                                         |
| -------------------------------------- | ------- | ------------------------------------------------------------------- |
| `set_zone_temp(value)`                 | `float` | Current zone temperature (°F)                                       |
| `set_target_zone_temp_setpoint(value)` | `float` | Occupied setpoint (°F)                                              |
| `set_schedule_next_value(value)`       | `bool`  | Whether the next schedule event is occupied                         |
| `set_schedule_next_event_time(value)`  | `int`   | Future event timestamp in ms (e.g., `time.time() * 1000 + 600_000`) |
| `set_clear_history_now(value)`         | `bool`  | Set to `True` to reset performance history                          |
| `set_max_minutes_allowed(value)`       | `float` | Max allowed runtime for a start sequence                            |
| `set_temp_tolerance(value)`            | `float` | Acceptable deviation from setpoint (e.g., `1.0`)                    |
| `set_command_off_delay_seconds(value)` | `float` | Countdown delay after reaching setpoint                             |

---

### 🔼 4. Output Slots (Getters)

| Method                           | Returns     | Description                        |
| -------------------------------- | ----------- | ---------------------------------- |
| `get_minutes_to_setpoint()`      | `float`     | Time required to reach setpoint    |
| `get_equipment_start_command()`  | `bool/None` | `True` to start, `None` for idle   |
| `get_is_running()`               | `bool`      | Whether a learning run is active   |
| `get_zone_at_temp_tolerance()`   | `bool`      | `True` if zone is within tolerance |
| `get_degrees_per_minute_heat()`  | `float`     | Learned heating rate               |
| `get_degrees_per_minute_cool()`  | `float`     | Learned cooling rate               |
| `get_status_log()`               | `str`       | Recent status message              |
| `get_countdown_to_null_status()` | `str`       | Description of off-delay state     |

---

### 🧪 5. Example Usage Per Mechanical System (AHU, Heat Pump, RTU, etc.)

```python
import time
from py_opt_start import OptimalStartModel

# Setup
model = OptimalStartModel()
model.start()

# Configure test values
model.set_zone_temp(80.0)
model.set_target_zone_temp_setpoint(72.0)
model.set_schedule_next_value(True)
model.set_schedule_next_event_time((time.time() + 600) * 1000)  # 10 minutes from now

# Run loop to simulate time passing
for i in range(5):
    print(f"\n--- Cycle {i + 1} ---")
    model.execute()
    print(f"Minutes to Setpoint: {model.get_minutes_to_setpoint():.2f}")
    print(f"Start Command: {model.get_equipment_start_command()}")
    print(f"Status: {model.get_status_log()}")
```


