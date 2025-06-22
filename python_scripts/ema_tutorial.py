class PerformanceRecord:
    """
    A simplified classic class to hold the essential performance data.
    """
    def __init__(self, rate, mode):
        self.rate = rate  # The key value: degrees per minute
        self.mode = mode

    def __repr__(self):
        """Provides a clean string representation for printing the object."""
        return f"PerformanceRecord(rate={self.rate}, mode='{self.mode}')"


class HvacPerformanceModel:
    """
    A class to manage HVAC performance history and run analytical calculations.
    """
    def __init__(self):
        """Initializes the model with history lists and a tunable EMA factor."""
        self.heat_history = []
        # This mimics the 'emaWeightingFactor' slot in the Java code.
        # It allows an operator to tune how responsive the EMA is.
        # Default is 2.0, which is standard for EMA.
        self.ema_weighting_factor = 2.0

    def generate_sample_data(self, num_days=10):
        """
        Populates the heat_history list with a simple list of rates.
        """
        print(f"--- Generating {num_days} days of sample heating data... ---")
        sample_rates = [0.15, 0.14, 0.16, 0.18, 0.15, 0.12, 0.13, 0.17, 0.19, 0.20]

        for rate_value in sample_rates:
            record = PerformanceRecord(rate=rate_value, mode="HEAT")
            self.heat_history.append(record)
        print("Sample data generated successfully.\n")


    def get_rates_from_history(self):
        """Extracts just the 'rate' from each record into a simple list."""
        return [record.rate for record in self.heat_history]

    def calculate_simple_average(self, series: list) -> float:
        """Calculates the simple arithmetic mean of a series."""
        if not series:
            return 0.0
        return sum(series) / len(series)

    def calculate_ema(self, series: list) -> float:
        """
        Calculates the Exponential Moving Average for a list of numbers.
        This now uses the tunable weighting factor from the class instance.
        """
        if not series:
            return 0.0

        # The smoothing factor 'k' is calculated using the tunable factor.
        k = self.ema_weighting_factor / (len(series) + 1)
        
        ema = series[0]
        
        for i in range(1, len(series)):
            ema = (series[i] * k) + (ema * (1 - k))
            
        return ema

    def run_analysis(self):
        """
        Executes the full analysis and prints a comparative report.
        """
        self.generate_sample_data()
        
        rates = self.get_rates_from_history()
        
        if not rates:
            print("No data available to analyze.")
            return
            
        simple_avg = self.calculate_simple_average(rates)
        ema_rate = self.calculate_ema(rates)

        print("--- Performance Analysis: Simple Average vs. EMA ---")
        print(f"Using an EMA Weighting Factor of: {self.ema_weighting_factor}")
        print(f"Historical Rates (deg/min): {rates}\n")
        
        print(f"Simple Average Rate: {simple_avg:.4f} deg/min")
        print("  - Treats every data point equally, from 10 days ago to today.\n")

        print(f"EMA Smoothed Rate:   {ema_rate:.4f} deg/min")
        print("  - Gives more weight to the most recent data points.\n")

        print("--- Conclusion ---")
        print("The EMA is higher because the system has performed better recently.")
        print("This makes it a more accurate predictor for the next heating cycle.")


# --- Main Execution ---
if __name__ == "__main__":
    hvac_model = HvacPerformanceModel()
    
    # You can now "tune" the model before running the analysis,
    # just like an operator would with the Java slot.
    # hvac_model.ema_weighting_factor = 3.0 # Example: make it even more responsive
    
    hvac_model.run_analysis()
