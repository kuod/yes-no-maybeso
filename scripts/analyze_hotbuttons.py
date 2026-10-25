"""Do high-engagement ('hot-button') measures lean yes or no? -> results/hotbuttons.json. Run from repo root after build_votes.py."""
import json, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
warnings.filterwarnings("ignore")

v = pd.read_csv("data/measures_votes.csv")
v["sy"] = v.state + v.year.astype(str)
v["decade"] = v.year // 10 * 10
v["pi"] = v.passed.astype(int)
v["against"] = (v.margin < 0).astype(int)
out = {"n": int(len(v)), "states": int(v.state.nunique())}

def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h

def summ(g):
    n = len(g); lo, hi = wilson(int(g.passed.sum()), n)
    se = g.margin.std() / np.sqrt(n) if n > 1 else np.nan
    return pd.Series(dict(n=n, mean_margin=g.margin.mean(), margin_lo=g.margin.mean() - 1.96 * se, margin_hi=g.margin.mean() + 1.96 * se,
                          median_margin=g.margin.median(), share_against=(g.margin < 0).mean(),
                          pass_rate=g.passed.mean(), pass_lo=lo, pass_hi=hi, mean_vpc=g.vpc.mean()))

# 1. raw votes per capita is mostly election type
out["vpc_by_pres_year"] = v.groupby("pres_year").vpc.agg(["size", "median"]).round(3).reset_index().to_dict("records")
out["top_decile_vpc_share_pres_year"] = float(v[v.vpc >= v.vpc.quantile(.9)].pres_year.mean())
out["share_pres_year"] = float(v.pres_year.mean())

# 2. slant by raw votes-per-capita quintile
v["vpc_q"] = pd.qcut(v.vpc, 5, labels=["Q1 (fewest)", "Q2", "Q3", "Q4", "Q5 (most)"])
out["by_vpc_quintile"] = v.groupby("vpc_q", observed=True).apply(summ).reset_index().round(4).to_dict("records")
rho, p = stats.spearmanr(v.vpc, v.margin); out["spearman_vpc_margin"] = dict(rho=float(rho), p=float(p))

# 3. relative engagement: only ballots with >=5 measures (otherwise 'most-voted measure that year' is meaningless)
r = v[v.n_on_ballot >= 5].copy()
r["rel_q"] = pd.qcut(r.rel_engage, 5, labels=["Q1 (least)", "Q2", "Q3", "Q4", "Q5 (most)"])
out["n_relative"] = int(len(r)); out["n_ballots_relative"] = int(r.sy.nunique())
out["by_rel_quintile"] = r.groupby("rel_q", observed=True).apply(summ).reset_index().round(4).to_dict("records")
rho, p = stats.spearmanr(r.rel_engage, r.margin); out["spearman_rel_margin"] = dict(rho=float(rho), p=float(p))
r["hot"] = r.rel_engage >= r.rel_engage.quantile(.9)
out["hot_threshold"] = float(r.rel_engage.quantile(.9))
out["hot_vs_rest"] = r.groupby("hot").apply(summ).reset_index().round(4).to_dict("records")
a, b = r[r.hot], r[~r.hot]
out["hot_pass_test_p"] = float(stats.chi2_contingency([[a.passed.sum(), (~a.passed).sum()], [b.passed.sum(), (~b.passed).sum()]])[1])
out["hot_margin_test_p"] = float(stats.mannwhitneyu(a.margin, b.margin).pvalue)


def ols(f, x, cl, term=None):
    m = smf.ols(f, x).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(x[cl])[0]})
    t = term or ("rel_z" if "rel_z" in f else "vpc_z")           # always pick the engagement term by NAME
    return dict(term=t, coef=float(m.params[t]), se=float(m.bse[t]), p=float(m.pvalues[t]), n=int(m.nobs), clusters=int(x[cl].nunique()))

# 3b. engagement BEYOND ballot position: residual of rel_engage after removing the roll-off trend with position on the ballot
out["rolloff_slope_per_full_ballot"] = float(np.polyfit(r.pos, r.rel_engage, 1)[0]); out["rolloff_r2"] = float(r[["pos", "rel_engage"]].corr().iloc[0, 1] ** 2)
out["corr_rel_pos_spearman"] = float(r[["rel_engage", "pos"]].corr(method="spearman").iloc[0, 1])
r["excess_z"] = (r.excess - r.excess.mean()) / r.excess.std()
r["excess_q"] = pd.qcut(r.excess, 5, labels=["Q1 (least)", "Q2", "Q3", "Q4", "Q5 (most)"])
out["by_excess_quintile"] = r.groupby("excess_q", observed=True).apply(summ).reset_index().round(4).to_dict("records")
r["hot_x"] = r.excess >= r.excess.quantile(.9)
out["hot_x_vs_rest"] = r.groupby("hot_x").apply(summ).reset_index().round(4).to_dict("records")
a, b = r[r.hot_x], r[~r.hot_x]
out["hot_x_pass_test_p"] = float(stats.chi2_contingency([[a.passed.sum(), (~a.passed).sum()], [b.passed.sum(), (~b.passed).sum()]])[1])
out["hot_x_margin_test_p"] = float(stats.mannwhitneyu(a.margin, b.margin).pvalue)
out["m_margin_excess_ballot_fe"] = ols("margin ~ excess_z + C(sy)", r, "state", "excess_z")
out["m_margin_excess_ballot_fe_topic"] = ols("margin ~ excess_z + C(domain) + C(sy)", r, "state", "excess_z")
r["abs_margin"] = r.margin.abs()
out["m_absmargin_excess_ballot_fe"] = ols("abs_margin ~ excess_z + C(sy)", r, "state", "excess_z")
mlx = smf.logit("pi ~ excess_z + C(sy)", r[r.groupby("sy").pi.transform(lambda s: s.nunique() > 1)]).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(r[r.groupby("sy").pi.transform(lambda s: s.nunique() > 1)].state)[0]})
out["m_pass_excess_ballot_fe"] = dict(odds=float(np.exp(mlx.params["excess_z"])), p=float(mlx.pvalues["excess_z"]), n=int(mlx.nobs))
out["by_domain_hot_x"] = r[r.hot_x].groupby("domain").apply(summ).reset_index().round(3).to_dict("records")
out["hot_x_topic_share"] = r[r.hot_x].topic.value_counts(normalize=True).round(3).to_dict()
out["top_excess"] = r.sort_values("excess", ascending=False).head(25)[["state", "year", "measure", "description", "topic", "mtype", "vpc", "rel_engage", "margin", "passed"]].round(3).to_dict("records")

# 4. models
v["vpc_z"] = (v.vpc - v.vpc.mean()) / v.vpc.std()
out["m_margin_vpc_state_decade"] = ols("margin ~ vpc_z + C(state) + C(decade)", v, "sy")
out["m_margin_vpc_state_year"] = ols("margin ~ vpc_z + C(sy)", v, "state")        # within the same ballot: raw vpc varies only with the measure
r["rel_z"] = (r.rel_engage - r.rel_engage.mean()) / r.rel_engage.std()
out["m_margin_rel_ballot_fe"] = ols("margin ~ rel_z + C(sy)", r, "state")
out["m_margin_rel_ballot_fe_sycl"] = ols("margin ~ rel_z + C(sy)", r, "sy")
# logit for passing with ballot FE, ballots with variation only
rb = r[r.groupby("sy").pi.transform(lambda s: s.nunique() > 1)]
ml = smf.logit("pi ~ rel_z + C(sy)", rb).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(rb.state)[0]})
out["m_pass_rel_ballot_fe"] = dict(odds=float(np.exp(ml.params["rel_z"])), p=float(ml.pvalues["rel_z"]), n=int(ml.nobs))
# with topic control
out["m_margin_rel_ballot_fe_topic"] = ols("margin ~ rel_z + C(domain) + C(sy)", r, "state")
# closeness: contested measures should be narrower. |margin| vs engagement (same ballot)
r["abs_margin"] = r.margin.abs(); v["abs_margin"] = v.margin.abs()
out["m_absmargin_rel_ballot_fe"] = ols("abs_margin ~ rel_z + C(sy)", r, "state")
out["m_absmargin_vpc_ballot_fe"] = ols("abs_margin ~ vpc_z + C(sy)", v, "state")
# is the slant just ballot position / roll-off? control for measure order within the ballot where the label is numeric
out["m_margin_rel_ballot_fe_order"] = ols("margin ~ rel_z + pos + C(sy)", r, "state")

# 5. which topics are hot buttons, and how do they slant?
t = r.groupby("domain").agg(n=("rel_engage", "size"), mean_rel=("rel_engage", "mean"), mean_margin=("margin", "mean"), share_against=("against", "mean"), pass_rate=("pi", "mean")).round(3).reset_index().sort_values("mean_rel", ascending=False)
out["by_domain_relative"] = t.to_dict("records")
tt = r.groupby("topic").agg(n=("rel_engage", "size"), mean_rel=("rel_engage", "mean"), mean_margin=("margin", "mean"), pass_rate=("pi", "mean")).round(3).reset_index().sort_values("mean_rel", ascending=False)
out["by_topic_relative"] = tt.to_dict("records")
out["hot_topic_mix"] = (r[r.hot].topic.value_counts(normalize=True).round(3)).to_dict()
out["all_topic_mix"] = (r.topic.value_counts(normalize=True).round(3)).to_dict()
out["hot_by_domain"] = r[r.hot].groupby("domain").apply(summ).reset_index().round(3).to_dict("records")

# 6. lists
cols = ["state", "year", "measure", "description", "topic", "mtype", "vpc", "rel_engage", "margin", "passed"]
out["top_vpc"] = v.sort_values("vpc", ascending=False).head(25)[cols].round(3).to_dict("records")
out["top_rel"] = r.sort_values("rel_engage", ascending=False).drop_duplicates("sy").head(0)[cols].to_dict("records")
out["top_hot_relative"] = r[r.n_on_ballot >= 8].sort_values("rel_engage", ascending=False).head(25)[cols].round(3).to_dict("records")
json.dump(out, open("results/hotbuttons.json", "w"), indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, (np.integer, np.bool_)) else str(o))

pd.set_option("display.width", 220)
print("pres-year share of top-decile vpc: %.3f (overall %.3f)" % (out["top_decile_vpc_share_pres_year"], out["share_pres_year"]))
print("## by raw vpc quintile"); print(pd.DataFrame(out["by_vpc_quintile"]).round(3).to_string(index=False)); print("spearman", out["spearman_vpc_margin"])
print("## by relative engagement quintile (ballots with >=5 measures: n=%d, ballots=%d)" % (out["n_relative"], out["n_ballots_relative"])); print(pd.DataFrame(out["by_rel_quintile"]).round(3).to_string(index=False)); print("spearman", out["spearman_rel_margin"])
print("## hot (top decile rel) vs rest"); print(pd.DataFrame(out["hot_vs_rest"]).round(3).to_string(index=False)); print("pass p", out["hot_pass_test_p"], "margin p", out["hot_margin_test_p"])
for k in ["m_absmargin_rel_ballot_fe", "m_absmargin_vpc_ballot_fe", "m_margin_rel_ballot_fe_order", "m_margin_vpc_state_decade", "m_margin_vpc_state_year", "m_margin_rel_ballot_fe", "m_margin_rel_ballot_fe_sycl", "m_margin_rel_ballot_fe_topic", "m_pass_rel_ballot_fe"]: print(k, {a: round(b, 4) if isinstance(b, float) else b for a, b in out[k].items()})
print("## by EXCESS (position-adjusted) engagement quintile; roll-off slope %.3f per full ballot, R2=%.2f" % (out["rolloff_slope_per_full_ballot"], out["rolloff_r2"])); print(pd.DataFrame(out["by_excess_quintile"]).round(3).to_string(index=False))
print("hot_x vs rest"); print(pd.DataFrame(out["hot_x_vs_rest"]).round(3).to_string(index=False)); print("pass p %.3f margin p %.3f" % (out["hot_x_pass_test_p"], out["hot_x_margin_test_p"]))
for k in ["m_margin_excess_ballot_fe", "m_margin_excess_ballot_fe_topic", "m_absmargin_excess_ballot_fe", "m_pass_excess_ballot_fe"]: print(k, {a: round(b, 4) if isinstance(b, float) else b for a, b in out[k].items()})
print("hot_x by domain"); print(pd.DataFrame(out["by_domain_hot_x"]).to_string(index=False))
print("## domain (relative)"); print(pd.DataFrame(out["by_domain_relative"]).to_string(index=False))
print("## topic (relative)"); print(pd.DataFrame(out["by_topic_relative"]).to_string(index=False))
