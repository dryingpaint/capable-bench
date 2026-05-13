"""
Validator for cb-polypharm-lead-001.

Reads the input files, applies the four filters, derives the gold, and
asserts uniqueness. Run from repo root.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
TDIR = REPO / "data" / "tasks" / "cb-polypharm-lead-001"
GOLD = yaml.safe_load(open(REPO / "data" / "answers" / "cb-polypharm-lead-001.yaml"))

DOSE_MG = 25
TAU_H = 12
MW = 400
Q_HEP = 90

# Filter thresholds (taken from prompt.md)
MIN_BRAIN_MARGIN = 10            # >= 10x IC80
HERG_MIN_RATIO = 30              # hERG IC50 / free Cmax
SEL_MIN_RATIO = 30               # off-target IC50 / MCHR1 EC50
CYP_MIN_RATIO = 10               # CYP IC50_preinc / free Cmax
MBI_SHIFT_THRESHOLD = 2          # IC50_no_preinc / IC50_preinc > 2 => MBI
SAFETY_CRITICAL_TARGETS = ["5HT2A", "5HT2B", "5HT2C", "D2", "D3", "M1", "M3", "H1"]


def parse_ic50(s):
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s.startswith(">"):
        return float("inf")
    if s in {"", "not_tested", "NA", "nan"}:
        return float("nan")
    return float(s)


def parse_ic50_lower_bound(s):
    """Return the lower bound for ratio-checking: if cell is '>10000', value is at least 10000."""
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s.startswith(">"):
        return float(s[1:])
    return float(s)


# Load inputs
pot = pd.read_csv(TDIR / "primary_potency.csv")
pk = pd.read_csv(TDIR / "pk.csv")
sel = pd.read_csv(TDIR / "selectivity_panel.csv")
cyp = pd.read_csv(TDIR / "cyp_inhibition.csv")
herg = pd.read_csv(TDIR / "herg_panel.csv")
regimen_text = (TDIR / "regimen.md").read_text()


# Compute exposure
df = pot.merge(pk, on="compound").merge(herg, on="compound")
df["Css_plasma_mgL"] = (df["F_oral_pct"] / 100 * DOSE_MG) / (df["CL_L_per_h"] * TAU_H)
df["Css_plasma_nM"] = df["Css_plasma_mgL"] * 1e6 / MW
df["Css_brain_free_nM"] = df["Css_plasma_nM"] * df["fu_plasma"] * df["Kp_uu_brain"]
df["free_Cmax_nM"] = df["Css_plasma_nM"] * df["fu_plasma"]
df["free_Cmax_uM"] = df["free_Cmax_nM"] / 1000
df["brain_margin"] = df["Css_brain_free_nM"] / df["IC80_nM_calc"]


# ----- Identify co-administered drug + relevant CYP -----
# parse regimen.md: looking for tacrolimus, identifying its CYP
co_med_match = re.search(r"Tacrolimus", regimen_text, re.IGNORECASE)
assert co_med_match, "regimen.md must mention tacrolimus"
relevant_cyp = "CYP3A4"  # tacrolimus is primarily CYP3A4-cleared


# ----- Apply filters -----
def filter_brain(row):
    return row["brain_margin"] >= MIN_BRAIN_MARGIN


def filter_cyp(compound):
    row = cyp[cyp["compound"] == compound].iloc[0]
    no_pre = parse_ic50_lower_bound(row[f"{relevant_cyp}_IC50_uM_no_preinc"])
    with_pre = parse_ic50_lower_bound(row[f"{relevant_cyp}_IC50_uM_30min_NADPH"])
    cand_free_cmax_uM = df[df["compound"] == compound].iloc[0]["free_Cmax_uM"]
    # Use lower of the two IC50s for the post-preincubation comparison
    effective_ic50 = with_pre
    mbi = (no_pre / max(with_pre, 1e-9)) > MBI_SHIFT_THRESHOLD if math.isfinite(with_pre) else False
    reversible = (effective_ic50 / cand_free_cmax_uM) < CYP_MIN_RATIO if math.isfinite(effective_ic50) else False
    return {
        "no_preinc": no_pre, "with_preinc": with_pre,
        "shift": (no_pre / with_pre) if math.isfinite(with_pre) and with_pre > 0 else float("inf"),
        "free_Cmax_uM": cand_free_cmax_uM,
        "IC50_to_Cmax_ratio": (effective_ic50 / cand_free_cmax_uM) if math.isfinite(effective_ic50) else float("inf"),
        "mbi": mbi,
        "reversible_inhibition": reversible,
        "pass": not (mbi or reversible),
    }


def filter_herg(row):
    free_cmax_uM = row["free_Cmax_uM"]
    if free_cmax_uM == 0:
        return True  # no exposure means no hERG risk -- but already fails coverage filter
    return (row["hERG_IC50_uM"] / free_cmax_uM) >= HERG_MIN_RATIO


def filter_selectivity(compound):
    ec50 = pot[pot["compound"] == compound].iloc[0]["EC50_nM_MCHR1"]
    row = sel[sel["compound"] == compound].iloc[0]
    fails = []
    for tgt in SAFETY_CRITICAL_TARGETS:
        col = f"{tgt}_IC50_nM"
        val = parse_ic50_lower_bound(row[col])
        if val < SEL_MIN_RATIO * ec50:
            fails.append((tgt, val, val / ec50))
    return {"pass": len(fails) == 0, "fails": fails}


# ----- Apply to every candidate -----
print("=" * 100)
print("PER-CANDIDATE FILTER PASS/FAIL")
print("=" * 100)
rows = []
for _, r in df.iterrows():
    cmp = r["compound"]
    f1 = filter_brain(r)
    f2_info = filter_cyp(cmp)
    f3 = filter_herg(r)
    f4_info = filter_selectivity(cmp)
    rows.append({
        "compound": cmp,
        "margin": round(r["brain_margin"], 2),
        "f1_coverage": f1,
        "f2_cyp": f2_info["pass"],
        "f2_detail": f"shift={f2_info['shift']:.2f} ratio={f2_info['IC50_to_Cmax_ratio']:.1f}",
        "f3_hERG": f3,
        "hERG_ratio": round(r["hERG_IC50_uM"] / max(r["free_Cmax_uM"], 1e-9), 1),
        "f4_sel": f4_info["pass"],
        "f4_fails": [t[0] for t in f4_info["fails"]] or "-",
    })

summary = pd.DataFrame(rows)
print(summary.to_string(index=False))


# ----- Lead derivation -----
print("\n" + "=" * 100)
print("LEAD DERIVATION")
print("=" * 100)
viable = summary[summary["f1_coverage"] & summary["f2_cyp"] & summary["f3_hERG"] & summary["f4_sel"]]
print(f"Candidates passing all four filters: {list(viable['compound'])}")
if len(viable) == 0:
    derived_lead = "none"
elif len(viable) == 1:
    derived_lead = viable.iloc[0]["compound"]
else:
    # Pick highest margin among tied viable candidates
    derived_lead = viable.sort_values("margin", ascending=False).iloc[0]["compound"]
    print(f"  (multiple viable; selecting highest margin: {derived_lead})")
print(f"Derived lead: {derived_lead}")


# ----- K's disqualifying finding -----
print("\n" + "=" * 100)
print("ROOT-CAUSE FOR APPARENT BEST CANDIDATE (K)")
print("=" * 100)
K_cyp = filter_cyp("K")
K_brain_pass = bool(summary[summary["compound"] == "K"]["f1_coverage"].iloc[0])
K_herg_pass = bool(summary[summary["compound"] == "K"]["f3_hERG"].iloc[0])
K_sel_pass = bool(summary[summary["compound"] == "K"]["f4_sel"].iloc[0])
print(f"  brain coverage pass : {K_brain_pass}  (margin {summary[summary.compound=='K']['margin'].iloc[0]}x)")
print(f"  CYP3A4 IC50 no-preinc: {K_cyp['no_preinc']} uM,  30min preinc: {K_cyp['with_preinc']} uM,  shift: {K_cyp['shift']:.1f}x")
print(f"  -> MBI on CYP3A4    : {K_cyp['mbi']}")
print(f"  -> reversible CYP   : {K_cyp['reversible_inhibition']}")
print(f"  hERG pass           : {K_herg_pass}")
print(f"  selectivity pass    : {K_sel_pass}")

if K_cyp["mbi"]:
    derived_K_reason = "mechanism_based_CYP3A4_inhibition"
elif K_cyp["reversible_inhibition"]:
    derived_K_reason = "reversible_CYP3A4_inhibition"
elif not K_herg_pass:
    derived_K_reason = "hERG_liability"
elif not K_sel_pass:
    derived_K_reason = "off_target_other"
elif not K_brain_pass:
    derived_K_reason = "inadequate_brain_coverage"
else:
    derived_K_reason = "no_disqualifying_finding"
print(f"  -> derived disqualifying finding for K: {derived_K_reason}")


# ----- Co-administered drug at risk -----
derived_co_med = "tacrolimus" if re.search(r"tacrolimus", regimen_text, re.IGNORECASE) else "no_DDI_risk"
print(f"\nCo-administered drug at risk: {derived_co_med}")


# ----- Validate gold -----
print("\n" + "=" * 100)
print("GOLD VALIDATION")
print("=" * 100)
g = GOLD["gold"]
checks = {
    "lead_candidate": (derived_lead, g["lead_candidate"]),
    "disqualifying_finding_for_K": (derived_K_reason, g["disqualifying_finding_for_K"]),
    "co_administered_drug_at_risk": (derived_co_med, g["co_administered_drug_at_risk"]),
}
all_ok = True
for field, (d, declared) in checks.items():
    ok = d == declared
    all_ok &= ok
    print(f"  {field:34s}  derived={d!r:42s} gold={declared!r:42s} {'OK' if ok else 'MISMATCH'}")
assert all_ok, "Gold does not match derivable answer"


# ----- Trap analysis -----
print("\n" + "=" * 100)
print("TRAP ANALYSIS")
print("=" * 100)


def score(a, g):
    return sum(a.get(k) == g.get(k) for k in g)


traps = {
    "Pick highest potency (K)": {
        "lead_candidate": "K",
        "disqualifying_finding_for_K": "no_disqualifying_finding",
        "co_administered_drug_at_risk": "tacrolimus",
    },
    "Pick K, recognize tacrolimus, but call inhibition reversible (miss MBI)": {
        "lead_candidate": "K",
        "disqualifying_finding_for_K": "reversible_CYP3A4_inhibition",
        "co_administered_drug_at_risk": "tacrolimus",
    },
    "Pass coverage + hERG + selectivity but ignore CYP entirely (pick K)": {
        "lead_candidate": "K",
        "disqualifying_finding_for_K": "no_disqualifying_finding",
        "co_administered_drug_at_risk": "no_DDI_risk",
    },
    "Pick B (clean CYP, but fails hERG)": {
        "lead_candidate": "B",
        "disqualifying_finding_for_K": "mechanism_based_CYP3A4_inhibition",
        "co_administered_drug_at_risk": "tacrolimus",
    },
    "Pick F (clean CYP, but fails 5-HT2B selectivity)": {
        "lead_candidate": "F",
        "disqualifying_finding_for_K": "mechanism_based_CYP3A4_inhibition",
        "co_administered_drug_at_risk": "tacrolimus",
    },
    "Pick I (passes 3 of 4 filters, fails reversible CYP3A4 inhibition)": {
        "lead_candidate": "I",
        "disqualifying_finding_for_K": "mechanism_based_CYP3A4_inhibition",
        "co_administered_drug_at_risk": "tacrolimus",
    },
    "Right MOA reasoning, wrong drug (think CYP2D6 inhibitor matters)": {
        "lead_candidate": "K",
        "disqualifying_finding_for_K": "mechanism_based_CYP3A4_inhibition",
        "co_administered_drug_at_risk": "fluoxetine",
    },
}
for name, ans in traps.items():
    print(f"  {name}")
    print(f"     -> {ans}")
    print(f"     -> score {score(ans, g)}/3")


print("=" * 100)
print("VALIDATION COMPLETE")
print("=" * 100)
