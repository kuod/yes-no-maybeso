"""Washington statewide ballot-measure campaign spending (WA Public Disclosure Commission open data)
joined to measures_votes.csv.  Output: data/measures_spending.csv

Source: https://data.wa.gov/resource/3h9x-7bvm (Campaign Finance Summary), committee_category = 'Statewide Ballot Measure',
saved to data/raw/wa_pdc/statewide_ballot_committees.json.  Spending is attributed to a measure by ballot_number when present, else by a
number found in the committee name (I-960, "Initiative 1029", R-74...).  Committees that name no measure are dropped and counted.

Run from repo root:  python3 -I scripts/build_spending.py
"""
import re
import pandas as pd

d = pd.read_json("data/raw/wa_pdc/statewide_ballot_committees.json", dtype=False)
d["year"] = d.election_year.astype(int)
d["spend"] = pd.to_numeric(d.expenditures_amount, errors="coerce").fillna(0)
d["raised"] = pd.to_numeric(d.contributions_amount, errors="coerce").fillna(0)

AGAINST = r"\b(?:no on|vote no|against|reject|stop|oppose|opposed|no to|defeat)\b|^no\b|\bno$"


def number(r):
    if pd.notna(r.ballot_number) and re.search(r"\d+", str(r.ballot_number)):
        return int(re.search(r"\d+", str(r.ballot_number)).group())
    m = re.search(r"\b(?:I|R|INITIATIVE|REFERENDUM|REF|SJR|HJR)[\s\-#]*(\d{1,4})\b", r.filer_name.upper())
    return int(m.group(1)) if m else None


def side(r):
    if r.for_or_against in ("for", "against"):
        return r.for_or_against
    n = r.filer_name.lower()
    return "against" if re.search(AGAINST, n) else "for"


d["num"] = d.apply(number, axis=1)
d["side"] = d.apply(side, axis=1)
matched = d[d.num.notna()].copy()
print(f"committees: {len(d)}; attributed to a measure: {len(matched)}; unattributed: {len(d) - len(matched)} (spend ${d[d.num.isna()].spend.sum()/1e6:.1f}M)")

agg = matched.groupby(["year", "num"]).apply(lambda g: pd.Series(dict(
    spend=g.spend.sum(), spend_for=g[g.side == "for"].spend.sum(), spend_against=g[g.side == "against"].spend.sum(),
    committees=len(g))), include_groups=False).reset_index()

m = pd.read_csv("data/measures_votes.csv")
w = m[(m.state == "Washington") & (m.year >= 2007)].copy()
w["num"] = w.measure.str.extract(r"(?:Initiative|Referendum)(?: Measure)? (\d+)")[0].astype(float)
w["kind"] = w.measure.str.extract(r"^(Initiative|Referendum)")[0]
w = w.merge(agg, on=["year", "num"], how="left")
w["has_spend"] = w.spend.notna()
w["spend_pc"] = w.spend / (w.votes_cast / 1e0)        # dollars per vote cast
w["for_share"] = w.spend_for / (w.spend_for + w.spend_against)
w.to_csv("data/measures_spending.csv", index=False)
print(w.kind.value_counts(dropna=False).to_string())
print("initiative/referendum rows:", w.kind.notna().sum(), "with spending:", w[w.kind.notna()].has_spend.sum())
print(w[w.kind.notna()][["year", "measure", "yes_pct", "spend", "spend_for", "spend_against"]].sort_values("year").to_string())
