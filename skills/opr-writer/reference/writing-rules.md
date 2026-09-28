# OPR writing rules

These rules are distilled from four sources:
- The SpOC Writing Guide (Sep 2023) body, §1.2–1.6.
- The CFC Writing Guide Attachments (26 Jun 2026).
- The DAF 707 instructions.
- Rules set by experienced raters.

`opr_lint.py` enforces the checkable ones. The rest are drafting judgment.

> The bundled lists are **CFC 26 Jun 2026 Att 1 (acronyms) and Att 2 (abbreviations)**. They supersede SpOC 2023 Att 1 and Att 2.
> The body rules below come from **SpOC Sep 2023**, because only the CFC *attachments* were available. Swap in the current command guide body when you have it.

## 1. Precedence (highest first)
1. The user's and rating chain's rules: this file's §6 and any `_opr_work/*.json` overrides.
2. The command writing guide: CFC, or a unit guide the user supplies in `Guidance/`.
3. DAFI 36-2406 / SpFI 36-2401, and the DAF 707 instructions.
4. The Tongue and Quill (AFH 33-337).

Known conflicts:
- **Numbers:** T&Q wants exact numbers, and so do boards: precise figures (517) read as measured, round ones (500+, 1,000, "over 300") read as made up. To break a duplicate, reword first, use a different precise figure second, and use "over N"/"N+" only as a last resort. Lint warns on round counts.
- **Small numbers:** T&Q spells out one through nine and uses figures for 10 and up, with commas from 1,000 (ch 28). Money, percents, units of measure (5-wk), multipliers (8x), strats, ratios, designators and any number in a series with a 10+ figure stay as figures. How strictly to apply it is **unit policy** `settings.policies.small_numbers`: follow the command or user writing guide if it states a rule; otherwise ask the user whether to keep it `flexible` (figures allowed to save space; lint judgment) or `strict` (lint warning). `off` disables it.
- **Sub-bullets:** T&Q allows `--` sub-bullets. On the 707 every bullet is one line, and `--` is the inline connector before the impact.
- **Adverb intensifiers:** T&Q likes them. They cost width, so use them rarely and only as a hook.
- **Degree completion:** the user's policy allows it in the strat line, but the 707 and SpOC 1.2.4.10 forbid it. Lint warns, and the rating chain decides.

## 2. Content: what goes in, what stays out
- **Results matter.** Use Action; Result--Impact. Quantify everything, and answer "so what?" at the highest *credible* level (T&Q ch 19: the impact must match the scope of the action).
- Duties tied to the mission or the primary job are strongest. Use additional duties only to fill space (SpOC 1.2.4.5).
- **Worth recording** (SpOC 1.2.3.4):
  - First-ever projects or results.
  - Anything that drew DoD, CSO, CMSSF or senior-officer notice.
  - Being hand-picked.
  - Money or time saved.
  - Deployments or support to operations.
  - Leadership tests.
  - Awards.
- **Extracurriculars never go in directly.** Examples: Space Force Association volunteering, a unit kickball tournament. They belong in award nominations, and the OPR can cite the nomination or win.
- **Work-related volunteer effort that took real work belongs.** Examples: running the commander's promotion ceremony, running a commander's program. Being named an appointee does not count on its own.
- **Award and nomination levels:**

  | Level | How it reads |
  |---|---|
  | Squadron | average |
  | Delta | good |
  | Field command | great |
  | USSF/DAF | the best possible |

  Give the level, not the period: "Dir FGOQ", not "FGOQ 2Q25" (SpOC 1.5.3.8). Quote rating and award titles when helpful, e.g. "Outstanding Performer" (1.5.3.9).
- **Outside-organization awards** (National Space Club's Schriever award, American Legion, Space Force Association and similar) are awarded to the USSF and distributed by HQSF to its units. Being the nominee of one's unit, higher unit or field command is credible and desirable, and the nominating echelon sets the level: "MD 8 NSC Schriever nom" (the Delta's nominee) is correct. Don't rewrite it as a bare national nomination.
- **Team or subordinate awards:** claim leading the team to them ("led tm to 7 FLDCOM awds"), never the awards themselves.
- **Schools that produce a training report** (in-residence DE or courses) never appear. Never write "in-res" (SpOC 1.5.2.4).
- **Significant completions** such as an online or correspondence master's or a certification level may go in the strat/push line or as line 1 overflow (user policy).
  - Certifications raise no conflict.
  - Degree completion conflicts with the 707 instructions and SpOC 1.2.4.10, so flag it for the rating chain.
- **Prohibited:** promotion recommendations, whether specific or implied (SpOC 1.2.4.7), and every topic listed in the 707 instructions. No classified content (1.2.4.1).
- **Never imply the ratee isn't already performing at the next level.** No "shows potential" or "has potential".

## 3. Stratification (SpOC 1.6, plus rating-chain practice)
- **Placeholders are the default.** Write `#[N]/[M] <grade group>` for the primary and `#[N]/[M] <duty group>` for the secondary. Use real numbers only when the user supplies them.
- **Never include a bottom-half strat,** with one exception. #1 of any pool is fine; otherwise N must be at most M/2. A weak strat hurts more than none, so omit it and keep the push.
  - **Exception:** a strong secondary strat requires a primary strat, **even a bottom-half one**. The secondary must be strong enough for the board to overlook the primary: **top third or better** strongly outweighs a bottom-half primary; lower in the top half is questionable (lint warns). Lint marks this as judgment; a bottom-half primary with no secondary is a warning; a bottom-half secondary or a secondary without a primary is an error.
  - **Strat omitted:** the last line keeps its place and becomes award + push only, with no `#`, e.g. `- SD 7 FGOY! My top planner--Del staff next, then sq CC; SDE soonest`. It needs no opening verb. Lint marks it judgment (confirm the omission is intentional).
- **Consistency across OPRs is critical**, especially for Lt Col boards and above. Compare against `_opr_work/career_review.md` before accepting a strat. Block V's strat should be at least as strong as Block IV's.
- **Every OPR carries a next-rank job push and a DE push** that stay consistent year to year. The Additional Rater's push is the strongest.
  - The Career Review worksheet calls it a "command push", but it need not name a command. It must push a **job suited to the next grade** that builds a strong record against the worksheet and current board priorities: command, ML/SML, DO, division chief, HQSF/HAF or joint staff, PEM, or an Exec to a senior principal (`interview-and-review.md` §4). "Chief of Staff" is ambiguous; confirm which role is meant.
  - Use the same peer-group wording in both strat lines (e.g. "O-4s" in both, not "Majors" in one); a board reads them side by side.
- **Program Element Monitor (PEM):** an action officer who manages, advocates for and oversees one Program Element's budget and capability line. It is always a Pentagon job (HQSF or HAF), so it also meets the Pentagon board priority. For **acquisition officers only** (USSF LSF-F / 62E-63A, and USAF acquisition officers equally), it is a highly desirable push as a Maj, or as a Lt Col not yet done. Never use it as an operations push. Define PEM in Sec X.
- **Functional reviewer.** When the rater and additional rater aren't in the ratee's career field, or the field command directs it, a functional may sign as additional rater or reviewer: e.g. a Portfolio Acquisition Executive for a 63A, or a field-command- or PAE-appointed senior chief engineer for a 62E. The functional's strat may override the additional rater's; the additional rater's strat may then move to the rater's line, and the rater's strat drops off. This depends on the chain of command, so ask the user who signs where and which strats appear; never assume it. Lint's "Block V must beat Block IV" check is then advisory.
- Only a **signatory** evaluator may stratify, and only within their own rating chain. The one exception is quoting a deployed LOE stratification.
- An evaluator never quotes a higher evaluator's stratification. A senior rater's stratification may be quoted only when that senior rater signs without comment.
- The format must be quantitative, with a qualified peer group:
  - **Primary: grade** (`#1/10 Majors`, `#1/3 O-4s`).
  - **Secondary: duty or command position** (`#3/41 Flt/CCs`, `#2/6 Sq/CCs`).
  - At most two, primary first. **A #1/1 primary is still mandatory before any secondary.**
  - Vague groups such as "#1/5" or "#1 of 30 officers" are prohibited.
- Selects are stratified only against other selects of the same grade, and frocked officers against the grade they are frocked to.
- Guardians may be stratified against Airmen by grade, but not the other way around. Duty and command strats may mix the two services.
- Completion or non-completion of non-resident DE never factors into a stratification.
- **The tool never invents stratification numbers.** When the ratee drafts, it writes the placeholder `#[N]/[M] [peer group]`.

## 4. Format (SpOC 1.2.4, 1.5; CFC Att 1/2)
- **Active voice, always.** No "was approved by"-style constructions.
  - **Performance lines (Blocks IV–VI) are past tense:** Led, Forged, Synchronized.
  - Recipient-style openers ("Selected as...", "Named...") are passive in effect. Recast them around what the ratee did.
  - The Job Description traditionally uses present tense ("Leads", "Manages"). This is a unit convention; confirm it with the user.
- Every line starts with `- `. No ending punctuation.
- Use `--` with no spaces around it, and `; ` between the action and the result.
- **Acronyms (CFC Att 1):**
  - The "commonly accepted" acronyms are never listed or defined.
  - An acronym is approved **only for its listed meaning**. For example, STO is listed as *Special Technical Operations*, so a Space Tasking Order must be defined in Sec X.
  - **The AFPC list is also approved** (`data/afpc_acronyms.json`, 28 Oct 24 update), again per meaning. For example, it lists AT as *Annual Tour*.
  - **AFPC also approves whole categories:**
    - common ranks and tiers;
    - office symbols (CC, A4, JA);
    - organizations at squadron level and above (e.g. AFGSC, STARCOM, CCMD, CJTF);
    - weapons and platforms (e.g. F-16, MILSTAR);
    - symbols and measurements ($25B, 5%, hrs, FY23).
    
    Each category use is a judgment call. Record it in `draft.acronym_categories`, e.g. `{"USINDOPACOM": "organizations"}`. Such terms need no Sec X entry, but defining one is never wrong.
  - AFPC's principle: performance statements default to **spelling out**. Being on the list doesn't mean you must use the acronym.
  - Any other acronym is defined in Sec X. Use acronyms sparingly, because boards skip acronym soup (1.2.4.4). Lint warns when more than half a line's words are acronyms or abbreviations, and names the terms to spell out.
- **USSF and joint structure acronyms are accepted for every board** (`data/ussf_structure.json`). Every officer is expected to know them:
  - HQSF, the field commands (CFC, formerly SpOC, SSC, STARCOM);
  - the component field commands (SFI, SFK, S4S ...);
  - the Delta types (MD, SD/DEL, SBD, SLD, SYD);
  - centers (CSpOC, NSDC, NSIC);
  - the CCMDs.
  
  These are approved only for the listed meaning, and they are never treated as career-field jargon.
- **Unit-dependent policies** (the answer varies by unit, so ask) live in `draft.settings.policies`, e.g. `degree_completion: allow | warn | forbid`.
- **Abbreviations (CFC Att 2):**
  - Use only approved abbreviations (1.5.1.6), **written exactly as listed, including case**: `Jt`, `tm`, `govt`, `lrgst`, `ntwrk`, `mth`.
  - The only additions allowed are `-'d`, `-'s`, `-s` and `-es`. `-s` and `-es` never go on abbreviated verbs.
  - A `-'d` form needs an approved base that has a verb meaning: coord'd, dir'd, eval'd, mng'd, sync'd, and so on.
  - `f/` and `w/` take **no space after the slash**.
  - `MD #` and `SD #` are written with a space.
- **Symbols** `& # + < % $` are accepted.
- **Consistency:** once a word is abbreviated or `&` is used, use that form **everywhere in the OPR**, in every block including the Job Description. Never mix "for" and "f/", or "and" and "&".
- **Organizations:** `61 ABG`, not "61st ABG" (1.5.3.2). No superscripts (1.5.3.3). Capitalize exercises and operations: `RESOLUTE SPACE`, `ULCHI FREEDOM SHIELD` (1.5.3.7; T&Q ch 27).
- **Ordinals** contract only *nd* and *rd*: 1st, 2d, 3d, 4th, 22d (T&Q p. 334).
- **Ranks** are mixed case: 2d Lt, 1st Lt, Capt, Maj, Lt Col, Col; Spc1–4, Sgt, TSgt… (see `data/ranks.json`).
- Hyphenate two-word modifiers that come before a noun: "error-free", "hand-picked" (1.5.3.11). GO ranks: "2-star" (1.5.3.12).
- **Signature blocks** must use one style throughout (1.5.3.1).
- If the rater is also the reviewer, Sec VI line 1 is `THE RATER IS ALSO THE REVIEWER`.

## 5. Sec X (Remarks) acronym list
- Sort alphabetically **by acronym**, not by the spelled-out word (1.2.4.3).
- Separate entries with `; ` (a semicolon and one space) (1.5.1.3).
- **Never list abbreviations** (1.5.1.4). **Every listed acronym must appear on the front** (1.5.1.5). Never list a common acronym used with its common meaning.
- Format: `Space Tasking Order (STO); Future Years Defense Program (FYDP)` → then sort by acronym.

## 6. Rating-chain rules (user-provided; highest precedence)
1. **Job Description vs. bullets.** The Job Description shows scope without cannibalizing the metrics the bullets need. Every metric has exactly one home.
2. **Bullets.** Use `Action; Result--Impact` or `Action; Impact--Result`: "what you did; how it helped your unit--how it helped the larger unit, the force, or the joint warfighter". Vary the pattern a little.
3. **No repeated number within a section,** even when the repeat is a coincidence. Numbers compare within a kind: dollars, percents and counts are separate, so "$5B" and "5 awds" don't collide. Fix a repeat by rewording first, then a different precise figure; "over N" or "N+" is the last resort. Prefer precise numbers to round ones.
3a. **One accomplishment earns credit once.** Several may feed a larger impact, but each line is unique; lint warns when one ledger item backs two performance lines.
3b. **Alternates and spares obey the whole OPR.** Every alternate and spare is audited against the full report before it is shown (lint rule `guard`). Example: the Job Description says "19-mbr", so no bullet alternate may reuse 19. When a candidate conflicts, fail loudly, name the line, and rewrite the candidate. **Never** edit other lines to make room.
3c. **Standout buzzwords at most once per OPR.** Doctrinal and strategic terms (pacing, lethality, decisive, competitive endurance, integrated deterrence ...) catch the eye, so a repeat reads as filler. The list lives in `data/buzzwords.json`; extend it there or per user in `_opr_work/buzzwords.json`. Lint warns on any repeat.
4. **No repeated opening verb** anywhere in Blocks IV–VI. A spelled-out verb and its abbreviated form count as the same verb (Coordinated = Coord'd). Avoid "Led". Choose distinctive but not outlandish verbs, so the metrics stay the star.
5. **No acronym stacked vertically** on consecutive lines at about the same horizontal position.
6. **Banned verbs and phrases:** Quarterbacked/QB'd, and "shows potential" or anything like it.
7. **Block IV's last line** is the stratification (rank first, then role if any) plus any awards, and it ends with a push to a job that requires the next rank. Say "do the job", never "promote".
8. **Block V's last line** follows the same pattern one level up. Its denominator is ideally larger, and it must be the best strat and push in the report.
9. **First and last lines of each block are the strongest** (primacy and recency). Awards that overflow the strat line go in line 1.
10. **Abbreviations stay consistent across every block.**

## 7. Audience: write for the competitive category's board
Promotion boards meet **within a competitive (USSF) or developmental (USAF) category**, so that category's officers are the readers (`data/competitive_categories.json`).

| Grades | USSF categories |
|---|---|
| O-1 to O-3 | LSF (all line specialties) |
| O-4 to O-5 | **LSF-O** (13A, 13S, 14N, 17X) or **LSF-F** (62E, 63A) |
| O-6 and above | LSF |

The USAF categories are LAF-A, LAF-C, LAF-F, LAF-I, LAF-N and LAF-X.

- `scripts/audience.py --grade <g> --core <AFSC/SFSC>` sets `draft.board`. Run it before drafting.
- **In-field experience:** the board lives the category's jobs, responsibilities and jargon. For an LSF-F board that means POM, PEO, CDR/PDR, CPARS and the like. These can be used, and they are still defined in Sec X if they aren't on an approved list.
- **Out-of-field experience** needs plain language, because the board may not know it. Examples: an acquisition officer's operations tour, an ops officer's staff or acquisition tour, deployed joint staff work.
  - Spell out, or generalize, any acronym that is "common" only inside that other field. STO, SPINS and OPIR are examples for an LSF-F board.
  - Lead with the outcome, not the process.
  - Translate scope into terms the board already weighs: dollars, people, users, commanders served, first-ever.
- `opr_lint.py` flags other-field jargon (from the editable `data/career_field_terms.json`) as *warning* when the acronym isn't approved, or as *judgment* when it is approved but may still be unfamiliar. Tag each ledger item with its `career_field` so out-of-field lines get the reminder.

## 8. Everything here has a date
Approved lists, competitive categories, USSF structure, CSO priorities, and **what boards value** all change. SECWAR, SECAF and CSO priorities shift with leadership and administrations.
- `data/currency.json` records each dataset's published and verified dates, its source, and how to refresh it. `scripts/data_check.py` flags anything overdue.
- `data/board_priorities.json` records current board emphasis, with sources.
  - As of Sep 2026, these are **highly valued**, reflecting SECWAR/SECAF emphasis:
    - **joint experience** (joint or combatant-command staff, including component commands such as U.S. Space Forces-Indo-Pacific);
    - **HQSF or HAF staff** time;
    - **Pentagon** time;
    - **Indo-Pacific** experience;
    - **fitness scores**, a new board data point.
  - Six-month **deployments** (e.g. CJTF-OIR) are valued, but less.
  - Make this experience visible (`career_review.md` shows where the record already carries it), and aim pushes at it when it's missing.
  - Fitness placement on the 707 is not yet published. The DOCX shows it as a Box I `FITNESS SCORE:` line by default (`draft.ratee.fitness_placement`: box1 | remarks | both | none).
- Re-verify this each board cycle. Never present an old priority as current.

## 9. Timelines and process (SpOC 1.2.2, 1.2.4.6)
- Evaluations that need an L2 or CC signature are due 14 days before the SCOD.
- Never sign before the close-out date.
- The feedback date must fall within the reporting period (1.5.1.9).
- An OPR is "Annual" unless the reporting period is shorter than a year (1.5.2.3).
