"""Does partisan context (presidential lean/shift, governor, legislature) relate to yes/no outcomes?
Reads data/measures_politics.csv; writes results/politics.json and results/politics_*.csv. Run from repo root."""
import json, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
warnings.filterwarnings("ignore")

d = pd.read_csv("data/measures_politics.csv")
d = d[d.state != "District of Columbia"].copy()          # no governor/legislature
d["sy"] = d.state + d.year.astype(str)
d["passed_i"] = d.passed.astype(int)
d["lean10"] = d.lean / 10                                # +1 = 10 pts more Democratic
d["shift10"] = d.shift4 / 10                             # +1 = moved 10 pts toward Democrats since previous presidential race
d["shift8_10"] = d.shift8 / 10
d["shift_dir"] = pd.cut(d.shift4, [-100, -2, 2, 100], labels=["toward R (>2 pts)", "flat (±2)", "toward D (>2 pts)"])
d["lean_cat"] = pd.cut(d.lean, [-100, -10, 10, 100], labels=["R-leaning (>10 pts)", "competitive (±10)", "D-leaning (>10 pts)"])
out = {}

def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h

def yes_ci(g):
    """Mean yes share (%) with a t-based 95% interval; NaN when fewer than 3 measures have a share."""
    y = g.yes_pct.dropna(); n = len(y)
    if n < 3:
        return dict(mean_yes_pct=y.mean() if n else float("nan"), yes_lo=float("nan"), yes_hi=float("nan"), yes_n=n)
    h = stats.t.ppf(0.975, n - 1) * y.std(ddof=1) / n ** 0.5
    return dict(mean_yes_pct=y.mean(), yes_lo=y.mean() - h, yes_hi=y.mean() + h, yes_n=n)


def rate(g):
    n = len(g); k = int(g.passed.sum()); lo, hi = wilson(k, n)
    return pd.Series(dict(n=n, pass_rate=k / n, lo=lo, hi=hi, **yes_ci(g)))

def tab(df, key, name):
    t = df.groupby(key, observed=True).apply(rate).reset_index()
    t.to_csv(f"results/politics_{name}.csv", index=False)
    return t.round(4).to_dict("records")

# ---- descriptive splits
out["by_gov"] = tab(d[d.gov_party.isin(["D", "R"])], "gov_party", "gov")
out["by_leg"] = tab(d.dropna(subset=["leg_ctrl"]), "leg_ctrl", "leg")
out["by_trifecta"] = tab(d.dropna(subset=["trifecta"]), "trifecta", "trifecta")
out["by_lean_cat"] = tab(d.dropna(subset=["lean"]), "lean_cat", "lean")
out["by_shift_dir"] = tab(d.dropna(subset=["shift4"]), "shift_dir", "shift")
# does the answer depend on measure origin?
kt = d[(d.mtype != "unknown") & d.gov_party.isin(["D", "R"])]
out["gov_by_origin"] = tab(kt, ["mtype", "gov_party"], "gov_origin")
out["leg_by_origin"] = tab(d[(d.mtype != "unknown") & d.leg_ctrl.notna()], ["mtype", "leg_ctrl"], "leg_origin")

# ---- within-state: pass rate when state moved toward D vs toward R (states with >=8 in each cell)
w = d.dropna(subset=["shift4"]); w = w[w.shift_dir != "flat (±2)"]
ws = w.groupby(["state", "shift_dir"], observed=True).apply(rate).reset_index()
cnt = ws.pivot(index="state", columns="shift_dir", values="n")
ok = cnt[(cnt >= 8).all(axis=1)].index
ws = ws[ws.state.isin(ok)]; ws.to_csv("results/politics_state_shift.csv", index=False)
out["state_shift"] = ws.round(4).to_dict("records")

# ---- models (logit, state + decade FE, clustered by state-election)
def fit(formula, data, cluster="sy"):
    m = smf.logit(formula, data).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(data[cluster])[0]})
    ci = m.conf_int()
    t = pd.DataFrame(dict(coef=m.params, se=m.bse, p=m.pvalues, odds=np.exp(m.params), lo=np.exp(ci[0]), hi=np.exp(ci[1])))
    return m, t[~t.index.str.startswith(("C(state)", "C(decade)", "Intercept"))]

base = "C(domain, Treatment('other')) + C(state) + C(decade)"
dm = d.dropna(subset=["lean10", "shift10"]).copy()
m1, t1 = fit(f"passed_i ~ lean10 + shift10 + {base}", dm)
out["m1"] = dict(n=int(m1.nobs), rows=t1.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

dg = dm[dm.gov_party.isin(["D", "R"]) & dm.leg_ctrl.notna()].copy()
dg["gov_D"] = (dg.gov_party == "D").astype(int)
dg["leg_cat"] = dg.leg_ctrl
m2, t2 = fit(f"passed_i ~ lean10 + shift10 + gov_D + C(leg_cat, Treatment('R')) + {base}", dg)
out["m2"] = dict(n=int(m2.nobs), rows=t2.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# governor + legislature only (drop presidential terms) to see whether lean is absorbing them
m2b, t2b = fit(f"passed_i ~ gov_D + C(leg_cat, Treatment('R')) + {base}", dg)
out["m2b"] = dict(n=int(m2b.nobs), rows=t2b.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# 8-year shift (two cycles)
d8 = dm.dropna(subset=["shift8_10"])
m3, t3 = fit(f"passed_i ~ lean10 + shift8_10 + {base}", d8)
out["m3"] = dict(n=int(m3.nobs), rows=t3.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# lean x domain  (does partisanship matter more for social/economic topics?)
dm["dom"] = dm.domain
m4, t4 = fit(f"passed_i ~ lean10:C(dom) + shift10:C(dom) + C(dom) + C(state) + C(decade)", dm)
out["m4"] = dict(n=int(m4.nobs), rows=t4[t4.index.str.contains("lean10|shift10")].round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# known-origin: do referrals vs initiatives respond differently to partisanship?
dk = dg[dg.mtype != "unknown"].copy()
m5, t5 = fit(f"passed_i ~ (lean10 + shift10 + gov_D)*C(mtype) + C(leg_cat, Treatment('R')) + C(domain, Treatment('other')) + C(state) + C(decade)", dk)
out["m5"] = dict(n=int(m5.nobs), rows=t5.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# continuous outcome: yes share (CA has none)
dy = dg.dropna(subset=["yes_pct"])
o = smf.ols(f"yes_pct ~ lean10 + shift10 + gov_D + C(leg_cat, Treatment('R')) + {base}", dy).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dy.sy)[0]})
to = pd.DataFrame(dict(coef=o.params, se=o.bse, p=o.pvalues)); to = to[~to.index.str.startswith(("C(state)", "C(decade)", "Intercept"))]
out["ols_yes"] = dict(n=int(o.nobs), rows=to.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"))

# how much did states actually move? (context for the 'becoming more D/R' question)
pr = pd.read_csv("data/presidential.csv"); pr = pr[pr.state.isin(d.state.unique())]
mv = pr.pivot(index="state", columns="year", values="dem_margin")
out["lean_change_1980_2024"] = (mv[2024] - mv[1980]).round(1).sort_values().to_dict()
out["lean_2024"] = mv[2024].round(1).to_dict(); out["lean_1980"] = mv[1980].round(1).to_dict()
out["lean_series"] = {s: mv.loc[s].round(1).to_dict() for s in mv.index}
out["coverage"] = dict(n=int(len(d)), n_lean=int(d.lean.notna().sum()), n_shift=int(d.shift4.notna().sum()), n_gov=int(d.gov_party.notna().sum()))
json.dump(out, open("results/politics.json", "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else str(o))

pd.set_option("display.width", 200)
for k in ["by_gov", "by_leg", "by_trifecta", "by_lean_cat", "by_shift_dir", "gov_by_origin", "leg_by_origin"]:
    print("##", k); print(pd.DataFrame(out[k]).round(3).to_string(index=False))
for k in ["m1", "m2", "m2b", "m3", "m4", "m5", "ols_yes"]:
    print("##", k, "n =", out[k]["n"]); print(pd.DataFrame(out[k]["rows"]).round(3).to_string(index=False))
print(out["coverage"]); print(out["lean_change_1980_2024"])
