---
name: opr-writer
description: Write a complete, board-ready DAF Form 707 Officer Performance Report (USSF/USAF, Lt thru Col) from a folder of guidance, prior OPRs, and accomplishment notes. Drafts the Job Description, Rater, Additional Rater and Reviewer blocks in OPR bullet language, fits every line flush to the form's exact width, lints against the command's approved acronym/abbreviation lists and stratification rules, and exports a DOCX that mirrors the 707. Use when someone asks to write, draft, fix, fit, or review an OPR, OPR bullets, strat/push lines, or a 707.
---

# OPR Writer (DAF Form 707)

You are drafting a promotion-record document. **Accuracy beats flourish.**
- Every claim must trace back to the user's inputs or a cited, user-confirmed public source.
- Never invent metrics, stratifications, awards, or dates.
- The OPR is CUI when filled out. Never include classified information.

**`<skill>`** is the folder that contains this SKILL.md. Run scripts with `python`.

## Workspace
| Path | Role |
|---|---|
| `<folder>/Output/<Name> OPR <period>.docx` | **The deliverable.** Page 1 is for 1:1 copy-paste into myEval or the PDF. Page 2 holds rater notes, alternates and the 4 spare bullets. |
| `<folder>/Output/<Name> OPR <period> - *.docx` | Fact ledger, research report and record review, when the user opted in. |
| `<folder>/_opr_work/draft.json` | Engine state. The user must **never hand-edit it**: that breaks the micro-spacing fit. Change it only through this skill and `opr.py`. To fix a typo, the user tells the agent, which edits `text` and refits. |
| `<folder>/_opr_work/ledger.md` | Human-readable fact ledger with citations. |
| `<folder>/_opr_work/research.md`, `record_review.md`, `career_review.md` | Research report, record review, board-worksheet view. |

## Works in Claude Code and Google Antigravity
| Need | Claude Code | Antigravity (IDE / CLI) |
|---|---|---|
| Ask the user (data or decisions) | `AskUserQuestion` | the approval/question prompt; else a numbered list in chat |
| Web research | `WebSearch` / `WebFetch`, or a deep-research skill | web search / browser tools |
| Tongue and Quill deep lookup | `tq-researcher` subagent | `invoke_subagent` with `reference/tq-researcher-prompt.md` |
| Run scripts | Bash / PowerShell tool | terminal tool |

**Always use the structured prompt** whenever you need data or a decision; chat is the fallback. Batch questions, recommended option first. If a tool isn't available, use the plain equivalent. Never skip the step.

**Windows shells:** never pass inline Python (`python -c "..."`) that contains `$`, backticks or regexes. PowerShell expands `$16B` to nothing and `$?` to `True`. Write a temp `.py` file to the harness's scratch/temp directory and run it.

## Reference files (read on demand)
| File | When |
|---|---|
| `reference/writing-rules.md` | **Always, before drafting.** Content, strats, format, Sec X, rating-chain rules. |
| `reference/bullet-style.md` | **Always, before drafting.** Line grammar, strat/push line, compression ladder, verbs. |
| `reference/interview-and-review.md` | Steps 1–2 and 3c: discovery, routine-item probe, forward-dated work, SURF/duty titles, record review, grade equivalents. |
| `reference/impact-research.md` | Steps 3b and 5b: impact research, the space threat sheet, OPSEC, report format. |
| `reference/daf707-form.md` | Block limits, line geometry, prohibitions. |
| `reference/draft-schema.md` | Before creating or changing `draft.json`. |
| `reference/tongue-and-quill-digest.md` | Punctuation, capitalization, numbers, abbreviations. |
| `reference/data/*.json` | Used by the scripts. Don't read the large ones whole. |

**Context budget:** the skill bundles digests, not full texts. Never read a T&Q PDF or any `*.chunks/` folder whole. Use `scripts/ref_lookup.py "<terms>"` (T&Q digest) or `--source cso` (CSO digest: themes and short quotes), then the tq-researcher. Never read `data/cso_digest.json` or `glossary.json` whole. For other large guidance, read its `*.chunks/index.json`, then only the chunk you need.

## Engine commands (the only ones; don't invent others)
- `python <skill>/scripts/opr.py check <draft.json>`: fit + lint, writes nothing.
- `python <skill>/scripts/opr.py fit <draft.json> --write [--apply-abbrev-set]`: stores fitted spacing for lines, spares and alternates.
- `python <skill>/scripts/opr.py build <draft.json> [--out <path.docx>]`: fit → Sec X → lint → DOCX (+ report DOCXs). Refuses while lint has errors.
- `python <skill>/scripts/opr.py measure "- Line one" ["- Line two" ...]`: measure candidate lines before they go into the draft.
- `check`, `fit` and `build` stop, changing nothing, if a `fitted` string was hand-edited. Move the change into `text`, then rerun.
- Helpers: `extract_inputs.py`, `opr_style.py`, `career_review.py`, `audience.py`, `verbs.py`, `data_check.py`, `ref_lookup.py`.

## Workflow
**Resume check:** if `_opr_work/draft.json` exists, read it, summarize where it stands, and continue from the first unfinished step.

### 0. Setup
- `python -m pip install -r <skill>/scripts/requirements.txt` (ask first).
- `python <skill>/scripts/opr.py measure "- Test line"` proves the font (Times New Roman, or Liberation Serif via `--font`/`OPR_FONT`).
- `python <skill>/scripts/data_check.py --report-thru <period end>`. Tell the user which datasets are stale and where to refresh them. User overrides go in `_opr_work/`. If it prints **STALE INSTALL**, stop and tell the user to run `python install.py update` from the repository first.
- Read `reference/data/board_priorities.json`. Highly valued now: joint/CCMD staff, HQSF/HAF, Pentagon, Indo-Pacific, fitness; deployments less. Put these first or last in a block when held; aim pushes at them when missing.

### 1. Discovery and ingest (`interview-and-review.md` §1)
- **Ask first** for award packages (unit, special, quarterly, annual) and other write-ups from this year, the **AMS SURF**, and the last 3–5 OPRs.
- **Ask whether to also export the ledger and research reports as DOCX** in `Output/` (usually yes) → `draft.settings.export_reports`.
- `python <skill>/scripts/extract_inputs.py "<folder>"`, then read `_opr_work/manifest.json` and the accomplishment and history files in full.
- Guidance files, per the manifest notes:
  - Approved lists that differ from the bundled CFC 26 Jun 2026 set: `build_approved_lists.py "<pdf>" --out "<folder>/_opr_work/approved"`.
  - AFPC list: 28 Oct 24 is bundled. AFPC also approves whole categories (ranks, office symbols, sq-and-above organizations, platforms, symbols/measurements); record each such call in `draft.acronym_categories`.
  - Newer T&Q: see "Updating the Tongue and Quill". Newer CSO compilation: `build_cso_index.py "<pdf>" --out "<folder>/_opr_work/cso"`; it lists C-Notes missing from `data/cso_digest.json`.
- `python <skill>/scripts/opr_style.py "<folder>/_opr_work" --first-name <name>`. Honor the profile, never its `unapproved_history_forms`.

### 2. Intake
Ask, batched in the structured prompt:
- **Board audience:** service, grade, core AFSC/SFSC → `audience.py --grade <g> --core <code> --draft <draft.json> --write`. Write everything for that board (`writing-rules.md` §7).
- **Ratee block:** name, grade, DAFSC/DSFSC, organization/location, period, duty title, SRID, last feedback date.
- **Fitness score, always:** score or category and test date → `draft.ratee.fitness_score`. It prints as a Box I line by default (`fitness_placement`).
- **Author mode:** ratee drafting for the rater (default) or rater writing.
- **Rating chain:** reviewer? rater also reviewer? each evaluator's peer pools.
- **Strats are placeholders by default** (`#[N]/[M] <grade group>`, `#[N]/[M] <duty group>`). No bottom-half strat, **except** a primary that a strong secondary requires; the secondary must be strong enough for the board to overlook it. Keep strats consistent with `career_review.md`.
- **Push targets:** a command push and a DE push in every OPR, consistent with prior OPRs; the Additional Rater's is the strongest. Tailor to grade and career field (`career_review.md` → Development).
- **Unit policies** (ask; never assume) → `draft.settings.policies`: `degree_completion` allow | warn | forbid; special spaces; exclamation points.
- **Awards and nominations** with level. Civilian/other-service sources may state a grade equivalent.
- **Space mode:** `adjusted` (default) or `normal`.
- **Board-priority experience, confirmed by the ratee, never inferred from OPR wording:** joint/CCMD staff, HQSF/HAF, Pentagon, Indo-Pacific, deployments, with years → `_opr_work/career_profile.json`. Supporting work may show joint *impact* but never implies an assignment.

### 3. Fact ledger
Write `_opr_work/ledger.md` and `draft.ledger[]`: ID, action, metrics, scope, impact, level, source, `career_field`.
- **Thin content?** Go line by line until every bullet has source material. Probe routine items ("met budget", "0 findings") with the three questions in `interview-and-review.md` §2.
- **Forward-dated work** likely to finish before closeout is fair game (confirm the date); nothing outside the period. Multi-year acquisition work shows progress, not completion.
- Decode shorthand with `glossary.json` (a decoder, never an approval list). Out-of-field items get plain language.
- **Flag and ask about:** conflicting numbers, out-of-period items, vague or round metrics, extracurriculars (award noms only), in-residence schooling (training report).
- **The user confirms the ledger before you draft.**

### 3b. Impact research
Per `impact-research.md`: exercise scale/tier, joint and warfighter users, short senior-leader quotes (user evidence or public articles only), CSO C-Note tie-ins (`ref_lookup.py "<theme>" --source cso`), doctrine (SFDD-1, SDPs, JP 3-14), and adversary context from `data/space_threats.json` (search for a newer edition; ask the user). **OPSEC:** public, generic query terms only. Log every candidate with its URL in `research.md`; the user confirms before use.

### 3c. Record review
Run `career_review.py "<folder>/_opr_work"` and read `career_review.md`: strats and pushes across OPRs, duty-title progression (never a regression), SCOD and accountability dates, career-field and education guidance. Write `record_review.md` with **Strengthen this OPR** and **Strengthen future boards** (`interview-and-review.md` §4). Walk the user through what the text can't show.

### 4. Allocate
Map each ledger item to exactly one line and each metric to one home. Show the table before drafting.
- **Job Description:** scope only. **Block IV:** 5 lines + strat/push. **Block V:** 3 lines + the report's strongest strat/push. **Block VI:** optional.
- First and last lines of each block are the strongest. Award overflow and significant completions go in the strat line or line 1.

### 5. Draft
Write `draft.json` (see `draft-schema.md`).
- **Alternates:** good ones on at least half the lines, the Job Description and strat/push lines first.
- **Spares:** 4 strong performance bullets in `draft.spares`, fitted, with no reused verbs, numbers or accomplishments.
- Openers: `verbs.py "<topic words>" --draft <draft.json>`. Record non-common acronyms in `draft.acronyms` and program/exercise words in `draft.proper_nouns`.

### 5b. Research report (mandatory after the first draft)
Research the programs, units and systems in the draft, write `research.md` with links and citations, and recommend updated bullets where research found stronger metrics or impacts. Offer them as alternates.

### 6. Fit loop
1. `opr.py fit <draft.json> --write`.
2. `too_long`: compression ladder (`bullet-style.md` §D). Add adopted abbreviations to `draft.abbrev_set`, then `opr.py fit ... --apply-abbrev-set --write` (applies to every line in every block).
3. `too_short`: spell abbreviations back out, then add a metric or sharpen the impact. Never drop an `abbrev_set` entry to lengthen one line.
4. Repeat until every line, spare and alternate `fits` (200.75–201.05 mm).

### 7. Lint loop
`opr.py check <draft.json>`. Fix every **error**, resolve or explain **warnings**, put **judgment** items to the user. Refit after each edit.
- **Whole-OPR guard:** every alternate and spare is audited against the full report (rule `guard`). If a candidate conflicts (e.g. reuses the Job Description's "28"), fail loudly, name the line, and rewrite the candidate. **Never edit other lines to make room.**
- Never silence a rule by editing data files unless the user changes a policy; save overrides in `_opr_work/`.

### 8. Board review pass
Read as a board member (`bullet-style.md` §H): weak "so what?", overreaching impacts, acronym soup, repeated buzzwords. Block V's last line must be the best in the report. Refit and relint after changes.

### 9. Export
`opr.py build <draft.json>`. Report: the file paths, lines fitted, lint errors (must be 0), decisions the rating chain still owns (placeholders, push options), and flagged policy conflicts.

## Updating the Tongue and Quill
The skill bundles only `tongue-and-quill-digest.md` (the OPR-relevant rules), not the full text.
1. `build_tq_index.py "<pdf>" --out "<folder>/_opr_work/tq"` (add `--compare <older local build>` if the user has one).
2. For chapters 8, 19 and 25–28, check each digest rule against the new edition with `ref_lookup.py "<terms>" --dir "<folder>/_opr_work/tq" --chapter N`, and report what changed.
3. Update `tongue-and-quill-digest.md` only where text changed, **with the user's approval**.

## Hard rules (never break)
- Never fabricate a number, stratification, award, or quote. Missing facts become questions or `[placeholders]`. Researched facts are sourced and user-confirmed.
- Never write a promotion recommendation, "shows potential", "in-res", DE-completion comments, or extracurriculars.
- Never reuse an opening verb in Blocks IV–VI (abbreviated forms count), never repeat a number within a section, never let one accomplishment earn credit twice, and use each standout buzzword at most once.
- Prefer precise numbers; "over N"/"N+" is a last resort.
- Use only approved abbreviations, exactly as listed, consistently across all blocks. An acronym is approved only for its listed meaning; anything else is defined in Sec X.
- Never propose an alternate or revision that breaks compliance elsewhere, and never silently edit lines that weren't in question.
- Keep the SSN out of all files.
