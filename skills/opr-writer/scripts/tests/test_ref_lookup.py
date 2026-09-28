import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import DATA_DIR, load_json  # noqa: E402
from ref_lookup import lookup_cso, lookup_tq, terms_of  # noqa: E402


class RefLookupTests(unittest.TestCase):
    def test_tq_digest_section_found(self):
        out = "\n".join(lookup_tq(terms_of("ordinal numbers"), 80))
        self.assertRegex(out, r"## Ch 2[68]")

    def test_tq_finds_ordinal_rule(self):
        self.assertIn("2d, 3d", "\n".join(lookup_tq(terms_of("ordinal numbers"), 80)))

    def test_cso_returns_cnote_with_quote(self):
        out = "\n".join(lookup_cso(terms_of("space control"), 80, "cnote"))
        self.assertIn("C-Note #34", out)
        self.assertIn('quote (p.', out)

    def test_cso_digest_shape(self):
        d = load_json(DATA_DIR / "cso_digest.json")
        cnotes = [e for e in d["entries"] if e["type"] == "cnote"]
        self.assertEqual(sorted(e["n"] for e in cnotes), list(range(1, 43)))
        for e in d["entries"]:
            for q in e.get("quotes", []):
                self.assertLessEqual(len(q["text"].split()), 20, q["text"])
                self.assertTrue(re.fullmatch(r"\d+", str(q["page"])), e["id"])


if __name__ == "__main__":
    unittest.main()
