# Codex leads claude on every task type — half of claude's gap is tool-use

**Date:** 2026-05-13
**Run:** all 77 previously-missing (task × agent) pairs against the latest curated benchmark, plus latest-run aggregation across the rest of the corpus.

## Headline

- Codex outperforms claude on every task type, gaps of 7–15pp.
- **Codex saturates `next_experiment`** (mean 1.00, n=4) — crosses the 0.9 gate. Tiny n, but flag per saturation rule.
- **`hit_prediction` is at chance for both** (0.46 / 0.46 on a binary task). Likely intrinsic: 6/24 of these tasks sit inside the p-value noise band.
- **`pairwise` is near coin-flip for claude** (0.52 across 60 tasks). Codex slightly better (0.60).
- **Claude has a tool-use reliability problem:** 7 of 17 "lost" discriminator tasks are simply never writing `answer.json` — not reasoning failures. Adjusting for that, head-to-head reasoning is **codex 10 / claude 7** across 17 hard tasks, much closer to even.

## Scores by task type

![Scores by task type, claude vs codex, latest run per (task, agent)](scores_by_task_type.png)

Each bar is the mean score across all tasks of that type for that agent, computed from each task's most recent run. `n` is the number of tasks of that type that have been run by that agent.

| task type        | claude n / mean    | codex n / mean    | notes                              |
|------------------|--------------------|--------------------|----------------------------------|
| pairwise         | 60 / 0.52          | 60 / 0.60          | claude near coin-flip              |
| multitarget      | 43 / 0.79          | 43 / 0.87          | strongest signal of differentiation |
| cb-curated       | 5 / 0.40           | 4 / 0.50           | small n, intentionally hard        |

`hit_prediction`, `ranking`, `prioritization`, and `next_experiment` are excluded from the plot — `hit_prediction` is at chance for both, and the others have small n or discrete-fraction graders that make the headline comparison harder to read. See "Executive summaries" below for context on those buckets.

## Executive summary per task type

**pairwise** — pick the more-potent of 2 peptides from sequence only; gold = held-out EC50 ratio. Both near coin-flip on a binary forced choice. Either the curated potency gap isn't large enough to read from sequence, or the agents lack a real SAR prior. Consistent with the in-flight failure-mode triage.

**multitarget** — per-family active/inactive (NPS/OXN/MCH); active = min EC50 ≤ 1000 nM. Both well above chance (random ~0.125 for 3 independent binaries). Strongest evidence of real differentiation; codex +8pp.

**hit_prediction** — in-vivo significance call given dose + in-vitro profile. Effectively at chance for both. Recall 6/24 sit inside the p-value noise band — this bucket is not currently discriminating models.

**ranking** — pick top-3 of N candidates; grader is precision@3 (0 / 0.33 / 0.67 / 1.0). Hardest bucket — claude lands at 0 or 0.33 on most tasks. Consistent with the <2× top-3 cutoffs we flagged earlier.

**prioritization** — precision@k / nDCG@k over a longer ranked list. Both clustered ~0.67; small n.

**cb-curated** — bespoke (orexin selectivity, NPS polymorphism, MCH disulfide). Tiny n; both well below saturation, which is the intent.

**next_experiment** — pick the most informative next experiment (MRR over ranked options). Codex saturates this bucket (1.00) but n=4 is too small to act on alone.

## Clean discriminators

24 tasks where one agent scored 0.0 and the other ≥0.99 on the latest run.

| split        | head-to-head | claude tool-use fails | total |
|--------------|--------------|------------------------|-------|
| codex_wins   | 10           | 7                      | 17    |
| claude_wins  | 7            | 0                      | 7     |

**Claude failed to write `answer.json` on 7 tasks** (graded from stdout instead, scored 0):

- 4 pairwise tasks: `mch-easy-013`, `mch-trivial-016`, `mch-trivial-017`, `nps-trivial-020`
- `pilot-peptide-multitarget-sequence-mono-active-011`
- `pilot-peptide-ranking-sequence-nps-small-001`
- `pilot-next-experiment-cross-family-003`

Most are "trivial/easy" tasks where claude should have scored 1.0 if it had committed an answer. The codex/claude gap on the easier buckets is partly a tool-use story, not a reasoning story.

Full task-by-task answers (gold / claude / codex) in [`discriminators.md`](discriminators.md).

## Recommended next steps

1. Investigate claude's "no `answer.json`" failures — likely a prompt-template issue.
2. Re-run the boundary-case analysis with the new scores: confirm whether the noisy-task cleanup actually tightened the signal where expected (multitarget, ranking).
3. Decide whether `hit_prediction` is worth keeping — both agents at chance suggests the binary in-vivo significance call may be irreducibly noisy.

## Artifacts

- `scores_by_task_type.png` — grouped bar plot of mean score per (task type, agent) with per-task dots.
- `scores.json` — per-task latest-run scores used to build the plot.
- `discriminators.md` — full list of clean discriminators with gold + each agent's submitted answer.
