import time

class PerformanceRecord:
    """A class to hold the results from a single grid flexibility event."""
    def __init__(self, day, kw_reduction, coasting_time_minutes, temp_drift_per_hour):
        self.day = day
        self.kw_reduction = kw_reduction # How much power was actually shed
        self.coasting_time_minutes = coasting_time_minutes # How long the shed lasted
        self.temp_drift_per_hour = temp_drift_per_hour # How fast the temp changed during the event

    def __repr__(self):
        return (f"Day {self.day:2}: (kW Reduced={self.kw_reduction:.1f}, "
                f"Coasting Time={self.coasting_time_minutes:.0f} min, "
                f"Temp Drift={self.temp_drift_per_hour:.2f}°F/hr)")

class GridFlexibilityOptimizer:
    """
    An adaptive model that learns a building's load-shed potential to optimize
    for grid flexibility and peak demand reduction.
    """

    def __init__(self):
        # --- Event & Building State (Inputs) ---
        self.high_price_event_active = True
        self.current_building_kw = 150.0  # Current power consumption
        self.max_allowable_temp_drift = 2.0 # How many degrees the temp is allowed to change

        # --- Historical Data Cache ---
        self.performance_history = []
        self.ema_weighting_factor = 2.0

        # --- Tuned Parameters (will be updated from history) ---
        self.learned_kw_flexibility = 0.0 # The predictable kW that can be shed
        self.learned_temp_drift_rate = 0.0 # The learned °F/hr drift during a shed event

    def generate_sample_data(self, num_days=10):
        """Populates the history with 10 simulated grid flexibility events."""
        print(f"--- Generating {num_days} days of sample grid performance data... ---")
        # Tuples of (kw_reduction, coasting_time, temp_drift)
        # (kW reduction, coasting time in minutes, temp drift in °F/hr)
        sample_events = [
            (25.0, 55, 1.8), # Day 1: Shed 25.0 kW, coasted for 55 mins, temp drifted 1.8°F/hr
            (28.0, 60, 2.0), # Day 2: Shed 28.0 kW, coasted for 60 mins, temp drifted 2.0°F/hr
            (26.5, 58, 1.9), # Day 3: Shed 26.5 kW, coasted for 58 mins, temp drifted 1.9°F/hr
            (30.0, 65, 2.2), # Day 4: Shed 30.0 kW, coasted for 65 mins, temp drifted 2.2°F/hr
            (32.5, 70, 2.1), # Day 5: Shed 32.5 kW, coasted for 70 mins, temp drifted 2.1°F/hr
            (31.0, 68, 2.0), # Day 6: Shed 31.0 kW, coasted for 68 mins, temp drifted 2.0°F/hr
            (35.0, 75, 2.4), # Day 7: Shed 35.0 kW, coasted for 75 mins, temp drifted 2.4°F/hr
            (36.0, 78, 2.5), # Day 8: Shed 36.0 kW, coasted for 78 mins, temp drifted 2.5°F/hr
            (38.5, 80, 2.6), # Day 9: Shed 38.5 kW, coasted for 80 mins, temp drifted 2.6°F/hr
            (40.0, 85, 2.8)  # Day 10: System learned to be more aggressive
        ]
        for i, params in enumerate(sample_events):
            record = PerformanceRecord(day=i+1, kw_reduction=params[0], coasting_time_minutes=params[1], temp_drift_per_hour=params[2])
            self.performance_history.append(record)
        
        print("Sample data generated successfully.\n")
        for record in self.performance_history:
            print(record)

    def _compute_ema(self, series: list) -> float:
        """Calculates the Exponential Moving Average for a list of numbers."""
        if not series: return 0.0
        k = self.ema_weighting_factor / (len(series) + 1)
        ema = series[0]
        for i in range(1, len(series)):
            ema = (series[i] * k) + (ema * (1 - k))
        return ema

    def tune_parameters_from_history(self):
        """Calculates the EMA for each parameter from the history."""
        print("\n--- Tuning Flexibility Parameters using EMA from 10-Day History ---")
        if not self.performance_history:
            print("No history available. Cannot tune parameters.")
            return

        kw_flex_series = [rec.kw_reduction for rec in self.performance_history]
        temp_drift_series = [rec.temp_drift_per_hour for rec in self.performance_history]

        self.learned_kw_flexibility = self._compute_ema(kw_flex_series)
        self.learned_temp_drift_rate = self._compute_ema(temp_drift_series)

        print(f"Tuned kW Flexibility: {self.learned_kw_flexibility:.2f} kW")
        print(f"Tuned Temp Drift Rate: {self.learned_temp_drift_rate:.2f} °F/hr")

    def calculate_load_shed_strategy(self):
        """
        Calculates an optimal load shed strategy using the tuned parameters.
        """
        print("\n--- Calculating Today's Load Shed Strategy ---")

        if not self.high_price_event_active:
            print("No high price event. No load shed required.")
            return

        # Strategy 1: How much power can we shed?
        # Based on learned history, we can confidently shed a certain amount.
        potential_kw_shed = self.learned_kw_flexibility
        new_target_kw = self.current_building_kw - potential_kw_shed

        # Strategy 2: How long can we maintain the shed?
        # Based on how fast the temperature changes, calculate the maximum coasting time.
        if self.learned_temp_drift_rate > 0:
            max_coasting_hours = self.max_allowable_temp_drift / self.learned_temp_drift_rate
            max_coasting_minutes = max_coasting_hours * 60
        else:
            max_coasting_minutes = float('inf')


        print("\n--- Recommended Grid Response Strategy ---")
        print(f"Action: Reduce building power demand by {potential_kw_shed:.1f} kW.")
        print(f"New Target: Set building power limit to {new_target_kw:.1f} kW.")
        print(f"Duration: Maintain this shed for up to {max_coasting_minutes:.0f} minutes before comfort is impacted.")
        
# --- Main Execution ---
if __name__ == "__main__":
    grid_model = GridFlexibilityOptimizer()
    
    # 1. Generate 10 days of historical grid response data
    grid_model.generate_sample_data()
    
    # 2. Tune the model's parameters using an EMA of that history
    grid_model.tune_parameters_from_history()
    
    # 3. For a new high-price event, calculate the optimal load shed strategy
    grid_model.calculate_load_shed_strategy()