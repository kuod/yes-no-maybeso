"""Run the analysis; writes results/*.json and results/*.csv consumed by the site."""
import json, os, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
warnings.filterwarnings("ignore")
os.makedirs("results", exist_ok=True)
d = pd.read_csv("data/measures.csv")
iri = pd.read_csv("data/state_year.csv")
out = {}
BOOL = ["passed", "restrictive", "expansive", "mentions_tax_debt", "is_amendment", "mentions_increase", "mentions_repeal", "has_year_title"]

def _noop(): pass

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den; h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (c-h, c+h)

def rate(g):
    n = len(g); k = int(g.passed.sum()); lo, hi = wilson(k, n)
    return pd.Series(dict(n=n, passed=k, pass_rate=k/n, lo=lo, hi=hi, mean_yes_pct=g.yes_pct.mean()))

d_bool = d[BOOL].copy()  # keep boolean views for the groupby tables; cast copies for model fitting
# 1. headline
k, n = int(d.passed.sum()), len(d)
out["headline"] = dict(n=n, passed=k, pass_rate=k/n, ci=wilson(k, n), states=int(d.state.nunique()),
                       binom_p=float(stats.binomtest(k, n, 0.5).pvalue),
                       mean_yes_pct=float(d.yes_pct.mean()), median_yes_pct=float(d.yes_pct.median()), n_with_pct=int(d.yes_pct.notna().sum()))

# 2. by state / decade / domain / topic / type
for key in ["state", "decade", "domain", "topic", "mtype"]:
    t = d.groupby(key).apply(rate).reset_index().sort_values("pass_rate", ascending=False)
    t.to_csv(f"results/by_{key}.csv", index=False)
    out[f"by_{key}"] = t.round(4).to_dict("records")

# 3. wording features: raw differences
feats = ["restrictive", "expansive", "mentions_tax_debt", "is_amendment", "mentions_increase", "mentions_repeal", "has_year_title"]
rows = []
for f in feats:
    a, b = d[d[f]], d[~d[f]]
    ct = [[a.passed.sum(), (~a.passed).sum()], [b.passed.sum(), (~b.passed).sum()]]
    chi_p = stats.chi2_contingency(ct)[1]
    rows.append(dict(feature=f, n_with=len(a), rate_with=a.passed.mean(), n_without=len(b), rate_without=b.passed.mean(),
                     diff=a.passed.mean()-b.passed.mean(), chi2_p=chi_p))
wf = pd.DataFrame(rows); wf.to_csv("results/wording_raw.csv", index=False)
out["wording_raw"] = wf.round(4).to_dict("records")
d["len_bin"] = pd.qcut(d.n_words, 4, labels=["shortest 25%", "short-mid", "long-mid", "longest 25%"])
lb = d.groupby("len_bin").apply(rate).reset_index(); out["by_length"] = lb.round(4).to_dict("records")
r, p = stats.spearmanr(d.n_words, d.yes_pct, nan_policy="omit"); out["len_vs_yespct"] = dict(rho=float(r), p=float(p))

# 4. regression: logit with state + decade fixed effects (cluster by state-year)
d["zlen"] = (np.log(d.n_words) - np.log(d.n_words).mean()) / np.log(d.n_words).std()
dd = d.dropna(subset=["flesch"]).copy()
dd[BOOL] = dd[BOOL].astype(int)
dd["zflesch"] = (dd.flesch - dd.flesch.mean()) / dd.flesch.std()
dd["sy"] = dd.state + dd.year.astype(str)
f = "passed ~ restrictive + expansive + mentions_tax_debt + mentions_increase + mentions_repeal + is_amendment + zlen + zflesch + C(domain, Treatment('other')) + C(state) + C(decade)"
m = smf.logit(f, dd).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.sy)[0]})
co = pd.DataFrame(dict(coef=m.params, se=m.bse, p=m.pvalues, odds=np.exp(m.params), lo=np.exp(m.conf_int()[0]), hi=np.exp(m.conf_int()[1])))
co = co[~co.index.str.startswith(("C(state)", "C(decade)", "Intercept"))]
co.to_csv("results/logit_wording.csv"); out["logit_wording"] = co.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records")
out["logit_n"] = int(m.nobs); out["logit_pseudo_r2"] = float(m.prsquared)

# 4b. within-state yes% OLS (continuous outcome, where vote shares exist)
dp = dd.dropna(subset=["yes_pct"])
mo = smf.ols("yes_pct ~ restrictive + expansive + mentions_tax_debt + mentions_increase + mentions_repeal + is_amendment + zlen + zflesch + C(domain, Treatment('other')) + C(state) + C(decade)", dp).fit(cov_type="HC1")
co2 = pd.DataFrame(dict(coef=mo.params, se=mo.bse, p=mo.pvalues))
co2 = co2[~co2.index.str.startswith(("C(state)", "C(decade)", "Intercept"))]
co2.to_csv("results/ols_yespct.csv"); out["ols_yespct"] = co2.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"); out["ols_n"] = int(mo.nobs)

# 5. type (initiative vs legislative) where known
kt = d[d.mtype != "unknown"]
tt = kt.groupby("mtype").apply(rate).reset_index(); out["type_known"] = tt.round(4).to_dict("records")
if kt.mtype.nunique() == 2:
    a, b = kt[kt.mtype == "initiative"], kt[kt.mtype == "legislative"]
    out["type_chi2_p"] = float(stats.chi2_contingency([[a.passed.sum(), (~a.passed).sum()], [b.passed.sum(), (~b.passed).sum()]])[1])
dt = kt.groupby(["domain", "mtype"]).apply(rate).reset_index(); dt.to_csv("results/by_domain_type.csv", index=False)
out["by_domain_type"] = dt.round(4).to_dict("records")

# 6. state trends: IRI aggregates (all initiative states) vs our measure-level subset
agg = iri.groupby("state").agg(initiatives=("initiatives", "sum"), approved=("approved", "sum")).reset_index()
agg["iri_approval"] = agg.approved / agg.initiatives
agg.sort_values("iri_approval").to_csv("results/iri_state_approval.csv", index=False)
out["iri_state"] = agg.round(4).to_dict("records")
iri["decade"] = (iri.year // 10) * 10
idec = iri.groupby("decade").agg(initiatives=("initiatives", "sum"), approved=("approved", "sum")).reset_index()
idec["approval"] = idec.approved / idec.initiatives; out["iri_decade"] = idec.round(4).to_dict("records")
init = d[d.mtype == "initiative"].groupby("state").agg(n=("passed", "size"), rate=("passed", "mean")).reset_index()
cmp_ = init.merge(agg[["state", "iri_approval", "initiatives"]], on="state")
cmp_["gap"] = cmp_.rate - cmp_.iri_approval; out["scrape_vs_iri"] = cmp_.round(4).to_dict("records")
# state baseline effect: does a measure beat its own state's long-run rate? (leave-one-out state rate)
d["state_rate_loo"] = d.groupby("state").passed.transform(lambda s: (s.sum() - s) / (len(s) - 1))
db = d[d.groupby("state").passed.transform("size") > 20].copy(); db["passed"] = db.passed.astype(int)
mb = smf.logit("passed ~ state_rate_loo", db).fit(disp=0)
out["state_baseline"] = dict(coef=float(mb.params["state_rate_loo"]), p=float(mb.pvalues["state_rate_loo"]))
# yes% trend over time (pooled and per state), by-year pass rate
yr = d.groupby("year").apply(rate).reset_index(); yr.to_csv("results/by_year.csv", index=False); out["by_year"] = yr.round(4).to_dict("records")
tr = stats.linregress(d.groupby("year").passed.mean().index, d.groupby("year").passed.mean().values)
out["trend_pass_rate"] = dict(slope_per_decade=float(tr.slope*10), p=float(tr.pvalue))
# state x domain heat
sd = d.groupby(["state", "domain"]).passed.agg(["size", "mean"]).reset_index(); sd.to_csv("results/state_domain.csv", index=False)
out["state_domain"] = sd.round(3).to_dict("records")

# margins: how lopsided are passes vs fails
dp = d.dropna(subset=["yes_pct"])
out["margins"] = dict(mean_yes_when_pass=float(dp[dp.passed].yes_pct.mean()), mean_yes_when_fail=float(dp[~dp.passed].yes_pct.mean()),
                      share_pass_above_60=float((dp[dp.passed].yes_pct > 60).mean()), share_fail_below_40=float((dp[~dp.passed].yes_pct < 40).mean()))
json.dump(out, open("results/summary.json", "w"), indent=1, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else str(o))
print(json.dumps({k: out[k] for k in ["headline", "trend_pass_rate", "type_known", "state_baseline", "margins", "logit_n", "ols_n"] if k in out}, indent=1, default=str))
print(wf.round(3).to_string()); print(co.round(3).to_string()); print(co2.round(3).to_string())
print(pd.DataFrame(out["by_domain"])[["domain","n","pass_rate","lo","hi"]].round(3).to_string())

# 7. robustness: (a) wording model on known-origin subset with origin control; (b) decade trend in full-coverage states only
kk = dd[dd.mtype != "unknown"].copy()
mk = smf.logit("passed ~ restrictive + expansive + mentions_tax_debt + mentions_increase + mentions_repeal + is_amendment + zlen + zflesch + C(mtype) + C(domain, Treatment('other')) + C(state)", kk).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(kk.sy)[0]})
ck = pd.DataFrame(dict(coef=mk.params, se=mk.bse, p=mk.pvalues, odds=np.exp(mk.params), lo=np.exp(mk.conf_int()[0]), hi=np.exp(mk.conf_int()[1])))
ck = ck[~ck.index.str.startswith(("C(state)", "Intercept"))]
ck.to_csv("results/logit_known_origin.csv"); out["logit_known_origin"] = ck.round(4).reset_index().rename(columns={"index": "term"}).to_dict("records"); out["logit_known_n"] = int(mk.nobs)
yrs = d.groupby("state").year.agg(["min", "max"])
full = yrs[(yrs["min"] <= 1982) & (yrs["max"] >= 2020)].index.tolist(); out["full_coverage_states"] = full
fd = d[d.state.isin(full)].groupby("decade").apply(rate).reset_index(); fd.to_csv("results/by_decade_fullcov.csv", index=False); out["by_decade_fullcov"] = fd.round(4).to_dict("records")
print("FULL", full); print(fd.round(3).to_string()); print(ck.round(3).to_string())
json.dump(out, open("results/summary.json", "w"), indent=1, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else str(o))
