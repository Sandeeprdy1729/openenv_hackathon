"""
inference.py — MetaGuard benchmark runner.

Evaluates LLMs on the 5 ad moderation tasks and reports
per-task scores, adversarial case accuracy, and overall rankings.

Usage
-----
python inference.py
python inference.py --models anthropic/claude-3.5-haiku openai/gpt-4o-mini
python inference.py --episodes 5 --output-markdown results.md
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY      = os.getenv("API_KEY") or os.getenv("HF_TOKEN", "")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

TASK_IDS = [
    "spam_detection",
    "hate_speech_detection",
    "misinformation_detection",
    "safe_content",
    "multi_violation_detection",
]

DEFAULT_MODELS = [
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o-mini",
    "google/gemma-2-9b-it",
]

OPENROUTER_PREFIXES = ("anthropic/", "openai/", "google/", "meta-llama/", "mistralai/")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    task_id: str
    episode_scores: list[float] = field(default_factory=list)
    adversarial_correct: int = 0
    adversarial_total: int = 0

    @property
    def avg_score(self) -> float:
        return round(sum(self.episode_scores) / len(self.episode_scores), 4) if self.episode_scores else 0.0

    @property
    def adversarial_accuracy(self) -> Optional[float]:
        if self.adversarial_total == 0:
            return None
        return round(self.adversarial_correct / self.adversarial_total, 3)


@dataclass
class ModelResult:
    model: str
    task_results: dict[str, TaskResult] = field(default_factory=dict)

    @property
    def overall_avg(self) -> float:
        scores = [r.avg_score for r in self.task_results.values()]
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    @property
    def success_rate(self) -> float:
        passing = sum(1 for r in self.task_results.values() if r.avg_score >= 0.70)
        return round(passing / len(self.task_results), 3) if self.task_results else 0.0


# ---------------------------------------------------------------------------
# Environment client
# ---------------------------------------------------------------------------

class EnvClient:
    def __init__(self, base_url: str = ENV_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30)

    def reset(self, task_id: str) -> dict:
        r = self._client.post(f"{self.base_url}/reset", json={"task_id": task_id})
        r.raise_for_status()
        return r.json()

    def step(self, action: str) -> dict:
        r = self._client.post(f"{self.base_url}/step", json={"action": action})
        r.raise_for_status()
        return r.json()

    def state(self) -> dict:
        r = self._client.post(f"{self.base_url}/state")
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# LLM agent
# ---------------------------------------------------------------------------

def query_model(model: str, prompt: str) -> str:
    """Send a prompt to the model via OpenRouter/HF and extract the action."""
    if not API_KEY or API_KEY == "your_openrouter_key":
        raise RuntimeError(
            "Missing valid API key. Set API_KEY for OpenRouter or HF_TOKEN for Hugging Face Router."
        )

    if "router.huggingface.co" in API_BASE_URL and model.startswith(OPENROUTER_PREFIXES):
        raise RuntimeError(
            f"Model '{model}' uses an OpenRouter-style ID, but API_BASE_URL is set to Hugging Face Router. "
            "Use https://openrouter.ai/api/v1 for anthropic/openai/google/meta-llama/mistralai model IDs."
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert content moderation AI. "
                    "Your job is to review advertisements and decide whether to approve, reject, or flag them. "
                    "Be precise — only respond with one word: approve, reject, or flag."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 10,
        "temperature": 0.0,
    }

    try:
        r = httpx.post(
            f"{API_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip().lower()
        # Extract first valid action word from response
        match = re.search(r"\b(approve|reject|flag)\b", raw)
        return match.group(1) if match else "flag"
    except Exception as e:
        if isinstance(e, httpx.HTTPStatusError):
            status = e.response.status_code
            body = ""
            try:
                body = e.response.text
            except Exception:
                body = ""

            if status in (401, 403):
                raise RuntimeError(
                    f"Authentication failed for {API_BASE_URL}. "
                    "Check API_KEY/HF_TOKEN and export a real secret before benchmarking."
                ) from e

            if status == 400 and "model_not_found" in body:
                raise RuntimeError(
                    f"Model '{model}' is not available on {API_BASE_URL}. "
                    "Use a provider-compatible model ID or switch API_BASE_URL."
                ) from e

        detail = ""
        if isinstance(e, httpx.HTTPStatusError):
            try:
                detail = f" | response={e.response.text[:400]}"
            except Exception:
                detail = ""
        print(f"    [warn] model query failed: {e}{detail} — defaulting to 'flag'", file=sys.stderr)
        return "flag"


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_task(
    model: str,
    task_id: str,
    episodes: int,
    client: EnvClient,
    verbose: bool = False,
) -> TaskResult:
    result = TaskResult(task_id=task_id)

    for ep in range(episodes):
        reset_result = client.reset(task_id)
        obs = reset_result.get("observation", reset_result)
        episode_rewards = []
        done = False

        while not done:
            prompt = obs.get("text", "")
            action = query_model(model, prompt)

            if verbose:
                ad_snippet = obs.get("ad_content", "")[:80].replace("\n", " ")
                print(f"      step — action={action!r}  ad='{ad_snippet}...'")

            step_result = client.step(action)
            reward   = step_result.get("reward", 0.0)
            done     = step_result.get("done", True)
            info     = step_result.get("info", {})
            obs      = step_result.get("observation", {})

            episode_rewards.append(reward)

            # Track adversarial case accuracy
            if info.get("adversarial"):
                result.adversarial_total += 1
                correct = info.get("correct_action")
                if correct and action == correct:
                    result.adversarial_correct += 1

        # Get final episode score from state
        state = client.state()
        ep_score = state.get("episode_score") or (
            sum(episode_rewards) / len(episode_rewards) if episode_rewards else 0.0
        )
        result.episode_scores.append(ep_score)

    return result


def run_benchmark(
    models: list[str],
    episodes: int = 3,
    verbose: bool = False,
) -> list[ModelResult]:
    client = EnvClient()
    results = []

    for model in models:
        print(f"\n  [{model}]")
        model_result = ModelResult(model=model)

        for task_id in TASK_IDS:
            print(f"    {task_id} ({episodes} episodes)...", end=" ", flush=True)
            try:
                task_result = run_task(model, task_id, episodes, client, verbose)
            except RuntimeError as exc:
                print(f"\n    [error] {exc}")
                print("    stopping benchmark early because this model/provider configuration is invalid.")
                raise
            model_result.task_results[task_id] = task_result
            adv_str = ""
            if task_result.adversarial_accuracy is not None:
                adv_str = f"  adv={task_result.adversarial_accuracy:.0%}"
            print(f"avg={task_result.avg_score:.3f}{adv_str}")

        print(f"    → overall avg={model_result.overall_avg:.3f}  success_rate={model_result.success_rate:.0%}")
        results.append(model_result)

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

DIFFICULTY = {
    "spam_detection": "Easy",
    "hate_speech_detection": "Medium",
    "misinformation_detection": "Medium",
    "safe_content": "Easy",
    "multi_violation_detection": "Hard",
}


def print_summary(results: list[ModelResult]) -> None:
    print("\n" + "=" * 70)
    print("MODEL BENCHMARK SUMMARY")
    print("=" * 70)
    for r in sorted(results, key=lambda x: x.overall_avg, reverse=True):
        task_scores = "  ".join(
            f"{tid}:{tr.avg_score:.3f}"
            for tid, tr in r.task_results.items()
        )
        print(
            f"{r.model}: "
            f"avg={r.overall_avg:.3f}  "
            f"success={r.success_rate:.0%}  "
            f"| {task_scores}"
        )


def write_markdown(results: list[ModelResult], path: str) -> None:
    lines = [
        "## MetaGuard benchmark results\n",
        "| Model | Overall | Spam | Hate Speech | Misinfo | Safe Content | Multi-Violation |",
        "|-------|--------:|-----:|------------:|--------:|-------------:|----------------:|",
    ]

    for r in sorted(results, key=lambda x: x.overall_avg, reverse=True):
        scores = [r.task_results.get(tid, TaskResult(tid)).avg_score for tid in TASK_IDS]
        row = (
            f"| `{r.model}` "
            f"| **{r.overall_avg:.3f}** "
            + "".join(f"| {s:.3f} " for s in scores)
            + "|"
        )
        lines.append(row)

    lines += [
        "",
        "### Task difficulty reference",
        "",
        "| Task | Difficulty | Expected score range |",
        "|------|-----------|---------------------|",
        "| spam_detection | Easy | 0.82 – 0.99 |",
        "| safe_content | Easy | 0.82 – 0.99 |",
        "| hate_speech_detection | Medium | 0.65 – 0.90 |",
        "| misinformation_detection | Medium | 0.65 – 0.90 |",
        "| multi_violation_detection | Hard | 0.40 – 0.88 |",
        "",
        "### Notes",
        "- Adversarial cases apply a 30% difficulty penalty to partial-credit answers.",
        "- Episode score uses a step-weighted mean (later steps count more).",
        "- Success threshold: ≥ 0.70 per task.",
        "- All rewards clamped strictly inside (0, 1) per OpenEnv spec.",
    ]

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nWrote markdown to {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MetaGuard benchmark runner")
    p.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    p.add_argument("--episodes", type=int, default=3, help="Episodes per task per model")
    p.add_argument("--output-markdown", metavar="PATH", help="Write results markdown to file")
    p.add_argument("--verbose", action="store_true", help="Print per-step actions")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print(f"MetaGuard benchmark — {len(args.models)} model(s), {args.episodes} episode(s)/task")
    print(f"  env: {ENV_BASE_URL}")
    print(f"  api: {API_BASE_URL}")

    results = run_benchmark(args.models, args.episodes, args.verbose)
    print_summary(results)

    if args.output_markdown:
        write_markdown(results, args.output_markdown)
