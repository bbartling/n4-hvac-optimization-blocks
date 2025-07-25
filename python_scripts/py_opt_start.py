import time
import datetime
import os

# --- Helper function to clear the console for the dashboard ---
def clear_screen():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

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
        # --- Internal State Variables ---
        self._is_optimal_start_running = False
        self._start_timestamp = 0
        self._last_start_trigger_timestamp = 0
        self.DEFAULT_RATE_DEG_PER_MIN = 0.1
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._is_off_delay_active = False
        self._off_delay_start_time = 0
        self._zone_temp_at_start = 0.0 # To store temp when a run begins
        self._outdoor_temp_at_start = 0.0 # To store OAT when a run begins

        # --- Data Histories ---
        self._heat_history = []
        self._cool_history = []

        # --- Attributes mimicking Niagara Slots ---
        self._zone_temp = 78.0
        self._outdoor_temp = 85.0 # Added for dynamic simulation
        self._target_zone_temp_setpoint = 72.0
        self._schedule_next_value = False # Is the next period occupied?
        self._schedule_next_event_time = 0 
        self._clear_history_now = False
        
        # --- Configurable Parameters ---
        self._max_minutes_allowed = 180.0
        self._temp_tolerance = 0.5
        self._history_days_to_retain = 10
        self._ema_weighting_factor = 2.0
        self._command_off_delay_seconds = 5.0
        self._print_to_console_log = False # Set to False for clean dashboard

        # --- Outputs ---
        self._is_running = False
        self._minutes_to_setpoint = 0.0
        self._degrees_per_minute_heat = self.DEFAULT_RATE_DEG_PER_MIN
        self._degrees_per_minute_cool = self.DEFAULT_RATE_DEG_PER_MIN
        self._equipment_start_command = None
        self._zone_at_temp_tolerance = False
        self._status_log = ""
        self._warmup_time_minutes = 0.0
        self._countdown_to_null_status = False
        self._current_history_record_count = 0

    def start(self):
        """Initializes the model with default values."""
        self.set_minutes_to_setpoint(self.get_max_minutes_allowed())
        self._update_model()
        self._set_formatted_status_log("[onStart] Optimal Start block initialized.")

    def execute(self):
        """Runs a single execution cycle of the program logic."""
        self._update_zone_at_temp_tolerance()

        if self.get_clear_history_now():
            self._clear_history()
            self.set_clear_history_now(False)

        if self._is_optimal_start_running:
            self._monitor_active_run()
            self.set_equipment_start_command(True)
            self.set_countdown_to_null_status(False)
        else:
            self._update_idle_estimate()
            self._update_equipment_start_command()

    def _update_equipment_start_command(self):
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

        is_next_period_occupied = self.get_schedule_next_value()
        start_condition_met = False

        if is_next_period_occupied:
            current_time = time.time() * 1000
            next_event_time = self.get_schedule_next_event_time()
            time_to_next_minutes = max(0, (next_event_time - current_time) / 60000.0)
            optimal_start_minutes = self.get_minutes_to_setpoint()
            if optimal_start_minutes >= time_to_next_minutes and time_to_next_minutes > 0:
                start_condition_met = True

        if start_condition_met:
            self._start_optimal_start_sequence()
            self.set_equipment_start_command(True)
            self.set_countdown_to_null_status(False)
        else:
            if self.get_equipment_start_command():
                self._is_off_delay_active = True
                self._off_delay_start_time = time.time() * 1000
                self.set_countdown_to_null_status(True)
                self._set_formatted_status_log("Entering command off-delay countdown...")

    def _start_optimal_start_sequence(self):
        if self.get_zone_at_temp_tolerance():
            self._set_formatted_status_log("[Start] Skipping: Zone temp is already within tolerance.")
            self.set_minutes_to_setpoint(0.0)
            return

        self._zone_temp_at_start = self.get_zone_temp()
        self._outdoor_temp_at_start = self.get_outdoor_temp()
        self._setpoint_was_met_during_run = False
        self._minutes_to_reach_setpoint = 0.0
        self._start_timestamp = int(time.time() * 1000)
        self._is_optimal_start_running = True
        self._last_start_trigger_timestamp = self._start_timestamp
        self.set_is_running(True)
        self._set_formatted_status_log(f"[Start] Optimal Start initiated. Start Temp: {self._zone_temp_at_start}°F")

    def _monitor_active_run(self):
        now = int(time.time() * 1000)
        elapsed_minutes = (now - self._start_timestamp) / 60000.0
        self.set_warmup_time_minutes(elapsed_minutes)

        if self.get_zone_at_temp_tolerance() and not self._setpoint_was_met_during_run:
            self._setpoint_was_met_during_run = True
            self._minutes_to_reach_setpoint = elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Target met in {elapsed_minutes:.1f} min. Stored value.")

        if not self.get_schedule_next_value(): # If schedule becomes UNOCCUPIED
            final_performance_minutes = self._minutes_to_reach_setpoint if self._setpoint_was_met_during_run else elapsed_minutes
            self._set_formatted_status_log(f"[Monitor] Schedule now unocc. Recording performance using {final_performance_minutes:.1f} min.")
            self._stop_and_record_performance(final_performance_minutes)

    def _stop_and_record_performance(self, actual_minutes):
        self._is_optimal_start_running = False
        self.set_is_running(False)
        
        zone_start = self._zone_temp_at_start
        outdoor_start = self._outdoor_temp_at_start
        zone_now = self.get_target_zone_temp_setpoint()
        delta = abs(zone_now - zone_start)

        if actual_minutes > 0.1:
            rate = delta / actual_minutes
            mode = "COOL" if zone_start > zone_now else "HEAT"
            
            new_record = PerformanceRecord(int(time.time() * 1000), rate, mode, zone_start, outdoor_start)
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
        self.set_current_history_record_count(len(self._heat_history) + len(self._cool_history))
        
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
        self._heat_history.clear(); self._cool_history.clear()
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

    def _update_zone_at_temp_tolerance(self):
        is_within_tolerance = abs(self.get_zone_temp() - self.get_target_zone_temp_setpoint()) <= self.get_temp_tolerance()
        self.set_zone_at_temp_tolerance(is_within_tolerance)

    def _set_formatted_status_log(self, message):
        last_trigger_str = "never"
        if self._last_start_trigger_timestamp > 0:
            dt_object = datetime.datetime.fromtimestamp(self._last_start_trigger_timestamp / 1000)
            last_trigger_str = dt_object.strftime('%H:%M:%S')
        self.set_status_log(f"[Last Start: {last_trigger_str}] {message}")

    # --- Getters and Setters ---
    def get_zone_temp(self): return self._zone_temp
    def set_zone_temp(self, value): self._zone_temp = value
    def get_outdoor_temp(self): return self._outdoor_temp
    def set_outdoor_temp(self, value): self._outdoor_temp = value
    def get_target_zone_temp_setpoint(self): return self._target_zone_temp_setpoint
    def set_target_zone_temp_setpoint(self, value): self._target_zone_temp_setpoint = value
    def get_schedule_next_value(self): return self._schedule_next_value
    def set_schedule_next_value(self, value): self._schedule_next_value = value
    def get_schedule_next_event_time(self): return self._schedule_next_event_time
    def set_schedule_next_event_time(self, value): self._schedule_next_event_time = value
    def get_clear_history_now(self): return self._clear_history_now
    def set_clear_history_now(self, value): self._clear_history_now = value
    def get_max_minutes_allowed(self): return self._max_minutes_allowed
    def get_temp_tolerance(self): return self._temp_tolerance
    def get_history_days_to_retain(self): return self._history_days_to_retain
    def get_ema_weighting_factor(self): return self._ema_weighting_factor
    def get_command_off_delay_seconds(self): return self._command_off_delay_seconds
    def get_is_running(self): return self._is_running
    def set_is_running(self, value): self._is_running = value
    def get_minutes_to_setpoint(self): return self._minutes_to_setpoint
    def set_minutes_to_setpoint(self, value): self._minutes_to_setpoint = value
    def get_degrees_per_minute_heat(self): return self._degrees_per_minute_heat
    def set_degrees_per_minute_heat(self, value): self._degrees_per_minute_heat = value # ADD THIS LINE
    def get_degrees_per_minute_cool(self): return self._degrees_per_minute_cool
    def set_degrees_per_minute_cool(self, value): self._degrees_per_minute_cool = value # ADD THIS LINE
    def get_equipment_start_command(self): return self._equipment_start_command
    def set_equipment_start_command(self, value): self._equipment_start_command = value
    def get_zone_at_temp_tolerance(self): return self._zone_at_temp_tolerance
    def set_zone_at_temp_tolerance(self, value): self._zone_at_temp_tolerance = value
    def get_status_log(self): return self._status_log
    def set_status_log(self, value): self._status_log = value
    def get_warmup_time_minutes(self): return self._warmup_time_minutes
    def set_warmup_time_minutes(self, value): self._warmup_time_minutes = value
    def get_current_history_record_count(self): return self._current_history_record_count
    def set_current_history_record_count(self, value): self._current_history_record_count = value

# --- Simulation-Specific Functions ---

def update_simulation_state(model, sim_time_seconds):
    """
    Simulates the passing of time and its effect on the building and schedule.
    This function acts as the 'fake BAS' providing data to the model.
    """
    # Simulate a 240-minute day cycle (4 hours for speed)
    minutes_into_day = (sim_time_seconds / 60) % 240
    
    sim_status = ""

    # --- Simulate BAS Schedule ---
    if 0 <= minutes_into_day < 120: # First 2 hours: UNOCCUPIED
        sim_status = "UNOCCUPIED"
        model.set_schedule_next_value(True) # Next event is OCCUPIED
        # Set next event time to the 120-minute mark
        model.set_schedule_next_event_time((time.time() + (120 - minutes_into_day) * 60) * 1000)
        # Temp drifts away from setpoint
        if not model.get_is_running():
            model.set_zone_temp(model.get_zone_temp() + 0.02) # Drifts warmer
            
    elif 120 <= minutes_into_day < 240: # Last 2 hours: OCCUPIED
        sim_status = "OCCUPIED"
        model.set_schedule_next_value(False) # Next event is UNOCCUPIED
        # Temp drifts away from setpoint if AC is off
        if not model.get_is_running() and not model.get_zone_at_temp_tolerance():
             model.set_zone_temp(model.get_zone_temp() + 0.05)


    # --- Simulate HVAC Action ---
    if model.get_equipment_start_command():
        # Cooling is running, so temperature drops
        learned_rate = model.get_degrees_per_minute_cool()
        model.set_zone_temp(model.get_zone_temp() - (learned_rate / 60.0)) # per-second drop

    return sim_status


def print_dashboard(model, sim_status, start_time):
    """Prints the real-time status of the model, mimicking a Niagara view."""
    clear_screen()
    print("--- Optimal Start Live Simulation Dashboard ---")
    print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Sim Uptime: {int(time.time() - start_time)}s")
    print(f"Simulation Period: {sim_status}")
    print("-" * 45)

    # --- Inputs ---
    print("\n[INPUTS]")
    print(f"  Zone Temp:                 {model.get_zone_temp():.2f}°F")
    print(f"  Outdoor Temp:              {model.get_outdoor_temp():.2f}°F")
    print(f"  Target Setpoint:           {model.get_target_zone_temp_setpoint():.2f}°F")
    next_occ = "OCCUPIED" if model.get_schedule_next_value() else "UNOCCUPIED"
    print(f"  Schedule Next Value:       {next_occ}")
    
    # --- Outputs & State ---
    print("\n[OUTPUTS / STATE]")
    print(f"  Is Running:                {model.get_is_running()}")
    print(f"  Equipment Start Command:   {model.get_equipment_start_command()}")
    print(f"  Calculated Mins To Setpoint: {model.get_minutes_to_setpoint():.1f} min")
    print(f"  Live Warmup/Cooldown Time: {model.get_warmup_time_minutes():.1f} min")
    
    # --- Learning Model ---
    print("\n[LEARNING MODEL]")
    print(f"  Learned Cool Rate (EMA):   {model.get_degrees_per_minute_cool():.3f} °F/min")
    print(f"  History Record Count:      {model.get_current_history_record_count()}")

    # --- Status Log ---
    print("\n[STATUS LOG]")
    print(f"  {model.get_status_log()}")
    print("\n" + "="*45)
    
# --- Main Execution Block (Simulation) ---
if __name__ == "__main__":
    model = OptimalStartModel()
    model.start()
    
    start_time = time.time()
    
    print("Starting continuous simulation... Press CTRL+C to exit.")
    time.sleep(2)

    try:
        while True:
            # 1. Update the 'fake' environment and BAS schedule
            current_sim_time = time.time() - start_time
            sim_status = update_simulation_state(model, current_sim_time)

            # 2. Run the core logic of the Optimal Start model
            model.execute()

            # 3. Print the live dashboard with all the getter values
            print_dashboard(model, sim_status, start_time)
            
            # 4. Pause to make the simulation readable
            time.sleep(1) 

    except KeyboardInterrupt:
        print("\n--- Simulation Stopped ---")