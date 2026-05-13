# Golden trace draft: `pilot-peptide-pairwise-sequence-mch-easy-011`

## Inputs shown to the agent

```csv
peptide_id,modification,receptor_family,receptors
PEP-77A315C29A,Trp17 f Ala,MCH,MCHR1;MCHR2
PEP-021CF7B0A5,D-Cys7,MCH,MCHR1;MCHR2
```

(The "f" in `Trp17 f Ala` is an OCR artifact for "→" / "to".)

## Gold

`PEP-77A315C29A` is more potent (potency ratio 30.67×, computed from `best_ec50_nm`).

## Observed evidence (FULLY VERIFIED — `data/processed/invitro_assays.csv`)

**PEP-77A315C29A** (compound `[Ala17]hMCH`): 4 records. Source: **Bednarek 2001 Table 1 alanine scan**.

| receptor | assay | EC50/IC50 (nM) | Emax (%) |
|---|---|---:|---:|
| MCHR1 | binding IC50 | **0.15** | — |
| MCHR2 | binding IC50 | 3.5 | — |
| MCHR1 | Ca2+ agonist | 17 | 104 |
| MCHR2 | Ca2+ agonist | 54 | 95 |

Best EC50/IC50 = **0.15 nM**; full agonist on functional readouts (Emax 95–104%).

**PEP-021CF7B0A5** (compound `MCH core19 D-Cys7`): 4 records. Source: **Bednarek 2001 Table 5 D-amino-acid scan on "compound 19"**.

| receptor | assay | EC50/IC50 (nM) | Emax (%) |
|---|---|---:|---:|
| MCHR1 | binding IC50 | **4.6** | — |
| MCHR2 | binding IC50 | 590 | — |
| MCHR1 | Ca2+ agonist | 910 | 67 |
| MCHR2 | Ca2+ agonist | 750 | 81 |

Best EC50/IC50 = **4.6 nM**; partial agonist on Ca2+ (Emax 67% MCHR1, 81% MCHR2).

Observed gap: 30× in MCHR1 binding IC50; ~50× in Ca2+ MCHR1; ~170× in MCHR2 binding IC50; plus a 37-point Emax drop. The label is overdetermined as an observation.

## ⚠️ Critical caveat: the two peptides have *different parent backbones*

This is the load-bearing complication for a "fully accurate" mechanistic rationale. Per the Bednarek 2001 source notes:

- `[Ala17]hMCH` (PEP-77A315C29A) is **full human MCH (19 residues, `DFDMLRCMLGRVYRPCWQV`)** with a Trp17→Ala substitution. From Bednarek 2001 Table 1.
- `MCH core19 D-Cys7` (PEP-021CF7B0A5) is **"compound 19"** — Bednarek's truncated MCH cyclic-core analog (likely an MCH-(5–17)-derivative or similar) — with a D-Cys7 substitution. From Bednarek 2001 Table 5.

These have different starting potencies. **A naïve reading of "Trp17→Ala vs D-Cys7" assumes a common parent; the lab data doesn't have one.** The 30× ratio includes whatever potency gap exists between the *unmodified* full hMCH and the *unmodified* compound-19 core.

The agent has no way to know this from the inputs shown — the `modification` field strips the backbone context.

## Mechanistic hypothesis

**HIGH-confidence (Bednarek 2001 literature, directly cited in our notes):**

1. *Bednarek 2001 Table 1 alanine scan on hMCH*: Trp17 (the C-terminal aromatic after the cyclic core) tolerates Ala substitution well. The alanine scan generally shows the cyclic core residues (Met–Leu–Gly–Arg–Val–Tyr–Arg–Pro between the two Cys) are individually critical, while flanking residues (the N-terminal `DFDML` and the C-terminal `QV` plus Trp17) are more tolerant. `[Ala17]hMCH` retains near-native potency.
2. *Bednarek 2001 Table 5 D-amino-acid scan on compound 19*: D-amino acid substitutions at the Cys residues (Cys7 or Cys16) **drop potency by 1–3 orders of magnitude** because they prevent native disulfide-bridge formation. The peptide effectively linearizes.
3. *MCH active conformation requires the Cys7–Cys16 disulfide.* This is established in the broader MCH literature (Audinot, Macdonald, the Bednarek series itself). Without the bridge, the cyclic active conformation isn't presented to the receptor.

**MEDIUM-confidence:**

4. *Why the gap is ~30× and not ~300×:* Because the two peptides have different parents, the ratio reflects both backbone difference and modification effect. The Bednarek 2001 paper itself shows D-Cys substitutions in his compound 19 cause ~100× loss; against a less-potent parent the resulting EC50 is in the low-µM range. The full hMCH parent is more potent (subnanomolar binding), so `[Ala17]hMCH` lands at 0.15 nM. Apparent ratio = 30× collapses two effects.
5. *Emax drop in the D-Cys7 variant is consistent with a partial agonist resulting from incomplete disulfide formation* — the population of correctly bridged molecules engages the receptor; the linearized population doesn't. Cannot be confirmed without HPLC separation of the populations.

**SPECULATIVE / NOT RESOLVABLE from this data alone:**

6. *Magnitude of the bridge-disruption effect on compound 19 specifically.* We have the modified compound 19 data (4.6 nM MCHR1 binding) but not the unmodified compound 19 data — so the per-modification effect of D-Cys7 vs the compound-19 parent isn't directly computable from our local data. The Bednarek 2001 paper has it, but it's not in our curated panel.
7. *Pure mechanism attribution for the Trp17→Ala effect.* From Table 1 we know [Ala17]hMCH is potent; we don't have the wild-type hMCH IC50 in our data either, so the same parent-controlled comparison isn't possible.

## Bottom line

Gold label as an observation is solid:
- Both peptides have 4 high-quality records each, with Bednarek 2001 literature provenance.
- All four MCH1/MCH2 × binding/Ca2+ measurements consistently favor `[Ala17]hMCH`.
- Emax + EC50 + receptor coverage agree.

But the **mechanistic rationale as currently formulatable mixes a backbone effect with a modification effect**. A "fully accurate" trace would have to either:
- Add the parent EC50s to the panel (full hMCH + compound 19), and decompose the ratio into "backbone gap × Trp17→Ala effect × D-Cys7 effect"; or
- Acknowledge explicitly that the comparison is between two compounds from different parent series rather than two modifications of a common parent.

**Estimated overall confidence in the mechanistic rationale: ~60%** if we limit to data in `data/processed/`. ~85% if we incorporate published Bednarek 2001 parent data (Table 1 + Table 5 native rows), which we'd need to add to the panel.
