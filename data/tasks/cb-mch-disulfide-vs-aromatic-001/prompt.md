Safety and scope: this is a non-clinical benchmark over anonymized internal
research data. Do not provide therapeutic advice, wet-lab protocols, synthesis
instructions, or real-world dosing instructions. Answer at the scientific
reasoning, evidence integration, and decision-gate level using only the files in
this task directory.

# Pairwise Potency Prediction from Sequence

`peptide_sequences.csv` contains two peptides targeting the MCH receptor
family. Each row gives the anonymized peptide identifier, the chemical
modification string (sequence plus any non-standard residues, lipidation, or
backbone modifications), the receptor family, and the receptor variants on
which the peptide series is tested. **No measured potency, efficacy, or assay
counts are provided.**

Using only the sequence and chemical modifications, predict which peptide is
more potent in functional in vitro assays at this receptor (lower EC50). Write
`answer.json` with `selected_option` set to the `peptide_id` of the more
potent peptide.
