"""Vote metrics per measure -> data/measures_votes.csv (only measures with yes/no counts; California has none yet).

votes_cast   = yes_votes + no_votes (blank/undervotes are not in the source)
vpc          = votes_cast / state population in the measure's year ("voters per capita")
margin       = 100 * (yes - no) / (yes + no); positive = in favor
rel_engage   = votes_cast / max votes_cast of any measure on that state-year's ballots (1.0 = the most-voted measure that year)
"""
import numpy as np, pandas as pd

d = pd.read_csv("data/measures.csv")
pop = pd.read_csv("data/population.csv")[["state", "year", "population"]]
d = d.merge(pop, on=["state", "year"], how="left")
v = d.dropna(subset=["yes_votes", "no_votes"]).copy()
v["votes_cast"] = v.yes_votes + v.no_votes
# Validate counts against the stated yes % (Hawaii excepted: it counts blank ballots as "no", so its % is of all ballots).
v["implied_yes"] = 100 * v.yes_votes / v.votes_cast
mismatch = (v.implied_yes - v.yes_pct).abs() > 0.6
implausible = (v.yes_votes < 1000) | (v.no_votes < 1000) | (v.votes_cast / v.population > 0.8) | (v.votes_cast / v.population < 0.05)  # <5% of residents: digits lost in the source
bad = ((mismatch & (v.state != "Hawaii")) | implausible).fillna(False)
v[bad][["state", "year", "measure", "yes_votes", "no_votes", "yes_pct"]].to_csv("data/raw/excluded_vote_counts.csv", index=False)
print("excluded for inconsistent/implausible counts:", int(bad.sum()), v[bad].groupby("state").size().to_dict())
v = v[~bad].copy()
v["blank_counts_as_no"] = v.state == "Hawaii"
v["vpc"] = v.votes_cast / v.population
v["margin"] = 100 * (v.yes_votes - v.no_votes) / v.votes_cast
v["rel_engage"] = v.votes_cast / v.groupby(["state", "year"]).votes_cast.transform("max")
v["n_on_ballot"] = v.groupby(["state", "year"]).votes_cast.transform("size")
v["pres_year"] = v.year % 4 == 0
# ballot position 0..1 within the state-year, from the source list order (NOT from any sorted file)
v["pos"] = v.groupby(["state", "year"]).src_order.rank(method="first").sub(1) / (v.n_on_ballot - 1).clip(lower=1)

# engagement beyond ballot position: residual of rel_engage on position, ballots with >=5 measures
m5 = v.n_on_ballot >= 5
b1, b0 = np.polyfit(v.loc[m5, "pos"], v.loc[m5, "rel_engage"], 1)
v["excess"] = np.where(m5, v.rel_engage - (b0 + b1 * v.pos), np.nan)
print("position slope of relative engagement: %.3f per full ballot" % b1)
v["vpc_rank"] = v.vpc.rank(ascending=False, method="first").astype(int)
keep = ["state", "year", "election", "pres_year", "measure", "description", "mtype", "topic", "domain", "passed", "yes_votes", "no_votes", "votes_cast",
        "population", "vpc", "margin", "yes_pct", "rel_engage", "n_on_ballot", "pos", "excess", "vpc_rank", "blank_counts_as_no"]
v[keep].sort_values("vpc", ascending=False).to_csv("data/measures_votes.csv", index=False)
print(len(v), "measures with counts from", v.state.nunique(), "jurisdictions;", int(d.population.isna().sum()), "rows lacking population")
print(v.groupby("state").size().to_dict())
print("vpc: median %.3f, p90 %.3f, max %.3f" % (v.vpc.median(), v.vpc.quantile(.9), v.vpc.max()))
print("measures where margin>0 but not passed:", int(((v.margin > 0) & ~v.passed).sum()), "| margin<0 but passed:", int(((v.margin < 0) & v.passed).sum()))
