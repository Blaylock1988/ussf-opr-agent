"""Approval data, tokenization and term classification shared by lint, acronyms and style scripts.

Approval layers (highest wins):
  1. user list: <work>/approved/{common_acronyms,approved_abbreviations}.json (replaces layer 3)
  2. AFPC list: <work>/approved/afpc_acronyms.json or reference/data/afpc_acronyms.json (always approved)
  3. bundled default: CFC Writing Guide Attachments (reference/data/*.json)
Plus: widely-known media acronyms (judgment) and the draft's own Sec X definitions.
The glossary is a decoder only and never approves anything.
"""
import re
from pathlib import Path

from common import DATA_DIR, load_json

SYMBOLS = {"&", "#", "+", "<", ">", "%", "$", "~"}

# Widely known from popular media / news. Subjective by design; lint reports these as "judgment".
MEDIA_ACRONYMS = {
    "AI", "CIA", "FBI", "NASA", "NATO", "GPS", "UN", "EU", "POTUS", "VPOTUS", "IRS", "TSA", "FEMA", "DHS",
    "NSA", "DoD", "USA", "UK", "ISIS", "COVID", "IT", "HR", "CEO", "PhD", "MBA", "STEM", "TV", "PC", "IED",
    "UAV", "ICBM", "NFL", "NBA", "WMD", "CDC", "FAA", "NOAA", "IRS", "DEA", "ATF", "EPA", "SEC",
}

# Shorthand seen in OPR history that is NOT on the CFC list, with the approved replacement.
KNOWN_UNAPPROVED = {
    "jt": "Jt", "gov't": "govt", "lgst": "lrgst", "ntwk": "ntwrk", "mos": "mths", "mo": "mth",
    "spc": "(spell out: space)", "upd": "(spell out: update)", "elim'd": "(spell out: eliminated)",
    "dev'd": "dvlp'd", "incrs'd": "incr'd", "decrs'd": "decr'd", "mntr'd": "(spell out: monitored)",
    "req'ts": "rqmts", "reqs": "rqmts", "equip't": "equip", "annly": "(spell out: annually)",
    "redux": "(spell out: reduction)", "prcs": "(spell out)", "nxt": "(spell out: next)",
    "crses": "crs (plural: crses is not listed; spell out: courses)", "dvlpmnt": "dvlp(mnt)",
    "mgmnt": "mgmt", "prgrm": "prgm", "trg": "trng", "tng'd": "trn'd", "qb'd": "(banned verb)",
}

GRADE_GROUP = re.compile(
    r"^(O-\d{1,2}|E-\d|FGO|CGO|SNCO|NCO|Maj|Majs|Major|Majors|Capt|Capts|Captain|Captains|Lt|Lts|Col|Cols|"
    r"Lt ?Cols?|Lieutenants?|Colonels?|Maj\(S\)|Lt Col\(S\)|Col\(S\)|Capt\(S\))", re.I)
UNIT_TYPES = ["ABG", "ABW", "STS", "SOPS", "SWS", "SDS", "SCS", "EWS", "NWS", "ISRS", "CYS", "FSS", "SFS",
              "LRS", "CES", "CONS", "CPTS", "OG", "MSG", "MDG", "OSS", "RS", "TES", "WPS", "CTS", "SPS", "SLS",
              "SBD", "SYD", "AF", "AEW", "AW", "Sq", "sq", "Gp", "Wg", "Del", "DEL", "MD", "SD"]
VAGUE_GROUPS = {"officers", "officer", "mbrs", "members", "personnel", "prsnl", "people", "guardians", "airmen"}
# push/strat scaffolding that every strat line shares; a repeat of these isn't a board-visible echo
STANDOUT_STOPWORDS = {"staff", "command", "school", "squadron", "delta", "soonest", "promote", "after", "their", "there",
                      "which", "while", "every", "first", "since", "today", "ready", "place", "needs", "must"}


def _load_layer(path):
    return load_json(path) if Path(path).is_file() else None


class Approvals:
    def __init__(self, work_dir=None):
        work = Path(work_dir) / "approved" if work_dir else None
        user_common = _load_layer(work / "common_acronyms.json") if work else None
        user_abbr = _load_layer(work / "approved_abbreviations.json") if work else None
        self.common_source = (user_common or load_json(DATA_DIR / "common_acronyms.json"))
        self.abbr_source = (user_abbr or load_json(DATA_DIR / "approved_abbreviations.json"))
        self.common = self.common_source["entries"]  # ACR -> [meanings]
        self.afpc = {}
        for p in ([work / "afpc_acronyms.json"] if work else []) + [DATA_DIR / "afpc_acronyms.json"]:
            layer = _load_layer(p)
            if layer:
                self.afpc.update(layer["entries"])
        self.abbr = {}  # exact form -> entry
        for e in self.abbr_source["entries"]:
            for f in e["forms"]:
                self.abbr.setdefault(f, e)
        self.abbr_lower = {}
        for f in self.abbr:
            self.abbr_lower.setdefault(f.lower(), []).append(f)
        self.d_forms = {}  # lower -> canonical
        for e in self.abbr_source["entries"]:
            for d in e.get("d_forms", []):
                self.d_forms[d.lower()] = d
            if e["pos"] == "verb_form":
                for f in e["forms"]:
                    self.d_forms[f.lower()] = f
        # Space Force / joint structure every officer is expected to know (accepted across all boards).
        self.structure = {}
        for p in [DATA_DIR / "ussf_structure.json"] + ([work / "ussf_structure.json"] if work else []):
            layer = _load_layer(p)
            for e in (layer or {}).get("entries", []):
                for a in [e["acr"]] + e.get("aliases", []):
                    self.structure.setdefault(a, []).append(e["name"])
        gl = _load_layer(DATA_DIR / "glossary.json")
        self.glossary = gl["entries"] if gl else {}
        self.glossary_abbr = {k.lower(): v for k, v in self.glossary.items()
                              if any(m["type"] == "abbreviation" for m in v)}

    # ---------------------------------------------------------- acronyms
    def acronym_status(self, acr, declared_meaning=None, category=None):
        """Return (status, detail): approved | afpc | structure | category | media | needs_definition.

        Approval is per meaning: an acronym listed by the command guide or AFPC is approved only when
        used with a listed meaning. AFPC also approves whole categories (organizations, platforms,
        office symbols, ranks, symbols/measurements); those are judgment calls recorded by the drafter
        in draft['acronym_categories'].
        """
        for status, table in (("approved", self.common), ("afpc", self.afpc), ("structure", self.structure)):
            listed = table.get(acr)
            if listed and (not declared_meaning or any(_same_meaning(declared_meaning, m) for m in listed)):
                return status, "; ".join(listed)
        if category:
            return "category", f"AFPC approved category: {category}"
        listed = self.common.get(acr, []) + self.afpc.get(acr, []) + self.structure.get(acr, [])
        if listed:
            return "needs_definition", f"listed as '{'; '.join(listed)}', used here as '{declared_meaning}'"
        if acr in MEDIA_ACRONYMS:
            return "media", "widely known (judgment)"
        return "needs_definition", self.glossary_hint(acr)

    def glossary_hint(self, term):
        hits = self.glossary.get(term) or self.glossary.get(term.upper()) or []
        return "glossary: " + "; ".join(m["long"] for m in hits) if hits else "not in glossary"

    # ---------------------------------------------------------- abbreviations
    def abbreviation_status(self, tok, line_start=False):
        """Return (status, detail) for a lowercase-ish shorthand token, or (None, None) if not shorthand."""
        bare = tok
        if tok in self.abbr:
            return "approved", self.abbr[tok]["meaning"]
        # allowed suffixes on listed forms: 's, s, es ('d handled below)
        for suf in ("'s", "es", "s"):
            if tok.endswith(suf) and tok[: -len(suf)] in self.abbr:
                e = self.abbr[tok[: -len(suf)]]
                if suf in ("s", "es") and e["pos"] in ("verb", "verb_form") and "noun" not in e["meaning"]:
                    if not _verb_also_noun(e["meaning"]):
                        return "error", f"-{suf} cannot be added to an abbreviated verb ({tok[:-len(suf)]} = {e['meaning']})"
                return "approved", e["meaning"]
        low = tok.lower()
        if low.endswith("'d"):
            if low in self.d_forms:
                canon = self.d_forms[low]
                if tok == canon or (line_start and tok == canon[0].upper() + canon[1:]):
                    return "approved", f"{canon}"
                if tok.lower() == canon.lower() and tok[0].isupper() and not line_start and canon[0].islower():
                    return "error", f"write exactly as listed: {canon}"
                return "approved", canon
            if low in KNOWN_UNAPPROVED:
                return "error", f"not approved; use {KNOWN_UNAPPROVED[low]}"
            return "error", f"-'d needs an approved verb base; '{tok[:-2]}' is not on the approved list"
        if low in self.abbr_lower:
            forms = self.abbr_lower[low]
            title_cased = any(f[0].islower() and f[0].upper() + f[1:] == tok for f in forms)
            if line_start and title_cased:
                return "approved", self.abbr[forms[0]]["meaning"]
            if title_cased:  # e.g. "Spt Tm of the Qtr" inside an award or proper name
                return "judgment", f"listed as {' or '.join(forms)}; capitalize only inside a proper name/title"
            return "error", f"write exactly as listed: {' or '.join(forms)}"
        stem = re.sub(r"(?:'s|s|es)$", "", low)
        if low in KNOWN_UNAPPROVED or stem in KNOWN_UNAPPROVED:
            return "error", f"not approved; use {KNOWN_UNAPPROVED.get(low) or KNOWN_UNAPPROVED[stem]}"
        if low in self.glossary_abbr or stem in self.glossary_abbr:
            hits = self.glossary_abbr.get(low) or self.glossary_abbr.get(stem)
            return "error", f"not on the approved list (glossary: {'; '.join(m['long'] for m in hits)}); spell out"
        if re.search(r"[a-z]'[a-z]", low) and not low.endswith("'s"):
            return "error", "apostrophe contraction not on the approved list; spell out"
        letters = re.sub(r"[^a-z]", "", low)
        if re.fullmatch(r"[a-z']+", low) and len(letters) >= 2 and not re.search(r"[aeiouy]", letters) \
                and tok == tok.lower():
            return "error", "looks like an unapproved abbreviation (no vowels); spell out or use an approved form"
        return None, None


def _same_meaning(a, b):
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower().replace("united states", "us"))
    return norm(a) == norm(b) or norm(a) in norm(b) or norm(b) in norm(a)


def _verb_also_noun(meaning):
    return any(w in meaning for w in ("support", "award", "change", "review", "transfer", "target",
                                     "schedule", "estimate", "evaluation", "organization", "qualification",
                                     "certification", "recommendation", "reorganization", "deployment",
                                     "development", "simulator", "publication", "regulation"))


# ---------------------------------------------------------------- tokenization

TOKEN = re.compile(r"[A-Za-z0-9&'#$%+<>.~()/-]+")


def tokens(text):
    """Split an OPR line into (token, start_index) pairs, peeling 'f/' and 'w/' prefixes and separators."""
    out = []
    work = text.replace("--", "  ")
    for m in TOKEN.finditer(work):
        tok, start = m.group(0), m.start()
        # peel leading "- " bullet dash handled by regex (lone "-")
        if tok == "-":
            continue
        pieces = _split_token(tok)
        offset = 0
        for p in pieces:
            idx = tok.find(p, offset)
            out.append((p, start + max(idx, 0)))
            offset = max(idx, 0) + len(p)
    return out


def _split_token(tok):
    tok = tok.strip(".,;:!?()")
    if not tok:
        return []
    for pre in ("w/in", "w/o", "f/", "w/", "b/w"):
        if tok.startswith(pre) and len(tok) > len(pre) and pre not in ("w/in", "w/o", "b/w"):
            return [pre] + _split_token(tok[len(pre):])
    if tok in ("f/", "w/", "w/in", "w/o", "b/w", "s/w", "h/w", "24/7", "stan/eval") or re.fullmatch(r"#?\d+/\d+", tok):
        return [tok]
    if re.fullmatch(r"[A-Za-z0-9]+/CC", tok):
        # SFK/CC is one office symbol; sq/CC is an abbreviation plus the CC billet
        return [tok] if is_acronym(tok[:-3]) else [tok[:-3], "CC"]
    if "/" in tok:
        return [p for part in tok.split("/") for p in _split_token(part)]
    return [tok]


def is_acronym(tok):
    if re.fullmatch(r"(MD|SD)\d+", tok):
        return False  # designator error is reported separately (MD 5)
    core = re.sub(r"(?:'s|s)$", "", tok)
    if tok.startswith("#") or re.fullmatch(r"[A-Z]-\d+s?", tok):
        return False  # strat ratio or grade (O-4s)
    if re.fullmatch(r"[A-Z][A-Za-z]*\d[A-Za-z0-9]*", core):
        return True  # C2, NC3, FY28, C4ISR
    return len(re.findall(r"[A-Z]", core)) >= 2


def acronym_core(tok):
    """STOs -> STO, DAF's -> DAF, FY28 -> FY, NC3 stays NC3 (listed with the digit)."""
    t = re.sub(r"'s$", "", tok)
    t = re.sub(r"/CC$", "", t)  # SFI/CC -> SFI (the /CC billet suffix is approved)
    t = re.sub(r"-(level|wide|led|based|class|grade|equivalent|run)$", "", t)  # SES-level -> SES
    if re.fullmatch(r"[A-Z&]{2,}[a-z]?s", t) and not t.endswith("SS"):
        t = t[:-1]
    m = re.fullmatch(r"(FY|CY|Q)\d+", t)
    return m.group(1) if m else t


def numbers_in(text, categorized=False):
    """Metric numbers in a line, normalized, excluding strat ratios, designators, labels and times.

    With categorized=True, returns (category, value, raw) tuples: currency ($16B -> 16B), percent (30%),
    or count (517, 9.5K). A $5B budget and 5 awards are different metrics, so duplicates are compared
    only within one category.
    """
    t = _strip_labels(text)
    out = []
    for m in re.finditer(r"(\$?)(\d[\d,]*(?:\.\d+)?)([KMB](?![A-Za-z]))?(%?)", t):
        value = m.group(2).replace(",", "").rstrip(".")
        if not categorized:
            out.append(value)
            continue
        cat = "currency" if m.group(1) else ("percent" if m.group(4) else "count")
        out.append((cat, value + (m.group(3) or ""), m.group(0)))
    # spelled-out counts ("four divisions") still count toward the repeat rules; "one" is too often a pronoun
    for m in re.finditer(r"\b(" + "|".join(SMALL_WORDS) + r")\b", t, re.I):
        value = str(SMALL_WORDS.index(m.group(1).lower()) + 2)
        out.append(("count", value, m.group(0)) if categorized else value)
    return out


SMALL_WORDS = ["two", "three", "four", "five", "six", "seven", "eight", "nine"]
PLACEHOLDER = re.compile(r"\$\[[^\[\]\n]*\][KMB]?|(?<!#)\[(?![NM]\])[^\[\]\n]*\]")
UNIT_WORDS = {"hr", "hrs", "hour", "hours", "min", "mins", "sec", "day", "days", "wk", "wks", "week", "weeks", "mo", "mos",
              "mth", "mths", "month", "months", "yr", "yrs", "year", "years", "mi", "ft", "lb", "lbs", "gal", "km", "nm",
              "mph", "psi", "rpm", "in", "pct", "x"}


def mask_placeholders(text):
    """Blank out [placeholders] (except the strat's #[N]/[M]) so no scan reads them as acronyms or numbers."""
    return PLACEHOLDER.sub("…", text)


def small_number_issues(text):
    """Figures the T&Q would spell out (one-nine as standalone counts) and 4+ digit figures missing the comma.

    Exempt: money, percents, units of measure and unit modifiers (5-wk, 3 mi), multipliers (8x), ratios, strats,
    designators and dates, and every number in a line that also carries a count of 10 or more (a related series).
    """
    t = _strip_labels(mask_placeholders(text))
    counts = [m for m in re.finditer(r"(?<![\w$#.,/:-])(\d[\d,]*)(?![\d.,%:/]|[KMB]\b|x\b|-\w|\+)", t)]
    if any(int(m.group(1).replace(",", "")) >= 10 for m in counts):
        small = []
    else:
        def next_word(m):
            return re.sub(r"[^a-z]", "", (t[m.end():].split() or [""])[0].lower())
        small = [m.group(1) for m in counts if m.group(1).isdigit() and 1 <= int(m.group(1)) <= 9 and next_word(m) not in UNIT_WORDS]
    no_comma = [m.group(1) for m in counts if re.fullmatch(r"\d{4,}", m.group(1)) and not 1900 <= int(m.group(1)) <= 2100]
    return small, no_comma


# 'cut over 2,317' / 'turned over 40' are phrasal verbs, not an estimate
ROUND_QUALIFIER = re.compile(r"(?:\b(?:(?<!cut )(?<!turned )(?<!handed )(?<!took )(?<!carried )(?<!switched )(?<!changed )(?<!rolled )over"
                             r"|more than|nearly|almost|approx|about)\s+|~\s*)$", re.I)


def round_numbers(text):
    """Counts that read as estimated: '500+', 'over 300', '1,000'. Precise figures (517) read as measured."""
    t = _strip_labels(text)
    hits = []
    for m in re.finditer(r"(?<![\w$.,])(\d[\d,]*)(\+?)(?![\d.,]*[%KMB\d])", t):
        raw, n = m.group(0), int(m.group(1).replace(",", ""))
        q = ROUND_QUALIFIER.search(t[:m.start()])
        if n >= 10 and (m.group(2) or q or (n >= 100 and n % 100 == 0 and not 1900 <= n <= 2100)):
            hits.append((q.group(0) if q else "") + raw)
    return hits


def _strip_labels(text):
    t = text
    t = re.sub(r"#\d+/\d+", " ", t)                              # stratifications
    t = re.sub(r"\b(MD|SD|DEL|Del|SYD|MD\s|SD\s)\s?\d+\b", " ", t)  # unit designators
    t = re.sub(r"\b[A-Z]{1,6}-?\d+[A-Z]*s?\b", " ", t)             # FY28, NC3, C2, O-4(s), E-7 labels
    t = re.sub(r"\b\d+\s(?:" + "|".join(UNIT_TYPES) + r")\b", " ", t)  # 61 ABG, 4 SOPS designators
    t = re.sub(r"\b24/7\b", " ", t)
    t = re.sub(r"\b[A-Z]{3,}(?:\s[A-Z]{3,})*\s\d{2}\b", " ", t)    # EXERCISE NAME 25
    return t
