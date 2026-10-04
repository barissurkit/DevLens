"""Blind comparison of language models on the real DevLens interpretation prompt, through OpenRouter.

Usage (from the ``backend`` directory):

    python scripts/compare_models.py --check-models          # ids and prices only, no key needed
    python scripts/compare_models.py --dry-run               # whole pipeline with canned answers, no key, no cost
    OPENROUTER_API_KEY=... python scripts/compare_models.py  # the real comparison

It builds the production system instruction and context for a recorded portfolio, sends the identical request to every
model, checks each answer with the same validation the application uses (valid JSON, the Pydantic schema, the
references to the deterministic signals), measures tokens, cost and time, and writes ``compare-out/index.html``:
the answers side by side as "Aday A, B, C..." in random order, so the models can be judged without knowing which is
which. A button reveals the models, their costs and checks. The API key is read from the environment only and is never
printed or written anywhere.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.gemini import GeminiInvalidResponseError, validate_interpretation_references  # noqa: E402
from app.prompts.portfolio_interpretation import SYSTEM_INSTRUCTION, build_interpretation_content  # noqa: E402
from app.schemas.analysis import GitHubPortfolioAnalysis  # noqa: E402
from app.schemas.interpretation import PortfolioInterpretation, PortfolioInterpretationContext  # noqa: E402
from app.services.portfolio_interpretation_context import build_portfolio_interpretation_context  # noqa: E402

API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "fixtures" / "portfolio.json"
DEFAULT_MODELS = [
    "openai/gpt-6-luna",
    "deepseek/deepseek-v4-pro",
    "qwen/qwen3.8-flash",
    "z-ai/glm-5.3-flash",
    "mistralai/mistral-small-2603",
    "meta/muse-spark-1.3-contributor",
    "google/gemini-3.6-flash",  # what production uses today, as the reference
]
TURKISH_LETTERS = "çğıöşüÇĞİÖŞÜ"


@dataclass
class Evaluation:
    json_valid: bool = False
    schema_valid: bool = False
    references_valid: bool = False
    issues: list[str] = field(default_factory=list)
    turkish_letter_ratio: float = 0.0
    summary_chars: int = 0
    explanation_count: int = 0
    interpretation: dict | None = None


@dataclass
class RunResult:
    model: str
    ok: bool
    error: str | None = None
    latency_seconds: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None
    finish_reason: str | None = None
    notes: list[str] = field(default_factory=list)
    evaluation: Evaluation = field(default_factory=Evaluation)

    @property
    def usable(self) -> bool:
        return self.ok and self.evaluation.json_valid and self.evaluation.schema_valid and self.evaluation.references_valid


# ---------------------------------------------------------------------------------------------------------------
# The request: exactly what production sends to its model.
# ---------------------------------------------------------------------------------------------------------------

def load_context(path: Path) -> PortfolioInterpretationContext:
    document = json.loads(path.read_text(encoding="utf-8"))
    analysis = GitHubPortfolioAnalysis.model_validate(document["analysis"])
    return build_portfolio_interpretation_context(analysis)


def build_messages(context: PortfolioInterpretationContext) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": build_interpretation_content(context)},
    ]


def build_body(model: str, messages: list[dict[str, str]], *, max_tokens: int, reasoning: str, with_reasoning: bool) -> dict:
    body: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        # The production prompt describes the JSON shape in words, so plain JSON mode matches what Gemini gets.
        "response_format": {"type": "json_object"},
        "usage": {"include": True},
    }
    if with_reasoning and reasoning != "default":
        body["reasoning"] = {"effort": reasoning}
    return body


def estimate_input_tokens(messages: list[dict[str, str]]) -> int:
    return round(sum(len(message["content"]) for message in messages) / 3.0)


# ---------------------------------------------------------------------------------------------------------------
# Checking an answer with the application's own validation.
# ---------------------------------------------------------------------------------------------------------------

def extract_json(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", stripped, flags=re.IGNORECASE)
    start, end = stripped.find("{"), stripped.rfind("}")
    return stripped[start : end + 1] if start != -1 and end > start else stripped


def evaluate(text: str, context: PortfolioInterpretationContext) -> Evaluation:
    result = Evaluation()
    try:
        data = json.loads(extract_json(text))
    except (json.JSONDecodeError, ValueError) as error:
        result.issues.append(f"Geçerli JSON değil: {error}")
        return result
    if not isinstance(data, dict):
        result.issues.append("JSON bir nesne değil.")
        return result
    result.json_valid = True
    try:
        interpretation = PortfolioInterpretation.model_validate(data)
    except Exception as error:  # pydantic.ValidationError, kept broad so one bad model cannot stop the run
        result.issues.append(f"Şema hatası: {str(error).splitlines()[0]}")
        result.interpretation = data
        return result
    result.schema_valid = True
    result.interpretation = interpretation.model_dump(mode="json")
    try:
        validate_interpretation_references(interpretation, context)
        result.references_valid = True
    except GeminiInvalidResponseError as error:
        result.issues.append(f"Referans hatası: {error}")

    prose = " ".join(
        [interpretation.summary]
        + [item.explanation for item in interpretation.strength_explanations + interpretation.improvement_explanations]
        + [value for value in (interpretation.technology_context, interpretation.project_area_context, interpretation.limitations_note) if value]
    )
    letters = [character for character in prose if character.isalpha()]
    result.turkish_letter_ratio = round(sum(character in TURKISH_LETTERS for character in letters) / max(1, len(letters)), 3)
    result.summary_chars = len(interpretation.summary)
    result.explanation_count = len(interpretation.strength_explanations) + len(interpretation.improvement_explanations)
    if result.turkish_letter_ratio < 0.03:
        result.issues.append("Metinde neredeyse hiç Türkçe harf yok; Türkçe yazılmamış olabilir.")
    return result


# ---------------------------------------------------------------------------------------------------------------
# Talking to OpenRouter.
# ---------------------------------------------------------------------------------------------------------------

async def fetch_catalog(client: httpx.AsyncClient) -> dict[str, dict]:
    response = await client.get(f"{API_BASE}/models", timeout=60)
    response.raise_for_status()
    return {item["id"]: item for item in response.json()["data"]}


def price_per_token(entry: dict | None) -> tuple[float, float]:
    if not entry:
        return 0.0, 0.0
    pricing = entry.get("pricing", {})
    try:
        return float(pricing["prompt"]), float(pricing["completion"])
    except (KeyError, TypeError, ValueError):
        return 0.0, 0.0


RETRY_FACTOR = 2.5
RETRY_CAP = 12000


def retry_limit(max_tokens: int) -> int:
    """The larger output limit for the one retry after an answer was cut off (thinking tokens count against it)."""
    return min(max(int(max_tokens * RETRY_FACTOR), max_tokens), max(RETRY_CAP, max_tokens))


async def run_model(
    client: httpx.AsyncClient,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    context: PortfolioInterpretationContext,
    catalog_entry: dict | None,
    *,
    max_tokens: int,
    reasoning: str,
    timeout: float,
    retry_on_length: bool = True,
) -> RunResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://devlens.barissurkit.com",
        "X-Title": "DevLens model comparison",
    }
    result = RunResult(model=model, ok=False)
    started = time.monotonic()
    try:
        response = await client.post(f"{API_BASE}/chat/completions", headers=headers, timeout=timeout,
                                     json=build_body(model, messages, max_tokens=max_tokens, reasoning=reasoning, with_reasoning=True))
        if response.status_code == 400 and "reasoning" in response.text.lower():
            # Some models do not accept the reasoning setting; ask again without it and say so.
            result.notes.append("Model 'reasoning' ayarını kabul etmedi; ayarsız yeniden denendi.")
            response = await client.post(f"{API_BASE}/chat/completions", headers=headers, timeout=timeout,
                                         json=build_body(model, messages, max_tokens=max_tokens, reasoning=reasoning, with_reasoning=False))
    except httpx.HTTPError as error:
        result.error = f"Bağlantı hatası: {type(error).__name__}"
        result.latency_seconds = round(time.monotonic() - started, 2)
        return result
    result.latency_seconds = round(time.monotonic() - started, 2)
    if response.status_code != 200:
        result.error = f"HTTP {response.status_code}: {response.text[:300]}"
        return result
    try:
        payload = response.json()
        choice = payload["choices"][0]
        text = choice["message"].get("content") or ""
    except (ValueError, KeyError, IndexError, TypeError):
        result.error = "Beklenmeyen yanıt biçimi."
        return result
    result.ok = True
    result.finish_reason = choice.get("finish_reason")
    usage = payload.get("usage") or {}
    result.prompt_tokens = usage.get("prompt_tokens")
    result.completion_tokens = usage.get("completion_tokens")
    result.reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if isinstance(usage.get("cost"), (int, float)):
        result.cost_usd = float(usage["cost"])
    elif result.prompt_tokens is not None and result.completion_tokens is not None:
        price_in, price_out = price_per_token(catalog_entry)
        result.cost_usd = round(result.prompt_tokens * price_in + result.completion_tokens * price_out, 6)
        result.notes.append("Maliyet katalog fiyatından hesaplandı.")
    if result.finish_reason == "length":
        result.notes.append("Yanıt max_tokens sınırında kesildi.")
    result.evaluation = evaluate(text, context)
    if not text.strip():
        result.evaluation.issues.append("Boş yanıt.")
    larger = retry_limit(max_tokens)
    if retry_on_length and result.finish_reason == "length" and not result.usable and larger > max_tokens:
        # Cut off before a usable answer (typically a thinking model): ask once more with more room, and keep both costs.
        retry = await run_model(client, api_key, model, messages, context, catalog_entry,
                                max_tokens=larger, reasoning=reasoning, timeout=timeout, retry_on_length=False)
        retry.notes = [*result.notes, f"İlk deneme {max_tokens} token sınırında kesildi; {larger} sınırıyla yeniden denendi.", *retry.notes]
        retry.cost_usd = round((result.cost_usd or 0.0) + (retry.cost_usd or 0.0), 6) if (result.cost_usd is not None or retry.cost_usd is not None) else None
        retry.latency_seconds = round(result.latency_seconds + retry.latency_seconds, 2)
        return retry
    return result


def canned_transport(context: PortfolioInterpretationContext) -> httpx.MockTransport:
    """Answers for ``--dry-run`` and the tests: no network, a valid answer for the given context."""

    # The application's validation wants an explanation for every deterministic signal, in order.
    strengths = [{"signal_key": signal.key, "explanation": f"{signal.key} sinyali birçok repository'de görülüyor."} for signal in context.strength_signals]
    improvements = [{"signal_key": signal.key, "explanation": f"{signal.key} birkaç repository'de eksik."} for signal in context.improvement_signals]
    recommendation = None
    if context.improvement_signals:
        recommendation = {
            "title": "Test ve CI odaklı küçük bir proje",
            "goal": "Eksik test ve CI sinyallerini tek bir projede örnek düzeye getirmek.",
            "rationale": "Bu sinyaller portföyde en çok eksik olan kanıtlardır.",
            "focus_signal_keys": [signal.key for signal in context.improvement_signals[:3]],
            "suggested_deliverables": ["Birim testleri", "CI iş akışı", "README'de test bölümü"],
        }
    answer = {
        "summary": "Portföy, düzenli README yapısı ve tutarlı hijyen pratikleriyle sağlam bir temel sunuyor; test ve otomasyon en çok gelişebilecek alan.",
        "strength_explanations": strengths,
        "improvement_explanations": improvements,
        "technology_context": None,
        "project_area_context": None,
        "limitations_note": "Yalnızca herkese açık repository'ler analiz edildi.",
        "next_project_recommendation": recommendation,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": model, "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}, "context_length": 1000000} for model in DEFAULT_MODELS]})
        body = json.loads(request.content)
        if body["model"].endswith("broken"):
            return httpx.Response(200, json={"choices": [{"message": {"content": "Üzgünüm, JSON veremiyorum."}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2700, "completion_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 300}, "cost": 0.0011},
        })

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------------------------------------------
# The blind page.
# ---------------------------------------------------------------------------------------------------------------

def blind_order(models: list[str], seed: str) -> list[str]:
    """A shuffled order that depends on the seed only, so the same run can be rebuilt."""
    order = list(models)
    random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16)).shuffle(order)
    return order


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_interpretation(data: dict) -> str:
    def section(title: str, body: str) -> str:
        return f"<section><h4>{escape(title)}</h4>{body}</section>" if body else ""

    def items(entries: list[dict]) -> str:
        return "<ul>" + "".join(f"<li><code>{escape(entry.get('signal_key'))}</code> {escape(entry.get('explanation'))}</li>" for entry in entries) + "</ul>" if entries else ""

    recommendation = data.get("next_project_recommendation")
    recommendation_html = ""
    if isinstance(recommendation, dict):
        deliverables = "".join(f"<li>{escape(item)}</li>" for item in recommendation.get("suggested_deliverables", []))
        recommendation_html = (
            f"<p><strong>{escape(recommendation.get('title'))}</strong></p><p>{escape(recommendation.get('goal'))}</p>"
            f"<p class='muted'>{escape(recommendation.get('rationale'))}</p><ul>{deliverables}</ul>"
        )
    return (
        section("Özet", f"<p>{escape(data.get('summary'))}</p>")
        + section("Güçlü yönler", items(data.get("strength_explanations", [])))
        + section("Gelişim alanları", items(data.get("improvement_explanations", [])))
        + section("Teknoloji bağlamı", f"<p>{escape(data.get('technology_context'))}</p>" if data.get("technology_context") else "")
        + section("Proje alanı bağlamı", f"<p>{escape(data.get('project_area_context'))}</p>" if data.get("project_area_context") else "")
        + section("Sınırlar", f"<p>{escape(data.get('limitations_note'))}</p>" if data.get("limitations_note") else "")
        + section("Sıradaki proje önerisi", recommendation_html)
    )


def label_for(index: int) -> str:
    return "Aday " + chr(ord("A") + index)


def render_page(results: list[RunResult], seed: str) -> str:
    by_model = {result.model: result for result in results}
    order = blind_order(list(by_model), seed)
    cards, reveal_rows = [], []
    for index, model in enumerate(order):
        result = by_model[model]
        label = label_for(index)
        if result.usable:
            body = render_interpretation(result.evaluation.interpretation or {})
        elif result.evaluation.interpretation and result.ok:
            body = "<p class='fail'>Çıktı uygulamanın doğrulamasından geçemedi; yine de aşağıda okunabilir.</p>" + render_interpretation(result.evaluation.interpretation)
        else:
            body = "<p class='fail'>Bu aday kullanılabilir bir çıktı üretemedi.</p>"
        cards.append(
            f"<article class='card' id='card-{index}'><header><h3>{escape(label)}</h3>"
            f"<label class='fav'><input type='radio' name='fav' value='{index}'> Favorim</label></header>{body}"
            f"<div class='reveal'><hr><p><strong>{escape(model)}</strong></p>{reveal_details(result)}</div></article>"
        )
        reveal_rows.append((result.cost_usd if result.cost_usd is not None else float("inf"), index, model, result))
    table_rows = "".join(
        f"<tr><td>{escape(label_for(index))}</td><td>{escape(model)}</td><td>{'evet' if result.usable else 'hayır'}</td>"
        f"<td>{'' if result.cost_usd is None else f'${result.cost_usd:.5f}'}</td><td>{escape(result.completion_tokens)}</td>"
        f"<td>{escape(result.reasoning_tokens)}</td><td>{result.latency_seconds:.1f} sn</td></tr>"
        for _, index, model, result in sorted(reveal_rows, key=lambda row: row[0])
    )
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DevLens model karşılaştırması</title>
<style>
body{{font:15px/1.55 system-ui,Segoe UI,sans-serif;margin:0;background:#f1f5f9;color:#0f172a}}
main{{max-width:1280px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:24px;margin:0 0 6px}} .muted{{color:#64748b}}
.grid{{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));margin-top:20px}}
.card{{background:#fff;border:1px solid #cbd5e1;border-radius:14px;padding:16px 18px}}
.card header{{display:flex;justify-content:space-between;align-items:center}}
.card h3{{margin:0;font-size:18px}} h4{{margin:14px 0 4px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#475569}}
ul{{padding-left:20px;margin:4px 0}} code{{background:#eef2ff;border-radius:4px;padding:0 4px;font-size:12px}}
.fail{{color:#b45309;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 10px}}
.fav{{font-size:13px;cursor:pointer}} .reveal{{display:none}} body.revealed .reveal{{display:block}}
button{{background:#4f46e5;color:#fff;border:0;border-radius:10px;padding:10px 16px;font-size:15px;cursor:pointer}}
table{{border-collapse:collapse;width:100%;margin-top:16px;background:#fff;display:none}} body.revealed table{{display:table}}
td,th{{border:1px solid #e2e8f0;padding:6px 10px;text-align:left;font-size:13px}} .issue{{color:#b45309;font-size:13px}}
</style></head><body><main>
<h1>DevLens model karşılaştırması (kör)</h1>
<p class="muted">Aynı istek {len(results)} modele gönderildi. Adaylar rastgele sırayla ve adsız gösteriliyor: önce okuyun, favorinizi seçin, sonra "Modelleri göster"e basın.</p>
<p><button type="button" onclick="document.body.classList.add('revealed')">Modelleri göster</button></p>
<div class="grid">{''.join(cards)}</div>
<table><thead><tr><th>Aday</th><th>Model</th><th>Geçerli</th><th>Maliyet</th><th>Çıktı token</th><th>Düşünme token</th><th>Süre</th></tr></thead><tbody>{table_rows}</tbody></table>
</main></body></html>"""


def reveal_details(result: RunResult) -> str:
    cost = "bilinmiyor" if result.cost_usd is None else f"${result.cost_usd:.5f}"
    rows = [
        f"Maliyet: {cost} · süre {result.latency_seconds:.1f} sn",
        f"Token: girdi {escape(result.prompt_tokens)} · çıktı {escape(result.completion_tokens)} · düşünme {escape(result.reasoning_tokens)}",
        f"Kontroller: JSON {'✓' if result.evaluation.json_valid else '✗'} · şema {'✓' if result.evaluation.schema_valid else '✗'} · referanslar {'✓' if result.evaluation.references_valid else '✗'}"
        f" · Türkçe harf oranı {result.evaluation.turkish_letter_ratio:.1%} · özet {result.evaluation.summary_chars} karakter",
    ]
    html_rows = "".join(f"<p class='muted'>{row}</p>" for row in rows)
    for text in [result.error, *result.evaluation.issues, *result.notes]:
        if text:
            html_rows += f"<p class='issue'>{escape(text)}</p>"
    return html_rows


# ---------------------------------------------------------------------------------------------------------------
# The command line.
# ---------------------------------------------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="comma separated OpenRouter model ids")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="a recorded analysis (the e2e fixture by default)")
    parser.add_argument("--out", type=Path, default=Path("compare-out"), help="output folder")
    parser.add_argument("--max-tokens", type=int, default=4000, help="output limit per request (thinking tokens count against it)")
    parser.add_argument("--reasoning", default="low", choices=["default", "none", "minimal", "low", "medium", "high"], help="reasoning effort sent to models that think")
    parser.add_argument("--max-cost", type=float, default=0.60, help="abort if the worst-case cost of the whole run exceeds this many dollars")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--seed", default=None, help="seed of the blind order (random by default)")
    parser.add_argument("--check-models", action="store_true", help="only check that the model ids exist and show their prices")
    parser.add_argument("--dry-run", action="store_true", help="use canned answers instead of the network; no key, no cost")
    return parser.parse_args(argv)


async def main_async(args: argparse.Namespace, transport: httpx.AsyncBaseTransport | None = None) -> int:
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    context = load_context(args.fixture)
    messages = build_messages(context)
    if transport is None and args.dry_run:
        transport = canned_transport(context)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not args.dry_run and not args.check_models and not api_key:
        print("OPENROUTER_API_KEY ortam değişkeni ayarlı değil. Önce --check-models veya --dry-run deneyebilirsiniz.", file=sys.stderr)
        return 2

    async with httpx.AsyncClient(transport=transport) as client:
        catalog = await fetch_catalog(client)
        input_tokens = estimate_input_tokens(messages)
        worst_case = 0.0
        print(f"İstek: ~{input_tokens} girdi token'ı; çıktı sınırı {args.max_tokens}.")
        for model in models:
            entry = catalog.get(model)
            price_in, price_out = price_per_token(entry)
            # One retry with a larger limit is possible after an answer is cut off, so the guard budgets for it.
            worst = 2 * input_tokens * price_in + (args.max_tokens + retry_limit(args.max_tokens)) * price_out
            worst_case += worst if entry else 0.0
            state = "bulundu" if entry else "KATALOGDA YOK (atlanacak)"
            print(f"  {model:42s} ${price_in * 1e6:6.2f} / ${price_out * 1e6:6.2f} per 1M  en kötü durum ${worst:.4f}  {state}")
        print(f"Toplam en kötü durum maliyeti: ${worst_case:.3f} (sınır ${args.max_cost:.2f})")
        if args.check_models:
            return 0
        if worst_case > args.max_cost:
            print("En kötü durum maliyeti sınırı aşıyor; --max-tokens'ı düşürün, model sayısını azaltın ya da --max-cost'u bilerek yükseltin.", file=sys.stderr)
            return 3

        runnable = [model for model in models if model in catalog]
        results = await asyncio.gather(*(
            run_model(client, api_key or "dry-run", model, messages, context, catalog.get(model),
                      max_tokens=args.max_tokens, reasoning=args.reasoning, timeout=args.timeout)
            for model in runnable
        ))

    seed = args.seed or f"{time.time_ns()}"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(render_page(list(results), seed), encoding="utf-8")
    (args.out / "results.json").write_text(json.dumps({"seed": seed, "order": blind_order([r.model for r in results], seed), "results": [asdict(r) for r in results]}, ensure_ascii=False, indent=2), encoding="utf-8")
    spent = sum(result.cost_usd or 0.0 for result in results)
    usable = sum(result.usable for result in results)
    print(f"\n{len(results)} model çalıştı, {usable} tanesi kullanılabilir çıktı verdi; toplam maliyet ${spent:.4f}.")
    print(f"Kör karşılaştırma sayfası: {args.out / 'index.html'}")
    print("Modellerin adı sayfada 'Modelleri göster'e basana kadar gizli; results.json hangi aday hangi model olduğunu içerir, sonuna kadar açmayın.")
    return 0


def main(argv: list[str] | None = None) -> int:
    # The Windows console defaults to a legacy code page that garbles Turkish letters.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
