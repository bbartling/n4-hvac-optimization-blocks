import time
import datetime

class PerformanceRecord:
    """A classic class to hold the performance data for a single HVAC run."""
    def __init__(self, timestamp, rate, mode, zone_temp_start, outdoor_temp_start):
        self.timestamp = timestamp
        self.rate = rate
        self.mode = mode
        self.zone_temp_start = zone_temp_start
        self.outdoor_temp_start = outdoor_temp_start

    def __repr__(self):
        """Provides a clean string representation for printing the object."""
        dt_object = datetime.datetime.fromtimestamp(self.timestamp / 1000)
        return (f"PerformanceRecord(date={dt_object.strftime('%Y-%m-%d %H:%M')}, "
                f"rate={self.rate:.2f}, mode='{self.mode}')")

class OptimalStartModel:
    """
    A Python class that simulates the complete Niagara Optimal Start Program Object,
    updated to match the final Java logic.
    """
    def __init__(self):
        # --- Internal State Variables (like Java member variables) ---
        self._is_optimal_start_running = False
        self._start_timestamp = 0
        self._last_start_trigger_timestamp = 0
        self.DEFAULT_RATE_DEG_PER_MIN = 0.1

        # --- NEW state variables to match final Java version ---
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._is_off_delay_active = False
        self._off_delay_start_time = 0

        # --- Data Histories ---
        self._heat_history = []
        self._cool_history = []

        # --- Attributes mimicking Niagara Slots ---
        self._zone_temp = 80.0
        self._target_zone_temp_setpoint = 72.0
        self._schedule_next_value = False
        self._schedule_next_event_time = 0 
        self._clear_history_now = False
        
        # --- Configurable Parameters ---
        self._max_minutes_allowed = 180.0
        self._temp_tolerance = 1.0
        self._history_days_to_retain = 10
        self._ema_weighting_factor = 2.0
        self._command_off_delay_seconds = 30.0 # Default value
        self._print_to_console_log = True

        # --- Outputs ---
        self._is_running = False
        self._minutes_to_setpoint = 0.0
        self._degrees_per_minute_heat = self.DEFAULT_RATE_DEG_PER_MIN
        self._degrees_per_minute_cool = self.DEFAULT_RATE_DEG_PER_MIN
        self._equipment_start_command = None # Using None to represent NULL
        self._zone_at_temp_tolerance = False
        self._status_log = ""
        self._warmup_time_minutes = 0.0
        self._countdown_to_null_status = False # UPDATED to be a boolean

    # --- "onStart" Equivalent ---
    def start(self):
        """Initializes the model with default values, mimicking onStart()."""
        print("[System] Block starting...")
        self.set_minutes_to_setpoint(self.get_max_minutes_allowed())
        self._update_model()
        self._set_formatted_status_log("[onStart] Optimal Start block initialized.")
        print(f"[Status] {self.get_status_log()}")
        print("-" * 50)

    # --- "onExecute" Equivalent ---
    def execute(self):
        """Runs a single execution cycle of the program logic, mimicking onExecute()."""
        self._update_zone_at_temp_tolerance()

        if self.get_clear_history_now():
            self._clear_history()
            self.set_clear_history_now(False)

        if self._is_optimal_start_running:
            self._monitor_active_run()
        else:
            self._update_idle_estimate()

        self._update_equipment_start_command()
        
        if self.get_print_to_console_log():
            print("--- [Debug] ---")
            print(f"isOptimalStartRunning: {self._is_optimal_start_running}")
            print(f"isOffDelayActive: {self._is_off_delay_active}")
            print(f"setpointWasMetDuringRun: {self._setpoint_was_met_during_run}")
            print(f"minutesToSetpoint (estimate): {self.get_minutes_to_setpoint():.1f}")
            print(f"equipmentStartCommand: {self.get_equipment_start_command()}")
            print(f"countdownToNullStatus: {self.get_countdown_to_null_status()}")
            print("-----------------")


    # --- ###################################################### ---
    # --- ### UPDATED METHODS TO MATCH FINAL JAVA LOGIC ### ---
    # --- ###################################################### ---

    def _update_equipment_start_command(self):
        # --- Off-Delay Timer Management ---
        if self._is_off_delay_active:
            elapsed_seconds = (time.time() * 1000 - self._off_delay_start_time) / 1000
            delay_duration = self.get_command_off_delay_seconds() or 60

            if elapsed_seconds >= delay_duration:
                self._is_off_delay_active = False
                self.set_equipment_start_command(None)
                self.set_countdown_to_null_status(False)
                self._set_formatted_status_log("Off-delay expired. Command released to NULL.")
            else:
                self.set_countdown_to_null_status(True)
                self._set_formatted_status_log(f"Command off-delay active. {int(delay_duration - elapsed_seconds)}s remaining.")
            return

        # --- Standard Start/Stop Logic ---
        # (Assuming schedule points are valid for simulation)
        is_next_period_occupied = self.get_schedule_next_value()
        start_condition_met = False

        if is_next_period_occupied and not self._is_optimal_start_running:
            current_time = time.time() * 1000
            next_event_time = self.get_schedule_next_event_time()
            time_to_next_minutes = max(0, (next_event_time - current_time) / 60000.0)
            optimal_start_minutes = self.get_minutes_to_setpoint()
            if optimal_start_minutes >= time_to_next_minutes:
                start_condition_met = True

        # --- Final Command Output Logic ---
        if start_condition_met:
            self._start_optimal_start_sequence()
            self.set_equipment_start_command(True)
            self.set_countdown_to_null_status(False)
        elif self._is_optimal_start_running:
            self.set_equipment_start_command(True)
            self.set_countdown_to_null_status(False)
        else:
            if self.get_equipment_start_command():
                self._is_off_delay_active = True
                self._off_delay_start_time = time.time() * 1000
                self.set_countdown_to_null_status(True)
                self._set_formatted_status_log("Entering command off-delay countdown...")
            else:
                self.set_countdown_to_null_status(False)
                
    def _start_optimal_start_sequence(self):
        if self.get_zone_at_temp_tolerance():
            self._set_formatted_status_log("[Start] Skipping: Zone temp is already within tolerance.")
            self.set_minutes_to_setpoint(0.0)
            return

        # NEW: Reset state for the new run
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0

        self._start_timestamp = int(time.time() * 1000)
        self._is_optimal_start_running = True
        self._last_start_trigger_timestamp = self._start_timestamp
        self.set_is_running(True)
        self._set_formatted_status_log("[Start] Optimal Start sequence initiated.")

    def _monitor_active_run(self):
        now = int(time.time() * 1000)
        elapsed_minutes = (now - self._start_timestamp) / 60000.0

        # 1. Check if the setpoint has been met for the first time.
        if self.get_zone_at_temp_tolerance() and not self._setpoint_was_met_during_run:
            self._setpoint_was_met_during_run = True
            self._minutes_to_reach_setpoint = elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Target met in {elapsed_minutes:.1f} min. Stored value.")

        # 2. Handle a loss of sensor data (simulated as always OK)

        # 3. The schedule changing state is the primary trigger to end the run.
        is_next_period_occupied = self.get_schedule_next_value()
        if not is_next_period_occupied:
            final_performance_minutes = self._minutes_to_reach_setpoint if self._setpoint_was_met_during_run else elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Schedule occupied. Recording performance using {final_performance_minutes:.1f} min.")
            self._stop_and_record_performance(final_performance_minutes)
        
        self.set_warmup_time_minutes(elapsed_minutes)

    # --- ###################################################### ---
    # --- ### END OF UPDATED METHODS ### ---
    # --- ###################################################### ---

    def _update_zone_at_temp_tolerance(self):
        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        tolerance = self.get_temp_tolerance()
        is_within_tolerance = abs(zone - target) <= tolerance
        self.set_zone_at_temp_tolerance(is_within_tolerance)

    def _stop_and_record_performance(self, actual_minutes):
        self._is_optimal_start_running = False
        self.set_is_running(False)
        
        # In a real scenario, you'd get the current temp. Here we simulate the change.
        zone_start = 80.0 
        zone_now = self.get_target_zone_temp_setpoint()
        delta = abs(zone_now - zone_start)

        if actual_minutes > 0.1:
            rate = delta / actual_minutes
            mode = "COOL" if zone_start > zone_now else "HEAT"
            
            if self.get_print_to_console_log():
                print(f"[Performance Record] Duration: {actual_minutes:.1f} min, Rate: {rate:.2f} deg/min, Mode: {mode}")

            new_record = PerformanceRecord(int(time.time() * 1000), rate, mode, zone_start, 50.0) # Assuming 50F OAT
            if mode == "HEAT": self._heat_history.append(new_record)
            else: self._cool_history.append(new_record)

            self._set_formatted_status_log(f"[{mode}] run recorded. Rate: {rate:.2f} deg/min.")
            self._update_model()
        else:
            self._set_formatted_status_log("[Record] Run was too short. Performance not recorded.")
    
    def _update_model(self):
        self._prune_history()
        heat_rate_ema = self._compute_ema_for_mode("HEAT")
        cool_rate_ema = self._compute_ema_for_mode("COOL")

        self.set_degrees_per_minute_heat(heat_rate_ema if heat_rate_ema > 0 else self.DEFAULT_RATE_DEG_PER_MIN)
        self.set_degrees_per_minute_cool(cool_rate_ema if cool_rate_ema > 0 else self.DEFAULT_RATE_DEG_PER_MIN)
        
        if self.get_print_to_console_log():
            print("--- [Model Update] ---")
            heat_rates = [f"{rec.rate:.2f}" for rec in self._heat_history]
            cool_rates = [f"{rec.rate:.2f}" for rec in self._cool_history]
            print(f"HEAT Rates: {heat_rates if heat_rates else '[No history]'}")
            print(f"New HEAT EMA: {self.get_degrees_per_minute_heat():.2f}")
            print(f"COOL Rates: {cool_rates if cool_rates else '[No history]'}")
            print(f"New COOL EMA: {self.get_degrees_per_minute_cool():.2f}")
            print("----------------------")

    def _update_idle_estimate(self):
        if self.get_zone_at_temp_tolerance():
            self.set_minutes_to_setpoint(0.0)
            return

        zone = self.get_zone_temp()
        target = self.get_target_zone_temp_setpoint()
        delta = abs(target - zone)
        
        rate = self.get_degrees_per_minute_cool() if zone > target else self.get_degrees_per_minute_heat()
        estimated_minutes = delta / rate if rate > 0.01 else self.get_max_minutes_allowed()
        self.set_minutes_to_setpoint(min(estimated_minutes, self.get_max_minutes_allowed()))

    def _prune_history(self):
        max_records = self.get_history_days_to_retain()
        while len(self._heat_history) > max_records: self._heat_history.pop(0)
        while len(self._cool_history) > max_records: self._cool_history.pop(0)

    def _clear_history(self):
        self._heat_history.clear()
        self._cool_history.clear()
        self._update_model()
        self._set_formatted_status_log("[History] All performance records have been cleared.")

    def _compute_ema_for_mode(self, mode):
        history = self._heat_history if mode == "HEAT" else self._cool_history
        if not history: return 0.0
        series = [rec.rate for rec in history]
        return self._compute_ema(series)

    def _compute_ema(self, series):
        if not series: return 0.0
        k = self.get_ema_weighting_factor() / (len(series) + 1.0)
        ema = series[0]
        for i in range(1, len(series)):
            ema = series[i] * k + ema * (1 - k)
        return ema

    def _set_formatted_status_log(self, message):
        last_trigger_str = "never"
        if self._last_start_trigger_timestamp > 0:
            last_trigger_str = datetime.datetime.fromtimestamp(self._last_start_trigger_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        self.set_status_log(f"[Last Trigger: {last_trigger_str}] {message}")

    # --- Classic Getters and Setters for all attributes ---
    def get_zone_temp(self): return self._zone_temp
    def set_zone_temp(self, value): self._zone_temp = value
    def get_target_zone_temp_setpoint(self): return self._target_zone_temp_setpoint
    def set_target_zone_temp_setpoint(self, value): self._target_zone_temp_setpoint = value
    def get_schedule_next_value(self): return self._schedule_next_value
    def set_schedule_next_value(self, value): self._schedule_next_value = value
    def get_schedule_next_event_time(self): return self._schedule_next_event_time
    def set_schedule_next_event_time(self, value): self._schedule_next_event_time = value
    def get_clear_history_now(self): return self._clear_history_now
    def set_clear_history_now(self, value): self._clear_history_now = value
    def get_max_minutes_allowed(self): return self._max_minutes_allowed
    def set_max_minutes_allowed(self, value): self._max_minutes_allowed = value
    def get_temp_tolerance(self): return self._temp_tolerance
    def set_temp_tolerance(self, value): self._temp_tolerance = value
    def get_history_days_to_retain(self): return self._history_days_to_retain
    def set_history_days_to_retain(self, value): self._history_days_to_retain = value
    def get_ema_weighting_factor(self): return self._ema_weighting_factor
    def set_ema_weighting_factor(self, value): self._ema_weighting_factor = value
    def get_command_off_delay_seconds(self): return self._command_off_delay_seconds
    def set_command_off_delay_seconds(self, value): self._command_off_delay_seconds = value
    def get_print_to_console_log(self): return self._print_to_console_log
    def set_print_to_console_log(self, value): self._print_to_console_log = value
    def get_is_running(self): return self._is_running
    def set_is_running(self, value): self._is_running = value
    def get_minutes_to_setpoint(self): return self._minutes_to_setpoint
    def set_minutes_to_setpoint(self, value): self._minutes_to_setpoint = value
    def get_degrees_per_minute_heat(self): return self._degrees_per_minute_heat
    def set_degrees_per_minute_heat(self, value): self._degrees_per_minute_heat = value
    def get_degrees_per_minute_cool(self): return self._degrees_per_minute_cool
    def set_degrees_per_minute_cool(self, value): self._degrees_per_minute_cool = value
    def get_equipment_start_command(self): return self._equipment_start_command
    def set_equipment_start_command(self, value): self._equipment_start_command = value
    def get_zone_at_temp_tolerance(self): return self._zone_at_temp_tolerance
    def set_zone_at_temp_tolerance(self, value): self._zone_at_temp_tolerance = value
    def get_status_log(self): return self._status_log
    def set_status_log(self, value): self._status_log = value
    def get_countdown_to_null_status(self): return self._countdown_to_null_status
    def set_countdown_to_null_status(self, value): self._countdown_to_null_status = value
    def get_warmup_time_minutes(self): return self._warmup_time_minutes
    def set_warmup_time_minutes(self, value): self._warmup_time_minutes = value

# --- Main Execution Block (Simulation) ---
if __name__ == "__main__":
    model = OptimalStartModel()
    
    # --- Scenario Setup ---
    # Next schedule event is in 12 minutes (720 seconds) and is OCCUPIED
    model.set_schedule_next_event_time((time.time() + 720) * 1000)
    model.set_schedule_next_value(True)
    model.set_command_off_delay_seconds(5) # Use a short delay for simulation
    
    # Start the block
    model.start()
    
    print("--- Starting Simulation ---")
    print(f"Target Temp: {model.get_target_zone_temp_setpoint()} F | Tolerance: {model.get_temp_tolerance()} F")
    print(f"Initial Zone Temp: {model.get_zone_temp()} F")
    print(f"Estimated time to setpoint: {model.get_minutes_to_setpoint():.1f} min")
    print("-" * 50)
    
    # Run the simulation for 15 minutes (15 cycles)
    for i in range(15): 
        print(f"\n--- Cycle {i+1} (Minute {i}) ---")
        
        # At minute 10, simulate the schedule becoming occupied
        if i == 10:
            print("!!! SIMULATING SCHEDULE CHANGE TO OCCUPIED !!!")
            model.set_schedule_next_value(False)

        # If the optimal start is running, simulate the temperature dropping
        if model.get_is_running():
            current_temp = model.get_zone_temp()
            model.set_zone_temp(current_temp - 1.0) # Drop temp by 1 degree per cycle
            print(f"  [Sim] Cooling is running. New Zone Temp: {model.get_zone_temp():.1f} F")

        # Run the block's logic
        model.execute()
        
        # Print key outputs
        print(f"  [Output] Status Log: {model.get_status_log()}")
        
        time.sleep(0.2) # Pause for readability

    print("\n--- Occupancy period over, simulating off-delay ---")
    # After the run is stopped, an off-delay should start. Simulate a few more cycles to see it count down.
    for i in range(7):
        print(f"\n--- Off-Delay Cycle {i+1} ---")
        model.execute()
        print(f"  [Output] Status Log: {model.get_status_log()}")
        time.sleep(1)

    print("\n--- Simulation Complete ---")