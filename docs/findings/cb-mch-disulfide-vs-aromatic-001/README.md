# MCH: agents trust Bednarek's analog; native hMCH wins 30×

A pairwise potency prediction where one option is the native hMCH 19-mer and the other is Bednarek 2001 compound 19 (a published truncated/cyclic MCH(6-17) analog with N-acetyl cap, D-Cys, and C-terminal Trp-NH2). Both Claude and Codex pick the Bednarek-optimized analog, applying textbook lead-optimization SAR: caps + D-amino-acid + aromatic extension + N-terminal truncation = more potent. The published assay data say the opposite — the native 19-mer is ~30× more potent at MCHR1.

**Date:** 2026-05-13
**Task type:** `next_experiment` (pairwise option selection; reused for binary potency comparison)
**Task ID:** `cb-mch-disulfide-vs-aromatic-001`
**Key property:** sequence-only task. The agent sees the modification string for both peptides and nothing else (no measured EC50, no efficacy, no record counts).

## The task

`peptide_sequences.csv` contains two MCH-family peptides:

| peptide_id | modification | receptors |
|---|---|---|
| PEP-77A315C29A | `DFDMLRCMLGRVYRPCAQV` (hMCH 19-mer with Cys7–Cys16 disulfide) | MCHR1;MCHR2 |
| PEP-021CF7B0A5 | `Ac-Arg-D-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2` (Bednarek 2001 compound 19 scaffold: Ac-MCH(6-17)-NH2 cyclic via Cys7–Cys16 disulfide) | MCHR1;MCHR2 |

Prompt: predict which peptide has lower EC50 in functional in vitro assays at MCHR1, using only the sequence and chemical modifications. Write `answer.json` with `selected_option` set to the more potent peptide's `peptide_id`. Random-guess baseline: **1/2 = 50%**.

## Gold answer

**`PEP-77A315C29A`** (the native 19-mer).

| compound | best EC50 (nM) at MCHR1 binding | source |
|---|---|---|
| **PEP-77A315C29A** (hMCH 19-mer) | **0.15** | Bednarek 2001 Table 1 (alanine scan, full hMCH) |
| PEP-021CF7B0A5 (compound 19) | 4.6 | Bednarek 2001 Table 5 (D-amino-acid scan on compound 19) |

Measured potency ratio: **30.67×** in favor of the native 19-mer.

The C-terminal `-Cys-Trp-NH2` shape that closes the Bednarek truncation is structurally distinct from the native `-Cys-Ala-Gln-Val` tail; the truncated analog loses the Gln18 H-bond and the receptor contacts made by the full C-terminal segment, and that loss is not recovered by the terminal caps or the D-Cys ring-geometry tweak.

## What both agents said

Both Claude and Codex picked `PEP-021CF7B0A5` (the Bednarek compound 19 analog).

### Claude rationale

> **PEP-021CF7B0A5** is predicted to be more potent. The Bednarek 2001 compound 19 scaffold improves on native hMCH via: (1) C-terminal Trp adding aromatic receptor contacts, (2) Ac/NH2 terminal caps reducing charge–desolvation cost, (3) D-Cys optimizing the disulfide ring geometry, and (4) removal of the non-pharmacophoric N-terminal `DFDML` tail — together consistent with a ~30-fold potency gain over the native 19-mer.

### Codex rationale

> I'm selecting the compact cyclic analog because it preserves the MCH core pharmacophore around `Arg/Val/Tyr/Arg/Pro/Cys/Trp` and includes terminal blocking, while the 19-mer candidate replaces the normally important aromatic Trp-side region with Ala in the shown sequence.

Both agents independently produce the *same* four-part rationale: terminal caps (PK/charge), D-amino acid (geometry / protease resistance), C-terminal Trp substitution (aromatic contacts), N-terminal truncation (non-pharmacophoric tail). Each piece is textbook-correct as a *generic* SAR principle. The conclusion is wrong because the comparator (the native hMCH 19-mer) is not a "naked starting material" — it is a high-affinity full-length agonist that uses the C-terminal `-Ala-Gln-Val` tail productively, and the truncation to `-Cys-Trp-NH2` is a *net loss* even with the optimization features layered on top.

Claude's rationale also contains a striking confabulation: it explicitly predicts that the optimization features are "consistent with a ~30-fold potency gain over the native 19-mer," which is the exact magnitude of the *opposite-signed* measured gap (30× the other direction). The number that should have been a sanity check was absorbed into the wrong-direction story.

## Failure mode: "published-optimization signal" overrides direct sequence reading

Same family as the [NPS-polymorphism finding](../cb-nps-polymorphism-001/) (canonical-template mis-application, modification-count heuristic), but the signal is different. Here the trap features are the surface marks of a medicinal-chemistry optimization campaign:

- N-terminal acetyl + C-terminal amide (terminal blocking)
- A D-amino acid (D-Cys)
- An aromatic substitution at the C-terminus (Trp)
- N-terminal truncation removing the disordered tail

Each feature is correctly recognized by both agents as a *typical* potency-/PK-improving move. The agents then read those features as evidence that the truncated analog must be better than the parent peptide it was derived from, because that is what "compound 19" in a published SAR paper usually means.

What the agents do *not* do is hold open the alternative reading that the longer parent peptide already has all the productive receptor contacts and that the truncation gives some of them up. The MCH 19-mer is itself an evolved high-affinity ligand; the Bednarek compound 19 is a *minimization* exercise that intentionally trades some potency for shorter, more synthetically tractable, more developable material.

The shape — picking the published, recognizable optimization story over the unfamiliar truth — reinforces the **published-or-optimized features dominate when no direct measurement is shown** failure mode.

## Diagnostic value

- Confirms the trap pattern is *not* receptor-specific (MCH here, NPS in the cb-nps finding) and is *not* gated on receptor-variant subtlety — it triggers on any pairwise comparison where one option carries surface marks of "medicinal-chemistry optimization."
- The 30× number appearing in Claude's rationale with the *wrong sign* is a clean instance of confident-and-uncalibrated direction reasoning: the magnitude is plausible, the direction is inverted, and the agent's own rationale provides no internal disconfirmation step.
- Task is reproducible from this directory: `task.yaml`, `prompt.md`, `peptide_sequences.csv`, and `gold_answer.yaml` are the inputs and gold; `traces/claude_*` and `traces/codex_*` are each agent's raw output and final `answer.json`.
