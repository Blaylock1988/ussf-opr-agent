# Interview, discovery and record review

SKILL.md points here for the parts of intake and review that need more detail than the workflow line.

## How to ask
Whenever you need data or a decision from the user, use the harness's structured prompt:
- **Claude Code:** `AskUserQuestion` (up to 4 questions per call, 2–4 options each; the user can always type "Other").
- **Antigravity:** its approval/question prompt.
- **Fallback:** a short numbered list in chat. Wait for the answers.

Batch related questions. Put the recommended option first. Never guess an answer the user owns.

## 1. Discovery phase (before the ledger)
1. **Ask first for anything already written this year:** unit, special, quarterly or annual award packages, decoration write-ups, feedback notes, and "brag sheets". These are the richest, already-vetted sources.
2. **Ask for the AMS SURF and the last 3–5 OPRs** (see §4).
3. **If content is still thin**, go line by line: for each Block IV/V line that has no source, ask a targeted question ("What was your biggest win in contracting this year? Numbers?") until every line has source material.
4. **Ask whether to export the reports as DOCX** (usually yes): the fact ledger, the research report and the record review go to `Output/` alongside the OPR. Store the answer in `draft.settings.export_reports` (default `true`).

## 2. Routine-compliance probe
When an item sounds routine ("met budget", "0 findings", "on time", "completed all reviews"), ask before drafting:
1. **Who consumed it?** Which SES, CCMD, FLDCOM or HQ decision-maker used this data or decision?
2. **What would have failed without it?** The delay, risk, or resource failure that was avoided.
3. **What did it save?** Annualized enterprise-wide time or dollars.

A routine item earns a line only if one of these answers gives it a measurable impact.

## 3. Forward-dated and long-horizon work
- Drafts are written months before closeout. Accomplishments with a **strong likelihood of finishing before closeout** are fair game; confirm the expected date with the user and flag them in the ledger (`forward_dated: true`).
- Nothing outside the rating period, ever. Check `career_review.md` → Close-out dates for the grade's accountability date and SCOD.
- **Acquisition programs run for years.** Don't claim completion. Show genuine contribution and measurable progress instead: milestones passed, risks retired, decisions enabled, schedule recovered, dollars protected.

## 4. Record review (last 3–5 OPRs + AMS SURF)
Run `career_review.py` after the ratee confirms their history. Record each duty title (SURF and OPRs) in `career_profile.json` → `duty_titles`.

**Duty titles** must show growth, progression and some consistency. An OPR must **never** show a regression (Flight CC → Branch Chief → Flight CC, or worse, Section Lead).
- The ratee has some say over the duty title (with supervisor/unit approval). Suggest one that shows growth before closeout.
- SURF titles cap at 30 characters, so they won't always match the OPR.
- Regressions often come from reorganizations. Flag them so the commander sees the unintended board impact.

Then write `_opr_work/record_review.md` with **two lists**:
1. **Strengthen this OPR.** Data the user can research about work already done (programs, people, systems, the unit), and tasks very likely to finish before closeout. Never suggest new work that can't be completed in time.
2. **Strengthen future boards.** Job and experience gaps measured against the USSF Assessment Worksheet – Career Review and current HHQ/SECAF guidance (`board_priorities.json`), tailored by `career_review.md` → Development and push guidance:
   - career-field paths (acquisition: ML at Lt Col, SML at Col; operations: Det CC at Maj, Deputy Sq CC at senior Maj, Sq CC at Lt Col);
   - competitively boarded schools and programs (strong at Capt/Maj);
   - education gates (IDE + Advanced Academic Degree for Lt Col; SDE for Col).

Education gates guide advice and DE pushes only. DE or degree **completion** stays out of the OPR unless unit policy allows it.

## 5. Grade equivalents (awards, nominations, strats)
When an award, nomination or stratification came from a senior civilian or another service, it can be appropriate to state the military grade equivalent, e.g. an SES-1 Portfolio Acquisition Executive with her own directorate is an O-7 equivalent. Confirm the equivalence with the user; never inflate it.
