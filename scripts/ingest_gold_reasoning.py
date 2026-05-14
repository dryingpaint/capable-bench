"""Inject analyst-authored `gold_reasoning` markdown into answer YAMLs for the
five tasks where we have grounded, source-citable rationale.

Grounding policy: each gold_reasoning string MUST contain at least two of:
  (a) An author-year citation (e.g., "Bednarek 2001", "Reinscheid 2005")
  (b) A repo source-path reference (e.g., "data/processed/invitro_assays.csv")
  (c) An explicit measurement claim (numeric EC50/IC50/Emax in nM or %)

Tasks that don't meet the bar are skipped with a warning. The script is
idempotent: running it twice produces the same YAML.

Run from repo root:
  uv run python scripts/ingest_gold_reasoning.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ANS = REPO / "data/answers"


class _BlockDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper, data):
    # Force `|` block-scalar style for multi-line strings so the dashboard's
    # lightweight YAML parser reads them correctly.
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_BlockDumper.add_representer(str, _str_representer)

# --- Grounding regexes ---
AUTHOR_YEAR = re.compile(r"\b[A-Z][a-z]+\s+\d{4}\b")           # "Bednarek 2001"
SOURCE_PATH = re.compile(r"`?data/(?:processed|validators)/[\w./-]+`?")
MEASUREMENT = re.compile(r"\b\d+(?:\.\d+)?\s*(?:nM|µM|%)\b", re.IGNORECASE)


def check_grounding(text: str) -> list[str]:
    signals = []
    if AUTHOR_YEAR.search(text):
        signals.append("author-year citation")
    if SOURCE_PATH.search(text):
        signals.append("source-path reference")
    if MEASUREMENT.search(text):
        signals.append("measurement claim")
    return signals


# --- Gold reasoning strings ---
# Each string is a markdown block. Citations and measurements are required;
# see check_grounding() above.

GOLD_REASONING: dict[str, str] = {

    # ============================================================
    "pilot-peptide-pairwise-sequence-mch-easy-011": """\
**Gold: `PEP-77A315C29A`** — observed potency ratio 30.67× over `PEP-021CF7B0A5`.

## Held-out measurements (from `data/processed/invitro_assays.csv`)

**PEP-77A315C29A** = `[Ala17]hMCH` (Bednarek 2001 Table 1, alanine scan on full hMCH):

| receptor | assay | EC50 / IC50 (nM) | Emax (%) |
|---|---|---:|---:|
| MCHR1 | binding | **0.15** | — |
| MCHR2 | binding | 3.5 | — |
| MCHR1 | Ca²⁺ | 17 | 104 |
| MCHR2 | Ca²⁺ | 54 | 95 |

Best EC50/IC50 = **0.15 nM**; full agonist (Emax 95–104%).

**PEP-021CF7B0A5** = `MCH core19 D-Cys7` (Bednarek 2001 Table 5, D-aa scan on "compound 19"):

| receptor | assay | EC50 / IC50 (nM) | Emax (%) |
|---|---|---:|---:|
| MCHR1 | binding | **4.6** | — |
| MCHR2 | binding | 590 | — |
| MCHR1 | Ca²⁺ | 910 | 67 |
| MCHR2 | Ca²⁺ | 750 | 81 |

Best EC50/IC50 = **4.6 nM**; partial agonist on Ca²⁺ (Emax 67% MCHR1, 81% MCHR2).

The label is overdetermined: 30× in MCHR1 binding, ~50× in Ca²⁺ MCHR1, ~170× in MCHR2 binding, plus a 37-point Emax drop. All four measurements agree.

## Mechanistic rationale

**HIGH-confidence (Bednarek 2001):**

1. *Bednarek 2001 Table 1 alanine scan on hMCH*: Trp17 (C-terminal aromatic after the cyclic core) tolerates Ala substitution well. The cyclic-core residues Met–Leu–Gly–Arg–Val–Tyr–Arg–Pro between the two Cys are individually critical; flanking residues including Trp17 are more tolerant. `[Ala17]hMCH` retains near-native potency.
2. *Bednarek 2001 Table 5 D-amino-acid scan on compound 19*: D-substitutions at Cys7 or Cys16 drop potency by 1–3 orders of magnitude because they prevent native disulfide formation. The peptide effectively linearizes.
3. *MCH active conformation requires the Cys7–Cys16 disulfide.* Established across the MCH literature (Audinot, Macdonald, the Bednarek series itself).

## Caveat — different parent backbones

The two peptides come from different Bednarek series: `[Ala17]hMCH` is full human MCH (19 residues, `DFDMLRCMLGRVYRPCWQV`); `MCH core19 D-Cys7` is on the truncated "compound 19" core (≈MCH 5–17). The 30× observed ratio mixes backbone-gap and modification effects; the agent has no way to detect this from the `modification` strings alone.
""",

    # ============================================================
    "pilot-peptide-pairwise-sequence-nps-easy-011": """\
**Gold: `PEP-17D19C9AD5`** — observed potency ratio 60.1× over `PEP-C9FE4F8ED3`.

## Held-out measurements (from `data/processed/invitro_assays.csv`)

**PEP-17D19C9AD5** = NPS-(1–17)-NH₂ truncation (compound `NPSv26.2`, 6 records, plates Z' > 0.5):

| receptor | assay | EC50 (nM) | Emax (%) |
|---|---|---:|---:|
| hNPSR1 Asn107 | Ca²⁺ | **1.0** | 96 |
| hNPSR1 Ile107 | IP-1 | 1.4 | 102 |
| hNPSR1 Ile107 | Ca²⁺ | 7.8 | 90 |
| hNPSR1 Asn107 | IP-1 | 15.9 | 100 |
| hNPSR1 Asn107 | cAMP | 44.6 | 106 |
| hNPSR1 Asn107 | β-arrestin | 57.5 | 97 |

Best EC50 = **1.0 nM**; full agonist (Emax 90–106%) on every assay × receptor combination.

**PEP-C9FE4F8ED3** = combo modification (compound `NPSv14`, 3 records):

| receptor | assay | EC50 (nM) | Emax (%) |
|---|---|---:|---:|
| hNPSR1 Ile107 | Ca²⁺ | **60.0** | 41 |
| hNPSR1 Ile107 | IP-1 | 75.1 | 74 |
| hNPSR1 Asn107 | β-arrestin | 5000 (capped) | 5 |

Best EC50 = **60.0 nM**; partial agonist on Ca²⁺ (41%) and IP-1 (74%); functionally inactive on β-arrestin.

The label is overdetermined by three independent signals: 60× best-EC50 gap, ~40-point Emax gap, and β-arrestin functional loss.

## Mechanistic rationale

**HIGH-confidence (NPS / GPCR-peptide SAR):**

1. The N-terminal `SF…` motif of NPS is the receptor-recognition core (Reinscheid 2005, Roth 2006). Modification at position 1 typically costs ≥10× in potency.
2. `PEP-17D19C9AD5 = NPS-(1–17)-NH₂` truncates the dispensable C-terminal `AKS` (positions 18–20). The active N-terminus is intact and the amide cap blocks C-terminal degradation. Standard medchem move that boosts in vitro potency.
3. `PEP-C9FE4F8ED3` modifies position 1 with D-Ser, inverting N-terminal chirality. This breaks helix nucleation NPS uses for receptor engagement — predicted ≥10× potency loss.

**MEDIUM-confidence:**

4. β-homoarginine at position 3 adds a CH₂ to the backbone, perturbing local geometry. Tolerated as a stability mod, rarely improves potency.
5. Internal C16-palmitoyl at K12 (versus C-terminal lipidation) can sequester the peptide in membranes or sterically obstruct binding. Consistent with the Ca²⁺ Emax drop to 41% (altered binding pose that engages the receptor incompletely).

**SPECULATIVE:** β-arrestin functional loss in the combo variant suggests a biased partial-agonist phenotype — possibly because the altered pose engages G-protein machinery suboptimally and fails to recruit β-arrestin. Cannot be confirmed without single-modification controls.
""",

    # ============================================================
    "cb-mch-disulfide-vs-aromatic-001": """\
**Gold: `PEP-77A315C29A`** (the native hMCH 19-mer) — observed potency ratio 30.67× at MCHR1 binding.

## Held-out measurements (from `data/processed/invitro_assays.csv`)

| compound | best EC50 / IC50 at MCHR1 (nM) | source |
|---|---:|---|
| **PEP-77A315C29A** (`DFDMLRCMLGRVYRPCAQV`, native hMCH) | **0.15** | Bednarek 2001 Table 1 (alanine scan, full hMCH) |
| PEP-021CF7B0A5 (`Ac-Arg-D-Cys-Met-Leu-Gly-Arg-Val-Tyr-Arg-Pro-Cys-Trp-NH2`, compound 19 scaffold) | 4.6 | Bednarek 2001 Table 5 (D-aa scan on compound 19) |

## Why the native 19-mer wins

The Bednarek 2001 "compound 19" scaffold is a truncated cyclic MCH(6–17) analog with three apparent optimizations:
- N-terminal Ac- cap and C-terminal -NH₂ cap (reduce charge-desolvation cost),
- C-terminal Trp (adds an aromatic contact),
- D-Cys7 (proposed to optimize disulfide ring geometry),
- removed N-terminal `DFDML` (claimed non-pharmacophoric tail).

Empirically (`data/processed/invitro_assays.csv`):
- D-Cys7 *disrupts* the Cys7–Cys16 disulfide rather than optimizing it. Without the native bridge, the peptide partly linearizes and loses the cyclic active conformation. Bednarek 2001 Table 5 shows D-Cys scans cost 1–3 orders of magnitude.
- The `DFDML` N-terminal tail is *not* non-pharmacophoric — it participates in MCHR1 receptor contacts in the full peptide. Truncation removes those contacts.
- The native C-terminal `Cys-Ala-Gln-Val` makes a Gln18 H-bond and adjacent receptor contacts; the truncated `Cys-Trp-NH₂` shape loses them, and the added Trp aromatic doesn't recover the loss.

Net effect: ~30× weaker, consistent with the measurement.

## Trap design

This task was deliberately constructed to test whether agents apply textbook lead-optimization SAR (caps + D-aa + aromatic + truncation = better) by analogy, without checking against the actual data. Both Claude and Codex fall for it; the published measurements contradict the textbook intuition.
""",

    # ============================================================
    "cb-nps-polymorphism-001": """\
**Gold: `NPSv18.9`** — computed Ile107 preference 276.7×, the largest in the 14-compound panel.

## Derivation

Gold is the geometric mean of `hNPSR1-Asn107 EC50` divided by the geometric mean of `hNPSR1-Ile107 EC50`, aggregated across replicates per (compound, receptor) in `data/processed/invitro_assays.csv`. Validator: `data/validators/cb-nps-polymorphism-001.py`.

## Top of the panel by Ile107 preference

| compound | Asn107 EC50 (nM) | Ile107 EC50 (nM) | preference | n(A) | n(I) | published? |
|---|---:|---:|---:|---:|---:|---|
| **NPSv18.9** | 260.8 | 0.94 | **277×** | 5 | 1 | no |
| rNPS(1–10) | 2090 | 18.8 | 111× | 1 | 1 | yes (Reinscheid lab) |
| hNPS(1–10) | 776 | 7.4 | 105× | 1 | 1 | yes |
| NPSv16.13 | 1026 | 11.1 | 93× | 17 | 4 | no |
| NPSv31.7 | 423 | 5.2 | 81× | 4 | 2 | no |
| NPSv10.16 | 1243 | 18.0 | 69× | 3 | 2 | no |
| NPSv5.4 | 52.3 | 0.89 | 59× | 8 | 2 | no |
| NPS (native) | 25.8 | 3.8 | 6.8× | 167 | 77 | yes (Reinscheid 2002) |

Gap from `NPSv18.9` to the #2 candidate `rNPS(1–10)` is 2.5×.

## Why NPSv18.9 wins

`NPSv18.9` is the native human NPS sequence with an unusually heavy lipidation linker at K11: gamma-Glu + two AEEA spacers + a C20 dicarboxylic acid (~30-atom total chain). The extended hydrophobic stalk on the Asn107 variant appears to clash with side-chain bulk at position 107 in the receptor, but the smaller Ile107 side chain accommodates it — producing the largest Ile107 preference in the panel.

The two published N-terminal truncations `hNPS(1–10)` and `rNPS(1–10)` rank #2 and #3 at 111× and 105×, and would be the answers a retrieval-only agent gives ("NPS truncation literature → Ile107 preference"). The actual winner is an unpublished internal modification with a 2.5× larger preference — the trap design is "looks-comprehensively-optimized" candidates (multiple D-aa + standard palmitoyl) versus a single unusual linker.

Random-guess baseline: 1/14 = 7.14%.
""",

    # ============================================================
    "pilot-hit-prediction-002": """\
**Gold: `inactive`.** Across all 8 NXNv10.15 (dose × window) tasks, *every* 50 µg condition is `inactive` in the held-out in-vivo significance call (`data/processed/invivo_olden_analysis_significance.csv`).

## Why the gold is correct

The visible row carries two coherent signals for *poor in-vivo translation*:

### Modification chemistry — no PK enhancement

- **AEEA-AEEA** (`NXNv10.1 + AEEA-AEEA linker`) is a flexible PEG-like spacer (8-amino-3,6-dioxaoctanoic acid). It adds **zero** PK benefit — no membrane stickiness, no protease resistance, no half-life extension. It is a connector, not a lipidation.
- **No C-terminal palmitate, no cholesterol, no D-amino acids, no non-natural backbone modifications** (Nle, hArg, aMeSer).
- This is, effectively, a naked NPS-like peptide with a fluffy spacer.

### Per-assay pharmacology — Gq-biased

Measured EC50 / Emax at the four readouts (Ca²⁺ 4.8 nM 113%, IP-1 5.5 nM 94%, β-arrestin 596 nM 114%, cAMP 260 nM 64%) — distal/proximal EC50 spread = 596 / 4.8 = **124×**.

This is a textbook Gq-bias signature (Kenakin 2007, Rajagopal 2010): compounds with this profile produce transient proximal signals but fail to sustain receptor occupancy through arrestin internalization, and typically don't translate to sustained in-vivo behavioral effects at sub-saturating doses.

### Dataset-internal control

Compound siblings `NXNv10.16` and `NXNv12.10` in the same dataset carry actual PK chemistry (C16 palmitoyl + D-aa backbone stabilizers) and are in-vivo active at multiple (dose × window) conditions. NXNv10.15 lacks both.

## Combined call

At 50 µg, 1-h window, a naked Gq-biased peptide with low-nM proximal potency but no PK chemistry doesn't reach the in-vivo significance threshold. Both Claude and Codex predicted `active` by weighting low Ca²⁺/IP-1 EC50 above the PK liability and the bias signature — see `docs/findings/hit-prediction-002-aeea-as-pk-booster/README.md` for the agent traces.
""",
}


def main() -> None:
    skipped = []
    written = []

    for task_id, reasoning in GOLD_REASONING.items():
        yaml_path = ANS / f"{task_id}.yaml"
        if not yaml_path.exists():
            print(f"  SKIP  {task_id}: answer YAML not found ({yaml_path})", file=sys.stderr)
            skipped.append(task_id)
            continue

        signals = check_grounding(reasoning)
        if len(signals) < 2:
            print(
                f"  SKIP  {task_id}: grounding too weak (found: {signals})",
                file=sys.stderr,
            )
            skipped.append(task_id)
            continue

        gold = yaml.safe_load(open(yaml_path))
        gold["gold_reasoning"] = reasoning
        # Write back preserving order: keep `id` first, then known fields, then reasoning at end
        with open(yaml_path, "w") as fh:
            yaml.dump(gold, fh, Dumper=_BlockDumper, sort_keys=False, allow_unicode=True, width=120)
        print(f"  OK    {task_id}: ingested ({', '.join(signals)})")
        written.append(task_id)

    print(f"\nIngested gold_reasoning into {len(written)} answer YAMLs.")
    if skipped:
        print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
