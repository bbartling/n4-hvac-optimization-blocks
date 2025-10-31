import time
import datetime
import math
from collections import deque

class PerformanceRecord:
    """Stores raw performance data from a single HVAC run."""
    def __init__(self, timestamp_ms, duration_minutes, delta_t, mode,
                 zone_temp_start, outdoor_temp_start):
        self.timestamp_ms = timestamp_ms
        self.duration_minutes = duration_minutes # y-value for regression
        self.delta_t = delta_t                 # Used for x-value (delta_t^2)
        self.mode = mode                       # 'HEAT' or 'COOL'
        self.zone_temp_start = zone_temp_start
        self.outdoor_temp_start = outdoor_temp_start # Store NaN if not available

    def __repr__(self):
        """Provides a clean string representation."""
        dt_object = datetime.datetime.fromtimestamp(self.timestamp_ms / 1000)
        oat_str = f"{self.outdoor_temp_start:.1f}" if not math.isnan(self.outdoor_temp_start) else "N/A"
        return (f"Run(date={dt_object.strftime('%y-%m-%d %H:%M')}, "
                f"mode='{self.mode}', t={self.duration_minutes:.1f}min, "
                f"dT={self.delta_t:.1f}F, ZS={self.zone_temp_start:.1f}F, "
                f"OAT={oat_str}F)")

class OptimalStartModel1:
    """
    Python implementation of the self-tuning Optimal Start logic using
    the quadratic Model 1 (t = a*dT^2 + b), storing parameters internally.

    Designed for integration into platforms like VOLTTRON. Mimics the
    structure of the Niagara Program Object.
    """

    # --- Default constants ---
    DEFAULT_ALPHA_A = 0.1  # Default slope for t = a*dT^2 + b
    DEFAULT_ALPHA_B = 5.0  # Default intercept
    DEFAULT_RATE_DEG_PER_MIN = 0.1 # Default for reference output

    def __init__(self, config=None):
        """
        Initializes the model.
        Args:
            config (dict, optional): Configuration overrides for parameters
                                     like tolerance, max_minutes, history_days etc.
        """
        # --- Internal State ---
        self._is_optimal_start_running = False
        self._start_timestamp_ms = 0
        self._last_start_trigger_timestamp_ms = 0
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._is_off_delay_active = False
        self._off_delay_start_time_ms = 0
        self._zone_temp_at_start = float('nan')
        self._outdoor_temp_at_start = float('nan')

        # --- "Under the Hood" Learned Parameters ---
        self._alpha_a_heat = self.DEFAULT_ALPHA_A
        self._alpha_b_heat = self.DEFAULT_ALPHA_B
        self._alpha_a_cool = self.DEFAULT_ALPHA_A
        self._alpha_b_cool = self.DEFAULT_ALPHA_B

        # --- Data Histories (using deque for efficient pop(0)) ---
        self._heat_history = deque()
        self._cool_history = deque()

        # --- Configurable Parameters (can be overridden by config dict) ---
        self._config = {
            "max_minutes_allowed": 180.0,
            "temp_tolerance": 0.5,
            "history_records_to_retain": 10, # Renamed from days for clarity
            "command_off_delay_seconds": 5.0,
            "print_to_console_log": False # Default to quiet operation
        }
        if config:
            self._config.update(config)

        # --- Inputs (Simulated Slots - update via setters) ---
        self._zone_temp = float('nan')
        self._outdoor_temp = float('nan')
        self._target_zone_temp_setpoint = float('nan')
        self._schedule_next_value = None # Boolean: True if next is occupied
        self._schedule_next_event_time_ms = 0 # Timestamp in milliseconds
        self._clear_history_now = False

        # --- Outputs (Simulated Slots - access via getters) ---
        self._is_running = False
        self._minutes_to_setpoint = self._config["max_minutes_allowed"]
        self._degrees_per_minute_heat = self.DEFAULT_RATE_DEG_PER_MIN # Reference only
        self._degrees_per_minute_cool = self.DEFAULT_RATE_DEG_PER_MIN # Reference only
        self._equipment_start_command = None # True, False, or None (for NULL/Off)
        self._zone_at_temp_tolerance = False
        self._status_log = "[Init] Optimal Start Model 1 initialized."
        self._warmup_time_minutes = 0.0
        self._countdown_to_null_status = False
        self._current_history_record_count = 0
        self._history_log_text = "" # For detailed history view

        # --- Initialization ---
        self._update_model() # Run once on start to set initial values

    def execute(self):
        """
        Runs a single execution cycle. Call this periodically (e.g., every minute).
        Updates internal state and output values based on current inputs.
        """
        current_time_ms = int(time.time() * 1000)

        # --- Input Validation ---
        if not self._validate_inputs():
            # If crucial inputs are missing, force OFF and log error
            self._force_shutdown("Input validation failed")
            return

        self._update_zone_at_temp_tolerance()

        if self.get_clear_history_now():
            self._clear_history()
            self.set_clear_history_now(False) # Auto-reset trigger

        # --- Main State Machine ---
        if self._is_optimal_start_running:
            # STATE 1: ACTIVE RUN
            self._monitor_active_run(current_time_ms)
            # Safeguard: Ensure command stays ON during active run
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)

        else:
            # STATE 2: NOT RUNNING (Idle, Estimating, or in Off-Delay)
            self._update_idle_estimate()
            self._update_equipment_start_command(current_time_ms)

        # --- Optional Logging ---
        if self._config["print_to_console_log"]:
            self._log_debug_status()

    # --- Core Logic Methods ---

    def _update_equipment_start_command(self, current_time_ms):
        """Handles starting a new run or managing the off-delay countdown."""
        # 1. Manage Off-Delay Timer
        if self._is_off_delay_active:
            elapsed_seconds = (current_time_ms - self._off_delay_start_time_ms) / 1000.0
            delay_duration = self._config["command_off_delay_seconds"]

            if elapsed_seconds >= delay_duration:
                # Timer expired
                self._is_off_delay_active = False
                self._set_equipment_start_command(None) # Set to None (NULL)
                self._set_countdown_to_null_status(False)
                self._set_formatted_status_log("Off-delay expired. Command released to NULL.")
            else:
                # Timer still running
                self._set_countdown_to_null_status(True)
                remaining_sec = int(delay_duration - elapsed_seconds)
                self._set_formatted_status_log(f"Command off-delay active. {remaining_sec}s remaining.")
            return # Skip start logic while timer active

        # 2. Determine if a start is needed
        is_next_period_occupied = self.get_schedule_next_value()
        start_condition_met = False

        if is_next_period_occupied:
            next_event_time_ms = self.get_schedule_next_event_time_ms()
            time_to_next_minutes = max(0, (next_event_time_ms - current_time_ms) / 60000.0)
            optimal_start_minutes = self.get_minutes_to_setpoint()

            # Start if the calculated time is >= time remaining AND there's time remaining
            # (prevents starting if next event is immediate)
            if optimal_start_minutes >= time_to_next_minutes and time_to_next_minutes > 0.1:
                 start_condition_met = True

        # 3. Set Final Command Output
        if start_condition_met:
            self._start_optimal_start_sequence(current_time_ms)
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)
        else:
            # If currently running but shouldn't be, start the off-delay
            if self.get_equipment_start_command() is True:
                self._is_off_delay_active = True
                self._off_delay_start_time_ms = current_time_ms
                self._set_countdown_to_null_status(True)
                self._set_formatted_status_log("Entering command off-delay countdown...")
                # Command remains True until delay expires
            elif self.get_equipment_start_command() is None and not self._is_off_delay_active:
                # If already NULL and not in delay, ensure state is clean
                 self._set_countdown_to_null_status(False)


    def _start_optimal_start_sequence(self, current_time_ms):
        """Initiates a new heating or cooling run."""
        if self.get_zone_at_temp_tolerance():
            self._set_formatted_status_log("[Start] Skipping: Zone temp already within tolerance.")
            self._set_minutes_to_setpoint(0.0)
            return

        # Record initial conditions
        self._zone_temp_at_start = self.get_zone_temp()
        self._outdoor_temp_at_start = self.get_outdoor_temp() # Will be NaN if not set

        # Reset run state variables
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._start_timestamp_ms = current_time_ms
        self._is_optimal_start_running = True
        self._last_start_trigger_timestamp_ms = current_time_ms
        self._set_is_running(True)
        self._set_warmup_time_minutes(0.0)

        start_temp_str = f"{self._zone_temp_at_start:.1f}F" if not math.isnan(self._zone_temp_at_start) else "N/A"
        self._set_formatted_status_log(f"[Start] Optimal Start initiated. Start Temp: {start_temp_str}")

    def _monitor_active_run(self, current_time_ms):
        """Monitors progress during an active optimal start run."""
        elapsed_minutes = (current_time_ms - self._start_timestamp_ms) / 60000.0
        self._set_warmup_time_minutes(elapsed_minutes)

        # 1. Check if setpoint was met for the first time
        if self.get_zone_at_temp_tolerance() and not self._setpoint_was_met_during_run:
            self._setpoint_was_met_during_run = True
            self._minutes_to_reach_setpoint = elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Target met in {elapsed_minutes:.1f} min. Stored value.")

        # 2. Check for stop conditions (schedule change or input loss)
        schedule_still_occupied = self.get_schedule_next_value()
        inputs_valid = self._validate_inputs() # Re-check inputs during run

        if not schedule_still_occupied or not inputs_valid:
            stop_reason = "Schedule now unocc" if not schedule_still_occupied else "Inputs invalid"
            # Use the time it took to reach setpoint if met, otherwise use total elapsed time
            final_performance_minutes = self._minutes_to_reach_setpoint if self._setpoint_was_met_during_run else elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] {stop_reason}. Recording performance using {final_performance_minutes:.1f} min.")
            self._stop_and_record_performance(final_performance_minutes)

    def _stop_and_record_performance(self, actual_minutes):
        """Ends the current run and records performance data."""
        self._is_optimal_start_running = False
        self._set_is_running(False)
        self._set_warmup_time_minutes(0.0) # Reset stopwatch

        # Use the *target* setpoint as the end temp for calculation consistency
        zone_start = self._zone_temp_at_start
        zone_target = self.get_target_zone_temp_setpoint()
        outdoor_start = self._outdoor_temp_at_start

        # Ensure we captured valid start data
        if math.isnan(zone_start) or math.isnan(zone_target):
             self._set_formatted_status_log("[Record] Invalid start/target temp. Performance not recorded.")
             return

        delta_t_achieved = abs(zone_target - zone_start)

        # Only record if the run was meaningful
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

            self._set_formatted_status_log(f"[{mode}] run recorded (t={actual_minutes:.1f}, dT={delta_t_achieved:.1f})")
            self._update_model() # Retune the model with the new data
        else:
           self._set_formatted_status_log("[Record] Run too short or no temp change. Performance not recorded.")

        # Reset start temps for next run
        self._zone_temp_at_start = float('nan')
        self._outdoor_temp_at_start = float('nan')


    def _update_model(self):
        """
        Updates the internal quadratic model parameters (a, b) using linear
        regression and updates the reference average rate outputs.
        """
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
            print(f"Reference Heat Rate (Avg): {avg_heat_rate:.3f} deg/min")
            print(f"Reference Cool Rate (Avg): {avg_cool_rate:.3f} deg/min")
            print("-------------------------")


    def _update_idle_estimate(self):
        """
        Calculates the estimated minutes to setpoint using the quadratic model
        when the system is not actively running.
        """
        if self.get_zone_at_temp_tolerance():
            self._set_minutes_to_setpoint(0.0)
            return

        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()

        # Ensure temps are valid before calculating
        if math.isnan(zone) or math.isnan(target):
             self._set_minutes_to_setpoint(self._config["max_minutes_allowed"])
             return

        delta_t = abs(target - zone)
        max_minutes = self._config["max_minutes_allowed"]
        estimated_minutes = max_minutes

        # Apply the quadratic formula: t = a * (deltaT^2) + b
        if zone < target: # Heating needed
            a = self._alpha_a_heat
            b = self._alpha_b_heat
            estimated_minutes = (a * (delta_t ** 2)) + b
        elif zone > target: # Cooling needed
            a = self._alpha_a_cool
            b = self._alpha_b_cool
            estimated_minutes = (a * (delta_t ** 2)) + b
        else: # Already at setpoint (should be caught by tolerance check, but safety)
             estimated_minutes = 0.0

        # Ensure estimate is non-negative and capped
        estimated_minutes = max(0.0, estimated_minutes)
        self._set_minutes_to_setpoint(min(estimated_minutes, max_minutes))

    # --- Regression and History Helpers ---

    def _compute_regression_for_mode(self, mode):
        """
        Performs Simple Linear Regression: y = mx + c
        where y = duration (t), x = delta_t^2. Returns [m, c] => [alpha_a, alpha_b].
        Uses basic formulas, no external libraries needed.
        """
        history = self._heat_history if mode == "HEAT" else self._cool_history

        if len(history) < 2: # Need at least 2 points for regression
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

        # Calculate slope (m = alpha_a)
        denominator = (n * sum_x_sq - sum_x ** 2)
        if abs(denominator) < 1e-6: # Avoid division by zero if all dT^2 are same
            alpha_a = self.DEFAULT_ALPHA_A
        else:
            alpha_a = (n * sum_xy - sum_x * sum_y) / denominator

        # Calculate intercept (c = alpha_b)
        alpha_b = (sum_y - alpha_a * sum_x) / n

        # Apply safety bounds (a must be non-negative, b can be slightly negative but cap)
        alpha_a = max(0.0, alpha_a)
        alpha_b = max(0.0, alpha_b) # Capping b >= 0 for simplicity

        return alpha_a, alpha_b

    def _compute_average_rate(self, history):
        """Calculates the overall average rate (dT / t) for reference."""
        if not history:
            return 0.0

        total_delta_t = sum(rec.delta_t for rec in history)
        total_duration = sum(rec.duration_minutes for rec in history)

        if total_duration < 0.01: # Avoid division by zero
            return 0.0

        return total_delta_t / total_duration

    def _prune_history(self):
        """Removes the oldest records to maintain the desired history size."""
        max_records = self._config["history_records_to_retain"]
        while len(self._heat_history) > max_records:
            self._heat_history.popleft() # Efficient removal from left
        while len(self._cool_history) > max_records:
            self._cool_history.popleft()

    def _clear_history(self):
        """Clears all learned performance data."""
        self._heat_history.clear()
        self._cool_history.clear()
        self._update_model() # Reset model parameters to defaults
        self._set_formatted_status_log("[History] All performance records cleared.")

    def _update_history_log_text(self):
        """Updates the multi-line string showing performance history."""
        lines = ["--- HEAT History ---"]
        if not self._heat_history:
            lines.append("No records.")
        else:
            for record in self._heat_history:
                 lines.append(repr(record)) # Use the PerformanceRecord's __repr__

        lines.append("\n--- COOL History ---")
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
        if self.get_schedule_next_value() is None: return False # Must be True or False
        if self.get_schedule_next_event_time_ms() <= 0: return False
        return True

    def _force_shutdown(self, reason=""):
        """Forces the system into a safe OFF state."""
        self._is_optimal_start_running = False
        self._is_off_delay_active = False
        self._set_is_running(False)
        self._set_equipment_start_command(None)
        self._set_countdown_to_null_status(False)
        self._set_warmup_time_minutes(0.0)
        self._set_formatted_status_log(f"[Forced OFF] {reason}")


    def _update_zone_at_temp_tolerance(self):
        """Updates the boolean flag indicating if zone temp is within tolerance."""
        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        tolerance = self._config["temp_tolerance"]
        if math.isnan(zone) or math.isnan(target):
            is_within = False
        else:
            is_within = abs(zone - target) <= tolerance
        self._set_zone_at_temp_tolerance(is_within)

    def _set_formatted_status_log(self, message):
        """Sets the status log with a timestamp prefix."""
        last_trigger_str = "never"
        if self._last_start_trigger_timestamp_ms > 0:
            try:
                dt_object = datetime.datetime.fromtimestamp(self._last_start_trigger_timestamp_ms / 1000)
                last_trigger_str = dt_object.strftime('%H:%M:%S')
            except ValueError: # Handle potential timestamp issues
                last_trigger_str = "invalid_ts"
        self._set_status_log(f"[Last Start: {last_trigger_str}] {message}")

    def _log_debug_status(self):
        """Prints key internal states to the console if logging is enabled."""
        print(f"--- [Debug {datetime.datetime.now().strftime('%H:%M:%S')}] ---")
        print(f"  State: Running={self._is_optimal_start_running}, OffDelay={self._is_off_delay_active}")
        print(f"  Temps: Zone={self.get_zone_temp():.1f}, Target={self.get_target_zone_temp_setpoint():.1f}, OAT={self.get_outdoor_temp():.1f}")
        print(f"  Schedule: NextOcc={self.get_schedule_next_value()}, T_remain={(self.get_schedule_next_event_time_ms() - time.time()*1000)/60000.0:.1f}min")
        print(f"  Model Out: Command={self.get_equipment_start_command()}, EstTime={self.get_minutes_to_setpoint():.1f}min")
        print(f"  Heat Model: a={self._alpha_a_heat:.3f}, b={self._alpha_b_heat:.2f} | Cool Model: a={self._alpha_a_cool:.3f}, b={self._alpha_b_cool:.2f}")
        print(f"  Ref Rates: Heat={self.get_degrees_per_minute_heat():.3f}, Cool={self.get_degrees_per_minute_cool():.3f}")
        print(f"  Status: {self.get_status_log()}")
        print("-" * 20)

    # --- Getters for Outputs (Read-only access) ---
    def get_is_running(self): return self._is_running
    def get_minutes_to_setpoint(self): return self._minutes_to_setpoint
    def get_degrees_per_minute_heat(self): return self._degrees_per_minute_heat # Reference
    def get_degrees_per_minute_cool(self): return self._degrees_per_minute_cool # Reference
    def get_equipment_start_command(self): return self._equipment_start_command
    def get_zone_at_temp_tolerance(self): return self._zone_at_temp_tolerance
    def get_status_log(self): return self._status_log
    def get_warmup_time_minutes(self): return self._warmup_time_minutes
    def get_countdown_to_null_status(self): return self._countdown_to_null_status
    def get_current_history_record_count(self): return self._current_history_record_count
    def get_history_log_text(self): return self._history_log_text # Get the detailed history

    # --- Setters for Inputs (How external data is fed in) ---
    def set_zone_temp(self, value): self._zone_temp = float(value) if value is not None else float('nan')
    def set_outdoor_temp(self, value): self._outdoor_temp = float(value) if value is not None else float('nan')
    def set_target_zone_temp_setpoint(self, value): self._target_zone_temp_setpoint = float(value) if value is not None else float('nan')
    def set_schedule_next_value(self, value): self._schedule_next_value = bool(value) if value is not None else None
    def set_schedule_next_event_time_ms(self, value): self._schedule_next_event_time_ms = int(value) if value is not None else 0
    def set_clear_history_now(self, value): self._clear_history_now = bool(value)

    # --- Private Setters for Outputs (Internal state updates) ---
    def _set_is_running(self, value): self._is_running = value
    def _set_minutes_to_setpoint(self, value): self._minutes_to_setpoint = value
    def _set_degrees_per_minute_heat(self, value): self._degrees_per_minute_heat = value
    def _set_degrees_per_minute_cool(self, value): self._degrees_per_minute_cool = value
    def _set_equipment_start_command(self, value): self._equipment_start_command = value
    def _set_zone_at_temp_tolerance(self, value): self._zone_at_temp_tolerance = value
    def _set_status_log(self, value): self._status_log = value
    def _set_warmup_time_minutes(self, value): self._warmup_time_minutes = value
    def _set_countdown_to_null_status(self, value): self._countdown_to_null_status = value
    def _set_current_history_record_count(self, value): self._current_history_record_count = value

# Example Usage (Could be within a VOLTTRON agent)
if __name__ == "__main__":
    # 1. Initialize the model (optionally pass config overrides)
    model_config = {
        "print_to_console_log": True,
         "history_records_to_retain": 5 # Keep shorter history for demo
    }
    optimal_start = OptimalStartModel1(config=model_config)

    print("Model initialized. Simulating...")

    # --- Simulate some data points (replace with actual agent logic) ---
    # Example: Feed data into the model before calling execute
    current_timestamp_ms = int(time.time() * 1000)

    # Scenario: Unoccupied, approaching occupied time
    optimal_start.set_zone_temp(78.5)
    optimal_start.set_target_zone_temp_setpoint(72.0)
    optimal_start.set_outdoor_temp(88.0)
    optimal_start.set_schedule_next_value(True) # Next is occupied
    # Set next event time to 90 minutes from now
    optimal_start.set_schedule_next_event_time_ms(current_timestamp_ms + 90 * 60 * 1000)

    # Call execute periodically
    for i in range(5): # Simulate 5 minutes passing
         print(f"\n--- Minute {i+1} ---")
         # In a real agent, update inputs here based on platform readings
         # optimal_start.set_zone_temp(read_from_platform(...))
         # ... etc ...

         # Update schedule time remaining
         time_remaining_ms = optimal_start.get_schedule_next_event_time_ms() - int(time.time() * 1000)
         if time_remaining_ms < 0: time_remaining_ms = 0 # Don't go negative

         if optimal_start.get_is_running():
              # Simulate temp change if running
              rate = optimal_start.get_degrees_per_minute_cool() # Assume cooling
              new_temp = optimal_start.get_zone_temp() - rate
              optimal_start.set_zone_temp(new_temp)
         else:
              # Simulate temp drift if not running
               optimal_start.set_zone_temp(optimal_start.get_zone_temp() + 0.1)


         optimal_start.execute()
         time.sleep(1) # Simulate time passing

    print("\nSimulation complete.")
    print(f"Final Status: {optimal_start.get_status_log()}")
    print(f"Final Command: {optimal_start.get_equipment_start_command()}")

    # Example: How to get the detailed history log
    # print("\n--- History Log ---")
    # print(optimal_start.get_history_log_text())
