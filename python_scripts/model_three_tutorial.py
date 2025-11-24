"""
Super-simple Model 3 tutorial.
Matches the PNNL equation exactly:

    warmup_minutes = a*(dT) + b*(dT*WF) + d

We will:
1. Make 3 fake datapoints
2. Compute the linear regression coefficients (a, b, d)
3. Predict warmup minutes for a new situation
"""

# ----------------------------
# 1. Three fake datapoints
# ----------------------------
# Format: (deltaT, outdoor_temp_at_start, warmup_minutes)
data = [
    (5, 80, 18),   # dT=5, OAT=80F → took 18 min
    (6, 90, 22),   # dT=6, OAT=90F → took 22 min
    (4, 70, 16),   # dT=4, OAT=70F → took 16 min
]

Tset = 72           # assume setpoint is 72F
ALPHA_C = 60.0      # same divisor used in your codebase


# ----------------------------
# 2. Build X matrix and y
# ----------------------------
X = []
y = []

for dT, oat, minutes in data:
    WF = (Tset - oat)/ALPHA_C        # Weather factor
    x1 = dT                          # Feature 1
    x2 = dT * WF                     # Feature 2
    X.append([x1, x2, 1])            # add constant term for intercept
    y.append(minutes)

# Convert to normal Python lists only — avoid numpy for simplicity
# X is a list of rows:  [[x1,x2,1], [x1,x2,1], ...]
# y is list: [18,22,16]


# ----------------------------
# 3. Solve linear regression by hand
# ----------------------------
# We will solve:
#     y = a*x1 + b*x2 + d*1
#
# Use the closed-form solution for 3 equations & 3 unknowns.

# Extract columns for clarity
x1_vals = [row[0] for row in X]
x2_vals = [row[1] for row in X]
ones    = [1,1,1]

# Sums
Sx1  = sum(x1_vals)
Sx2  = sum(x2_vals)
S1   = 3                   # three samples
Sy   = sum(y)
Sx1y = sum(x1*y_i for x1,y_i in zip(x1_vals,y))
Sx2y = sum(x2*y_i for x2,y_i in zip(x2_vals,y))
Sx1x1 = sum(x1*x1 for x1 in x1_vals)
Sx2x2 = sum(x2*x2 for x2 in x2_vals)
Sx1x2 = sum(x1*x2 for x1,x2 in zip(x1_vals,x2_vals))

# Solve system:
# |Sx1x1  Sx1x2  Sx1|   |a|   |Sx1y|
# |Sx1x2  Sx2x2  Sx2| * |b| = |Sx2y|
# |Sx1    Sx2    S1 |   |d|   |Sy  |

import numpy as np

A = np.array([
    [Sx1x1, Sx1x2, Sx1],
    [Sx1x2, Sx2x2, Sx2],
    [Sx1,   Sx2,   S1 ],
], dtype=float)

B = np.array([Sx1y, Sx2y, Sy], dtype=float)

a, b, d = np.linalg.solve(A, B)

print("Learned Model 3 parameters:")
print(f"  a (coef for dT):     {a:.4f}")
print(f"  b (coef for dT*WF):  {b:.4f}")
print(f"  d (intercept):       {d:.4f}\n")


# ----------------------------
# 4. Predict warmup time
# ----------------------------
def predict(dT_today, oat_today):
    WF_today = (Tset - oat_today)/ALPHA_C
    return a*dT_today + b*(dT_today*WF_today) + d

print("Example predictions:")
for oat in [60, 80, 95]:
    print(f"OAT={oat}F → warmup ≈ {predict(6, oat):.1f} minutes")
