## MetaGuard benchmark results

| Model | Overall | Spam | Hate Speech | Misinfo | Safe Content | Multi-Violation |
|-------|--------:|-----:|------------:|--------:|-------------:|----------------:|
| `anthropic/claude-3.5-haiku` | **0.829** | 0.876 | 0.781 | 0.838 | 0.812 | 0.835 |
| `openai/gpt-4o-mini` | **0.815** | 0.837 | 0.903 | 0.737 | 0.787 | 0.813 |
| `google/gemma-2-9b-it` | **0.628** | 0.533 | 0.810 | 0.700 | 0.451 | 0.647 |

### Task difficulty reference

| Task | Difficulty | Expected score range |
|------|-----------|---------------------|
| spam_detection | Easy | 0.82 – 0.99 |
| safe_content | Easy | 0.82 – 0.99 |
| hate_speech_detection | Medium | 0.65 – 0.90 |
| misinformation_detection | Medium | 0.65 – 0.90 |
| multi_violation_detection | Hard | 0.40 – 0.88 |

### Notes
- Adversarial cases apply a 30% difficulty penalty to partial-credit answers.
- Episode score uses a step-weighted mean (later steps count more).
- Success threshold: ≥ 0.70 per task.
- All rewards clamped strictly inside (0, 1) per OpenEnv spec.
