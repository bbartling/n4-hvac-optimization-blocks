import time
import datetime
import math
from collections import deque

class PerformanceRecord:
    """
    Stores raw performance data from a single HVAC run.
    Corresponds to the inner static class PerformanceRecord in the Java code.
    """
    def __init__(self, timestamp_ms, duration_minutes, delta_t, mode,
                 zone_temp_start, outdoor_temp_start):
        self.timestamp_ms = timestamp_ms
        self.duration_minutes = duration_minutes # t (our y-value for regression)
        self.delta_t = delta_t                 # deltaT (used for x-value delta_t^2)
        self.mode = mode                       # 'HEAT' or 'COOL'
        self.zone_temp_start = zone_temp_start
        self.outdoor_temp_start = outdoor_temp_start # Store NaN if not available

    def __repr__(self):
        """Provides a clean string representation for history log."""
        dt_object = datetime.datetime.fromtimestamp(self.timestamp_ms / 1000)
        oat_str = f"{self.outdoor_temp_start:.1f}" if not math.isnan(self.outdoor_temp_start) else "N/A"
        return (f"t: {self.duration_minutes:.1f}, dT: {self.delta_t:.1f}, "
                f"ZS: {self.zone_temp_start:.1f}, OAT: {oat_str} "
                f"(Date: {dt_object.strftime('%y-%m-%d %H:%M')})")

class OptimalStartModel1:
    """
    Python implementation of the self-tuning Optimal Start logic using
    the quadratic Model 1 (t = a*dT^2 + b), storing parameters internally.
    Matches the latest Java ProgramObject implementation.
    """

    # --- Default constants ---
    DEFAULT_ALPHA_A = 0.1  # Default slope for t = a*dT^2 + b
    DEFAULT_ALPHA_B = 5.0  # Default intercept
    DEFAULT_RATE_DEG_PER_MIN = 0.1 # Default for reference output

    def __init__(self, config=None):
        """Initializes the model."""
        # --- Internal State (Unchanged) ---
        self._is_optimal_start_running = False
        self._start_timestamp_ms = 0
        self._last_start_trigger_timestamp_ms = 0
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._is_off_delay_active = False
        self._off_delay_start_time_ms = 0
        self._zone_temp_at_start = float('nan')
        self._outdoor_temp_at_start = float('nan')

        # --- "Under the Hood" Learned Parameters (Unchanged) ---
        self._alpha_a_heat = self.DEFAULT_ALPHA_A
        self._alpha_b_heat = self.DEFAULT_ALPHA_B
        self._alpha_a_cool = self.DEFAULT_ALPHA_A
        self._alpha_b_cool = self.DEFAULT_ALPHA_B

        # --- Data Histories (Unchanged) ---
        self._heat_history = deque()
        self._cool_history = deque()

        # --- Configurable Parameters (Unchanged) ---
        self._config = {
            "max_minutes_allowed": 180.0,
            "temp_tolerance": 0.5,
            "history_records_to_retain": 10,
            "command_off_delay_seconds": 60.0, # Default changed to 60.0 for consistency
            "print_to_console_log": False
        }
        if config:
            self._config.update(config)

        # --- Inputs (Simulated Slots - Unchanged) ---
        self._zone_temp = float('nan')
        self._outdoor_temp = float('nan')
        self._target_zone_temp_setpoint = float('nan')
        self._schedule_next_value = None
        self._schedule_next_event_time_ms = 0
        self._clear_history_now = False

        # --- Outputs (Simulated Slots - MATCHING JAVA VERSION ---
        self._is_running = False
        self._minutes_to_setpoint_predicted = self._config["max_minutes_allowed"] # RENAMED
        self._degrees_per_minute_heat = self.DEFAULT_RATE_DEG_PER_MIN
        self._degrees_per_minute_cool = self.DEFAULT_RATE_DEG_PER_MIN
        self._equipment_start_command = None
        self._zone_at_temp_tolerance = False
        self._status_log = "[Init] Optimal Start Model 1 initialized."
        self._current_run_elapsed_minutes = 0.0 # RENAMED
        self._countdown_to_null_status = False
        self._current_history_record_count = 0
        self._history_log_text = ""
        
        # --- NEW OUTPUT SLOTS FOR PERFORMANCE TRACKING ---
        self._last_run_predicted_minutes = 0.0
        self._last_run_actual_minutes = 0.0
        self._last_run_error_minutes = 0.0

        # --- Initialization ---
        self._update_model() # Run once on start to set initial values


    def execute(self):
        """Runs a single execution cycle."""
        current_time_ms = int(time.time() * 1000)

        # --- Input Validation ---
        if not self._validate_inputs():
            self._force_shutdown("Input validation failed")
            return

        self._update_zone_at_temp_tolerance()

        if self.get_clear_history_now():
            self._clear_history()
            self.set_clear_history_now(False)

        # --- Main State Machine ---
        if self._is_optimal_start_running:
            # STATE 1: ACTIVE RUN
            self._monitor_active_run(current_time_ms)
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)
        else:
            # STATE 2: NOT RUNNING
            self._update_idle_estimate()
            self._update_equipment_start_command(current_time_ms)

        # --- Optional Logging ---
        if self._config["print_to_console_log"]:
            self._log_debug_status()

    # --- Core Logic Methods ---
    # ... (all core logic methods remain unchanged) ...
    def _update_equipment_start_command(self, current_time_ms):
        """Handles starting a new run or managing the off-delay countdown."""
        # 1. Manage Off-Delay Timer
        if self._is_off_delay_active:
            elapsed_seconds = (current_time_ms - self._off_delay_start_time_ms) / 1000.0
            delay_duration = self._config["command_off_delay_seconds"]

            if elapsed_seconds >= delay_duration:
                # Timer expired
                self._is_off_delay_active = False
                self._set_equipment_start_command(None)
                self._set_countdown_to_null_status(False)
                self._set_formatted_status_log("Off-delay expired. Command released to NULL.")
            else:
                # Timer still running
                self._set_countdown_to_null_status(True)
                remaining_sec = int(delay_duration - elapsed_seconds)
                self._set_formatted_status_log(f"Command off-delay active. {remaining_sec}s remaining.")
            return

        # 2. Determine if a start is needed
        is_next_period_occupied = self.get_schedule_next_value()
        start_condition_met = False

        if is_next_period_occupied:
            next_event_time_ms = self.get_schedule_next_event_time_ms()
            time_to_next_minutes = max(0, (next_event_time_ms - current_time_ms) / 60000.0)
            # RENAMED GETTER
            optimal_start_minutes = self.get_minutes_to_setpoint_predicted()

            if optimal_start_minutes >= time_to_next_minutes and time_to_next_minutes > 0.1:
                 start_condition_met = True

        # 3. Set Final Command Output
        if start_condition_met:
            self._start_optimal_start_sequence(current_time_ms)
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)
        else:
            # Start the off-delay if the command was just running
            if self.get_equipment_start_command() is True:
                self._is_off_delay_active = True
                self._off_delay_start_time_ms = current_time_ms
                self._set_countdown_to_null_status(True)
                self._set_formatted_status_log("Entering command off-delay countdown...")
            elif self.get_equipment_start_command() is None and not self._is_off_delay_active:
                 self._set_countdown_to_null_status(False)


    def _start_optimal_start_sequence(self, current_time_ms):
        """Initiates a new heating or cooling run."""
        if self.get_zone_at_temp_tolerance():
            self._set_formatted_status_log("[Start] Skipping: Zone temp already within tolerance.")
            # RENAMED SETTER
            self._set_minutes_to_setpoint_predicted(0.0)
            return

        # --- NEW: Snapshot prediction and clear last run data ---
        prediction = self.get_minutes_to_setpoint_predicted()
        self._set_last_run_predicted_minutes(prediction)
        self._set_last_run_actual_minutes(0.0)
        self._set_last_run_error_minutes(0.0)
        # --------------------------------------------------------

        # Record initial conditions
        self._zone_temp_at_start = self.get_zone_temp()
        self._outdoor_temp_at_start = self.get_outdoor_temp()

        # Reset run state variables
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._start_timestamp_ms = current_time_ms
        self._is_optimal_start_running = True
        self._last_start_trigger_timestamp_ms = current_time_ms
        self._set_is_running(True)
        # RENAMED SETTER
        self._set_current_run_elapsed_minutes(0.0)

        start_temp_str = f"{self._zone_temp_at_start:.1f}F" if not math.isnan(self._zone_temp_at_start) else "N/A"
        self._set_formatted_status_log(f"[Start] Optimal Start initiated. Predicted: {prediction:.1f} min. Start Temp: {start_temp_str}")


    def _monitor_active_run(self, current_time_ms):
        """Monitors progress during an active optimal start run."""
        elapsed_minutes = (current_time_ms - self._start_timestamp_ms) / 60000.0
        # RENAMED SETTER
        self._set_current_run_elapsed_minutes(elapsed_minutes)

        # 1. Check if setpoint was met for the first time
        if self.get_zone_at_temp_tolerance() and not self._setpoint_was_met_during_run:
            self._setpoint_was_met_during_run = True
            self._minutes_to_reach_setpoint = elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Target met in {elapsed_minutes:.1f} min. Stored value.")

        # 2. Check for stop conditions
        schedule_still_occupied = self.get_schedule_next_value()
        inputs_valid = self._validate_inputs()

        if not schedule_still_occupied or not inputs_valid:
            stop_reason = "Schedule now unocc" if not schedule_still_occupied else "Inputs invalid"
            final_performance_minutes = self._minutes_to_reach_setpoint if self._setpoint_was_met_during_run else elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] {stop_reason}. Recording performance using {final_performance_minutes:.1f} min.")
            self._stop_and_record_performance(final_performance_minutes)


    def _stop_and_record_performance(self, actual_minutes):
        """Ends the current run and records performance data."""
        self._is_optimal_start_running = False
        self._set_is_running(False)
        # RENAMED SETTER
        self._set_current_run_elapsed_minutes(0.0)

        # --- NEW: Set final "stopwatch" and error values ---
        self._set_current_run_elapsed_minutes(actual_minutes)
        self._set_last_run_actual_minutes(actual_minutes)

        last_prediction = self.get_last_run_predicted_minutes()
        error = last_prediction - actual_minutes
        self._set_last_run_error_minutes(error)
        # ---------------------------------------------------

        zone_start = self._zone_temp_at_start
        zone_target = self.get_target_zone_temp_setpoint()
        outdoor_start = self._outdoor_temp_at_start

        if math.isnan(zone_start) or math.isnan(zone_target):
             self._set_formatted_status_log("[Record] Invalid start/target temp. Performance not recorded.")
             return

        # THIS IS THE KEY: We use the *total* temp change achieved
        delta_t_achieved = abs(zone_target - zone_start)

        if actual_minutes > 0.1 and delta_t_achieved > 0.1:
            mode = "HEAT" if zone_start < zone_target else "COOL"

            new_record = PerformanceRecord(
                timestamp_ms=int(time.time() * 1000),
                duration_minutes=actual_minutes,
                delta_t=delta_t_achieved,
                mode=mode,
                zone_temp_start=zone_start,
                outdoor_temp_start=outdoor_start
            )

            if mode == "HEAT":
                self._heat_history.append(new_record)
            else:
                self._cool_history.append(new_record)

            self._set_formatted_status_log(
                f"[{mode}] run recorded (t={actual_minutes:.1f}, dT={delta_t_achieved:.1f}, Err={error:.1f}m)"
            )
            self._update_model()
        else:
           self._set_formatted_status_log("[Record] Run too short or no temp change. Performance not recorded.")

        self._zone_temp_at_start = float('nan')
        self._outdoor_temp_at_start = float('nan')


    def _update_model(self):
        """Updates Model 1 quadratic parameters (a, b) using linear regression."""
        self._prune_history()

        # 1. Tune Quadratic Parameters (Internal)
        heat_alphas = self._compute_regression_for_mode("HEAT")
        cool_alphas = self._compute_regression_for_mode("COOL")

        self._alpha_a_heat, self._alpha_b_heat = heat_alphas
        self._alpha_a_cool, self._alpha_b_cool = cool_alphas

        # 2. Calculate and Update Reference Average Rate (Output)
        avg_heat_rate = self._compute_average_rate(self._heat_history)
        avg_cool_rate = self._compute_average_rate(self._cool_history)

        self._set_degrees_per_minute_heat(avg_heat_rate if avg_heat_rate > 0 else self.DEFAULT_RATE_DEG_PER_MIN)
        self._set_degrees_per_minute_cool(avg_cool_rate if avg_cool_rate > 0 else self.DEFAULT_RATE_DEG_PER_MIN)

        # 3. Update History Count and Log Text
        self._set_current_history_record_count(len(self._heat_history) + len(self._cool_history))
        self._update_history_log_text()

        # 4. Optional console logging
        if self._config["print_to_console_log"]:
            print("--- [Model 1 Update] ---")
            print(f"HEAT Model: t = {self._alpha_a_heat:.3f} * (dT^2) + {self._alpha_b_heat:.2f}")
            print(f"COOL Model: t = {self._alpha_a_cool:.3f} * (dT^2) + {self._alpha_b_cool:.2f}")
            print(f"Writing to SLOT degreesPerMinuteHeat (Avg): {avg_heat_rate:.3f}")
            print(f"Writing to SLOT degreesPerMinuteCool (Avg): {avg_cool_rate:.3f}")
            print("-------------------------")


    def _update_idle_estimate(self):
        """Calculates the estimated minutes to setpoint using the quadratic model."""
        if self.get_zone_at_temp_tolerance():
            self._set_minutes_to_setpoint_predicted(0.0) # RENAMED
            return

        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()

        if math.isnan(zone) or math.isnan(target):
             self._set_minutes_to_setpoint_predicted(self._config["max_minutes_allowed"]) # RENAMED
             return

        delta_t = abs(target - zone)
        max_minutes = self._config["max_minutes_allowed"]
        estimated_minutes = max_minutes

        # t_opt = alpha_a * (deltaT^2) + alpha_b
        if zone < target: # Heating needed
            a = self._alpha_a_heat
            b = self._alpha_b_heat
            estimated_minutes = (a * (delta_t ** 2)) + b
        elif zone > target: # Cooling needed
            a = self._alpha_a_cool
            b = self._alpha_b_cool
            estimated_minutes = (a * (delta_t ** 2)) + b
        else:
             estimated_minutes = 0.0

        estimated_minutes = max(0.0, estimated_minutes)
        self._set_minutes_to_setpoint_predicted(min(estimated_minutes, max_minutes)) # RENAMED


    # --- Regression and History Helpers ---

    def _compute_regression_for_mode(self, mode):
        """Performs Simple Linear Regression: y = mx + c where y = t, x = delta_t^2."""
        history = self._heat_history if mode == "HEAT" else self._cool_history

        if len(history) < 2:
            return self.DEFAULT_ALPHA_A, self.DEFAULT_ALPHA_B

        n = len(history)
        sum_x = sum_y = sum_xy = sum_x_sq = 0.0

        for record in history:
            x = record.delta_t ** 2
            y = record.duration_minutes
            sum_x += x
            sum_y += y
            sum_xy += x * y
            sum_x_sq += x * x

        denominator = (n * sum_x_sq - sum_x ** 2)
        if abs(denominator) < 1e-6:
            alpha_a = self.DEFAULT_ALPHA_A
        else:
            alpha_a = (n * sum_xy - sum_x * sum_y) / denominator

        alpha_b = (sum_y - alpha_a * sum_x) / n

        # Apply safety bounds
        alpha_a = max(0.0, alpha_a)
        alpha_b = max(0.0, alpha_b) # Capping b >= 0 for simplicity/safety

        return alpha_a, alpha_b

    def _compute_average_rate(self, history):
        """Calculates the overall average rate (dT / t) for reference."""
        if not history:
            return 0.0

        total_delta_t = sum(rec.delta_t for rec in history)
        total_duration = sum(rec.duration_minutes for rec in history)

        if total_duration < 0.01:
            return 0.0

        return total_delta_t / total_duration

    def _prune_history(self):
        """Removes the oldest records to maintain the desired history size."""
        max_records = self._config["history_records_to_retain"]
        while len(self._heat_history) > max_records:
            self._heat_history.popleft()
        while len(self._cool_history) > max_records:
            self._cool_history.popleft()

    def _clear_history(self):
        """Clears all learned performance data."""
        self._heat_history.clear()
        self._cool_history.clear()
        self._update_model()
        self._set_formatted_status_log("[History] All performance records cleared.")

    def _update_history_log_text(self):
        """Updates the multi-line string showing performance history (t, dT format)."""
        lines = ["--- HEAT History (t, dT) ---"]
        if not self._heat_history:
            lines.append("No records.")
        else:
            for record in self._heat_history:
                 # Use repr(record) for clean, formatted output
                 lines.append(repr(record))

        lines.append("\n--- COOL History (t, dT) ---")
        if not self._cool_history:
            lines.append("No records.")
        else:
             for record in self._cool_history:
                 lines.append(repr(record))

        self._history_log_text = "\n".join(lines)


    # --- Utility Methods ---

    def _validate_inputs(self):
        """Checks if essential inputs are valid numbers or booleans."""
        if math.isnan(self.get_zone_temp()): return False
        if math.isnan(self.get_target_zone_temp_setpoint()): return False
        if self.get_schedule_next_value() is None: return False
        if self.get_schedule_next_event_time_ms() <= 0: return False
        return True

    def _force_shutdown(self, reason=""):
        """Forces the system into a safe OFF state."""
        self._is_optimal_start_running = False
        self._is_off_delay_active = False
        self._set_is_running(False)
        self._set_equipment_start_command(None)
        self._set_countdown_to_null_status(False)
        self._set_current_run_elapsed_minutes(0.0) # RENAMED
        self._set_formatted_status_log(f"[Forced OFF] {reason}")


    def _update_zone_at_temp_tolerance(self):
        """Updates the boolean flag, adjusting tolerance to match Java logic."""
        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        
        # Read the base tolerance from the config/slot
        base_tolerance = self._config["temp_tolerance"]
        
        # Add the fixed 0.1 value to it, matching the Java code
        effective_tolerance = base_tolerance + 0.1 

        if math.isnan(zone) or math.isnan(target):
            is_within = False
        else:
            is_within = abs(zone - target) <= effective_tolerance
        self._set_zone_at_temp_tolerance(is_within)

    def _set_formatted_status_log(self, message):
        """Sets the status log with a timestamp prefix."""
        last_trigger_str = "never"
        if self._last_start_trigger_timestamp_ms > 0:
            try:
                dt_object = datetime.datetime.fromtimestamp(self._last_start_trigger_timestamp_ms / 1000)
                last_trigger_str = dt_object.strftime('%H:%M:%S')
            except ValueError:
                last_trigger_str = "invalid_ts"
        self._set_status_log(f"[Last Start: {last_trigger_str}] {message}")

    def _log_debug_status(self):
        """Prints key internal states to the console."""
        current_time_ms = int(time.time() * 1000)
        time_to_next_minutes = (self.get_schedule_next_event_time_ms() - current_time_ms) / 60000.0
        
        print(f"--- [Debug {datetime.datetime.now().strftime('%H:%M:%S')}] ---")
        print(f"  State: Running={self._is_optimal_start_running}, OffDelay={self._is_off_delay_active}")
        print(f"  Temps: Zone={self.get_zone_temp():.1f}, Target={self.get_target_zone_temp_setpoint():.1f}, OAT={self.get_outdoor_temp():.1f}")
        # RENAMED GETTER
        print(f"  Schedule: NextOcc={self.get_schedule_next_value()}, T_remain={time_to_next_minutes:.1f}min")
        # RENAMED GETTER
        print(f"  Model Out: Command={self.get_equipment_start_command()}, EstTime={self.get_minutes_to_setpoint_predicted():.1f}min")
        print(f"  Perf: Pred={self.get_last_run_predicted_minutes():.1f}m, Act={self.get_last_run_actual_minutes():.1f}m, Err={self.get_last_run_error_minutes():.1f}m")
        print(f"  Heat Model: a={self._alpha_a_heat:.3f}, b={self._alpha_b_heat:.2f} | Cool Model: a={self._alpha_a_cool:.3f}, b={self._alpha_b_cool:.2f}")
        print(f"  Ref Rates: Heat={self.get_degrees_per_minute_heat():.3f}, Cool={self.get_degrees_per_minute_cool():.3f}")
        print(f"  Status: {self.get_status_log()}")
        print("-" * 20)

    # --- Getters for Outputs (Read-only access) ---
    def get_is_running(self): return self._is_running
    # RENAMED GETTER
    def get_minutes_to_setpoint_predicted(self): return self._minutes_to_setpoint_predicted
    def get_degrees_per_minute_heat(self): return self._degrees_per_minute_heat
    def get_degrees_per_minute_cool(self): return self._degrees_per_minute_cool
    def get_equipment_start_command(self): return self._equipment_start_command
    def get_zone_at_temp_tolerance(self): return self._zone_at_temp_tolerance
    def get_status_log(self): return self._status_log
    # RENAMED GETTER
    def get_current_run_elapsed_minutes(self): return self._current_run_elapsed_minutes
    def get_countdown_to_null_status(self): return self._countdown_to_null_status
    def get_current_history_record_count(self): return self._current_history_record_count
    def get_history_log_text(self): return self._history_log_text
    # NEW GETTERS
    def get_last_run_predicted_minutes(self): return self._last_run_predicted_minutes
    def get_last_run_actual_minutes(self): return self._last_run_actual_minutes
    def get_last_run_error_minutes(self): return self._last_run_error_minutes

    # --- Getters for Inputs (Sensor/Schedule readings) ---
    def get_zone_temp(self): return self._zone_temp
    def get_outdoor_temp(self): return self._outdoor_temp
    def get_target_zone_temp_setpoint(self): return self._target_zone_temp_setpoint
    def get_schedule_next_value(self): return self._schedule_next_value
    def get_schedule_next_event_time_ms(self): return self._schedule_next_event_time_ms
    def get_clear_history_now(self): return self._clear_history_now


    # --- Setters for Inputs (How external data is fed in - Unchanged) ---
    def set_zone_temp(self, value): self._zone_temp = float(value) if value is not None else float('nan')
    def set_outdoor_temp(self, value): self._outdoor_temp = float(value) if value is not None else float('nan')
    def set_target_zone_temp_setpoint(self, value): self._target_zone_temp_setpoint = float(value) if value is not None else float('nan')
    def set_schedule_next_value(self, value): self._schedule_next_value = bool(value) if value is not None else None
    def set_schedule_next_event_time_ms(self, value): self._schedule_next_event_time_ms = int(value) if value is not None else 0
    def set_clear_history_now(self, value): self._clear_history_now = bool(value)

    # --- Private Setters for Outputs (Internal state updates) ---
    def _set_is_running(self, value): self._is_running = value
    # RENAMED SETTER
    def _set_minutes_to_setpoint_predicted(self, value): self._minutes_to_setpoint_predicted = value
    def _set_degrees_per_minute_heat(self, value): self._degrees_per_minute_heat = value
    def _set_degrees_per_minute_cool(self, value): self._degrees_per_minute_cool = value
    def _set_equipment_start_command(self, value): self._equipment_start_command = value
    def _set_zone_at_temp_tolerance(self, value): self._zone_at_temp_tolerance = value
    def _set_status_log(self, value): self._status_log = value
    # RENAMED SETTER
    def _set_current_run_elapsed_minutes(self, value): self._current_run_elapsed_minutes = value
    def _set_countdown_to_null_status(self, value): self._countdown_to_null_status = value
    def _set_current_history_record_count(self, value): self._current_history_record_count = value
    # NEW SETTERS
    def _set_last_run_predicted_minutes(self, value): self._last_run_predicted_minutes = value
    def _set_last_run_actual_minutes(self, value): self._last_run_actual_minutes = value
    def _set_last_run_error_minutes(self, value): self._last_run_error_minutes = value

# Example Usage (Could be within a VOLTTRON agent)
if __name__ == "__main__":
    # 1. Initialize the model (optionally pass config overrides)
    model_config = {
        "print_to_console_log": True,
         "history_records_to_retain": 5
    }
    optimal_start = OptimalStartModel1(config=model_config)

    # --- Manually add history for a quick non-default model ---
    # Simulate a few previous HEAT runs: t = a*dT^2 + b
    optimal_start._heat_history.append(PerformanceRecord(time.time() * 1000, 10.0, 5.0, "HEAT", 65.0, 40.0))
    optimal_start._heat_history.append(PerformanceRecord(time.time() * 1000 + 1, 20.0, 8.0, "HEAT", 65.0, 40.0))
    optimal_start._update_model()
    print("\nModel pre-trained with sample data.")

    # 2. Set up scenario for a new cooling run
    current_timestamp_ms = int(time.time() * 1000)

    # Scenario: Unoccupied (78.5F), approaching occupied time (72.0F - needs cooling)
    optimal_start.set_zone_temp(78.5)
    optimal_start.set_target_zone_temp_setpoint(72.0)
    optimal_start.set_outdoor_temp(88.0)
    optimal_start.set_schedule_next_value(True) # Next is occupied
    # Set next event time to 90 minutes from now (should be a start)
    start_offset_minutes = 90
    optimal_start.set_schedule_next_event_time_ms(current_timestamp_ms + start_offset_minutes * 60 * 1000)
    
    # *** WORKAROUND: Snapshot the starting elapsed time for the rate simulation ***
    # The problem is that elapsed time resets to 0 when starting a run.
    # We need a proxy for the previous step's elapsed minutes to calculate deltaT.
    # This value is only needed for this simulation block, not the core model.
    optimal_start._last_elapsed_minutes = 0.0

    # Call execute periodically
    sim_steps = 10
    print(f"\nModel initialized. Simulating {sim_steps} steps (1 min each).")
    for i in range(sim_steps):
         print(f"\n--- Minute {i+1} ---")

         # Simulate time passing (This is a simplified 1-second delay for a 1-minute step simulation)
         time.sleep(1) 
         
         # The next call to execute will update its internal timestamp
         optimal_start.execute()

         # Check if run started and simulate temp change
         if optimal_start.get_is_running():
              rate = optimal_start.get_degrees_per_minute_cool()
              
              # Calculate how much time passed since last step (should be 1 min)
              current_elapsed = optimal_start.get_current_run_elapsed_minutes()
              time_delta = current_elapsed - optimal_start._last_elapsed_minutes
              
              # Simulate temp change based on the **cooling rate**
              # Use the cooling rate from the model to simulate the temperature drop
              new_temp = optimal_start.get_zone_temp() - rate * time_delta
              optimal_start.set_zone_temp(new_temp)
              
              # Update the snapshot for the next loop
              optimal_start._last_elapsed_minutes = current_elapsed
              
         else:
              # Simulate temp drift if not running
              optimal_start.set_zone_temp(optimal_start.get_zone_temp() + 0.1)

         # Force a stop after a few steps if it hasn't stopped already for a quick record
         if i == sim_steps - 2:
              optimal_start.set_schedule_next_value(False)

    print("\nSimulation complete.")
    print(f"Final Status: {optimal_start.get_status_log()}")
    print(f"Final Command: {optimal_start.get_equipment_start_command()}")
    print(f"Final Error: {optimal_start.get_last_run_error_minutes():.1f} min")

    # Example: How to get the detailed history log
    print("\n--- History Log ---")
    print(optimal_start.get_history_log_text())