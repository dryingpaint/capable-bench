"""Modal-deployed ESM-2 scoring service for the variant-effect probe.

Two surfaces, one underlying class:
  - `EsmScorer.score` callable in-process via `.remote()` from the orchestrator
    (used by `scripts/run_esm_oracle_probe.py`).
  - HTTP endpoint at `/score_endpoint` for the agent-as-tool experiment, after
    `modal deploy capablebench/esm_modal_app.py`.

Metric: masked pseudo-log-likelihood per residue. For each position i in a
sequence of length L, mask position i, run a single forward pass, take
log p(true_aa_i | x_\\{i}). Average across positions. Higher = more natural
under the ESM-2 prior. The probe hypothesis is that the more potent peptide
in a pair has higher mean PLL.

Non-canonical residues (D-Xxx, N-Me-Xxx, HomoArg, Nle, [AEEA] linkers, etc.)
are stripped to the closest canonical L-amino acid before scoring. This is
lossy — pairs differing only in stereochemistry or methylation will tie.
"""
from __future__ import annotations

import re
from typing import Any

import modal


APP_NAME = "capable-bench-esm"


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.3.0",
        "transformers==4.41.2",
        "fastapi[standard]>=0.110",
        "pydantic>=2",
    )
)

app = modal.App(APP_NAME, image=image)


# ---------- Modification stripping ----------

_THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
}
_NONCANONICAL_TO_CANONICAL: dict[str, str] = {
    **{f"D-{k}": v for k, v in _THREE_TO_ONE.items()},
    **{f"N-Me-{k}": v for k, v in _THREE_TO_ONE.items()},
    **{f"alpha-Me-{k}": v for k, v in _THREE_TO_ONE.items()},
    "HomoArg": "R", "hArg": "R", "Har": "R",
    "Nle": "L", "Norleucine": "L",
    "Nva": "V", "Norvaline": "V",
    "Aib": "A",
    "Sar": "G",
    "Cit": "Q",
    "Orn": "K",
    "Hyp": "P",
    "Pyr": "Q",
    "pGlu": "Q",
    "Nw-Arg": "R",
}
_LINKER_TOKENS = {"AEEA", "Ahx", "PEG", "PEG2", "PEG4", "PEG8", "PEG12", "Lipid"}
_TERMINAL_TOKENS = {"Ac", "NH2", "H2N", "Boc", "Fmoc"}
_SALT_PATTERN = re.compile(r"\((?:Acetate|HCl|TFA|Salt|Free Acid)\)", re.IGNORECASE)
_CANONICAL_SET = set("ACDEFGHIKLMNPQRSTVWY")


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Split a modification string into typed tokens, respecting parens/brackets.

    Returns a list of (kind, value) where kind ∈ {"text", "paren", "bracket", "sep"}.
    Whitespace and "-" both collapse to a single ("sep", "-") between non-sep tokens.
    """
    tokens: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if buf:
            s = "".join(buf).strip()
            if s:
                tokens.append(("text", s))
            buf = []

    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "(":
            flush()
            j = text.find(")", i)
            if j < 0:
                buf.append(c)
                i += 1
                continue
            tokens.append(("paren", text[i + 1 : j].strip()))
            i = j + 1
        elif c == "[":
            flush()
            j = text.find("]", i)
            if j < 0:
                buf.append(c)
                i += 1
                continue
            tokens.append(("bracket", text[i + 1 : j].strip()))
            i = j + 1
        elif c in "- \t\n":
            flush()
            if not tokens or tokens[-1][0] != "sep":
                tokens.append(("sep", "-"))
            i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return tokens


def _lookup(name: str) -> str | None:
    return _NONCANONICAL_TO_CANONICAL.get(name) or _THREE_TO_ONE.get(name)


def strip_to_canonical(mod_string: str) -> tuple[str, list[str]]:
    """Reduce a modification string to a canonical 20-AA sequence.

    Handles three notations that coexist in our peptide data:
      - 1-letter runs:        "SFRNGVGTGMKKTSFQRAKS"
      - dashed 3-letter:      "Ac-Cys-Gly-Arg-Val-Tyr-Cys-NH2"
      - parenthesized mods:   "(D-Ser)FRNGVGTGMK(N-Me-Lys)..."
      - bracketed linkers:    "[AEEA]" (dropped)

    Bare multi-part modifiers across separators are recognized greedily
    (e.g. "D-Arg" → R, "N-Me-Lys" → K, "alpha-Me-Ser" → S).

    Returns (canonical_seq, dropped_tokens). dropped_tokens lists any
    parenthesized/bracketed names we couldn't map — useful for audit.
    """
    text = _SALT_PATTERN.sub("", mod_string)
    tokens = _tokenize(text)
    out: list[str] = []
    dropped: list[str] = []

    # Index of text tokens only (skip seps) for lookahead modifier matching.
    text_idx: list[int] = [k for k, (kind, _) in enumerate(tokens) if kind == "text"]
    text_idx_pos: dict[int, int] = {orig: rank for rank, orig in enumerate(text_idx)}

    i = 0
    while i < len(tokens):
        kind, val = tokens[i]
        if kind == "sep":
            i += 1
            continue
        if kind == "bracket":
            if val in _LINKER_TOKENS:
                i += 1
                continue
            mapped = _lookup(val)
            if mapped:
                out.append(mapped)
            else:
                dropped.append(val)
            i += 1
            continue
        if kind == "paren":
            mapped = _lookup(val)
            if mapped:
                out.append(mapped)
            else:
                dropped.append(val)
            i += 1
            continue
        # kind == "text"
        if val in _TERMINAL_TOKENS:
            i += 1
            continue
        # Try multi-text-token modifier (D-Arg = 2, N-Me-Lys / alpha-Me-Ser = 3).
        # Only fold across seps, not parens/brackets.
        matched_until: int | None = None
        matched_value: str | None = None
        for span in (3, 2):
            text_rank = text_idx_pos.get(i)
            if text_rank is None or text_rank + span > len(text_idx):
                continue
            end_text = text_idx[text_rank + span - 1]
            # All tokens between i and end_text must be text or sep
            ok = all(tokens[k][0] in ("text", "sep") for k in range(i, end_text + 1))
            if not ok:
                continue
            joined = "-".join(tokens[text_idx[text_rank + s]][1] for s in range(span))
            if joined in _NONCANONICAL_TO_CANONICAL:
                matched_value = _NONCANONICAL_TO_CANONICAL[joined]
                matched_until = end_text + 1
                break
        if matched_value is not None and matched_until is not None:
            out.append(matched_value)
            i = matched_until
            continue
        if val in _THREE_TO_ONE:
            out.append(_THREE_TO_ONE[val])
            i += 1
            continue
        kept = "".join(c for c in val.upper() if c in _CANONICAL_SET)
        if kept:
            out.append(kept)
        i += 1

    return "".join(out), dropped


# ---------- ESM-2 scoring service ----------


MODEL_NAME = "facebook/esm2_t33_650M_UR50D"


@app.cls(
    gpu="T4",
    timeout=600,
    scaledown_window=300,
    min_containers=0,
)
class EsmScorer:
    @modal.enter()
    def load(self) -> None:
        import torch
        from transformers import AutoModelForMaskedLM, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self._model = (
            AutoModelForMaskedLM.from_pretrained(MODEL_NAME).to("cuda").eval()
        )
        self._mask_id = self._tokenizer.mask_token_id

    @modal.method()
    def score(self, sequences: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for seq in sequences:
            if not seq:
                results.append(
                    {"sequence": seq, "length": 0, "mean_pll": None, "sum_pll": None}
                )
                continue
            mean_pll, sum_pll = self._pll(seq)
            results.append(
                {
                    "sequence": seq,
                    "length": len(seq),
                    "mean_pll": float(mean_pll),
                    "sum_pll": float(sum_pll),
                }
            )
        return results

    def _pll(self, seq: str) -> tuple[float, float]:
        torch = self._torch
        tokens = self._tokenizer(seq, return_tensors="pt").to("cuda")
        input_ids = tokens["input_ids"]
        attn = tokens["attention_mask"]
        L = input_ids.shape[1]
        residue_positions = list(range(1, L - 1))  # skip CLS, EOS
        if not residue_positions:
            return 0.0, 0.0
        batch = input_ids.repeat(len(residue_positions), 1)
        for row, pos in enumerate(residue_positions):
            batch[row, pos] = self._mask_id
        with torch.no_grad():
            logits = self._model(
                input_ids=batch,
                attention_mask=attn.repeat(len(residue_positions), 1),
            ).logits
        log_probs = torch.log_softmax(logits, dim=-1)
        true_ids = input_ids[0, residue_positions]
        per_pos = log_probs[
            torch.arange(len(residue_positions)), residue_positions, true_ids
        ]
        return per_pos.mean().item(), per_pos.sum().item()


# ---------- HTTP endpoint for the agent-as-tool experiment ----------


@app.function(timeout=600)
@modal.fastapi_endpoint(method="POST", label="esm-score")
def score_endpoint(payload: dict) -> dict:
    """POST {"sequences": [str, ...]} → {"results": [{"raw_input", "canonical_sequence", "dropped_tokens", "length", "mean_pll", "sum_pll"}, ...]}

    Each input is passed through `strip_to_canonical` first, so callers can
    POST raw modification strings (e.g. "(D-Ser)FRNGVGTGMK(N-Me-Lys)..."). The
    response includes the canonical sequence that was actually scored and any
    parenthesized/bracketed tokens that were dropped.
    """
    raw_sequences = payload.get("sequences") or []
    if not isinstance(raw_sequences, list) or not all(
        isinstance(s, str) for s in raw_sequences
    ):
        return {"error": "`sequences` must be a list of strings"}
    canonical = []
    dropped_per: list[list[str]] = []
    for s in raw_sequences:
        c, d = strip_to_canonical(s)
        canonical.append(c)
        dropped_per.append(d)
    scored = EsmScorer().score.remote(canonical)
    enriched = []
    for raw, can, drop, sc in zip(raw_sequences, canonical, dropped_per, scored):
        enriched.append(
            {
                **sc,
                "raw_input": raw,
                "canonical_sequence": can,
                "dropped_tokens": drop,
            }
        )
    return {"results": enriched}
