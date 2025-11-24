"""
Super-simple optimal start Model 1 tutorial.

Model 1 assumes:
    warmup_minutes = a * (deltaT^2) + b

We will:
1. Make 3 fake datapoints
2. Compute a and b using the simplest algebra possible
3. Predict warmup minutes for a new deltaT
"""

# -----------------------------
# 1. Three fake datapoints
# -----------------------------
# Format: (deltaT, minutes_to_setpoint)
data = [
    (2, 10),   # if dT = 2F it took 10 minutes
    (4, 21),   # if dT = 4F it took 25 minutes
    (6, 59),   # if dT = 6F it took 50 minutes
]

# Convert to x = deltaT^2, y = minutes
xs = [dT**2 for (dT, t) in data]
ys = [t for (dT, t) in data]

# -----------------------------
# 2. Solve a and b for y = a*x + b
# -----------------------------
n = len(xs)
sum_x  = sum(xs)
sum_y  = sum(ys)
sum_xy = sum(x*y for x, y in zip(xs, ys))
sum_x2 = sum(x*x for x in xs)

# slope (a)
a = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x*sum_x)

# intercept (b)
b = (sum_y - a*sum_x) / n

print("Learned model:")
print(f"    minutes ≈ {a:.4f} * (deltaT^2) + {b:.4f}\n")

# -----------------------------
# 3. Predict future warmup time
# -----------------------------
def predict(deltaT):
    return a*(deltaT**2) + b

print("Prediction examples:")
for dT in [2, 4, 6, 8, 10]:
    print(f"  deltaT={dT}F → warmup ≈ {predict(dT):.1f} minutes")
