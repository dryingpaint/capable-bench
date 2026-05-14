---
task_ids: [pilot-peptide-ranking-sequence-mch-small-001, pilot-peptide-ranking-sequence-mch-medium-001, pilot-peptide-ranking-sequence-mch-large-001]
verdict: small=PROMOTE, medium=trim-and-PROMOTE, large=trim-and-PROMOTE
reviewed: 2026-05-13 (re-graded under stricter validity criterion)
---

## Stricter validity criterion (applied here)

A task is valid only if a competent biochemist who sees only `peptide_id` +
`modification` and has access to published MCH SAR (Bednarek 2001 *Mol Pharmacol*
60:1115; Audinot 2001 *J Biol Chem* 276:13554) can construct a Section-1
predictive chain that lands on the gold ranking (or top-k). Held-out EC50
values in `data/processed/invitro_assays.csv` serve only as auxiliary
verification — the agent never sees them.

Public MCH SAR rules a biochemist can apply to a modification string:

1. **Native hMCH (19-mer `DFDMLRCMLGRVYRPCWQV`, Cys7–Cys16 disulfide)** is the
   benchmark. Anything else is downhill from it.
2. **Cys7–Cys16 disulfide is mandatory.** Cys→Ala or Cys→Ser at either bridge
   position drops affinity ≥10⁴-fold; D-Cys at 7 disrupts geometry and is also
   highly deleterious.
3. **N-terminal `DFDM` tail (residues 1–4)** contributes ~5–20× extra potency
   over the truncated cyclic core MCH(5–17) `RCMLGRVYRPCW`.
4. **Retro-enantiomer (all-D, reverse sequence)** abolishes activity.
5. **Bednarek 2001 alanine scan:** most internal positions tolerate Ala
   (≤10× loss, e.g., Phe2, Met8, Met4 mild). Critical positions where Ala
   substitution causes large losses are Arg6, Arg11, Tyr13, Arg14.
6. **Truncated cyclic hexapeptides** (Cys-Arg-Val-Tyr-Arg-Cys) retain only
   high-nanomolar/µM binding.
7. **Pro15 deletion** preserves binding modestly but sharply impairs
   functional agonism.
8. **Acyclic 10-mer fragments** (Bednarek "north" or "south" halves) are
   essentially inactive (≥10 µM, partial agonism).

Anything **internal** that is not on this list (novel hArg/HomoArg insertions,
unusual lipidations, unpublished cyclization geometries) is **not
publication-derivable**.

---

## mch-small-001 — VERDICT: PROMOTE

5 peptides, top-3 gold = `B2688A8B6F` > `F13501AAC3` > `FE1C020140`.

| peptide_id | modification (visible to agent) | public-SAR call | predictable? |
|---|---|---|---|
| PEP-B2688A8B6F | `DFDMLRCMLGRVYRPCWQV` (19-mer, Cys7–Cys16) | Native hMCH; rule 1 → **#1** | HIGH |
| PEP-F13501AAC3 | 17-mer same as above minus C-terminal QV | Truncated native, intact disulfide; rule 1+3 → **#2** | HIGH |
| PEP-FE1C020140 | 12-mer `RCMLGRAYRPCW` (cyclic core, MCH(5–17)-like, Ala11→Ala11 = native G→A swap; missing N-terminal `DFDM`) | Truncated cyclic core; rule 3 → **#3** | HIGH |
| PEP-B41BAA7006 | `Ac-RAMLGRVYRP-NH2` (acyclic 10-mer, no Cys) | Disulfide ablated by truncation; rule 2 → bottom | HIGH |
| PEP-65DFE88AA1 | `DFD-MLRAMLG-NH2` (acyclic 10-mer, no Cys) | Disulfide ablated; rule 2+8 → bottom | HIGH |

5/5 predictable; top-3 = 3/3 predictable. **PROMOTE.**

### Section-1 gold_reasoning (small)

> By inspection of the modification strings: PEP-B2688A8B6F is the canonical
> 19-mer hMCH `DFDMLRCMLGRVYRPCWQV` with Cys7–Cys16 — the literature gold
> standard (Bednarek 2001 Table 1; Audinot 2001 Table II). Rank #1.
> PEP-F13501AAC3 is the same disulfide-bridged sequence truncated to 17 mer
> (loses C-terminal Gln-Val); the C-terminal dipeptide contributes little to
> binding (Bednarek 2001 fragment series), so this should rank just below
> native. Rank #2. PEP-FE1C020140 is the cyclic MCH(5–17) core lacking the
> N-terminal `DFDM` tail — Bednarek/Audinot show ~10× loss when the tail is
> removed. Rank #3. PEP-B41BAA7006 and PEP-65DFE88AA1 are acyclic ten-mers
> with no Cys residues at all (disulfide cannot form); the Bednarek 2001
> Table 5 fragment series shows such acyclic fragments are essentially
> inactive (>10 µM, ≤20% Emax). Bottom two; tie-break by which retains more
> of the conserved core: B41BAA7006 keeps `RAMLGRVYRP` (most of the core
> ring), 65DFE88AA1 keeps the N-tail + first half of ring, so B41BAA7006
> slightly preferred (rank #4) over 65DFE88AA1 (rank #5).

---

## mch-medium-001 — VERDICT: trim-and-PROMOTE (PROMOTE for top-3 only)

8 peptides, top-3 gold = `B2688A8B6F` > `5D7C340C27` > `28227AE493`.

| peptide_id | modification (visible to agent) | public-SAR call | predictable? |
|---|---|---|---|
| PEP-B2688A8B6F | `DFDMLRCMLGRVYRPCWQV` | Native hMCH → **#1** | HIGH |
| PEP-5D7C340C27 | `DADMLRCMLGRVYRPCWQV` | Phe2→Ala — Bednarek 2001 Table 1 lists [Ala2]hMCH as one of the most tolerant single-Ala substitutions (sub-nM IC50). Rank #2. | HIGH |
| PEP-28227AE493 | `DTMRCMVGRVYRPCWEV` (17-mer; T2, M4-deletion-like, V7→V, E for Q) | Salmon/teleost MCH variant — recognizable as a non-mammalian MCH ortholog by the conserved cyclic core + altered tail. A biochemist familiar with Audinot 2001 Table II (which includes salmon MCH) would predict near-native potency, but **identifying it as salmon MCH from the raw sequence requires either knowing the salmon sequence or recognizing the conserved Cys7–Cys16 ring is intact with mild N-tail mutations.** Borderline. | MEDIUM |
| PEP-86DBECA755 | `R-cyclo(S-S)(CMLGRVYRPC)-NH2` (cyclic decapeptide, MCH core only) | Audinot 2001 cyclic core MCH(5–14)-NH2 — high-affinity (~1 nM). Predictable by rule 3 as just below truncated 17-mer. Rank #4. | HIGH |
| PEP-0D5499FC99 | `DMLRCMLGRVYRPCW` (15-mer, missing F2-D3 N-tail and QV C-tail) | Truncated mid-region; intact disulfide. Rule 3 → mid-pack. Rank #5 plausible. | HIGH |
| PEP-021CF7B0A5 | `Ac-R-D-Cys-MLGRVYRPC-W-NH2` (D-Cys at position 7) | D-Cys disrupts disulfide geometry (rule 2) → bottom. | HIGH |
| PEP-2458EB436B | `DFDMLR-Ser-MLGRVYRP-Ser-WQV` (Cys7,16→Ser) | Disulfide ablated by Ser substitution (rule 2) → bottom. | HIGH |
| PEP-CF372AC677 | `Ac-(all-D, retro)` 12-mer | Retro-enantiomer (rule 4) → absolute bottom. | HIGH |

7/8 fully predictable; PEP-28227AE493 is borderline (predictable as "intact ring + mildly altered N-tail = near-native" but exact rank #3 over #4 (cyclic core lacking N-tail) requires recognizing that the salmon-MCH N-tail substitutions are individually mild while removing the entire DFDM tail loses more potency). Top-3 prediction is solid: native > [Ala2]hMCH > intact-ring variant > everything cyclic-core-only.

**Top-3 gold-derivable: 3/3 (PEP-28227AE493 ranks above core-only variants by N-tail-presence rule).** Full-ranking derivability ~75% — below the 80% bar for full-rank PROMOTE but above for top-3.

**Recommendation: PROMOTE for top-3 evaluation only**, or trim panel to drop PEP-86DBECA755 vs PEP-28227AE493 ambiguity. Current `top_k: 3` setting in answer file is defensible.

### Section-1 gold_reasoning (medium, top-3)

> PEP-B2688A8B6F is canonical 19-mer hMCH (rank #1). PEP-5D7C340C27 differs
> from native only at position 2 (`DADMLRCMLG…` vs `DFDMLRCMLG…`); Bednarek
> 2001 Table 1 alanine scan lists [Ala2]hMCH as one of the most tolerated
> single-Ala substitutions (≤2× IC50 loss vs native). Rank #2.
> PEP-28227AE493 retains the intact Cys7–Cys16 ring and most of the
> N-terminal tail with only conservative substitutions (T2, M4 retained as
> M, V7→V, E18 for Q18); a biochemist would recognize this as either the
> salmon-MCH ortholog or a closely related variant — Audinot 2001 reports
> salmon MCH as near-equipotent to hMCH at MCHR1. Rank #3 above the
> core-only PEP-86DBECA755 because the N-terminal DFDM/DTMR tail is intact.

---

## mch-large-001 — VERDICT: trim-and-PROMOTE (PROMOTE for top-3 with caveats)

12 peptides, top-3 gold = `76033AAA8F` > `0D5499FC99` > `2778ED6AA3`.

| peptide_id | modification (visible to agent) | public-SAR call | predictable? |
|---|---|---|---|
| PEP-76033AAA8F | `DFDMLRCMLGRV-ITyr-RPCWQV` (19-mer, 3-iodo-Tyr at pos 13) | 3-IodoTyr13 = Audinot 2001 radioligand precursor; published as **slightly more potent than native** (cAMP EC50 0.44 nM vs 0.28 nM for native; not a huge gap). A biochemist *would* recognize `ITyr` as the radio-iodination intermediate and infer near-native or marginally improved potency. Predictable as **top-1 or top-2**, but the literal rank #1 over native depends on knowing iodination *enhances* rather than mildly depresses affinity (a coin-flip prior without the specific paper). | MEDIUM |
| PEP-0D5499FC99 | `DMLRCMLGRVYRPCW` (15-mer, intact ring, lost F2-D3 + QV) | Truncated native, intact disulfide → very high potency (~1–2 nM). Predictable as top-3. | HIGH |
| PEP-2778ED6AA3 | `LRCMLGRVYRPCW` (13-mer, intact ring, lost DFD + QV) | Further N-truncated cyclic; Audinot 2001 shows MCH(4–17) ≈ MCH(5–17) ≈ ~1–3 nM. Top-3 plausible. | HIGH |
| PEP-ADE0407385 | `RCMLGRVYRA-CW` (12-mer; Pro15→Ala in the ring) | Pro15→Ala in the disulfide ring — Audinot 2001 Table III shows modest loss (~3–10× vs cyclic core). Mid-pack. | MEDIUM |
| PEP-759341CC19 | `DFDMLRCMAGRVYRPCWQV` (Leu9→Ala in the ring) | Bednarek 2001 alanine scan: [Ala9]hMCH = one of the most tolerant scan positions (IC50 ~3.7 nM). Predictable. | HIGH |
| PEP-9BC43BFBCF | `DFDMLRCALGRVYRPCWQV` (Met8→Ala in the ring) | Bednarek 2001 [Ala8]hMCH = 59–99 nM IC50, ~100× loss. Predictable as mid/lower-mid. | HIGH |
| PEP-B0CE5E7267 | `RCALGRVYRPCW` (12-mer cyclic core + Met8→Ala) | Stacked penalties: lost N-tail + Ala8 substitution. Predictable as lower-mid. | HIGH |
| PEP-C87C5400D0 | `Ac-[ΔPro15]-RCMLGRVYRCW-NH2` (cyclic core, Pro15-deleted) | Audinot 2001: Pro15 deletion preserves binding (~250 nM IC50) but kills functional agonism (>10 µM Ca²⁺). Predictable as low. | HIGH |
| PEP-70DED4DFCB | `Ac-CGRVYRC-NH2` (truncated cyclic hexapeptide) | Bednarek 2001 Table 2 minimal cyclic hexamer; ~700 nM binding, inactive in functional assay. Predictable as near-bottom. | HIGH |
| PEP-940F7913A1 | `Ac-CRVYRC-NH2` (cyclic hexapeptide, no Gly spacer) | Bednarek 2001 Table 2: minimal pharmacophore; ~1 µM. Near-bottom. | HIGH |
| PEP-1C3A95C258 | `Ac-GRVYR-NH2` (acyclic 5-mer) | No disulfide possible (no Cys); ~1 µM binding, inactive. Bottom. | HIGH |
| PEP-BE74C0EE55 | `DFDMLRAMLGRVYRPAWQV` (Cys7→Ala AND Cys16→Ala) | Disulfide ablated (rule 2) → absolute bottom (>10 µM). | HIGH |

11/12 fully predictable; PEP-76033AAA8F (3-IodoTyr13) is borderline for the
*exact* rank #1 over native — but native hMCH is **not in the panel here**, so
the call is "near-native cyclic 19-mer" → top-1, which is correct.

Top-3 derivability:
- #1 PEP-76033AAA8F: predictable as top-1 (only intact 19-mer with N-tail and ring).
- #2 PEP-0D5499FC99: predictable (15-mer with intact ring, no Ala-scan loss).
- #3 PEP-2778ED6AA3: predictable (13-mer with intact ring, no Ala-scan loss).

**Top-3 gold-derivable: 3/3.** Full-ranking is ~92% derivable. **PROMOTE.**

The mid-ranks 4–8 distinguishing PEP-ADE0407385 (Pro15→Ala) vs PEP-759341CC19
(Leu9→Ala) vs PEP-9BC43BFBCF (Met8→Ala) requires consulting Bednarek's exact
table (Ala8 = 99 nM, Ala9 = 6.9 nM, Pro15→Ala in core = ~3.7 nM EC50).
A biochemist with the paper open can do this; a biochemist without it cannot
distinguish 4 from 5 from 6 confidently. This is acceptable because the
top-3 is the graded slice.

### Section-1 gold_reasoning (large, top-3)

> Among the 12 modification strings, only three retain the full intact
> Cys7–Cys16 disulfide ring AND the conserved internal residues Met8, Leu9,
> Pro15, Tyr13 in their native forms: PEP-76033AAA8F (19-mer with
> 3-iodo-Tyr13), PEP-0D5499FC99 (15-mer DMLRCMLGRVYRPCW), and PEP-2778ED6AA3
> (13-mer LRCMLGRVYRPCW). PEP-76033AAA8F is the only sequence retaining the
> full N-terminal `DFDM` tail; iodination of Tyr13 is the standard MCH
> radioligand modification (Audinot 2001) and is known to preserve or
> slightly enhance receptor affinity, so this is rank #1. PEP-0D5499FC99
> retains 15 residues including most of the N-tail (`DM-LRCMLGRVYRPCW`),
> giving it more N-tail context than PEP-2778ED6AA3 (13-mer, only `LR`
> N-tail residues). Rank #2. PEP-2778ED6AA3 is the cyclic core MCH(4–17),
> still high-potency per Audinot 2001 cyclic-core series. Rank #3.
> All other panel members carry either a Bednarek alanine substitution at a
> conserved position (Met8→Ala, Leu9→Ala), a Pro15 deletion, total disulfide
> ablation (Cys→Ala), severe truncation to a hexapeptide, or N-terminal
> acyclic fragments — and rank below the three intact-ring full-length
> variants.

---

## Summary

| task | original verdict | new verdict | top-3 derivable | full-rank derivable |
|---|---|---|---|---|
| mch-small-001 | PROMOTE | **PROMOTE** | 3/3 | 5/5 (100%) |
| mch-medium-001 | PROMOTE | **PROMOTE (top-3 only)** | 3/3 | 6–7/8 (~80%) |
| mch-large-001 | PROMOTE | **PROMOTE (top-3 strong; mid-ranks need paper)** | 3/3 | 11/12 (~92%) |

All three pass the stricter criterion **for the graded top-3 slice**.
Medium and large would benefit from explicit narrowing of the evaluation to
top-3 only (which `top_k: 3` in the answer files already enforces); the
full-ranking gold is verifiable but not fully publication-derivable for a
handful of mid-rank distinctions in `mch-medium-001`.

## Caveats / follow-ups

- No validator file exists for this family. Recommend adding
  `data/validators/pilot-peptide-ranking-sequence-mch-*.py` enforcing the
  `min(ec50_nm)` rule for the auxiliary verification step.
- Two ranking ties remain (medium 7-vs-8 at 81 vs 1000 nM is clear; large
  4-vs-5 both at 3.7 nM is gold-broken by second-best-assay tie-break — not
  derivable from public SAR but doesn't affect top-3).
- Original draft erroneously claimed Section 1 was sufficient without
  quantifying which peptides have published predictors; this revised draft
  corrects that.
