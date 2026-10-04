# AI provider

The AI interpretation and the AI suggestions can be written by Gemini (the default) or through OpenRouter. The
deterministic analysis, scores and cache never depend on the provider: when the AI is unavailable the portfolio is
shown without it, whichever provider is selected.

## Choosing a provider

| Variable | Default | Meaning |
| --- | --- | --- |
| `AI_PROVIDER` | `gemini` | `gemini` or `openrouter` |
| `OPENROUTER_API_KEY` | none | Secret. Without it the AI layer reports `not_configured` |
| `OPENROUTER_MODEL` | `z-ai/glm-5.3-flash` | Primary model |
| `OPENROUTER_FALLBACK_MODELS` | `openai/gpt-6-luna` | Comma separated, tried in order |
| `OPENROUTER_MAX_TOKENS` | `6000` | Output limit per request (thinking tokens count against it) |
| `OPENROUTER_TIMEOUT_SECONDS` | `60` | Per request |
| `AI_DAILY_CALL_LIMIT` | `500` | Provider calls per UTC day, every model attempt counts; `0` turns the cap off |

Switching is a configuration change only: set `AI_PROVIDER=openrouter` and `OPENROUTER_API_KEY` in the backend
environment and redeploy. Setting `AI_PROVIDER=gemini` (or removing the variable) returns to Gemini at any time.

## What the OpenRouter client does

- Sends the same prompts as the Gemini client (`app/prompts`), in JSON mode, and validates the answer with the same
  rules (`validate_interpretation_references`). Suggestions get their JSON schema in the instruction.
- Tries the models in order. A timeout, a 5xx/429/404 response, a cut-off answer (`finish_reason: length`) or an
  answer that fails validation moves on to the next model. Missing credit (HTTP 402) stops at once, because every
  model would fail the same way.
- If a model only returns the explanations in a different order, they are put back in the deterministic order. A
  skipped, invented or repeated signal is still rejected, so the grounding guarantee is unchanged.
- Logs one structured event per attempt (`openrouter.request.completed`: model, duration, result, token counts, cost,
  never the prompt or the answer).
- Stops calling the provider once `AI_DAILY_CALL_LIMIT` is reached; users then see the usual "rate limit" state of the
  AI tab while the analysis keeps working. The counter lives in the backend process and resets at 00:00 UTC (and on a
  restart), so it is a safety net and not an exact meter.

The existing `Gemini*` error classes are reused as the provider-neutral boundary errors, so the API error mapping and
the service layer are shared.

## Budget

Measured with `backend/scripts/compare_models.py` (see [model-comparison.md](model-comparison.md)), one
interpretation costs about $0.0006 to $0.0013 with the default models, so $10 of credit is roughly 8,000 to
16,000 interpretations. Cached interpretations are reused and cost nothing. Recommended safeguards:

1. Create a dedicated OpenRouter key with a **credit limit** (for example $10) and only put that key in Render.
2. Keep `AI_DAILY_CALL_LIMIT` at a value you are comfortable paying for every day (500 calls is at most about $0.65).
3. Watch the OpenRouter activity page for the first days.
