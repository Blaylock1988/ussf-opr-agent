"""Score an officer's OPR record the way a promotion board's Career Review worksheet does.

Reads _opr_work/history.json (prior OPRs) and, if present, _opr_work/draft.json (this OPR). It writes
_opr_work/career_review.md, which has three parts:
  - a year-by-year table of strats, DE pushes and next-rank job pushes (the "Top OPR" and "Overall OPRs" rows);
  - Strong/Average/Weak ratings for the factors that can be derived from the text;
  - questions for the factors the OPR text cannot show (commander time, JDAL, staff, awards, education...).

Usage:  career_review.py "<folder>/_opr_work"
"""
import argparse
import re
from pathlib import Path

from common import DATA_DIR, load_json, normalize_spaces, utf8_stdout, write_text

STRAT = re.compile(r"#(\d+|\[N\])/(\d+|\[M\])\s+(.+?)(?=,|;|--|!|$)")
DE_PUSH = re.compile(r"\b(SDE|IDE|ILE|SLE|PDE|IDE/SDE|Senior Developmental|Intermediate Developmental|War College|ACSC|AWC|NWC|SOS)\b", re.I)
# Next-rank job push: the worksheet calls it the "command push", but any job suited to the next grade counts
# (command, ML/SML, DO, division chief, HQSF/HAF/joint staff, PEM).
JOB_PUSH = re.compile(r"\b(\w+/CC|CC next|command|cmd|sq (?:ldrs?hi?p|leadership|CC)|Del(?:ta)? (?:ldrs?hi?p|leadership|CC)|"
                      r"Squadron Commander|ML|materiel leader|SML|PEM|staff|HQSF|HAF|Pentagon|Jt|joint|CCMD|DO|"
                      r"Div(?:ision)? Ch(?:ief)?|Branch Chief|deputy|dir(?:ector)?|ldrs?hi?p|leadership)\b", re.I)


# Rough duty-title ladder (higher = more responsibility). Heuristic only: unknown titles are left for judgment.
TITLE_LEVELS = [
    (6, r"senior materiel leader|\bSML\b|delta (commander|CC)|\bDel(ta)?/CC\b|group (commander|CC)|\bGp/CC\b"),
    (5, r"squadron commander|\bSq/CC\b|\bSq CC\b|materiel leader|\bML\b|deputy director"),
    (4, r"deputy (squadron )?commander|\bDep(uty)? Sq|director of operations|\bDO\b|detachment commander|\bDet/CC\b|"
        r"division chief|\bDiv(ision)? Ch"),
    (3, r"branch chief|\bBr(anch)? Ch|deputy division"),
    (2, r"flight commander|\bFlt/CC\b|flight chief|team (lead|chief)"),
    (1, r"section (lead|chief)|element (lead|chief)|\bOIC\b|crew commander|officer\b|engineer|analyst|instructor"),
]  # role titles such as Program Manager span levels, so they stay unranked for the user to judge


def ladder_level(title):
    for level, rx in TITLE_LEVELS:
        if re.search(rx, title or "", re.I):
            return level
    return None


def duty_title_review(profile, draft):
    """Duty titles must show growth and never regress (e.g. Flight CC -> Branch Chief -> Flight CC)."""
    titles = list((profile or {}).get("duty_titles", []))
    rated = {k.lower(): v for k, v in (profile or {}).get("title_levels", {}).items()}  # the user's rating of role titles

    def title_level(title):
        return rated.get((title or "").lower(), ladder_level(title))

    current = (draft or {}).get("sections", {}).get("job_description", {}).get("duty_title")
    if current:
        titles.append({"period": "THIS OPR (draft)", "title": current, "source": "draft"})
    out = ["", "## Duty title progression (AMS SURF + prior OPRs)", ""]
    if len(titles) < 2:
        return out + ["**Not yet reviewed.** Ask for the AMS SURF and prior OPRs, and record each duty title in "
                      "`career_profile.json` → `duty_titles` [{period, title, source}]."]
    out += ["| Period | Duty title | Source | Level |", "|---|---|---|---|"]
    out += [f"| {t.get('period', '?')} | {t['title']} | {t.get('source', '')} | {title_level(t['title']) or '?'} |" for t in titles]
    notes, prev = [], None
    for t in titles:
        lvl = title_level(t["title"])
        if lvl is not None and prev is not None and lvl < prev[1]:
            notes.append(f"**REGRESSION:** {prev[0]['title']} → {t['title']} ({t.get('period', '?')}). Never let an OPR show a "
                         "step down. If a reorganization caused it, flag it so the commander sees the unintended board impact.")
        if lvl is not None:
            prev = (t, lvl)
    if titles[-1]["source"] == "draft" and prev and title_level(current) is not None and len(titles) > 1:
        before = [title_level(t["title"]) for t in titles[:-1] if title_level(t["title"]) is not None]
        if before and title_level(current) <= max(before):
            notes.append("**No visible growth** in this OPR's duty title. The ratee can propose a title (with supervisor/unit "
                         "approval) that shows growth before closeout. SURF titles are capped at 30 characters, so they may differ from the OPR.")
    unrated = list(dict.fromkeys(t["title"] for t in titles if title_level(t["title"]) is None))
    if unrated:
        notes.append("**UNRATED titles:** " + "; ".join(unrated) + ". The regression check skips them. Ask the user where each "
                     "sits (1 section lead … 3 branch chief, 4 division chief/DO, 5 Sq/CC or ML, 6 Delta/Gp CC or SML) and record it "
                     "in `career_profile.json` → `title_levels` {title: level}, then rerun.")
    return out + [""] + (notes or ["No regression found (levels are a heuristic; unknown titles need judgment)."])


def grade_of(draft):
    scod = load_json(DATA_DIR / "scod.json")
    g = (draft or {}).get("ratee", {}).get("grade") or (draft or {}).get("board", {}).get("grade") or ""
    return scod["grade_aliases"].get(g, g), scod


def closeout_section(draft):
    grade, scod = grade_of(draft)
    row = next((e for e in scod["entries"] if grade in e["grades"]), None)
    if not row:
        return ["", "## Close-out dates", "", "Grade unknown; set draft.ratee.grade to show the SCOD and accountability date."]
    return ["", f"## Close-out dates ({row['label']}; as of {scod['as_of']})", "",
            f"- Accountability (lock) date: **{row['accountability']}** (MM-DD)",
            f"- Static close-out date (SCOD): **{row['scod']}** (MM-DD)",
            f"- {scod['caution']}",
            "- Only accomplishments inside the rating period count. Work very likely to finish by closeout is fair game."]


def development_section(draft, prios):
    guide = prios.get("career_guidance")
    if not guide:
        return []
    grade, _ = grade_of(draft)
    fields = set((draft or {}).get("board", {}).get("audience_fields", []))
    core = ((draft or {}).get("board", {}).get("core") or (draft or {}).get("ratee", {}).get("dafsc") or "")[:3]
    out = ["", f"## Development and push guidance for {grade or 'this grade'} ({guide['source']})", ""]
    for name, f in guide["fields"].items():
        if name in fields or core in f["specialties"]:
            out += [f"- **{name.title()}:** " + " ".join(f["notes"])]
            if f["push_by_grade"].get(grade):
                out += [f"  - Push target at {grade}: {f['push_by_grade'][grade]}"]
    bp = guide["boarded_programs"]
    if grade in bp["strong_at"]:
        out += ["- **Competitively boarded schools/programs** (strong at this grade): " + "; ".join(bp["items"])]
    for gate in guide["education_gates"]:
        if grade in gate["applies_to"]:
            out += [f"- **Education gate:** {gate['requirement']}"]
    out += [f"- {guide['note']}", "",
            "Next: write `_opr_work/record_review.md` with two lists (see `reference/interview-and-review.md`): "
            "**Strengthen this OPR** and **Strengthen future boards**."]
    return out


def strat_list(text):
    out = []
    for num, den, group in STRAT.findall(text):
        pct = int(num) / int(den) if num.isdigit() and den.isdigit() and int(den) else None
        # score: #1 of any pool is the strongest signal (0); otherwise the percentile
        score = None if pct is None else (0.0 if num == "1" else pct)
        out.append({"num": num, "den": den, "group": group.strip(), "pct": pct, "score": score,
                    "bad": num.isdigit() and den.isdigit() and num != "1" and int(num) > int(den) / 2})
    return out


def push_of(text):
    return text.split("--", 1)[1].strip() if "--" in text else ""


def rate_strat(strats):
    real = [s for s in strats if s["pct"] is not None]
    if not strats:
        return "Weak/Missing"
    if not real:
        return "Pending (placeholder)"
    best = min(s["score"] for s in real)
    if best <= 0.2:
        return "Strong"
    return "Average" if best <= 0.5 else "Weak (bottom half: omit)"


def rows_from(lines, year):
    by_sec = {}
    for ln in lines:
        by_sec.setdefault(ln["section"], []).append(normalize_spaces(ln["text"]))
    row = {"year": year}
    for sec in ("rater", "additional_rater", "reviewer"):
        lines = by_sec.get(sec, [])
        last = lines[-1] if lines else ""  # the strat/push line is always the block's last line
        push = push_of(last)
        row[sec] = {"line": last, "strats": strat_list(last), "push": push,
                    "de": bool(DE_PUSH.search(push)), "job": bool(JOB_PUSH.search(push))}
    return row


def fmt_strats(s):
    return ", ".join(f"#{x['num']}/{x['den']} {x['group']}" for x in s) or "-"


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work_dir")
    args = ap.parse_args()
    work = Path(args.work_dir)
    hist = load_json(work / "history.json")["lines"] if (work / "history.json").is_file() else []
    years = sorted({h["year"] for h in hist if h["year"]})
    rows = [rows_from([h for h in hist if h["year"] == y], y) for y in years]
    draft_path = work / "draft.json"
    if draft_path.is_file():
        d = load_json(draft_path)
        cur = [{"section": k, "text": ln["text"]} for k, sec in d.get("sections", {}).items() for ln in sec.get("lines", [])]
        rows.append(rows_from(cur, "THIS OPR (draft)"))

    board = (load_json(draft_path).get("board") if draft_path.is_file() else None) or {}
    who = (f"**Board audience:** {board['category']} ({board.get('category_name', '')}): "
           f"{', '.join(board.get('board_specialty_names', []))}. Write for these readers.") if board.get("category") else         "**Board audience:** unknown; run audience.py to set the competitive category."
    out = ["# Career Review (board worksheet view)", "", who, "",
           "This mirrors the USSF Assessment Worksheet - Career Review. Boards read the **top (most recent) OPR** and the "
           "**consistency across all OPRs**: stratification, DE push and next-rank job push (the worksheet's 'command push': any job suited to the next grade, not only command). Strong means present, high and "
           "consistent every year, with the Additional Rater at least as strong as the Rater.", "",
           "| Year | Rater strat | Addl Rater strat | DE push | Next-job push | Addl Rater push |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        a, b = r["rater"], r["additional_rater"]
        out.append(f"| {r['year']} | {fmt_strats(a['strats'])} | {fmt_strats(b['strats'])} | "
                   f"{'yes' if a['de'] or b['de'] else 'NO'} | {'yes' if a['job'] or b['job'] else 'NO'} | {b['push'] or '-'} |")

    findings = []
    if rows:
        top = rows[-1]
        top_strats = top["rater"]["strats"] + top["additional_rater"]["strats"]
        findings.append(f"**Top OPR - Stratification:** {rate_strat(top_strats)}")
        findings.append(f"**Top OPR - DE push:** {'Strong' if top['additional_rater']['de'] else ('Average (Rater only)' if top['rater']['de'] else 'Weak/Missing')}")
        findings.append(f"**Top OPR - Next-job push:** {'Strong' if top['additional_rater']['job'] else ('Average (Rater only)' if top['rater']['job'] else 'Weak/Missing')}")
        n = len(rows)
        with_strat = sum(1 for r in rows if r["rater"]["strats"] or r["additional_rater"]["strats"])
        with_de = sum(1 for r in rows if r["rater"]["de"] or r["additional_rater"]["de"])
        with_job = sum(1 for r in rows if r["rater"]["job"] or r["additional_rater"]["job"])

        def consistency(k):
            return "Strong/Consistent" if k == n else ("Average/Inconsistent" if k else "Weak/Missing")

        findings.append(f"**Overall OPRs - Stratifications:** {consistency(with_strat)} ({with_strat}/{n} OPRs)")
        findings.append(f"**Overall OPRs - DE push:** {consistency(with_de)} ({with_de}/{n})")
        findings.append(f"**Overall OPRs - Next-job push:** {consistency(with_job)} ({with_job}/{n})")
        pcts = [(r["year"], min((s["score"] for s in r["additional_rater"]["strats"] + r["rater"]["strats"] if s["score"] is not None), default=None)) for r in rows]
        real = [(y, p) for y, p in pcts if p is not None]
        for (y1, p1), (y2, p2) in zip(real, real[1:]):
            if p2 > p1 + 0.15:
                findings.append(f"**Consistency warning:** best strat fell from top {p1:.0%} ({y1}) to top {p2:.0%} ({y2}). "
                                "Boards (especially Lt Col and above) read drops. Consider a different, legitimately "
                                "stronger peer group or omit a weak strat.")
        for r in rows:
            if r["rater"]["strats"] and r["additional_rater"]["strats"]:
                def best(ss):
                    s = ss[0]  # compare primary (grade) strats; the secondary is a different pool
                    return (s["score"], -int(s["den"])) if s["score"] is not None else None
                ra, ad = best(r["rater"]["strats"]), best(r["additional_rater"]["strats"])
                if ra is not None and ad is not None and ad > ra:
                    findings.append(f"**{r['year']}:** Additional Rater strat is weaker than the Rater's; Block V should be the strongest.")
            for block in (r["rater"]["strats"], r["additional_rater"]["strats"]):
                for n, s in enumerate(block):
                    # a bottom-half primary that a strong secondary requires is the one allowed exception
                    if s["bad"] and not (n == 0 and len(block) > 1 and not block[1]["bad"]):
                        findings.append(f"**{r['year']}:** #{s['num']}/{s['den']} is below the top half; it should not have been included.")

    fitness = (load_json(draft_path).get("ratee", {}).get("fitness_score") if draft_path.is_file() else None)
    findings.append(f"**Fitness (board priority, 2026+):** {fitness if fitness else 'NOT RECORDED - capture score/category and test date'}")
    out += ["", "## Derived ratings", ""] + [f"- {f}" for f in findings]
    prio_path = work / "board_priorities.json"
    prios = load_json(prio_path if prio_path.is_file() else DATA_DIR / "board_priorities.json")
    out += ["", f"## Current board priorities (as of {prios.get('as_of', '?')}; re-verify every cycle)", ""]
    out += [f"- **{p['id']}** ({p['weight']}): {p['summary']}" for p in prios.get("priorities", [])]

    # Assignment experience comes from the ratee (career_profile.json), never from bullet wording: an OPR that
    # mentions the Joint Staff or a CCMD usually describes supporting work, not a joint assignment.
    sig = [p for p in prios.get("priorities", []) if p.get("signals")]
    profile_path = work / "career_profile.json"
    profile = load_json(profile_path)["experience"] if profile_path.is_file() else None
    if sig:
        out += ["", "## Board-priority experience (confirmed by the ratee)", ""]
        if profile is None:
            out += ["**Not yet confirmed.** Ask the ratee, for each item below, whether they have held it as an official "
                    "assignment or deployment (with years), and record the answers in `_opr_work/career_profile.json`. "
                    "Do not infer assignments from OPR wording.", ""]
            out += [f"- {p['id']}: {p['summary']}" for p in sig]
        else:
            out += ["| Priority | Weight | Held? | Detail |", "|---|---|---|---|"]
            for p in sig:
                e = profile.get(p["id"], {})
                has = {True: "yes", False: "no"}.get(e.get("has"), "unknown")
                out.append(f"| {p['id']} | {p['weight']} | {has} | {e.get('detail', '')} |")
            missing = [p["id"] for p in sig if p["weight"] == "high" and profile.get(p["id"], {}).get("has") is False]
            held = [p["id"] for p in sig if profile.get(p["id"], {}).get("has")]
            if held:
                out += ["", "**Make visible:** " + ", ".join(held) + ". Put these accomplishments first or last in a block, "
                        "with joint/theater metrics."]
            if missing:
                out += ["", "**Not held (high value):** " + ", ".join(missing) + ". Aim pushes at them alongside the command "
                        "push (e.g. 'Jt/CCMD staff next', 'HQSF staff next', 'Pentagon staff next'). Joint *support* work "
                        "(exercises, CCMD customers) can still show joint impact, but never imply an assignment that was not held."]

        def experience(text):
            t = normalize_spaces(text)
            return t.split("--", 1)[0] if t[2:].lstrip().startswith("#") else t  # a push is aspiration, not experience

        texts = {y: " ".join(experience(h["text"]) for h in hist if h["year"] == y) for y in years}
        if draft_path.is_file():
            texts["THIS OPR (draft)"] = " ".join(experience(ln["text"]) for sec in load_json(draft_path).get("sections", {}).values()
                                                 for ln in sec.get("lines", []))

        def hit(text, words):
            return any(re.search(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])", text, 0 if w.isupper() else re.I) for w in words)

        out += ["", "### Mentions in OPR text (supporting work only; NOT proof of an assignment)", "",
                "| Year | " + " | ".join(p["id"] for p in sig) + " |", "|---|" + "---|" * len(sig)]
        for y, t in texts.items():
            out.append(f"| {y} | " + " | ".join("mention" if hit(t, p["signals"]) else "-" for p in sig) + " |")
    draft = load_json(draft_path) if draft_path.is_file() else {}
    full_profile = load_json(profile_path) if profile_path.is_file() else {}
    out += duty_title_review(full_profile, draft)
    out += closeout_section(draft)
    out += development_section(draft, prios)
    out += ["", "## Factors the OPR text can't show (ask the user; use the answers to steer bullets and pushes)", "",
            "| Worksheet factor | Question | How this OPR can help |",
            "|---|---|---|",
            "| Competence: Depth in specialty | Years and levels in core SFSC? Certification level? | Bullets proving mastery; certs in strat line (if unit allows) |",
            "| Competence: Breadth of experience | Different mission areas, ops vs acq vs staff? | Highlight cross-functional/joint scope |",
            "| Competence: Selective assignment | LL, assignment hire, FAO, Olmstead, SAASS, etc.? | 'Hand-picked/selected f/...' hooks (allowed on OPRs) |",
            "| Leadership: Commander | Sq/ML/Gp, Det/Flt/HQ Sq command, or none? | Next-rank job push every OPR (command, ML, staff, PEM for acquisition); 'led N-mbr' scope |",
            "| Leadership: Joint (JDAL) | JDAL billet held/now/none? | Joint impacts, CCMD/exercise support, JPME-relevant work |",
            "| Leadership: Space/Air Staff, HHQ, Intermediate HQ | Staff tours at HQSF/HAF, FLDCOM, Delta? | Staff-level impact; next-assignment push to staff |",
            "| Achievements: Special awards/DG | Wing/Delta+, FLDCOM, USSF/DAF-level awards? | Awards in strat line; overflow to line 1 |",
            "| Achievements: Decorations | Right level after each assignment? | (decorations are separate; ensure accomplishments support one) |",
            "| Education: Advanced degree | MA/MS/PhD? | Unit policy decides if completion can be mentioned |",
            "| Education: PME | IDE/SDE completed or in residence? | DE push consistent with PME status (no 'in-res') |",
            "| Other: Deployments / OI&RSD / Language | Any this period? | Deployed or exercise bullets with joint metrics |",
            "| Promotions | Due course or late? | - |",
            "| Quality-force eliminators | Referral OPR, UIF/Art 15, LOR/LOA? | (never in the OPR; affects overall record) |"]
    write_text(work / "career_review.md", "\n".join(out) + "\n")
    table = out.index("| Year | Rater strat | Addl Rater strat | DE push | Next-job push | Addl Rater push |")
    print("\n".join(out[table:table + 2 + len(rows)]))
    print("\n".join(f"- {f}" for f in findings))
    print("\n".join(n for n in out if n.startswith(("**REGRESSION", "**UNRATED", "**No visible growth"))))
    print(f"\nwrote {work / 'career_review.md'}")


if __name__ == "__main__":
    main()
