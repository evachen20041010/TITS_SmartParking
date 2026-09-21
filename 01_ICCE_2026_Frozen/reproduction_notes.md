2026-09-21:
The recovered sumo_py310 environment did not contain pandas.
The archived ICCE source requires pandas for CSV/KPI output.
pandas 2.2.3 was therefore installed for baseline reproduction.
The original historical pandas version is unknown.

---

2026-09-21:
Milestone 0A PASS.

ICCE-TW Free_95 / Seed 10 was reproduced using:

Python 3.10.18
SUMO 1.24.0
pandas 2.2.3

Archived and reproduced results were identical for:
- Is_Truncated = True
- N_Trips = 152
- Avg_Cruising_Time = 79.552631578947 s
- Total_CO2 = 37.4852 kg
- Trips with stopTime > 1 s = 149
- Trips with stopTime <= 1 s = 3
- Vaporized_traci = 97

The original historical pandas version is unknown.

---

2026-09-21:
Milestone 0B PASS.

The ICCE-TW Free_95 scenario was reproduced for all 10 original
random seeds (10, 20, ..., 100).

Results:
- Exact core matches: 10/10
- Mean N_Trips = 174.9
- Mean cruising time = 78.988812141207 s
- Mean Total CO2 = 42.80728 kg
- Truncated runs = 8/10 (80%)

Important historical discrepancy:
The archived simulation outputs contain 8/10 truncated Free_95 runs,
whereas the ICCE-TW manuscript states that 70% of free-search runs
exhibited systemic instability.

The current reproduction exactly matches the archived outputs.
No attempt was made to alter the archived simulation to match the
manuscript statement.

---

2026-09-21:
Milestone 0C PASS.
Milestone 0 COMPLETE.

The complete ICCE-TW experiment was reproduced for all four scenarios
and all 10 original random seeds (40 simulation runs total).

Exact core matches: 40/40.

Reconstructed aggregate results:

Free_85
- Mean N_Trips = 166.8
- Mean cruising time = 78.872922 s
- Mean Total CO2 = 40.778020 kg
- Truncated = 3/10

Free_95
- Mean N_Trips = 174.9
- Mean cruising time = 78.988812 s
- Mean Total CO2 = 42.807280 kg
- Truncated = 8/10

Assigned_85
- Mean N_Trips = 170.0
- Mean cruising time = 73.945294 s
- Mean Total CO2 = 38.969170 kg
- Truncated = 0/10

Assigned_95
- Mean N_Trips = 190.0
- Mean cruising time = 74.555263 s
- Mean Total CO2 = 43.913050 kg
- Truncated = 0/10

Historical discrepancy:
The archived Free_95 experiment contains 8/10 truncated runs (80%),
although the ICCE-TW manuscript reports 70%.

The reproduction exactly matches the archived simulation outputs.
No attempt was made to alter the archived experiment to match the
manuscript statement.
