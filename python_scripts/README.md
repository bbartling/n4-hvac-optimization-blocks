## 💻 Python Versions of the Optimal Start Algorithms and API Reference (Model 1 & Model 3)

This reference outlines the consistent inputs and outputs used across `OptimalStartModel1` and `OptimalStartModel3` based on the PNNL paper in the [pdf](https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/pdf) directory.

### 1. ⚙️ Inputs (Setters)

These methods feed real-time and scheduled data into the model.

| Method | Type | Description |
| :--- | :--- | :--- |
| `set_zone_temp(value)` | `float` | Current **zone temperature** ($T_z$). |
| `set_outdoor_temp(value)` | `float` | Current **outdoor air temperature** ($T_o$) (Required by Model 3). |
| `set_target_zone_temp_setpoint(value)` | `float` | Desired **occupied set point** ($T_{sp}$). |
| `set_schedule_next_value(value)` | `bool` | `True` if the next schedule event is the start of occupancy. |
| `set_schedule_next_event_time_ms(value)` | `int` | Timestamp (in milliseconds) of the next scheduled occupancy event. |
| `set_clear_history_now(value)` | `bool` | Set to `True` to clear all learned **performance history**. |

---

### 2. 📊 Outputs (Getters)

These methods return the current state, predictions, and learned parameters.

| Method | Returns | Description |
| :--- | :--- | :--- |
| `get_minutes_to_setpoint_predicted()` | `float` | The **Estimated Time** ($t_{opt}$) (in minutes) required to reach the set point, which is the model's primary target output. |
| `get_equipment_start_command()` | `bool/None` | The recommended command: `True` to start RTU, `None` to be idle. |
| `get_is_running()` | `bool` | `True` if the optimal start sequence is currently active (run in progress). |
| `get_zone_at_temp_tolerance()` | `bool` | `True` if the zone temperature is within the tolerance band of the set point. |
| `get_degrees_per_minute_heat()` | `float` | **Learned average heating rate** (°F/min) based on historical data. |
| `get_degrees_per_minute_cool()` | `float` | **Learned average cooling rate** (°F/min) based on historical data. |
| `get_status_log()` | `str` | A formatted log string of the most recent system event. |
| `get_current_run_elapsed_minutes()` | `float` | Stopwatch: The elapsed time of the currently active optimal start run. |
| `get_countdown_to_null_status()` | `bool` | `True` when the **off-delay countdown** is actively preventing the command from resetting to `None`. |
| `get_current_history_record_count()` | `int` | The total number of performance records used for model tuning. |
| **`get_last_run_predicted_minutes()`** | `float` | The predicted time ($t_{opt}$) from the **start** of the last completed run. |
| **`get_last_run_actual_minutes()`** | `float` | The actual time ($t_{act}$) it took to reach the set point during the last run. |
| **`get_last_run_error_minutes()`** | `float` | The time error ($e_{time} = t_{act} - t_{opt}$) of the last completed run. |

---

## 3. 📝 Model Equations Summary

The models are formulated from a simplified thermal-resistance and capacitance model (2R1C or 1R1C) of the zone dynamics.

| Model | Underlying Equation | Description |
| :--- | :--- | :--- |
| **Model 1** | $t_{opt} = \alpha_{1,a}(T_{sp} - T_{z,0})^{2} + \alpha_{1,b}$ | **Quadratic:** Assumes thermal mass is concentrated in the indoor air (1R1C model) and neglects outdoor temperature influence. Best for interior/well-insulated zones. |
| **Model 3** | $t_{opt} = \alpha_{3,a}(T_{sp} - T_{z,0}) + \alpha_{3,b}(T_{sp} - T_{z,0})\frac{(T_{sp} - T_{o})}{\alpha_{3,c}} + \alpha_{3,d}$ | **Weather Compensated:** Uses a 2R1C approximation and includes outdoor air temperature ($T_o$) influence via the second term.|


The difference in implementation stems directly from the mathematical **complexity** of the underlying models:

* **Model 1** uses a **Simple Linear Regression** formulation ($y = mx + c$), which is easy to implement manually with a basic set of equations.
* **Model 3** requires **Multiple Linear Regression** ($y = a \cdot x_1 + b \cdot x_2 + d$), which is complex and better handled by a dedicated library like scikit-learn.

***

## 4. Model Details

**Model 1: Manual Simple Regression:**
$$t = \alpha_{1,a} \cdot (\Delta T^2) + \alpha_{1,b}$$

In this formula, the duration ($t$) is the dependent variable ($y$), and the squared temperature difference ($\Delta T^2$) is the single independent variable ($x$).

* **Implementation:** Model 1 implements the core tuning logic in `_compute_regression_for_mode` by manually calculating the sums needed for the **ordinary least squares (OLS)** solution.
* **Why Manual?** Simple Linear Regression has basic, closed-form equations (the familiar $\frac{n \Sigma xy - \Sigma x \Sigma y}{n \Sigma x^2 - (\Sigma x)^2}$ formula) that are short and reliable enough to code directly without needing external libraries.

***


**Model 3: Scikit-learn for Multiple Regression**
$$t = \alpha_{3,a} \cdot \Delta T + \alpha_{3,b} \cdot \Delta T \cdot \text{WF} + \alpha_{3,d}$$

In this formula, the model has **two distinct features** used for prediction:
1.  **Feature $x_1$:** The temperature difference ($\Delta T$).
2.  **Feature $x_2$:** The weather-compensated term ($\Delta T \cdot \text{WF}$), where $\text{WF} = \frac{T_{sp} - T_{o}}{60.0}$.

This is a classic **Multiple Linear Regression** problem, essentially fitting $y \approx \alpha_{3,a} \cdot x_1 + \alpha_{3,b} \cdot x_2 + \alpha_{3,d}$.

* **Implementation:** Model 3 uses the `sklearn.linear_model.LinearRegression` class in its `_compute_regression_for_mode` method.
* **Why Scikit-learn?** Implementing Multiple Linear Regression requires **matrix algebra** (specifically, solving $\mathbf{w} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{y}$). Using `scikit-learn` handles the necessary matrix computations (like inverting the feature matrix) and ensures better numerical stability and optimization, greatly simplifying the code compared to a manual implementation.