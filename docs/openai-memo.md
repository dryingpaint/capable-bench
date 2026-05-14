# Why our data is useful to OpenAI

Capable is one of few companies running the entire drug-discovery process end to end, from drug design through clinical trials.

What this means concretely:

- **[Current] Drug design.** Sequence/structure proposal and computational triage.
- **[Current] In-vitro assessment.** Capable can evaluate the effectiveness of novel peptide designs within one day.
- **[Current] In-vivo assessment.** Mouse studies with held-out behavioural endpoints.
- **[Upcoming] Clinical-trial design and downstream.** Active programs across peptides, small molecules, and RNA are pre-clinical today; we anticipate IND, Phase I, and beyond.

Because we own the assays, every benchmark item ships with held-out experimental data — including items where the published SAR literature points one way and our assays point the other. That's where we see agents fail most often.

We've documented some noticeable failure modes in biochemical reasoning that we've identified in the models. [Full results](https://your-dashboard-url/findings).

---

## What we test

~140 tasks, all graded against held-out experimental data from our own assays. The agent typically sees a peptide's modification string and sometimes per-assay EC50/Emax readouts, and has to make a structural-biology call — predict potency, predict receptor or variant selectivity, predict in-vivo translation, or rank a candidate panel for advancement.

---

## Failures of biochemical reasoning

A curated subset of cases. Each links to the dashboard report page; click through for the full agent traces.

**Agents read modification count as potency.** Given two peptides, both Claude and Codex consistently pick the more elaborately-modified one — even when the cleaner alternative wins by an order of magnitude or more.

- **[NPS pairwise: agents read modification count as potency; truncation wins 60×](https://your-dashboard-url/findings/pilot-peptide-pairwise-sequence-nps-easy-011).** A four-modification peptide loses to a single-D-Thr version by 60–79×. Claude cites the published `[t-Bu-Ala3]NPS / [Cha3]NPS` analog series by name and still picks wrong — the published series covers a different position and a different question.

**Agents stop at the first relevant published template.** Find a paper or canonical SAR series whose compound matches the candidate's surface shape; commit; do not check whether the template's mechanism actually applies to *this* task.

- **[NPSR1 N107I: agents apply a stability template to a variant-selectivity question](https://your-dashboard-url/findings/cb-nps-polymorphism-001).** Gold (`NPSv18.9`, 277× variant-selective) carries one mechanism-specific feature — a long ~30-atom lipidation arm at K11 that reaches the polymorphic residue. Both agents pick `NPSv5.4`, which carries the canonical "D-aa scatter + palmitoyl" optimization template. That template is documented for half-life and protease stability, not for variant selectivity — but the agents conflate the two.
- **[MCH: agents trust Bednarek's analog; native hMCH wins 30×](https://your-dashboard-url/findings/cb-mch-disulfide-vs-aromatic-001).** Bednarek 2001 compound 19 (a published cyclic-optimization analog) loses to native hMCH 19-mer by 30×. Both agents anchor on "this is the published optimized form" and don't look further.

**Agents pick by sequence length, not SAR, at narrow potency gaps.** Across 60 pairwise tasks, both agents are above chance at wide ratios and below chance at narrow ones. On the 15 hardest pairs, both agents make the *same wrong pick* on 6/6 of their joint failures.

- **[Pairwise potency: agents pick by length, not SAR, at narrow gaps](https://your-dashboard-url/findings/pairwise-sequence-calibration).** Length-cue dominates codex's failure profile (62%); pharmacophore-misapplied dominates claude's (55%).

---

## Where the agents diverge

**Codex fails, Claude performs well** 

Codex's traces are systematically shorter and less mechanistic. On `oxn-medium-006`, claude correctly identifies a D-Citrulline replacing a conserved Arg (combined D-stereochemistry + charge-loss at a pharmacophore residue → 14× potency penalty). Codex never mentions D-Citrulline.

**Claude fails, Codex performs well** 

Barring the obvious failure mode in which Claude Code refuses every other request with the word "peptide" (23% of claude's failures are AUP refusals on tasks codex completes), the comparison is much closer than aggregate scores suggest.

---

## Why our data shape is unusual

The examples above are a curated subset. Our **program lead selection** items, and the most discriminating items in each of the other categories, ship with golden reasoning traces derived from our fantastic medicinal chemists — every gold rationale is grounded in (a) author-year citation, (b) source-path reference to our assay records, or (c) explicit measurement claim with units. We've found that the models tend to take reasoning shortcuts (as described above) and fail to use deeper domain insights. It's especially difficult when the tasks require multiple of these logical inferences in sequence.

Capable is currently able to synthesize and test peptides in vitro and in vivo within **24 hours**. This enables us to retrospectively curate combinatorially many benchmark tasks. It also enables a highly accelerated biological RL environment.

---

## What's next

In the next year, drug development will start to integrate more AI tooling — both biological foundation models for target ID and design, and general-purpose coding agents like Codex that orchestrate them. We will be setting up a simple API for the models to run inference on the foundation models of their choice. At the moment, **neither Codex nor Claude currently considers the possibility of leveraging ESM-2 or Boltz-2** for design or classification tasks. We see this as a reasoning flaw — the agents don't have those models in their tool-mental-model — and we're building the API to fix it.

We have identified core reasoning failures of Codex in our preclinical peptide work. We also have active programs in small molecules and RNA therapeutics. As we move drugs toward IND, Phase I, and beyond, we anticipate continuing to collect rich feedback.

Our goal is to be the fastest drug-discovery company in the world. We're continuously improving our ability to automate our workflows — computationally and, eventually, in the wet lab. We are keen to continue providing insights on where the models currently fail, build benchmarks grounded in our data, and ultimately make Codex the best drug-discovery agent available today.

Let us know what you think!

— Melissa