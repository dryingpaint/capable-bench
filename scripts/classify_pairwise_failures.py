"""Classify pairwise-task failures into reasoning-failure categories using
claude -p as the judge. AUP refusals are detected by regex before invoking
the LLM; all others are routed through the judge."""
from __future__ import annotations
import csv, json, re, subprocess, sys, time, yaml
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]
ANS = REPO / "data/answers"
TASKS = REPO / "data/tasks"
RUNS = REPO / "runs"
OUT_CSV = REPO / "docs/findings/pairwise-sequence-calibration/failure_classifications.csv"

CATEGORIES = [
    "aup_refusal",
    "length_or_complexity_cue",
    "pharmacophore_misapplied",
    "no_substantive_reasoning",
]

AUP_RE = re.compile(
    r"usage policy|violate.{0,40}policy|unable to respond|refuse",
    re.IGNORECASE,
)


def agent_of(cmd: str) -> str:
    cmd = (cmd or "").lower()
    return "codex" if "codex" in cmd else "claude" if "claude" in cmd else "?"


def latest_failure_run(tid: str, agent: str):
    tdir = RUNS / tid
    if not tdir.exists():
        return None
    for run in sorted(tdir.iterdir(), reverse=True):
        if not run.is_dir():
            continue
        rsum = run / "run_summary.json"
        if not rsum.exists():
            continue
        try:
            s = json.load(open(rsum))
        except Exception:
            continue
        if agent_of(s.get("command", "")) != agent:
            continue
        score = (s.get("grade") or {}).get("score")
        if score is None:
            continue
        return s
    return None


def extract_reasoning(trace_path: Path, max_chars: int = 3500) -> str:
    if not trace_path.exists():
        return ""
    text = trace_path.read_text(errors="replace")
    keep = []
    for line in text.splitlines():
        if "[assistant]" in line or "[reasoning]" in line:
            stripped = re.sub(r"^.*?\[(assistant|reasoning)\]\s*", "", line)
            stripped = re.sub(r"… \(\+\d+ chars\).*$", "…", stripped)
            if len(stripped.strip()) >= 20:
                keep.append(stripped)
    out = "\n".join(keep)
    return out[:max_chars]


def build_prompt(task_info, trace_snippet, agent_pick, gold):
    p1, p2 = task_info["pep1"], task_info["pep2"]
    return f"""You are categorizing why an AI agent FAILED on a peptide pairwise potency task.

The agent saw two peptides (sequence only, no measurements) and had to pick the more potent one. The agent picked WRONG.

Pick exactly ONE category that best describes the failure mode. Output ONLY the category name on a single line.

CATEGORIES:
- length_or_complexity_cue: The agent's reasoning leans on sequence length, scaffold size, or sheer number of modifications without engaging with specific residues, motifs, or mechanism.
- pharmacophore_misapplied: The agent invoked real SAR concepts (pharmacophore residues, stereochemistry, charge, motif positions, binding mechanism) but reached the wrong conclusion. This includes failures where the agent anchored on a literature reference, named compound, or scaffold annotation while still attempting mechanism-based reasoning.
- no_substantive_reasoning: The agent picked an answer without articulating biochemical reasoning; the trace contains only boilerplate, filesystem chatter, or one-line non-mechanistic claims.

TASK CONTEXT
Agent picked: {agent_pick}   (WRONG)
Gold answer: {gold}

Peptide 1 ({p1['peptide_id']}): {p1['modification']}
Peptide 2 ({p2['peptide_id']}): {p2['modification']}

AGENT REASONING TRACE
{trace_snippet}

Output exactly one of: length_or_complexity_cue, pharmacophore_misapplied, no_substantive_reasoning"""


def classify_via_claude(prompt: str) -> str:
    """Invoke claude -p as the judge. Use Haiku for speed/cost."""
    cmd = [
        "claude", "-p",
        "--model", "claude-haiku-4-5-20251001",
        "--permission-mode", "bypassPermissions",
        prompt,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=90,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    out = (result.stdout or "").strip().lower()
    # Pick the first matching category token
    for cat in CATEGORIES[1:]:  # skip aup_refusal (handled before)
        if cat in out:
            return cat
    # Fallback
    return f"UNCLASSIFIED:{out[:80]}"


def main() -> None:
    pairwise = sorted([f.stem for f in ANS.glob("pilot-peptide-pairwise-sequence-*.yaml")])

    # Build the full failure list
    failures = []  # list of dict
    for tid in pairwise:
        g = yaml.safe_load(open(ANS / f"{tid}.yaml"))
        gold = g["gold_top"][0]
        rows = list(csv.DictReader(open(TASKS / tid / "peptide_sequences.csv")))
        bucket = re.match(r"pilot-peptide-pairwise-sequence-(\w+)-(\w+)-", tid).group(2)
        family = re.match(r"pilot-peptide-pairwise-sequence-(\w+)-(\w+)-", tid).group(1).upper()
        for agent in ("claude", "codex"):
            s = latest_failure_run(tid, agent)
            if not s:
                continue
            score = (s.get("grade") or {}).get("score")
            if score is None or score >= 0.5:
                continue  # success or unscored
            # Pull pick
            ans_path = Path(s["run_dir"]) / "answer.json"
            pick = None
            try:
                a = json.load(open(ans_path))
                if isinstance(a, dict):
                    pick = a.get("selected_option")
            except Exception:
                pass
            trace_text = (Path(s["run_dir"]) / "agent_trace.txt").read_text(errors="replace") if (Path(s["run_dir"]) / "agent_trace.txt").exists() else ""
            failures.append({
                "tid": tid, "family": family, "bucket": bucket,
                "agent": agent, "pick": pick, "gold": gold,
                "pep1": rows[0], "pep2": rows[1],
                "raw_trace": trace_text,
                "trace_path": str(Path(s["run_dir"]) / "agent_trace.txt"),
            })

    print(f"Failures to classify: {len(failures)}")

    # Pass 1: AUP regex
    for f in failures:
        if AUP_RE.search(f["raw_trace"]):
            f["category"] = "aup_refusal"
        else:
            f["category"] = None

    aup_n = sum(1 for f in failures if f["category"] == "aup_refusal")
    print(f"AUP refusals (regex): {aup_n}")
    print(f"Remaining to LLM-judge: {len(failures) - aup_n}")

    # Pass 2: LLM judge for the rest
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    classified = 0
    t0 = time.time()
    for i, f in enumerate(failures, 1):
        if f["category"] is not None:
            continue
        snippet = extract_reasoning(Path(f["trace_path"]))
        if not snippet.strip():
            f["category"] = "no_substantive_reasoning"
            print(f"  [{i}/{len(failures)}] {f['agent']:<6s} {f['tid']:<50s}  -> no_substantive_reasoning (empty trace)")
            classified += 1
            continue
        prompt = build_prompt(f, snippet, f["pick"], f["gold"])
        cat = classify_via_claude(prompt)
        f["category"] = cat
        classified += 1
        elapsed = time.time() - t0
        print(f"  [{i}/{len(failures)}] {f['agent']:<6s} {f['tid']:<50s}  -> {cat}   ({elapsed:.0f}s elapsed)")

    # Write CSV
    with open(OUT_CSV, "w") as fh:
        w = csv.writer(fh)
        w.writerow(["task_id", "family", "bucket", "agent", "pick", "gold", "category"])
        for f in failures:
            w.writerow([f["tid"], f["family"], f["bucket"], f["agent"], f["pick"], f["gold"], f["category"]])
    print(f"\nWrote {OUT_CSV}")


if __name__ == "__main__":
    main()
