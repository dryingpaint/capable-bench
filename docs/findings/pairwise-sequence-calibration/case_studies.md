# Case studies — pairwise potency failure modes

One illustrative case per failure mode identified in `README.md`. Every quote is verbatim from `runs/<task_id>/<timestamp>/agent_trace.txt`; click the *Full agent trace* toggle to expand each one inline.

The full per-task category labels for all 53 graded failures are in `failure_classifications.csv`.

---

## 1. AUP refusal — [`mch-trivial-016`](traces/mch-trivial-016-claude.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-mch-trivial-016/) (claude)

**Setup.** A 9-residue cyclic mimetic vs. a 17-residue native MCH-like peptide.

| | Modification |
|---|---|
| PEP-4BE58CE8E0 | `Ac-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Cys-NH2` |
| PEP-F13501AAC3 (gold) | `Asp-Phe-Asp-Met-Leu-Arg-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Pro-Cys-Trp` |

**What claude did.** Did not engage. The trace contains only:

> *"API Error: Claude Code is unable to respond to this request, which appears to violate our Usage Policy (https://www.anthropic.com/legal/aup). Try rephrasing the request or attempting a different approach."*

[Full agent trace](traces/mch-trivial-016-claude.jsonl)

**Why this matters.** The task prompt explicitly begins with *"Safety and scope: this is a non-clinical benchmark over anonymized internal research data. Do not provide therapeutic advice, wet-lab protocols..."* — yet claude's safety classifier still triggers, presumably on the peptide-sequence content itself. 5 of claude's 22 reasoning failures (23%) are AUP refusals; codex has 0.

**Implication.** Until refusals are surfaced as a separate column, claude's failure rate is inflated by ~23%. The benchmark cannot currently distinguish "claude can't do peptide SAR" from "claude refuses peptide tasks."

**More examples (claude AUP refusals).** `mch-easy-013`, `mch-medium-010`, [`mch-trivial-016`](traces/mch-trivial-016-claude.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-mch-trivial-016/), `mch-trivial-017`, `nps-trivial-020`. All MCH or NPS family.

---

## 2. Length / complexity cue — [`oxn-hard-001`](traces/oxn-hard-001-codex.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-oxn-hard-001/) (codex)

**Setup.** Two OX2R-family peptides; gold is the shorter analog with non-natural residue substitutions. Potency ratio **4.46×** (gold more potent).

| | Modification | Length |
|---|---|---|
| PEP-3238F2B9CF (gold) | `GLQGX LQ(hArg)XL QASGN HAAGI LT(Nle)-NH2` | 14 residues |
| PEP-8806C23CA2 | `RSGPPGLQGRLQRLLQA(Thr)GNHAAGILTM-NH2` | 28 residues |

**What codex did.** Picked the longer one. Verbatim trace:

> *"The stronger sequence signal is the full-length, native-like OX2R peptide versus the shorter analog with multiple nonstandard substitutions. I'm going to select the full-length native-like entry as the predicted lower-EC50 peptide."*

[Full agent trace](traces/oxn-hard-001-codex.jsonl)

**Why this matters.** The decision is explicitly length-based ("full-length, native-like" → potency call). Codex doesn't engage with the specific non-natural residues (hArg, Nle, X) at all — it treats their presence as a generic "modified analog" signal rather than reasoning about what those substitutions do at OX2R. The shorter peptide wins ~4× because the substitutions are at receptor-engagement positions; codex can't access that reasoning from a "full-length wins" prior.

**Implication.** Codex's failures at narrow potency ratios (1.1–1.5×) average 7/9 = 78% picking-the-longer-one. This is the dominant codex failure mode at the difficulty level the benchmark is supposed to discriminate.

**More examples (codex length cue).** `mch-easy-012`, `nps-easy-013`, `nps-easy-014`, `nps-medium-010`, `nps-trivial-019`, `oxn-easy-015`, `oxn-hard-005`, `oxn-trivial-019` — 10 total in the dataset.

---

## 3. Pharmacophore misapplied — [`nps-easy-012`](traces/nps-easy-012-claude.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-nps-easy-012/) (claude)

**Setup.** Two NPS analogs; gold is the simpler peptide with a single D-Thr substitution. Potency ratio **79×** (gold more potent — robust gold).

| | Modification | Visible "optimizations" |
|---|---|---|
| PEP-EBF5A06DFA (gold) | `SFRNGVGTGMKK(D-Thr)SFQRAKS` | 1 — D-Thr at position 13 |
| PEP-93846D9997 | `(D-Ser)F(4-F-Phe)NGVGTGMKK(N-Me-Thr)SFQRAKS-NH2` | 4 — D-Ser1, 4-F-Phe at position 3, N-Me-Thr13, C-terminal amide |

**What claude did.** Picked the heavily-modified peptide with *named-series-level* reasoning:

> *"R3 → 4-F-Phe (hydrophobic/aromatic at position 3 — a well-known SAR-driven potency enhancement at NPSR; consistent with the [t-Bu-Ala3]NPS / [Cha3]NPS analog series)."*
>
> *"PEP-93846D9997 combines multiple potency- and stability-enhancing modifications, including the canonical position-3 hydrophobic substitution that drives large EC50 reductions in NPS SAR series."*

[Full agent trace](traces/nps-easy-012-claude.jsonl)

**Why this matters.** This is *real medicinal-chemistry knowledge*: [t-Bu-Ala3]NPS and [Cha3]NPS are published NPSR analog series, position-3 aromatic/hydrophobic substitutions are a documented potency-enhancing move in some NPS SAR contexts, and D-Ser1 / N-Me-Thr / C-terminal amide are all canonical peptide-stability features. The conclusion is wrong here because Claude failed to do residue-level accounting in this exact sequence.

The heavily modified peptide does not simply add a 4-F-Phe feature; it replaces native **Arg3** in the NPS `SFRN` activation motif with 4-F-Phe. That removes a conserved cationic contact in the N-terminal recognition region. The gold peptide preserves the N-terminal `SFRN` pharmacophore and changes only Thr13 to D-Thr, a less central position for NPSR activation.

So the failure is not "published SAR is useless." It is that Claude treated optimization-like features as additive and portable without checking whether the modification deletes a load-bearing residue at the exact position. The visible modification count is misleading: four plausible-looking medchem changes are worse than one small change when one of the four breaks the core activation motif.

The 79× ratio rules out gold-noise, so the failure is real — not an artifact of close-discrimination.

**More examples (claude pharmacophore misapplied).** `mch-easy-014`, `mch-hard-002`, `mch-medium-007`, `nps-easy-014`, `nps-hard-002`, `nps-hard-004`, `nps-medium-010`, `nps-trivial-017`, `oxn-easy-014`, `oxn-hard-003`, `oxn-medium-009` — 12 total in the dataset.

---

## 4. No substantive reasoning — [`oxn-medium-006`](traces/oxn-medium-006-codex.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-oxn-medium-006/) (codex)

**Setup.** Potency ratio **14×** (gold more potent). Loser carries a D-Citrulline substitution at a conserved Arg.

| | Modification |
|---|---|
| PEP-F9A8AC8ACB (gold) | `RQK GLQGR LYRLL QGSGN HAAGI LT(Nle)-NH2` |
| PEP-1644F77D58 | `RSGPPGLQGRLQ(D-Citrulline)LLQASGNHAAGILTM-NH2` |

**What codex did.** Picked the wrong one. Full reasoning trace:

> *"I'll inspect the task directory contents and the peptide sequence file, then make the potency call from the structural differences only."*
>
> *"The two candidates are both amidated OXN/OX2R peptide analogs. I'm comparing them against the recognizable orexin-B-like motif and the likely impact of truncation/substitution versus a single noncanonical residue."*

That's it. No conclusion sentence, no claim about which substitution is worse, no mention of D-Citrulline.

[Full codex trace](traces/oxn-medium-006-codex.jsonl)

**Compare to claude on the same task** (correct):

> *"...PEP-1644F77D58 is orexin-B with a **D-Citrulline replacing a conserved mid-sequence arginine** — a combined D-stereochemistry + charge-loss modification at a key pharmacophore residue that typically causes a large EC50 increase at OX2R."*

[Full claude trace](traces/oxn-medium-006-claude.jsonl)

Claude names the modification (D-Citrulline), identifies what it replaces (arginine → citrulline is canonical charge-removal), notes the position context (mid-sequence pharmacophore residue), and combines two independent effects (stereochemistry + charge).

**Why this matters.** Codex's traces are systematically shorter and less mechanistic than claude's. The current grader sees only `selected_option` — so codex's thinner reasoning is invisible at the metric level even when it produces the same answer claude got via real chemistry. If you graded the rationale, you'd see the gap; if you only grade the pick, the agents look equivalent.

**More examples (codex no-substantive-reasoning).** This is a rare classification (1 codex case across 60 tasks). The broader pattern — short codex traces, single-clause picks — shows up as `length_or_complexity_cue` whenever codex's terse rationale leans on a surface feature.

---

## Summary

| Category | Example | n (claude / codex) | Concern level | Fix path |
|---|---|---|---|---|
| AUP refusal | [`mch-trivial-016`](traces/mch-trivial-016-claude.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-mch-trivial-016/) | 5 / 0 | Inflates claude failure rate by ~23% | Surface as a separate column; not addressable in-task |
| Length / complexity cue | [`oxn-hard-001`](traces/oxn-hard-001-codex.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-oxn-hard-001/) (codex) | 4 / 10 | Dominant codex failure at narrow ratios | Controlled probes that invert length-vs-potency |
| Pharmacophore misapplied | [`nps-easy-012`](traces/nps-easy-012-claude.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-nps-easy-012/) (claude) | 12 / 6 | Real SAR + wrong answer; hardest to address | Likely requires changes to agent reasoning, not benchmark design |
| No substantive reasoning | [`oxn-medium-006`](traces/oxn-medium-006-codex.jsonl) · [task page](/tasks/pilot-peptide-pairwise-sequence-oxn-medium-006/) (codex) | 1 / 0 | Hidden by current grader | Grade the rationale, not just the pick |
