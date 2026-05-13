# pilot-peptide-pairwise-sequence-nps-easy-011

**One-liner:** Both codex and claude pick the heavily-modified peptide over a simple truncated amide. Gold contradicts: the truncation is 60× more potent *and* a clean full agonist, while the combo-modified peptide is a weak partial agonist.

**Date:** 2026-05-12
**Task type:** `next_experiment` (pairwise potency prediction from sequence)
**Difficulty bucket (as labeled):** `easy` (60.1× potency ratio)
**Real difficulty:** hard — shared blind spot in current frontier LLMs

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

3 records. Partial agonist on Ca2+ (Emax 41%) and IP-1 (74%); **functionally inactive** on β-arrestin. Plates Z' > 0.5 — this is real chemistry, not bad data.

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

## Failure mode taxonomy

Three specific reasoning failures both agents committed, plus one efficacy-related one Claude missed explicitly:

1. **Additivity assumption.** Both agents treated 5 simultaneous modifications as additive improvements. In real medchem, combo modifications routinely *destroy* the active conformation — each may be net-positive in isolation but collectively distort binding geometry. Neither agent flagged combinatorial risk or proposed that "5 modifications at once" is qualitatively different from "1 modification at a time."

2. **"Lipidation = potency boost" misapplied to internal lipidation.** C16-palm at K12 is in the *middle* of the sequence (position 12 of ~20), not at a terminus. Internal lipidation often sequesters the peptide in membranes *away from* the receptor pocket, or sterically blocks binding. Terminal lipidation (the classic potency trick used in e.g. GLP-1 analogs) is mechanistically different. Claude's phrase "major potency enhancer for membrane-associated receptors" is true for terminal lipidation; misapplied here.

3. **No N-terminal active core principle.** NPS biology says the N-terminal `SFRNG...` is the active core; the C-terminal `TSFQRAKS` region is dispensable or destabilizing. `SFRNGVGTGMKKTSFQR-NH2` is exactly a truncation *before* `TSFQRAKS` with a C-amide cap — a textbook way to boost potency for this peptide family. Neither agent invoked "truncation can be good."

4. **Conflated potency and efficacy (Claude specifically).** Claude asserted modifications would improve "potency" without distinguishing potency from efficacy. The data shows the modified peptide loses ~50% Emax and becomes β-arrestin-inactive — heavy backbone modification (β-homoarginine adds a CH2 to the main chain; N-methylation alters H-bonding) can convert full agonists to partial. This is a separate failure mode from #1–3 and is specific to thinking about EC50 in isolation.

## What this means for the benchmark

- **Keep this task.** It's a high-quality reasoning probe — both frontier agents fail it via correct-sounding textbook SAR, which is the most diagnostic possible failure mode.
- **The `easy/medium/hard/trivial` bucket labels are misleading.** "Easy" here refers to the potency *ratio* (60×), not the task's actual difficulty for an LLM. Both agents got this 60× pair wrong while getting the 2× pair right. Worth renaming buckets to `ratio_2_5x` / `ratio_5_30x` / `ratio_30_100x` / `ratio_gte_100x` to avoid confusing readers.
- **Targeted task ideas seeded by this finding:**
  - More "combo-mod vs focused-truncation" pairs to confirm this isn't a one-off.
  - Pairs that isolate internal-lipidation vs terminal-lipidation explicitly.
  - Pairs that test efficacy reasoning (full agonist vs partial agonist) since potency-only framing missed it.

## Reproducing

```bash
uv run capablebench run \
  pilot-peptide-pairwise-sequence-nps-easy-011 \
  --runs-dir /absolute/path/to/runs \
  --agent-command '<codex-or-claude-command>'
```

Use absolute `--runs-dir`; relative paths fail because the runner subprocess `cwd`s into the run directory before the shell expands `$(cat {prompt_file})`.

## Source run directories (ephemeral)

- Codex run: `runs/saturation_codex/pilot-peptide-pairwise-sequence-nps-easy-011/20260512-224351/`
- Claude run: `runs/saturation_claude/pilot-peptide-pairwise-sequence-nps-easy-011/20260512-224437/`

These are gitignored — the preserved traces in this folder are the durable record.
