# Hidden Answers

Hidden answer or rubric YAML files live here.

These files are gitignored by default because they contain evaluation labels.
For a public release, keep private held-out labels outside the distributed task
package.

Supported hidden-answer modes include ranking labels for candidate
prioritization, exact labels for hit prediction, utility rankings for
next-experiment tasks, and expert concept rubrics for mechanistic hypotheses,
experiment plans, foundation-model triage, and end-to-end drug discovery program
tasks.

Tasks whose outcomes are still waiting on wet-lab validation may use
`label_status: wet_lab_validation_pending` and omit gold labels. Those answer
YAMLs should still define the intended `outcome_definition`; the grader records
parsed recommendations but does not assign a score until validation labels or an
expert rubric are added.
