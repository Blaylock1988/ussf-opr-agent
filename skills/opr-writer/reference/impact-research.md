# Impact research: finding joint and warfighter impacts with metrics

Boards reward impacts that reach **beyond the unit**: the joint force, the warfighter in the field, the CSO's priorities, and doctrine. The most common weak spot in a draft is impact that is *asserted* ("enhanced readiness") instead of *measured* ("enabled 35 STOs f/700 Guardians"). This step researches public context so each impact clause can carry a real, sourced number.

## When to run it
- **Before allocation (step 3b):** for each ledger item whose impact is vague, unit-level only, or has no metric.
- **After the first full draft (mandatory, step 5b):** always research the programs, units and systems named in the draft, even when the user's inputs looked complete. Write the research report (`_opr_work/research.md`, format below) with **links and citations** for every finding, then recommend updated bullets wherever research found a stronger metric or impact. Show the recommendations as proposed alternates; they go through the whole-OPR guard like any other alternate.

## Space threat context
`data/space_threats.json` holds the S2 Space Threat Fact Sheet metrics (v8, published 16 May 2025): PRC/Russian counterspace, DA-ASAT and co-orbital weapons, ISR constellations, jamming, lasers, launch rates.
- **Every run:** search for a newer edition (the canonical page is spaceforce.mil Article 4297159, which had no file as of Sep 2026) and ask the user if they have one. Cite the edition and date you used.
- Index relevant metrics into the ledger as **external impact sources** (`impact_candidates`), e.g. a SATCOM line can cite the PLA's jamming of protected EHF; an SDA line can cite 510+ PLA ISR satellites.
- The threat is context for *why the work mattered*. Never imply the ratee changed the threat numbers.
- Threat vocabulary ("pacing challenge", "counterspace", "lethality") is buzzword territory: each term at most once per OPR (`data/buzzwords.json`; lint warns on repeats).

## What to look for (strongest first)
1. **Joint and exercise impact.**
   - Scale: participants, nations, CCMDs, component commands, aircraft and ships, duration.
   - Whether the exercise is **tier-1**, meaning a CJCS/CCDR-level, JCS-designated large-scale exercise.
   - What the ratee's product *enabled*: the STOs, taskings or plans that executed; the commanders who used it.
2. **Warfighter and operational impact.**
   - Users, terminals, or units served by the system or program. Publicly stated user counts are ideal.
   - Operations or missions supported, and the CCMDs served.
   - Availability, timeliness, or risk reduction that operators felt.
3. **Senior-leader recognition.**
   - A **very short** quote (about 3–8 words) from a GO/SES or commander, e.g. `--CFSCC: "best JSOD I've seen"`.
   - The quote must come from the user's own evidence (an email, LOA, award write-up) or a public article. **Never fabricate or paraphrase into quote marks.**
   - A quote is not a stratification. Stratifications may come only from signatories (SpOC 1.6.2).
4. **CSO priorities.** Tie the work to a published CSO initiative, e.g. "...--advanced CSO Space Control imperative (C-Note #34)".
   - Search `data/cso_digest.json` with `scripts/ref_lookup.py "<theme>" --source cso [--type cnote|speech|article]`. It covers all 42 of Saltzman's C-Notes, his speeches and published articles: date, title, URL, key themes and short verbatim quotes with page numbers. Cite the number and date.
   - A digest quote may be echoed in an impact only when it fits; never alter it inside quote marks.
   - Check that the reporting period and the C-Note date line up.
   - Cite the idea, not just the number. Boards know the themes.
5. **Doctrine.** Adherence to, or better, **contribution to** USSF and joint doctrine.
   - **SFDD-1**, *The Space Force* (capstone, 3 Apr 2025). It supersedes the 2020 *Spacepower* Space Capstone Publication.
   - **SDP series** (Space Doctrine Publications), e.g. SDP 1-0 *Personnel*.
   - **JP 3-14**, *Joint Space Operations*.
   - **AFDP 3-14**, *Space Support* (1 Apr 2025).
   - Examples: "codified theater space ops IAW JP 3-14" or "authored input adopted in SDP x-x".

## How to research
- Use the environment's web tools: `WebSearch` / `WebFetch` in Claude Code, or the search and browser tools in Antigravity. For broad, multi-source questions, use a deep-research skill or subagent if one is available.
- **Several sites block automated fetches:**
  - spaceforce.mil
  - afpc.af.mil
  - e-publishing.af.mil (often)
  
  When a fetch fails, give the user the exact URL. Ask them to save the page or PDF into `<folder>/Guidance/research/`, then rerun `extract_inputs.py`.
- Good public sources:
  - spaceforce.mil news and the CSO Leadership Library.
  - Field command, Delta and STARCOM news pages.
  - DVIDS.
  - defense.gov releases.
  - Combatant command press pages, e.g. usfk.mil or indopacom.mil exercise releases.
  - Air & Space Forces Magazine, Breaking Defense, SpaceNews, DefenseScoop.
  - GAO reports and program fact sheets.

## OPSEC / CUI guardrails (non-negotiable)
- **Search only public, generic terms:** an exercise name and year, a program name, "user count", "fact sheet".
  - **Never** put the ratee's name, unit rosters, non-public numbers, vulnerabilities, operational details, or anything classified or CUI into a query or a URL.
- Use only **published, unclassified** facts. When a public figure differs from the user's internal number, use the user's number (it is what the OPR can defend) and note the public figure only as context.
- Record every finding with its **source URL and date** in `_opr_work/research.md`, and add it to the ledger item as an `impact_candidates` entry. **The user confirms each one before it is used.**
- Never claim someone else's effect. The impact must plausibly follow from the ratee's action (T&Q ch 19: the impact scope must match the action).

## Executive lexicon (find the impact, don't inflate the words)
Board members read at the enterprise level. Use this map to find the *impact* a tactical task had; the metric must still carry the line. These phrases are buzzwords too: each at most once per OPR.

| Tactical wording | Board-level framing |
|---|---|
| SharePoint, Power BI, dashboards | data fabric, digital architecture, decision advantage |
| reviews, reconciliations, audits | automated governance, statutory compliance, fiscal integrity |
| reduced prep time | accelerated decision cycles |

## Output format (`_opr_work/research.md`)
Every finding carries a clickable link (`[title](url)`) and date, so the DOCX export keeps its citations. End the report with a **Recommended bullet updates** section: line, current text, proposed text, and the finding that supports it.
```
## L4 - Exercise planning (ledger)
- Candidate: "exercise spanned 2 CCMDs, 14K US/allied prsnl" - source: <url> (date) - confidence: high/med/low
- Candidate quote: Del/CC: "best exercise plan I've seen" - source: user email (provided) - confirmed: ?
- CSO tie-in: C-Note #34 Space Control (7 Mar 25) - fits reporting period: yes
- Doctrine: JP 3-14 theater space integration - how: JSOD aligned space effects to campaign plan
```
