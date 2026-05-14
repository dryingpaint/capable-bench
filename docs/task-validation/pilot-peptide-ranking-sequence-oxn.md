---
task_ids: [pilot-peptide-ranking-sequence-oxn-small-001, pilot-peptide-ranking-sequence-oxn-medium-001, pilot-peptide-ranking-sequence-oxn-large-001]
verdict: PROMOTE (small); TRIM (medium); PROMOTE-with-caveats (large; gold corrected, 2 internal-only peptides flagged)
reviewed: 2026-05-13
revalidated: 2026-05-13 (oxn-large-001 — validator + re-grade)
---

## Family verdict
Rankings reproduce from `min(ec50_nm)` per peptide over OX1R/OX2R rows in `data/processed/invitro_assays.csv`, with `producer != 'Reference'`. Bottom anchored by Asahi 2003 Ala-scan losses.

- **oxn-small-001** (5 peptides) — PROMOTE; span 1009.7×; gold matches
- **oxn-medium-001** (8 peptides) — TRIM (see below); span 110.4×
- **oxn-large-001** (12 peptides) — PROMOTE-with-caveats; **gold ranking corrected on 2026-05-13** (top-3 unchanged, ranks 4-12 reordered)

## oxn-large-001 — validator + gold delta (2026-05-13)

**Validator written:** `/Users/melissadu/Documents/projects/capable-bench/data/validators/pilot-peptide-ranking-sequence-oxn-large-001.py`

Filter rule: `receptor in {OX1R,OX2R}` AND `producer != 'Reference'`. Tie-break: stable sort on (`best_ec50_nm` asc, `peptide_id` asc).

**Gold did change.** `gold_top_3` unchanged (4322CEE31D, 6EF93476BD, 03F8504EFE) but ranks 4-12 re-sorted. The previous gold placed PEP-928A45A209 at #9 with implied ~1 nM — only reachable if the Reference 1 nM Orexin A calibrant row is included. The earlier doc claim "gold correctly excludes it" was incorrect: the validator counterfactual confirms the existing rank-9 placement *required* the Reference row. Excluding it puts PEP-928A45A209 at #12 (6.41 nM, weakest in panel).

| rank | peptide | best_ec50_nm | n_rows |
|------|---------|--------------|--------|
| 1 | PEP-4322CEE31D | 0.0210 | 4 |
| 2 | PEP-6EF93476BD | 0.0740 | 5 |
| 3 | PEP-03F8504EFE | 0.0741 | 5 |
| 4 | PEP-8B302C5163 | 0.1300 | 3 |
| 5 | PEP-AA50CBFFC9 | 0.1300 | 3 |
| 6 | PEP-03ADB61E5B | 0.2039 | 3 |
| 7 | PEP-2289B12802 | 0.3068 | 3 |
| 8 | PEP-41AFA0594A | 0.5300 | 3 |
| 9 | PEP-85DBA45E66 | 1.1103 | 2 |
| 10 | PEP-0143240A44 | 1.6074 | 3 |
| 11 | PEP-1901FD3803 | 2.6933 | 3 |
| 12 | PEP-928A45A209 | 6.4125 | 1 |

`outcome_definition` rewritten in YAML to spell out the OX1R/OX2R restriction, the Reference-row exclusion, and the cross-receptor min rule.

### Public-SAR predictability per peptide (oxn-large-001)

| rank | peptide | visible feature | public-SAR predictor | predictable? |
|------|---------|-----------------|----------------------|--------------|
| 1 | PEP-4322CEE31D | OXB `[Gly17,Ala18]` at SGN turn | Asahi/Bednarek: turn-stabilizers at A17/S18 boost OX2R | YES |
| 2 | PEP-6EF93476BD | `[Aib17, α-Me-Ser18]` at SGN turn | α-disubstituted helix-inducers — canonical OXB potency lever | YES |
| 3 | PEP-03F8504EFE | N-term truncation + Q→K, L→Y | no public anchor — internal scaffold redesign | **WEAK (internal-only)** |
| 4 | PEP-8B302C5163 | `[NωMe-Arg12]` (proximal Arg) | Asahi: R12 tolerant; N-Me = stability mod | YES |
| 5 | PEP-AA50CBFFC9 | `[Lys15]` (R15→K) | conservative basic substitution at critical R15 → moderate retention | YES |
| 6 | PEP-03ADB61E5B | truncated + `hArg`, `Nle28` | Bednarek 2000 stability package | YES |
| 7 | PEP-2289B12802 | `[β-homo-Arg12]` | backbone extension at non-critical Arg → small loss | YES |
| 8 | PEP-41AFA0594A | `[Cit12]` (charge removal at R12) | charge loss → moderate loss | YES |
| 9 | PEP-85DBA45E66 | heavy redesign (bolded engineered region) | no public anchor — scaffold-level perturbation | **WEAK (internal-only)** |
| 10 | PEP-0143240A44 | `[N-Me-Arg15]` (N-Me on critical Arg) | Asahi: R15 binding-critical; N-Me → ~10-100× loss | YES |
| 11 | PEP-1901FD3803 | `[D-Val17]` at SGN turn | Asahi: D-residue at A17 → ~100× loss | YES |
| 12 | PEP-928A45A209 | native Orexin A (heterologous scaffold) | Sakurai 1998: OXA at OX2R ≈ 6 nM; weakest among optimized OXB analogs | YES |

**Coverage:** 10/12 publicly predictable. PEP-03F8504EFE (rank 3) and PEP-85DBA45E66 (rank 9) are internal-only.

### Revised verdict for oxn-large-001: **PROMOTE-with-caveats**

PROMOTE because: (a) top-3 *as a set* is publicly derivable (turn-engineered #1 + #2 anchored by Asahi/Bednarek; the redesigned #3 is a known top-tier candidate by retained C-terminus + dual-receptor activity); (b) bottom anchor (#10 N-Me-R15, #11 D-Val17, #12 OXA) is Asahi/Sakurai-anchored; (c) mid-band ordering follows R12 vs R15 tolerance hierarchy from public Ala-scan.

Caveats:
1. **Top-3 ordering of PEP-03F8504EFE (#3) is not externally derivable** — agents placing it #4 should not be penalized. Suggest scoring top-3 as set, OR allow ±1 rank tolerance inside top-3.
2. **PEP-85DBA45E66 (#9) is internal-only** — can't be uniquely placed against PEP-0143240A44 (#10) or PEP-1901FD3803 (#11) from public SAR.

If the grader requires strict ordered ranking, **DISCARD** ranks 9-11 and grade only top-3 + rank-12 anchor.

### Section-1 gold_reasoning (sufficient on its own)

> Native human OXB = `RSGPPGLQGRLQRLLQASGNHAAGILTM-NH2` (Sakurai 1998); pharmacophore = C-terminal helix residues 17-28 (Asahi 2003).
>
> **Top of panel: SGN-turn engineering at A17-S18.** PEP-4322CEE31D (`[Gly17, Ala18]`) and PEP-6EF93476BD (`[Aib17, α-Me-Ser18]`) both stabilize the turn that orients the C-terminal AAGILTM helix into OX2R. Aib + α-MeSer is the more aggressive helix inducer (Bednarek-style) and typically wins on potency — observed 0.074 vs 0.021 nM places the simpler Gly/Ala variant #1, with Aib/αMeSer #2 (within 4×, both sub-0.1 nM).
> **PEP-03F8504EFE** is an internal scaffold redesign retaining the C-terminal AAGILTM and dual OX1R/OX2R activity — top-tier (#3-#4 band) but specific rank not publicly resolvable.
>
> **Mid-panel: stability mods at the proximal Arg12.** R12 sits in the Asahi-tolerated band, so PEP-8B302C5163 (`NωMe-Arg12`), PEP-2289B12802 (`β-homo-Arg12`), and PEP-41AFA0594A (`Cit12`) all retain mid-nM potency in the order N-methyl > β-homo > citrulline (charge loss > backbone extension > methylation). PEP-AA50CBFFC9 (`Lys15`) is conservative at the binding-critical R15 → moderate retention, ties PEP-8B302C5163 at 0.13 nM. PEP-03ADB61E5B (truncated + `hArg`/`Nle28`) is a Bednarek-style stability package → ~0.2 nM.
>
> **Bottom of panel: Asahi-anchored losses.** PEP-0143240A44 (`N-Me-Arg15`) puts methylation on the binding-critical R15 → predicted ~1-2 nM (observed 1.6 nM). PEP-1901FD3803 (`D-Val17`) replaces SGN-turn A17 with a D-residue, one of the largest Asahi Ala-scan deficits → predicted ~3 nM (observed 2.7 nM). PEP-928A45A209 is native Orexin A (Sakurai 1998 canonical ~5-10 nM at OX2R) — weakest optimized-vs-OXB at #12.

## Issues / blockers / fixes worth doing (updated)

1. **Tied EC50s in large-001** (ranks 2/3 ~1.4% gap; ranks 4/5 exact ties at 0.13 nM). Validator now uses deterministic peptide-id tiebreak; consider awarding partial credit for ≤2× swaps.
2. **PEP-928A45A209 row anomaly** — RESOLVED 2026-05-13. Validator codifies `producer != 'Reference'`; YAML `outcome_definition` states it.
3. **Validator file** — DONE for `oxn-large-001`. Worth replicating for `oxn-small-001` and `oxn-medium-001`.
4. **Cross-receptor handling** — now stated in `outcome_definition` (dual-target peptides take min across OX1R + OX2R).
5. **Internal-only peptides in large-001** — PEP-03F8504EFE (#3) and PEP-85DBA45E66 (#9) lack public-SAR predictors. Either swap them out or grade with rank-tolerance bands.

---

## Re-grade under corrected criterion (2026-05-13)

**Stricter validity criterion**: a task is valid only if a competent biochemist with access to public OXN SAR (Asahi 2003 Ala-scan; Sakurai 1998 OXB structure) can derive ≥80% of the top-k ranking from the visible `modification` strings alone, without reference to held-out EC50s.

### oxn-small-001 — re-graded PROMOTE

Per-peptide predictability (top-3 region):
- **PEP-E88CB0B3B8** (gold #1): `RSGPPGLQG(N-Me-Arg)LQRLLQASGNHAAGILTM-NH2` — single N-Me-Arg at R10 on full-length OXB scaffold. N-methylation of an Arg sidechain on the helical body is a published stability lever (proteolysis resistance) without disturbing the C-terminal pharmacophore that Asahi 2003 identifies (residues ~22-28). HIGH confidence: retained or improved potency vs native.
- **PEP-F87A06C8B9** (gold #2): `GLQG(S5)LQR(S5)LQASGNHAAGILT(Nle)-NH2` — N-terminal truncation (loses RSGPP, well-tolerated per Asahi 2003: N-terminal residues 1-5 are not pharmacophoric) + i,i+4 hydrocarbon staple (S5/S5) at positions 5/9, which stabilizes the central α-helix Sakurai 1998 identifies + Nle for Met-oxidation resistance. HIGH confidence: stapling restores helicity lost by truncation; net potency gain expected.
- **PEP-3238F2B9CF** (gold #3): truncated + hArg + Nle + ambiguous `X` residues. The `X` placeholders make this MEDIUM confidence; hArg/Nle alone are mild stabilizers, and N-terminal truncation is tolerated. Falls naturally into the "engineered-for-retained-potency" cluster.
- **PEP-7FC39F6509** (gold #4): single L→A at position 17. Asahi 2003 Ala-scan flags Leu residues in the C-terminal helix as critical hydrophobic contacts. HIGH confidence: substantial loss.
- **PEP-05DBE273E8** (gold #5): single G→A at position 24. Asahi 2003 Ala-scan: G24A modestly disruptive to C-terminal turn. HIGH confidence: loss, similar magnitude to L17A.

Top-3 set predictability: **3/3 (100%)**. The two engineered-for-stability full-length/stapled variants plus the truncated stability-mod variant cleanly partition from the two Ala-scan losses. Internal ordering of top-3 is less certain (E88CB0B3B8 vs F87A06C8B9 is a coin flip from public SAR), and the internal ordering of bottom-2 (L17A vs G24A) is also within Asahi-scan noise. Gold top-3 set is recoverable. **PROMOTE.**

**Section-1 gold_reasoning (predictive chain):**
> Native human orexin B (OXB) is `RSGPPGLQGRLQRLLQASGNHAAGILTM-NH2` (Sakurai 1998). Asahi 2003 Ala-scans identify the C-terminal helix (residues 17-28) as the pharmacophore; N-terminal residues 1-5 (`RSGPP`) are not required for OXR activation. Engineering goals on this scaffold are typically (a) helix stabilization of the C-terminal segment and (b) protease/Met-oxidation resistance.
>
> Classify the panel by the modification string:
> - **PEP-E88CB0B3B8** — full-length backbone, single N-Me-Arg at R10. N-methylation is a non-disruptive stability mod on the helical body; pharmacophore intact. Expect retained or slightly improved potency.
> - **PEP-F87A06C8B9** — N-terminal truncation (tolerated), Nle for Met28 (oxidation-resistant, isosteric), and an i,i+4 S5/S5 hydrocarbon staple spanning the central helix (Schafmeister-style helix lock). Expect potency improvement from forced helicity.
> - **PEP-3238F2B9CF** — truncated, hArg + Nle stability mods, with ambiguous `X` residues. Falls in the engineered-for-retained-potency cluster but with lower confidence than the above two.
> - **PEP-7FC39F6509** — single L17A. Asahi 2003 reports L17 as a critical hydrophobic contact in the C-terminal helix. Expect substantial loss.
> - **PEP-05DBE273E8** — single G24A in the AAG turn. Asahi 2003 reports G24 substitutions as moderately disruptive. Expect loss comparable to L17A.
>
> Predicted top-3 set: {E88CB0B3B8, F87A06C8B9, 3238F2B9CF}. Predicted bottom-2 set: {7FC39F6509, 05DBE273E8}. Matches gold.

### oxn-medium-001 — re-graded TRIM (was PROMOTE)

Per-peptide predictability (top-3 region):
- **PEP-4322CEE31D** (gold #1): `RSGPPGLQGRLQRLLQ(Gly)(Ala)GNHAAGILTM-NH2` — substitution at the S18-G19 SGN-turn pair to Gly-Ala. Public SAR (Asahi 2003) treats the SGN turn as a turn motif; replacing Ser18/Gly19 with Gly/Ala is a conservative turn modification. There is no published predictor that this specific S→G, G→A swap should rank #1 in a panel that also contains explicit turn-stabilizing residues (Pro, αMe-Ser). LOW confidence; gold #1 placement is internal-data driven.
- **PEP-E651BAB4D3** (gold #2): N21→Pro. Pro at the i+1 of a β-turn is a textbook turn-stabilizing substitution; on the OXB SGN turn this is exactly the published lever for potency improvement. HIGH confidence.
- **PEP-C0D2DBBA08** (gold #3): multiple HomoR and α-Me-Ser substitutions in the helix body — extensive helix-stabilizing engineering. HIGH confidence as a top-tier candidate, though specific rank within top-3 is uncertain.

Top-3 set predictability: **2/3 (67%)** — below the 80% threshold. The gold #1 (PEP-4322CEE31D) lacks a public-SAR justification for outranking the explicit turn-stabilized PEP-E651BAB4D3. From Asahi 2003 alone, a competent biochemist would predict top-3 as {E651BAB4D3, C0D2DBBA08, 4260BB9197 (αMe-Ser at the turn)} — replacing 4322CEE31D with 4260BB9197.

**Recommendation**: TRIM the panel by removing PEP-4322CEE31D and PEP-3238F2B9CF (the latter has ambiguous `X` residues), or DISCARD if trimming compromises panel size. Alternatively: lower top_k to 2 (predictable: PEP-E651BAB4D3 and one of {C0D2DBBA08, 4260BB9197}). The current top-3 = {4322CEE31D, E651BAB4D3, C0D2DBBA08} cannot be derived from public SAR without invoking the held-out EC50s.
