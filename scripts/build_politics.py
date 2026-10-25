"""Attach partisan context to each measure -> data/measures_politics.csv.

Inputs : data/measures.csv, data/presidential.csv, data/raw/politics/gov_leg_*.csv (state-year governor + legislature)
Outputs: data/state_politics.csv (state-year context), data/measures_politics.csv

Definitions
- last_pres: most recent presidential election strictly BEFORE the measure's year (a same-year race is contemporaneous, not history).
- lean: Democratic two-party margin (pts) at last_pres; positive = Democratic-leaning.
- shift4: lean change vs the presidential election before last_pres (pts; + = moved toward Democrats).
- shift8: lean change vs two cycles before last_pres.
- gov_party / senate_ctrl / house_ctrl / leg_ctrl / trifecta: as shown in Wikipedia's party-strength tables for the measure's year.
"""
import glob
import numpy as np, pandas as pd

m = pd.read_csv("data/measures.csv")
pres = pd.read_csv("data/presidential.csv").set_index(["state", "year"]).dem_margin
PY = sorted(pres.index.get_level_values(1).unique())


def prior(y):
    c = [p for p in PY if p < y]
    return c[-1] if c else None


def lag(state, y, k):
    py = prior(y)
    if py is None:
        return np.nan, None
    i = PY.index(py)
    if k == 0:
        return pres.get((state, py), np.nan), py
    return (pres.get((state, PY[i - k]), np.nan) if i - k >= 0 else np.nan), py


lean, s4, s8, lp = [], [], [], []
for st, y in zip(m.state, m.year):
    a, py = lag(st, y, 0)
    b, _ = lag(st, y, 1)
    c, _ = lag(st, y, 2)
    lean.append(a); s4.append(a - b if pd.notna(b) else np.nan); s8.append(a - c if pd.notna(c) else np.nan); lp.append(py)
m["last_pres"], m["lean"], m["shift4"], m["shift8"] = lp, lean, s4, s8

files = sorted(glob.glob("data/raw/politics/gov_leg_*.csv"))
if files:
    sp = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    def ctrl(d, r):
        if pd.isna(d) or pd.isna(r):
            return np.nan
        return "D" if d > r else "R" if r > d else "tie"

    sp["senate_ctrl"] = [ctrl(a, b) for a, b in zip(sp.senate_dem, sp.senate_rep)]
    sp["house_ctrl"] = [ctrl(a, b) for a, b in zip(sp.house_dem, sp.house_rep)]
    def leg(sen, hou):
        if pd.isna(sen) or pd.isna(hou):
            return np.nan
        return sen if sen == hou and sen in ("D", "R") else "split"

    def tri(l, g):
        if pd.isna(l) or pd.isna(g):
            return np.nan
        return "D trifecta" if l == "D" and g == "D" else "R trifecta" if l == "R" and g == "R" else "divided"

    sp["leg_ctrl"] = [leg(a, b) for a, b in zip(sp.senate_ctrl, sp.house_ctrl)]
    sp["trifecta"] = [tri(l, g) for l, g in zip(sp.leg_ctrl, sp.gov_party)]
    sp.to_csv("data/state_politics.csv", index=False)
    m = m.merge(sp[["state", "year", "gov_party", "senate_ctrl", "house_ctrl", "leg_ctrl", "trifecta"]], on=["state", "year"], how="left")
m.to_csv("data/measures_politics.csv", index=False)
print(len(m), "rows;", "with lean:", m.lean.notna().sum(), "| with shift4:", m.shift4.notna().sum(),
      "| with gov:", m.get("gov_party", pd.Series(dtype=object)).notna().sum() if "gov_party" in m else "n/a")
