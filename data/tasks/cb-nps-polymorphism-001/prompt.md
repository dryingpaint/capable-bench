# Receptor-variant-preference prediction from peptide sequences

The peptides in `analogs.csv` are synthetic peptide variants characterized
in vitro at two natural variants of the same receptor, the human NPSR1
receptor. The two variants differ at a single residue position
(asparagine-107 in one variant; isoleucine-107 in the other — the
Asn107Ile polymorphism). Each peptide has been profiled in a cellular
signaling assay; we have measured the response half-maximal concentration
at both variants. The measured values are not provided to you.

Using only the peptide sequences and modification descriptions in
`analogs.csv`, plus any published structure-activity literature you can
locate that is relevant to the parent peptide family, identify which
single variant in the panel has the strongest preference for the
**isoleucine-107 variant (Ile107)** over the **asparagine-107 variant
(Asn107)**, defined as the largest ratio:

    preference = response_concentration(Asn107) / response_concentration(Ile107)

A higher ratio indicates a stronger preference for Ile107. In this panel,
the most preferring variant has a ratio above 200; the least preferring
has a ratio below 1 (i.e., prefers Asn107). The panel contains a mix of
literature-referenced peptides (native and truncated forms) and internal
modifications outside the published variant set.

Write `answer.json` with exactly one field:

    most_Ile107_preferring: one of the compound IDs listed in analogs.csv

Grading is exact-match on this field. Use whatever reasoning chain you
wish — sequence analysis, structural arguments, retrieval of published
SAR for this peptide family. Your rationale is not scored.
