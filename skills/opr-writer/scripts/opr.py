"""Single entry point for the OPR engine. Use these commands; there are no others (no 'opr_fit.py check',
no 'opr_export.py').

  opr.py build draft.json [--out "<folder>/Output/<Name> OPR <period>.docx"] [--apply-abbrev-set] [--force]
        fit (writes fitted spacing) -> rebuild Sec X acronyms -> lint -> render the DOCX, plus the ledger,
        research and record-review reports as DOCX when settings.export_reports is true (the default).
        Refuses to render while lint has errors, unless --force.
  opr.py check draft.json [--apply-abbrev-set]
        fit + lint, reporting only; writes nothing.
  opr.py fit draft.json --write [--apply-abbrev-set]
        store fitted spacing for every line, spare and alternate back into draft.json.
  opr.py lint draft.json [--json]
        lint only (includes the whole-OPR audit of every alternate and spare).
  opr.py measure "- Line one" ["- Line two" ...] [--font <ttf>]
        measure ad-hoc lines against the form width (also proves the font at setup).

build, check and fit stop, changing nothing, if a 'fitted' string was hand-edited (the fit would drop it).

draft.json is engine state: edit it only through these commands or the skill, never by hand in an editor,
because hand edits break the micro-spacing fit.
"""
import argparse
import json
import sys
from pathlib import Path

from common import load_form, load_json, save_json, utf8_stdout
from opr_acronyms import build_remarks
from opr_fit import fit_draft, fitter_from_args, show
from opr_lint import lint, stale_fits
from rules import Approvals

ORDER = {"error": 0, "warning": 1, "judgment": 2, "info": 3}


def report_fit(results, alt_results):
    show(results, False)
    bad = [r["where"] for r in results if r["status"] != "fits"]
    print(f"\nfit: {len(results) - len(bad)}/{len(results)} lines fit" + (f"; fix: {', '.join(bad)}" if bad else ""))
    alt_bad = [r["where"] for r in alt_results if r["status"] != "fits"]
    if alt_results:
        print(f"fit: {len(alt_results) - len(alt_bad)}/{len(alt_results)} alternates fit" + (f"; fix: {', '.join(alt_bad)}" if alt_bad else ""))
    return bad


def report_lint(findings, as_json=False):
    findings.sort(key=lambda f: (ORDER[f["severity"]], f["where"]))
    if as_json:
        print(json.dumps(findings, ensure_ascii=False, indent=1))
    else:
        print()
        for f in findings:
            print(f"{f['severity'].upper():8} {f['rule']:13} {f['where']:22} {f['message']}")
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ORDER}
    if not as_json:
        print(f"\nlint: {counts['error']} errors, {counts['warning']} warnings, {counts['judgment']} judgment, {counts['info']} info")
    return counts["error"]


def rebuild_sec_x(path):
    draft = load_json(path)
    form = load_form(draft.get("form"), path.parent)
    remarks, missing, _ = build_remarks(draft, form, Approvals(path.parent))
    # generated Sec X is a record only; 'remarks' stays null so check, guard and build regenerate it alike.
    # A 'remarks' equal to earlier generated text (older builds stored it there) is migrated back to auto.
    if draft.get("remarks") in (remarks, draft.get("remarks_auto")):
        draft["remarks"] = None
    draft["remarks_auto"] = remarks
    save_json(path, draft)
    for acr, hint in missing:
        print(f"Sec X: '{acr}' needs a meaning in draft['acronyms'] ({hint})")


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "check", "fit", "lint", "measure"])
    ap.add_argument("draft", nargs="+", help="draft.json (measure: one or more quoted lines)")
    ap.add_argument("--out")
    ap.add_argument("--write", action="store_true", help="fit: store the results in draft.json")
    ap.add_argument("--apply-abbrev-set", action="store_true", help="apply draft.abbrev_set to every line first")
    ap.add_argument("--force", action="store_true", help="build: render even with lint errors")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--font", help="measure: font file (default Times New Roman; or OPR_FONT)")
    args = ap.parse_args()

    if args.cmd == "measure":
        fitter, _ = fitter_from_args(argparse.Namespace(spaces="adjusted", width=None, tol=None, font=args.font, form=None))
        show([fitter.fit(ln) for ln in args.draft], args.json)
        return
    path = Path(args.draft[0])

    if args.cmd == "lint":
        sys.exit(1 if report_lint(lint(path), args.json) else 0)
    # a hand edit of 'fitted' would be overwritten by the fit below; stop before it is lost
    edits = [s for s in stale_fits(load_json(path), load_form(load_json(path).get("form"), path.parent)) if s[0] == "error"]
    if edits:
        for _, _, where, msg in edits:
            print(f"ERROR    fit           {where:22} {msg}")
        sys.exit(f"\nstopped: {len(edits)} hand edit(s) in draft.json would be lost; nothing was changed")
    if args.cmd == "fit":
        results, alts, _ = fit_draft(path, args.write, args.apply_abbrev_set)
        bad = report_fit(results, alts)
        if not args.write:
            print("(dry run: add --write to store the fitted spacing)")
        sys.exit(1 if bad else 0)
    if args.cmd == "check":
        results, alts, fitted = fit_draft(path, False, args.apply_abbrev_set)
        report_fit(results, alts)
        sys.exit(1 if report_lint(lint(path, draft=fitted)) else 0)

    # build
    report_fit(*fit_draft(path, True, args.apply_abbrev_set)[:2])
    rebuild_sec_x(path)
    findings = lint(path)
    errors = report_lint(findings)
    if errors and not args.force:
        sys.exit(f"\nnot rendered: fix the {errors} lint error(s) first (or pass --force for a working copy)")
    from opr_docx import render

    out = render(path, args.out, [f for f in findings if f["severity"] in ("error", "warning", "judgment")])
    print(f"\nwrote {out}")
    if load_json(path).get("settings", {}).get("export_reports", True):
        from md_docx import export_reports

        for p in export_reports(path.parent, out.parent):
            print(f"wrote {p}")


if __name__ == "__main__":
    main()
