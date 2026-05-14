# NPSR1 N107I: agents pick the optimization trap, miss the long-arm mechanism

Predict-from-sequence task on intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). Both frontier agents fail at 1/14 random baseline. Both converge on the same wrong compound (`NPSv5.4`), falling for a "looks-comprehensively-optimized" trap (multiple D-amino acids + standard palmitoyl lipidation > a single unusual lipidation linker).

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

## Failure mode taxonomy

1. **Modification-count heuristic (both agents).** `NPSv5.4` carries 4 visible modifications (D-Ser, D-Lys, D-Thr, palmitoyl) versus `NPSv18.9`'s single visible feature (one heavy lipidation chain). Both agents reward modification count over modification chemistry. The actual selectivity-driving feature in `NPSv18.9` — the unusually long C20-diacid + dual-AEEA linker that creates a binding-pocket footprint asymmetry between Asn107 and Ile107 — is invisible to a "count the substitutions" reading.

2. **Canonical-template mis-application (claude specifically).** Claude searched for and found the well-published "D-amino acid + palmitoyl" template (Asahi 2003 hardened OXB, similar GLP-1 analog work) and applied it to the NPS variant question. That template optimizes proteolytic stability and half-life, *not* variant selectivity. Claude conflated the two via template-matching rather than reasoning about which feature is mechanistically relevant to a polymorphism that changes a single residue in the binding pocket.

3. **Literature-truncation trap was NOT triggered.** The two literature compounds hNPS(1-10) and rNPS(1-10) — top-3 by gold preference — were ignored despite both agents finding them in retrieval. Codex explicitly noted the truncations "do not appear to identify one of the CSV IDs directly as the >200-ratio compound" and skipped them; claude went straight to the D-aa + lipidation template.

4. **Convergent wrong answer.** Codex and claude land on `NPSv5.4` via independent reasoning paths and independent retrieval — a shared bias, not a one-model quirk.

5. **Mis-routed literature retrieval.** Claude's searches for `lipidation D-amino acids` and `D-amino acids palmitic acid` are correct queries for a typical peptide-optimization task. This task is variant-discriminating, not optimization-driven, but the canonical-template queries fire anyway and the canonical-template answer (`NPSv5.4`) gets selected.

## Re-run on tightened panel (Modal, 2026-05-13)

The original 14-compound panel had nine candidates within 2.5× of the gold preference, which made it possible to confidently land on the wrong answer through close-discrimination reasoning. The panel was tightened to 5 compounds — keeping the gold (`NPSv18.9`), the trap (`NPSv5.4`), one sibling control (`NPSv18.16` — same K11 lipidation site as the gold but standard C16 palmitoyl, prefers Asn107), the native baseline (`NPS`), and an all-D decoy (`NPSv8`). The gap to the runner-up grew from 2.5× to **4.73×**, and the random-guess baseline went from 7.14% to 20%.

Codex was re-run on Modal (clean container per run, no shared filesystem with claude, no `grade.json` leakage). Claude was attempted but the Modal container is missing Anthropic API credentials (`401 authentication_failed`), so claude could not be evaluated cleanly. Locally, claude continues to refuse this task with the AUP filter.

### Codex result on tightened panel

**Predicted:** `NPSv5.4` — wrong, same trap.
**Score:** 0.0.
**Trace:** runs/cb-nps-polymorphism-001/20260513-201847-db7dadc0-modal/

Codex's verbatim reasoning:

> *"The CSV is small: native NPS, two full-length lipidated analogs, one truncated/lipidated 1-13-like analog with D substitutions, and a full retro-inverso D-peptide. The key literature signal so far is that NPS truncations around residues 1-7/1-8 can become highly Ile107-selective because Asn107 is much less tolerant of changes in the N-terminal/structured region."*
>
> *"The literature table that matters most reports native NPS as only modestly Ile107-favored, while disruption/truncation in the N-terminal/5-13 region can push Asn107/Ile107 EC50 ratios into the hundreds. Within this panel, the only analog combining truncation with stereochemical disruption near the critical N-terminal/5-13 segment is `NPSv5.4`, so I'm writing that as the prediction."*

Codex ran 4 web-search batches, narrowed on the published "truncation + D-aa near the N-terminus → Ile107 selectivity" template, and matched it to `NPSv5.4`. The mechanism it picks is plausible from the literature; it just happens to be the wrong mechanism for the actual winner.

### What the re-run rules out

The hypothesis "panel size / close runners-up is the confounder" is **falsified for codex**: with the close competitors removed and a 4.73× gap to the runner-up, codex still picks `NPSv5.4` based on the same template match. The failure mode is upstream of panel design — codex is doing template-matching to published NPS truncation SAR rather than reasoning about which ligand modifications would amplify the specific Asn→Ile polymorphism at position 107.

To force the right answer, the task would need to either:
- explicitly surface chain-length / arm-geometry metadata so the unique extended lipidation in `NPSv18.9` is visible without atom-counting from the modification string, or
- add structural metadata showing what residue 107 contacts in the bound ligand, so the "long hydrophobic arm reaches position 107" reasoning is grounded.

### Claude — unresolved

Local: AUP refusal (claude-opus-4-7 in claude-code's local harness) — claude won't engage with the peptide prompt.
Modal: 401 authentication error — the Modal container is missing valid Anthropic credentials. Until a `claude-auth` Modal secret is provisioned (mirroring `codex-auth`), claude cannot be evaluated on Modal.
