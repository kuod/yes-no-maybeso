"""Adversarial checks on the headline results -> results/robustness.json. Run from repo root after the other scripts."""
import json, re, sys, warnings
import numpy as np, pandas as pd, patsy
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
sys.path.insert(0, "scripts")
import build_dataset as B

out = {}
d = pd.read_csv("data/measures.csv"); d["pi"] = d.passed.astype(int); d["sy"] = d.state + d.year.astype(str)
for c in ["restrictive", "expansive", "mentions_tax_debt", "mentions_increase", "mentions_repeal", "is_amendment"]:
    d[c] = d[c].astype(int)
d["zlen"] = (np.log(d.n_words) - np.log(d.n_words).mean()) / np.log(d.n_words).std()

# 1. repeal effect: leave-one-state-out
F = "pi ~ mentions_repeal + restrictive + expansive + mentions_tax_debt + is_amendment + zlen + C(domain,Treatment('other')) + C(state) + C(decade)"
def fit(x, f=F):
    return smf.logit(f, x).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(x.sy)[0]})
loo = {s: float(np.exp(fit(d[d.state != s]).params["mentions_repeal"])) for s in sorted(d.state.unique())}
pl = {s: float(fit(d[d.state != s]).pvalues["mentions_repeal"]) for s in loo}
out["repeal_loo"] = dict(min=min(loo.values()), max=max(loo.values()), max_p=max(pl.values()), n_states_with_repeal=int(d[d.mentions_repeal == 1].state.nunique()), n_repeal=int(d.mentions_repeal.sum()))
k = d[d.mtype != "unknown"]
out["repeal_raw_by_origin"] = {f"{t}_{r}": float(k[(k.mtype == t) & (k.mentions_repeal == r)].passed.mean()) for t in ("initiative", "legislative") for r in (0, 1)}
out["regex_corr_expansive_amendment"] = float(d.expansive.corr(d.is_amendment))

# 2. origin gap within state (states with >=10 of each identified origin)
w = k.groupby(["state", "mtype"]).size().unstack(fill_value=0); ok = w[(w >= 10).all(axis=1)].index.tolist()
kk = k[k.state.isin(ok)].copy(); kk["leg"] = (kk.mtype == "legislative").astype(int)
m = smf.logit("pi ~ leg + C(state) + C(decade)", kk).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(kk.sy)[0]})
ci = np.exp(m.conf_int().loc["leg"])
out["origin_within_state"] = dict(states=ok, odds=float(np.exp(m.params["leg"])), lo=float(ci[0]), hi=float(ci[1]), p=float(m.pvalues["leg"]), n=int(m.nobs))
raw = B.collect(); raw = raw[raw.year.between(B.FIRST, B.LAST) & raw.passed.notna()]
key = ["state", "year", "measure", "description"]
inf = d.merge(raw[key + ["mtype"]].rename(columns={"mtype": "src"}).drop_duplicates(key), on=key, how="left")
out["origin_share_from_text"] = float(((inf.src == "unknown") & (inf.mtype != "unknown")).sum() / (inf.mtype != "unknown").sum())
out["oregon_share_of_legislative"] = float(((k.mtype == "legislative") & (k.state == "Oregon")).sum() / (k.mtype == "legislative").sum())

# 3. completeness vs IRI initiative counts
iy = pd.read_csv("data/state_year.csv"); sy = d.groupby(["state", "year"]).size().rename("scraped").reset_index()
j = iy.merge(sy, on=["state", "year"], how="left").fillna({"scraped": 0}); j = j[j.state.isin(d.state.unique())]
gap = j[j.scraped < j.initiatives]
out["completeness"] = dict(state_years_checked=int(len(j)), state_years_short=int(len(gap)), initiatives_missing_lower_bound=int((gap.initiatives - gap.scraped).sum()),
                           by_state=(gap.initiatives - gap.scraped).groupby(gap.state).sum().astype(int).to_dict())

# 4. politics: clustering level, few-cluster wild bootstrap, leave-one-out, FE sensitivity
p = pd.read_csv("data/measures_politics.csv"); p = p[p.state != "District of Columbia"].copy()
p["pi"] = p.passed.astype(int); p["sy"] = p.state + p.year.astype(str); p["lean10"] = p.lean / 10; p["shift10"] = p.shift4 / 10
p = p.dropna(subset=["lean10", "shift10"]); p = p[p.gov_party.isin(["D", "R"]) & p.leg_ctrl.notna()].copy()
p["gov_D"] = (p.gov_party == "D").astype(int); p["legD"] = (p.leg_ctrl == "D").astype(int); p["legS"] = (p.leg_ctrl == "split").astype(int)
base = "C(domain,Treatment('other')) + C(state) + C(decade)"
f = f"pi ~ lean10 + shift10 + gov_D + legD + legS + {base}"
def runp(fm, x, cl):
    return smf.logit(fm, x).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(x[cl])[0]})
ms = runp(f, p, "state")
out["politics_state_clustered"] = {t: dict(odds=float(np.exp(ms.params[t])), p=float(ms.pvalues[t])) for t in ["lean10", "shift10", "gov_D", "legD", "legS"]}
g1 = {s: float(np.exp(runp(f, p[p.state != s], "state").params["gov_D"])) for s in sorted(p.state.unique())}
out["gov_D_loo_range"] = [min(g1.values()), max(g1.values())]
mn = runp(f"pi ~ lean10 + shift10 + gov_D + legD + legS + C(domain,Treatment('other')) + C(state)", p, "state")
out["politics_no_decade_fe"] = {t: dict(odds=float(np.exp(mn.params[t])), p=float(mn.pvalues[t])) for t in ["lean10", "shift10", "gov_D"]}

dy = p.dropna(subset=["yes_pct"]).copy()
y, X = patsy.dmatrices("yes_pct ~ lean10 + shift10 + gov_D + legD + legS + " + base, dy, return_type="dataframe")
cols = list(X.columns); j_ = cols.index("gov_D"); g = pd.factorize(dy.state)[0]; G = int(g.max() + 1); Xv, yv = X.values, y.values.ravel()
def fit_t(yy, XX):
    XtXi = np.linalg.pinv(XX.T @ XX); b = XtXi @ XX.T @ yy; u = yy - XX @ b
    meat = sum(np.outer(XX[g == k_].T @ u[g == k_], XX[g == k_].T @ u[g == k_]) for k_ in range(G))
    n, kk_ = XX.shape; V = G / (G - 1) * (n - 1) / (n - kk_) * XtXi @ meat @ XtXi
    return b[j_], b[j_] / np.sqrt(V[j_, j_])
b0, t0 = fit_t(yv, Xv)
Xr = np.delete(Xv, j_, axis=1); br = np.linalg.lstsq(Xr, yv, rcond=None)[0]; fr = Xr @ br; ur = yv - fr
rng = np.random.default_rng(0); Bn = 2999
ts = np.array([fit_t(fr + rng.choice([-1.0, 1.0], size=G)[g] * ur, Xv)[1] for _ in range(Bn)])
out["gov_D_yes_share"] = dict(coef=float(b0), t=float(t0), clusters=G, n=int(len(dy)), wild_bootstrap_p=float((np.sum(np.abs(ts) >= abs(t0)) + 1) / (Bn + 1)))
json.dump(out, open("results/robustness.json", "w"), indent=1)
print(json.dumps(out, indent=1))
