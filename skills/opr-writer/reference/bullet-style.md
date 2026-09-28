# OPR bullet language

This model is drawn from 84 real OPR lines, all of which fit to the form edge. In that sample:
- 65 of the 84 use `;` and 60 use `--`.
- Each line carries about 2.7 numbers on average.

`writing-rules.md` holds the rules. This file covers how the language is built.

## A. Performance line (Blocks IV–VI)
```
- <Verb-past> <what + scope>; <how/result + metric>--<impact + metric at the highest credible level>
```
- **Voice and tense.** Active voice and past tense only. `- Plan was approved by HAF` becomes `- Steered plan to HAF approval`.
- **Action.** A past-tense verb, then its object with scope: "Rebuilt sq $48M O&M spend plan". No subject, pronoun or article, and no closing period.
- **Result** comes after `; `. It says how it was done or what came out of it, with numbers: "realigned 31 funding lines in 2 wks".
- **Impact** comes after `--`, with no spaces. It says why anyone should care, for the mission, the warfighter or HHQ: "closed 18% shortfall f/4 GPS grnd sys".
- **Variant:** `Action; Impact--Result` is fine. Vary the rhythm across a block.
- **Impact ladder** (reach as high as the facts honestly allow):

  | Rung | Level |
  |---|---|
  | 1 | Unit |
  | 2 | Delta |
  | 3 | FLDCOM / HQ |
  | 4 | CCMD / Joint Staff |
  | 5 | POTUS / national |

  The number of people affected also counts, e.g. 640 warfighters or 12K users.
- **Packing more in:**
  - Chain results with `/`: "eval'd/negotiated in 3 mths", "fielded 2 mths early/saved $1.4M".
  - Use hyphenated compounds: "32-mbr", "5-wk", "first-ever".
- **Hooks for line 1:** first-ever, largest to date, senior-leader visibility, hand-picked, an award overflow ("Del FGOQ, SD 7 FGOY! Forged ..."), or a short exclamatory opener ("Master Arbitrator!").
- **Numbers:**
  - Write them like `$1.5B`, `$122M`, `9.5K`, `517`, `<1 wk`, `99.9%`.
  - The default is exact figures. Compress only to fit a line ($213,480,000 becomes $213M). Precise counts (517) beat round ones (500+, 1,000), which read as made up. `N+` and "over N" are a last resort for breaking a duplicate, after rewording and after a different precise figure.
  - Never mix units within a line.
- **One accomplishment per line.** T&Q warns that combining actions dilutes each one.

## B. Job Description (4 lines; present tense, scope only)
The format is more flexible than the performance lines. The usual order is:
1. Role, plus team size and makeup ("Leads 19-mbr ops, intel & training tm ...").
2. Portfolio dollars, and the programs or systems covered.
3. Supervision, contracts and additional duties.
4. External liaison and partners.

**Do not cannibalize.** The allocation step gives every ledger metric one home. If a bullet headlines "$410M", the Job Description either leaves that figure out or states it differently (for example "7 SATCOM prgms"). Lint warns when a number appears in both the Job Description and a bullet.

## C. Strat/push line (the last line of Blocks IV and V)
```
- #N/M <grade group>[, #N/M <duty group>]; <award(s) and/or character praise>--<next-rank job push>, <DE push>[!]
```
- The grade strat always comes first, **even when it is #1/1**. Then an optional duty strat, e.g. "#1/11 Flt/CCs".
- **Praise** can use the ratee's first name ("Alex is a brilliant ldr"), plus awards and nominations at their level.
- **Push:** name the job one rank up, e.g. "sq CC next" or "Del staff ldrship next". Never write "promote" or "in-res".
- **DE push** (IDE or SDE) is allowed. Completion of DE is not.
- **Block V** must beat Block IV: a bigger pool, the higher push, the best award.
- **Placeholders are the default:**
  - Write `#[N]/[M] O-4s` for the primary strat and `#[N]/[M] <duty group>` for the secondary.
  - Use real numbers only when the user gives them, and **never include a bottom-half strat**.
  - Offer 2–3 push options per evaluator in `draft.push_options`. Each option should include a command push and a DE push that stay consistent with prior OPRs (`career_review.md`).
- **Compliant example:**
  `- #1/6 Del O-4s, #1/11 Flt/CCs; hand-picked exercise planning lead f/USEUCOM--sq CC next, SDE soonest`
  USEUCOM goes in Sec X.
- **Historical example (not compliant with CFC 2026):**
  `- #1/6 Del O-4s, #1/7 PMs; hand picked f/Spc Exercise Tm lead ...`
  - "Spc" is not an approved abbreviation, and "Tm" should be `tm`.
  - "hand-picked" needs its hyphen.
  - PM needs a Sec X entry.

## D. Compression ladder (after `opr.py check` or `opr.py measure` says a line is too long)
Stop as soon as the line fits.
1. Drop articles, helping verbs, forms of *be/have/do*, pronouns, the ratee's name, and extra prepositions (T&Q ch 19 brevity list).
2. Use `f/`, `w/`, `w/in`, `w/o`, `thru`, `b/w`, `vs`, `ISO`, `&` (no space after `f/` or `w/`).
3. Use approved CFC Att 2 abbreviations, **exactly as listed**.
4. Use `-'d` verb forms with an approved verb base (coord'd, dir'd, eval'd, mng'd, sync'd, est'd, dvlp'd …).
5. Chain with `/`.
6. Compress numbers (2,500 → 2.5K).
7. Swap in a shorter verb from the same lexicon bucket (Consolidated → Merged). **Never "Led".**
8. Drop the weakest clause.

**Too short?** Spell abbreviations back out first, because readability comes first. Then add a metric or sharpen the impact.

**Report-wide rule.** Steps 2–4 add entries to `draft.abbrev_set`, for example `{"for": "f/"}`. `opr.py fit <draft.json> --write --apply-abbrev-set` then applies them to **every** line in every block. Pick the smallest set that lets the longest lines fit, then refit everything. Lines that end up short get reworded or given more content. Never switch them back to the long form.

## E. Verb choice (`data/action_verbs.json`)
- Choose the opener from the `preferred` tier, within the topic bucket that matches the accomplishment. Buckets include "Saved Time or Money", "Prevented something from happening", "Led a Team" and so on.
- **Distinctive but professional.** The metric and impact are the star, not the verb.
- `overused` verbs (Led, Spearheaded, Orchestrated, Managed, Directed, Drove, Oversaw, Executed …) may appear once, with a warning. `banned` verbs never appear.
- No opening verb repeats across Blocks IV–VI, and an abbreviated form counts as the same verb.
- Use only a verb's `approved_forms`. `unapproved_forms` such as elim'd, supv'd and brf'd have no approved base.

## F. Style profile (`_opr_work/style_profile.json`)
Match the voice of the user's prior OPRs: their separators, exclamation habits, first-name use, and which approved alternates they prefer (ldrship vs ldrshp, trng vs tng).
- **Readable first still wins.** Lint warns when more than 50% of a line's tokens are acronyms or abbreviations, and names the terms to spell out.
- **Never carry over unapproved shorthand from history:**

  | History form | Use instead |
  |---|---|
  | jt | Jt |
  | gov't | govt |
  | lgst | lrgst |
  | ntwk | ntwrk |
  | mos | mths |
  | spc, upd | spell out |
  | elim'd | eliminated |
  | Dev'd | dvlp'd |

## G. Worked transform
**Source (an award narrative):**
"led the squadron's annual requirements review, submitting 142 requirements and resolving over 900 higher headquarters comments ... secured $1.2 billion across the FYDP"

**Draft:**
`- Steered sq FY28 WSS POM; built 142 rqmts/resolved 900 HHQ comments--secured $1.2B FYDP f/6 SATCOM prgms`

- FY, WSS, POM, HHQ and SATCOM are in Att 1, so they are not defined.
- **FYDP is not in Att 1**, so it goes in Sec X.
- sq, rqmt(s), prgm(s), f/ and B are in Att 2.

**Then:** run `opr.py measure "<line>"`, apply the ladder until the status is `fits`, and let space adjustment close the final millimetre.

## I. Plain speak for out-of-field experience (the example audience is LSF-F)
These examples show how to rewrite an operations or staff tour for an acquisition board:

| Ops-field version | Written for an LSF-F board |
|---|---|
| `- Built 35 STOs & SPINS f/SFI JSOD; set ALRs/MOEs--enabled CFSCC battle rhythm` | `- Wrote theater space directive & 35 tasking orders; set risk/effect measures--armed 4-star cmdr f/Jt ex` |
| `- Led OPT thru JPP; dvlp'd 3 COAs f/JTF--CCDR approved` | `- Steered 9-mbr planning tm; built 3 options f/Jt task force--combatant cmdr approved plan` |

- Keep the numbers and the level of the impact. Drop the process vocabulary.
- If an out-of-field acronym must stay because of space, it goes in Sec X, and the line gets extra plain words around it.

## H. Board-reader check (run before export)
For every line:
- Does it answer "so what?"
- Is the impact credible for the action?
- Would a non-specialist understand it?
- Is the first line the strongest, and is the Block V strat line the best in the report?
- Is anything recycled from a prior OPR?
