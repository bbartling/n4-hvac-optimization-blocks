import time

class PerformanceRecord:
    """A class to hold the calculated parameters from a single day's run."""
    def __init__(self, day, alpha_3a, alpha_3b, alpha_3d):
        self.day = day
        self.alpha_3a = alpha_3a # The calculated rate for that day
        self.alpha_3b = alpha_3b # The calculated weather factor for that day
        self.alpha_3d = alpha_3d # The calculated offset for that day

    def __repr__(self):
        # return a clean string
        return (f"Day {self.day:2}: (α3a={self.alpha_3a:.2f}, "
                f"α3b={self.alpha_3b:.3f}, α3d={self.alpha_3d:.1f})")

class Model3_OptimalStart_With_History:
    """
    An expanded class for Model 3 that demonstrates how parameters are tuned
    over time using a history of performance data.
    """

    def __init__(self):
        # --- Current Day's Conditions (Inputs) ---
        self.zone_temp_initial = 78.0  # (T_z,0) Initial zone temperature in °F
        self.zone_setpoint = 72.0      # (T_sp) Desired occupied temperature in °F
        self.outdoor_temp = 90.0       # (T_o) Outdoor air temperature in °F

        # --- Historical Data Cache ---
        self.performance_history = []
        self.ema_weighting_factor = 2.0 # Standard EMA weighting factor

        # --- Tuned Parameters (will be updated from history) ---
        self.alpha_3a = 0.0
        self.alpha_3b = 0.0
        self.alpha_3c = 60.0 # This is a constant and not tuned
        self.alpha_3d = 0.0

    def generate_sample_data(self, num_days=10):
        """
        Populates the performance_history list with 10 days of sample data.
        This simulates the daily results that would be cached.
        """
        print(f"--- Generating {num_days} days of sample performance data... ---")
        # Tuples of (alpha_3a, alpha_3b, alpha_3d) for each day
        sample_params = [
            (2.8, 0.110, -2.0), # Day 1
            (2.7, 0.105, -1.0), # Day 2
            (2.6, 0.100, 0.0),  # Day 3
            (2.5, 0.095, 1.0),  # Day 4
            (2.5, 0.090, 1.5),  # Day 5
            (2.4, 0.092, 2.0),  # Day 6
            (2.4, 0.098, 3.0),  # Day 7
            (2.3, 0.100, 4.0),  # Day 8
            (2.2, 0.102, 4.5),  # Day 9 - System getting more efficient
            (2.2, 0.105, 5.0)   # Day 10 - Most recent day
        ]
        for i, params in enumerate(sample_params):
            day_num = i + 1
            record = PerformanceRecord(day=day_num, alpha_3a=params[0], alpha_3b=params[1], alpha_3d=params[2])
            self.performance_history.append(record)
        
        print("Sample data generated successfully.\n")
        for record in self.performance_history:
            print(record)

    def _compute_ema(self, series: list) -> float:
        """Calculates the Exponential Moving Average for a list of numbers."""
        if not series: return 0.0
        # The smoothing factor 'k' gives more weight to recent values
        k = self.ema_weighting_factor / (len(series) + 1)
        ema = series[0]
        for i in range(1, len(series)):
            ema = (series[i] * k) + (ema * (1 - k))
        return ema

    def tune_parameters_from_history(self):
        """
        Calculates the EMA for each parameter from the history and updates
        the model's current working parameters.
        """
        print("\n--- Tuning Parameters using EMA from 10-Day History ---")
        if not self.performance_history:
            print("No history available. Cannot tune parameters.")
            return

        # Create a time-series list for each parameter
        alpha_3a_series = [rec.alpha_3a for rec in self.performance_history]
        alpha_3b_series = [rec.alpha_3b for rec in self.performance_history]
        alpha_3d_series = [rec.alpha_3d for rec in self.performance_history]

        # Calculate the EMA for each and update the instance variables
        self.alpha_3a = self._compute_ema(alpha_3a_series)
        self.alpha_3b = self._compute_ema(alpha_3b_series)
        self.alpha_3d = self._compute_ema(alpha_3d_series)

        print(f"Tuned α3a (Rate): {self.alpha_3a:.3f} min/°F")
        print(f"Tuned α3b (Weather): {self.alpha_3b:.3f} min/°F")
        print(f"Tuned α3d (Offset): {self.alpha_3d:.2f} minutes")


    def calculate_optimal_start_time(self):
        """
        Calculates the optimal start time using the EMA-tuned parameters.
        """
        print("\n--- Calculating Today's Optimal Start Time with Tuned Parameters ---")
        
        # Part 1: Base Runtime
        temp_delta = self.zone_setpoint - self.zone_temp_initial
        base_runtime = self.alpha_3a * abs(temp_delta)
        
        # Part 2: Weather Compensation
        weather_factor = (self.zone_setpoint - self.outdoor_temp) / self.alpha_3c
        weather_compensation = self.alpha_3b * abs(temp_delta) * weather_factor
        weather_compensation = abs(weather_compensation)

        # Part 3: Learned Offset
        learned_offset = self.alpha_3d
        
        # Final Calculation
        total_optimal_start_time = base_runtime + weather_compensation + learned_offset

        print("\n--- Final Result ---")
        print(f"Base Runtime:           {base_runtime:5.1f} minutes (using tuned α3a)")
        print(f"Weather Compensation:   + {weather_compensation:5.1f} minutes (using tuned α3b)")
        print(f"Learned Offset:         + {learned_offset:5.1f} minutes (using tuned α3d)")
        print("---------------------------------")
        print(f"Total Estimated Start Time: {total_optimal_start_time:5.1f} minutes")
        
        return total_optimal_start_time

# --- Main Execution ---
if __name__ == "__main__":
    model3_sim = Model3_OptimalStart_With_History()
    
    # 1. Generate 10 days of historical performance data
    model3_sim.generate_sample_data()
    
    # 2. Tune the model's parameters using an EMA of that history
    model3_sim.tune_parameters_from_history()
    
    # 3. Calculate today's optimal start time using the newly tuned parameters
    model3_sim.calculate_optimal_start_time()