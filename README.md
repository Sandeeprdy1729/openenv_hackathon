---
title: Ad Integrity OpenEnv
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
---

# 🛡️ Ad Integrity — OpenEnv Benchmark

> **A real-world content moderation RL environment** where an AI agent reviews social media advertisements and decides whether to `APPROVE`, `REJECT`, or `FLAG` each ad.

Built for the **Meta PyTorch RL Hackathon** by **Team RL Meta**.

---

## 🎯 Problem Statement

Content moderation at scale is one of the hardest challenges facing social media platforms. Human moderators face thousands of ads per day — many with subtle policy violations. This environment benchmarks whether an LLM agent can perform **accurate, consistent, and fast** ad moderation across 5 task categories.

The benchmark is intentionally designed to avoid trivial shortcutting:
- Agent-visible prompts include only the ad text and moderation objective.
- Backend-only metadata such as category, severity, and flags are hidden from the policy.
- Safe ads include urgency, discounts, and promotional language so models must separate legitimate marketing from spam.
- Harmful ads include softer dog whistles, pseudo-clinical claims, and mixed-signal copy rather than only obvious violations.

---

## 📋 Tasks (Easy → Hard)

| Task | Description | Correct Action | Difficulty |
|------|-------------|---------------|------------|
| `spam_detection` | Phishing, prize scams, suspicious links, and borderline get-rich-quick offers | REJECT / FLAG | Medium |
| `hate_speech_detection` | Slurs, discrimination, dehumanization | REJECT | Medium |
| `misinformation_detection` | False medical claims, pseudoscience, conspiracy, and softer wellness claims | REJECT / FLAG | Hard |
| `safe_content` | Legitimate brand ads, including promotional urgency, discounts, and free offers | APPROVE | Medium |
| `multi_violation_detection` | Multiple simultaneous policy violations and borderline mixed-signal cases | REJECT / FLAG | Hard |

---

## 🔧 Action Space

| Action | Meaning |
|--------|---------|
| `approve` | Ad is safe and follows all guidelines |
| `reject` | Ad violates policy — remove immediately |
| `flag` | Borderline — escalate to human review |

---

## 🏆 Reward Function

| Agent Decision | Correct Answer | Reward |
|----------------|---------------|--------|
| exact `reject` on harmful content | `reject` | high reward, severity-weighted, capped below 1.0 |
| exact `approve` on legitimate content | `approve` | high reward, slightly lower than severe rejects |
| exact `flag` on ambiguous content | `flag` | solid reward for calibrated escalation |
| `flag` on `reject` | `reject` | partial credit |
| `reject` on `flag` | `flag` | partial credit |
| `reject` on `approve` | `approve` | low reward for over-censorship |
| `approve` on `reject` | `reject` | near-floor reward, worst-case miss |

**Design notes**
- Exact matches are rewarded differently for `approve`, `reject`, and `flag` so the benchmark can separate model behavior on ambiguous cases.
- Adversarial cases apply a light penalty to partial-credit outcomes, which makes “flag everything” weaker than actual reasoning.
- Episode scores are aggregated from step rewards and kept strictly inside `(0, 1)` to satisfy OpenEnv validation.

---

## 🚀 Setup

```bash
# Clone and install
git clone https://github.com/Sandeeprdy1729/openenv_hackathon
cd openenv_hackathon
uv sync

# Start the environment server
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

---

## 🤖 Running Benchmark

```bash
export API_BASE_URL="https://openrouter.ai/api/v1"
export API_KEY="your_openrouter_key"
export MODEL_NAME="anthropic/claude-3.5-haiku"
export ENV_BASE_URL="http://localhost:8000"

python inference.py
```

You can also use Hugging Face router or any OpenAI-compatible endpoint:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export HF_TOKEN="hf_your_token_here"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
python inference.py
```

## 📊 Benchmark Multiple Models

Use the benchmark runner to compare several models and generate a markdown report:

```bash
export API_BASE_URL="https://openrouter.ai/api/v1"
export API_KEY="your_openrouter_key"
export ENV_BASE_URL="http://localhost:8000"

python inference.py \
  --models \
  anthropic/claude-3.5-haiku \
  openai/gpt-4o-mini \
  google/gemma-2-9b-it \
  --episodes 5 \
  --output-markdown benchmark_results.md
```

The script prints a console summary and writes a markdown report you can reuse in the README.
All model runs are logged in `benchmark_logs/` to keep evaluation transparent and reproducible across providers.

### Current Benchmark Results

| Rank | Model | Overall | Success Rate | Task Scores |
|------|-------|--------:|-------------:|------------|
| 1 | `anthropic/claude-3.5-haiku` | 0.829 | 100% | spam=0.876, hate=0.781, misinfo=0.838, safe=0.812, multi=0.835 |
| 2 | `openai/gpt-4o-mini` | 0.815 | 100% | spam=0.837, hate=0.903, misinfo=0.737, safe=0.787, multi=0.813 |
| 3 | `google/gemma-2-9b-it` | 0.628 | 40% | spam=0.533, hate=0.810, misinfo=0.700, safe=0.451, multi=0.647 |

### Benchmark Highlights

- `claude-3.5-haiku` ranked first overall with the most balanced performance across all 5 tasks.
- `gpt-4o-mini` led on `hate_speech_detection` but trailed Claude on spam, misinformation, safe-content calibration, and multi-violation handling.
- `gemma-2-9b-it` remained competitive on hate-speech and misinformation, but underperformed on spam and safe-content, dropping its task success rate to 2/5.
- The current benchmark meaningfully separates model behavior on ambiguous `flag` cases and adversarial safe ads instead of collapsing everything to the same near-perfect score.




### Adversarial Case Accuracy

| Model | Spam | Hate Speech | Misinfo | Safe Content | Multi-Violation |
|------|-----:|------------:|--------:|-------------:|----------------:|
| `anthropic/claude-3.5-haiku` | 40% | 70% | 50% | 100% | 60% |
| `openai/gpt-4o-mini` | 50% | 50% | 40% | 100% | 70% |
| `google/gemma-2-9b-it` | 67% | 30% | 43% | 25% | 70% |

### Result Notes

- Success threshold is `avg >= 0.70` per task.
- Scores are produced from 5 episodes per task using the current calibrated reward function.
- Adversarial difficulty penalties apply only to partial-credit answers on tricky near-miss cases.

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start a new episode (pass `{"task_id": "spam_detection"}`) |
| POST | `/step` | Take an action (pass `{"action": "reject"}`) |
| POST | `/state` | Get current environment state |
| GET | `/health` | Health check |
| GET | `/tasks` | List all available tasks |

---

## 🐳 Docker

```bash
docker build -t ad-integrity .
docker run -p 8000:8000 ad-integrity
```

---

## 📁 Project Structure

```
ad_integrity/
├── server/
│   ├── __init__.py
│   └── app.py                  # FastAPI server — all endpoints
├── tasks/
│   ├── __init__.py
│   ├── definitions.py          # Task metadata (id, description, difficulty)
│   └── graders.py              # Reward computation logic
├── models.py                   # Pydantic typed models (Action, Observation, State)
├── inference.py                # Agent benchmark script (required by OpenEnv)
├── openenv.yaml                # Environment manifest
├── Dockerfile                  # Docker build
├── pyproject.toml              # Dependencies
└── requirements.txt
```

---

## 🌍 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API endpoint | `https://openrouter.ai/api/v1` |
| `MODEL_NAME` | Model identifier | `anthropic/claude-3.5-haiku` |
| `API_KEY` | OpenRouter or OpenAI-compatible API key | — |
| `HF_TOKEN` | HuggingFace router API key (optional alternative) | — |
| `ENV_BASE_URL` | Environment server URL | `http://localhost:8000` |

---

## 👥 Team

**Team RL Meta**
- Sanjay Utchula
- Sandeep Thummala  
- Umesh Chandran Yenugula

---

## 📄 License

MIT
