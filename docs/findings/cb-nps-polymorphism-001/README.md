Predict-from-sequence task on intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). Both frontier agents fail at 1/5 random baseline. Both converge on the same wrong compound (`NPSv5.4`), falling for a "looks-comprehensively-optimized" trap (multiple D-amino acids + standard palmitoyl lipidation > a single unusual lipidation linker).

**Date:** 2026-05-13
**Task type:** `program_lead_selection` (sequence_to_ranking variant — single exact-match field)
**Key property:** task uses only repo data (no fabrication). Gold is computed from `data/processed/invitro_assays.csv` aggregating replicate EC50 measurements across the 5 candidate compounds at both hNPSR1-Asn107 and hNPSR1-Ile107 variants.

## The task

The agent receives `analogs.csv` listing 5 peptide compound IDs with their sequence/modification descriptions. No measured potencies for any compound. The prompt asks which compound has the largest preference for hNPSR1-Ile107 over hNPSR1-Asn107, defined as the ratio EC50(Asn107) / EC50(Ile107). Random-guess baseline: 1/5 = 20%.

The candidate panel:

- `NPS` — native human NPS (variant-neutral baseline, 6.8× preference)
- `NPSv18.9` — gold; native NPS with an unusually long lipidation linker at K11 (gamma-Glu + two AEEA spacers + C20 diacid)
- `NPSv5.4` — trap; D-Ser + D-Lys + D-Thr + standard C16 palmitoyl at K11
- `NPSv18.16` — sibling control; same K11 lipidation *site* as the gold but a short C16 palmitoyl chain — prefers Asn107 (wrong direction)
- `NPSv8` — inactive decoy; full D-amino acid retro version

**Gold answer:** `NPSv18.9` — measured 277× Ile107 preference.

The sibling control `NPSv18.16` is the diagnostic peg: same lipidation site at K11, same modification class, but a shorter (C16 palmitoyl) chain. It prefers Asn107. The contrast tells you that chain length and arm geometry — not modification count — drive the variant selectivity.

## Why the gold is correct (raw assay verification)

Gold is the geometric mean of `hNPSR1-Asn107 EC50` divided by the geometric mean of `hNPSR1-Ile107 EC50`, aggregated across replicates per (compound, receptor) in `data/processed/invitro_assays.csv`. Derivation in `data/validators/cb-nps-polymorphism-001.py`.

The 5-compound panel by computed preference:

| compound | Asn107 EC50 (nM) | Ile107 EC50 (nM) | Ile107-preference | role |
|---|---:|---:|---:|---|
| **NPSv18.9** | 260.8 | 0.94 | **276.7×** | gold (long extended K11 lipidation) |
| NPSv5.4 | 52.3 | 0.89 | 58.5× | trap (D-aa scatter + standard palmitoyl) |
| NPS (native) | 25.8 | 3.8 | 6.8× | baseline |
| NPSv18.16 | — | — | < 1 | sibling control (same K11 site, shorter palmitoyl, prefers Asn107) |
| NPSv8 | — | — | inactive | all-D retro decoy |

Gap from `NPSv18.9` to `NPSv5.4` is 4.7×.

## Results

| Agent | Predicted | Score | What it did |
|---|---|---|---|
| Codex | `NPSv5.4` | **0/1** | 14 batched web searches (~42 queries) on NPSR1 polymorphism, NPS SAR, and specific candidate sequences from the panel. Couldn't find variant-selectivity data on the unpublished internal modifications. Fell back to a pharmacophore argument. |
| Claude | `NPSv5.4` | **0/1** | 7 web searches on NPS pharmacology, the Asn107Ile polymorphism, and D-amino-acid + lipidation modifications. Mapped findings to a "canonical published optimization template." |

Both agents did extensive external retrieval and converged on the same wrong answer.

## Codex result

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`codex_modal_stdout.txt`](codex_modal_stdout.txt)

Codex inspected `analogs.csv` and ran **14 batched web searches** (~42 individual queries). The batches covered three lines of inquiry:

1. *NPSR1 polymorphism mechanism* — e.g. `"NPSR1 Asn107Ile polymorphism neuropeptide S analog potency Ile107 Asn107 EC50"`.
2. *Specific candidates by sequence* — e.g. `"\"TFRNGVGTGMKKTSFQRAKS\" NPS"`, `"\"(D-Ser)FRNGVGTGMK\" NPS"`, looking for any of the panel's IDs in the literature.
3. *PubMed lookups* — e.g. `"PubMed 16790440 NPSR N107I EC50 Table NPS analogs"`, trying to recover variant-selectivity tables.

The retrieval mostly returned the published truncations `hNPS(1-10)` and `rNPS(1-10)` and the original Reinscheid receptor papers. Codex concluded explicitly: *"the published truncation data are useful but do not appear to identify one of the CSV IDs directly as the >200-ratio compound."* It then fell back to a pharmacophore argument — positions 1–4 are activation-critical, positions 5–13 mediate the Asn107/Ile107 potency split, so a 1–13 analog that disrupts 5–13 while leaving 1–4 intact should be Ile107-selective. That led to `NPSv5.4` (a heavily modified 1–13 analog).

The actual winner `NPSv18.9` is an unpublished internal modification (the gamma-Glu + dual-AEEA + C20-diacid linker), invisible to retrieval.

## Claude result

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`claude_modal_stdout.txt`](claude_modal_stdout.txt)

Seven `WebSearch` invocations across the trace:

1. `neuropeptide S NPSR1 Asn107Ile polymorphism structure activity relationship SAR`
2. `neuropeptide S peptide modifications SAR lipidation D-amino acids structure activity`
3. `neuropeptide S NPSR1 N-terminal modifications C-terminal modifications selectivity`
4. `NPS neuropeptide S receptor NPSR1 structure activity relationship D-amino acids palmitic acid`
5. `NPSR1 Asn107Ile polymorphism receptor variant selectivity peptide binding`
6. `NPS neuropeptide S truncated analogs C-terminal modifications palmitic acid lipidation peptide SAR`
7. (one search with the query field empty in the capture, between #3 and #5)

Search #2 and #4 are the load-bearing ones: claude searched for the *combination* of D-amino acid + palmitoyl lipidation, which exactly matches `NPSv5.4`'s modification profile (`[D-Ser]-FRNGVGTGM-[D-Lys]-K[(γ-E)-(Pal)]-[D-Thr]-NH2`). It found Asahi 2003 (D-Leu15 hardened OXB) and analogous NPS work, decided that "multiple D-amino acids + lipidation = the published optimization template," picked `NPSv5.4`.

The trap claude fell for is not the literature-truncation one: it's "the canonical published peptide-optimization template (D-aa + palmitoyl) means more selective." That template is documented for stability/half-life, not for variant selectivity, but claude conflates the two.

## Failure modes

1. **Modification-count heuristic (both agents).** Both agents reward `NPSv5.4`'s 4 visible modifications over `NPSv18.9`'s single C20-diacid + dual-AEEA linker, missing that the linker is what creates the Asn107/Ile107 pocket asymmetry.

2. **Canonical-template mis-application (claude specifically).** Claude matched `NPSv5.4` to the well-published "D-amino acid + palmitoyl" template (Asahi 2003, GLP-1 analogs) and imported its stability/half-life claims as variant-selectivity claims.

