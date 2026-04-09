---
title: Ad Moderation Environment
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: docker
app_port: 8000
---

# Ad Moderation OpenEnv Benchmark

An OpenEnv-compliant environment for content moderation benchmarking.

## Tasks

| Task | Description | Ideal Action |
|------|-------------|--------------|
| `spam_detection` | Detect and remove spam advertisements | reject |
| `hate_speech_detection` | Detect and remove hate speech content | reject |
| `misinformation_detection` | Detect false or misleading claims | reject |
| `safe_content` | Approve legitimate advertisements | approve |

## Setup

```bash
uv sync
cp .env.example .env
uv run server
```

## Running Inference

```bash
python inference.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| API_BASE_URL | LLM API endpoint | https://router.huggingface.co/v1 |
| MODEL_NAME | Model identifier | Qwen/Qwen2.5-72B-Instruct |
| HF_TOKEN | HuggingFace API key | - |
| LOCAL_IMAGE_NAME | Docker image for env | - |
| ENV_BASE_URL | Environment server URL | http://localhost:8000 |

## Project Structure

```
ad_integrity/
├── tasks/
│   ├── __init__.py
│   ├── definitions.py    # Task definitions
│   └── graders.py       # Reward grading
├── server/
│   ├── __init__.py
│   ├── app.py           # FastAPI server using create_app
│   └── ad_moderation_environment.py
├── models.py            # Pydantic schemas
├── client.py           # EnvClient wrapper
├── inference.py        # Benchmark script
├── openenv.yaml        # Environment manifest
└── pyproject.toml      # Dependencies
```

## License

MIT | Team RL Meta
