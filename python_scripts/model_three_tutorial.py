import math
import numpy as np
from sklearn.linear_model import LinearRegression
from collections import deque

# --- 1. Storing Raw Performance Data ---
# We store actual results: time taken (duration), temperature change (delta_t),
# and the outdoor temperature at the start (outdoor_temp_start).
class PerformanceRecord:
    def __init__(self, duration_minutes, delta_t, zone_temp_start, outdoor_temp_start):
        self.duration_minutes = duration_minutes # What we want to predict (y)
        self.delta_t = delta_t                 # Basis for feature x1
        self.zone_temp_start = zone_temp_start # Context
        self.outdoor_temp_start = outdoor_temp_start # Basis for feature x2

    def __repr__(self):
        oat_str = f"{self.outdoor_temp_start:.1f}" if not math.isnan(self.outdoor_temp_start) else "N/A"
        return f"Run(t={self.duration_minutes:.1f}min, dT={self.delta_t:.1f}F, OAT={oat_str}F)"

class Model3_OptimalStart_Sklearn_Tutorial:
    """Focuses on tuning Model 3 (t = a*dT + b*dT*WF + d) with sklearn."""

    ALPHA_C = 60.0 # Constant weather factor divisor

    def __init__(self):
        # Sample history - built over time in a real app
        self.history = deque([
            PerformanceRecord(duration_minutes=17.3, delta_t=6.0, zone_temp_start=78.0, outdoor_temp_start=88.2),
            PerformanceRecord(duration_minutes=16.6, delta_t=5.5, zone_temp_start=77.5, outdoor_temp_start=87.6),
            PerformanceRecord(duration_minutes=18.3, delta_t=6.5, zone_temp_start=78.5, outdoor_temp_start=91.1),
            PerformanceRecord(duration_minutes=19.9, delta_t=6.7, zone_temp_start=78.7, outdoor_temp_start=92.2),
            PerformanceRecord(duration_minutes=18.5, delta_t=6.2, zone_temp_start=78.2, outdoor_temp_start=90.3),
        ], maxlen=10) # Keep last 10 runs

        # Parameters to be learned by sklearn
        self.alpha_a = 2.5 # Default coefficient for dT
        self.alpha_b = 0.1 # Default coefficient for dT*WF
        self.alpha_d = 2.0 # Default offset (intercept)

        # Today's conditions for prediction
        self.zone_temp_initial = 78.0
        self.zone_setpoint = 72.0
        self.outdoor_temp = 90.0

    # --- 2. The Core Learning Logic ---
    def tune_parameters_with_sklearn(self):
        """Uses LinearRegression to find a, b, d from history."""
        print("\n--- Tuning Parameters with Scikit-learn ---")

        valid_records = [r for r in self.history if not math.isnan(r.outdoor_temp_start)]
        if len(valid_records) < 3:
            print("Not enough valid history data (need >= 3 with OAT). Using defaults.")
            return

        # --- 2a. Prepare Data for Regression ---
        # Target variable 'y': the actual time taken (duration)
        y = np.array([rec.duration_minutes for rec in valid_records])

        # --- MAGIC PART 1: Feature Engineering ---
        # Create the input features (X matrix) based on the Model 3 equation:
        # Feature x1 = delta_t
        # Feature x2 = abs(delta_t * WeatherFactor_at_start)
        X_list = []
        for rec in valid_records:
            # Calculate the WeatherFactor specific to the conditions *during that run*
            weather_factor_start = (self.zone_setpoint - rec.outdoor_temp_start) / self.ALPHA_C
            feature_x1 = rec.delta_t
            feature_x2 = abs(rec.delta_t * weather_factor_start) # Feature incorporating OAT
            X_list.append([feature_x1, feature_x2])
        X = np.array(X_list)
        # --- End of Feature Engineering ---

        # --- MAGIC PART 2: Scikit-learn Linear Regression ---
        # This is where sklearn does the heavy lifting. It finds the best 'a', 'b', and 'd'
        # to fit the equation: y ≈ a*x1 + b*x2 + d
        model = LinearRegression(fit_intercept=True) # Tell it to find 'd' (the intercept)
        model.fit(X, y)                       # Train the model on historical data
        # --- End of Scikit-learn Magic ---

        # --- MAGIC PART 3: Extract Learned Parameters ---
        # Sklearn stores the results in model.coef_ and model.intercept_
        self.alpha_a = max(0.0, model.coef_[0])     # Coefficient for x1 (delta_t)
        self.alpha_b = max(0.0, model.coef_[1])     # Coefficient for x2 (dT*WF)
        self.alpha_d = max(0.0, model.intercept_) # The intercept 'd'

        print(f"Input Features (X) shape: {X.shape}") # (num_runs, 2 features)
        print(f"Target Variable (y) shape: {y.shape}") # (num_runs,)
        print(f"Learned α_a (Coef for dT):    {self.alpha_a:.3f}")
        print(f"Learned α_b (Coef for dT*WF): {self.alpha_b:.3f}")
        print(f"Learned α_d (Intercept):    {self.alpha_d:.2f} minutes")


    # --- 3. Using the Learned Parameters for Prediction ---
    def calculate_optimal_start_time(self):
        """Calculates today's start time using the learned a, b, d."""
        print("\n--- Calculating Today's Optimal Start Time ---")

        delta_t_today = abs(self.zone_setpoint - self.zone_temp_initial)
        weather_factor_today = (self.zone_setpoint - self.outdoor_temp) / self.ALPHA_C

        # --- MAGIC PART 4: Apply Model 3 Formula ---
        # Use the parameters learned by sklearn to predict today's time
        term1 = self.alpha_a * delta_t_today
        term2 = self.alpha_b * abs(delta_t_today * weather_factor_today)
        term3 = self.alpha_d

        total_optimal_start_time = max(0.0, term1 + term2 + term3) # Ensure non-negative

        print(f"Term 1 (Base):   {term1:.1f} (using learned a={self.alpha_a:.2f})")
        print(f"Term 2 (Weather):{term2:.1f} (using learned b={self.alpha_b:.2f})")
        print(f"Term 3 (Offset): {term3:.1f} (using learned d={self.alpha_d:.1f})")
        print(f"--> Estimated Start Time: {total_optimal_start_time:.1f} minutes")
        return total_optimal_start_time

# --- Main Execution ---
if __name__ == "__main__":
    model3_tut = Model3_OptimalStart_Sklearn_Tutorial()

    print("--- Sample Performance History ---")
    for record in model3_tut.history:
        print(record)

    # The "Magic" happens here: Learn parameters from history
    model3_tut.tune_parameters_with_sklearn()

    # Predict today's time using the learned parameters
    model3_tut.calculate_optimal_start_time()

