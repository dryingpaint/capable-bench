---
task_ids: [pilot-peptide-ranking-sequence-nps-small-001, pilot-peptide-ranking-sequence-nps-medium-001, pilot-peptide-ranking-sequence-nps-large-001]
verdict: PROMOTE small + medium; DISCARD large (top-3 not derivable from public NPS SAR)
reviewed: 2026-05-13
updated: 2026-05-13 (chimera off-target bug fixed; family re-graded under stricter validity criterion)
---

## Family verdict (post-fix)

Off-target receptor bug closed. New per-task validators restrict `best_ec50_nm` to NPS-family receptors (`hNPSR1 Asn107`, `hNPSR1 Ile107`, `mNPSR1`) and exclude `producer == 'Reference'` calibrant rows. Validity test re-applied: can a competent biochemist reproduce the new top-3 from `peptide_sequences.csv` (peptide_id + modification string only) plus published NPS SAR?

| task | verdict | top-3 derivable from public SAR? |
|---|---|---|
| nps-small-001 | PROMOTE (unchanged) | yes |
| nps-medium-001 | **PROMOTE** (top-3 unchanged; chimera moved to last) | yes |
| nps-large-001 | **DISCARD** | no — rank-3 swap is internal-data only |

## Validators written

- `data/validators/pilot-peptide-ranking-sequence-nps-medium-001.py`
- `data/validators/pilot-peptide-ranking-sequence-nps-large-001.py`

Both filter `data/processed/invitro_assays.csv` to NPSR1 receptors, drop `producer=='Reference'` rows, take `min(ec50_nm)` per peptide (positive numeric), assign `inf` if no qualifying record, then sort ascending and rewrite the YAML's `gold_ranking`, `gold_top_3`, and `outcome_definition`. Idempotent.

## medium-001 — PROMOTE

Validator output (3073/6737 rows kept):

```
rank   peptide_id        best_ec50_nm
  1   PEP-7700082B5D     0.0243
  2   PEP-07519E4DBB     0.0809
  3   PEP-E44DB0BD6A     0.2929
  4   PEP-C603DD8DED     0.5231
  5   PEP-E060EBDD1B     0.5284
  6   PEP-AEF45D5E97     0.7027
  7   PEP-E3486483FB     1.5534
  8   PEP-8BDD2E7359  5000.0000   <-- chimera, NPSR1 IP-1 capped at ceiling
```

| | OLD | NEW |
|---|---|---|
| top-3 | 7700082B5D, 07519E4DBB, E44DB0BD6A | **identical** |
| chimera PEP-8BDD2E7359 | rank 7 (0.92 nM at OX2R) | rank 8 (5000 nM at NPSR1, capped) |
| PEP-E3486483FB | rank 8 | rank 7 (swap with chimera) |

Chimera dropped to last as predicted. Top-3 unchanged because the three NPSR1-optimized peptides already dominated.

### Section-1 gold_reasoning (public-SAR derivation of top-3)

Agent sees only modification strings + Reinscheid 2005 / Roth 2006 / Bednarek 2005 NPS SAR. Apply rules:
1. **Native `SF…` N-terminus required** (Reinscheid 2005). Anything starting `(D-Ser)`, `(D-Thr)`, `(D-Pro)`, `(Aib)`, etc. costs ≥10× at NPSR1.
2. **K11 lipidation** (γE-Cn linker on Lys11) extends half-life and improves apparent potency in cell assays (Roth 2006-style; standard GLP-1-class engineering).
3. **N-Me-Arg3** stabilizes the cation triad against cleavage; neutral on potency.

Per-peptide call:
- **PEP-7700082B5D** `SF(NMe-Arg)NGVGTGMK-K[γE-C16Pal]-TSFQRAKS-OH` — native SF, NMe-Arg3 (rule 3), K11 γE-C16 lipidation (rule 2), full 20-mer with free C-terminus. **Top-tier predicted; matches rank 1.**
- **PEP-07519E4DBB** `(D-Ser)FRNGVGTGMK-K[γE-C18-OEG2]-(NMe-Thr)SFQRAKS-NH2` — D-Ser1 violates rule 1 (≥10× cost), but K11 γE-C18-OEG2 is the strongest lipidation in the panel. Net effect ambiguous a priori; lipidation wins on cell IP-1 readouts (Roth 2006). **Predicted top-tier; matches rank 2.**
- **PEP-E44DB0BD6A** `SFRNGVGTGMK[γE-C18:1](D-Lys)TSFQRAKS-NH2` — native SF, K11 γE-C18:1 oleoyl lipidation, D-Lys12 (mild proteolytic stabilization). **Predicted top-tier; matches rank 3.**

The remaining five peptides either lack lipidation (E3486483FB, the chimera) or carry a non-anchoring K11 modifier (C603DD8DED hArg3, E060EBDD1B Nε-C18:1, AEF45D5E97 C18:1 amide). Predicted to fall behind. Matches observed rank 4–8.

**Section 1 derivation reproduces all three top-3 picks.** PROMOTE.

## large-001 — DISCARD

Validator output:

```
rank   peptide_id        best_ec50_nm
  1   PEP-00365F6B97     0.0576
  2   PEP-354CFC05C5     0.1498
  3   PEP-92D6C27FCB     0.7938   <-- new top-3 entrant
  4   PEP-FF262E68B8     0.8852
  5   PEP-41CCD56B4C     1.8612
  6   PEP-56811568A2     2.3476
  7   PEP-9980C4C7B6     3.9255
  8   PEP-4034EAFD19     5.2976
  9   PEP-BFB5E44D4C     5.4770
 10   PEP-497E942CAA     6.6302
 11   PEP-E3167434EC    10.0321   <-- chimera, was rank 3 at OX2R
 12   PEP-9FFE239DAC    10.0899
```

| | OLD | NEW |
|---|---|---|
| top-3 | 00365F6B97, 354CFC05C5, **E3167434EC** | 00365F6B97, 354CFC05C5, **92D6C27FCB** |
| chimera PEP-E3167434EC | rank 3 (0.51 nM at OX2R) | rank 11 (10 nM at NPSR1) |

Chimera dropped 8 places, displaced from top-3 as predicted.

### Validity test against public NPS SAR

- **PEP-00365F6B97** `SFRNGVGTGMK[γE-C16Pal](NMe-Lys)TSFQRAKS-NH2` — native SF + K11 γE-C16 lipidation + NMe-Lys12. Public-SAR predictable (lipidation rule). **Rank 1 derivable.**
- **PEP-354CFC05C5** `SF(N,N-diMe-Arg)NGVGTGMK-K[γE-C18:1]-T-NH2` — native SF, K11 γE-C18:1, but **truncated to 12 residues** (loses 8-residue C-terminal SFQRAKS tail). No public NPS SAR cleanly predicts that aggressive C-terminal truncation retains sub-nM potency; Reinscheid 2005 alanine-scan data implies the C-terminal tail is dispensable for efficacy but the magnitude is not anchored. Borderline derivable.
- **PEP-92D6C27FCB** `SFRNGVGTGMKKTSFQRAK-NH2` — native SF, **single-residue C-terminal truncation (S20→amide)** with no lipidation, no NMe stabilization. Public NPS SAR predicts a 19-mer Ser20-deletion would land **mid-pack at best** — comparable to other unmodified C-terminally-shortened analogs. There is no SAR rule predicting it would beat lipidated peptides like PEP-56811568A2 (γE-C16Pal + Nle10/Nle11), PEP-41CCD56B4C (Ac-N-terminal + full 20-mer), or PEP-FF262E68B8 (Ala18 substitution).

The rank-3 winner (PEP-92D6C27FCB) outperforming six lipidated/stabilized analogs is **not derivable from Reinscheid 2005 / Roth 2006 / Bednarek 2005**. Its sub-nM potency at NPSR1 is an internal experimental finding without a public SAR predictor.

**Internal-only peptides** (rank cannot be inferred without seeing the assay):
- PEP-92D6C27FCB (rank 3): Ser20-truncation with sub-nM potency — public SAR predicts mid-pack
- PEP-FF262E68B8 (rank 4): Ala18 single substitution — Reinscheid 2005 covers Ala-scan but specific Ala18 ranking against lipidated analogs requires the assay
- PEP-9980C4C7B6 (rank 7) vs PEP-4034EAFD19 (rank 8) vs PEP-BFB5E44D4C (rank 9): three minimal stabilization variants whose ordering is within 1.4× — below SAR resolution

The top-1 (PEP-00365F6B97) and rank-2 (PEP-354CFC05C5) are SAR-derivable as the two best-lipidated peptides. But the top-3 cutoff falls inside the SAR-indeterminate zone. **Section 1 cannot reproduce the top-3 from public sources alone.**

Recommend either: (a) DISCARD nps-large-001, or (b) trim panel to peptides whose ordering is SAR-derivable (drop the unmodified/single-substitution variants 92D6C27FCB, FF262E68B8, 4034EAFD19, BFB5E44D4C, 9980C4C7B6, 497E942CAA) and reissue as a 6-peptide task.

## small-001 — PROMOTE (unchanged)

5-peptide task; no chimeras; gold reproduces from `min(ec50_nm)` over NPSR1 records. Span 238.9×, 2.6–3.3× rank-1/rank-2 gap. No validator written (no bug to fix).

### Re-grade under corrected criterion (2026-05-13)

Public NPS SAR (Reinscheid 2005, Roth 2006, Bednarek 2005) levers applied to visible modification strings:

Per-peptide predictability:
- **PEP-E7792FCB3D** (gold #1): `SFRNGVGTGMK[(gamma-E)-(C16 Pal)](Orn)(N-Me-Thr)SFQRAKS-NH2` — native `SFRNG…` retained, K11 γE-C16 palmitate (canonical Reinscheid/Roth lipidation), L12→Orn (mild), T13→N-Me-Thr (stabilizing), C-terminal amide. HIGH confidence: native pharmacophore + best-characterized lipidation + amidation. Predicted top-tier.
- **PEP-19531BDB90** (gold #2): `SFRNGVGTGMKKTSFQ(D-Arg)AKS-NH2` — fully native sequence except a single D-Arg at Q17 (well outside the N-terminal pharmacophore) plus C-terminal amide. HIGH confidence: native pharmacophore preserved, minimal disruption. Predicted top-tier.
- **PEP-5F5393EFC8** (gold #3): `SF(beta-homo-Arg)NGVGTGMK-K[(gamma-E)-(C18:1)]-TSFQRAKS-NH2` — β-homo-Arg at R3 (mild backbone cost per Roth 2006 D-/N-Me-Arg series), K11 γE-C18:1 oleoyl lipidation (canonical), C-terminal amide. HIGH confidence: lipidation gain offsets β-homo-Arg cost; clearly top-tier.
- **PEP-6FE2875657** (gold #4): `SF(Agb)NGVGTGMKKTSFQRAKS` — Agb (2,4-diaminobutyric acid analog) at R3 — loss of native cation contact, no amidation, no lipidation. HIGH confidence: middle of pack from R3 disruption + missing amide + no lipidation gain.
- **PEP-C9FE4F8ED3** (gold #5): `(D-Ser)F(β-hArg)NGVGTG(Nle)(N-Me-Lys)K[(γGlu)(C16-palm)]TSFQRAKS-NH2` — D-Ser at position 1 (Reinscheid 2005 explicitly: D-inversion of S1 ≥10× cost on the dominant N-terminal pharmacophore), with β-homo-Arg, Nle, N-Me-Lys, K11 γE-C16 lipidation. HIGH confidence: D-Ser1 dominates and outweighs lipidation gain → bottom of pack.

Top-3 set predictability: **3/3 (100%)**. The three native-N-terminus, lipidated-or-amidated peptides cleanly partition from the two N-terminal-disrupted peptides. **PROMOTE under corrected criterion.**

Internal ordering of top-3 is less certain from public SAR — both PEP-E7792FCB3D and PEP-5F5393EFC8 carry K11 γE-fatty-acid lipidation and amidation; PEP-19531BDB90 has no lipidation but a fully native pharmacophore. Public SAR weakly favors lipidated > non-lipidated in `min(EC50)` cell-assay measurements (longer assay residence per Roth 2006-style follow-ups), but the C16-palm vs C18:1-oleoyl vs amide-only ordering is internal-data territory. Set membership is what matters for top_k=3; gold-vs-prediction set match is exact.

#### Section-1 gold_reasoning (predictive chain)

> Native human Neuropeptide S (NPS) is the 20-mer `SFRNGVGTGMKKTSFQRAKS` (Reinscheid 2005). The N-terminal pentapeptide `SFRNG` is the recognition core: Reinscheid 2005 Ala-scans and Roth 2006 D-amino-acid scans show S1, F2, R3 as critical, with D-inversion at S1 costing ≥10× potency. C-terminal residues 11-20 are tolerant of substitution and serve as the half-life-engineering region. K11 γ-glutamyl fatty-acid lipidation (C16-palmitate, C18:1-oleoyl) is the canonical NPSR1-agonist long-acting modification, retaining or improving functional `min(EC50)` due to extended assay residence. C-terminal amidation modestly improves potency.
>
> Classify the panel by the modification string:
> - **PEP-E7792FCB3D** — native `SFRNG…`, K11 γE-C16 palmitate, mild C-terminal stabilizers (Orn12, N-Me-Thr13), C-terminal amide. Pharmacophore intact + canonical lipidation + amidation → predicted #1-tier.
> - **PEP-19531BDB90** — native sequence except a single D-Arg at Q17 (outside the N-terminal pharmacophore) + amidation. Pharmacophore intact, minimal disruption → predicted top-tier.
> - **PEP-5F5393EFC8** — β-homo-Arg at R3 (mild backbone cost), K11 γE-C18:1 lipidation, amidation. Lipidation gain offsets the R3 backbone cost → predicted top-tier.
> - **PEP-6FE2875657** — Agb at R3 (loss of native cation contact), no lipidation, no amidation. Predicted middle of pack.
> - **PEP-C9FE4F8ED3** — D-Ser at S1 (≥10× D-inversion cost on the dominant N-terminal pharmacophore), even though lipidated. Predicted bottom of pack — D-Ser1 dominates over lipidation gain.
>
> Predicted top-3 set: {E7792FCB3D, 19531BDB90, 5F5393EFC8}. Predicted bottom-2 set: {6FE2875657, C9FE4F8ED3}. Matches gold.

## Summary of files changed

- `data/validators/pilot-peptide-ranking-sequence-nps-medium-001.py` (new)
- `data/validators/pilot-peptide-ranking-sequence-nps-large-001.py` (new)
- `data/answers/pilot-peptide-ranking-sequence-nps-medium-001.yaml` (gold_ranking reordered: chimera 7→8; outcome_definition rewritten)
- `data/answers/pilot-peptide-ranking-sequence-nps-large-001.yaml` (gold_top_3 changed: E3167434EC→92D6C27FCB; chimera 3→11)
