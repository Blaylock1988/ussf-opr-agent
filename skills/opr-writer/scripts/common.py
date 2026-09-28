"""Shared helpers for the opr-writer scripts: paths, font discovery, measurement, JSON I/O."""
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = SKILL_DIR / "reference"
DATA_DIR = REFERENCE_DIR / "data"
FORMS_DIR = DATA_DIR / "forms"

DEFAULT_FORM = "daf707-20240213"

# Width-adjusting spaces (bullet-buddy technique). Advances in Times New Roman, 2048 units/em:
# normal 512, U+2004 683 (+171), U+2006 341 (-171), U+2009 410 (-102).
SPACE = " "
THICK = "\u2004"   # 1/3 em
SIX_PER_EM = "\u2006"  # 1/6 em
THIN = "\u2009"    # 1/5 em
ADJUSTED_SPACES = (THICK, SIX_PER_EM, THIN, "\u2005")

FONT_CANDIDATES = {
    "Windows": [r"C:\Windows\Fonts\times.ttf"],
    "Darwin": [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/Library/Fonts/Times New Roman.ttf",
    ],
    "Linux": [
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/times.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/liberation-serif/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
    ],
}


def utf8_stdout():
    """Windows consoles default to cp1252 and crash on U+2006; force UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def find_font(explicit=None):
    """Return a Times New Roman (or metric-compatible Liberation Serif) TTF path."""
    if explicit:
        if Path(explicit).is_file():
            return str(explicit)
        sys.exit(f"Font not found: {explicit}")
    env = os.environ.get("OPR_FONT")
    if env and Path(env).is_file():
        return env
    for path in FONT_CANDIDATES.get(platform.system(), []) + sum(FONT_CANDIDATES.values(), []):
        if Path(path).is_file():
            return path
    sys.exit(
        "Times New Roman not found. Install it (or Liberation Serif, which is metric-compatible) "
        "and pass --font <path> or set OPR_FONT."
    )


class Ruler:
    """Measures rendered text width in millimetres at a given point size."""

    SCALE = 100  # render at 100x point size for sub-point precision

    def __init__(self, font_path=None, size_pt=12.0):
        from PIL import ImageFont

        self.font_path = find_font(font_path)
        self.size_pt = size_pt
        self._font = ImageFont.truetype(self.font_path, int(size_pt * self.SCALE))

    def mm(self, text):
        return self._font.getlength(text) / self.SCALE * 25.4 / 72

    def em_mm(self):
        return self.size_pt * 25.4 / 72


def normalize_spaces(text):
    """Collapse width-adjusting spaces back to plain spaces."""
    for ch in ADJUSTED_SPACES:
        text = text.replace(ch, SPACE)
    return text


INSTALL_MANIFEST = ".installed_from.json"  # written by install.py into each installed copy


def skill_hash(root=SKILL_DIR):
    """Content fingerprint of a skill folder (install.py computes the same), to spot a stale installed copy."""
    h = hashlib.sha1()
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and p.name != INSTALL_MANIFEST and "__pycache__" not in rel and p.suffix != ".pyc" and ".pytest_cache" not in rel:
            h.update(rel.encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:12]


def text_hash(text):
    """Short fingerprint of a line's text, stored at fit time to tell a hand-edited 'fitted' from a refit-pending 'text'."""
    return hashlib.sha1(normalize_spaces(text).encode("utf-8")).hexdigest()[:12]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


VERB_LISTS = ("buckets", "skills", "approved_forms", "unapproved_forms")


def load_verbs():
    """The action-verb lexicon, with the fields the file omits when empty filled back in."""
    verbs = load_json(DATA_DIR / "action_verbs.json")["verbs"]
    for v in verbs:
        for k in VERB_LISTS:
            v.setdefault(k, [])
        v["chars"] = len(v["verb"])
    return verbs


def save_verbs(path, lexicon):
    """Write the lexicon compactly: one verb per line, empty lists and derived fields left out."""
    verbs = [{"verb": v["verb"], "tier": v["tier"], **{k: v[k] for k in VERB_LISTS if v.get(k)}} for v in lexicon["verbs"]]
    head = {k: v for k, v in lexicon.items() if k != "verbs"}
    head["fields"] = ", ".join(VERB_LISTS) + " are omitted when empty"
    text = json.dumps(head, indent=2, ensure_ascii=False)[:-2] + ',\n  "verbs": [\n' + \
        ",\n".join("    " + json.dumps(v, ensure_ascii=False) for v in verbs) + "\n  ]\n}\n"
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path, text):
    """Write UTF-8 text with CRLF line endings."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)


def load_form(name=None, work_dir=None):
    """Load a form profile; a user override at <work_dir>/form.json wins."""
    if work_dir and (Path(work_dir) / "form.json").is_file():
        return load_json(Path(work_dir) / "form.json")
    return load_json(FORMS_DIR / f"{name or DEFAULT_FORM}.json")


def data(name):
    return load_json(DATA_DIR / name)


def iter_lines(draft, form):
    """Yield (section_key, index, line_dict) for every drafted line in form order."""
    for sec in form["sections"]:
        lines = draft.get("sections", {}).get(sec["key"], {}).get("lines", [])
        for i, line in enumerate(lines):
            yield sec["key"], i, line
