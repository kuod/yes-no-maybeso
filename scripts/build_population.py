"""State resident population by year, 1976-2024 -> data/population.csv.

1980-89: Census intercensal estimates (st8090ts.txt; Apr-1980 census count used for 1980).
1990-99: Census estimates ST-99-03 (pre-2000-census base, so a small step at 2000).
2000-09: intercensal estimates (st-est00int-alldata.csv).  2010-19: vintage 2019.  2020-24: vintage 2024.
1976-79: intercensal estimates (st7080ts.txt; July 1 estimates for 1976-79).
"""
import re
import numpy as np, pandas as pd

P = "data/raw/population"
ABBR = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
        "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
        "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
        "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
STATES = set(ABBR.values())
rows = []

# 1980s: two blocks; columns [4/80cen, 7/81..7/84] and [7/85..7/89, 4/90cen]
block = 0; cols = []
for line in open(f"{P}/st8090ts.txt"):
    if re.search(r"4/80cen", line): block, cols = 1, [1980, 1981, 1982, 1983, 1984]
    elif re.search(r"7/85", line): block, cols = 2, [1985, 1986, 1987, 1988, 1989, 1990]
    m = re.match(r"^([A-Z]{2})\s+([\d ]+)$", line.rstrip())
    if m and m.group(1) in ABBR and block:
        for y, v in zip(cols, m.group(2).split()):
            if not (block == 2 and y == 1990):          # 1990 comes from the 1990s file
                rows.append((ABBR[m.group(1)], y, int(v)))

# 1990s: block 1 = 1999..1994, block 2 = 1993..1990 (+ 4/1/90 census, ignored)
block = None
for line in open(f"{P}/st-99-03.txt"):
    if "7/1/99" in line: block = [1999, 1998, 1997, 1996, 1995, 1994]
    elif "7/1/93" in line: block = [1993, 1992, 1991, 1990]
    m = re.match(r"^\s+\d\s+([A-Za-z .]+?)\s{2,}([\d ]+)$", line.rstrip())
    if m and block and m.group(1).strip() in STATES:
        for y, v in zip(block, m.group(2).split()):
            rows.append((m.group(1).strip(), y, int(v)))

def wide(path, rng, namecol="NAME", pre="POPESTIMATE"):
    d = pd.read_csv(path, encoding="latin-1")
    d = d[d[namecol].isin(STATES)]
    for _, r in d.iterrows():
        for y in rng:
            if f"{pre}{y}" in d.columns:
                rows.append((r[namecol], y, int(r[f"{pre}{y}"])))
wide(f"{P}/st-est00int-alldata.csv", range(2000, 2010))
wide(f"{P}/nst-est2019-alldata.csv", range(2010, 2020))
wide(f"{P}/NST-EST2024-ALLDATA.csv", range(2020, 2025))

pop = pd.DataFrame(rows, columns=["state", "year", "population"]).drop_duplicates(["state", "year"]).sort_values(["state", "year"])
# 1970s: second block lists 7/76..7/79 and 4/1/80
block = None
for line in open(f"{P}/st7080ts.txt"):
    if "7/76" in line: block = [1976, 1977, 1978, 1979]
    m = re.match(r"^\s*\d+\s+([A-Z]{2})\s+([\d ]+)$", line.rstrip())
    if m and block and m.group(1) in ABBR:
        for y, v in zip(block, m.group(2).split()):
            rows.append((ABBR[m.group(1)], y, int(v)))
pop = pd.DataFrame(rows, columns=["state", "year", "population"]).drop_duplicates(["state", "year"]).sort_values(["state", "year"])
pop.to_csv("data/population.csv", index=False)
cnt = pop.groupby("state").size()
print("states:", pop.state.nunique(), "| years per state min/max:", cnt.min(), cnt.max())
