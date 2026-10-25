"""Parse Wikipedia state ballot-measure list pages into one tidy CSV.

Each page is a series of <table class="wikitable"> elements preceded by a
heading carrying the election year. Column names vary by state, so columns are
matched by keyword rather than position.
"""
import re, sys, glob, os, csv
from lxml import html as H

RAW = "data/raw/wiki"

def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", s)          # footnote markers
    return " ".join(s.split())

def num(s):
    m = re.search(r"\d[\d,]*", s or "")
    return int(m.group().replace(",", "")) if m else None

def pct(s):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s or "")
    return float(m.group(1)) if m else None

def header_cells(table):
    """Return flattened header labels, expanding colspan, merging stacked header rows."""
    rows = table.findall(".//tr")
    labels = []
    for r in rows:
        if r.findall("./td"):
            break
        cells = r.findall("./th")
        if not cells:
            continue
        row = []
        for c in cells:
            span = int(c.get("colspan", 1))
            row += [clean(c.text_content()).lower()] * span
        labels.append(row)
    if not labels:
        return []
    width = max(len(r) for r in labels)
    out = []
    for i in range(width):
        parts = []
        for r in labels:
            if i < len(r) and r[i] not in parts:
                parts.append(r[i])
        out.append(" ".join(parts))
    return out

def colmap(hdr):
    m = {}
    for i, h in enumerate(hdr):
        if h.startswith(("measure name", "no.", "meas", "name", "proposition", "number", "measure")) and "name" not in m:
            m["name"] = i
        elif any(k in h for k in ("description", "title", "summary", "subject")) and "desc" not in m:
            m["desc"] = i
        elif any(k in h for k in ("status", "result", "passed", "outcome")) and "result" not in m:
            m["result"] = i
        elif re.search(r"\byes\b", h) and "%" not in h and "yes" not in m:
            m["yes"] = i
        elif re.search(r"\bno\b", h) and "%" not in h and "no" not in m:
            m["no"] = i
        elif "% yes" in h or ("yes" in h and "%" in h):
            m["yespct"] = i
        elif h.startswith("type") or "origin" in h or "referred" in h:
            m["type"] = i
    return m

def expand_row(tr):
    """Expand a data row to cell text honouring colspan (rowspan ignored)."""
    out = []
    for c in tr.findall("./td") + tr.findall("./th"):
        pass
    cells = [c for c in tr if c.tag in ("td", "th")]
    for c in cells:
        span = int(c.get("colspan", 1))
        out += [clean(c.text_content())] * span
    return out

def classify_type(*texts):
    t = " ".join(x for x in texts if x).lower()
    if re.search(r"\b(init|initiative|citizen|cit)\b|initiated", t) and "legislat" not in t:
        return "initiative"
    if re.search(r"\b(leg|legislative|legislature|referred|referral|legislatively)\b", t):
        return "legislative"
    return "unknown"

def parse_page(path, state):
    doc = H.fromstring(open(path, encoding="utf-8").read())
    rows_out = []
    year = None
    section = ""
    for el in doc.iter("h2", "h3", "h4", "table"):
        if el.tag != "table":
            txt = clean(el.text_content())
            m = re.search(r"\b(1[89]\d\d|20\d\d)\b", txt)
            if m and len(txt) < 40:
                year = int(m.group(1))
            elif el.tag == "h2" and not m:
                section = txt.lower()
            continue
        if "wikitable" not in (el.get("class") or ""):
            continue
        hdr = header_cells(el)
        cm = colmap(hdr)
        if "yes" not in cm and "yespct" not in cm and "result" not in cm:
            continue
        for tr in el.findall(".//tr"):
            if tr.findall("./td") == []:
                continue
            cells = expand_row(tr)
            def g(k):
                i = cm.get(k)
                return cells[i] if i is not None and i < len(cells) else ""
            name, desc, res = g("name"), g("desc"), g("result")
            yes, no = num(g("yes")), num(g("no"))
            yp = pct(g("yes")) or pct(g("yespct"))
            if yp is None and yes and no:
                yp = round(100 * yes / (yes + no), 2)
            rl = res.lower()
            passed = True if re.search(r"pass|approv|adopt|yes|carried", rl) else (False if re.search(r"fail|reject|defeat|no\b|not", rl) else None)
            if passed is None and yp is not None:
                passed = yp > 50
            rows_out.append(dict(state=state, year=year, measure=name, description=desc,
                                 passed=passed, yes_votes=yes, no_votes=no, yes_pct=yp,
                                 raw_type=g("type"), section=section,
                                 mtype=classify_type(g("type"), section, name)))
    return rows_out

if __name__ == "__main__":
    path, state = sys.argv[1], sys.argv[2]
    rows = parse_page(path, state)
    print(len(rows), "rows")
    for r in rows[:5]:
        print(r)


def parse_list_page(path, state):
    """California-style pages: <h3>election date</h3> followed by <ul><li>NUM – Passed/Failed – Title</li></ul>."""
    doc = H.fromstring(open(path, encoding="utf-8").read())
    out = []
    for h in doc.iter("h3"):
        m = re.search(r"\b(19|20)\d\d\b", h.text_content())
        if not m:
            continue
        year = int(m.group())
        n = h.getparent().getnext()
        while n is not None and not (n.tag == "div" and "mw-heading" in (n.get("class") or "")):
            if n.tag == "ul":
                for li in n.findall("./li"):
                    txt = clean(li.text_content())
                    mm = re.match(r"^(\S+)\s*[–-]\s*(Passed|Failed)\s*[–-]\s*(.+)$", txt)
                    if not mm:
                        continue
                    title = mm.group(3)
                    out.append(dict(state=state, year=year, measure=mm.group(1), description=title,
                                    passed=mm.group(2) == "Passed", yes_votes=None, no_votes=None, yes_pct=None,
                                    raw_type="", section="", mtype=classify_ca(title)))
            n = n.getnext()
    return out


def classify_ca(title):
    t = title.lower()
    if "initiative" in t:
        return "initiative"
    if "legislative" in t or "legislature" in t:
        return "legislative"
    return "unknown"
