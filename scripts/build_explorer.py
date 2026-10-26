"""Generate docs/explorer.html: an interactive, sorted view of every measure with vote counts.
Reads data/measures_votes.csv. Run from repo root after build_votes.py."""
import json, os
import numpy as np, pandas as pd

v = pd.read_csv("data/measures_votes.csv")
ex = pd.read_csv("data/raw/excluded_vote_counts.csv")
rows = []
for r in v.itertuples():
    rows.append(dict(
        s=r.state, y=int(r.year), m=("" if pd.isna(r.measure) else str(r.measure)), d=(r.description or "")[:230], t=r.topic, g=r.domain,
        o={"initiative": "Citizen initiative", "legislative": "Legislative referral"}.get(r.mtype, "Origin not identified"),
        v=round(float(r.vpc), 4), re=None if pd.isna(r.rel_engage) or r.n_on_ballot < 5 else round(float(r.rel_engage), 4),
        ex=None if pd.isna(r.excess) else round(float(r.excess), 4), mg=round(float(r.margin), 2), p=int(bool(r.passed)),
        yv=int(r.yes_votes), nv=int(r.no_votes), pop=int(r.population), n=int(r.n_on_ballot), h=int(bool(r.blank_counts_as_no))))
try:
    _rb = json.load(open("results/robustness_hotbuttons.json")); MIX = f"{100 * _rb['ballots_votes_ratio_gt2'] / _rb['ballots_total']:.0f}%"
except Exception:
    MIX = "a few percent"
meta = dict(n=len(rows), excluded=int(len(ex)), states=int(v.state.nunique()))

TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hot-Button Explorer</title>
<meta name="description" content="Every statewide ballot measure with vote counts, sorted by how many voters turned out per capita, with the margin for or against.">
<style>
:root{--bg:#fcfcfb;--panel:#f4f3f0;--ink:#0b0b0b;--ink2:#52514e;--grid:#e3e2dd;--pos:#2a78d6;--neg:#eb6834;--line:#0b0b0b;--hi:#0b0b0b;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1a1a19;--panel:#242422;--ink:#f0efec;--ink2:#c3c2b7;--grid:#34342f;--pos:#3987e5;--neg:#d95926;--line:#f0efec;--hi:#f0efec;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#1a1a19;--panel:#242422;--ink:#f0efec;--ink2:#c3c2b7;--grid:#34342f;--pos:#3987e5;--neg:#d95926;--line:#f0efec;--hi:#f0efec;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1060px;margin:0 auto;padding:28px 16px 70px}
h1{font-size:1.9rem;margin:.1em 0 .2em}p{margin:.5em 0}.sub{color:var(--ink2)}a{color:var(--pos)}
.controls{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:flex-end;margin:18px 0 10px;padding:12px 14px;background:var(--panel);border-radius:10px}
.controls label{display:flex;flex-direction:column;font-size:.78rem;color:var(--ink2);gap:3px}
select,input[type=search],input[type=range]{font:inherit;font-size:.92rem;color:var(--ink);background:var(--bg);border:1px solid var(--grid);border-radius:7px;padding:5px 8px;min-width:130px}
input[type=range]{padding:0;min-width:160px}
.btn{font:inherit;font-size:.9rem;color:var(--ink);background:var(--bg);border:1px solid var(--grid);border-radius:7px;padding:6px 10px;cursor:pointer}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:10px 0}
.stat{background:var(--panel);border-radius:10px;padding:9px 12px}.stat b{display:block;font-size:1.35rem;line-height:1.15}.stat span{font-size:.78rem;color:var(--ink2)}
#chartwrap{position:relative;margin-top:6px}svg{display:block;width:100%;height:auto}
.axis text{fill:var(--ink2);font-size:11.5px}.grid{stroke:var(--grid);stroke-width:1}.zero{stroke:var(--ink2);stroke-width:1.2}
.lab{fill:var(--ink2);font-size:12px}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.85rem;color:var(--ink2);margin:6px 0}.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.legend i.ln{height:3px;border-radius:2px;vertical-align:3px;width:18px}
#tip{position:absolute;pointer-events:none;background:var(--bg);color:var(--ink);border:1px solid var(--grid);border-radius:9px;padding:9px 12px;font-size:.84rem;max-width:330px;box-shadow:0 4px 18px rgba(0,0,0,.18);display:none;z-index:5}
#tip b{display:block;margin-bottom:2px}#tip .m{color:var(--ink2)}
#pin{margin:8px 0;padding:10px 14px;background:var(--panel);border-radius:10px;font-size:.9rem;display:none}
details{margin:10px 0;font-size:.88rem;color:var(--ink2)}summary{cursor:pointer}.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.85rem}th,td{text-align:left;padding:4px 10px 4px 0;border-bottom:1px solid var(--grid);vertical-align:top}td.n,th.n{text-align:right;white-space:nowrap}
.note{font-size:.84rem;color:var(--ink2)}.qt{width:100%;margin-top:6px}
.pos{color:var(--pos)}.neg{color:var(--neg)}
</style></head><body><main>
<p class="note"><a href="./">&larr; Back to the report</a></p>
<h1>Hot-Button Explorer</h1>
<p class="sub">Every statewide measure with vote counts, sorted by how many voters weighed in. Each bar is one measure; its height is the margin (yes minus no, as a share of votes cast). <span class="pos">Blue</span> = in favor, <span class="neg">orange</span> = against.</p>

<div class="controls" role="group" aria-label="Controls">
<label>Sort by<select id="sort">
<option value="v">Votes per capita (raw)</option>
<option value="re">Engagement vs. the same ballot</option>
<option value="ex">Engagement beyond ballot position</option></select></label>
<label>Order<select id="dir"><option value="1">Hottest first</option><option value="0">Coolest first</option></select></label>
<label>State<select id="f_state"></select></label>
<label>Topic<select id="f_topic"></select></label>
<label>Origin<select id="f_origin"></select></label>
<label>Era<select id="f_era"><option value="">All years</option><option value="1976-1989">1976–1989</option><option value="1990-1999">1990s</option><option value="2000-2009">2000s</option><option value="2010-2019">2010s</option><option value="2020-2024">2020s</option></select></label>
<label>Result<select id="f_res"><option value="">Passed and failed</option><option value="1">Passed</option><option value="0">Failed</option></select></label>
<label>Search<input id="q" type="search" placeholder="e.g. marijuana, tax, abortion"></label>
<label>Show hottest <span id="topn_v" style="color:var(--ink)"></span><input id="topn" type="range" min="25" max="100" value="100" step="1"></label>
<button class="btn" id="reset" type="button">Reset</button>
</div>

<div class="stats" id="stats" aria-live="polite"></div>
<div class="legend"><span><i style="background:var(--pos)"></i>Margin in favor</span><span><i style="background:var(--neg)"></i>Margin against</span><span><i class="ln" style="background:var(--line)"></i>Rolling average margin (is there a slant as you move across?)</span></div>
<div id="chartwrap"><svg id="chart" role="img" aria-label="Bars of margin for or against for each ballot measure, sorted by voter engagement"></svg><div id="tip"></div></div>
<div id="pin"></div>
<p class="note" id="explain"></p>
<div class="tw"><table class="qt" id="qt"></table></div>
<details><summary>View the hottest 25 in the current view as a table</summary><div class="tw"><table id="tbl"></table></div></details>

<h2 style="font-size:1.15rem;margin-top:1.6em">How to read this, and what it can't tell you</h2>
<ul class="note">
<li><b>Votes per capita</b> = votes cast on the measure (yes + no) divided by the state's total resident population that year. It is <i>not</i> turnout among eligible voters (children and non-citizens are in the denominator), and it mostly reflects <i>which election it was</i>: about 96% of the top-decile measures are in presidential years. Use the other two sorts to compare measures on equal footing.</li>
<li><b>Engagement vs. the same ballot</b> = votes on this measure ÷ votes on the most-voted measure on that state-year's ballot (ballots with at least 5 measures). <b>Beyond ballot position</b> removes the small trend with where the measure sits on the list.</li>
<li><b>Margin</b> = (yes − no) ÷ (yes + no), in points. Blank ballots are not in the source counts. <b>Hawaii</b> treats blank ballots as "no" for passage, so a measure can have a positive margin here and still fail there.</li>
<li><b>A "ballot" is a state-year</b>, which can combine a primary or special election with the general election; about __MIX__ of ballots show vote counts that differ by more than 2× between measures, a sign of mixed electorates. That adds noise to the engagement measures.</li>
<li><b>Not shown:</b> California (no vote counts yet) and __EXCLUDED__ measures whose parsed counts disagreed with the stated yes percentage. Data: Wikipedia state lists; Census population estimates. All associations, not causes.</li>
</ul>
</main>
<script>
const DATA = /*DATA*/;
const META = /*META*/;
const $ = id => document.getElementById(id);
const METRIC = {v:{k:"v",name:"votes per capita",fmt:x=>(x*1000).toFixed(0)+" per 1,000"},re:{k:"re",name:"engagement vs. same ballot",fmt:x=>(x*100).toFixed(0)+"% of ballot's top measure"},ex:{k:"ex",name:"engagement beyond ballot position",fmt:x=>(x>=0?"+":"")+(x*100).toFixed(1)+" pts vs expected"}};
const fmtM = x => (x>0?"+":"") + x.toFixed(1);
const esc = s => String(s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let view = [], pinned = null;

function fillSelect(id, values, first){const el=$(id);el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option>${esc(v)}</option>`).join("");}
fillSelect("f_state",[...new Set(DATA.map(d=>d.s))].sort(),"All states");
fillSelect("f_topic",[...new Set(DATA.map(d=>d.t))].sort(),"All topics");
fillSelect("f_origin",[...new Set(DATA.map(d=>d.o))].sort(),"All origins");

function filtered(){
  const m=$("sort").value, st=$("f_state").value, tp=$("f_topic").value, og=$("f_origin").value, era=$("f_era").value, rs=$("f_res").value, q=$("q").value.trim().toLowerCase();
  let a=DATA.filter(d=>d[m]!==null && d[m]!==undefined);
  if(st) a=a.filter(d=>d.s===st); if(tp) a=a.filter(d=>d.t===tp); if(og) a=a.filter(d=>d.o===og);
  if(era){const[lo,hi]=era.split("-").map(Number);a=a.filter(d=>d.y>=lo&&d.y<=hi);}
  if(rs!=="") a=a.filter(d=>d.p===+rs); if(q) a=a.filter(d=>(d.d+" "+d.m+" "+d.t).toLowerCase().includes(q));
  const dir=$("dir").value==="1"?-1:1;
  a.sort((x,y)=>dir*(x[m]-y[m]) || x.y-y.y);
  return a;
}
function ranks(arr){const idx=arr.map((v,i)=>[v,i]).sort((a,b)=>a[0]-b[0]);const r=new Array(arr.length);let i=0;while(i<idx.length){let j=i;while(j+1<idx.length&&idx[j+1][0]===idx[i][0])j++;const avg=(i+j)/2+1;for(let k=i;k<=j;k++)r[idx[k][1]]=avg;i=j+1;}return r;}
function spearman(x,y){if(x.length<8)return null;const a=ranks(x),b=ranks(y),n=a.length,ma=a.reduce((s,v)=>s+v,0)/n,mb=b.reduce((s,v)=>s+v,0)/n;let sa=0,sb=0,sab=0;for(let i=0;i<n;i++){sa+=(a[i]-ma)**2;sb+=(b[i]-mb)**2;sab+=(a[i]-ma)*(b[i]-mb);}return sab/Math.sqrt(sa*sb);}
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:NaN;
const median=a=>{if(!a.length)return NaN;const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2;};

function render(){
  const m=$("sort").value, all=filtered();
  const tn=$("topn"); const maxN=Math.max(all.length,25); tn.max=maxN; if(+tn.value>maxN||tn.dataset.auto!=="0")tn.value=maxN;
  const N=Math.min(+tn.value,all.length); $("topn_v").textContent=N+(N===all.length?" (all)":"");
  view=all.slice(0,N); pinned=null; $("pin").style.display="none";
  // stats
  const mg=view.map(d=>d.mg), fav=view.filter(d=>d.mg>0).length, pass=view.filter(d=>d.p).length;
  const rho=spearman(view.map(d=>d[m]),mg);
  $("stats").innerHTML=[[view.length.toLocaleString(),"measures shown"],[view.length?Math.round(100*fav/view.length)+"%":"–","with a margin in favor"],[view.length?fmtM(median(mg))+" pts":"–","median margin"],[view.length?Math.round(100*pass/view.length)+"%":"–","passed"],[rho===null?"–":(rho>0?"+":"")+rho.toFixed(2),"rank correlation: engagement vs. margin"]].map(([a,b])=>`<div class="stat"><b>${a}</b><span>${b}</span></div>`).join("");
  draw(); quint(m); table();
}
function draw(){
  const svg=$("chart"), W=Math.max(320,$("chartwrap").clientWidth), H=Math.round(Math.min(480,Math.max(300,W*.46)));
  const ml=54, mr=10, mt=10, mb=50, pw=W-ml-mr, ph=H-mt-mb, n=view.length;
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`); svg.setAttribute("width",W); svg.setAttribute("height",H);
  const Y=v=>mt+(100-v)/200*ph, y0=Y(0);
  let g=`<g class="axis">`;
  [-100,-50,0,50,100].forEach(t=>{g+=`<line class="${t===0?'zero':'grid'}" x1="${ml}" x2="${W-mr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${ml-8}" y="${Y(t)+4}" text-anchor="end">${t>0?"+"+t:t}</text>`;});
  g+=`<text class="lab" transform="translate(13 ${mt+ph/2}) rotate(-90)" text-anchor="middle">Margin (points): in favor ↑ · against ↓</text></g>`;
  if(!n){svg.innerHTML=g+`<text x="${W/2}" y="${H/2}" text-anchor="middle" class="lab">No measures match these filters</text>`;return;}
  const bw=pw/n, w=Math.max(bw*0.82,0.7); let pp="",nn="";
  view.forEach((d,i)=>{const x=ml+i*bw+(bw-w)/2, yy=Y(d.mg), top=Math.min(yy,y0), h=Math.max(Math.abs(yy-y0),0.8); const r=`M${x.toFixed(2)} ${top.toFixed(2)}h${w.toFixed(2)}v${h.toFixed(2)}h${(-w).toFixed(2)}z`; if(d.mg>=0)pp+=r; else nn+=r;});
  g+=`<path d="${pp}" fill="var(--pos)" opacity=".85"/><path d="${nn}" fill="var(--neg)" opacity=".85"/>`;
  // rolling average
  const win=Math.max(5,Math.round(n/12)); let pts=[];
  for(let i=0;i<n;i++){const a=Math.max(0,i-(win>>1)), b=Math.min(n-1,i+(win>>1)); let s=0;for(let j=a;j<=b;j++)s+=view[j].mg; pts.push(`${(ml+(i+.5)*bw).toFixed(1)},${Y(s/(b-a+1)).toFixed(1)}`);}
  if(n>=8) g+=`<polyline points="${pts.join(" ")}" fill="none" stroke="var(--bg)" stroke-width="4.5" stroke-linejoin="round"/><polyline points="${pts.join(" ")}" fill="none" stroke="var(--line)" stroke-width="2.2" stroke-linejoin="round"/>`;
  // x axis
  const m=$("sort").value, M=METRIC[m]; g+=`<g class="axis">`;
  (W<560?[0,.5,1]:[0,.25,.5,.75,1]).forEach(f=>{const i=Math.min(n-1,Math.round(f*(n-1))), x=ml+(i+.5)*bw; g+=`<line class="grid" x1="${x}" x2="${x}" y1="${mt+ph}" y2="${mt+ph+5}"/><text x="${Math.min(Math.max(x,ml+30),W-mr-30)}" y="${mt+ph+18}" text-anchor="middle">#${i+1}</text><text x="${Math.min(Math.max(x,ml+40),W-mr-40)}" y="${mt+ph+31}" text-anchor="middle">${esc(M.fmt(view[i][m]))}</text>`;});
  g+=`<text class="lab" x="${ml+pw/2}" y="${H-4}" text-anchor="middle">${$("dir").value==="1"?"hottest → coolest":"coolest → hottest"}${W<560?"":" by "+M.name} (one bar per measure)</text></g>`;
  g+=`<rect id="hl" x="0" y="${mt}" width="${Math.max(bw,2)}" height="${ph}" fill="var(--hi)" opacity=".13" style="display:none"/><rect id="cap" x="${ml}" y="${mt}" width="${pw}" height="${ph}" fill="transparent" style="cursor:crosshair"/>`;
  svg.innerHTML=g;
  const cap=$("cap"), hl=$("hl"), tip=$("tip");
  const idxAt=e=>{const r=svg.getBoundingClientRect(), x=(e.clientX-r.left)*(W/r.width)-ml; return Math.max(0,Math.min(n-1,Math.floor(x/bw)));};
  const show=(i,e)=>{const d=view[i]; hl.style.display="block"; hl.setAttribute("x",ml+i*bw); hl.setAttribute("width",Math.max(bw,2)); tip.innerHTML=card(d,i); tip.style.display="block";
    const wr=$("chartwrap").getBoundingClientRect(); let tx=e.clientX-wr.left+14, ty=e.clientY-wr.top+14; if(tx+340>wr.width)tx=e.clientX-wr.left-344; if(tx<0)tx=4; tip.style.left=tx+"px"; tip.style.top=ty+"px";};
  cap.addEventListener("pointermove",e=>show(idxAt(e),e)); cap.addEventListener("pointerleave",()=>{tip.style.display="none";hl.style.display="none";});
  cap.addEventListener("click",e=>{const i=idxAt(e); pinned=i; const p=$("pin"); p.style.display="block"; p.innerHTML="<b>Pinned:</b> "+card(view[i],i,true);});
}
function card(d,i,inline){
  const pct=(100*d.yv/(d.yv+d.nv)).toFixed(1), m=$("sort").value;
  const eng=[`${(d.v*1000).toFixed(0)} voters per 1,000 residents`, d.re!==null?`${(d.re*100).toFixed(0)}% of its ballot's most-voted measure (${d.n} on ballot)`:`ballot has only ${d.n} measure${d.n===1?"":"s"}`].join(" · ");
  return `<b>#${i+1} · ${esc(d.s)} ${d.y}${d.m?" · "+esc(d.m):""}</b><span class="m">${esc(d.o)} · ${esc(d.t)}</span><br>${esc(d.d)}<br><span class="${d.mg>=0?'pos':'neg'}"><b style="display:inline">${fmtM(d.mg)} pts</b></span> (${pct}% yes of ${(d.yv+d.nv).toLocaleString()} votes) — <b style="display:inline">${d.p?"Passed":"Failed"}</b>${d.h?" (Hawaii: blanks count as no)":""}<br><span class="m">${eng}</span>`;
}
function quint(m){
  const n=view.length, t=$("qt"); if(n<25){t.innerHTML="";$("explain").textContent="Fewer than 25 measures in view; slant statistics are hidden.";return;}
  const q=5, rows=[]; for(let k=0;k<q;k++){const s=view.slice(Math.floor(k*n/q),Math.floor((k+1)*n/q)); rows.push([k,s]);}
  const names=$("dir").value==="1"?["Hottest fifth","2nd","3rd","4th","Coolest fifth"]:["Coolest fifth","2nd","3rd","4th","Hottest fifth"];
  t.innerHTML=`<thead><tr><th>Fifth of measures in view</th><th class="n">n</th><th class="n">Mean margin</th><th class="n">Share against</th><th class="n">Passed</th></tr></thead><tbody>`+rows.map(([k,s])=>`<tr><td>${names[k]}</td><td class="n">${s.length}</td><td class="n">${fmtM(mean(s.map(d=>d.mg)))}</td><td class="n">${Math.round(100*s.filter(d=>d.mg<0).length/s.length)}%</td><td class="n">${Math.round(100*s.filter(d=>d.p).length/s.length)}%</td></tr>`).join("")+`</tbody>`;
  const a=mean(rows[0][1].map(d=>d.mg)), b=mean(rows[4][1].map(d=>d.mg));
  $("explain").textContent=`Mean margin moves from ${fmtM(a)} points in the first fifth to ${fmtM(b)} in the last. Differences of a few points between fifths are well within what chance and state differences produce; the report tests this with ballot fixed effects.`;
}
function table(){
  const t=$("tbl"), rows=view.slice(0,25);
  t.innerHTML=`<thead><tr><th class="n">#</th><th>Measure</th><th>State, year</th><th class="n">Margin</th><th class="n">Per 1,000</th><th>Result</th></tr></thead><tbody>`+rows.map((d,i)=>`<tr><td class="n">${i+1}</td><td>${d.m?esc(d.m)+" — ":""}${esc(d.d.slice(0,120))}</td><td>${esc(d.s)} ${d.y}</td><td class="n ${d.mg>=0?'pos':'neg'}">${fmtM(d.mg)}</td><td class="n">${(d.v*1000).toFixed(0)}</td><td>${d.p?"Passed":"Failed"}</td></tr>`).join("")+`</tbody>`;
}
["sort","dir","f_state","f_topic","f_origin","f_era","f_res"].forEach(id=>$(id).addEventListener("change",()=>{$("topn").dataset.auto="1";render();}));
$("q").addEventListener("input",()=>{$("topn").dataset.auto="1";render();});
$("topn").addEventListener("input",()=>{$("topn").dataset.auto="0";render();});
$("reset").addEventListener("click",()=>{["f_state","f_topic","f_origin","f_era","f_res"].forEach(id=>$(id).value="");$("q").value="";$("sort").value="v";$("dir").value="1";$("topn").dataset.auto="1";render();});
new ResizeObserver(()=>{if(view.length||DATA.length)draw();}).observe($("chartwrap"));
$("topn").dataset.auto="1"; render();
</script></body></html>'''

html = TEMPLATE.replace("/*DATA*/", json.dumps(rows, separators=(",", ":"))).replace("/*META*/", json.dumps(meta)).replace("__EXCLUDED__", str(meta["excluded"])).replace("__MIX__", MIX)
os.makedirs("docs", exist_ok=True)
open("docs/explorer.html", "w").write(html)
print("wrote docs/explorer.html", len(html), "bytes;", len(rows), "measures")
