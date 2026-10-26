"""Adversarial checks on the hot-button results -> results/robustness_hotbuttons.json. Run from repo root after analyze_hotbuttons.py."""
import json, re, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore")

v = pd.read_csv("data/measures_votes.csv"); v["sy"] = v.state + v.year.astype(str); v["pi"] = v.passed.astype(int)
out = {}

# 1. contamination by multiple elections in one state-year (primary/special + general)
v["month_label"] = v.measure.fillna("").str.contains(r"(?i)january|february|march|april|may\b|june|july|august|september|october|special|primary")
disp = v.groupby("sy").votes_cast.agg(lambda s: s.max() / s.min())
out["ballots_total"] = int(v.sy.nunique()); out["ballots_votes_ratio_gt2"] = int((disp > 2).sum())
out["ballots_with_month_label"] = int(v[v.month_label].sy.nunique())
by_state = v.groupby("state").apply(lambda g: float((g.groupby("sy").votes_cast.agg(lambda s: s.max() / s.min()) > 2).mean())).round(3).to_dict()
out["share_ballots_ratio_gt2_by_state"] = by_state

def est(x, label, minb=5):
    r = x[x.n_on_ballot >= minb].copy()
    r["n_b"] = r.groupby("sy").votes_cast.transform("size"); r = r[r.n_b >= minb]
    r["rel"] = r.votes_cast / r.groupby("sy").votes_cast.transform("max")
    r["rel_z"] = (r.rel - r.rel.mean()) / r.rel.std()
    m = smf.ols("margin ~ rel_z + C(sy)", r).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(r.state)[0]})
    ci = m.conf_int().loc["rel_z"]
    rb = r[r.groupby("sy").pi.transform(lambda s: s.nunique() > 1)]
    ml = smf.logit("pi ~ rel_z + C(sy)", rb).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(rb.state)[0]})
    return dict(label=label, n=int(len(r)), ballots=int(r.sy.nunique()), coef=float(m.params["rel_z"]), se=float(m.bse["rel_z"]), lo=float(ci[0]), hi=float(ci[1]), p=float(m.pvalues["rel_z"]),
                pass_odds=float(np.exp(ml.params["rel_z"])), pass_p=float(ml.pvalues["rel_z"]))

rows = [est(v, "baseline (state-year ballots, >=5 measures)")]
clean = v[(v.year % 2 == 0) & ~v.month_label]
rows.append(est(clean, "even years only, drop month/special-labelled"))
tight = v[v.sy.isin(disp[disp <= 2].index)]
rows.append(est(tight, "only ballots whose vote counts are within 2x (single electorate)"))
rows.append(est(v, ">=3 measures per ballot", 3)); rows.append(est(v, ">=8 measures per ballot", 8))
rows.append(est(v[v.year >= 2000], "2000 onward"))
rows.append(est(v[v.state != "Hawaii"], "without Hawaii (blank-as-no)"))
rows.append(est(v[~v.state.isin(["Oregon"])], "without Oregon (largest state in sample)"))
# put back the rows excluded for inconsistent counts? (they have no usable counts, so only the implausibility rule is relevant)
out["sensitivity"] = rows

# 2. power: smallest slant detectable (80% power, alpha .05) from the baseline SE, in points per SD of engagement
b = rows[0]; out["mde_points_per_sd"] = float(2.8 * b["se"])
# what does one SD of relative engagement mean in measure terms?
r0 = v[v.n_on_ballot >= 5]; out["sd_rel_engage"] = float((r0.votes_cast / r0.groupby("sy").votes_cast.transform("max")).std())
json.dump(out, open("results/robustness_hotbuttons.json", "w"), indent=1)
print({k: out[k] for k in ["ballots_total", "ballots_votes_ratio_gt2", "ballots_with_month_label", "mde_points_per_sd", "sd_rel_engage"]})
print(pd.DataFrame(rows)[["label", "n", "ballots", "coef", "lo", "hi", "p", "pass_odds", "pass_p"]].round(3).to_string(index=False))
print({k: v_ for k, v_ in by_state.items() if v_ > 0.15})
