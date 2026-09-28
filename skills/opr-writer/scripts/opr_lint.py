"""Lint an OPR draft against the form, the command writing guide lists, and the user's hard rules.

Severities: error (must fix), warning (should fix), judgment (Claude/user decides), info.
Every alternate and spare is also audited against the whole OPR (rule 'guard'); see guard_candidates.
Usage:  opr_lint.py draft.json [--json] [--history history.json] [--no-guard]
Exit code 1 when any error is found.
"""
import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import (DATA_DIR, Ruler, iter_lines, load_form, load_json, load_verbs, normalize_spaces, text_hash,
                    utf8_stdout)
from audience import load_terms
from opr_acronyms import build_remarks, used_acronyms
from rules import (GRADE_GROUP, STANDOUT_STOPWORDS, SYMBOLS, VAGUE_GROUPS, Approvals, acronym_core, is_acronym,
                   mask_placeholders, numbers_in, round_numbers, small_number_issues, tokens)


IRREGULAR_BASES = {"lead", "drive", "build", "write", "run", "oversee", "teach", "win", "make", "keep", "hold", "bring",
                   "seek", "undertake", "overcome", "fight", "sell", "grow", "find", "give", "set", "cut", "draw",
                   "begin", "choose", "meet", "sweep", "rebuild", "rewrite", "uphold", "stand"}
REFIT = "run `opr.py fit <draft.json> --write`"
# "NSC Schriever awd nominee", "Schriever nom", "FGOY": award names for the text-based double-credit check
AWARD_NAME = re.compile(r"\b((?:[A-Z][A-Za-z0-9&]*\s+){0,2}[A-Z][A-Za-z0-9&]*)\s+(?:awd|award|nom|nominee|nomination)s?\b")
AWARD_ACRONYM = re.compile(r"\b((?:[A-Z]{2,4})O[YQ])\b")


def stale_fits(draft, form):
    """Compare each 'fitted' string with its 'text' and the text fingerprint stored at fit time.

    - 'fitted' changed but 'text' didn't (hash still matches): a hand edit of 'fitted'. ERROR, because the next
      fit rebuilds 'fitted' from 'text' and silently drops the fix.
    - 'text' changed since the fit: normal editing, pending a refit. WARNING.
    """
    items = [(f"{k}[{i + 1}]", line) for k, i, line in iter_lines(draft, form)]
    items += [(f"spares[{n + 1}]", sp) for n, sp in enumerate(draft.get("spares", []))]
    out = []
    for where, line in items:
        fitted = line.get("fitted")
        if not fitted or normalize_spaces(fitted) == normalize_spaces(line["text"]):
            continue
        if line.get("fit_hash") == text_hash(line["text"]):
            out.append(("error", "fit", where, f"'fitted' was hand-edited ('{normalize_spaces(fitted)}'); the next fit would drop it. "
                                               "Move the change into 'text' through the skill, then refit; never hand-edit draft.json"))
        else:
            out.append(("warning", "fit", where, f"'text' changed since the last fit; {REFIT}"))
    return out


class Linter:
    def __init__(self, draft, form, work_dir, history=None, ruler=None):
        self.d, self.form, self.work = draft, form, Path(work_dir)
        self.ap = Approvals(work_dir)
        self.settings = draft.get("settings", {})
        self.findings = []
        self.verbs = load_verbs()
        self.verb_by_form = {}
        for v in self.verbs:
            self.verb_by_form[v["verb"].lower()] = v
            for f in v["approved_forms"] + v["unapproved_forms"]:
                self.verb_by_form.setdefault(f.lower(), v)
        phrases = load_json(DATA_DIR / "banned_phrases.json")["entries"]
        user_path = Path(work_dir) / "banned_phrases.json"  # user-extended list
        if user_path.is_file():
            phrases += load_json(user_path)["entries"]
        self.banned = [(re.compile(e["pattern"], re.I), e["reason"], e.get("severity", "error"), e.get("policy"))
                       for e in phrases]
        self.ranks = load_json(DATA_DIR / "ranks.json")
        self.history = history or []
        self.ruler = ruler
        self.proper = set(" ".join(draft.get("proper_nouns", [])).split())
        # [placeholders] are masked so no scan reads "[2,5xx]" as a number or "xxx" as an abbreviation
        self.lines = [(k, i, mask_placeholders(normalize_spaces(line["text"])), line) for k, i, line in iter_lines(draft, form)]
        self.sections = {s["key"]: s for s in form["sections"]}
        # a strat/push line with the (weak) strat omitted: push only, no opening verb expected
        last = {k: (i, t) for k, i, t, _ in self.lines if self.sections[k].get("strat_line") == "last"}
        self.push_only = {(k, i) for k, (i, t) in last.items() if "#" not in t}

    def add(self, sev, rule, where, msg):
        self.findings.append({"severity": sev, "rule": rule, "where": where, "message": msg})

    # ------------------------------------------------------------------ run
    def run(self):
        self.structure()
        for key, i, text, _ in self.lines:
            where = f"{key}[{i + 1}]"
            self.mechanics(where, text)
            self.terms(where, text)
            self.banned_phrases(where, text)
            self.style_conventions(where, text)
        self.duplicate_numbers()
        self.small_numbers()
        self.buzzwords()
        self.repeated_standouts()
        self.adjacent_numbers()
        self.double_credit()
        self.opening_verbs()
        self.voice_and_tense()
        self.consistency()
        self.stacked_acronyms()
        self.stratifications()
        self.sec_x()
        self.audience()
        self.history_overlap()
        if not self.d.get("_candidate"):
            self.coverage()
            self.fitness()
        return self.findings

    # ------------------------------------------------------------------ checks
    def structure(self):
        secs = self.d.get("sections", {})
        for key, sec in self.sections.items():
            lines = secs.get(key, {}).get("lines", [])
            if sec.get("required") and not lines:
                self.add("error", "structure", key, f"{sec['label']} is required but empty")
            if len(lines) > sec["max_lines"]:
                self.add("error", "structure", key, f"{len(lines)} lines; limit is {sec['max_lines']}")
            if sec.get("required") and 0 < len(lines) < sec["max_lines"]:
                self.add("warning", "structure", key, f"{len(lines)}/{sec['max_lines']} lines; use all available space")
            if sec.get("has_duty_title") and not secs.get(key, {}).get("duty_title"):
                self.add("error", "structure", key, "duty title missing")
            for i, line in enumerate(lines):
                st = line.get("status")
                if st and st != "fits":
                    self.add("error", "fit", f"{key}[{i + 1}]", f"line {st.replace('_', ' ')} ({line.get('delta_mm', 0):+.2f} mm); "
                             "spacing can't close it: reword (compression ladder, bullet-style.md §D, or add content), then refit")
                elif not st:
                    self.add("warning", "fit", f"{key}[{i + 1}]", f"not yet fitted; {REFIT}")
        for sev, rule, where, msg in stale_fits(self.d, self.form):
            self.add(sev, rule, where, msg)

    def mechanics(self, where, text):
        if not text.startswith("- "):
            self.add("error", "mechanics", where, "every line starts with '- '")
        if text.rstrip().endswith("."):
            self.add("error", "mechanics", where, "no ending punctuation (T&Q ch 19)")
        if re.search(r"\b[fw]/\s", text):
            self.add("error", "mechanics", where, "no space after the slash in f/ or w/ (CFC Att 2)")
        if re.search(r"[¹²³⁰-₟]", text):
            self.add("error", "mechanics", where, "no superscripts (SpOC 1.5.3.3)")
        if re.search(r"\s--|--\s", text):
            self.add("warning", "mechanics", where, "no spaces around '--'")
        if self.settings.get("ban_ampersand") and "&" in text:
            self.add("error", "mechanics", where, "'&' not allowed by settings")

    def terms(self, where, text):
        body = text[2:] if text.startswith("- ") else text
        toks = tokens(body)
        short, total, shorts = 0, 0, []
        first_word = True
        for tok, _ in toks:
            if tok in SYMBOLS or re.fullmatch(r"[\d$#%.,+<>/~-]+[KMB%+]?", tok):
                first_word = False
                continue
            total += 1
            if tok in self.proper:
                first_word = False
                continue
            if is_acronym(tok):
                short += 1
                shorts.append(tok)
            else:
                # 32-mbr, 5-wk, hand-picked: check each hyphenated part on its own
                parts = [p for p in tok.split("-") if p and not p.isdigit()] if "-" in tok else [tok]
                flagged = False
                for n, part in enumerate(parts):
                    status, detail = self.ap.abbreviation_status(part, line_start=first_word and n == 0)
                    if status in ("error", "judgment"):
                        self.add(status, "abbreviation", where, f"'{part}': {detail}")
                    flagged = flagged or bool(status)
                if flagged:
                    short += 1
                    shorts.append(tok)
            if tok in self.ranks["wrong_case_forms"]:
                self.add("error", "ranks", where, f"'{tok}': USAF/USSF ranks are mixed case (e.g. Maj, Capt, Lt Col)")
            first_word = False
        limit = self.settings.get("density_max", 0.50)
        if total and short / total > limit:
            # suggest the terms that cost the most readability: the longest shorthand first (acronyms, then abbreviations)
            spell = sorted(dict.fromkeys(shorts), key=lambda t: (not is_acronym(t), -len(t)))[:3]
            self.add("warning", "density", where, f"{short}/{total} tokens ({short / total:.0%}) are acronyms/abbreviations "
                                                  f"(> {limit:.0%}); the line is hard to read. Spell out: {', '.join(spell)}")

    def banned_phrases(self, where, text):
        policies = self.settings.get("policies", {})
        for rx, reason, severity, policy in self.banned:
            m = rx.search(text)
            if not m:
                continue
            if policy:  # unit-dependent rule: allow | warn | forbid (set per user in draft.settings.policies)
                choice = policies.get(policy, "warn")
                if choice == "allow":
                    continue
                severity = "error" if choice == "forbid" else "warning"
                reason += f" [unit policy '{policy}' = {choice}]"
            self.add(severity, "content", where, f"'{m.group(0)}': {reason}")

    def style_conventions(self, where, text):
        for m in re.finditer(r"\b(\d+)(nd|rd)\b", text):
            self.add("error", "ordinals", where, f"'{m.group(0)}' -> '{m.group(1)}d' (military ordinals)")
        for m in re.finditer(r"\b\d+(st|nd|rd|th|d)\s+(?=[A-Z]{2,})", text):
            self.add("error", "ordinals", where, f"'{m.group(0).strip()}': unit designators take no ordinal (61 ABG) (SpOC 1.5.3.2)")
        for m in re.finditer(r"\b(MD|SD)(\d+)\b", text):
            self.add("error", "designators", where, f"'{m.group(0)}' -> '{m.group(1)} {m.group(2)}' (CFC Att 1)")

    # ------------------------------------------------------------------ cross-line rules
    def duplicate_numbers(self):
        # Numbers compare only within a category: a $5B budget and 5 awards are different metrics.
        by_sec = {}
        for key, i, text, _ in self.lines:
            for cat, n, raw in numbers_in(text[2:], categorized=True):
                by_sec.setdefault(key, []).append(((cat, n), raw, i))
        fix = "reword first; then use a different precise figure; 'over N'/'N+' only as a last resort"
        for key, items in by_sec.items():
            seen = {}
            for n, raw, i in items:
                if n in seen:
                    self.add("error", "numbers", f"{key}[{i + 1}]",
                             f"{n[0]} '{raw}' repeats within {key} (first at line {seen[n] + 1}); {fix}")
                seen.setdefault(n, i)
        jd = {n for n, _, _ in by_sec.get("job_description", [])}
        for key, items in by_sec.items():
            if key == "job_description":
                continue
            for n, raw, i in items:
                if n in jd:
                    self.add("warning", "numbers", f"{key}[{i + 1}]",
                             f"'{raw}' also appears in the Job Description; each metric has one home")
        seen_all = {}
        for key, items in by_sec.items():
            if key == "job_description":
                continue
            for n, raw, i in items:
                if n in seen_all and seen_all[n][0] != key:
                    self.add("warning", "numbers", f"{key}[{i + 1}]", f"'{raw}' also used in {seen_all[n][0]}[{seen_all[n][1] + 1}]")
                seen_all.setdefault(n, (key, i))
        # a vetted round count (ledger entry's exact_numbers) is a real figure, not an estimate
        vetted = {e["id"]: {n.replace(",", "") for n in e.get("exact_numbers", [])} for e in self.d.get("ledger", []) if "id" in e}
        for key, i, text, line in self.lines:
            for raw in round_numbers(text[2:]):
                src = next((lid for lid in line.get("ledger", []) if raw.replace(",", "") in vetted.get(lid, ())), None)
                if src:
                    self.add("info", "numbers", f"{key}[{i + 1}]", f"'{raw}' is round but vetted as exact (ledger {src})")
                else:
                    self.add("warning", "numbers", f"{key}[{i + 1}]",
                             f"'{raw}' reads as an estimate; boards trust precise figures (e.g. 517 over 500+). Use the exact count, "
                             "or, if it is a vetted exact count, list it in the ledger entry's exact_numbers")

    def buzzwords(self):
        """Doctrinal/strategic buzzwords stand out; each may appear at most once per OPR."""
        terms = load_json(DATA_DIR / "buzzwords.json")["terms"]
        user_path = self.work / "buzzwords.json"
        if user_path.is_file():
            terms += load_json(user_path)["terms"]
        reported = []
        # shortest first: 'pacing' inside 'pacing challenge' still counts, and the longer phrase isn't reported again
        for term in sorted({t.lower() for t in terms}, key=len):
            if any(r in term for r in reported):
                continue
            # '--lethality' counts (the impact connector); 'non-lethality' doesn't
            rx = re.compile(rf"(?<!\w)(?<!\w-){re.escape(term)}(?!\w)(?!-\w)", re.I)
            hits = [f"{k}[{i + 1}]" for k, i, t, _ in self.lines for _ in rx.findall(t)]
            if len(hits) > 1:
                reported.append(term)
                self.add("warning", "buzzword", ", ".join(hits[1:]),
                         f"'{term}' used {len(hits)} times ({', '.join(hits)}); a standout buzzword should appear once per OPR")

    def small_numbers(self):
        """T&Q ch 28: words for one-nine, figures for 10+ with commas. Unit policy: flexible (judgment) | strict | off."""
        policy = self.settings.get("policies", {}).get("small_numbers", "flexible")
        if policy == "off":
            return
        sev = "warning" if policy == "strict" else "judgment"
        for key, i, text, _ in self.lines:
            if (key, i) in self.push_only or text[2:].lstrip().startswith("#"):
                continue  # strat/push lines: strats and grades are figures by rule
            small, no_comma = small_number_issues(text[2:])
            if small:
                self.add(sev, "numbers", f"{key}[{i + 1}]", f"spell out {', '.join(repr(s) for s in small)} (T&Q ch 28: one-nine in words) "
                         f"[unit policy 'small_numbers' = {policy}]")
            for raw in no_comma:
                self.add(sev, "numbers", f"{key}[{i + 1}]", f"'{raw}' needs the thousands separator ({int(raw):,})")

    def repeated_standouts(self):
        """The two strat/push lines are the most-read lines; a descriptor used in both ('planner') reads as a repeat."""
        def words(text):
            body = re.sub(r"#(\d+|\[N\])/(\d+|\[M\])\s+[^,;!]*?(?=,|;|--|!|$)", " ", text[2:])  # drop the strat groups
            out = {}
            for w in re.findall(r"[A-Za-z]+", body):
                low = w.lower()
                abbr = len(w) >= 3 and self.ap.abbreviation_status(w)[0] == "approved"  # "ldr" echoes as loudly as "leader"
                if (len(w) < 5 and not abbr) or low in STANDOUT_STOPWORDS or is_acronym(w) or w in self.proper:
                    continue
                out.setdefault(re.sub(r"(ers|er|ing|ed|s)$", "", low), w)
            return out

        last = {}
        for k, i, t, _ in self.lines:
            if k in ("rater", "additional_rater") and self.sections[k].get("strat_line") == "last":
                last[k] = (i, t)
        if len(last) < 2:
            return
        (ri, rt), (ai, at) = last["rater"], last["additional_rater"]
        rw, aw = words(rt), words(at)
        for stem in sorted(rw.keys() & aw.keys()):
            self.add("judgment", "board_read", f"additional_rater[{ai + 1}]",
                     f"'{aw[stem]}' also in rater[{ri + 1}] ('{rw[stem]}'); both strat/push lines are read closely, so vary the descriptor")

    def adjacent_numbers(self):
        """The same figure on consecutive lines reads as a repeat even across categories (100 sites / 100% on time)."""
        prev = None
        for key, i, text, _ in self.lines:
            here = {}
            for cat, n, raw in numbers_in(text[2:], categorized=True):
                m = re.match(r"[\d.]+", n)
                if m and float(m.group(0)) >= 10:
                    here.setdefault(m.group(0), (cat, raw))
            if prev and prev[0] == key:
                for val, (cat, raw) in here.items():
                    if val in prev[2] and prev[2][val][0] != cat:
                        self.add("judgment", "board_read", f"{key}[{i + 1}]",
                                 f"'{raw}' sits next to '{prev[2][val][1]}' in {key}[{prev[1] + 1}]; legal (different metrics), but reads as a repeat")
            prev = (key, i, here)

    def double_credit(self):
        """One accomplishment must not visibly earn credit in two performance lines."""
        used = {}
        for key, i, _, line in self.lines:
            if self.sections[key]["kind"] == "job_description":
                continue
            for lid in line.get("ledger", []):
                if lid in used and used[lid] != (key, i):
                    k0, i0 = used[lid]
                    self.add("warning", "double_credit", f"{key}[{i + 1}]",
                             f"ledger {lid} also backs {k0}[{i0 + 1}]; one accomplishment must not earn credit twice. Several "
                             "items may feed one larger impact, but each line must stand on its own")
                used.setdefault(lid, (key, i))
        # the same award or nomination named in two performance lines, even when the ledger tags differ
        named = {}
        for key, i, text, _ in self.lines:
            if self.sections[key]["kind"] == "job_description":
                continue
            # key on the name's last word ("Won NSC Schriever awd" and "MD 8 NSC Schriever nom" are both "Schriever")
            names = {m.group(1).split()[-1] for m in AWARD_NAME.finditer(text)} | set(AWARD_ACRONYM.findall(text))
            for name in names:
                if name in named and named[name][0] != (key, i):
                    k0, i0 = named[name][0]
                    self.add("warning", "double_credit", f"{key}[{i + 1}]", f"award/nomination '{name}' also named in {k0}[{i0 + 1}]; "
                             "claim it once, in the strongest spot (usually a strat line)")
                named.setdefault(name, [(key, i)])

    def coverage(self):
        """Alternates for at least half the lines (the JD and strat/push lines first), and 4 fitted spare bullets."""
        lines = [(k, i, line) for k, i, _, line in self.lines]
        if lines:
            with_alt = sum(1 for _, _, ln in lines if ln.get("alternates"))
            if with_alt / len(lines) < 0.5:
                self.add("warning", "alternates", "report", f"alternates on {with_alt}/{len(lines)} lines; give good alternates for at least half")
            last = {k: i for k, i, _ in lines}
            for k, i, ln in lines:
                strat = self.sections[k].get("strat_line") == "last" and i == last[k]
                if (self.sections[k]["kind"] == "job_description" or strat) and not ln.get("alternates"):
                    self.add("warning", "alternates", f"{k}[{i + 1}]", "priority line (Job Description or strat/push) has no alternates")
        spares = self.d.get("spares", [])
        if len(spares) < 4:
            self.add("warning", "spares", "spares", f"{len(spares)}/4 spare performance bullets; page 2 carries 4 fitted, lint-clean swap-ins")
        for n, sp in enumerate(spares):
            if sp.get("status") != "fits":
                st = sp.get("status", "unfitted")
                self.add("error", "fit", f"spares[{n + 1}]", f"spare {st.replace('_', ' ')}; "
                         + (REFIT if st == "unfitted" else "reword (compression ladder or add content), then refit"))

    def fitness(self):
        if not self.d.get("ratee", {}).get("fitness_score"):
            self.add("warning", "fitness", "ratee", "no fitness score recorded; boards weigh it heavily (2026+). Ask for score and test date")

    def opener(self, text):
        body = text[2:]
        if body.startswith("#") or body.startswith("#["):
            return None
        toks = [t for t, _ in tokens(body)]
        start = 0
        if "!" in body[:60] and not self._verb(toks[0] if toks else ""):
            after = body.split("!", 1)[1]
            toks = [t for t, _ in tokens(after)]
        for t in toks[start:start + 6]:
            v = self._verb(t)
            if v:
                return v
        return None

    def _verb(self, tok):
        low = tok.lower()
        if low in self.verb_by_form:
            return self.verb_by_form[low]["verb"]
        if re.fullmatch(r"[a-z]+ed", low) or re.fullmatch(r"[a-z]+'d", low):
            return tok.capitalize()
        return None

    def opening_verbs(self):
        seen = {}
        tiers = {v["verb"]: v["tier"] for v in self.verbs}
        for key, i, text, _ in self.lines:
            if self.sections[key]["kind"] == "job_description" or (key, i) in self.push_only:
                continue
            v = self.opener(text)
            where = f"{key}[{i + 1}]"
            if not v:
                if not text[2:].startswith("#"):
                    self.add("warning", "verbs", where, "could not find an opening action verb (T&Q: start with action)")
                continue
            if v in seen:
                self.add("error", "verbs", where, f"opening verb '{v}' already used at {seen[v]} (spelled-out and abbreviated forms count as the same verb)")
            seen.setdefault(v, where)
            tier = tiers.get(v, "neutral")
            if tier == "banned":
                self.add("error", "verbs", where, f"'{v}' is a banned verb")
            elif tier == "overused":
                self.add("warning", "verbs", where, f"'{v}' is overused; prefer a distinctive verb" + (" (avoid 'Led')" if v == "Led" else ""))

    PASSIVE_OPENERS = {"selected", "chosen", "hand-picked", "handpicked", "named", "appointed", "tasked", "recognized",
                       "nominated", "assigned", "designated", "tapped", "entrusted", "charged"}

    def voice_and_tense(self):
        """OPRs are written in active voice; performance lines (Blocks IV-VI) in past tense."""
        past = {v["verb"].lower() for v in self.verbs}
        for key, i, text, _ in self.lines:
            where = f"{key}[{i + 1}]"
            body = text[2:].strip()
            if re.search(r"\b(was|were|is|are|been|being|be)\s+(\w+ly\s+)?\w+(ed|en)\b", body, re.I):
                self.add("warning", "voice", where, "passive construction ('was/were ... -ed'); rewrite in active voice")
            if self.sections[key]["kind"] == "job_description" or body.startswith("#") or (key, i) in self.push_only:
                continue
            first = re.match(r"([A-Za-z'-]+)", body.split("!", 1)[1].strip() if "!" in body[:60] else body)
            if not first:
                continue
            w = first.group(1).lower()
            if w in self.PASSIVE_OPENERS:
                self.add("judgment", "voice", where, f"'{first.group(1)}' opens with a passive/recipient verb; prefer an "
                                                     "active verb for what the ratee did (e.g. 'Led ... as hand-picked dep')")
            elif w.endswith("ing"):
                self.add("error", "tense", where, f"'{first.group(1)}': performance lines are past tense, not -ing")
            elif w.endswith("s") and not w.endswith("ss") and (w[:-1] + "d" in past or w[:-1] + "ed" in past
                                                                or w[:-2] + "ied" in past or w[:-2] + "ed" in past
                                                                or w[:-1] in IRREGULAR_BASES or w[:-2] in IRREGULAR_BASES):
                self.add("error", "tense", where, f"'{first.group(1)}': performance lines are past tense")

    def consistency(self):
        """Abbreviations must be used consistently across all blocks (no mixing 'for' and 'f/')."""
        # The duty title is an official title, so it is exempt from abbreviation consistency.
        all_text = "\n".join(t for _, _, t, _ in self.lines)
        all_text_wd = all_text
        used_forms = {}
        for key, i, text, _ in self.lines:
            for tok, _ in tokens(text[2:]):
                base = tok if tok in self.ap.abbr else re.sub(r"(?:'s|es|s)$", "", tok)
                if base in self.ap.abbr:
                    used_forms.setdefault(self.ap.abbr[base]["listed"], set()).add(base)
                low = tok.lower()
                if low.endswith("'d") and low in self.ap.d_forms:
                    used_forms.setdefault("'d:" + low, set()).add(tok)
        for listed, forms in used_forms.items():
            if listed.startswith("'d:"):
                d = listed[3:]
                verb = self.verb_by_form.get(d, {}).get("verb")
                if verb and re.search(rf"\b{verb}\b", all_text_wd, re.I):
                    self.add("error", "consistency", "report", f"both '{d}' and '{verb}' used; pick one form for the whole OPR")
                continue
            entry = next(e for e in self.ap.abbr_source["entries"] if e["listed"] == listed)
            if len(forms) > 1:
                self.add("error", "consistency", "report", f"alternates {sorted(forms)} both used; use one form of '{listed}' throughout")
            for long_ in _long_forms(entry["meaning"]):
                if re.search(rf"(?<![\w/]){re.escape(long_)}(?![\w'])", all_text_wd, re.I):
                    self.add("error", "consistency", "report",
                             f"'{sorted(forms)[0]}' and spelled-out '{long_}' both used; abbreviations must be consistent across all blocks")
                    break
        if "&" in all_text and re.search(r"\band\b", all_text):
            self.add("error", "consistency", "report", "'&' and 'and' both used; once '&' is used, use it everywhere (proper names excepted)")
        # acronym vs spelled-out (warning)
        for acr, meaning in self.d.get("acronyms", {}).items():
            if re.search(rf"\b{re.escape(acr)}\b", all_text) and re.search(re.escape(meaning), all_text, re.I):
                self.add("warning", "consistency", "report", f"'{acr}' and '{meaning}' both appear")

    def stacked_acronyms(self):
        if not self.ruler:
            return
        thresh = self.settings.get("stack_mm", 20.0)
        prev_key, prev = None, None
        for key, i, text, line in self.lines:
            shown = line.get("fitted") or text
            pos = {}
            for tok, start in tokens(shown):
                if is_acronym(tok):
                    pos.setdefault(acronym_core(tok), []).append(self.ruler.mm(shown[:start]))
            if prev is not None and prev_key == key:
                for acr, xs in pos.items():
                    for x in xs:
                        for px in prev.get(acr, []):
                            if abs(x - px) < thresh:
                                self.add("error", "stacking", f"{key}[{i + 1}]",
                                         f"'{acr}' sits {abs(x - px):.0f} mm from the same acronym on the line above; move or reword so it doesn't stack")
            prev_key, prev = key, pos

    def stratifications(self):
        for key, sec in self.sections.items():
            if sec.get("strat_line") != "last":
                continue
            lines = [(i, t) for k, i, t, _ in self.lines if k == key]
            if not lines:
                continue
            if lines[0][1][2:].lstrip().startswith("#"):
                self.add("error", "strat", f"{key}[1]", "first line must be a strong performance line, not the strat line")
            last_i, last = lines[-1]
            where = f"{key}[{last_i + 1}]"
            strats = re.findall(r"#(\d+|\[N\])/(\d+|\[M\])\s+(.+?)(?=,|;|--|!|$)", last)
            if (key, last_i) in self.push_only:
                self.add("judgment", "strat", where, "no stratification stated; confirm the omission is intentional "
                                                     "(a weak strat hurts more than none) and that the push still lands")
                continue
            if not last[2:].startswith("#"):
                self.add("error", "strat", where, "last line should open with the stratification (#N/M peer group)")
                continue
            if len(strats) > 2:
                self.add("error", "strat", where, "a rater may give at most two stratifications (SpOC 1.6.3.2.5)")
            for n, (num, den, group) in enumerate(strats):
                g = group.strip()
                if num.isdigit() and den.isdigit() and int(num) > int(den):
                    self.add("error", "strat", where, f"#{num}/{den}: numerator exceeds denominator")
                elif num.isdigit() and den.isdigit() and num != "1" and int(num) > int(den) / 2:
                    if n > 0:
                        self.add("error", "strat", where, f"secondary #{num}/{den} is below the top half; a secondary strat must be strong")
                    elif len(strats) > 1:
                        # The one exception to "no bad strats": a strong secondary still needs its primary stated.
                        self.add("judgment", "strat", where, f"bottom-half primary #{num}/{den} stands only because a secondary follows; "
                                                             "confirm the secondary is strong enough for the board to overlook it")
                    else:
                        self.add("warning", "strat", where,
                                 f"#{num}/{den} is below the top half with no secondary; omit it (a weak strat hurts more than none) and keep the push")
                if not g or g.split()[0].lower() in VAGUE_GROUPS:
                    self.add("error", "strat", where, f"vague peer group after #{num}/{den} (SpOC 1.6.3.2.4)")
                if n == 0 and not GRADE_GROUP.search(re.sub(r"^(Del|DEL|Dir|Sq|Gp|Wg|Delta|Directorate|Squadron|MD \d+|SD \d+)\s+", "", g)):
                    self.add("error", "strat", where, f"first strat '{g}' must be the primary rank strat (e.g. O-4s), even if #1/1")
            if "[N]" in last or "[M]" in last:
                self.add("info", "strat", where, "stratification placeholder for the rating chain to fill")
        # Block V strat/push should be the strongest; flag smaller denominator
        dens = {}
        for key in ("rater", "additional_rater"):
            lines = [t for k, _, t, _ in self.lines if k == key]
            if lines:
                m = re.search(r"#\d+/(\d+)", lines[-1])
                if m:
                    dens[key] = int(m.group(1))
        if len(dens) == 2 and dens["additional_rater"] < dens["rater"]:
            # a functional reviewer can reshuffle which evaluator carries which strat, so the rule is advisory then
            functional = (self.d.get("rating_chain") or {}).get("functional")
            self.add("info" if functional else "warning", "strat", "additional_rater",
                     "additional rater's strat pool is smaller than the rater's; Block V should be the strongest strat/push"
                     + (" (functional in the chain: confirm the intended strat placement)" if functional else ""))
        # both strat lines are read side by side: name the grade the same way ("O-4s" in both, not "Majors" in one)
        grades = {}
        for key in ("rater", "additional_rater"):
            lines = [(i, t) for k, i, t, _ in self.lines if k == key]
            if lines:
                m = re.search(r"#(?:\d+|\[N\])/(?:\d+|\[M\])\s+(?:\S+\s+){0,2}?(O-\d+s?|Majs?|Majors?|Capts?|Captains?|Lt ?Cols?|Cols?|Colonels?)\b",
                              lines[-1][1])
                if m:
                    g = m.group(1).lower()
                    grades[key] = (lines[-1][0], m.group(1), "o" if g.startswith("o-") else g.rstrip("s").replace("major", "maj"))
        if len(grades) == 2 and grades["rater"][2] != grades["additional_rater"][2]:
            (ri, rg, _), (ai, ag, _) = grades["rater"], grades["additional_rater"]
            self.add("judgment", "strat", f"additional_rater[{ai + 1}]",
                     f"grade group '{ag}' differs from rater[{ri + 1}]'s '{rg}'; use the same wording in both strat lines")

    def sec_x(self):
        remarks, missing, statuses = build_remarks(self.d, self.form, self.ap)
        used = used_acronyms(self.d, self.form)
        for acr, hint in missing:
            where = ", ".join(dict.fromkeys(used.get(acr, ["remarks"])))
            self.add("error", "acronyms", where, f"'{acr}' is not approved for this use: define it in draft['acronyms'] ({hint}), or, if it fits an AFPC "
                                                 f"category (organization, platform, office symbol...), record it in draft['acronym_categories']")
        for acr, (st, detail) in statuses.items():
            if st == "media":
                self.add("judgment", "acronyms", "remarks", f"'{acr}' treated as widely known; confirm it need not be defined")
            elif st == "category":
                self.add("judgment", "acronyms", "remarks", f"'{acr}' relies on {detail}; confirm (defining it in Sec X is never wrong)")
        override = self.d.get("remarks")
        if override and override not in (remarks, self.d.get("remarks_auto")):  # only a hand-written Sec X is linted
            listed = re.findall(r"\(([^()]+)\)", override)
            text = "\n".join(t for _, _, t, _ in self.lines)
            for acr in listed:
                if not re.search(rf"\b{re.escape(acr)}", text):
                    self.add("error", "acronyms", "remarks", f"'{acr}' listed in Sec X but not used in the report (SpOC 1.5.1.5)")
                elif statuses.get(acr, ("",))[0] == "approved":
                    self.add("error", "acronyms", "remarks", f"'{acr}' is a common acronym; do not list it (CFC Att 1)")
                if acr in self.ap.abbr:
                    self.add("error", "acronyms", "remarks", f"'{acr}' is an abbreviation; do not list abbreviations (SpOC 1.5.1.4)")
            if listed != sorted(listed, key=str.upper):
                self.add("error", "acronyms", "remarks", "Sec X must be alphabetical by acronym (SpOC 1.2.4.3)")
            if re.search(r";(?! )|;  ", override):
                self.add("error", "acronyms", "remarks", "separate entries with a semicolon and one space")

    def audience(self):
        """Boards meet within a competitive category; jargon from other career fields should be plain-spoken."""
        board = self.d.get("board") or {}
        if not board.get("audience_fields"):
            self.add("info", "audience", "report", "no board audience set; run audience.py --grade <g> --core <AFSC> --draft <draft> --write")
            return
        terms = load_terms(self.work)
        familiar = {t for f in board["audience_fields"] for t in terms.get(f, [])}
        field_of = {}
        for field, ts in terms.items():
            for t in ts:
                field_of.setdefault(t, set()).add(field)
        who = f"{board['category']} board ({', '.join(board.get('board_specialty_names', []))})"
        ledger = {e["id"]: e for e in self.d.get("ledger", [])}
        for key, i, text, line in self.lines:
            where = f"{key}[{i + 1}]"
            seen = set()
            for tok, _ in tokens(text[2:]):
                core = acronym_core(tok) if is_acronym(tok) else tok
                fields = field_of.get(core)
                if not fields or core in familiar or core in seen:
                    continue
                seen.add(core)
                status, _ = self.ap.acronym_status(core, self.d.get("acronyms", {}).get(core),
                                                   self.d.get("acronym_categories", {}).get(core))
                if status == "structure":
                    continue  # USSF/joint structure is familiar to every board
                sev = "warning" if status == "needs_definition" else "judgment"
                self.add(sev, "audience", where, f"'{core}' is {'/'.join(sorted(fields))} jargon; the {who} may not "
                                                 "know it: spell out, generalize, or say it plainly")
            for lid in line.get("ledger", []):
                field = ledger.get(lid, {}).get("career_field")
                if field and field not in board["audience_fields"]:
                    self.add("info", "audience", where, f"built from {field} experience ({lid}); write it for the {who}: "
                                                        "plain language, outcome over process, fewer field acronyms")
                    break

    def history_overlap(self):
        if not self.history:
            return
        hist = [set(re.findall(r"[a-z0-9$]+", h.lower())) for h in self.history]
        for key, i, text, _ in self.lines:
            words = set(re.findall(r"[a-z0-9$]+", text.lower()))
            for h in hist:
                if words and len(words & h) / len(words | h) > 0.6:
                    self.add("warning", "history", f"{key}[{i + 1}]", "very similar to a prior OPR line; boards notice recycled bullets")
                    break


def _long_forms(meaning):
    out = []
    for part in re.split(r";| or ", meaning):
        part = re.sub(r"\(.*?\)", "", part).strip().lower()
        if part and len(part) > 2:
            out.append(part)
    return out


GUARD_SKIP = {"fit", "structure", "alternates", "spares", "fitness", "history", "audience"}


def _alt_text(alt):
    return alt["text"] if isinstance(alt, dict) else alt


def guard_candidates(draft, form, work_dir, ruler=None):
    """Audit every alternate and spare against the whole OPR before it is shown to the user.

    Each candidate is swapped in (alternates) or added (spares) and the report is re-linted. Any error or
    warning the candidate introduces anywhere in the OPR (a reused metric, verb, accomplishment, or a broken
    consistency rule) is reported loudly against the candidate. Other lines are never edited to make room.
    """
    def findings_of(d, shift=None):
        d = dict(d, _candidate=True)
        return Counter((f["severity"], f["rule"], shifted(f["where"], shift), shifted(f["message"], shift))
                       for f in Linter(d, form, work_dir, None, ruler).run()
                       if (f["severity"] in ("error", "warning") or f["rule"] == "board_read") and f["rule"] not in GUARD_SKIP)

    def shifted(s, shift):
        """Undo the renumbering caused by inserting spares, so a base finding at rater[6] that moved to
        rater[7] is recognized as pre-existing instead of blamed on the spare; the inserted lines themselves
        are named after the candidate."""
        if not shift:
            return s
        key, at, n, label = shift  # n lines inserted before 0-based index `at`

        def ref(m):
            k = int(m.group(1))
            return f"{key}[{k - n}]" if k > at + n else (label if k > at else m.group(0))
        return re.sub(rf"\b{key}\[(\d+)\]", ref, s)

    base = findings_of(draft)
    out = []

    def check(label, mutated, shift=None):
        # strict on purpose: a candidate must never be offered if it breaks compliance anywhere, so an error or
        # warning it introduces is an error here. Board-read judgments stay judgments (taste, not compliance).
        for (sev, rule, where, msg), _ in (findings_of(mutated, shift) - base).items():
            at = "in the candidate itself" if where == label else f"at {where}"
            out.append({"severity": "judgment" if sev == "judgment" else "error", "rule": "guard", "where": label,
                        "message": f"would break whole-OPR compliance {at}: {msg}. Rewrite this candidate; never edit other lines to make room"})

    secs = draft.get("sections", {})
    for key, i, line in iter_lines(draft, form):
        for n, alt in enumerate(line.get("alternates", [])):
            mutated = copy.deepcopy(draft)
            mutated["sections"][key]["lines"][i] = {"text": normalize_spaces(_alt_text(alt)), "ledger": line.get("ledger", [])}
            check(f"{key}[{i + 1}] alt {n + 1}", mutated)
    target = next((k for k in ("rater", "additional_rater") if secs.get(k, {}).get("lines")), None)
    spares = draft.get("spares", [])
    if target:
        def with_spares(items):
            mutated = copy.deepcopy(draft)
            lines = mutated["sections"][target]["lines"]
            for sp in items:  # insert before the strat/push line, as a swap-in would sit
                lines.insert(len(lines) - 1, {"text": normalize_spaces(sp["text"]), "ledger": sp.get("ledger", [])})
            return mutated
        at = len(secs[target]["lines"]) - 1
        for n, sp in enumerate(spares):
            check(f"spares[{n + 1}]", with_spares([sp]), (target, at, 1, f"spares[{n + 1}]"))
        if len(spares) > 1:
            check("spares (together)", with_spares(spares), (target, at, len(spares), "spares (together)"))
    return out


def lint(draft_path, history_path=None, use_ruler=True, guard=True, draft=None):
    """Lint the draft at draft_path, or the in-memory draft (overrides still load from draft_path's folder)."""
    path = Path(draft_path)
    draft = draft if draft is not None else load_json(path)
    form = load_form(draft.get("form"), path.parent)
    history = []
    hp = Path(history_path) if history_path else path.parent / "history.json"
    if hp.is_file():
        history = [ln["text"] for ln in load_json(hp).get("lines", [])]
    ruler = Ruler(None, form.get("font_size_pt", 12)) if use_ruler else None
    findings = Linter(draft, form, path.parent, history, ruler).run()
    if guard:
        findings += guard_candidates(draft, form, path.parent, ruler)
    return findings


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft")
    ap.add_argument("--history")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-guard", action="store_true", help="skip the whole-OPR audit of alternates and spares")
    args = ap.parse_args()
    findings = lint(args.draft, args.history, guard=not args.no_guard)
    order = {"error": 0, "warning": 1, "judgment": 2, "info": 3}
    findings.sort(key=lambda f: (order[f["severity"]], f["where"]))
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"{f['severity'].upper():8} {f['rule']:12} {f['where']:22} {f['message']}")
        counts = {s: sum(1 for f in findings if f["severity"] == s) for s in order}
        print(f"\n{counts['error']} errors, {counts['warning']} warnings, {counts['judgment']} judgment, {counts['info']} info")
    sys.exit(1 if any(f["severity"] == "error" for f in findings) else 0)


if __name__ == "__main__":
    main()
