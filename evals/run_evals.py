"""Run the golden dataset: python -m evals.run_evals --limit 10 --repeats 1"""
import argparse
import hashlib
import json
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from evals.checks import answer_checks, passed, retrieval_metrics
from evals.judge import RUBRIC_VERSION, judge
from pensionqa import config
from pensionqa.llm import get_llm
from pensionqa.rag import answer
from pensionqa.retrieval import load_retriever

DATASETS = Path(__file__).parent / "datasets"
RESULTS = Path(__file__).parent / "results"
AGENT_ONLY = {"use_calculator", "ignore_injection"}   # run by evals/run_agent_evals.py


def load_cases(path: Path, subset: str | None = None, limit: int | None = None) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if subset == "smoke":
        cases = [c for c in cases if c.get("smoke")]
    return cases[:limit] if limit else cases


def git_commit() -> str:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                         stderr=subprocess.DEVNULL).strip()
        # uncommitted edits to tracked files mean this commit alone can't reproduce the run
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True,
                                        stderr=subprocess.DEVNULL).strip()
        return f"{commit}-dirty" if dirty else commit
    except Exception:
        return "unknown"


def dataset_sha256(path: Path) -> str:
    # hash the text, not the bytes: git checks the same file out with CRLF on Windows and LF on Linux
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:16]


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = config.PRICES.get(model, (0.0, 0.0))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def summarise(rows: list[dict]) -> dict:
    def mean(key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return round(statistics.mean(values), 3) if values else None

    judged = [r for r in rows if r.get("grounded") is not None]
    latencies = sorted(r["latency_ms"] for r in rows)
    return {
        "runs": len(rows),
        "pass_rate": mean("passed"),
        "recall_at_5": mean("recall_at_5"),
        "mrr": mean("mrr"),
        "hallucination_rate": round(sum(not r["grounded"] for r in judged) / len(judged), 3) if judged else None,
        "correctness": mean("correctness"),
        "source_quality": mean("source_quality"),
        "p95_latency_ms": latencies[int(0.95 * (len(latencies) - 1))] if latencies else None,
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 4),
    }


def run(args) -> dict:
    dataset = DATASETS / args.dataset
    cases = [c for c in load_cases(dataset, args.subset, args.limit) if c["expected_behaviour"] not in AGENT_ONLY]
    retriever, llm = load_retriever(), get_llm("answer")
    judge_llm = get_llm("judge") if args.judge else None
    rows = []
    for case in cases:
        for repeat in range(args.repeats):
            ans = answer(case["question"], retriever, llm)
            checks = answer_checks(case, ans)
            row = {
                "case_id": case["id"], "category": case["category"], "repeat": repeat,
                "answer": ans.text, "cited": ans.cited, "retrieved": [s["chunk_id"] for s in ans.sources],
                "checks": checks, "passed": passed(checks), "stop_reason": ans.stop_reason,
                **retrieval_metrics(case, ans),
                "latency_ms": ans.latency_ms,
                "cost_usd": cost_usd(config.ANSWER_MODEL, ans.input_tokens, ans.output_tokens),
            }
            if judge_llm and checks.get("answered"):
                grade = judge(case, ans, judge_llm)
                row.update({k: grade.get(k) for k in ("grounded", "correctness", "source_quality",
                                                       "unsupported_claims", "rationale", "error")})
                row["cost_usd"] += cost_usd(config.JUDGE_MODEL, *grade.get("judge_tokens", [0, 0]))
            rows.append(row)
            stopped = "" if ans.stop_reason == "end_turn" else f"  (stopped: {ans.stop_reason})"
            print(f"{case['id']:<12} run {repeat + 1}: {'PASS' if row['passed'] else 'FAIL'}{stopped}")

    outcomes = defaultdict(set)
    for r in rows:
        outcomes[r["case_id"]].add(r["passed"])
    categories = defaultdict(list)
    for r in rows:
        categories[r["category"]].append(r)
    return {
        "run_id": time.strftime("%Y%m%d-%H%M%S"),
        "meta": {
            "git_commit": git_commit(),
            "dataset": dataset.name,
            "dataset_sha256": dataset_sha256(dataset),
            "subset": args.subset, "cases": len(cases), "repeats": args.repeats,
            "llm_mode": config.LLM_MODE,   # "fake" runs must not look like real model results
            "answer_model": config.ANSWER_MODEL, "answer_effort": config.ANSWER_EFFORT,
            "judge_model": config.JUDGE_MODEL if args.judge else None, "rubric": RUBRIC_VERSION,
            "prompt_version": config.PROMPT_VERSION, "top_k": config.TOP_K,
        },
        "summary": summarise(rows),
        "by_category": {cat: summarise(rs) for cat, rs in sorted(categories.items())},
        "unstable_cases": sorted(cid for cid, seen in outcomes.items() if len(seen) > 1),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="golden_v1.jsonl")
    parser.add_argument("--subset", choices=["smoke"], default=None)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--no-judge", dest="judge", action="store_false")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    results = run(args)
    out = Path(args.out) if args.out else RESULTS / f"{results['run_id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results["summary"], indent=2))
    print("unstable:", results["unstable_cases"] or "none", "| saved", out)


if __name__ == "__main__":
    main()
