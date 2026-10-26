# Yes, No, Maybe So

Do yeses or nos win more on US statewide ballot measures, 1976–2024? Does wording, topic, or who put the measure on the ballot change the odds? How do the answers line up with each state's history?

**Report:** https://kuod.github.io/yes-no-maybeso/

**Headline results** (2,522 measures, 15 states + DC):

- 57% of measures passed overall, but citizen initiatives passed only 46% vs 62% for legislative referrals.
- Wording that asks voters to *repeal, eliminate or abolish* something cuts the odds of passing by roughly 60%. Most other wording features show no reliable effect.
- State track record is a strong predictor (Hawaii 83% pass, South Dakota 40%).
- Partisan climate does not reliably move the average yes/no: presidential lean, a state becoming more Democratic or Republican, governor party and legislative control all show no significant effect once the state is held fixed.
- Hot-button issues (the most voters per capita) lean slightly toward "no" in every specification tried (about −2 to −3 margin points per SD of engagement), but only some variants are significant and the test is underpowered. Explore every measure in the [interactive Hot-Button Explorer](https://kuod.github.io/yes-no-maybeso/explorer.html). California is missing from that view (no vote counts).

**Caveat:** measure-level data come from Wikipedia lists for 16 jurisdictions, not all 50 states. Initiative counts for every initiative state come from the Initiative & Referendum Institute. See the report's "Limits" section and `CLAUDE.md`.

## Next steps

Roughly in order of how much they would improve the findings:

1. **Full 50-state measure-level data.** Everything about wording, topic and origin rests on 15 states plus DC. Ballotpedia's export or Matsusaka's IRI database would fix this (both block scraping; needs a supplied file).
2. **California vote counts.** California holds many of the best-known hot-button measures (Props 13, 187, 209, 8, 64) but has no vote counts. `data/raw/ca_votes/todo.csv` lists what is needed; the Secretary of State's CDN blocks automated requests, so the files must be supplied or access authorised.
3. **Official ballot-title text.** Wikipedia mixes official titles with editors' summaries, so wording is confounded with who wrote it.
4. **Ideological direction coding.** Label each measure conservative / liberal / neutral to test whether partisan climate affects *which* measures pass. Averaged over all measures, the partisan effects can cancel.
5. **Better topic classifier.** Keyword rules are roughly 75-80% accurate; a hand-labelled sample plus a model would help.
6. **Election-type flags.** Mark primary, special and general elections so hot-button "ballots" don't mix electorates (about 6% do). This should sharpen the engagement estimate, which is currently consistent but underpowered.
7. **More covariates.** Signature requirements, turnout, and per-measure campaign spending.

## Reproduce

```
pip install -r requirements.txt
python3 -I scripts/build_dataset.py
python3 -I scripts/analyze.py
python3 -I scripts/build_presidential.py
python3 -I scripts/build_politics.py
python3 -I scripts/analyze_politics.py
python3 -I scripts/build_population.py
python3 -I scripts/build_votes.py
python3 -I scripts/analyze_hotbuttons.py
python3 -I scripts/build_explorer.py
python3 -I scripts/robustness.py   # slow
python3 -I scripts/build_site.py
```

Data: Wikipedia (CC BY-SA), IRI / Matsusaka (USC), MIT Election Data and Science Lab, tonmcg county presidential results. Governor/legislature tables were extracted by subagents (see `CLAUDE.md`).
