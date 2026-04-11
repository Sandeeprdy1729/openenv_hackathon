#!/usr/bin/env python3
"""
benchmark_models.py — run inference.py across multiple models and summarize scores.

This script keeps credentials in the environment and never writes API keys to disk.
"""

from __future__ import annotations

import argparse
import os
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


START_RE = re.compile(r"^\[START\]\s+task=(?P<task>\S+)\s+env=(?P<env>\S+)\s+model=(?P<model>.+)$")
END_RE = re.compile(
    r"^\[END\]\s+success=(?P<success>\w+)\s+steps=(?P<steps>\d+)\s+score=(?P<score>\d+\.\d+)\s+rewards=(?P<rewards>.*)$"
)


@dataclass
class TaskResult:
    task: str
    success: bool
    steps: int
    score: float


@dataclass
class ModelResult:
    model: str
    tasks: List[TaskResult]
    raw_output: str

    @property
    def average_score(self) -> float:
        return statistics.mean(task.score for task in self.tasks) if self.tasks else 0.0

    @property
    def success_rate(self) -> float:
        return sum(1 for task in self.tasks if task.success) / len(self.tasks) if self.tasks else 0.0

    @property
    def fallback_count(self) -> int:
        return self.raw_output.count("falling back to")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark one or more chat models against ad_integrity.")
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="One or more model identifiers, e.g. anthropic/claude-3.5-haiku openai/gpt-4o-mini",
    )
    parser.add_argument(
        "--inference-script",
        default=str(Path(__file__).with_name("inference.py")),
        help="Path to inference.py",
    )
    parser.add_argument(
        "--output-markdown",
        default="",
        help="Optional path to write a markdown benchmark report.",
    )
    parser.add_argument(
        "--log-dir",
        default="benchmark_logs",
        help="Directory to store raw per-model transcripts.",
    )
    parser.add_argument(
        "--require-remote",
        action="store_true",
        help="Fail the run if a remote model call falls back instead of succeeding.",
    )
    return parser.parse_args()


def safe_model_filename(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model)


def run_inference(inference_script: str, model: str, require_remote: bool, log_dir: Path) -> ModelResult:
    env = os.environ.copy()
    env["MODEL_NAME"] = model
    env["REQUIRE_REMOTE_MODEL"] = "1" if require_remote else "0"

    proc = subprocess.run(
        [sys.executable, inference_script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    output = proc.stdout.strip()
    if proc.stderr.strip():
        output = f"{output}\n{proc.stderr.strip()}".strip()

    current_task = ""
    results: List[TaskResult] = []

    for line in output.splitlines():
        start_match = START_RE.match(line.strip())
        if start_match:
            current_task = start_match.group("task")
            continue

        end_match = END_RE.match(line.strip())
        if end_match:
            results.append(
                TaskResult(
                    task=current_task or f"task_{len(results) + 1}",
                    success=end_match.group("success").lower() == "true",
                    steps=int(end_match.group("steps")),
                    score=float(end_match.group("score")),
                )
            )

    if not results:
        raise RuntimeError(f"Could not parse benchmark output for model {model!r}.\n\n{output}")

    log_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = log_dir / f"{safe_model_filename(model)}.txt"
    transcript_path.write_text(output + "\n", encoding="utf-8")

    return ModelResult(model=model, tasks=results, raw_output=output)


def render_markdown(results: List[ModelResult]) -> str:
    lines = [
        "## Model Benchmark Results",
        "",
        "| Model | Avg Score | Success Rate | Task Scores |",
        "|------|-----------:|-------------:|------------|",
    ]

    for result in results:
        task_scores = ", ".join(f"{task.task}={task.score:.3f}" for task in result.tasks)
        lines.append(
            f"| `{result.model}` | {result.average_score:.3f} | {result.success_rate:.0%} | {task_scores} |"
        )

    lines.extend(
        [
            "",
            "### Benchmark Notes",
            "",
            "- Scores are episode scores reported by `inference.py` for the 5 OpenEnv tasks.",
            "- Each task score is clamped to stay strictly inside `(0, 1)` for submission validation.",
            "- Success rate is the fraction of tasks whose final score met the benchmark success threshold.",
        ]
    )
    return "\n".join(lines)


def render_console_summary(results: List[ModelResult]) -> str:
    rows = ["MODEL BENCHMARK SUMMARY", ""]
    for result in results:
        rows.append(
            f"{result.model}: avg={result.average_score:.3f} "
            f"success_rate={result.success_rate:.0%} "
            f"fallbacks={result.fallback_count} "
            f"tasks={[f'{task.task}:{task.score:.3f}' for task in result.tasks]}"
        )
    return "\n".join(rows)


def main() -> None:
    args = parse_args()

    missing = [name for name in ("API_BASE_URL", "API_KEY", "ENV_BASE_URL") if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")

    log_dir = Path(args.log_dir)
    all_results = [run_inference(args.inference_script, model, args.require_remote, log_dir) for model in args.models]

    console_summary = render_console_summary(all_results)
    print(console_summary)
    print()

    markdown = render_markdown(all_results)
    print(markdown)

    if args.output_markdown:
        output_path = Path(args.output_markdown)
        output_path.write_text(markdown + "\n", encoding="utf-8")
        print(f"\nWrote markdown report to {output_path}")

    print(f"Wrote raw transcripts to {log_dir}")


if __name__ == "__main__":
    main()
