# CLAUDE.md

Project: **yes-no-maybeso** — do yeses or nos win more on US statewide ballot measures (1976–2024), and do wording, topic and origin change the odds? The published report is a GitHub Pages site served from `docs/`.

## Pipeline (run from repo root, in order)

```
python3 -I scripts/build_dataset.py   # data/raw/** -> data/measures.csv, data/state_year.csv
python3 -I scripts/analyze.py         # data/*.csv -> results/*.csv, results/summary.json
python3 -I scripts/build_presidential.py  # data/raw/politics/pres_* -> data/presidential.csv
python3 -I scripts/build_politics.py  # + gov_leg_*.csv -> data/state_politics.csv, data/measures_politics.csv
python3 -I scripts/analyze_politics.py    # -> results/politics.json, results/politics_*.csv
python3 -I scripts/build_population.py    # Census files in data/raw/population -> data/population.csv
python3 -I scripts/build_votes.py     # votes per capita, margin, engagement -> data/measures_votes.csv
python3 -I scripts/analyze_hotbuttons.py  # -> results/hotbuttons.json
python3 -I scripts/build_explorer.py  # -> docs/explorer.html (interactive, data embedded)
python3 -I scripts/build_spending.py   # exploratory WA spending join -> data/measures_spending.csv
python3 -I scripts/analyze_spending.py   # -> results/spending.json
python3 -I scripts/robustness_hotbuttons.py  # sensitivity of the hot-button estimate -> results/robustness_hotbuttons.json
python3 -I scripts/robustness.py      # adversarial checks -> results/robustness.json (slow: bootstrap)
python3 -I scripts/build_site.py      # results/*.json -> docs/index.html
```

`docs/index.html` is generated. Never hand-edit it; change `scripts/build_site.py` and rebuild. Prose numbers are interpolated from `results/summary.json`; a few comparisons (CA/OR/WA vs IRI) are hard-coded in the text and must be rechecked if the data changes.

Dependencies: `pip install -r requirements.txt`.

## Data

- `data/raw/wiki/*.html` — Wikipedia state list pages fetched with `scripts/wiki.py` (MediaWiki API). Source of measure-level data for 15 states + DC. Re-fetch to refresh; the parser keys on `wikitable` tables with an `h3` year heading (California 1970–2009 uses bulleted lists).
- `data/raw/iri_state_year.xls` — IRI initiative counts and approvals by state and year (all initiative states).
- `data/measures.csv` — one row per measure: state, year, description, origin (`mtype`: initiative / legislative / unknown), topic, domain, passed, yes_pct, wording features.
- Ballotpedia blocks automated access (403). Do not scrape around it. The same applies to the California Secretary of State's CDN (`elections.cdn.sos.ca.gov` returns 403 to plain requests): **do not spoof a browser User-Agent or otherwise get past a bot block**; the auto-mode classifier denied exactly that. Ask the user first. As a result **California has no vote counts** (`data/raw/ca_votes/todo.csv` is the ready-made input list if access is ever authorised or the user supplies the files; each row can be validated because yes>no must equal `passed`). If full measure-level data for all 50 states is supplied (Ballotpedia export or Matsusaka's IRI database), add a loader in `build_dataset.py` and keep `measures.csv`'s schema.

- `data/raw/politics/pres_1976_2016.tsv` — MIT Election Lab state presidential returns (Harvard Dataverse, doi:10.7910/DVN/42MVDX, v20171015). 2020 and 2024 come from `tonmcg/US_County_Level_Election_Results` county files summed to state.
- `data/raw/politics/gov_leg_{A,B,C,D}.csv` — governor party and legislative seat counts per state-year (15 states, 1976–2024) from Wikipedia "Political party strength in <State>". **Extracted by four subagents, not by a script**, so the pipeline cannot regenerate them. They passed row-count, chamber-size and 17 known-state-year checks, but are not fully audited. Ties are coded `tie` and counted as a split legislature. DC is excluded from all partisan analysis.

## Method conventions

- Window is 1976–2024 completed elections; rows with undecided outcomes are dropped.
- `passed` follows the source's result. It matches `yes_pct > 50` in 98.3% of rows; mismatches are legitimate supermajority rules (FL 60%, WY). Don't "fix" them.
- Origin (`mtype`) is unknown for ~59% of rows. Anything comparing initiatives with referrals must say it uses identified cases only.
- Wording models are logits with state and decade fixed effects, errors clustered by state-election. Model A = all rows; Model B = known-origin rows with an origin control. Report both, and report null results as nulls.
- Topic labels are keyword rules (`TOPICS` in `build_dataset.py`), roughly 75–80% accurate on a 40-row hand audit. Order of rules matters (first match wins); keep `\b` word boundaries (an earlier `rent\b` matched "current").

## Vote-count metrics (hot-button analysis)

- `votes_cast` = yes + no; `vpc` = votes_cast / state population that year (Census files, `scripts/build_population.py`); `margin` = 100·(yes−no)/(yes+no); `rel_engage` = votes / max votes on that state-year's ballot (ballots with ≥5 measures); `excess` = rel_engage minus its trend with ballot position (`pos`, from the source list order `src_order`).
- Validation in `build_votes.py`: counts must agree with the stated yes % (Hawaii exempt: blanks count as "no", so its % is of all ballots), and votes must be 5–80% of residents. 26 rows are excluded and logged in `data/raw/excluded_vote_counts.csv`.
- A "ballot" here is a state-year, which can mix a primary/special with the general election (~6% of ballots show >2× vote spread). Hot-button estimates are negative in every specification (−1.7 to −3.5 margin pts per SD) but only some are significant, and power is low (MDE ≈4.6 pts/SD). Say "consistent, not robust"; do not say "no slant".
- Raw votes per capita mostly measures election type (≈96% of top-decile measures are presidential-year). Always show the relative versions alongside it.
- Never derive position or order from a file that has been re-sorted. Ballot position must come from `src_order` (parse order).

## Campaign spending (exploratory; short note in report section 6)

- `scripts/build_spending.py` joins Washington PDC open data (`data.wa.gov` dataset `3h9x-7bvm`, committee_category 'Statewide Ballot Measure', 2007+) to WA initiatives/referenda. Only ~half of committees name a measure in `ballot_number` or their name; the unattributed ones hold more money than the attributed ones, so spend is a **lower bound** and the for/against split is unreliable. Transaction-level `ballot_number` tags exist only from 2019. Do not hand-map committees to measures from memory.
- Exploratory result (n=37): more spending goes with lower margins (Spearman -0.30, p≈0.07; not significant with year fixed effects, p≈0.36). Reported only as a labelled exploratory note, never as a finding. A real answer needs a source keyed by measure (Ballotpedia / National Institute on Money in Politics) for many states.

## Partisan-context definitions

- `lean` = Democratic two-party presidential margin (pts) at the last presidential election strictly before the measure's year. `shift4` = lean minus the margin one race earlier (positive = state moved toward Democrats); `shift8` = two races earlier.
- Models use state and decade fixed effects, so lean/shift are identified within state over time. The raw cross-state pattern (Republican-leaning states pass more) is a between-state difference and vanishes with fixed effects; don't report it as an effect of partisanship.
- Yes/no is not ideologically signed: averaged over all measures the partisan effects can cancel. The report says so; testing direction needs per-measure ideological coding (not built yet).
- Partisan results are null. Governor party tilts slightly Democratic-higher (pass odds ratio ≈1.14, yes share +1.5 pts, wild bootstrap p≈0.21), none significant. An earlier +2.6 pts / p≈0.006 result was an artifact of Arizona 2010–2024 being dropped by a parser bug; do not resurrect it. With ~15 clusters never quote ordinary cluster-robust p-values for state-level regressors; use the bootstrap in `robustness.py`.

## Lessons from the adversarial pass

- Wording regexes must use whole-word boundaries and be checked for what they actually match (`amend` once made "expansive" a proxy for "amendment"). Audit token counts after any regex change.
- Origin comparisons need a within-state version; Oregon dominates the identified referrals.
- Wikipedia lists omit measures (≥113 initiatives vs IRI). Don't present pooled counts as complete.

- A silent parser skip changed a conclusion (Arizona). After any parser change, count rows per state-year against an independent source (IRI counts) and list skipped tables.
- Extract regression coefficients by name, not by position (`params.iloc[1]` once returned a dummy variable).
- Add an automated check wherever two fields should agree (counts vs stated %, passed vs yes>no).

## Honesty rules for this project

- The report must state that wording results come from the 16-jurisdiction subset, not all 50 states.
- Wikipedia text mixes official ballot titles and editor summaries, so wording is confounded with who wrote it. Keep that caveat next to any wording claim.
- Association, not causation. Don't write "rewording would change outcomes".
- Flag coverage gaps whenever pooled numbers are shown (AZ 1990–2008, MO/SD from 2000, OK from 2004, DC 1979 only).

## Style

Python 3.13, pandas/statsmodels/scipy, no notebooks. Scripts are plain files run with `python3 -I` from the repo root. Charts are hand-built inline SVG with CSS custom properties for light/dark themes (palette from the dataviz skill: slot 1 purple #7a4fd0 light / #9470e0 dark, slot 2 orange; deliberately no red/blue, which reads as partisan), always with a table view.

## Open scope

1. Full 50-state measure-level data.
2. Official ballot-title text for every measure.
3. Better topic classifier (labelled sample plus a model, or manual coding).
4. Ideological direction coding of each measure (conservative / liberal / neutral) to test climate-by-direction effects; other state covariates (signature requirements, turnout, per-measure campaign spending).
