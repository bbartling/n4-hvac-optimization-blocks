
import time
import datetime
import math
import numpy as np
from sklearn.linear_model import LinearRegression
from collections import deque

# --- 1. Data Structure ---
class PerformanceRecord:
    """
    Stores raw performance data for Model 3 regression.
    The primary purpose is to capture (duration, deltaT, OAT).
    """
    def __init__(self, duration_minutes, delta_t, mode, zone_temp_start, outdoor_temp_start):
        self.duration_minutes = duration_minutes # y-value (t)
        self.delta_t = delta_t                 # Basis for features
        self.mode = mode                       # 'HEAT' or 'COOL'
        self.zone_temp_start = zone_temp_start
        self.outdoor_temp_start = outdoor_temp_start 

    def __repr__(self):
        dt_object = datetime.datetime.fromtimestamp(int(time.time()))
        oat_str = f"{self.outdoor_temp_start:.1f}" if not math.isnan(self.outdoor_temp_start) else "N/A"
        return (f"t: {self.duration_minutes:.1f}, dT: {self.delta_t:.1f}, "
                f"ZS: {self.zone_temp_start:.1f}, OAT: {oat_str} "
                f"(Date: {dt_object.strftime('%y-%m-%d %H:%M')})")

class OptimalStartModel3:
    """
    Implements PNNL Model 3: t = a*dT + b*dT*WF + d.
    Tuning uses scikit-learn's Linear Regression to handle the multiple features
    and fit the intercept (d).
    """

    # --- Default constants (Used if not enough history) ---
    DEFAULT_ALPHA_A = 2.0  # Default coeff for deltaT
    DEFAULT_ALPHA_B = 0.5  # Default coeff for weather term
    DEFAULT_ALPHA_D = 5.0  # Default offset (intercept)
    DEFAULT_RATE_DEG_PER_MIN = 0.1 # Default for reference output
    ALPHA_C_DIVISOR = 60.0 # PNNL Model 3's normalizing factor (alpha_3,c)

    def __init__(self, config=None):
        """Initializes the model with default and learned parameters."""
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
        self._last_elapsed_minutes = 0.0 # Added for simulation helper

        # --- "Under the Hood" Learned Parameters (a, b, d) ---
        self._alpha_a_heat = self.DEFAULT_ALPHA_A
        self._alpha_b_heat = self.DEFAULT_ALPHA_B
        self._alpha_d_heat = self.DEFAULT_ALPHA_D
        self._alpha_a_cool = self.DEFAULT_ALPHA_A
        self._alpha_b_cool = self.DEFAULT_ALPHA_B
        self._alpha_d_cool = self.DEFAULT_ALPHA_D

        # --- Configurable Parameters (Initialize FIRST) ---
        self._config = {
            "max_minutes_allowed": 180.0,
            "temp_tolerance": 0.5,
            "history_records_to_retain": 10,
            "command_off_delay_seconds": 60.0,
            "print_to_console_log": False
        }
        if config:
            self._config.update(config)

        # --- Data Histories (FIXED: Use config value for maxlen) ---
        history_size = self._config["history_records_to_retain"]
        self._heat_history = deque(maxlen=history_size)
        self._cool_history = deque(maxlen=history_size)
        
        # --- Inputs (Simulated Slots) ---
        self._zone_temp = float('nan')
        self._outdoor_temp = float('nan')
        self._target_zone_temp_setpoint = float('nan')
        self._schedule_next_value = None
        self._schedule_next_event_time_ms = 0
        self._clear_history_now = False

        # --- Outputs (Simulated Slots - MATCHING JAVA VERSION) ---
        self._is_running = False
        self._minutes_to_setpoint_predicted = self._config["max_minutes_allowed"] 
        self._degrees_per_minute_heat = self.DEFAULT_RATE_DEG_PER_MIN
        self._degrees_per_minute_cool = self.DEFAULT_RATE_DEG_PER_MIN
        self._equipment_start_command = None
        self._zone_at_temp_tolerance = False
        self._status_log = "[Init] Optimal Start Model 3 initialized."
        self._current_run_elapsed_minutes = 0.0 
        self._countdown_to_null_status = False
        self._current_history_record_count = 0
        self._history_log_text = ""
        self._last_run_predicted_minutes = 0.0
        self._last_run_actual_minutes = 0.0
        self._last_run_error_minutes = 0.0

        # --- Initialization ---
        self._update_model()


    def execute(self):
        """Runs a single execution cycle."""
        current_time_ms = int(time.time() * 1000)

        if not self._validate_inputs():
            self._force_shutdown("Input validation failed")
            return

        self._update_zone_at_temp_tolerance()

        if self.get_clear_history_now():
            self._clear_history()
            self.set_clear_history_now(False)

        # --- Main State Machine ---
        if self._is_optimal_start_running:
            self._monitor_active_run(current_time_ms)
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)
        else:
            self._update_idle_estimate()
            self._update_equipment_start_command(current_time_ms)

        if self._config["print_to_console_log"]:
            self._log_debug_status()

    # --- Core Logic Methods (Identical to Model 1, except for Model-specific logic) ---

    def _update_equipment_start_command(self, current_time_ms):
        """Handles starting a new run or managing the off-delay countdown."""
        if self._is_off_delay_active:
            elapsed_seconds = (current_time_ms - self._off_delay_start_time_ms) / 1000.0
            delay_duration = self._config["command_off_delay_seconds"]

            if elapsed_seconds >= delay_duration:
                self._is_off_delay_active = False
                self._set_equipment_start_command(None)
                self._set_countdown_to_null_status(False)
                self._set_formatted_status_log("Off-delay expired. Command released to NULL.")
            else:
                self._set_countdown_to_null_status(True)
                remaining_sec = int(delay_duration - elapsed_seconds)
                self._set_formatted_status_log(f"Command off-delay active. {remaining_sec}s remaining.")
            return

        is_next_period_occupied = self.get_schedule_next_value()
        start_condition_met = False

        if is_next_period_occupied:
            next_event_time_ms = self.get_schedule_next_event_time_ms()
            time_to_next_minutes = max(0, (next_event_time_ms - current_time_ms) / 60000.0)
            optimal_start_minutes = self.get_minutes_to_setpoint_predicted()

            if optimal_start_minutes >= time_to_next_minutes and time_to_next_minutes > 0.1:
                 start_condition_met = True

        if start_condition_met:
            self._start_optimal_start_sequence(current_time_ms)
            self._set_equipment_start_command(True)
            self._set_countdown_to_null_status(False)
        else:
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
            self._set_minutes_to_setpoint_predicted(0.0)
            return

        prediction = self.get_minutes_to_setpoint_predicted()
        self._set_last_run_predicted_minutes(prediction)
        self._set_last_run_actual_minutes(0.0)
        self._set_last_run_error_minutes(0.0)

        self._zone_temp_at_start = self.get_zone_temp()
        self._outdoor_temp_at_start = self.get_outdoor_temp()
        self._last_elapsed_minutes = 0.0 # Reset helper for simulation

        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._start_timestamp_ms = current_time_ms
        self._is_optimal_start_running = True
        self._last_start_trigger_timestamp_ms = current_time_ms
        self._set_is_running(True)
        self._set_current_run_elapsed_minutes(0.0)

        start_temp_str = f"{self._zone_temp_at_start:.1f}F" if not math.isnan(self._zone_temp_at_start) else "N/A"
        self._set_formatted_status_log(f"[Start] Optimal Start initiated. Predicted: {prediction:.1f} min. Start Temp: {start_temp_str}")


    def _monitor_active_run(self, current_time_ms):
        """Monitors progress during an active optimal start run."""
        elapsed_minutes = (current_time_ms - self._start_timestamp_ms) / 60000.0
        self._set_current_run_elapsed_minutes(elapsed_minutes)

        if self.get_zone_at_temp_tolerance() and not self._setpoint_was_met_during_run:
            self._setpoint_was_met_during_run = True
            self._minutes_to_reach_setpoint = elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Target met in {elapsed_minutes:.1f} min. Stored value.")

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

        self._set_current_run_elapsed_minutes(actual_minutes)
        self._set_last_run_actual_minutes(actual_minutes)

        last_prediction = self.get_last_run_predicted_minutes()
        error = last_prediction - actual_minutes
        self._set_last_run_error_minutes(error)

        zone_start = self._zone_temp_at_start
        zone_target = self.get_target_zone_temp_setpoint()
        outdoor_start = self._outdoor_temp_at_start

        if math.isnan(zone_start) or math.isnan(zone_target):
             self._set_formatted_status_log("[Record] Invalid start/target temp. Performance not recorded.")
             return

        delta_t_achieved = abs(zone_target - zone_start)

        if actual_minutes > 0.1 and delta_t_achieved > 0.1:
            mode = "HEAT" if zone_start < zone_target else "COOL"

            new_record = PerformanceRecord(
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

    # --- Model-Specific Logic: Tuning (Regression) ---
    def _update_model(self):
        """Updates Model 3 parameters (a, b, d) using Linear Regression."""
        self._prune_history()

        heat_params = self._compute_regression_for_mode("HEAT")
        cool_params = self._compute_regression_for_mode("COOL")

        self._alpha_a_heat, self._alpha_b_heat, self._alpha_d_heat = heat_params
        self._alpha_a_cool, self._alpha_b_cool, self._alpha_d_cool = cool_params

        # Calculate and Update Reference Average Rate (Output) for display
        avg_heat_rate = self._compute_average_rate(self._heat_history)
        avg_cool_rate = self._compute_average_rate(self._cool_history)

        self._set_degrees_per_minute_heat(avg_heat_rate if avg_heat_rate > 0 else self.DEFAULT_RATE_DEG_PER_MIN)
        self._set_degrees_per_minute_cool(avg_cool_rate if avg_cool_rate > 0 else self.DEFAULT_RATE_DEG_PER_MIN)

        self._set_current_history_record_count(len(self._heat_history) + len(self._cool_history))
        self._update_history_log_text()

        if self._config["print_to_console_log"]:
            print("--- [Model 3 Update] ---")
            print(f"HEAT Model: t = {self._alpha_a_heat:.3f}*dT + {self._alpha_b_heat:.3f}*dT*WF + {self._alpha_d_heat:.2f}")
            print(f"COOL Model: t = {self._alpha_a_cool:.3f}*dT + {self._alpha_b_cool:.3f}*dT*WF + {self._alpha_d_cool:.2f}")
            print(f"Writing to SLOT degreesPerMinuteHeat (Avg): {avg_heat_rate:.3f}")
            print(f"Writing to SLOT degreesPerMinuteCool (Avg): {avg_cool_rate:.3f}")
            print("-------------------------")

    
    def _compute_regression_for_mode(self, mode):
        """Performs Linear Regression: y ≈ a*x1 + b*x2 + d"""
        history = self._heat_history if mode == "HEAT" else self._cool_history
        
        # Need at least 3 points to fit a 2-feature model with intercept
        valid_records = [r for r in history if not math.isnan(r.outdoor_temp_start)]
        if len(valid_records) < 3:
            return self.DEFAULT_ALPHA_A, self.DEFAULT_ALPHA_B, self.DEFAULT_ALPHA_D

        y = np.array([rec.duration_minutes for rec in valid_records])
        
        # Build X matrix: [ [dT], [dT * WeatherFactor] ]
        X_list = []
        for rec in valid_records:
            # WeatherFactor = (Tsp - OAT) / alpha_c (Tsp is unknown, so use a proxy)
            # PNNL Eq. (17) uses Tsp - To. We will use the recorded ZoneStart temp
            # as a proxy for Tsp for simplicity in historical analysis (since Tsp is 
            # assumed constant for the day of the run). We must use the OAT *during that run*.
            
            # Use the target setpoint for the current run as a proxy for the historical Tsp
            Tsp_proxy = self.get_target_zone_temp_setpoint() # Assume setpoint is relatively constant in practice
            
            # Use a sensible proxy if target is NaN during initial runs
            if math.isnan(Tsp_proxy):
                 Tsp_proxy = 72.0 if rec.mode == "COOL" else 70.0 # Default fallback
            
            weather_term_numerator = Tsp_proxy - rec.outdoor_temp_start
            
            # Feature x1 = delta_t
            feature_x1 = rec.delta_t
            
            # Feature x2 = delta_t * (Tsp - OAT) / ALPHA_C_DIVISOR
            feature_x2 = rec.delta_t * (weather_term_numerator / self.ALPHA_C_DIVISOR)
            
            # NOTE: We use the absolute value of dT * WF, consistent with typical PNNL Model 3 implementations 
            # to prevent model instability, as the sign is handled by the model context (Heat/Cool).
            X_list.append([feature_x1, abs(feature_x2)])
        X = np.array(X_list)

        # Scikit-learn Linear Regression: y ≈ a*x1 + b*x2 + d
        try:
            model = LinearRegression(fit_intercept=True) 
            model.fit(X, y)
            
            # Extract Learned Parameters
            alpha_a = max(0.0, model.coef_[0])     
            alpha_b = max(0.0, model.coef_[1]) 
            alpha_d = max(0.0, model.intercept_) 
            
            return alpha_a, alpha_b, alpha_d
        except Exception as e:
            if self._config["print_to_console_log"]:
                print(f"[ERROR] Regression failed for {mode}: {e}")
            return self.DEFAULT_ALPHA_A, self.DEFAULT_ALPHA_B, self.DEFAULT_ALPHA_D


    def _compute_average_rate(self, history):
        """Calculates the overall average rate (dT / t) for reference."""
        if not history: return 0.0
        total_delta_t = sum(rec.delta_t for rec in history)
        total_duration = sum(rec.duration_minutes for rec in history)
        if total_duration < 0.01: return 0.0
        return total_delta_t / total_duration


    # --- Model-Specific Logic: Prediction ---
    def _update_idle_estimate(self):
        """Calculates the estimated minutes to setpoint using Model 3."""
        if self.get_zone_at_temp_tolerance():
            self._set_minutes_to_setpoint_predicted(0.0) 
            return

        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        oat = self.get_outdoor_temp()
        
        if math.isnan(zone) or math.isnan(target) or math.isnan(oat):
             self._set_minutes_to_setpoint_predicted(self._config["max_minutes_allowed"])
             return

        delta_t_today = abs(target - zone)
        max_minutes = self._config["max_minutes_allowed"]
        estimated_minutes = max_minutes

        # Weather Factor (WF): (Tsp - OAT) / alpha_c (alpha_c = 60.0 in our case)
        weather_term_numerator = target - oat
        weather_factor_term = weather_term_numerator / self.ALPHA_C_DIVISOR
        
        # Model 3: t = a*dT + b*dT*WF + d
        if zone < target: # Heating needed
            a = self._alpha_a_heat
            b = self._alpha_b_heat
            d = self._alpha_d_heat
            
            # Use absolute value of the weather term in prediction, 
            # as the sign should be consistent with the mode (Heat/Cool).
            # The calculation is T_opt = a*dT + b*abs(dT*WF) + d 
            # where dT is already positive (abs(target - zone)).
            estimated_minutes = (a * delta_t_today) + (b * delta_t_today * abs(weather_factor_term)) + d
            
        elif zone > target: # Cooling needed
            a = self._alpha_a_cool
            b = self._alpha_b_cool
            d = self._alpha_d_cool
            
            estimated_minutes = (a * delta_t_today) + (b * delta_t_today * abs(weather_factor_term)) + d
        else:
             estimated_minutes = 0.0

        estimated_minutes = max(0.0, estimated_minutes)
        self._set_minutes_to_setpoint_predicted(min(estimated_minutes, max_minutes))


    # --- Utility and Boilerplate Methods (Copied from Model 1) ---
    def _prune_history(self):
        max_records = self._config["history_records_to_retain"]
        # Deques created with maxlen automatically handle pruning on append,
        # but we include this for completeness if maxlen is changed.
        while len(self._heat_history) > max_records: self._heat_history.popleft()
        while len(self._cool_history) > max_records: self._cool_history.popleft()

    def _clear_history(self):
        self._heat_history.clear()
        self._cool_history.clear()
        self._update_model()
        self._set_formatted_status_log("[History] All performance records cleared.")

    def _update_history_log_text(self):
        lines = ["--- HEAT History (t, dT, OAT) ---"]
        if not self._heat_history: lines.append("No records.")
        else:
            for record in self._heat_history: lines.append(repr(record))
        lines.append("\n--- COOL History (t, dT, OAT) ---")
        if not self._cool_history: lines.append("No records.")
        else:
             for record in self._cool_history: lines.append(repr(record))
        self._history_log_text = "\n".join(lines)

    def _validate_inputs(self):
        # Requires OAT to be valid, unlike Model 1
        if math.isnan(self.get_zone_temp()): return False
        if math.isnan(self.get_target_zone_temp_setpoint()): return False
        if self.get_schedule_next_value() is None: return False
        if self.get_schedule_next_event_time_ms() <= 0: return False
        if math.isnan(self.get_outdoor_temp()): return False # New Requirement
        return True

    def _force_shutdown(self, reason=""):
        self._is_optimal_start_running = False
        self._is_off_delay_active = False
        self._set_is_running(False)
        self._set_equipment_start_command(None)
        self._set_countdown_to_null_status(False)
        self._set_current_run_elapsed_minutes(0.0)
        self._set_formatted_status_log(f"[Forced OFF] {reason}")

    def _update_zone_at_temp_tolerance(self):
        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        base_tolerance = self._config["temp_tolerance"]
        effective_tolerance = base_tolerance + 0.1 
        if math.isnan(zone) or math.isnan(target):
            is_within = False
        else:
            is_within = abs(zone - target) <= effective_tolerance
        self._set_zone_at_temp_tolerance(is_within)

    def _set_formatted_status_log(self, message):
        last_trigger_str = "never"
        if self._last_start_trigger_timestamp_ms > 0:
            try:
                dt_object = datetime.datetime.fromtimestamp(self._last_start_trigger_timestamp_ms / 1000)
                last_trigger_str = dt_object.strftime('%H:%M:%S')
            except ValueError:
                last_trigger_str = "invalid_ts"
        self._set_status_log(f"[Last Start: {last_trigger_str}] {message}")

    def _log_debug_status(self):
        current_time_ms = int(time.time() * 1000)
        time_to_next_minutes = (self.get_schedule_next_event_time_ms() - current_time_ms) / 60000.0
        
        print(f"--- [Debug {datetime.datetime.now().strftime('%H:%M:%S')}] ---")
        print(f"  State: Running={self._is_optimal_start_running}, OffDelay={self._is_off_delay_active}")
        print(f"  Temps: Zone={self.get_zone_temp():.1f}, Target={self.get_target_zone_temp_setpoint():.1f}, OAT={self.get_outdoor_temp():.1f}")
        print(f"  Schedule: NextOcc={self.get_schedule_next_value()}, T_remain={time_to_next_minutes:.1f}min")
        print(f"  Model Out: Command={self.get_equipment_start_command()}, EstTime={self.get_minutes_to_setpoint_predicted():.1f}min")
        print(f"  Perf: Pred={self.get_last_run_predicted_minutes():.1f}m, Act={self.get_last_run_actual_minutes():.1f}m, Err={self.get_last_run_error_minutes():.1f}m")
        print(f"  Heat Model: t = {self._alpha_a_heat:.3f}*dT + {self._alpha_b_heat:.3f}*dT*WF + {self._alpha_d_heat:.2f}")
        print(f"  Cool Model: t = {self._alpha_a_cool:.3f}*dT + {self._alpha_b_cool:.3f}*dT*WF + {self._alpha_d_cool:.2f}")
        print(f"  Ref Rates: Heat={self.get_degrees_per_minute_heat():.3f}, Cool={self.get_degrees_per_minute_cool():.3f}")
        print(f"  Status: {self.get_status_log()}")
        print("-" * 20)

    # --- Getters for Outputs (Read-only access) ---
    def get_is_running(self): return self._is_running
    def get_minutes_to_setpoint_predicted(self): return self._minutes_to_setpoint_predicted
    def get_degrees_per_minute_heat(self): return self._degrees_per_minute_heat
    def get_degrees_per_minute_cool(self): return self._degrees_per_minute_cool
    def get_equipment_start_command(self): return self._equipment_start_command
    def get_zone_at_temp_tolerance(self): return self._zone_at_temp_tolerance
    def get_status_log(self): return self._status_log
    def get_current_run_elapsed_minutes(self): return self._current_run_elapsed_minutes
    def get_countdown_to_null_status(self): return self._countdown_to_null_status
    def get_current_history_record_count(self): return self._current_history_record_count
    def get_history_log_text(self): return self._history_log_text
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

    # --- Setters for Inputs (How external data is fed in) ---
    def set_zone_temp(self, value): self._zone_temp = float(value) if value is not None else float('nan')
    def set_outdoor_temp(self, value): self._outdoor_temp = float(value) if value is not None else float('nan')
    def set_target_zone_temp_setpoint(self, value): self._target_zone_temp_setpoint = float(value) if value is not None else float('nan')
    def set_schedule_next_value(self, value): self._schedule_next_value = bool(value) if value is not None else None
    def set_schedule_next_event_time_ms(self, value): self._schedule_next_event_time_ms = int(value) if value is not None else 0
    def set_clear_history_now(self, value): self._clear_history_now = bool(value)

    # --- Private Setters for Outputs (Internal state updates) ---
    def _set_is_running(self, value): self._is_running = value
    def _set_minutes_to_setpoint_predicted(self, value): self._minutes_to_setpoint_predicted = value
    def _set_degrees_per_minute_heat(self, value): self._degrees_per_minute_heat = value
    def _set_degrees_per_minute_cool(self, value): self._degrees_per_minute_cool = value
    def _set_equipment_start_command(self, value): self._equipment_start_command = value
    def _set_zone_at_temp_tolerance(self, value): self._zone_at_temp_tolerance = value
    def _set_status_log(self, value): self._status_log = value
    def _set_current_run_elapsed_minutes(self, value): self._current_run_elapsed_minutes = value
    def _set_countdown_to_null_status(self, value): self._countdown_to_null_status = value
    def _set_current_history_record_count(self, value): self._current_history_record_count = value
    def _set_last_run_predicted_minutes(self, value): self._last_run_predicted_minutes = value
    def _set_last_run_actual_minutes(self, value): self._last_run_actual_minutes = value
    def _set_last_run_error_minutes(self, value): self._last_run_error_minutes = value

# Example Usage (Demonstrates the learning process)
if __name__ == "__main__":
    
    # Requires scikit-learn (sklearn) and numpy to be installed
    print(f"--- Running Model 3 Simulation ({datetime.datetime.now().strftime('%H:%M:%S')}) ---")
    
    # 1. Initialize Model and pre-load sample COOLING history (OAT is critical here)
    model_config = {"print_to_console_log": True, "history_records_to_retain": 5}
    optimal_start = OptimalStartModel3(config=model_config)

    # Clear default history and add new COOLING examples for Model 3 regression
    optimal_start._cool_history.clear()
    
    # Example cooling runs. Notice how different OATs affect the time (t)
    # Target SP is assumed to be 72.0 F
    # Cooler OAT (80F) -> faster recovery
    optimal_start._cool_history.append(PerformanceRecord(duration_minutes=17.0, delta_t=6.0, mode="COOL", zone_temp_start=78.0, outdoor_temp_start=88.2))
    optimal_start._cool_history.append(PerformanceRecord(duration_minutes=16.0, delta_t=5.5, mode="COOL", zone_temp_start=77.5, outdoor_temp_start=87.6))
    optimal_start._cool_history.append(PerformanceRecord(duration_minutes=18.5, delta_t=6.5, mode="COOL", zone_temp_start=78.5, outdoor_temp_start=91.1))
    optimal_start._cool_history.append(PerformanceRecord(duration_minutes=20.0, delta_t=7.0, mode="COOL", zone_temp_start=79.0, outdoor_temp_start=95.0))
    optimal_start._cool_history.append(PerformanceRecord(duration_minutes=17.5, delta_t=6.2, mode="COOL", zone_temp_start=78.2, outdoor_temp_start=90.3))
    
    # Must explicitly set Target SP for the regression calculation (Tsp - OAT)
    optimal_start.set_target_zone_temp_setpoint(72.0)
    
    optimal_start._update_model()
    print("\nModel 3 pre-trained with sample data.")

    # 2. Set up scenario for today's prediction
    current_timestamp_ms = int(time.time() * 1000)

    optimal_start.set_zone_temp(78.5)
    optimal_start.set_outdoor_temp(92.0) # Today is hot! (Will lead to longer prediction time)
    optimal_start.set_schedule_next_value(True) 
    start_offset_minutes = 90
    optimal_start.set_schedule_next_event_time_ms(current_timestamp_ms + start_offset_minutes * 60 * 1000)
    
    optimal_start._last_elapsed_minutes = 0.0 # Reset helper for simulation

    # 3. Execute first step (should trigger Optimal Start sequence)
    print("\n--- Execute Step 1: Trigger Optimal Start ---")
    optimal_start.execute()
    
    estimated_time = optimal_start.get_minutes_to_setpoint_predicted()
    print(f"\nModel 3 Prediction for today (OAT=92.0F): {estimated_time:.1f} minutes")
    print(f"Prediction Error Snapshot: {optimal_start.get_last_run_predicted_minutes():.1f} min")
    
    # 4. Simulate the run for 5 minutes
    sim_steps = 5
    print(f"\n--- Simulating Active Run ({sim_steps} minutes) ---")
    for i in range(1, sim_steps + 1):
         current_timestamp_ms += 60000 # Advance time by 1 minute
         
         # Simulate temperature drop based on the calculated rate
         rate = optimal_start.get_degrees_per_minute_cool()
         new_temp = optimal_start.get_zone_temp() - rate * 1.0
         optimal_start.set_zone_temp(new_temp)
         
         # Execute logic
         optimal_start.execute()
         print(f"Minute {i}: Temp={optimal_start.get_zone_temp():.1f}, Command={optimal_start.get_equipment_start_command()}")

    # 5. Force stop and record performance
    print("\n--- Execute Stop: Schedule set to unoccupied ---")
    optimal_start.set_schedule_next_value(False)
    optimal_start.execute()

    print("\nSimulation complete. New Run Recorded:")
    print(f"Final Actual Time: {optimal_start.get_last_run_actual_minutes():.1f} min")
    print(f"Final Error (Pred - Act): {optimal_start.get_last_run_error_minutes():.1f} min")
    print("\n--- Updated History Log ---")
    print(optimal_start.get_history_log_text())