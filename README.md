# Yes, No, Maybe So

Do yeses or nos win more on US statewide ballot measures, 1976–2024? Does wording, topic, or who put the measure on the ballot change the odds? How do the answers line up with each state's history?

**Report:** https://kuod.github.io/yes-no-maybeso/

**Headline results** (2,465 measures, 15 states + DC):

- 57% of measures passed overall, but citizen initiatives passed only 46% vs 62% for legislative referrals.
- Wording that asks voters to *repeal, eliminate or abolish* something cuts the odds of passing by roughly 60%. Most other wording features show no reliable effect.
- State track record is a strong predictor (Hawaii 83% pass, South Dakota 40%).
- Partisan climate mostly does not move the average yes/no: presidential lean, a state becoming more Democratic or Republican, and legislative control show no reliable effect once the state is held fixed. Democratic-governor years pass slightly more often (suggestive, not significant).

**Caveat:** measure-level data come from Wikipedia lists for 16 jurisdictions, not all 50 states. Initiative counts for every initiative state come from the Initiative & Referendum Institute. See the report's "Limits" section and `CLAUDE.md`.

## Reproduce

```
pip install -r requirements.txt
python3 -I scripts/build_dataset.py
python3 -I scripts/analyze.py
python3 -I scripts/build_presidential.py
python3 -I scripts/build_politics.py
python3 -I scripts/analyze_politics.py
python3 -I scripts/build_site.py
```

Data: Wikipedia (CC BY-SA), IRI / Matsusaka (USC), MIT Election Data and Science Lab, tonmcg county presidential results. Governor/legislature tables were extracted by subagents (see `CLAUDE.md`).
