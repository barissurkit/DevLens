import asyncio
import importlib.util
import json
import re
import sys
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_models.py"
spec = importlib.util.spec_from_file_location("compare_models", SCRIPT)
compare = importlib.util.module_from_spec(spec)
assert spec and spec.loader
# Dataclasses look their module up in sys.modules, so it has to be registered before it runs.
sys.modules["compare_models"] = compare
spec.loader.exec_module(compare)


@pytest.fixture(scope="module")
def context():
    return compare.load_context(compare.DEFAULT_FIXTURE)


def valid_answer(context) -> dict:
    return json.loads(
        httpx.Client(transport=compare.canned_transport(context)).post(
            f"{compare.API_BASE}/chat/completions", json={"model": "x"}
        ).json()["choices"][0]["message"]["content"].removeprefix("```json\n").removesuffix("\n```")
    )


def run(args_list: list[str], transport=None, key: str | None = "test-key-not-real", monkeypatch=None) -> int:
    if monkeypatch is not None:
        if key is None:
            monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        else:
            monkeypatch.setenv("OPENROUTER_API_KEY", key)
    return asyncio.run(compare.main_async(compare.parse_args(args_list), transport))


def test_the_request_is_the_production_prompt(context) -> None:
    from app.prompts.portfolio_interpretation import SYSTEM_INSTRUCTION, build_interpretation_content

    messages = compare.build_messages(context)

    assert messages == [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": build_interpretation_content(context)},
    ]


def test_body_asks_for_json_with_usage_and_an_optional_reasoning_effort(context) -> None:
    messages = compare.build_messages(context)

    body = compare.build_body("a/b", messages, max_tokens=1234, reasoning="low", with_reasoning=True)

    assert body["response_format"] == {"type": "json_object"}
    assert body["usage"] == {"include": True}
    assert body["max_tokens"] == 1234 and body["model"] == "a/b"
    assert body["reasoning"] == {"effort": "low"}
    assert "reasoning" not in compare.build_body("a/b", messages, max_tokens=1, reasoning="low", with_reasoning=False)
    assert "reasoning" not in compare.build_body("a/b", messages, max_tokens=1, reasoning="default", with_reasoning=True)


def test_json_is_found_inside_fences_and_prose() -> None:
    assert json.loads(compare.extract_json('```json\n{"a": 1}\n```')) == {"a": 1}
    assert json.loads(compare.extract_json('Tabii, işte sonuç:\n{"a": 1}\nUmarım yardımcı olur.')) == {"a": 1}


def test_a_correct_answer_passes_every_check(context) -> None:
    result = compare.evaluate(json.dumps(valid_answer(context), ensure_ascii=False), context)

    assert (result.json_valid, result.schema_valid, result.references_valid) == (True, True, True)
    assert result.issues == []
    assert result.turkish_letter_ratio >= 0.03
    assert result.explanation_count == len(context.strength_signals) + len(context.improvement_signals)


def test_broken_answers_are_caught_at_the_right_step(context) -> None:
    not_json = compare.evaluate("Üzgünüm, yapamam.", context)
    wrong_shape = compare.evaluate('{"summary": "x", "strength_explanations": "not a list"}', context)
    only_a_summary = compare.evaluate('{"summary": "x"}', context)
    answer = valid_answer(context)
    answer["strength_explanations"] = answer["strength_explanations"][:-1]
    skipped_signal = compare.evaluate(json.dumps(answer), context)

    assert not_json.json_valid is False
    assert (wrong_shape.json_valid, wrong_shape.schema_valid) == (True, False)
    # The schema alone accepts a bare summary; the signal references are what reject it.
    assert (only_a_summary.schema_valid, only_a_summary.references_valid) == (True, False)
    # The application rejects an answer that skips a deterministic signal, so the comparison does too.
    assert (skipped_signal.schema_valid, skipped_signal.references_valid) == (True, False)
    assert any("Referans hatası" in issue for issue in skipped_signal.issues)


def test_text_that_is_not_turkish_is_flagged(context) -> None:
    answer = valid_answer(context)
    answer["summary"] = "This portfolio has a solid base."
    for item in answer["strength_explanations"] + answer["improvement_explanations"]:
        item["explanation"] = "This signal appears in many repositories."
    answer["limitations_note"] = "Only public repositories were analyzed."

    result = compare.evaluate(json.dumps(answer), context)

    assert result.turkish_letter_ratio < 0.03
    assert any("Türkçe" in issue for issue in result.issues)


def test_blind_order_depends_on_the_seed_only() -> None:
    models = [f"vendor/model-{index}" for index in range(8)]

    first = compare.blind_order(models, "seed-1")

    assert first == compare.blind_order(models, "seed-1")
    assert sorted(first) == sorted(models)
    assert len({tuple(compare.blind_order(models, f"seed-{n}")) for n in range(20)}) > 1


def test_a_full_dry_run_writes_the_blind_page_and_never_the_key(tmp_path, monkeypatch) -> None:
    exit_code = run(["--dry-run", "--out", str(tmp_path), "--seed", "s"], key="sk-or-secret-key-value", monkeypatch=monkeypatch)

    assert exit_code == 0
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    results = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert len(results["results"]) == len(compare.DEFAULT_MODELS)
    assert all(item["evaluation"]["references_valid"] for item in results["results"])
    assert "sk-or-secret-key-value" not in page + json.dumps(results)
    # Candidates are anonymous until the reveal: model ids only appear inside hidden reveal blocks.
    visible = re.sub(r"<div class='reveal'>.*?</div>", "", page, flags=re.S)
    visible = re.sub(r"<table>.*?</table>", "", visible, flags=re.S)
    for model in compare.DEFAULT_MODELS:
        assert model not in visible
        assert model in page
    for label in ("Aday A", "Aday B", "Aday G"):
        assert label in page


def test_the_api_key_goes_only_into_the_authorization_header(tmp_path, monkeypatch, context) -> None:
    seen: list[httpx.Request] = []
    inner = compare.canned_transport(context)

    def spy(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return inner.handler(request)

    exit_code = run(["--models", "openai/gpt-6-luna", "--out", str(tmp_path)], transport=httpx.MockTransport(spy), key="sk-or-secret-key-value", monkeypatch=monkeypatch)

    assert exit_code == 0
    posts = [request for request in seen if request.method == "POST"]
    assert len(posts) == 1
    assert posts[0].headers["authorization"] == "Bearer sk-or-secret-key-value"
    assert b"sk-or-secret-key-value" not in posts[0].content


def test_a_model_that_cannot_answer_does_not_stop_the_others(tmp_path, monkeypatch, context) -> None:
    inner = compare.canned_transport(context)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": name, "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}} for name in ("a/good", "b/broken", "c/down")]})
        body = json.loads(request.content)
        if body["model"] == "c/down":
            return httpx.Response(503, text="upstream unavailable")
        return inner.handler(request)

    run(["--models", "a/good,b/broken,c/down", "--out", str(tmp_path)], transport=httpx.MockTransport(handler), monkeypatch=monkeypatch)

    results = {item["model"]: item for item in json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["results"]}
    assert results["a/good"]["evaluation"]["references_valid"] is True
    assert results["b/broken"]["ok"] is True and results["b/broken"]["evaluation"]["json_valid"] is False
    assert results["c/down"]["ok"] is False and "503" in results["c/down"]["error"]
    assert "kullanılabilir bir çıktı üretemedi" in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_a_model_that_rejects_the_reasoning_setting_is_asked_again_without_it(tmp_path, monkeypatch, context) -> None:
    inner = compare.canned_transport(context)
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "a/strict", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}}]})
        body = json.loads(request.content)
        bodies.append(body)
        if "reasoning" in body:
            return httpx.Response(400, text='{"error": "unsupported parameter: reasoning"}')
        return inner.handler(request)

    run(["--models", "a/strict", "--out", str(tmp_path)], transport=httpx.MockTransport(handler), monkeypatch=monkeypatch)

    assert ["reasoning" in body for body in bodies] == [True, False]
    result = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["results"][0]
    assert result["evaluation"]["references_valid"] is True
    assert any("reasoning" in note for note in result["notes"])


def test_the_page_escapes_whatever_a_model_writes(context) -> None:
    answer = valid_answer(context)
    answer["summary"] = "<script>alert('x')</script> & <img src=x onerror=alert(1)>"
    evaluation = compare.evaluate(json.dumps(answer), context)
    result = compare.RunResult(model="evil/model", ok=True, evaluation=evaluation, cost_usd=0.001)

    page = compare.render_page([result], "seed")

    assert "<script>alert" not in page
    assert "&lt;script&gt;alert" in page
    assert "<img src=x" not in page


def test_check_models_needs_no_key_and_a_missing_key_is_reported(monkeypatch, tmp_path, capsys, context) -> None:
    assert run(["--check-models", "--dry-run"], key=None, monkeypatch=monkeypatch) == 0
    assert run(["--out", str(tmp_path)], key=None, monkeypatch=monkeypatch) == 2
    assert "OPENROUTER_API_KEY" in capsys.readouterr().err


def test_a_run_that_could_cost_too_much_is_refused_before_any_request(tmp_path, monkeypatch, context) -> None:
    calls: list[httpx.Request] = []
    inner = compare.canned_transport(context)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return inner.handler(request)

    exit_code = run(["--dry-run", "--max-cost", "0.0001", "--out", str(tmp_path)], transport=httpx.MockTransport(handler), monkeypatch=monkeypatch)

    assert exit_code == 3
    assert [request.method for request in calls] == ["GET"]
    assert not (tmp_path / "index.html").exists()


def test_an_answer_cut_off_by_the_token_limit_is_retried_once_with_more_room(tmp_path, monkeypatch, context) -> None:
    inner = compare.canned_transport(context)
    limits: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "a/thinker", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}}]})
        body = json.loads(request.content)
        limits.append(body["max_tokens"])
        if body["max_tokens"] <= 4000:
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"prompt_tokens": 2700, "completion_tokens": 4000, "cost": 0.002}})
        return inner.handler(request)

    run(["--models", "a/thinker", "--out", str(tmp_path)], transport=httpx.MockTransport(handler), monkeypatch=monkeypatch)

    assert limits == [4000, 10000]
    result = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["results"][0]
    assert result["evaluation"]["references_valid"] is True
    assert result["cost_usd"] == pytest.approx(0.0031)  # both attempts are paid for, so both are counted
    assert any("yeniden denendi" in note for note in result["notes"])


def test_a_cut_off_answer_is_retried_only_once(tmp_path, monkeypatch) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "a/endless", "pricing": {"prompt": "0.0000001", "completion": "0.0000005"}}]})
        calls.append(json.loads(request.content)["max_tokens"])
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001}})

    run(["--models", "a/endless", "--out", str(tmp_path)], transport=httpx.MockTransport(handler), monkeypatch=monkeypatch)

    assert len(calls) == 2
    result = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["results"][0]
    assert result["evaluation"]["json_valid"] is False
    assert result["cost_usd"] == pytest.approx(0.002)


def test_the_retry_limit_grows_but_stays_capped() -> None:
    assert compare.retry_limit(4000) == 10000
    assert compare.retry_limit(8000) == 12000
    assert compare.retry_limit(20000) == 20000
