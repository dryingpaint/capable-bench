# Agents pick the more modified peptide; the simpler one is 60× more potent (pilot-peptide-pairwise-sequence-nps-easy-011)

Both codex and claude pick the heavily-modified peptide over a simple truncated amide. Gold contradicts: the truncation is 60× more potent *and* a clean full agonist, while the combo-modified peptide is a weak partial agonist.

**Date:** 2026-05-12
**Task type:** `next_experiment` (pairwise potency prediction from sequence)

## The task

The agent is given only `peptide_id`, `modification` (sequence + chemistry), `receptor_family`, and `receptors` (variants tested). No EC50, Emax, fold, or assay counts. It must pick the more potent of two peptides at the NPS receptor family.

Inputs shown to the agent:

```csv
peptide_id,modification,receptor_family,receptors
PEP-17D19C9AD5,SFRNGVGTGMKKTSFQR-NH2,NPS,hNPSR1 Asn107;hNPSR1 Ile107
PEP-C9FE4F8ED3,D-Ser1 + β-hArg3 + Nle10 + N-Me-K11 + C16-palm-K12 + C-term amide (combo),NPS,hNPSR1 Asn107;hNPSR1 Ile107
```

**Gold answer:** `PEP-17D19C9AD5` (the simple truncated amide).

## Why the gold is correct (raw assay verification)

The gold is `best_ec50_nm` sorted ascending; the underlying lab records are robust:

**PEP-17D19C9AD5** (`SFRNGVGTGMKKTSFQR-NH2`, gold winner):

| date | receptor | assay | ec50_nm | emax_pct |
|---|---|---|---|---|
| 2026-03-12 | hNPSR1 Asn107 | Ca2+ | **0.9987** | 95.69 |
| 2026-03-10 | hNPSR1 Ile107 | IP-1 | 1.4321 | 101.86 |
| 2026-03-12 | hNPSR1 Ile107 | Ca2+ | 7.7736 | 90.37 |
| 2026-03-10 | hNPSR1 Asn107 | IP-1 | 15.9149 | 100.17 |
| 2026-03-12 | hNPSR1 Asn107 | cAMP | 44.5697 | 106.39 |
| 2026-03-11 | hNPSR1 Asn107 | b-Arrestin | 57.4878 | 97.25 |

6 records, clean full agonist (Emax 90–106%) on every assay/receptor combination. All plates Z' > 0.5.

**PEP-C9FE4F8ED3** (heavy-combo modifications, what both agents picked):

| date | receptor | assay | ec50_nm | emax_pct |
|---|---|---|---|---|
| 2026-01-09 | hNPSR1 Ile107 | Ca2+ | **60.02** | 41.46 |
| 2026-01-06 | hNPSR1 Ile107 | IP-1 | 75.10 | 73.99 |
| 2026-03-11 | hNPSR1 Asn107 | b-Arrestin | 5000.00 | 4.74 |

3 records. Partial agonist on Ca2+ (Emax 41%) and IP-1 (74%); **functionally inactive** on β-arrestin. All plates Z' > 0.5.

So the modified peptide isn't just less potent — it's a *partial agonist* and *β-arrestin-dead*. The gap is both potency and efficacy, in the same direction.

## Codex result

**Predicted:** `PEP-C9FE4F8ED3` — **WRONG**.
**Trace:** [`codex_trace.txt`](codex_trace.txt)

Codex's reasoning was terse but explicit:

> "The two candidates are an unmodified amidated NPS-like sequence and a heavily optimized analog with D-Ser1, beta-hArg3, Nle10, N-methyl lysine, and C16 palmitoylation. I'm writing the modified analog as the lower-EC50 prediction."

Applied "modifications → more potent" as a default heuristic. Did not consider combinatorial interference, internal-vs-terminal lipidation, or efficacy.

## Claude result

**Predicted:** `PEP-C9FE4F8ED3` — **WRONG**.
**Trace:** [`claude_trace.txt`](claude_trace.txt)

Claude's reasoning was much more detailed and is the more diagnostic of the two. It attributed each modification a textbook-correct individual function:

> - "D-Ser1: D-serine at position 1 (proteolytic resistance)"
> - "β-hArg3: β-homoarginine at position 3 (enhanced electrostatic binding)"
> - "Nle10: Norleucine at position 10 (optimized hydrophobic interaction)"
> - "N-Me-K11: N-methylated lysine at position 11 (metabolic stability)"
> - "C16-palm-K12: C16 palmitic acid lipidation at position 12 (membrane association)"

Then collapsed all five into an additive claim:

> "The extensive chemical optimization in PEP-C9FE4F8ED3, particularly the lipidation, should provide significantly higher potency at NPS receptors compared to the unmodified sequence."

## Failure modes

Three specific reasoning failures both agents committed, plus one efficacy-related one Claude missed explicitly:

1. **Additive-modification fallacy.** Both agents treated 5 simultaneous modifications as additive improvements, missing that combo modifications routinely destroy the active conformation even when each is net-positive in isolation.

2. **"Lipidation = potency boost" misapplied to internal lipidation.** C16-palm at K12 sits mid-sequence (position 12 of ~20), where internal lipidation typically sequesters the peptide in membranes or sterically blocks binding — a mechanism distinct from the terminal lipidation trick used in e.g. GLP-1 analogs.

3. **No N-terminal active core principle.** Neither agent invoked the textbook "truncation before `TSFQRAKS` + C-amide cap boosts potency" move, despite `SFRNGVGTGMKKTSFQR-NH2` being exactly that.

4. **Conflated potency and efficacy (Claude specifically).** Claude asserted modifications would improve "potency" without distinguishing it from efficacy, missing that the heavy backbone modifications (β-homoarginine, N-methylation) convert the full agonist to a partial one (~50% Emax loss, β-arrestin-inactive).

## Golden reasoning trace

What the correct rationale looks like from the same inputs.

1. *The N-terminal SF... motif of NPS is the receptor-recognition core.* NPS = 20-residue peptide `SFRNGVGTGMKKTSFQRAKS`. The N-terminal Ser-Phe is essential for full Gq-coupled potency at NPSR1 (Reinscheid 2005; Roth 2006). Any modification at position 1 typically costs ≥10× in potency.
2. *PEP-17D19C9AD5 = NPS-(1–17)-NH₂* — a 17-residue truncation of native NPS with a C-terminal amide cap. The active N-terminal core is intact; the C-terminal `AKS` (positions 18–20) is removed. That segment is dispensable for in vitro potency and is a metabolism-driven liability, not a binding contact. Truncate + amide-cap is a standard medchem move that *boosts* observed in vitro potency.
3. *PEP-C9FE4F8ED3 modifies position 1 with D-Ser.* D-amino-acid substitution at position 1 inverts N-terminal chirality and breaks the helix nucleation NPS uses for receptor engagement. Expected effect: ≥10× potency loss.

