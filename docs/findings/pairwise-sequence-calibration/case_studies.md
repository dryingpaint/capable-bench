# Case studies — pairwise potency failure modes

One illustrative case per failure mode identified in `README.md`, plus a positive-control case showing real SAR reasoning when it works.

Every example pulls the actual agent reasoning from `runs/<task_id>/<timestamp>/agent_trace.txt`. Quotes are verbatim.

---

## 1. AUP refusal — `mch-trivial-016` (claude)

**Setup.** Potency ratio **26,316×** (gold more potent).

| | Modification |
|---|---|
| PEP-4BE58CE8E0 | `Ac-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Cys-NH2` |
| PEP-F13501AAC3 (gold) | `Asp-Phe-Asp-Met-Leu-Arg-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Pro-Cys-Trp` |

**What claude did.** Did not engage with the task at all. The trace contains only:

> *"API Error: Claude Code is unable to respond to this request, which appears to violate our Usage Policy (https://www.anthropic.com/legal/aup). Try rephrasing the request or attempting a different approach."*

**Why this matters.** The task prompt explicitly begins with *"Safety and scope: this is a non-clinical benchmark over anonymized internal research data. Do not provide therapeutic advice, wet-lab protocols..."* — yet claude's safety classifier still triggers, presumably on the peptide-sequence content itself. This is one of 5 such refusals (all claude, all in MCH or NPS families). Codex never refuses.

**Implication.** The benchmark cannot currently distinguish "claude can't do peptide SAR" from "claude refuses peptide tasks." Until refusals are surfaced as a separate column, claude's failure rate is inflated by ~17%.

---

## 2. Length / complexity cue — `mch-hard-005` (codex)

**Setup.** Potency ratio **2.97×** (gold more potent). The two peptides are length 30 chars vs 56 chars.

| | Modification | Length |
|---|---|---|
| PEP-70DED4DFCB (gold) | `Ac-Cys-Gly-Arg-Val-Tyr-Cys-NH2` | 30 |
| PEP-72E481BD02 | `Ac-Arg-Cys-Met-Leu-Gly-D-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2` | 56 |

**What codex did.** Picked the longer one. Verbatim trace:

> *"The two candidates differ sharply: one is an annotated cyclic Ac-MCH(6-17)-NH2 scaffold with the longer MCH pharmacophore context and D-Arg substitution, while the other is a much shorter cyclic fragment missing much of that context. **I'm selecting the longer scaffold as the potency prediction.**"*

**Why this matters.** No residue-level analysis. The decision is explicitly phrased as length-based (*"the longer scaffold"*) with the only specific feature mentioned being "D-Arg substitution" — which codex doesn't reason about, just acknowledges. The 6-mer mimetic wins in reality (~3× more potent in held-out assays), but codex's prior says "more pharmacophore context = more potent."

**Implication.** At the 1.1–1.5× ratio range, codex's failures average 7/9 = 78% picking-the-longer-one. This is the dominant failure mode at the difficulty level the benchmark is supposed to discriminate.

---

## 3. Pharmacophore misapplied — `mch-hard-005` (claude)

**Setup.** Same task. Gold is the 6-residue cyclic peptide.

**What claude did.** Picked the longer peptide, but with *sophisticated* reasoning:

> *"Selected PEP-72E481BD02 as the more potent peptide. It contains the **full DRVY pharmacophore plus the Trp anchor and Pro hinge**, which the 6-residue Cys-Gly-Arg-Val-Tyr-Cys peptide lacks — the truncated hexapeptide retains only the RVY core and should bind MCHR1 substantially more weakly."*

**Why this matters.** This is *real medicinal chemistry knowledge*: the DRVY motif is the established MCH pharmacophore, the Trp at position 17 is a hydrophobic anchor residue in receptor binding, and Pro residues do act as conformational hinges. Claude correctly identified all three concepts. The conclusion is just wrong for this particular dataset — the truncated hexapeptide is the gold winner anyway.

**Implication.** This is the most concerning category because it's the failure mode that *cannot be fixed* by sanitizing the input. Claude is doing the right kind of reasoning and reaching the wrong answer. Two possible explanations:

1. **The gold is non-obvious by SAR.** The dataset may contain a peptide that breaks textbook expectations — maybe the minimal mimetic has unusual conformational rigidity that compensates for missing residues. If true, this is a *good* benchmark item that exposes the limits of textbook SAR.
2. **The gold is noisy.** At a 2.97× potency ratio in a single in-vitro assay, the call may not be robust. A re-derivation from raw replicates would tell us whether the "correct" answer survives noise.

We don't currently have the information to distinguish (1) from (2). Both would be useful follow-ups.

---

## 4. No substantive reasoning — `oxn-medium-006` (codex)

**Setup.** Potency ratio **14×** (gold more potent).

| | Modification |
|---|---|
| PEP-F9A8AC8ACB (gold) | `RQK GLQGR LYRLL QGSGN HAAGI LT(Nle)-NH2` |
| PEP-1644F77D58 | `RSGPPGLQGRLQ(D-Citrulline)LLQASGNHAAGILTM-NH2` |

**What codex did.** Picked the wrong one with this complete trace:

> *"I'll inspect the task directory contents and the peptide sequence file, then make the potency call from the structural differences only."*
>
> *"The two candidates are both amidated OXN/OX2R peptide analogs. I'm comparing them against the recognizable orexin-B-like motif and the likely impact of truncation/substitution versus a single noncanonical residue."*

That's it. No conclusion sentence, no claim about *which* substitution is worse, no mention of D-Citrulline specifically.

**Compare to claude on the same task** (correct):

> *"...PEP-1644F77D58 is orexin-B with a **D-Citrulline replacing a conserved mid-sequence arginine** — a combined D-stereochemistry + charge-loss modification at a key pharmacophore residue that typically causes a large EC50 increase at OX2R."*

Claude names the modification (D-Citrulline), identifies what it replaces (arginine → citrulline is canonical charge-removal), notes the position context (mid-sequence pharmacophore residue), and combines two independent effects (stereochemistry + charge). Codex never engages with any of those features.

**Why this matters.** Codex's traces are systematically shorter and less mechanistic than claude's. On tasks where the SAR is non-trivial (small potency ratios), codex's thinner reasoning gets caught. The grader doesn't see this — both agents output `selected_option` and nothing else — but it's visible in the trace.

**Implication.** If you grade only `selected_option`, codex and claude look equivalent on most tasks. If you grade the rationale, claude is doing substantively more chemistry. The benchmark is currently invisible to this distinction.

---

## 5. Positive control: correct SAR reasoning — `nps-hard-001` (both agents)

**Setup.** Potency ratio **4.24×** (gold more potent). Both agents got this right.

| | Modification |
|---|---|
| PEP-57AA9A237F (gold) | `(D-Ser)FRNGVGTGMK(N-Me-Lys)(N-Me-Thr)SFQRAKS-NH2` |
| PEP-DCA805671F | `SF(D-Arg)NGVGTGMKKTSFQRAKS` |

Native NPS sequence is `SFRNGVGTGMKKTSFQRAKS`. Gold has modifications at the *peripheral* positions (D-Ser1, mid-region N-methylation, C-terminal amide). Loser has a D-Arg substitution at position 3 — inside the conserved SFRNG activation motif.

**What claude did:**

> *"its modifications (D-Ser1, mid-region N-methylations, C-terminal amide) preserve the critical N-terminal pharmacophore, whereas PEP-DCA805671F's **D-Arg3 substitution disrupts an essential cationic residue in the SFRNG activation motif**."*

**What codex did:**

> *"I'm treating the **D-Arg substitution at position 3 as the larger likely potency penalty for NPSR activation**, compared with the other peptide's D-Ser/N-methyl/C-amide pattern."*

Both agents independently identified:
- The same critical residue (Arg3 of NPS)
- The same disruption (D-substitution at a conserved cationic position)
- The same mechanism (loss of NPSR activation)

**Why this matters.** This is what the benchmark *claims* to test, and when conditions align — clear conserved-motif SAR, modifications at chemically distinct positions — both agents succeed via real reasoning. The benchmark *can* discriminate engaged-SAR-reasoning from surface heuristics; the problem is most tasks aren't structured cleanly enough to force this mode.

**Implication.** Build more tasks like `nps-hard-001`: short potency ratios, modifications at well-known SAR positions. The current 1.1–1.5× success rate of ~4/15 between the two agents suggests roughly that many tasks are structured this way; the other 11 are confounded by length or complexity cues.

---

## Summary

| Category | Example | Severity | Fixable by prompt/data change? |
|---|---|---|---|
| AUP refusal | `mch-trivial-016` (claude) | Claude-only, ~17% of claude failures | No — model-side filter; surface as separate column |
| Length / complexity cue | `mch-hard-005` (codex) | Dominant codex failure mode at narrow ratios | Yes — add controlled probes |
| Pharmacophore misapplied | `mch-hard-005` (claude) | Most concerning; real SAR + wrong answer | Partial — needs gold-noise audit |
| No substantive reasoning | `oxn-medium-006` (codex) | Hidden by current grader | Yes — grade the rationale |
| **Positive control** | `nps-hard-001` (both) | What success looks like | n/a (this is the target shape) |
