# Golden trace draft: `pilot-peptide-pairwise-sequence-nps-easy-011`

## Inputs shown to the agent

```csv
peptide_id,modification,receptor_family,receptors
PEP-17D19C9AD5,SFRNGVGTGMKKTSFQR-NH2,NPS,hNPSR1 Asn107;hNPSR1 Ile107
PEP-C9FE4F8ED3,"D-Ser1 + β-hArg3 + Nle10 + N-Me-K11 + C16-palm-K12 + C-term amide (combo)",NPS,hNPSR1 Asn107;hNPSR1 Ile107
```

## Gold

`PEP-17D19C9AD5` is more potent (potency ratio 60.1×).

## Observed evidence (FULLY VERIFIED — straight from `data/processed/invitro_assays.csv`)

**PEP-17D19C9AD5** (compound `NPSv26.2`): 6 records, all internal, all status=tested, all plates Z' > 0.5.

| receptor | assay | EC50 (nM) | Emax (%) |
|---|---|---:|---:|
| hNPSR1 Asn107 | Ca2+ | **0.9987** | 95.7 |
| hNPSR1 Ile107 | IP-1 | 1.43 | 101.9 |
| hNPSR1 Ile107 | Ca2+ | 7.77 | 90.4 |
| hNPSR1 Asn107 | IP-1 | 15.91 | 100.2 |
| hNPSR1 Asn107 | cAMP | 44.57 | 106.4 |
| hNPSR1 Asn107 | b-Arrestin | 57.49 | 97.3 |

Best EC50 = **1.0 nM**; full agonist on every assay/receptor combination (Emax 90–106%).

**PEP-C9FE4F8ED3** (compound `NPSv14`): 3 records, all internal, all status=tested.

| receptor | assay | EC50 (nM) | Emax (%) |
|---|---|---:|---:|
| hNPSR1 Ile107 | Ca2+ | **60.02** | 41.5 |
| hNPSR1 Ile107 | IP-1 | 75.10 | 74.0 |
| hNPSR1 Asn107 | b-Arrestin | 5000 (capped) | 4.74 |

Best EC50 = **60.0 nM**; partial agonist on Ca2+ (41%) and IP-1 (74%); **functionally inactive** on β-arrestin.

Observed gap: best EC50 ~60× in favor of PEP-17D19C9AD5, plus ~40 percentage-point Emax gap, plus β-arrestin functional loss in the combo-mod variant. The label is overdetermined — three independent signals point the same way.

## Mechanistic hypothesis

**HIGH-confidence (well-documented in NPS / GPCR ligand SAR):**

1. *The N-terminal SF... motif of NPS is the receptor-recognition core.* NPS = 20-residue peptide `SFRNGVGTGMKKTSFQRAKS`. The N-terminal Ser-Phe is essential for full Gq-coupled potency at NPSR1 (Reinscheid 2005; Roth 2006). Any modification at position 1 typically costs ≥10× in potency.
2. *PEP-17D19C9AD5 = NPS-(1–17)-NH₂* — a 17-residue truncation of native NPS with a C-terminal amide cap. The active N-terminal core is intact; the C-terminal `AKS` (positions 18–20) is removed. The C-terminal segment is dispensable for in vitro potency and known to be a metabolism-driven liability rather than a binding contact. Truncating it + amide-capping is a standard medchem move that *boosts* observed in vitro potency.
3. *PEP-C9FE4F8ED3 modifies position 1 with D-Ser.* D-amino-acid substitution at position 1 of NPS inverts the N-terminal chirality. This breaks the N-terminal helix nucleation that NPS uses for receptor engagement. Expected effect: ≥10× potency loss, consistent across the GPCR-active peptide family.

**MEDIUM-confidence (plausible from family):**

4. *β-homoarginine at position 3* adds a CH₂ to the backbone, perturbing local geometry. Generally tolerated as a stability modification but rarely improves potency.
5. *Internal lipidation (C16-palm at K12, inside the sequence)* differs mechanistically from C-terminal lipidation. Internal lipidation can sequester the peptide in cell membranes away from the receptor pocket or sterically obstruct binding. The Emax loss to partial agonism on Ca2+ (41%) is consistent with an altered binding pose that engages the receptor incompletely.

**SPECULATIVE (cannot be quantitatively pinned from this data alone):**

6. *β-arrestin functional loss.* The combo variant goes from agonist on Ca2+/IP-1 to inactive on β-arrestin. This suggests a biased partial agonist phenotype — possibly because the altered binding pose engages G-protein machinery suboptimally and fails to recruit β-arrestin entirely. *Cannot be confirmed without single-modification controls; the combo confounds attribution.*
7. *Exact contribution of each modification.* The combo variant carries five modifications simultaneously. Without per-modification ablation data we cannot say "N-terminal D-Ser1 contributes X×, internal palmitoylation contributes Y×, …" with quantitative confidence.

## Bottom line

Gold label is supported by:
- Direct lab observation (60× potency, 40-point Emax, β-arrestin loss — three independent signals).
- Established NPS-family SAR (N-terminal modification = bad; truncation of C-terminal AKS = neutral-to-good).
- Plausible secondary mechanisms (internal lipidation, backbone modification) for the Emax / β-arrestin gap.

**Cannot resolve from this data alone:** quantitative per-modification attribution; whether β-arrestin loss is a pose effect or a separate failure.

**Estimated overall confidence in the mechanistic rationale: ~80%.**
