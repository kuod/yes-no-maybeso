"""State two-party presidential results 1976-2024 -> data/presidential.csv.

1976-2016: MIT Election Lab 'U.S. President 1976-2020' release v20171015 (state level).
2020, 2024: county-level files (tonmcg/US_County_Level_Election_Results) summed to state.
dem_margin = (D - R) / (D + R) in percentage points; positive = Democratic.
"""
import pandas as pd

P = "data/raw/politics"
m = pd.read_csv(f"{P}/pres_1976_2016.tsv", sep="\t")
m = m[m.office == "US President"]
m["party"] = m.party.str.lower()
w = m[m.party.isin(["democrat", "republican"]) & (m.writein.astype(str).str.upper() != "TRUE")]
w = w.groupby(["year", "state", "party"]).candidatevotes.sum().unstack().reset_index()
w = w.rename(columns={"democrat": "dem", "republican": "rep"})
rows = [w[["year", "state", "dem", "rep"]]]
for y in (2020, 2024):
    c = pd.read_csv(f"{P}/{y}_US_County_Level_Presidential_Results.csv")
    s = c.groupby("state_name")[["votes_dem", "votes_gop"]].sum().reset_index()
    s.columns = ["state", "dem", "rep"]; s["year"] = y
    rows.append(s[["year", "state", "dem", "rep"]])
d = pd.concat(rows, ignore_index=True)
d["state"] = d.state.str.title().str.replace("Of", "of")
d["dem_share2"] = 100 * d.dem / (d.dem + d.rep)
d["dem_margin"] = 100 * (d.dem - d.rep) / (d.dem + d.rep)
d.sort_values(["state", "year"]).to_csv("data/presidential.csv", index=False)
print(d.groupby("year").size().to_string())
