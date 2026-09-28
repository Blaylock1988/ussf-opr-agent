# DAF Form 707 (20240213): Officer Performance Report (Lt thru Col)

The machine-readable profile is `data/forms/daf707-20240213.json`. A user can override it with `_opr_work/form.json`.

## Sections the tool writes
| Section | Limit | Content |
|---|---|---|
| I. Ratee Identification Data | fields (one row each in the DOCX) | Name, SSN (last 4 only, never in drafts), grade, DAFSC/DSFSC, reason, PAS, organization/command/location/component, period, days supervised/non-rated. The data must match myEval. |
| II. Job Description | Duty title (own row) + **4 lines** | Scope only, in the present tense. SRID goes in block 10. |
| III. Performance Factors | checkbox | Meets / Does Not Meet. The tool does not write this block. |
| IV. Rater Overall Assessment | **6 lines** | 5 performance lines, then the strat/push line last. Include "Last performance feedback was accomplished on: <date>" (own row). |
| V. Additional Rater Overall Assessment | **4 lines** | 3 performance lines, then the strongest strat/push line in the report. |
| VI. Reviewer | **3 lines** (if required) | If the rater is also the reviewer, the first line is `THE RATER IS ALSO THE REVIEWER`, with no period. |
| X. Remarks | block | Spells out the acronyms used on the front of the form (see `writing-rules.md`, Sec X). |

## Line geometry
- The font is Times New Roman 12 pt. Each line is **201.05 mm** wide, which is the bullet-buddy OPR width.
- The user's 2025 OPR lines measure 200.78–201.02 mm, which confirms that width.
- A line "fits" when its width falls in **[200.75, 201.05] mm**, so the last character nearly touches the right wall of the box.
- The last millimetre or so is closed with width-adjusting spaces: U+2004 (+0.354 mm), U+2006 (−0.354 mm) and U+2009 (−0.212 mm). The space after the leading `- ` is never adjusted.
- The official PDF is an encrypted, dynamic XFA form, so the tool never writes into it. Users paste each fitted line from the DOCX into the form, and the special spaces survive the paste.

## Form instructions (page 2), binding on every evaluator
- Recommendations must be based on performance and the potential shown by that performance. **Promotion recommendations are prohibited.**
- Do **not** comment on:
  - completion of or enrollment in Developmental Education or advanced education;
  - previous or anticipated DAF Form 709 promotion recommendations;
  - OPR endorsement levels;
  - family activities, marital status, race, sex, ethnic origin, age, religion or sexual orientation.
- **Rater:** say what the officer did, how well, and how it contributed to the mission. Write in concise bullet format. Recommendations for assignment are allowed.
- **Additional rater:** may include a recommendation for assignment. Mark NON-CONCUR only for a real disagreement.
- The OPR is **CUI when filled out**. Never enter classified information.

## Fitness scores (placement pending)
Boards weigh fitness heavily in 2026, but the 20240213 form has no fitness block. Until official placement is published, the DOCX prints `FITNESS SCORE: <score>` as a Box I identification line whenever `ratee.fitness_score` is set. `ratee.fitness_placement` (`box1` | `remarks` | `both` | `none`) overrides it per report; `optional_blocks.fitness` in the form profile sets the default.
