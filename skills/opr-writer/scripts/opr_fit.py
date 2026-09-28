"""Measure OPR lines and fit them flush to the form's right edge.

Width model: Times New Roman 12 pt, 201.05 mm line (DAF 707), measured with real glyph advances.
Space adjustment (bullet-buddy technique, extended): normal spaces are swapped for
U+2004 (+0.354 mm), U+2006 (-0.354 mm) or U+2009 (-0.212 mm) to land in [max - tol, max].

Usage:
  opr_fit.py measure "- Line one" "- Line two"      measure/fit ad-hoc lines
  opr_fit.py file lines.txt                         measure/fit each line of a text file
  opr_fit.py draft draft.json [--write] [--apply-abbrev-set]
                                                    fit every line, spare and alternate in a draft;
                                                    --write stores results
Options: --spaces adjusted|normal  --width MM  --tol MM  --font PATH  --form NAME  --json
"""
import argparse
import itertools
import json
import re
import sys
from pathlib import Path

from common import (SIX_PER_EM, SPACE, THICK, THIN, Ruler, iter_lines, load_form, load_json,
                    normalize_spaces, save_json, text_hash, utf8_stdout)

NORMAL_MODE_TOL_MM = 2.0  # without space adjustment, "fits" means within 2 mm of the edge
SAFETY_MM = 0.01  # aim just inside the edge so rounding never pushes a line over


class Fitter:
    def __init__(self, ruler, max_mm, tol_mm, mode="adjusted"):
        self.r, self.max, self.tol, self.mode = ruler, max_mm, tol_mm, mode
        base = ruler.mm(SPACE)
        self.deltas = {THICK: ruler.mm(THICK) - base, SIX_PER_EM: ruler.mm(SIX_PER_EM) - base,
                       THIN: ruler.mm(THIN) - base}
        self.avg_char_mm = ruler.mm("abcdefghijklmnopqrstuvwxyz ") / 27

    @staticmethod
    def adjustable_positions(text):
        """Indices of spaces that may be swapped; never the space after the leading '- '."""
        skip = 1 if text.startswith("- ") else -1
        return [i for i, ch in enumerate(text) if ch == SPACE and i != skip]

    def fit(self, text):
        base = normalize_spaces(text).rstrip()
        w0 = self.r.mm(base)
        result = {"text": base, "width_mm": round(w0, 3)}
        if self.mode == "normal":
            return self._finish(result, base, w0, NORMAL_MODE_TOL_MM)

        pos = self.adjustable_positions(base)
        n = len(pos)
        best = None  # (width, swaps, a, b, c)
        dt, ds, dn = self.deltas[THICK], self.deltas[SIX_PER_EM], self.deltas[THIN]
        for a in range(n + 1):
            for b in range(n + 1 - a):
                if a and b:
                    continue  # growing and shrinking at once only wastes swaps
                for c in range(n + 1 - a - b):
                    w = w0 + a * dt + b * ds + c * dn
                    if w > self.max - SAFETY_MM:
                        continue
                    key = (round(w, 4), -(a + b + c))
                    if best is None or key > (round(best[0], 4), -best[1]):
                        best = (w, a + b + c, a, b, c)
        if best is None:  # even all-shrink is too wide
            return self._finish(result, base, w0, self.tol)
        _, _, a, b, c = best
        fitted = self._apply(base, pos, a, b, c)
        return self._finish(result, fitted, self.r.mm(fitted), self.tol)

    @staticmethod
    def _apply(text, pos, a, b, c):
        k = a + b + c
        if k == 0:
            return text
        # Spread swaps evenly across the line so no region looks gappy or cramped.
        n = len(pos)
        if k >= n:
            chosen = pos[:k]
        elif k == 1:
            chosen = [pos[n // 2]]
        else:
            chosen = [pos[round(i * (n - 1) / (k - 1))] for i in range(k)]  # step >= 1, so unique
        kinds = [THICK] * a + [SIX_PER_EM] * b + [THIN] * c
        # interleave kinds so each type is spread out
        order = sorted(range(k), key=lambda i: (i % 2, i))
        chars = list(text)
        for slot, kind in zip((chosen[i] for i in order), kinds):
            chars[slot] = kind
        return "".join(chars)

    def _finish(self, result, fitted, w, tol):
        delta = w - self.max
        if w > self.max + SAFETY_MM:
            status = "too_long"
        elif w < self.max - tol:
            status = "too_short"
        else:
            status = "fits"
        result.update({"fitted": fitted, "fitted_width_mm": round(w, 3), "delta_mm": round(delta, 3),
                       "status": status,
                       "chars_to_change": 0 if status == "fits" else int(round(-delta / self.avg_char_mm))})
        return result


# ---------------------------------------------------------------- abbreviation set

def apply_abbrev_set(text, abbrev_set):
    """Apply the report-wide abbreviation set to one line (case-aware, whole words)."""
    for long_, short in sorted(abbrev_set.items(), key=lambda kv: -len(kv[0])):
        tail = r"\s*" if short.endswith("/") else ""  # "for the" -> "f/the" (no space after slash)

        def rep(m, short=short):
            word = m.group(1)
            out = short
            if word[0].isupper() and not short[0].isupper():
                out = short[0].upper() + short[1:]
            return out

        text = re.sub(rf"(?<![\w'/])({re.escape(long_)})(?![\w'])" + tail, rep, text, flags=re.IGNORECASE)
    return text


# ---------------------------------------------------------------- CLI

def fitter_from_args(args, work_dir=None):
    form = load_form(args.form, work_dir)
    ruler = Ruler(args.font, form.get("font_size_pt", 12))
    width = args.width or form["line_width_mm"]
    tol = args.tol if args.tol is not None else form.get("tolerance_mm", 0.30)
    return Fitter(ruler, width, tol, args.spaces), form


def fit_draft(draft_path, write=False, apply_abbrev=False, args=None):
    """Fit every form line, spare and alternate (alternates are stored as fitted text).

    Results are applied to the in-memory draft; write also saves it to draft_path.
    Returns (line_results, alternate_results, draft). Spares are in line_results as spares[n].
    """
    args = args or argparse.Namespace(spaces=None, width=None, tol=None, font=None, form=None)
    path = Path(draft_path)
    draft = load_json(path)
    args.spaces = args.spaces or draft.get("settings", {}).get("spaces", "adjusted")
    args.form = args.form or draft.get("form")
    fitter, form = fitter_from_args(args, path.parent)
    abbrev = draft.get("abbrev_set", {}) if apply_abbrev else {}
    lines = [(f"{k}[{i + 1}]", line) for k, i, line in iter_lines(draft, form)]
    lines += [(f"spares[{n + 1}]", sp) for n, sp in enumerate(draft.get("spares", []))]
    results, alt_results = [], []
    for where, line in lines:
        text = normalize_spaces(line["text"])
        if abbrev:
            text = apply_abbrev_set(text, abbrev)
            line["text"] = text
        r = fitter.fit(text)
        r["where"] = where
        results.append(r)
        line.update({"fitted": r["fitted"], "fit_hash": text_hash(text), "width_mm": r["fitted_width_mm"],
                     "delta_mm": r["delta_mm"], "status": r["status"]})
        alts = line.get("alternates", [])
        for n, alt in enumerate(alts):
            is_dict = isinstance(alt, dict)
            alt_text = normalize_spaces(alt["text"] if is_dict else alt)
            if abbrev:
                alt_text = apply_abbrev_set(alt_text, abbrev)
            ar = fitter.fit(alt_text)
            ar["where"] = f"{where} alt {n + 1}"
            alt_results.append(ar)
            # alternates are stored already fitted so they paste flush, like the lines they replace
            alts[n] = dict(alt, text=ar["fitted"], status=ar["status"]) if is_dict else ar["fitted"]
    if write:
        save_json(path, draft)
    return results, alt_results, draft


def show(results, as_json):
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return
    for r in results:
        tag = r.get("where", "")
        hint = "" if r["status"] == "fits" else f"  ({'cut' if r['status'] == 'too_long' else 'add'} ~{abs(r['chars_to_change'])} chars)"
        print(f"{r['status']:9} {r['fitted_width_mm']:7.2f} mm {r['delta_mm']:+6.2f}  {tag:22} {r['text']}{hint}")


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["measure", "file", "draft"])
    ap.add_argument("items", nargs="*")
    ap.add_argument("--spaces", choices=["adjusted", "normal"], default=None)
    ap.add_argument("--width", type=float)
    ap.add_argument("--tol", type=float)
    ap.add_argument("--font")
    ap.add_argument("--form")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--apply-abbrev-set", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "draft":
        results, alt_results, _ = fit_draft(args.items[0], args.write, args.apply_abbrev_set, args)
        show(results, args.json)
        bad = [r for r in results if r["status"] != "fits"]
        print(f"\n{len(results) - len(bad)}/{len(results)} lines fit" + (f"; fix: {', '.join(r['where'] for r in bad)}" if bad else ""))
        alt_bad = [r["where"] for r in alt_results if r["status"] != "fits"]
        if alt_results:
            print(f"{len(alt_results) - len(alt_bad)}/{len(alt_results)} alternates fit" + (f"; fix: {', '.join(alt_bad)}" if alt_bad else ""))
        sys.exit(1 if bad else 0)

    args.spaces = args.spaces or "adjusted"
    fitter, _ = fitter_from_args(args)
    if args.cmd == "file":
        with open(args.items[0], encoding="utf-8") as f:
            lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]
    else:
        lines = args.items or [ln.rstrip("\r\n") for ln in sys.stdin if ln.strip()]
    show([fitter.fit(ln) for ln in lines], args.json)


if __name__ == "__main__":
    main()
