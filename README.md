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

---

## 📋 Tasks (Easy → Hard)

| Task | Description | Correct Action | Difficulty |
|------|-------------|---------------|------------|
| `spam_detection` | Phishing, prize scams, suspicious links | REJECT | Easy |
| `hate_speech_detection` | Slurs, discrimination, dehumanization | REJECT | Medium |
| `misinformation_detection` | False medical claims, pseudoscience, conspiracy | REJECT | Medium |
| `safe_content` | Legitimate brand advertising, no violations | APPROVE | Easy |
| `multi_violation_detection` | Multiple simultaneous policy violations | REJECT | Hard |

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
| correct | correct | **1.0 × severity_multiplier** |
| flag | reject | 0.4 (noticed problem, not decisive) |
| flag | approve | 0.5 (overly cautious) |
| reject | approve | 0.1 (over-censorship) |
| approve | reject | **0.0** (worst — harmful content passes) |

**Severity multipliers**: low=1.0, medium=1.1, high=1.2, critical=1.3  
**Speed bonus**: +0.05 per remaining step for fast correct decisions

All rewards clamped to **[0.0, 1.0]**.

---

## 🚀 Setup

```bash
# Clone and install
git clone https://github.com/Sandeeprdy1729/openenv_hackathon
cd openenv_hackathon
uv sync

# Copy env file and fill in your tokens
cp .env.example .env

# Start the environment server
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

---

## 🤖 Running Inference

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="hf_your_token_here"
export ENV_BASE_URL="http://localhost:8000"

python inference.py
```

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
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `Qwen/Qwen2.5-72B-Instruct` |
| `HF_TOKEN` | HuggingFace API key | — |
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