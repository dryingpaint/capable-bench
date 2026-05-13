# cb-nps-polymorphism-001

**One-liner:** Predict-from-sequence task on intra-receptor variant selectivity (NPSR1 Asn107 vs Ile107). Both frontier agents fail honestly on Modal at 1/14 random baseline. Both converge on the same wrong compound (`NPSv5.4`) — neither picks the literature-truncation trap I designed, instead both fall for a new "looks-comprehensively-optimized" trap (multiple D-amino acids + standard palmitoyl lipidation > a single unusual lipidation linker).

**Date:** 2026-05-13
**Task type:** `program_lead_selection` (sequence_to_ranking variant — single exact-match field)
**Real difficulty:** hard — both honest frontier attempts score 0/1.
**Key property:** task uses only repo data (no fabrication). Gold is computed from `data/processed/invitro_assays.csv` aggregating ~25 replicate EC50 measurements across the 14 candidate compounds at both hNPSR1-Asn107 and hNPSR1-Ile107 variants.

## The task

The agent receives `analogs.csv` listing 14 peptide compound IDs with their sequence/modification descriptions. No measured potencies for any compound. The prompt asks which compound has the largest preference for hNPSR1-Ile107 over hNPSR1-Asn107, defined as the ratio EC50(Asn107) / EC50(Ile107). Random-guess baseline: 1/14 = 7.14%.

The candidate panel contains:

- 7 internal NPS modifications (NPSv5.4, NPSv10.16, NPSv16.13, NPSv21.9, NPSv31.7, NPSv2-proKKv1, NPSv18.9)
- 2 literature truncations (hNPS(1-10), rNPS(1-10)) — the trap I designed in
- 1 native human NPS (variant-neutral baseline)
- 2 wrong-direction decoys (NPSv18.16, NPSv18.26 — these prefer Asn107)
- 1 inactive decoy (NPSv8 — full D-amino acid retro version)
- 1 mid-table filler (NPSv34.14)

**Gold answer:** `NPSv18.9` — native human NPS sequence with an unusually heavy lipidation linker at K11 (gamma-Glu + two AEEA spacers + C20 diacid; ~30-atom total chain). Measured 277× Ile107 preference.

**Intended trap:** `hNPS(1-10)` and `rNPS(1-10)`, the published N-terminal truncations. They rank #2 and #3 in the panel at 111× and 105× preference. An agent that retrieves "NPS truncation literature → prefers Ile107" would pick one of these.

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

| Executor | Agent | Predicted | Score | What it did |
|---|---|---|---|---|
| Modal | codex (gpt-5-codex) | `NPSv5.4` | **0/1** | 8 commands. Read files, computed native NPS sequence positioning, made guess. |
| Modal | claude (sonnet-4-0) | `NPSv5.4` | **0/1** | 31 actions. 4 WebSearches on NPS pharmacology, lipidation chemistry, and the Asn107Ile polymorphism specifically. |

Both agents converged on the same wrong answer despite different reasoning paths. Both stayed in the sandbox — zero reads of `/data/answers/` or `/data/validators/`.

## Codex result (Modal)

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`codex_modal_stdout.txt`](codex_modal_stdout.txt)

Codex listed files, read prompt + analogs.csv, ran a python snippet to index the native NPS sequence positions, then committed. Terse reasoning chain. The shell sequence:

```
pwd && rg --files && sed -n '1,200p' analogs.csv
python - <<'PY' import csv; ... fieldnames + row count
sed -n prompt.md / task.yaml
find .. -maxdepth 3 -type f
python - <<'PY' native='SFRNGVGTGMKKTSFQRAKS' position indexing
python -m json.tool answer.json
```

No external retrieval. Picked the compound based on visible modifications without specific variant-selectivity SAR.

## Claude result (Modal)

**Predicted:** `NPSv5.4` — wrong.
**Trace:** [`claude_modal_stdout.txt`](claude_modal_stdout.txt)

31 actions total. Four diagnostic WebSearches:

1. `neuropeptide S NPSR1 Asn107Ile polymorphism structure activity relationship SAR`
2. `neuropeptide S peptide modifications SAR lipidation D-amino acids structure activity`
3. `neuropeptide S NPSR1 N-terminal modifications C-terminal modifications selectivity`
4. `"neuropeptide S" palmitic acid lipidation "gamma-glutamic acid" modifications`

Search #2 and #4 are the relevant ones: claude searched for the *combination* of D-amino acid + palmitoyl lipidation, which exactly matches `NPSv5.4`'s modification profile (`[D-Ser]-FRNGVGTGM-[D-Lys]-K[(γ-E)-(Pal)]-[D-Thr]-NH2`). It found Asahi 2003 (D-Leu15 hardened OXB) and analogous NPS work, decided that "multiple D-amino acids + lipidation = the published optimization template," picked `NPSv5.4`.

The trap claude actually fell for is *not* my designed literature-truncation trap. It's a deeper one: "the canonical published peptide-optimization template (D-aa + palmitoyl) means more selective." That template is well-documented for stability/half-life, less so for variant selectivity, but claude conflates the two.

## Failure mode taxonomy

1. **Modification-count heuristic (both agents).** `NPSv5.4` carries 4 visible modifications (D-Ser, D-Lys, D-Thr, palmitoyl) versus `NPSv18.9`'s single visible feature (one heavy lipidation chain). Both agents reward modification count over modification chemistry. The actual selectivity-driving feature in `NPSv18.9` — the unusually long C20-diacid + dual-AEEA linker that creates a binding-pocket footprint asymmetry between Asn107 and Ile107 — is invisible to a "count the substitutions" reading.

2. **Canonical-template mis-application (claude specifically).** Claude searched for and found the well-published "D-amino acid + palmitoyl" template (Asahi 2003 hardened OXB, similar GLP-1 analog work) and applied it to the NPS variant question. That template optimizes proteolytic stability and half-life, *not* variant selectivity. Claude conflated the two via template-matching rather than reasoning about which feature is mechanistically relevant to a polymorphism that changes a single residue in the binding pocket.

3. **Literature-truncation trap was NOT triggered.** The two literature compounds I expected to fool the agents (hNPS(1-10), rNPS(1-10)) were ignored. Both rank in the top 3 and would have been the "obvious published" answer — but neither agent retrieved the truncation SAR. This is a different failure: the agents found *some* published SAR but not the right one for this specific question.

4. **Convergent wrong answer.** Both codex and claude land on `NPSv5.4` via independent reasoning paths. This makes the wrong answer especially diagnostic — it's not a one-model quirk but a shared bias.

## What this means for the benchmark

- **Keep this task.** Adds a second sandboxed prediction task with independent measurement of frontier reasoning. Convergent failure across both agents is a strong negative-direction signal.

- **The trap I designed in is not the trap that fired.** Worth noting: when authoring tasks with a hypothesized trap, run the agents *before* writing the README to find the trap that actually triggers. The literature-truncation trap was theoretical; the modification-count trap is what fires in practice. Both are real failure modes but only one is testable in this panel as constructed.

- **Modification chemistry vs modification count.** This task surfaces a second deeper failure: agents treat number-of-visible-modifications as a quality proxy. A complementary task that isolates this — same panel with reordered descriptions, or sequences shown without the modification descriptions — would let us tell whether agents are reading the modification chemistry at all or just counting tokens.

- **The literature retrieval is real but mis-routed.** Claude's WebSearch for `palmitic acid lipidation "gamma-glutamic acid" modifications` is the exact correct query for a typical peptide-optimization task. But this isn't a typical peptide-optimization task — it's a variant-discriminating one. Future tasks should probe whether agents can *distinguish task-relevant retrieval queries* from canonical ones.

## Operational findings (data infrastructure)

- **`data/tasks/*` and `data/answers/*` are git-ignored.** The cb-* task directories and answer YAMLs disappear between sessions (presumably swept by `capablebench curate-pilot --clean` or a similar cleanup). After the first Modal run, the grade came back null because the gold YAML was missing. I restored it from preserved snapshots, regraded, confirmed both agents 0/1. Recommendation: either add `!data/tasks/cb-*` and `!data/answers/cb-*` exceptions to `.gitignore`, or move cb-* tasks to a tracked subdirectory. The current state risks irreproducibility.

- **Modal sandbox confirmed correct** for the second time. Both agents stayed within their run_dir + internet. Zero filesystem escape attempts.

## Reproducing

```bash
# Sandboxed runs via Modal:
uv run capablebench run cb-nps-polymorphism-001 \
  --remote modal \
  --agent-command 'codex exec --json --skip-git-repo-check --cd {task_dir} --dangerously-bypass-approvals-and-sandbox "$(cat {task_dir}/prompt.md)"' \
  --timeout-seconds 900

ANTHROPIC_API_KEY=… uv run capablebench run cb-nps-polymorphism-001 \
  --remote modal \
  --agent-command 'claude -p --output-format stream-json --verbose --permission-mode bypassPermissions --model claude-sonnet-4-20250514 "$(cat {task_dir}/prompt.md)"' \
  --timeout-seconds 900

# Validate the gold derives from raw repo data:
uv run python data/validators/cb-nps-polymorphism-001.py
```

## Source run directories

- Modal codex: `runs/cb-nps-polymorphism-001/20260513-083756-ba6d62b3-modal/`
- Modal claude (sonnet-4-0): `runs/cb-nps-polymorphism-001/20260513-083816-d71b01bb-modal/`
