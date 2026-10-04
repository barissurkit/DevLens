# Comparing language models (blind)

`backend/scripts/compare_models.py` sends the **real DevLens interpretation prompt** (the production system
instruction and the context of a recorded portfolio) to several models through [OpenRouter](https://openrouter.ai),
and shows the answers side by side **without the model names**, so the writing can be judged on its own.

For every answer it also runs the checks the application runs: valid JSON, the `PortfolioInterpretation` schema, and the
signal references (an explanation for every deterministic signal, in order; a model that skips one would be rejected in
production). It measures tokens (including "thinking" tokens), cost and time.

## Run it

From the `backend` folder, with the backend's virtual environment:

```powershell
# 1. Ids and prices only. No key needed, nothing is sent to a model.
python scripts/compare_models.py --check-models

# 2. The whole pipeline with canned answers. No key, no cost.
python scripts/compare_models.py --dry-run

# 3. The real comparison. The key is read from the environment only (never printed or saved).
$env:OPENROUTER_API_KEY = "sk-or-..."      # this window only
python scripts/compare_models.py
```

Then open `compare-out/index.html`, read the candidates, pick a favourite, and press **Modelleri göster**.
`compare-out/results.json` maps candidates to models; leave it closed until you have chosen.

Useful options: `--models a/b,c/d` (OpenRouter ids), `--reasoning low|minimal|none|medium|high|default` (effort sent to
models that think; `low` keeps the cost near the plain-output price), `--max-tokens` (thinking counts against it),
`--max-cost` (the run is refused up front if its worst case would cost more; default $0.60), `--seed` (rebuild the same
blind order).

## Cost

One request is about 2,900 input tokens plus up to `--max-tokens` output tokens. With the default list the whole run costs
a few cents. Give the API key a credit limit in the OpenRouter dashboard (a couple of dollars is plenty for this).

## What the numbers mean

- *Geçerli* is true only if the answer passed all three application checks.
- *Türkçe harf oranı* is a crude flag: the prompt demands Turkish, and a text with almost no Turkish letters was
  probably written in English. It says nothing about how good the Turkish is; that is what the blind reading is for.
- A model that does not accept the `reasoning` setting is asked again without it, and the page says so.
