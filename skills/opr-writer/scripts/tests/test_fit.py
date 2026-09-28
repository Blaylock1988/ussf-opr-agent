import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import Ruler, normalize_spaces  # noqa: E402
from opr_fit import Fitter, apply_abbrev_set  # noqa: E402

MAX, TOL = 201.05, 0.30

# Fictional lines of realistic OPR length (a few mm over/under the edge before adjustment).
SAMPLES = [
    "- Rebuilt sq $48M O&M spend plan; realigned 31 funding lines in 2 wks--closed 18% shortfall f/4 GPS grnd sys",
    "- Steered sq FY28 WSS POM; built 142 rqmts/resolved 900 HHQ comments--secured $1.2B FYDP f/6 SATCOM prgms",
    "- Forged 3-nation data-sharing pact; synced 11 ops ctrs w/allied partners--cut warning timelines 40% f/2 CCMDs",
    "- Salvaged failing $9M s/w upgrade; re-baselined sched/mng'd 4 ktrs--fielded 2 mths early f/640 warfighters",
]


class FitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fitter = Fitter(Ruler(), MAX, TOL, "adjusted")

    def test_samples_fit_window(self):
        for s in SAMPLES:
            r = self.fitter.fit(s)
            with self.subTest(s=s):
                if r["status"] == "fits":
                    self.assertLessEqual(r["fitted_width_mm"], MAX)
                    self.assertGreaterEqual(r["fitted_width_mm"], MAX - TOL)
                    self.assertEqual(normalize_spaces(r["fitted"]), s)
                else:  # too far off for spaces alone: must report how much to change
                    self.assertNotEqual(r["chars_to_change"], 0)

    def test_dash_space_never_adjusted(self):
        r = self.fitter.fit(SAMPLES[0])
        self.assertTrue(r["fitted"].startswith("- "))

    def test_too_long_detected(self):
        r = self.fitter.fit(SAMPLES[0] + " plus a long tail of extra words that cannot possibly fit")
        self.assertEqual(r["status"], "too_long")

    def test_abbrev_set_consistent(self):
        out = apply_abbrev_set("- Coordinated support for the team with partners", {"for": "f/", "with": "w/", "coordinated": "coord'd"})
        self.assertEqual(out, "- Coord'd support f/the team w/partners")

    @unittest.skipUnless(os.environ.get("OPR_CALIBRATION_FILE"), "set OPR_CALIBRATION_FILE to real fitted OPR lines")
    def test_calibration_real_lines(self):
        lines = [ln.strip("\r\n") for ln in open(os.environ["OPR_CALIBRATION_FILE"], encoding="utf-8") if ln.startswith("- ")]
        ruler = Ruler()
        for ln in lines:
            with self.subTest(ln=ln[:40]):
                # real lines were fitted by eye/other tools: none may exceed the edge by more than rendering noise
                self.assertTrue(199.5 <= ruler.mm(ln) <= 201.3, f"{ruler.mm(ln):.2f} mm")
                self.assertEqual(self.fitter.fit(normalize_spaces(ln))["status"], "fits")


if __name__ == "__main__":
    unittest.main()
