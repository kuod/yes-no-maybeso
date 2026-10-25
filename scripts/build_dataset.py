"""Build data/measures.csv (measure level) and data/state_year.csv (IRI aggregate).

Run from repo root:  python3 -I scripts/build_dataset.py
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import parse_wiki as P

RAW = "data/raw/wiki"
FIRST, LAST = 1976, 2024  # last 50 years of completed general-election cycles

TABLE_PAGES = {
    "Alaska": "Alaska", "Arizona": "List_of_Arizona_ballot_propositions", "Colorado": "List_of_Colorado_ballot_measures",
    "Florida": "Florida", "Hawaii": "Hawaii", "Michigan": "Michigan", "Missouri": "List_of_Missouri_ballot_measures",
    "Montana": "Montana", "Ohio": "Ohio", "Oklahoma": "Oklahoma", "Oregon": "List_of_Oregon_ballot_measures",
    "South Dakota": "South_Dakota", "Washington": "List_of_Washington__state__ballot_measures", "Wyoming": "Wyoming",
    "District of Columbia": "DC",
}
CA_LIST = ["CA1970", "CA1980", "CA1990", "CA2000"]
CA_TABLE = ["CA2010", "CA2020"]


def collect():
    rows = []
    for state, f in TABLE_PAGES.items():
        rows += P.parse_page(f"{RAW}/{f}.html", state)
    for f in CA_LIST:
        rows += P.parse_list_page(f"{RAW}/{f}.html", "California")
    for f in CA_TABLE:
        rows += P.parse_page(f"{RAW}/{f}.html", "California")
    return pd.DataFrame(rows)


# --- topic: first matching rule wins, ordered from most to least specific -----------------
TOPICS = [
    ("social", r"abortion|marriage|same[- ]sex|gay\b|lgbt|transgender|gender|marijuana|cannabis|hemp|psilocybin|drugs?\b|gambl|casino|lotter|bingo|racing|"
               r"firearm|guns?\b|weapon|concealed|immigra|english|official (state )?language|affirmative action|discriminat|equal rights|civil rights|"
               r"prayer|religio|euthanasia|assisted suicide|death with dignity|obscen|pornograph|tobacco|cigarette|smok|alcohol|liquor|sunday|animal|cruelty|hunting|trapping|dogs?\b|homosexual|stem cell|privacy"),
    ("criminal justice", r"death penalty|capital punishment|crimes?\b|criminal|victims?\b|bail|sentenc|prison|parole|felon|police|law enforcement|three strikes|juvenile|"
                         r"incarcerat|sex offender|probation|jur(y|ies)|marsy|rights of (the )?accused|misdemeanor|correctional"),
    ("education", r"schools?\b|education|college|universit|students?\b|teachers?\b|tuition|charter|voucher"),
    ("environment & resources", r"environment|wildlife|conserv|water\b|forest|parks?\b|wilderness|pollut|clean air|energy|nuclear|oil\b|gas\b|coal|solar|renewable|"
                                r"climate|fishing|fish\b|land use|growth|open space|recycl|bottle|container|mining|wolf|bear\b"),
    ("health & welfare", r"health|medic|hospital|insurance|welfare|nursing|disabled|disabilit|seniors?\b|elder|minimum wage|workers.? comp|"
                         r"labor|union|right[- ]to[- ]work|employ|wages?\b|housing|homeless|rent control|renters?\b"),
    ("taxes & budget", r"\btax|bonds?\b|debt|budget|revenue|spending|appropriat|fees?\b|assessment|reserve|funds?\b|financ|"
                       r"surplus|rebate|exemption|levy|mill\b|gann|proposition 13|tabor"),
    ("transportation & infrastructure", r"transport|highway|roads?\b|rail|transit|bridge|airport|toll|infrastructure"),
    ("elections & government", r"term limit|redistrict|reapportion|campaign|ballot|primary|election|voter|voting|suffrage|initiative|"
                               r"referendum|legislat|governor|lieutenant|judges?\b|judicial|courts?\b|ethics|lobby|salar|pay raise|"
                               r"auditor|secretary of state|constitutional convention|home rule|civil service|public employee|pension|state officer|"
                               r"count(y|ies)|municipal|cit(y|ies)|sheriff|annex|capital\b|office|commission|congress|reapportion"),
]
ECON = {"taxes & budget", "transportation & infrastructure", "health & welfare"}
SOCIAL = {"social", "criminal justice"}


def topic(desc):
    d = (desc or "").lower()
    for name, rx in TOPICS:
        if re.search(rx, d):
            return name
    return "other"


def broad(t):
    if t in ECON:
        return "economic"
    if t in SOCIAL:
        return "social"
    if t == "elections & government":
        return "political process"
    if t in {"environment & resources", "education"}:
        return t.split(" ")[0]
    return "other"


# --- wording features ---------------------------------------------------------------------
RESTRICT = (r"\b(?:prohibit\w*|bans?|banned|banning|forbid\w*|limit\w*|restrict\w*|repeal\w*|eliminat\w*|abolish\w*|caps?|capped|capping|"
            r"reduc\w*|cuts?|cutting|prevent\w*|term limits?|require[sd]? (?:a )?(?:two-thirds|supermajority|voter))\b")
EXPAND = (r"\b(?:authoriz\w*|allow\w*|permit\w*|legaliz\w*|establish\w*|creat\w*|provid\w*|guarantee\w*|protect\w*|"
          r"expand\w*|extend\w*|issu\w*|enact\w*|grant\w*)\b")
TAXWORD = r"\b(?:tax|taxes|taxation|fee|fees|bond|bonds|debt|levy|assessment)\b"


def syllables(w):
    w = w.lower()
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1:
        n -= 1
    return max(n, 1)


def flesch(text):
    words = re.findall(r"[A-Za-z']+", text)
    if len(words) < 3:
        return None
    sents = max(len(re.findall(r"[.!?]+", text)), 1)
    syl = sum(syllables(w) for w in words)
    return 206.835 - 1.015 * len(words) / sents - 84.6 * syl / len(words)


def features(df):
    d = df.description.fillna("")
    df["n_words"] = d.str.split().str.len()
    df["flesch"] = d.map(flesch)
    low = d.str.lower()
    df["restrictive"] = low.str.contains(RESTRICT)
    df["expansive"] = low.str.contains(EXPAND)
    df["mentions_tax_debt"] = low.str.contains(TAXWORD)
    df["is_amendment"] = low.str.contains(r"amendment|constitution")
    df["mentions_increase"] = low.str.contains(r"\b(?:increase|raise|new tax|impose)")
    df["mentions_repeal"] = low.str.contains(r"\b(?:repeal|eliminat|abolish|rescind)")
    df["has_year_title"] = low.str.contains(r"act of \d{4}|\bact\b")
    return df


def infer_type(df):
    """Fill 'unknown' origin from description text when it states it; otherwise leave unknown."""
    low = df.description.fillna("").str.lower()
    ini = low.str.contains(r"\binitiative\b|citizen[- ]initiated|\binitiated\b")
    leg = low.str.contains(r"legislative|legislature|referred by|legislatively|\bleg\b")
    m = df.mtype.copy()
    m[(m == "unknown") & ini & ~leg] = "initiative"
    m[(m == "unknown") & leg & ~ini] = "legislative"
    return m


def main():
    df = collect()
    df = df[df.year.between(FIRST, LAST) & df.passed.notna()].copy()
    df["passed"] = df.passed.astype(bool)
    df["description"] = df.description.fillna("").str.strip()
    df = df[df.description.str.len() > 3]
    df = df.drop_duplicates(["state", "year", "measure", "description"])
    df["mtype"] = infer_type(df)
    df["topic"] = df.description.map(topic)
    df["domain"] = df.topic.map(broad)
    df = features(df)
    df["decade"] = (df.year // 10) * 10
    cols = ["state", "year", "decade", "measure", "description", "mtype", "topic", "domain", "passed", "yes_votes", "no_votes", "yes_pct",
            "n_words", "flesch", "restrictive", "expansive", "mentions_tax_debt", "is_amendment", "mentions_increase", "mentions_repeal", "has_year_title"]
    os.makedirs("data", exist_ok=True)
    df[cols].sort_values(["state", "year", "measure"]).to_csv("data/measures.csv", index=False)

    iri = pd.read_excel("data/raw/iri_state_year.xls", sheet_name=1)
    iri = iri.rename(columns={"State": "state", "Year": "year", "number_all": "initiatives", "number_approved": "approved"})
    iri[iri.year.between(FIRST, LAST)].to_csv("data/state_year.csv", index=False)
    print(df.groupby("state").size().to_string())
    print("TOTAL", len(df), "| pass rate", round(df.passed.mean(), 3))
    print(df.mtype.value_counts().to_string())
    print(df.topic.value_counts().to_string())


if __name__ == "__main__":
    main()
