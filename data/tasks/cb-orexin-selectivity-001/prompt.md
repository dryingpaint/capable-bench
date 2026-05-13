# Receptor-preference prediction from peptide sequences

The peptides in `analogs.csv` are a panel of synthetic peptide variants
characterized in vitro at two related G-protein-coupled receptors,
labeled Receptor 1 (R1) and Receptor 2 (R2). Each variant has been
profiled in a cellular signaling assay; we have measured response
half-maximal concentration values at both receptors. Those measured
values are not provided to you.

Using only the peptide sequences and modification descriptions in
`analogs.csv`, plus any published structure-activity literature you can
locate that is relevant to the parent peptide family, identify which
single variant in the panel has the strongest preference for R2 over
R1, defined as the largest ratio:

    preference = response_concentration(R1) / response_concentration(R2)

A higher ratio indicates a stronger preference for R2. In this panel,
the most preferring variant has a ratio above 1000; the least
preferring has a ratio below 10. The variants represent a mix of
single-position substitutions, multi-position combinations, and
modifications outside the published variant set.

Write `answer.json` with exactly one field:

    most_R2_preferring: one of the compound IDs listed in analogs.csv

Grading is exact-match on this field. Use whatever reasoning chain you
wish — sequence analysis, structural arguments, retrieval of published
SAR for this peptide family. Your rationale is not scored.
