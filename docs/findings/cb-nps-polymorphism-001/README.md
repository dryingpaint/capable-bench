# cb-nps-polymorphism-001

**One-liner:** Predict-from-sequence task on intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). Both frontier agents fail at 1/14 random baseline. Both converge on the same wrong compound (`NPSv5.4`), falling for a "looks-comprehensively-optimized" trap (multiple D-amino acids + standard palmitoyl lipidation > a single unusual lipidation linker).

**Date:** 2026-05-13
**Task type:** `program_lead_selection` (sequence_to_ranking variant — single exact-match field)
**Key property:** task uses only repo data (no fabrication). Gold is computed from `data/processed/invitro_assays.csv` aggregating ~25 replicate EC50 measurements across the 14 candidate compounds at both hNPSR1-Asn107 and hNPSR1-Ile107 variants.

## The task

The agent receives `analogs.csv` listing 14 peptide compound IDs with their sequence/modification descriptions. No measured potencies for any compound. The prompt asks which compound has the largest preference for hNPSR1-Ile107 over hNPSR1-Asn107, defined as the ratio EC50(Asn107) / EC50(Ile107). Random-guess baseline: 1/14 = 7.14%.

The candidate panel contains:

- 7 internal NPS modifications (NPSv5.4, NPSv10.16, NPSv16.13, NPSv21.9, NPSv31.7, NPSv2-proKKv1, NPSv18.9)
- 2 literature truncations (hNPS(1-10), rNPS(1-10))
- 1 native human NPS (variant-neutral baseline)
- 2 wrong-direction decoys (NPSv18.16, NPSv18.26 — these prefer Asn107)
- 1 inactive decoy (NPSv8 — full D-amino acid retro version)
- 1 mid-table filler (NPSv34.14)

**Gold answer:** `NPSv18.9` — native human NPS sequence with an unusually heavy lipidation linker at K11 (gamma-Glu + two AEEA spacers + C20 diacid; ~30-atom total chain). Measured 277× Ile107 preference.

The two published N-terminal truncations `hNPS(1-10)` and `rNPS(1-10)` rank #2 and #3 in the panel at 111× and 105× preference — the answers an agent would give if it retrieved "NPS truncation literature → prefers Ile107."

## Why the gold is correct (raw assay verification)

Gold is the geometric mean of `hNPSR1-Asn107 EC50` divided by the geometric mean of `hNPSR1-Ile107 EC50`, aggregated across replicates per (compound, receptor) in `data/processed/invitro_assays.csv`. Derivation in `data/validators/cb-nps-polymorphism-001.py`.

Top of the panel by computed preference:

| compound | Asn107 EC50 (nM) | Ile107 EC50 (nM) | Ile107-preference | n(A) | n(I) | published? |
|---|---|---|---|---|---|---|
| **NPSv18.9** | 260.8 | 0.94 | **276.7×** | 5 | 1 | no |
| rNPS(1-10) | 2090.0 | 18.8 | 111.2× | 1 | 1 | yes (Reinscheid lab) |
| hNPS(1-10) | 776.0 | 7.4 | 105.2× | 1 | 1 | yes |
| NPSv16.13 | 1025.7 | 11.1 | 92.7× | 17 | 4 | no |
| NPSv31.7 | 423.1 | 5.2 | 81.0× | 4 | 2 | no |
| NPSv10.16 | 1243.2 | 18.0 | 69.1× | 3 | 2 | no |
| NPSv5.4 | 52.3 | 0.89 | 58.5× | 8 | 2 | no |
| NPSv21.9 | 550.3 | 9.6 | 57.3× | 3 | 2 | no |
| NPSv2-proKKv1 | 310.0 | 7.0 | 44.3× | 6 | 2 | no |
| NPS (native) | 25.8 | 3.8 | 6.8× | 167 | 77 | yes (Reinscheid 2002) |
| ...wrong-direction decoys below this line... |

Gap from `NPSv18.9` to `rNPS(1-10)` is 2.5×. Both `hNPS(1-10)` and `rNPS(1-10)` would be the second-best answers but neither was chosen by the agents.

## Results

| Agent | Predicted | Score | What it did |
|---|---|---|---|
| Codex | `NPSv5.4` | **0/1** | Read files, computed native NPS sequence positioning, made guess. No external retrieval. |
| Claude | `NPSv5.4` | **0/1** | Four web searches on NPS pharmacology, lipidation chemistry, and the Asn107Ile polymorphism specifically. |

Both agents converged on the same wrong answer despite different reasoning paths.

## Codex result

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`codex_modal_stdout.txt`](codex_modal_stdout.txt)

Codex read the prompt and analogs.csv, ran a short Python snippet to index the native NPS sequence positions, and committed. No external retrieval. Picked the compound based on visible modifications without specific variant-selectivity SAR.

## Claude result

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`claude_modal_stdout.txt`](claude_modal_stdout.txt)

Four diagnostic searches:

1. `neuropeptide S NPSR1 Asn107Ile polymorphism structure activity relationship SAR`
2. `neuropeptide S peptide modifications SAR lipidation D-amino acids structure activity`
3. `neuropeptide S NPSR1 N-terminal modifications C-terminal modifications selectivity`
4. `"neuropeptide S" palmitic acid lipidation "gamma-glutamic acid" modifications`

Search #2 and #4 are the relevant ones: claude searched for the *combination* of D-amino acid + palmitoyl lipidation, which exactly matches `NPSv5.4`'s modification profile (`[D-Ser]-FRNGVGTGM-[D-Lys]-K[(γ-E)-(Pal)]-[D-Thr]-NH2`). It found Asahi 2003 (D-Leu15 hardened OXB) and analogous NPS work, decided that "multiple D-amino acids + lipidation = the published optimization template," picked `NPSv5.4`.

The trap claude fell for is not the literature-truncation one: it's "the canonical published peptide-optimization template (D-aa + palmitoyl) means more selective." That template is documented for stability/half-life, not for variant selectivity, but claude conflates the two.

## Failure mode taxonomy

1. **Modification-count heuristic (both agents).** `NPSv5.4` carries 4 visible modifications (D-Ser, D-Lys, D-Thr, palmitoyl) versus `NPSv18.9`'s single visible feature (one heavy lipidation chain). Both agents reward modification count over modification chemistry. The actual selectivity-driving feature in `NPSv18.9` — the unusually long C20-diacid + dual-AEEA linker that creates a binding-pocket footprint asymmetry between Asn107 and Ile107 — is invisible to a "count the substitutions" reading.

2. **Canonical-template mis-application (claude specifically).** Claude searched for and found the well-published "D-amino acid + palmitoyl" template (Asahi 2003 hardened OXB, similar GLP-1 analog work) and applied it to the NPS variant question. That template optimizes proteolytic stability and half-life, *not* variant selectivity. Claude conflated the two via template-matching rather than reasoning about which feature is mechanistically relevant to a polymorphism that changes a single residue in the binding pocket.

3. **Literature-truncation trap was NOT triggered.** The two literature compounds hNPS(1-10) and rNPS(1-10) — top-3 by gold preference — were ignored. Neither agent retrieved the truncation SAR. The agents found *some* published SAR but not the variant-relevant one.

4. **Convergent wrong answer.** Codex and claude land on `NPSv5.4` via independent reasoning paths — a shared bias, not a one-model quirk.

5. **Mis-routed literature retrieval.** Claude's search for `palmitic acid lipidation "gamma-glutamic acid" modifications` is the correct query for a typical peptide-optimization task. This task is variant-discriminating, not optimization-driven, but the canonical-template query fires anyway.
