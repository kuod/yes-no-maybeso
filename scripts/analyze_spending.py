"""Exploratory: Washington measure-level campaign spending vs outcome. data/measures_spending.csv -> results/spending.json
Run from repo root:  python3 -I scripts/analyze_spending.py
"""
import json
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import spearmanr, fisher_exact

w = pd.read_csv("data/measures_spending.csv")
allm = w[w.kind.notna()]
w = allm[allm.spend.notna()].copy()
w["ls"] = np.log10(w.spend + 1000)
out = dict(n_initref=int(len(allm)), n=int(len(w)), n_zero=int((w.spend == 0).sum()), median_spend=float(w.spend.median()),
           total_spend=float(w.spend.sum()), years=[int(w.year.min()), int(w.year.max())])
r, p = spearmanr(w.spend, w.margin); out["spearman_margin"] = dict(r=float(r), p=float(p))
# within-year permutation: shuffle spending among measures of the same year, so a year's electorate/turnout cannot drive the result
rng = np.random.default_rng(0); obs = spearmanr(w.spend, w.margin)[0]; cnt = 0; B = 5000
grp = [g.index.values for _, g in w.groupby("year")]
for _ in range(B):
    sp = w.spend.copy()
    for ix in grp:
        sp.loc[ix] = rng.permutation(w.spend.loc[ix].values)
    cnt += abs(spearmanr(sp, w.margin)[0]) >= abs(obs)
out["perm_within_year"] = dict(r=float(obs), p=float((cnt + 1) / (B + 1)), draws=B)
w["hi"] = w.spend > w.spend.median()
g = w.groupby("hi").agg(n=("passed", "size"), pass_rate=("passed", "mean"), margin=("margin", "mean"))
out["median_split"] = {("high" if k else "low"): {c: float(v) for c, v in row.items()} for k, row in g.iterrows()}
f = smf.ols("margin ~ ls", w).fit(cov_type="HC1")
out["ols"] = dict(coef=float(f.params["ls"]), p=float(f.pvalues["ls"]), lo=float(f.conf_int().loc["ls", 0]), hi=float(f.conf_int().loc["ls", 1]))
f = smf.ols("margin ~ ls + C(year)", w).fit(cov_type="HC1")
out["ols_year_fe"] = dict(coef=float(f.params["ls"]), p=float(f.pvalues["ls"]), lo=float(f.conf_int().loc["ls", 0]), hi=float(f.conf_int().loc["ls", 1]))
s = w[(w.spend_for + w.spend_against) > 0].copy(); s["yes_more"] = s.for_share > 0.5
tab = pd.crosstab(s.yes_more, s.passed)
out["side"] = dict(n=int(len(s)), yes_outspent_n=int(s.yes_more.sum()), yes_outspent_pass=float(s[s.yes_more].passed.mean()),
                   other_n=int((~s.yes_more).sum()), other_pass=float(s[~s.yes_more].passed.mean()), fisher_p=float(fisher_exact(tab)[1]))
top = w.sort_values("spend", ascending=False).head(8)[["year", "measure", "spend", "yes_pct", "passed"]]
out["coverage"] = json.load(open("data/spending_coverage.json"))
out["top"] = json.loads(top.to_json(orient="records"))
json.dump(out, open("results/spending.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "top"}, indent=1))
