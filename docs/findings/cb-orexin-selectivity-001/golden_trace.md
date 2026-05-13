# Golden trace — cb-orexin-selectivity-001

This is the reference reasoning chain that lands on the correct answer
(`OXNv25.5`) without reading the gold yaml or the raw assay data. It
uses only what the agent has access to: the 16 compound IDs with
sequence/modification strings in `analogs.csv`, public scientific
literature, and general peptide chemistry.

The goal is to make the agent's reasoning auditable. An agent that
arrives at `OXNv25.5` via a different path is fine; an agent that
arrives at it by reading `data/answers/*.yaml` (as the local-claude
run did) is not, even though both produce the right answer.

---

## Step 1 — Identify the parent peptide family

From `analogs.csv`, several compounds carry sequences ending in
`...HAAGILTM-NH2` or `...HAAGILTL-NH2`. The conserved C-terminus
`HAAGILT(M/L)-NH2` matches the orexin B / orexin A C-terminal motif
verbatim. The compound `OXNv7` is described as `Orexin A: pGlu-PLPD…`
in plain text — confirming the family without further inference.

Conclusion: the panel is orexin B 6–28 analogs (plus one orexin A
reference and one mouse-orexin variant), tested at the OX1R / OX2R
receptor pair.

## Step 2 — Retrieve the canonical SAR

The relevant published literature:

- **Lang et al. 2004** (*J. Med. Chem.* 47:1153). Alanine and proline
  scan of human orexin B 6–28 at both receptors. Most OX2R-selective
  single substitutions reported: [A27] >1350×, [P11] >1265×,
  [P14] >560×, [A15] >430×, [P7]/[P10]/[P13] in the 20–30× range,
  [P17] 20.4×, [P12] 18.8×, [A13]/[A11] 18.1×/22.4×. Truncation
  6→10 is >1750× selective (orexin B 10–28).

- **Asahi et al. 2003** (*Bioorg. Med. Chem. Lett.* 13:111). The
  compound [Ala11, D-Leu15]orexin B at ~1500× OX2R selectivity. This
  is the canonical Ox2R-selective orexin B reference and predates the
  Lang scan.

Both papers single out the same residue set as critical: the
C-terminal helix (L15, I25, L26, T27) anchors OX1R activation, so
disrupting it preferentially blocks OX1R while leaving OX2R active.
Q12 / R13 / L14 are secondary contact residues whose substitution
also confers modest OX2R selectivity.

## Step 3 — Identify the literature-matching candidate (the trap)

Inspect each compound description for matches against the published
SAR. The hits:

- `OXNv2` — described in the panel as `hardened OXB: D-Leu15`. This
  is exactly the Asahi 2003 compound (D-Leu at position 15 plus the
  Ala11 substitution implied by "hardened"). The literature reports
  ~1500× selectivity for this compound.

- `OXNv7` — full-length orexin A. Not selective (OX1R-preferring by
  Lang et al.; selectivity ratio ~0.3).

- The `[A6]…[A28]` and `[P6]…[P28]` style compounds from the Lang
  scan are not in this panel (they would be the obvious decoys); the
  panel uses internal `OXNv*` / `MOXv*` identifiers instead.

**Critical inference: `OXNv2` is a candidate but not necessarily the
answer.** The user's panel is internal modifications, not a
reproduction of the published series. The prompt says the most-
selective compound in the panel exceeds 1000× — Asahi 2003 sits at
~1500×, which is consistent with `OXNv2` being a reasonable
candidate, but the panel could also contain compounds that *exceed*
the published winner. Commit to `OXNv2` only if no other candidate
plausibly beats it.

## Step 4 — Scan the panel for compounds the literature can't predict

The published SAR covers single-residue substitutions. Anything in the
panel that uses *combinations* of substitutions, *novel chemistry*
(unnatural amino acids, lipidation, cyclization), or *modifications
at positions the paper didn't probe* is outside the literature's
reach and could exceed it.

Categorize the 16 compounds:

| Category | Compounds |
|---|---|
| Literature-replicated | OXNv2, OXNv7 (orexin A reference) |
| Single-position swaps (paper-positions) | OXNv14.15 (hArg at 12), OXNv14.16 (β-hArg at 12), OXNv15.7 (hArg at 9), OXNv16.20 (Ser at 16) |
| Double substitutions, paper-positions | OXNv16.13 ([H14, G15, A16]), OXNv16.18 ([G15, A16]), OXNv16.19 ([Aib15, αMeSer16]) |
| OXNv25.x series — substitutions at positions 12/13 ± 17 ± terminus | OXNv25.3, OXNv25.5, OXNv25.6, OXNv25.7, OXNv25.9, OXNv25.10 |
| Cyclized / N-terminally modified | OXNv12.2 (hydrocarbon-stapled `S5` at 7/10; Nle28) |

The `OXNv25.x` series is the standout. Six compounds varying around
a shared design — that's a chemistry team optimizing a specific
hypothesis. The series spans:

- `OXNv25.3`: single [A17G]
- `OXNv25.5`: double [Q12Y, R13E]
- `OXNv25.6`: double [Q12Y, A17G]
- `OXNv25.7`: triple [Q12Y, R13E, A17G]
- `OXNv25.9`: N-terminal RQK extension + scattered changes
- `OXNv25.10`: [Q12Y, A17G, M28Nle]

The `[Q12Y, R13E]` core (in OXNv25.5 and OXNv25.7) is the most
aggressive perturbation in the entire panel: it removes the
positively charged R13 sidechain and replaces it with a negatively
charged E — a *charge reversal* — while inserting an aromatic Tyr at
Q12. The Lang scan shows positions 12 and 13 are each selectivity-
sensitive on their own (Ala at 13 = 18.1× selective; Pro at 12 =
18.8×). Combining a charge-reversing and a polar-to-aromatic
substitution at adjacent positions is a qualitatively larger
perturbation than any single-residue swap in the Lang panel.

## Step 5 — Within-series comparison

If `[Q12Y, R13E]` is the load-bearing modification, the question
becomes: does adding *more* substitutions to that core help or hurt?

Predict from the Lang SAR:

- A17 is a residue in the loop between the two helices. The Lang
  alanine scan didn't test A17→A (trivial), but [P17] at 20.4× shows
  this position is selectivity-relevant. However, position 17 is
  also part of the OX1R recognition surface — substitutions here can
  *recover* some OX1R activity if they restore a contact the C-helix
  needs.

- Therefore, adding `[A17G]` on top of `[Q12Y, R13E]` (giving
  OXNv25.7) likely partially *rescues* OX1R binding, reducing
  selectivity even if it improves potency at both receptors.

- The minimal `[Q12Y, R13E]` member of the series — `OXNv25.5` —
  should be the most selective, because it has the disrupting
  modification at 12/13 without the OX1R-rescuing modification at 17.

## Step 6 — Reject the trap, commit to OXNv25.5

The choice is between:

- `OXNv2` (Asahi 2003 [Ala11, D-Leu15]): ~1500× selective by
  literature. Single position 15 D-substitution at the C-helix
  anchor.

- `OXNv25.5` ([Q12Y, R13E]): unpublished double substitution at
  positions 12/13. The combined perturbation (charge reversal +
  aromatic insertion at adjacent secondary-contact residues) should
  exceed any single-residue substitution at the anchor position 15,
  because:
  1. Position 15 is one residue; positions 12+13 together are two
     residues of disruption.
  2. The 12/13 perturbation includes a *charge reversal*, which the
     Lang scan never tested. Going from R+ to E− at a residue in the
     OX1R contact surface is a much larger change than the L→D
     stereochemistry inversion at 15.
  3. The fact that the chemistry team made a series around
     `[Q12Y, R13E]` (six compounds in the OXNv25.x family vs zero
     compounds replicating the Asahi 2003 hardened-OXB chemistry)
     suggests the team had already found `[Q12Y, R13E]` to be the
     more productive optimization direction.

Answer: **`OXNv25.5`**.

## What this trace illustrates

Three reasoning moves separate this trace from the observed failure
modes:

1. **Refuse to commit at the moment of literature match.** Claude's
   sonnet-4 trace stopped reasoning the moment WebSearch returned a
   hit on "hardened orexin D-Leu15." A correct chain treats the
   literature match as a *candidate*, not an *answer*.

2. **Recognize a series within the panel.** Six `OXNv25.x` compounds
   sharing structural features is a signal that a chemistry team
   was optimizing around a specific design. The series is the
   single biggest hint that something in this region beats the
   literature winner.

3. **Reason about which series member is the maximally-selective
   one.** Once the `[Q12Y, R13E]` core is identified, predicting
   that the *least-modified* member of the series is the most
   selective (because additional modifications rescue the receptor
   you're trying to disrupt) is the move that picks `OXNv25.5`
   over `OXNv25.7`.

## Verifying this is actually how the data lands

The validator (`data/validators/cb-orexin-selectivity-001.py`)
confirms the prediction order from the raw assay data:

- OXNv25.5: 8856× (gold)
- OXNv2: 1473× (Asahi 2003 winner; 6.0× behind)
- OXNv25.7 ([Q12Y, R13E, A17G]): 1345× — *less* selective than
  OXNv25.5 by 6.6×, consistent with the prediction that the A17G
  addition rescues some OX1R activity
- OXNv25.6 ([Q12Y, A17G]): 143× — confirms that [Q12Y] alone (without
  R13E) is much less selective than the [Q12Y, R13E] combination,
  validating the "charge reversal at 13 is doing the heavy lifting"
  reasoning
- OXNv25.3 ([A17G] only): 246× — single-position [A17G] without any
  helper substitution; modestly selective

The data is consistent with the chain above. The reasoning is
prospective, not constructed-after-the-fact from the measurements.

## What this is NOT

This is a reference reasoning chain, not the only correct chain. An
agent that picked OXNv25.5 by raw structural intuition (e.g.,
"largest charge perturbation in the panel wins") would also be
correct. An agent that arrived at OXNv25.5 by *eliminating* candidates
rather than building toward it would also be correct. The point of
this trace is to demonstrate that the correct answer is reachable
without reading the gold file, by an agent that does literature
retrieval + within-panel structural comparison.
