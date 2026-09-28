import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opr_acronyms import build_remarks  # noqa: E402
from opr_lint import lint  # noqa: E402
from common import load_form  # noqa: E402
from rules import Approvals  # noqa: E402


def draft(rater, additional=None, jd=None, acronyms=None, remarks=None, abbrev=None):
    return {
        "form": "daf707-20240213",
        "acronyms": acronyms or {},
        "remarks": remarks,
        "abbrev_set": abbrev or {},
        "sections": {
            "job_description": {"duty_title": "Program Manager", "lines": [{"text": t} for t in (jd or ["- Leads 12-mbr tm; manages 7 kts"] * 1)]},
            "rater": {"lines": [{"text": t} for t in rater]},
            "additional_rater": {"lines": [{"text": t} for t in (additional or ["- #1/7 Dir O-4s; top FGO--sq CC next"])]},
        },
    }


def run(d):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "draft.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        return lint(p, use_ruler=True)


def msgs(findings, rule=None, severity="error"):
    return [f["message"] for f in findings if f["severity"] == severity and (rule is None or f["rule"] == rule)]


class LintTests(unittest.TestCase):
    def test_unapproved_and_wrong_case_abbreviations(self):
        f = run(draft(["- Forged jt plan w/gov't ktrs; saved 5 mos--lgst gain f/Tm", "- #1/3 Del O-4s; sharp--sq CC next"]))
        text = " ".join(msgs(f, "abbreviation"))
        for bad in ("'jt'", "'gov't'", "'mos'", "'lgst'"):
            self.assertIn(bad, text)
        self.assertIn("'Tm'", " ".join(msgs(f, "abbreviation", "judgment")))

    def test_d_form_needs_approved_verb_base(self):
        f = run(draft(["- Elim'd 4 gaps; coord'd 9 orgs--saved $2M", "- #1/3 Del O-4s; sharp--sq CC next"]))
        text = " ".join(msgs(f, "abbreviation"))
        self.assertIn("elim'd", text.lower())
        self.assertNotIn("coord'd", text)

    def test_repeated_number_in_section(self):
        f = run(draft(["- Forged 12 pacts; linked 3 ctrs--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertTrue(any("'12' repeats" in m for m in msgs(f, "numbers")))

    def test_repeated_opening_verb_abbrev_equivalence(self):
        f = run(draft(["- Coordinated 4 mtgs; set agenda--aligned 9 orgs", "- Coord'd 6 reviews; closed 30 items--cut risk", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertTrue(any("Coordinated" in m for m in msgs(f, "verbs")))

    def test_banned_content(self):
        f = run(draft(["- Quarterbacked 3 events; shows potential--promote now", "- #1/3 Del O-4s; sharp--IDE in-res"]))
        text = " ".join(msgs(f, "content")) + " ".join(msgs(f, "verbs"))
        self.assertIn("potential", text)
        self.assertIn("in-res", text.lower())
        self.assertIn("Quarterbacked", text)

    def test_primary_strat_required(self):
        f = run(draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", "- #1/5 Program Managers; sharp--sq CC next"]))
        self.assertTrue(any("primary rank strat" in m for m in msgs(f, "strat")))

    def test_consistency_for_vs_f_slash(self):
        f = run(draft(["- Forged plan f/3 wgs; built tools for 9 orgs--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertTrue(any("'for'" in m for m in msgs(f, "consistency")))

    def test_acronym_meaning_mismatch_needs_definition(self):
        d = draft(["- Built 35 STOs; synced 4 ctrs--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"],
                  acronyms={"STO": "Space Tasking Order"})
        form = load_form("daf707-20240213")
        remarks, missing, _ = build_remarks(d, form, Approvals())
        self.assertIn("Space Tasking Order (STO)", remarks)

    def test_common_acronym_listed_in_remarks_is_error(self):
        d = draft(["- Built HHQ plan; synced 4 ctrs--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"],
                  remarks="Higher Headquarters (HHQ)")
        f = run(d)
        self.assertTrue(any("HHQ" in m and "common" in m for m in msgs(f, "acronyms")))

    def test_bottom_half_strat_rules(self):
        body = "- Forged 4 pacts; linked 3 ctrs--armed 9 units"
        # bottom-half primary alone: warn (omit it, keep the push)
        f = run(draft([body, "- #3/4 Del O-4s; sharp--sq CC next"]))
        self.assertTrue(any("below the top half" in m for m in msgs(f, "strat", "warning")))
        # bottom-half primary with a strong secondary: the one allowed exception (judgment, not error)
        f = run(draft([body, "- #3/4 Del O-4s, #1/7 PMs; sharp--sq CC next"]))
        self.assertFalse([m for m in msgs(f, "strat") if "top half" in m or "#3/4" in m])
        self.assertTrue(any("secondary follows" in m for m in msgs(f, "strat", "judgment")))
        # bottom-half secondary: error
        f = run(draft([body, "- #1/1 Del O-4s, #3/4 PMs; sharp--sq CC next"]))
        self.assertTrue(any("secondary" in m for m in msgs(f, "strat")))

    def test_numbers_compare_within_category(self):
        f = run(draft(["- Secured $5B FYDP; won 5 awds--cut 30% risk f/517 users", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertFalse(msgs(f, "numbers"))
        f = run(draft(["- Secured $5B FYDP; won 7 awds--cut 30% risk", "- Saved $5B in 2 wks; fixed 9 gaps--armed 30% more units",
                       "- #1/3 Del O-4s; sharp--sq CC next"]))
        text = " ".join(msgs(f, "numbers"))
        self.assertIn("'$5B' repeats", text)
        self.assertIn("'30%' repeats", text)

    def test_round_numbers_warned(self):
        f = run(draft(["- Trained 500+ mbrs; briefed over 300 users--armed 1,000 ops", "- #1/3 Del O-4s; sharp--sq CC next"]))
        text = " ".join(msgs(f, "numbers", "warning"))
        for raw in ("'500+'", "'over 300'", "'1,000'"):
            self.assertIn(raw, text)
        f = run(draft(["- Trained 517 mbrs; saved $1,500--armed 12K users", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertFalse([m for m in msgs(f, "numbers", "warning") if "estimate" in m])

    def test_double_credit_and_buzzwords(self):
        d = draft(["- Forged 4 pacts; linked 3 ctrs--armed pacing sys", "- Built 6 tools; synced 9 orgs--boosted lethality f/NC3 ops",
                   "- Wrote 2 plans; fixed 5 gaps--raised lethality & met pacing challenge", "- #1/3 Del O-4s; sharp--sq CC next"])
        d["sections"]["rater"]["lines"][0]["ledger"] = ["L1"]
        d["sections"]["rater"]["lines"][1]["ledger"] = ["L1"]
        f = run(d)
        self.assertTrue(any("L1" in m for m in msgs(f, "double_credit", "warning")))
        buzz = " ".join(msgs(f, "buzzword", "warning"))
        self.assertIn("'lethality' used 2", buzz)
        self.assertIn("'pacing' used 2", buzz)  # the word counts inside 'pacing challenge' too
        self.assertNotIn("'pacing challenge'", buzz)

    def test_guard_rejects_noncompliant_alternates_and_spares(self):
        d = draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", "- #1/3 Del O-4s; sharp--sq CC next"],
                  jd=["- Leads 19-mbr tm; manages 7 kts"])
        d["sections"]["rater"]["lines"][0]["alternates"] = ["- Built 4 pacts w/19 mbrs; linked 3 ctrs--armed 9 units",
                                                            "- Built 4 pacts; linked 3 ctrs--armed 9 units"]
        d["spares"] = [{"text": "- Forged 11 tools; synced 6 orgs--cut 2 wks"}]
        guard = msgs(run(d), "guard")
        self.assertTrue(any("alt 1" in m or "19" in m for m in guard))
        self.assertFalse([m for m in guard if "alt 2" in m])
        self.assertTrue(any("Forged" in m for m in guard))  # the spare reuses an opening verb

    def test_unit_policy_controls_degree_rule(self):
        line = "- #1/3 Del O-4s; earned MBA online--sq CC next"
        for policy, sev in (("forbid", "error"), ("warn", "warning")):
            d = draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", line])
            d["settings"] = {"policies": {"degree_completion": policy}}
            self.assertTrue(any("degree_completion" in m for m in msgs(run(d), "content", sev)), policy)
        d = draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", line])
        d["settings"] = {"policies": {"degree_completion": "allow"}}
        self.assertFalse(any("degree" in f["message"] for f in run(d)))

    def test_afpc_meaning_and_category(self):
        ap = Approvals()
        self.assertEqual(ap.acronym_status("AT", "Annual Tour")[0], "afpc")
        self.assertEqual(ap.acronym_status("ADCON")[0], "approved")
        self.assertEqual(ap.acronym_status("AFLCMC", None, "organizations")[0], "category")
        self.assertEqual(ap.acronym_status("AFLCMC")[0], "needs_definition")

    def test_board_audience_resolution(self):
        from audience import resolve
        self.assertEqual(resolve("Maj", "63A4")["category"], "LSF-F")
        self.assertEqual(resolve("Lt Col", "13S3")["category"], "LSF-O")
        self.assertEqual(resolve("Capt", "63A3")["category"], "LSF")
        self.assertEqual(resolve("Col", "62E4")["category"], "LSF")
        self.assertEqual(resolve("Maj", "17D3", "USAF")["category"], "LAF-I")

    def test_out_of_field_jargon_flagged_for_board(self):
        from audience import resolve
        d = draft(["- Wrote 35 STOs; built PDR pkg--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"],
                  acronyms={"STO": "Space Tasking Order"})
        d["board"] = resolve("Maj", "63A4")
        f = run(d)
        aud = " ".join(m["message"] for m in f if m["rule"] == "audience")
        self.assertIn("'STO'", aud)       # ops jargon for an acquisition board
        self.assertNotIn("'PDR'", aud)    # native to the board's field

    def test_active_voice_and_past_tense(self):
        f = run(draft(["- Leads 4 pacts; linked 3 ctrs--armed 9 units", "- Plan was approved by HHQ; linked 5 ctrs--armed 8 units",
                       "- Selected as acting dep; ran 42-mbr div--stood up new sq", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertTrue(any("past tense" in m for m in msgs(f, "tense")))
        self.assertTrue(any("active voice" in m for m in msgs(f, "voice", "warning")))
        self.assertTrue(any("Selected" in m for m in msgs(f, "voice", "judgment")))

    def test_structure_acronyms_accepted_everywhere(self):
        from audience import resolve
        ap = Approvals()
        for acr in ("SFI", "CFC", "STARCOM", "USSF-INDOPAC", "USINDOPACOM", "SYD"):
            self.assertIn(ap.acronym_status(acr)[0], ("structure", "approved"), acr)
        d = draft(["- Synced SFI & S4S plans; linked 3 ctrs--armed 9 units", "- #1/3 Del O-4s; sharp--sq CC next"])
        d["board"] = resolve("Maj", "63A4")
        self.assertFalse(any(m["rule"] == "audience" and "SFI" in m["message"] for m in run(d)))

    def test_ordinals_and_designators(self):
        f = run(draft(["- Forged 2nd plan f/MD5; linked 61st ABG--armed 9 units", "- #1/3 Del O-4s; sharp--sq CC next"]))
        text = " ".join(msgs(f))
        self.assertIn("2d", text)
        self.assertIn("MD 5", text)
        self.assertIn("61st", text)

    # ---- 2026-09-27 test report regressions
    def test_buzzword_after_impact_connector(self):
        f = run(draft(["- Built 6 tools; synced 9 orgs--lethality f/3 CCMDs", "- Wrote 2 plans; fixed 5 gaps--lethality",
                       "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertIn("'lethality' used 2", " ".join(msgs(f, "buzzword", "warning")))

    def test_guard_ignores_base_findings_shifted_by_spares(self):
        d = draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", "- #3/4 Del O-4s; sharp--sq CC next"])
        d["spares"] = [{"text": "- Wrote 11 tools; synced 6 orgs--cut 2 wks"}, {"text": "- Built 13 plans; fixed 8 gaps--saved 5 wks"}]
        guard = [x for x in run(d) if x["rule"] == "guard"]
        self.assertFalse([x for x in guard if "top half" in x["message"]], guard)

    def test_push_only_last_line_when_strat_omitted(self):
        f = run(draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", "- SD 7 FGOY! My top planner--sq CC next, SDE soonest"]))
        self.assertFalse([x for x in f if x["rule"] == "strat" and x["severity"] == "error" and x["where"].startswith("rater")])
        self.assertTrue(any("no stratification" in m for m in msgs(f, "strat", "judgment")))
        self.assertFalse([x for x in f if x["rule"] == "verbs" and x["where"] == "rater[2]"])

    def test_generated_sec_x_is_not_linted_as_hand_written(self):
        d = draft(["- Built STO plan; synced 4 ctrs--armed 12 units", "- #1/3 Del O-4s; sharp--sq CC next"],
                  acronyms={"STO": "Space Tasking Order"}, remarks="Space Tasking Order (STO)")
        d["remarks_auto"] = "Space Tasking Order (STO)"
        d["sections"]["rater"]["lines"][0]["alternates"] = ["- Built ops plan; synced 4 ctrs--armed 12 units"]
        f = run(d)
        self.assertFalse([m for m in msgs(f) if "not used in the report" in m])

    def test_hand_edited_fitted_is_caught(self):
        from common import text_hash
        d = draft(["- Forged 4 pacts; linked 3 ctrs--armed 9 units", "- #1/3 Del O-4s; sharp--sq CC next"])
        line = d["sections"]["rater"]["lines"][0]
        line.update(fitted="- Forged 4 pact; linked 3 ctrs--armed 9 units", fit_hash=text_hash(line["text"]), status="fits")
        self.assertTrue(any("hand-edited" in m for m in msgs(run(d), "fit")))
        line["fit_hash"] = "stale"  # text changed after the fit: normal editing, refit pending
        f = run(d)
        self.assertFalse([m for m in msgs(f, "fit") if "hand-edited" in m])
        self.assertTrue(any("changed since the last fit" in m for m in msgs(f, "fit", "warning")))

    def test_lint_false_positives_from_drafting(self):
        f = run(draft(["- Cut over 2,317 radios; briefed sq/CC--armed SES-level review", "- #1/3 Del O-4s; sharp--sq CC next"]))
        self.assertFalse([m for m in msgs(f, "numbers", "warning") if "over" in m])
        acr = " ".join(msgs(f, "acronyms"))
        self.assertNotIn("'sq'", acr)
        self.assertNotIn("SES-level", acr)

    def test_vetted_round_number(self):
        d = draft(["- Moved 2,317 radios across 100 sites--8x capacity", "- #1/3 Del O-4s; sharp--sq CC next"])
        d["ledger"] = [{"id": "L1", "summary": "AEHF", "exact_numbers": ["100"]}]
        d["sections"]["rater"]["lines"][0]["ledger"] = ["L1"]
        f = run(d)
        self.assertFalse([m for m in msgs(f, "numbers", "warning") if "'100'" in m])
        self.assertTrue(any("vetted" in m for m in msgs(f, "numbers", "info")))

    def test_board_read_judgments(self):
        f = run(draft(["- Moved 2,317 radios across 100 sites--8x capacity", "- Hit 100% on time; kept 31 kts--0 terminations",
                       "- #1/3 Del O-4s; top planner--sq CC next"], additional=["- #1/7 Dir O-4s; superb planner--sq CC next"]))
        text = " ".join(msgs(f, "board_read", "judgment"))
        self.assertIn("planner", text)
        self.assertIn("'100%' sits next to '100'", text)

    def test_docx_highlights_any_bracket_placeholder(self):
        from opr_docx import PLACEHOLDER
        for ph in ("[2,5xx]", "[N]", "[test date]", "#[N]/[M]"):
            self.assertTrue(PLACEHOLDER.fullmatch(ph), ph)
        self.assertFalse(PLACEHOLDER.search("swap for rater[4]"))


if __name__ == "__main__":
    unittest.main()
