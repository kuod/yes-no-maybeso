"""Generate docs/index.html (GitHub Pages) from results/summary.json. Run from repo root."""
import json, html, math, os
import pandas as pd

S = json.load(open("results/summary.json"))
H = S["headline"]
os.makedirs("docs", exist_ok=True)

B, O = "var(--s1)", "var(--s2)"
W = 720


def esc(x):
    return html.escape(str(x))


def pct(x, d=0):
    return f"{100 * x:.{d}f}%"


def dotrange(rows, series, xmin, xmax, ref=None, log=False, fmt=lambda v: pct(v), label_w=170, row_h=26, xticks=None, xlabel=""):
    """rows: [(label, [(value, lo, hi, n_label)...] aligned with series)]; draws one SVG."""
    pad_r, top = 24, 14
    h = top + row_h * len(rows) + 40
    iw = W - label_w - pad_r
    f = (lambda v: math.log(v)) if log else (lambda v: v)
    a, b = f(xmin), f(xmax)
    X = lambda v: label_w + (f(min(max(v, xmin), xmax)) - a) / (b - a) * iw
    g = [f'<svg viewBox="0 0 {W} {h}" role="img" class="chart" aria-label="{esc(xlabel)}">']
    for t in xticks:
        x = X(t)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 4}" y2="{h - 34}" class="grid"/>')
        g.append(f'<text x="{x:.1f}" y="{h - 18}" class="tick" text-anchor="middle">{esc(fmt(t))}</text>')
    if ref is not None:
        x = X(ref)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top - 4}" y2="{h - 34}" class="ref"/>')
    g.append(f'<text x="{label_w + iw / 2:.0f}" y="{h - 3}" class="axis" text-anchor="middle">{esc(xlabel)}</text>')
    off = [0] if len(series) == 1 else [-5, 5]
    for i, (label, pts) in enumerate(rows):
        y = top + row_h * i + row_h / 2
        g.append(f'<text x="{label_w - 10}" y="{y + 4:.1f}" class="lab" text-anchor="end">{esc(label)}</text>')
        for j, p in enumerate(pts):
            if p is None:
                continue
            v, lo, hi, tip = p
            yy = y + off[j]
            g.append(f'<g class="pt"><title>{esc(tip)}</title>'
                     f'<line x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{series[j][1]}" stroke-width="2" stroke-linecap="round"/>'
                     f'<circle cx="{X(v):.1f}" cy="{yy:.1f}" r="4.5" fill="{series[j][1]}" class="dot"/>'
                     f'<rect x="{label_w}" y="{yy - row_h / 2 + 3:.1f}" width="{iw}" height="{row_h - 6}" fill="transparent"/></g>')
    g.append("</svg>")
    leg = ""
    if len(series) > 1:
        leg = '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in series) + "</div>"
    return leg + "".join(g)


def table(df, cols, label="View as table", open_=False):
    th = "".join(f"<th>{esc(c[1])}</th>" for c in cols)
    tr = "".join("<tr>" + "".join(f"<td>{esc(c[2](r[c[0]]) if len(c) > 2 else r[c[0]])}</td>" for c in cols) + "</tr>" for _, r in df.iterrows())
    return f'<details{" open" if open_ else ""}><summary>{esc(label)}</summary><div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>'


def wrow(r, name=None):
    n = int(r["n"])
    return (r["pass_rate"], r["lo"], r["hi"], f"{name or ''} {pct(r['pass_rate'], 1)} passed (95% CI {pct(r['lo'])}–{pct(r['hi'])}), n={n}".strip())


# ---------------- charts ----------------
dec = pd.DataFrame(S["by_decade"]).sort_values("decade")
dec_f = pd.DataFrame(S["by_decade_fullcov"]).set_index("decade")
rows = []
for _, r in dec.iterrows():
    rf = dec_f.loc[r.decade] if r.decade in dec_f.index else None
    rows.append((f"{int(r.decade)}s", [wrow(r, "All sample:"), wrow(rf, "Full-coverage states:") if rf is not None else None]))
c_decade = dotrange(rows, [("All 16 jurisdictions", B), ("11 full-coverage states only", O)], 0.35, 0.75, ref=0.5, xticks=[0.4, 0.5, 0.6, 0.7], xlabel="Share of measures that passed (95% CI)")
t_decade = table(dec, [("decade", "Decade", lambda v: f"{int(v)}s"), ("n", "Measures", int), ("pass_rate", "Pass rate", lambda v: pct(v, 1)), ("mean_yes_pct", "Mean yes %", lambda v: f"{v:.1f}")])

ty = pd.DataFrame(S["by_domain_type"])
order = ["social", "political process", "economic", "education", "environment", "other"]
rows = []
for dom in order:
    a = ty[(ty.domain == dom) & (ty.mtype == "initiative")]
    b = ty[(ty.domain == dom) & (ty.mtype == "legislative")]
    rows.append((dom.capitalize(), [wrow(a.iloc[0], "Citizen initiatives:") if len(a) else None, wrow(b.iloc[0], "Legislative referrals:") if len(b) else None]))
c_type = dotrange(rows, [("Citizen initiatives", B), ("Legislative referrals", O)], 0.15, 0.95, ref=0.5, xticks=[0.2, 0.4, 0.5, 0.6, 0.8], xlabel="Share passed (95% CI), origin known only")
t_type = table(ty, [("domain", "Domain"), ("mtype", "Origin"), ("n", "n", int), ("pass_rate", "Pass rate", lambda v: pct(v, 1))])

tp = pd.DataFrame(S["by_topic"]).sort_values("pass_rate")
c_topic = dotrange([(r.topic.capitalize(), [wrow(r)]) for _, r in tp.iterrows()], [("Passed", B)], 0.3, 0.95, ref=0.5, xticks=[0.4, 0.5, 0.6, 0.7, 0.8, 0.9], label_w=210, xlabel="Share passed (95% CI), all measures")
t_topic = table(tp.sort_values("pass_rate", ascending=False), [("topic", "Topic"), ("n", "n", int), ("pass_rate", "Pass rate", lambda v: pct(v, 1)), ("mean_yes_pct", "Mean yes %", lambda v: "n/a" if pd.isna(v) else f"{v:.1f}")])

st = pd.DataFrame(S["by_state"]).sort_values("pass_rate")
c_state = dotrange([(f"{r.state} ({int(r.n)})", [wrow(r)]) for _, r in st.iterrows()], [("Passed", B)], 0.2, 1.0, ref=0.5, xticks=[0.3, 0.5, 0.7, 0.9], label_w=190, xlabel="Share passed (95% CI); n in brackets")
t_state = table(st.sort_values("pass_rate", ascending=False), [("state", "State"), ("n", "n", int), ("pass_rate", "Pass rate", lambda v: pct(v, 1)), ("mean_yes_pct", "Mean yes %", lambda v: "n/a" if pd.isna(v) else f"{v:.1f}")])

cv = pd.DataFrame(S["scrape_vs_iri"])
cv = cv[cv.n >= 30].sort_values("iri_approval")
rows = []
for _, r in cv.iterrows():
    lo = max(0, r.rate - 1.96 * math.sqrt(r.rate * (1 - r.rate) / r.n))
    hi = min(1, r.rate + 1.96 * math.sqrt(r.rate * (1 - r.rate) / r.n))
    rows.append((f"{r.state} ({int(r.n)})", [(r.rate, lo, hi, f"This dataset: {pct(r.rate, 1)} of {int(r.n)} identified initiatives passed"),
                                              (r.iri_approval, r.iri_approval, r.iri_approval, f"IRI (all {int(r.initiatives)} initiatives, 1976–2024): {pct(r.iri_approval, 1)}")]))
c_iri = dotrange(rows, [("This dataset (identified initiatives, 95% CI)", B), ("IRI official count, all initiatives", O)], 0.15, 0.8, ref=None, xticks=[0.2, 0.4, 0.6, 0.8], xlabel="Initiative approval rate")
t_iri = table(cv, [("state", "State"), ("n", "n identified", int), ("rate", "This dataset", lambda v: pct(v, 1)), ("initiatives", "IRI initiatives", int), ("iri_approval", "IRI approval", lambda v: pct(v, 1))])

LABELS = {"mentions_repeal": "Says repeal / eliminate / abolish", "restrictive": "Restrictive verbs (ban, limit, cut…)", "expansive": "Expansive verbs (allow, create, provide…)",
          "mentions_tax_debt": "Mentions tax, fee, bond or debt", "mentions_increase": "Mentions increase / raise / impose", "is_amendment": "Constitutional amendment",
          "zlen": "Longer text (+1 SD of log words)", "zflesch": "Easier to read (+1 SD Flesch)"}
rowsf, tab = [], []
a = {r["term"]: r for r in S["logit_wording"]}
b = {r["term"]: r for r in S["logit_known_origin"]}
for k, lab in LABELS.items():
    ra, rb = a.get(k), b.get(k)
    tip = lambda r, nm: (r["odds"], r["lo"], r["hi"], f"{nm}: odds ratio {r['odds']:.2f} (95% CI {r['lo']:.2f}–{r['hi']:.2f}), p={r['p']:.3f}")
    rowsf.append((lab, [tip(ra, "Full sample"), tip(rb, "Known-origin sample")]))
    tab.append(dict(term=lab, a=f"{ra['odds']:.2f} ({ra['lo']:.2f}–{ra['hi']:.2f}), p={ra['p']:.3f}", b=f"{rb['odds']:.2f} ({rb['lo']:.2f}–{rb['hi']:.2f}), p={rb['p']:.3f}"))
c_forest = dotrange(rowsf, [(f"Model A: all measures (n={S['logit_n']:,})", B), (f"Model B: origin known, origin controlled (n={S['logit_known_n']:,})", O)], 0.12, 3.5, ref=1.0, log=True,
                    fmt=lambda v: f"{v:g}×", xticks=[0.25, 0.5, 1, 2], label_w=250, xlabel="Odds ratio of passing (1× = no effect; left = hurts, right = helps)")
t_forest = table(pd.DataFrame(tab), [("term", "Wording feature"), ("a", "Model A: OR (95% CI)"), ("b", "Model B: OR (95% CI)")])


# ---------------- politics charts ----------------
PJ = json.load(open("results/politics.json"))
RB = json.load(open("results/robustness.json"))
PEOPLE = {"D": "Democratic", "R": "Republican"}

def prow(r, label):
    return (label, [wrow(r)])

split_rows = []
for r in PJ["by_gov"]:
    split_rows.append(prow(r, f"Governor: {PEOPLE[r['gov_party']]}"))
for r in sorted(PJ["by_leg"], key=lambda r: {"D": 0, "R": 1, "split": 2}[r["leg_ctrl"]]):
    split_rows.append(prow(r, {"D": "Legislature: Democratic (both chambers)", "R": "Legislature: Republican (both chambers)", "split": "Legislature: split or tied"}[r["leg_ctrl"]]))
for r in sorted(PJ["by_trifecta"], key=lambda r: {"D trifecta": 0, "R trifecta": 1, "divided": 2}[r["trifecta"]]):
    split_rows.append(prow(r, {"D trifecta": "Democratic trifecta", "R trifecta": "Republican trifecta", "divided": "Divided government"}[r["trifecta"]]))
for r in PJ["by_lean_cat"]:
    split_rows.append(prow(r, "State lean: " + r["lean_cat"]))
for r in PJ["by_shift_dir"]:
    split_rows.append(prow(r, "Since last race: " + r["shift_dir"]))
c_split = dotrange(split_rows, [("Passed", B)], 0.4, 0.75, ref=0.5, xticks=[0.4, 0.5, 0.6, 0.7], label_w=250, xlabel="Share of measures that passed (95% CI)")
t_split = table(pd.DataFrame([dict(group=l, n=int(x[0][3].split("n=")[1]), rate=x[0][0]) for l, x in split_rows]), [("group", "Context"), ("n", "n", int), ("rate", "Pass rate", lambda v: pct(v, 1))])

sh = pd.DataFrame(PJ["state_shift"])
pv = sh.pivot(index="state", columns="shift_dir", values=["pass_rate", "lo", "hi", "n"])
rows = []
for st_ in pv.index:
    def cell(k, nm):
        return (pv.loc[st_, ("pass_rate", k)], pv.loc[st_, ("lo", k)], pv.loc[st_, ("hi", k)], f"{st_}, {nm}: {pct(pv.loc[st_, ('pass_rate', k)], 1)} passed, n={int(pv.loc[st_, ('n', k)])}")
    rows.append((f"{st_} ({int(pv.loc[st_, ('n', 'toward R (>2 pts)')])}/{int(pv.loc[st_, ('n', 'toward D (>2 pts)')])})",
                 [cell("toward D (>2 pts)", "after a shift toward D"), cell("toward R (>2 pts)", "after a shift toward R")]))
rows.sort(key=lambda r: r[1][0][0] - r[1][1][0])
c_shift = dotrange(rows, [("After the state moved toward Democrats", B), ("After the state moved toward Republicans", O)], 0.1, 1.0, ref=0.5, xticks=[0.2, 0.4, 0.6, 0.8, 1.0], label_w=190, xlabel="Share passed (95% CI); n in brackets = toward R / toward D")
t_shift = table(sh, [("state", "State"), ("shift_dir", "Shift"), ("n", "n", int), ("pass_rate", "Pass rate", lambda v: pct(v, 1))])

def fmtm(v):
    return f"D+{v:.0f}" if v > 0 else (f"R+{-v:.0f}" if v < 0 else "even")
order_states = sorted(PJ["lean_2024"], key=lambda k: PJ["lean_2024"][k])
mv_rows = []
for st_ in order_states:
    a_, b_ = PJ["lean_1980"][st_], PJ["lean_2024"][st_]
    mv_rows.append((st_, [(a_, a_, a_, f"{st_} 1980: {fmtm(a_)}"), (b_, b_, b_, f"{st_} 2024: {fmtm(b_)} (change {b_ - a_:+.1f} pts)")]))
c_move = dotrange(mv_rows, [("1980 presidential race", B), ("2024 presidential race", O)], -50, 50, ref=0, fmt=lambda v: fmtm(v) if v else "even", xticks=[-40, -20, 0, 20, 40], label_w=120, xlabel="Two-party presidential margin (negative = Republican, positive = Democratic)")
t_move = table(pd.DataFrame([dict(state=k, a=PJ["lean_1980"][k], b=PJ["lean_2024"][k]) for k in order_states]), [("state", "State"), ("a", "1980", fmtm), ("b", "2024", fmtm)])

LAB2 = {"lean10": "Lean: +10 pts more Democratic", "shift10": "Shifted +10 pts toward Democrats", "gov_D": "Democratic governor (vs Republican)",
        "C(leg_cat, Treatment('R'))[T.D]": "Democratic legislature (vs Republican)", "C(leg_cat, Treatment('R'))[T.split]": "Split or tied legislature (vs Republican)"}
M1 = {r["term"]: r for r in PJ["m1"]["rows"]}; M2 = {r["term"]: r for r in PJ["m2"]["rows"]}
frows, ftab = [], []
for k, lab in LAB2.items():
    def tp_(r, nm):
        return None if r is None else (r["odds"], r["lo"], r["hi"], f"{nm}: odds ratio {r['odds']:.2f} (95% CI {r['lo']:.2f}–{r['hi']:.2f}), p={r['p']:.2f}")
    frows.append((lab, [tp_(M1.get(k), "Presidential terms only"), tp_(M2.get(k), "All partisan terms")]))
    ftab.append(dict(term=lab, a="–" if k not in M1 else f"{M1[k]['odds']:.2f} ({M1[k]['lo']:.2f}–{M1[k]['hi']:.2f}), p={M1[k]['p']:.2f}", b=f"{M2[k]['odds']:.2f} ({M2[k]['lo']:.2f}–{M2[k]['hi']:.2f}), p={M2[k]['p']:.2f}"))
c_pforest = dotrange(frows, [(f"Model 1: presidential lean and shift (n={PJ['m1']['n']:,})", B), (f"Model 2: plus governor and legislature (n={PJ['m2']['n']:,})", O)], 0.5, 2.0, ref=1.0, log=True,
                     fmt=lambda v: f"{v:g}×", xticks=[0.5, 0.75, 1, 1.5, 2], label_w=290, xlabel="Odds ratio of passing (1× = no effect)")
t_pforest = table(pd.DataFrame(ftab), [("term", "Partisan context"), ("a", "Model 1: OR (95% CI)"), ("b", "Model 2: OR (95% CI)")])
G_ = {r["gov_party"]: r for r in PJ["by_gov"]}; L_ = {r["leg_ctrl"]: r for r in PJ["by_leg"]}; T_ = {r["trifecta"]: r for r in PJ["by_trifecta"]}
SD_ = {r["shift_dir"]: r for r in PJ["by_shift_dir"]}; LC_ = {r["lean_cat"]: r for r in PJ["by_lean_cat"]}
OY = {r["term"]: r for r in PJ["ols_yes"]["rows"]}
CH = PJ["lean_change_1980_2024"]


# ---------------- values that used to be hard-coded in prose ----------------
_mp = pd.read_csv("data/measures_politics.csv"); _mp = _mp[(_mp.state != "District of Columbia") & _mp.gov_party.isin(["D", "R"])]
_ws = []
for _s, _g in _mp.groupby("state"):
    _a, _b = _g[_g.gov_party == "D"], _g[_g.gov_party == "R"]
    if len(_a) >= 15 and len(_b) >= 15:
        _ws.append(_a.passed.mean() - _b.passed.mean())
WS_POS, WS_N, WS_MEAN = int(sum(x > 0 for x in _ws)), len(_ws), 100 * sum(_ws) / len(_ws)
_xh = _mp[_mp.state != "Hawaii"].groupby("gov_party").passed.mean()
XHI_D, XHI_R = _xh["D"], _xh["R"]
M4 = {r["term"]: r for r in PJ["m4"]["rows"]}; M5 = {r["term"]: r for r in PJ["m5"]["rows"]}
EDU = M4["shift10:C(dom)[education]"]; M5L = M5["lean10"]; N_M5 = PJ["m5"]["n"]
SM = {r["state"]: r for r in S["by_state"]}
_cov = pd.read_csv("data/measures.csv").groupby("state").year.agg(["min", "max"])

# ---------------- hot-button section ----------------
HB = json.load(open("results/hotbuttons.json"))
RH = json.load(open("results/robustness_hotbuttons.json"))
_x = pd.read_csv("data/measures.csv").dropna(subset=["yes_pct"]); PASS_MAJ = 100 * (_x.passed == (_x.yes_pct > 50)).mean()
QN = ["Fewest voters", "2nd", "Middle", "4th", "Most voters"]
def qchart(key, label):
    rows_ = []
    for nm, r in zip(QN, HB[key]):
        rows_.append((nm, [(r["mean_margin"], r["margin_lo"], r["margin_hi"], f"{nm}: mean margin {r['mean_margin']:+.1f} pts (95% CI {r['margin_lo']:+.1f} to {r['margin_hi']:+.1f}); {pct(r['pass_rate'])} passed; n={int(r['n'])}")]))
    return dotrange(rows_, [("Mean margin", B)], -5, 20, ref=0, fmt=lambda v: f"{v:+.0f}", xticks=[0, 5, 10, 15], label_w=130, row_h=24, xlabel=label)
c_hb1 = qchart("by_vpc_quintile", "Mean margin, points (95% CI): raw votes per capita")
c_hb2 = qchart("by_rel_quintile", "Mean margin, points (95% CI): engagement vs the same ballot")
c_hb3 = qchart("by_excess_quintile", "Mean margin, points (95% CI): engagement beyond ballot position")
def cf(d_, nd=1):
    return f"{d_['coef']:+.{nd}f} pts (p={d_['p']:.2f})"
hb_def = pd.DataFrame([
    dict(a="Raw votes per capita", b=f"{HB['by_vpc_quintile'][4]['mean_margin']:+.1f} vs {HB['by_vpc_quintile'][0]['mean_margin']:+.1f}", c=cf(HB["m_margin_vpc_state_decade"]) + " (state + decade FE)", d="n/a"),
    dict(a="Engagement vs the same ballot", b=f"{HB['by_rel_quintile'][4]['mean_margin']:+.1f} vs {HB['by_rel_quintile'][0]['mean_margin']:+.1f}", c=cf(HB["m_margin_rel_ballot_fe"]), d=f"{HB['m_pass_rel_ballot_fe']['odds']:.2f} (p={HB['m_pass_rel_ballot_fe']['p']:.2f})"),
    dict(a="Engagement beyond ballot position", b=f"{HB['by_excess_quintile'][4]['mean_margin']:+.1f} vs {HB['by_excess_quintile'][0]['mean_margin']:+.1f}", c=cf(HB["m_margin_excess_ballot_fe"]), d=f"{HB['m_pass_excess_ballot_fe']['odds']:.2f} (p={HB['m_pass_excess_ballot_fe']['p']:.2f})")])
t_hbdef = table(hb_def, [("a", "How 'hot' is defined"), ("b", "Mean margin: most vs fewest voters"), ("c", "Within the same ballot: margin per +1 SD of engagement"), ("d", "Odds of passing per +1 SD")], label="Compare the three definitions of 'hot'", open_=True)
hb_top = pd.DataFrame([dict(m=f"{r['state']} {r['year']}" + (f" {r['measure']}" if isinstance(r['measure'], str) and r['measure'] not in ('', 'nan') else ""), d=(r["description"] or "")[:92], mg=r["margin"], v=r["vpc"] * 1000, p="Passed" if r["passed"] else "Failed") for r in HB["top_excess"][:14]])
t_hbtop = table(hb_top, [("m", "Measure"), ("d", "What it was"), ("mg", "Margin", lambda v: f"{v:+.1f}"), ("v", "Votes per 1,000", lambda v: f"{v:.0f}"), ("p", "Result")], label="The 14 hottest measures")
hb_dom = pd.DataFrame(HB["by_domain_relative"])
t_hbdom = table(hb_dom, [("domain", "Topic area"), ("n", "n", int), ("mean_rel", "Engagement vs ballot top", lambda v: pct(v)), ("mean_margin", "Mean margin", lambda v: f"{v:+.1f}"), ("pass_rate", "Passed", lambda v: pct(v, 1))], label="Topic areas: engagement, margin, pass rate")
HBV = {r["pres_year"]: r for r in HB["vpc_by_pres_year"]}


rh = pd.DataFrame(RH["sensitivity"])
t_rh = table(rh, [("label", "Specification"), ("n", "Measures", int), ("coef", "Margin per +1 SD engagement", lambda v: f"{v:+.1f}"), ("lo", "95% CI low", lambda v: f"{v:+.1f}"), ("hi", "95% CI high", lambda v: f"{v:+.1f}"), ("p", "p", lambda v: f"{v:.3f}"), ("pass_odds", "Pass odds ratio", lambda v: f"{v:.2f}"), ("pass_p", "p (pass)", lambda v: f"{v:.3f}")], label="The eight specifications", open_=True)
RHS = {r["label"][:8]: r for r in RH["sensitivity"]}
RH_COEF = [r["coef"] for r in RH["sensitivity"]]; RH_ODDS = [r["pass_odds"] for r in RH["sensitivity"]]
RH_EVEN = next(r for r in RH["sensitivity"] if r["label"].startswith("even years")); RH_TIGHT = next(r for r in RH["sensitivity"] if r["label"].startswith("only ballots")); RH_BASE = RH["sensitivity"][0]

# ---------------- text ----------------
ini = next(r for r in S["type_known"] if r["mtype"] == "initiative")
leg = next(r for r in S["type_known"] if r["mtype"] == "legislative")
rep = a["mentions_repeal"]
repB = b["mentions_repeal"]
wr = {r["feature"]: r for r in S["wording_raw"]}
OR_ORIG = math.exp(b['C(mtype)[T.legislative]']['coef']) if 'C(mtype)[T.legislative]' in b else 2.5

PAGE = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Yes, No, Maybe So</title>
<meta name="description" content="Do yeses or nos win more on US state ballot measures, and does wording or topic change the odds? {H['n']:,} measures, 1976–2024.">
<style>
:root{{--bg:#fcfcfb;--panel:#f4f3f0;--ink:#0b0b0b;--ink2:#52514e;--grid:#e3e2dd;--s1:#2a78d6;--s2:#eb6834;--ref:#52514e;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#1a1a19;--panel:#242422;--ink:#f0efec;--ink2:#c3c2b7;--grid:#34342f;--s1:#3987e5;--s2:#d95926;--ref:#c3c2b7;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#1a1a19;--panel:#242422;--ink:#f0efec;--ink2:#c3c2b7;--grid:#34342f;--s1:#3987e5;--s2:#d95926;--ref:#c3c2b7;color-scheme:dark}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:40px 16px 80px}}
h1{{font-size:2.3rem;line-height:1.15;margin:.2em 0 .3em}}h2{{font-size:1.4rem;margin:2.2em 0 .4em}}h3{{font-size:1.05rem;margin:1.6em 0 .2em}}
.sub{{color:var(--ink2);font-size:1.1rem}}p{{margin:.7em 0}}a{{color:var(--s1)}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}}
.kpi{{background:var(--panel);border-radius:10px;padding:14px 16px}}.kpi b{{display:block;font-size:1.9rem;line-height:1.1}}.kpi span{{color:var(--ink2);font-size:.88rem}}
.chart{{width:100%;height:auto;display:block;margin:6px 0 4px}}.grid{{stroke:var(--grid);stroke-width:1}}.ref{{stroke:var(--ref);stroke-width:1.2;stroke-dasharray:4 3}}
.tick,.axis{{fill:var(--ink2);font-size:11.5px}}.lab{{fill:var(--ink);font-size:12.5px}}.pt:hover .dot{{r:6.5}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.88rem;color:var(--ink2);margin-top:8px}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.fig{{margin:18px 0 8px}}.fig h3{{margin-top:0}}.note{{color:var(--ink2);font-size:.9rem}}
details{{margin:4px 0 16px;font-size:.88rem;color:var(--ink2)}}summary{{cursor:pointer}}.tw{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;margin-top:6px}}th,td{{text-align:left;padding:4px 10px 4px 0;border-bottom:1px solid var(--grid);white-space:nowrap}}
.callout{{background:var(--panel);border-left:4px solid var(--s1);padding:10px 16px;border-radius:0 8px 8px 0;margin:18px 0}}
.warn{{border-left-color:var(--s2)}}code{{font-size:.9em}}footer{{margin-top:50px;color:var(--ink2);font-size:.88rem}}
</style></head><body><main>
<p class="note">A data project on US state ballot measures, 1976–2024</p>
<h1>Yes, No, Maybe So</h1>
<p class="sub">Do voters say yes more than no? Does the way a measure is worded, or what it is about, change the odds?</p>
<p><a href="explorer.html"><b>Interactive: sort every measure by voters per capita →</b></a></p>

<div class="kpis">
<div class="kpi"><b>{H['n']:,}</b><span>statewide measures decided, 1976–2024</span></div>
<div class="kpi"><b>{pct(H['pass_rate'])}</b><span>passed (95% CI {pct(H['ci'][0])}–{pct(H['ci'][1])})</span></div>
<div class="kpi"><b>{pct(ini['pass_rate'])} vs {pct(leg['pass_rate'])}</b><span>initiatives vs legislative referrals</span></div>
<div class="kpi"><b>{H['states']}</b><span>jurisdictions with measure-level data</span></div>
</div>

<div class="callout" id="summary"><b>Executive summary</b>
<p><b>Question.</b> Across {H['n']:,} statewide ballot measures (1976&ndash;2024, 15 states plus DC), do yeses or nos win more, and do wording, topic, origin or politics change the odds?</p>
<ul>
<li><b>Yes wins slightly more than no</b>: {pct(H['pass_rate'])} of measures passed. The average hides a split: legislative referrals passed {pct(leg['pass_rate'])}, citizen initiatives only {pct(ini['pass_rate'])} (about {OR_ORIG:.1f}&times; the odds after controls). For initiatives, no wins more.</li>
<li><b>Wording: one robust signal.</b> Measures that ask voters to repeal, eliminate or abolish something pass far less often (odds ratio {rep['odds']:.2f}). Verb framing, tax mentions and amendment status show nothing reliable once state and topic are held fixed.</li>
<li><b>Type matters, but less than origin.</b> Criminal-justice measures pass most (79%); social, economic, environment and education sit around 52&ndash;57%.</li>
<li><b>State history matters most.</b> Pass rates run from {pct(st.iloc[0].pass_rate)} (South Dakota) to {pct(st.iloc[-1].pass_rate)} (Hawaii), and a state's record predicts its next result.</li>
<li><b>Politics: no reliable effect.</b> Presidential lean, a state shifting toward either party, governor's party and legislative control do not move the average yes/no once the state is held fixed. Because a "yes" can be conservative or liberal, this does not rule out partisan effects on <i>which</i> measures pass.</li>
<li><b>Hot-button issues: a mild, consistent tilt toward "no", not robust.</b> Measures that draw more voters than others on the same ballot have about {abs(RH_BASE['coef']):.1f} points lower margins per SD (negative in all eight specifications, significant in some). The test is underpowered, so this is suggestive, not settled.</li>
</ul>
<p><b>Confidence and limits.</b> Association, not causation. Wording and topic results cover the 16 jurisdictions with measure-level data, not all 50 states; California has no vote counts; Wikipedia's lists miss some initiatives; topic labels are keyword-based (~75&ndash;80% accurate). Two earlier findings were retracted or weakened after audits (a governor-party effect that came from a parser bug, and an over-strong &ldquo;no hot-button slant&rdquo;); see <a href="#stress">section 7</a>.</p>
</div>

<div class="callout warn"><b>Read this first: coverage.</b> There is no free, complete, machine-readable database of every statewide measure in all 50 states. This report uses a <b>two-tier design</b>.
(1) <b>Measure-level data</b> ({H['n']:,} measures) come from Wikipedia's per-state lists, which exist for 15 states and DC (AK, AZ, CA, CO, FL, HI, MI, MO, MT, OH, OK, OR, SD, WA, WY, DC) and are uneven in span.
(2) <b>Initiative counts and approval rates for every initiative state</b> come from the Initiative &amp; Referendum Institute (IRI). Everything about <i>wording</i> rests on tier 1 only, so it speaks for those states, not all 50. Ballotpedia's complete data blocks automated access; swapping it in is the obvious next step (see <a href="#limits">limits</a>).</div>

<h2>The short answer</h2>
<p><b>Yes wins slightly more often than no: {pct(H['pass_rate'])} of measures passed</b> (mean yes share {H['mean_yes_pct']:.1f}%). But that average hides a split that matters more than anything else in the data:</p>
<ul>
<li><b>Who puts it on the ballot matters most.</b> Where origin is identifiable, <b>legislative referrals passed {pct(leg['pass_rate'])}</b> and <b>citizen initiatives only {pct(ini['pass_rate'])}</b>. For initiatives, <b>no wins more than yes</b>. After controls, referrals have about {math.exp(b['C(mtype)[T.legislative]']['coef']) if 'C(mtype)[T.legislative]' in b else 2.5:.1f}× the odds.</li>
<li><b>One wording signal is robust: asking voters to repeal, eliminate or abolish something.</b> Those measures passed {pct(wr['mentions_repeal']['rate_with'])} of the time vs {pct(wr['mentions_repeal']['rate_without'])}, and the effect survives controls for state, decade, topic and length (odds ratio {rep['odds']:.2f}; {repB['odds']:.2f} in the stricter model).</li>
<li><b>Most other wording features do nothing detectable</b> once state and topic are held fixed: restrictive vs expansive verbs, mentioning taxes or debt, or being a constitutional amendment.</li>
<li><b>Topic matters, but less than origin.</b> Criminal-justice measures pass most (79%); environment, education, social and tax measures sit near 52–54%.</li>
<li><b>Partisan climate does not reliably move the average yes/no.</b> Presidential lean and a state becoming more Democratic or Republican show no reliable effect once the state is held fixed, and neither does legislative control. Democratic-governor years pass a little more often ({M2['gov_D']['odds']:.2f}× the odds), but that is not statistically distinguishable from zero (<a href="#politics">section 5</a>).</li>
<li><b>Hot-button issues lean slightly toward "no", but not robustly.</b> Measures that draw more voters than others on the same ballot have somewhat lower margins and pass less often (about {RH_BASE['coef']:+.1f} points and {RH_BASE['pass_odds']:.2f}× the odds per SD), consistent in sign across eight specifications but significant in only some, and the test is underpowered (<a href="#hotbuttons">section 6</a>, <a href="explorer.html">explorer</a>).</li>
<li><b>State culture matters a lot.</b> Pass rates range from {pct(st.iloc[0].pass_rate)} (South Dakota) to {pct(st.iloc[-1].pass_rate)} (Hawaii). A state's own track record is a strong predictor of any new measure (p&lt;0.001).</li>
</ul>

<h2>1. Do yeses win more than nos?</h2>
<p>Across all measures, yes wins {pct(H['pass_rate'])} of the time, higher than a coin flip (binomial p&lt;0.001). The mean passing measure gets {S['margins']['mean_yes_when_pass']:.0f}% yes; the mean failing one gets {S['margins']['mean_yes_when_fail']:.0f}%. Results are usually decisive: {pct(S['margins']['share_pass_above_60'])} of passes top 60%, and {pct(S['margins']['share_fail_below_40'])} of failures are below 40%.</p>
<p>The pooled number is partly an artifact of mix, though. Legislative referrals, often routine constitutional housekeeping, pass easily. Citizen initiatives, which are contested, usually fail.</p>
<div class="fig"><h3>Pass rate by decade</h3>{c_decade}{t_decade}
<p class="note">Pooled data suggest a fall from ~63% in the 1970s–80s to ~54% in the 1990s–2000s. Part of that is composition: Arizona, Missouri, South Dakota and Oklahoma only enter the data later. Restricted to the 11 states covered across the whole period (orange), the drop is real but between the 1980s and 1990s, then flat, with a 2020s rebound (small n). The linear trend in the pooled series is not significant (p={S['trend_pass_rate']['p']:.2f}).</p></div>

<h2>2. Does the type of measure matter?</h2>
<h3>By origin</h3>
<p>Origin is explicit in the data for {ini['n'] + leg['n']:,.0f} measures (California titles say "Initiative"; Oregon, Alaska, DC and others label it; some descriptions state it). Initiatives: <b>{pct(ini['pass_rate'])}</b> passed. Legislative referrals: <b>{pct(leg['pass_rate'])}</b> (difference p&lt;0.001). The gap holds within every topic area.</p>
<div class="fig"><h3>Pass rate by topic area and origin</h3>{c_type}{t_type}
<p class="note">"Social" combines social issues (drugs, guns, abortion, marriage, gambling…) and criminal justice. "Economic" combines taxes/budget, transportation, health/welfare and labor. Topics are assigned by keyword rules and are imperfect (see limits).</p></div>

<h3>By topic</h3>
<div class="fig">{c_topic}{t_topic}
<p class="note">Criminal-justice measures (victims' rights, sentencing, bail) pass about four times in five. The rest cluster around 52–57%. "Other" is a grab-bag; in the regression it serves as the reference category, so every named topic shows a negative coefficient against it. Read the raw rates above instead.</p></div>

<h2>3. Does the wording matter?</h2>
<p>For each measure I extracted features from the official or summarized title: verbs that restrict (ban, limit, cut) or expand (allow, create, provide), whether it mentions taxes/fees/bonds, an increase, or a repeal; whether it is a constitutional amendment; length; and reading ease (Flesch). I then fit logistic regressions of passing on all of them at once, with state and decade fixed effects and topic controls, so each feature is judged against similar measures in the same state and era.</p>
<div class="fig"><h3>Effect of each wording feature on the odds of passing</h3>{c_forest}{t_forest}
<p class="note">Model A uses everything. Model B keeps only measures whose origin is known and controls for it. Standard errors cluster by state-election. A bar crossing 1× means the effect is indistinguishable from zero.</p></div>
<ul>
<li><b>Repeal language is the one clear signal.</b> Both models agree: odds of passing are roughly 60% lower. Voters appear to resist taking things away, especially when the measure frames itself as undoing an existing law.</li>
<li><b>Restrictive vs expansive framing, tax/debt mentions, "increase" language and amendment status</b> show no reliable effect after controls, even where raw differences look large (for example amendments pass {pct(wr['is_amendment']['rate_with'])} vs {pct(wr['is_amendment']['rate_without'])} raw, but that gap is mostly origin and state).</li>
<li><b>Length and readability are suggestive, not conclusive.</b> Longer text goes with higher pass rates (rank correlation with yes share ρ={S['len_vs_yespct']['rho']:.2f}). In Model B each extra SD of length raises the odds ~{(b['zlen']['odds'] - 1) * 100:.0f}% and harder-to-read text does slightly better. In Model A neither survives. With eight features tested, treat these as hypotheses.</li>
</ul>
<div class="callout"><b>An important caveat on "wording".</b> Wikipedia's text is a mix of official ballot titles (California, Oregon, Washington) and editors' plain-English summaries (Colorado, Missouri, Wyoming and others). So some "wording" differences are really differences in who wrote the summary. State fixed effects absorb most of this, but a true test of wording effects needs the official ballot language for every measure. That is the main upgrade this project needs.</div>

<h2>4. Cross-referencing with state history</h2>
<div class="fig"><h3>How often measures pass, by state</h3>{c_state}{t_state}
<p class="note">Hawaii, Florida, DC and Wyoming say yes most often. South Dakota, Oregon, Michigan and Colorado say no almost as often as yes. South Dakota is the most skeptical on vote share (mean yes {SM['South Dakota']['mean_yes_pct']:.0f}%).</p></div>
<p><b>State history predicts the next result.</b> Using each measure's own state's pass rate from all <i>other</i> measures (leave-one-out) to predict the outcome gives a coefficient of {S['state_baseline']['coef']:.1f} (p&lt;0.001): a state that says yes often keeps saying yes, whatever the wording.</p>

<h3>Sanity check against the official initiative record</h3>
<p>For the states where I could identify enough initiatives (30+), the pass rate in this dataset closely tracks the IRI's independent count of all initiatives from 1976 to 2024, for example California {pct(0.403, 1)} vs {pct(0.404, 1)}, Oregon 36.5% vs 35.7%, Washington 53.0% vs 54.0%. That gives some confidence in the parsing and origin tagging. Colorado and Michigan diverge, as their initiative tagging relies on text cues.</p>
<div class="fig">{c_iri}{t_iri}</div>
<p>IRI's all-state series shows initiative approval rising from 39% in the 1970s to 51% in the 2010s, which is the opposite direction of the pooled series above. Initiatives and referrals tell different stories, another reason to keep origin separate.</p>

<h2 id="politics">5. Does politics matter? Presidential lean, governors and legislatures</h2>
<p>To test whether a state's partisan climate affects yes-or-no outcomes, I attached four pieces of context to every measure (DC is excluded because it has no governor or state legislature):</p>
<ul>
<li><b>Lean:</b> the Democratic two-party margin in the <i>most recent presidential race before the measure's year</i> (a same-year race is simultaneous, not history).</li>
<li><b>Shift:</b> how far that margin moved from the race before it. Positive means the state was becoming more Democratic; negative, more Republican. I also tested a two-cycle (8-year) shift.</li>
<li><b>Governor's party</b> and <b>legislative control</b> (both chambers Democratic, both Republican, or split/tied) as shown for that year in Wikipedia's party-strength tables. A Democratic or Republican trifecta means governor plus both chambers.</li>
</ul>
<div class="fig"><h3>How these states moved, 1980 to 2024</h3>{c_move}{t_move}
<p class="note">Colors here mark the year, not a party. Over this period, the states in the data that became <b>more Democratic</b> were California ({CH['California']:+.0f} pts), Colorado ({CH['Colorado']:+.0f}), Washington ({CH['Washington']:+.0f}), Arizona ({CH['Arizona']:+.0f}) and Oregon ({CH['Oregon']:+.0f}), plus Alaska and Hawaii (about +21). The states that became <b>more Republican</b> were Missouri ({CH['Missouri']:+.0f}), Wyoming ({CH['Wyoming']:+.0f}) and Oklahoma ({CH['Oklahoma']:+.0f}). Margins are two-party, so they ignore third-party votes (Anderson in 1980, Perot in 1992 and 1996) and long-run comparisons are approximate.</p></div>

<h3>The raw picture</h3>
<div class="fig">{c_split}{t_split}</div>
<p>Raw differences are small and lean one way. Under Democratic governors {pct(G_['D']['pass_rate'], 1)} of measures passed vs {pct(G_['R']['pass_rate'], 1)} under Republicans. Under Democratic legislatures {pct(L_['D']['pass_rate'], 1)} vs {pct(L_['R']['pass_rate'], 1)} (Republican) and {pct(L_['split']['pass_rate'], 1)} (split). Democratic trifectas passed {pct(T_['D trifecta']['pass_rate'], 1)}, Republican trifectas {pct(T_['R trifecta']['pass_rate'], 1)}. The 95% intervals overlap in most comparisons. Part of the governor gap is state composition: Hawaii is mostly Democratic-run and passes 83% of its measures, and without it the gap roughly halves ({pct(G_['D']['pass_rate'], 1)} vs {pct(G_['R']['pass_rate'], 1)} becomes {pct(XHI_D, 1)} vs {pct(XHI_R, 1)}).</p>
<p>Presidential lean points the other way in the raw data: measures in Republican-leaning states (more than 10 points) passed {pct(LC_['R-leaning (>10 pts)']['pass_rate'], 1)}, vs {pct(LC_['D-leaning (>10 pts)']['pass_rate'], 1)} in Democratic-leaning ones. And states that had just moved toward Democrats passed {pct(SD_['toward D (>2 pts)']['pass_rate'], 1)} vs {pct(SD_['toward R (>2 pts)']['pass_rate'], 1)} after moving toward Republicans.</p>

<h3>With controls: mostly no detectable effect</h3>
<p>The cleaner test uses state fixed effects, so lean and shift are identified by <i>the same state changing over time</i> rather than comparing, say, Wyoming with California. It also controls for decade and topic and clusters by state-election.</p>
<div class="fig">{c_pforest}{t_pforest}</div>
<ul>
<li><b>A state's presidential lean does not predict yes or no</b> once the state is held fixed (odds ratio {M1['lean10']['odds']:.2f} per 10 points, p={M1['lean10']['p']:.2f}). The raw Republican-state advantage is a difference between states, not an effect of partisanship.</li>
<li><b>A state becoming more Democratic or more Republican shows no reliable effect</b> (odds ratio {M1['shift10']['odds']:.2f} per 10 points toward Democrats, p={M1['shift10']['p']:.2f}; the 8-year version is similar). The point estimate leans slightly negative, so the raw gap above is not distinguishable from noise.</li>
<li><b>Governor's party shows a small tilt that is not statistically reliable.</b> Democratic-governor years pass slightly more often, but the pass/fail odds ratio ({M2['gov_D']['odds']:.2f}, CI {M2['gov_D']['lo']:.2f}–{M2['gov_D']['hi']:.2f}, p={M2['gov_D']['p']:.2f}) is not significant, and the odds ratio stays between {RB['gov_D_loo_range'][0]:.2f} and {RB['gov_D_loo_range'][1]:.2f} whichever state is dropped. Within states the direction is mostly the same: more passes under Democratic governors in {WS_POS} of the {WS_N} states with enough data (average {WS_MEAN:+.1f} points), though Arizona and Missouri go the other way. On vote share, yes runs {RB['gov_D_yes_share']['coef']:+.1f} points higher under Democratic governors, but with only {RB['gov_D_yes_share']['clusters']} states contributing vote shares (California has none) ordinary standard errors are unreliable, and a wild cluster bootstrap gives p={RB['gov_D_yes_share']['wild_bootstrap_p']:.2f}. <b>Correction:</b> an earlier version of this report called this effect significant (+2.6 points, p≈0.006). That result was an artifact of a parser bug that had silently dropped Arizona's 2010–2024 measures; with them restored, it disappears.</li>
<li><b>Legislative control shows nothing</b> (Democratic: {M2['C(leg_cat, Treatment(\'R\'))[T.D]']['odds']:.2f}×, split: {M2['C(leg_cat, Treatment(\'R\'))[T.split]']['odds']:.2f}× vs Republican; both p&gt;0.5).</li>
<li><b>Does it depend on topic or origin?</b> The one interaction that stands out is that education measures do worse as a state moves toward Democrats (odds ratio {EDU['odds']:.2f} per 10 points, p={EDU['p']:.2f}). It is one of twelve interaction terms, so it may be chance. Among initiatives with a known origin there is weak evidence of a lower pass rate in more Democratic states (odds ratio {M5L['odds']:.2f} per 10 points, p={M5L['p']:.2f}; n={N_M5}), and no clear difference for referrals.</li>
</ul>
<div class="fig"><h3>Within the same state: after shifts toward Democrats vs toward Republicans</h3>{c_shift}{t_shift}
<p class="note">Only the 14 states with at least 8 measures in each condition. Pass rates were higher after shifts toward Republicans in 9 of the 14 (average +3.1 points), which a sign test cannot distinguish from a coin flip (p=0.42). Intervals overlap in nearly every state.</p></div>
<div class="callout"><b>Why the null result isn't surprising.</b> A "yes" vote is not inherently partisan: it can enact a conservative or a liberal policy. If Democratic-leaning electorates say yes to a minimum-wage hike and no to a tax cap while Republican ones do the opposite, the pass rate averaged across all measures cancels out. So these results show that a state's partisan climate does not make voters <i>generally</i> more or less willing to say yes. They say nothing about whether partisanship shapes <i>which</i> measures pass. Testing that needs each measure coded for its ideological direction, which this dataset does not yet have (see next steps).</div>

<h2 id="hotbuttons">6. Hot-button issues: do the most-voted measures lean yes or no?</h2>
<p><a href="explorer.html"><b>Open the interactive Hot-Button Explorer →</b></a> sort every measure by votes per capita, filter by state, topic, origin and era, and see the margin for or against on the y-axis.</p>
<p>I measured how many voters weighed in on each measure (yes plus no votes) and divided by the state's population that year. Three versions, because the obvious one is misleading:</p>
<ul>
<li><b>Raw votes per capita</b> mostly measures <i>which election it was</i>. In presidential years the median is {HBV[True]['median']*1000:.0f} voters per 1,000 residents vs {HBV[False]['median']*1000:.0f} otherwise, and {pct(HB['top_decile_vpc_share_pres_year'])} of the top-decile measures sit in presidential years (they are {pct(HB['share_pres_year'])} of all measures). The highest raw value of all is {HB['top_vpc'][0]['vpc']*1000:.0f} per 1,000 ({HB['top_vpc'][0]['state']}, {HB['top_vpc'][0]['year']}).</li>
<li><b>Engagement vs the same ballot</b> divides a measure's votes by the most-voted measure on that state-year's ballot (ballots with at least 5 measures), which removes the election effect.</li>
<li><b>Engagement beyond ballot position</b> additionally removes the small trend with where the measure sits on the ballot.</li>
</ul>
<div class="fig"><h3>Does the margin change as more voters weigh in? Mean margin by fifth, three definitions</h3>{c_hb1}{c_hb2}{c_hb3}
<p class="note">Margin = (yes − no) ÷ (yes + no), in points; positive favors the measure. Hawaii counts blank ballots as "no" for passage. Bars show 95% intervals for the mean.</p></div>
<h3>Findings</h3>
{t_hbdef}
<ul>
<li><b>A modest, consistent tilt toward "no" as engagement rises, but not a robust one.</b> The raw and election-adjusted views lean slightly toward "no" (the most-engaged fifth averages about {HB['by_rel_quintile'][4]['mean_margin']:+.0f} points vs {HB['by_rel_quintile'][0]['mean_margin']:+.0f} for the least-engaged). Comparing measures on the same ballot, the baseline estimate is {RH_BASE['coef']:+.1f} points per standard deviation of engagement (95% CI {RH_BASE['lo']:+.1f} to {RH_BASE['hi']:+.1f}, p={RH_BASE['p']:.2f}). Across the eight variants I tried, the estimate is <b>never positive</b> ({min(RH_COEF):+.1f} to {max(RH_COEF):+.1f} points; pass odds {min(RH_ODDS):.2f}–{max(RH_ODDS):.2f}). It strengthens when the electorates are cleaner: counting only even-year, non-special ballots gives {RH_EVEN['coef']:+.1f} points (p={RH_EVEN['p']:.3f}; pass odds {RH_EVEN['pass_odds']:.2f}, p={RH_EVEN['pass_p']:.3f}), and only ballots whose measures all drew similar vote counts gives {RH_TIGHT['coef']:+.1f} (p={RH_TIGHT['p']:.2f}; pass odds {RH_TIGHT['pass_odds']:.2f}, p={RH_TIGHT['pass_p']:.2f}). Because I tried eight variants, treat the two significant ones as suggestive. The ballot-position-adjusted version is weaker ({HB['m_margin_excess_ballot_fe']['coef']:+.1f}, p={HB['m_margin_excess_ballot_fe']['p']:.2f}) and its fifths do not slope downward ({HB['by_excess_quintile'][4]['mean_margin']:+.1f} vs {HB['by_excess_quintile'][0]['mean_margin']:+.1f}).</li>
<li><b>The test is underpowered.</b> With these standard errors the smallest slant I could reliably detect is about {RH['mde_points_per_sd']:.1f} points per standard deviation, larger than every estimate above. So "not significant" here does not mean "no slant"; a real tilt of the size observed would usually go undetected.</li>
<li><b>Hot is not the same as close.</b> More-engaged measures are not detectably more narrowly decided (margin size changes {HB['m_absmargin_excess_ballot_fe']['coef']:+.1f} points per SD, p={HB['m_absmargin_excess_ballot_fe']['p']:.2f}).</li>
<li><b>Passing odds:</b> within a ballot, more-engaging measures pass less often in every variant (odds ratio {HB['m_pass_rel_ballot_fe']['odds']:.2f} per SD in the baseline, p={HB['m_pass_rel_ballot_fe']['p']:.2f}), consistent with a mild status-quo bias: when more people vote, "no" gains a little.</li>
<li><b>Which topics draw voters?</b> Social-issue measures draw the most voters relative to their ballot, though the spread across topic areas is small (below).</li>
</ul>
<p class="note"><b>How the same-ballot estimate changes with how the sample is cut</b> (margin per +1 SD of engagement vs the same ballot):</p>
{t_rh}
{t_hbdom}
<h3>The measures that drew the most voters beyond their ballot position</h3>
{t_hbtop}
<p class="note">Ranked by position-adjusted engagement on ballots with at least 5 measures. It includes real hot-button fights (Alaska's 1998 marriage definition, Colorado's 1988 English-language amendment, Washington's 2001 property-tax cap).</p>
<div class="callout warn"><b>Two caveats specific to this section.</b> <b>California is missing.</b> It has no vote counts in my data: the Secretary of State publishes them as per-election PDFs on a CDN that rejects ordinary automated requests, and I have not pulled them. It holds many of the best-known hot-button measures (Props 13, 187, 209, 8, 64). Everything here covers the other 14 states and DC, {HB['n']:,} measures. <b>Votes per capita is not turnout:</b> the denominator is total resident population, so it understates participation and varies with age structure and non-citizens.</div>

<h2 id="stress">7. Stress tests: what I tried to break</h2>
<p>After the first version of this report I went looking for ways the headline results could be wrong. What I found and what held up:</p>
<ul>
<li><b>A bug in two wording features, now fixed.</b> The "expansive verbs" pattern contained <code>amend</code>, so it fired on nearly every constitutional amendment (correlation with "amendment" 0.62), and "restrictive" matched words like <i>capital</i> and <i>bargaining</i>. After fixing both (correlation now {RB['regex_corr_expansive_amendment']:.2f}), every wording estimate moved by a few hundredths at most and no conclusion changed, but the earlier "restrictive vs expansive" comparison did not measure what it claimed.</li>
<li><b>The repeal effect holds up.</b> Dropping any one state leaves the odds ratio between {RB['repeal_loo']['min']:.2f} and {RB['repeal_loo']['max']:.2f} (all p&lt;{max(RB['repeal_loo']['max_p'], 0.001):.3f}). It appears in {RB['repeal_loo']['n_states_with_repeal']} states and within each origin: initiatives with repeal language passed {pct(RB['repeal_raw_by_origin']['initiative_1'])} vs {pct(RB['repeal_raw_by_origin']['initiative_0'])} without; referrals {pct(RB['repeal_raw_by_origin']['legislative_1'])} vs {pct(RB['repeal_raw_by_origin']['legislative_0'])}. Caveats: it is only {RB['repeal_loo']['n_repeal']} measures, the word's presence is not the same as the measure's main action, and a repeal measure is also a different policy.</li>
<li><b>The origin gap is not an Oregon artifact, but the data are lopsided.</b> Oregon supplies {pct(RB['oregon_share_of_legislative'])} of identified legislative referrals, and {pct(RB['origin_share_from_text'])} of all origin labels are inferred from description text. Restricting to the {len(RB['origin_within_state']['states'])} states with at least 10 of each origin ({', '.join(RB['origin_within_state']['states'])}) and comparing within state, referrals still have {RB['origin_within_state']['odds']:.1f}× the odds (CI {RB['origin_within_state']['lo']:.1f}–{RB['origin_within_state']['hi']:.1f}). The direction is reversed or flat in a few small-sample states (Michigan, South Dakota).</li>
<li><b>The lists are incomplete.</b> Against the IRI's official initiative counts, Wikipedia's lists are short by at least {RB['completeness']['initiatives_missing_lower_bound']} initiatives in {RB['completeness']['state_years_short']} of {RB['completeness']['state_years_checked']} state-years. Most of that is the late-starting windows noted above (Missouri, Oklahoma, South Dakota); the rest are unexplained gaps in Arizona, Montana, Ohio and Oregon (about {sum(RB['completeness']['by_state'].get(k, 0) for k in ('Arizona', 'Montana', 'Ohio', 'Oregon'))} initiatives). I cannot tell whether missing measures skew toward passes or failures; this is a lower bound only for initiatives, and referrals cannot be checked this way.</li>
<li><b>Partisan results under harsher inference.</b> Clustering by state (15 clusters) instead of by state-election changes none of the logit conclusions. Removing decade fixed effects makes shifts toward Democrats look slightly more negative (odds ratio {RB['politics_no_decade_fe']['shift10']['odds']:.2f}, p={RB['politics_no_decade_fe']['shift10']['p']:.2f}) but still not significant.</li>
<li><b>A parser bug changed a conclusion.</b> While adding vote counts I found that Arizona's stacked-header tables for 2010–2024 had been silently skipped (57 measures). Restoring them moved the governor-party yes-share effect from +2.6 points (bootstrap p≈0.006, which I had reported as the most credible partisan signal) to {RB['gov_D_yes_share']['coef']:+.1f} points (p={RB['gov_D_yes_share']['wild_bootstrap_p']:.2f}). Other headline results moved by less than a point. Lesson: a result that hinges on a handful of states is only as good as the audit of each state's rows.</li>
<li><b>The first hot-button conclusion was too strong.</b> I first wrote "no reliable slant." A sensitivity check showed that state-year "ballots" sometimes mix a primary or special election with the general (about {100*RH['ballots_votes_ratio_gt2']/RH['ballots_total']:.0f}% of ballots have vote counts differing by more than 2×), which attenuates the engagement measure, and that the test could only detect effects above ~{RH['mde_points_per_sd']:.0f} points per SD. The conclusion was revised to "a consistent but not robust tilt toward no" (section 6).</li>
<li><b>Two errors caught in the hot-button analysis before publishing.</b> A helper that returned the wrong regression coefficient (it reported a dummy variable, producing spurious p&lt;0.001 results), and a "ballot position" variable that was accidentally each measure's own engagement rank (correlation −0.76 with engagement; the real correlation is +0.14). Both are fixed; the section 6 numbers use the corrected code.</li>
<li><b>Not tested:</b> causation; whether Wikipedia's coverage is selective; independent double-extraction of the governor and legislature tables; and ideological direction of each measure. All results are associations in 15 states.</li>
</ul>

<h2 id="limits">Limits and next steps</h2>
<ul>
<li><b>Not all 50 states.</b> Measure-level data cover 15 states and DC; ~24 states allow citizen initiatives but all 50 hold referred measures. Coverage varies: Arizona from 1990, Missouri and South Dakota from 2000, Oklahoma from 2004, Montana and Ohio from 1980, DC 1979 only. Pooled figures overweight California, Oregon, Colorado and Washington.</li>
<li><b>Origin unknown for 59% of measures.</b> Pass rates by origin use only identifiable cases, and Oregon supplies nearly half of the identified referrals (section 7). Model B uses only those cases.</li>
<li><b>Lists are incomplete.</b> At least {RB['completeness']['initiatives_missing_lower_bound']} initiatives from the IRI's official count are absent (section 7), and referral coverage cannot be checked.</li>
<li><b>Topic labels are keyword rules</b> (about 75–80% sensible in a hand audit of 40 titles), so topic effects are blurred toward zero.</li>
<li><b>Wording is measured from summaries, not full ballot language.</b> And "wording" is correlated with substance: a measure to repeal a law is also a different <i>policy</i>, so this is association, not proof that rewording would change outcomes.</li>
<li><b>Outcomes:</b> passage matches simple majority in {PASS_MAJ:.1f}% of rows with vote data; exceptions are legitimate supermajority rules (Florida's 60%, Wyoming).</li>
<li><b>Partisan context:</b> governor and legislature data were extracted from Wikipedia's party-strength pages by four parallel agents, then checked for row counts, chamber sizes and 17 known state-years. Treat individual cells as probably right, not audited. Ties are coded as split. Years are as shown on the page, with the governor in office that year. Only 15 states, so partisan estimates are noisy. Without ideological coding of each measure, the partisan analysis cannot say whether liberal or conservative measures fare differently by climate.</li>
<li><b>Next (also):</b> code each measure's ideological direction (conservative, liberal, neutral) to test climate-by-direction effects, the natural follow-up to section 5.</li>
<li><b>Next:</b> add Ballotpedia or IRI measure-level data for all states; add official ballot titles; add a better topic classifier; model state-level covariates (partisanship, signature rules).</li>
</ul>

<footer>Data: Wikipedia state ballot-measure and party-strength lists (CC BY-SA), IRI state-by-year initiative counts (Matsusaka, USC), MIT Election Data and Science Lab presidential returns 1976-2016, county-level presidential results 2020 and 2024 (tonmcg), Census Bureau state population estimates. Code, data and method: see the repository. Generated by <code>scripts/build_site.py</code> from <code>results/summary.json</code>.</footer>
</main></body></html>"""

open("docs/index.html", "w").write(PAGE)
print("wrote docs/index.html", len(PAGE))
