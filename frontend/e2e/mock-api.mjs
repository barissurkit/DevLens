// A tiny stand-in for the DevLens API used by the browser tests. It replays a recorded public analysis and
// lets a test switch behaviour with cookies: `e2e_owner=1` (signed in as the portfolio owner) and
// `e2e_ai=off` (AI interpretation unavailable).
import fs from "node:fs";
import http from "node:http";

const PORT = Number(process.env.MOCK_API_PORT ?? 8100);
const base = JSON.parse(fs.readFileSync(new URL("./fixtures/portfolio.json", import.meta.url), "utf8"));
const OWNER = base.analysis.user.username;
const insights = base.analysis.intelligence;

function interpretation(aiOff) {
  if (aiOff) return { status: "unavailable", reason: "rate_limit" };
  const keys = (items) => (items ?? []).map((item) => item.key);
  const strengths = keys(insights.strength_signals).slice(0, 1);
  const gaps = keys(insights.improvement_signals).slice(0, 2);
  return {
    status: "available",
    interpretation: {
      summary: "Portföy düzenli bir temel sunuyor; test ve otomasyon alanı en çok gelişebilecek yer.",
      strength_explanations: strengths.map((key) => ({ signal_key: key, explanation: "Bu sinyal birçok repository'de görülüyor." })),
      improvement_explanations: gaps.map((key) => ({ signal_key: key, explanation: "Küçük bir iyileştirme skora doğrudan yansır." })),
      technology_context: null,
      project_area_context: null,
      limitations_note: null,
      next_project_recommendation: null,
    },
  };
}

function cookies(request) {
  return Object.fromEntries(
    (request.headers.cookie ?? "")
      .split(";")
      .map((part) => part.trim().split("="))
      .filter(([key]) => key),
  );
}

function resultFor(request) {
  const jar = cookies(request);
  const owner = jar.e2e_owner === "1";
  return {
    ...base,
    interpretation: interpretation(jar.e2e_ai === "off"),
    viewer_context: owner ? { is_owner: true, mode: "my_workspace" } : { is_owner: false, mode: "explore" },
    guided_improvements: owner
      ? [{
          rule_key: "tests_structure",
          title: "Test yapısı ekle",
          why: "Testler davranışı korur.",
          steps: ["Bir test dizini oluşturun."],
          verification: { detected_repository_count: 1, analyzed_repository_count: 8, current_state: "needs_improvement", analysis_available: true, analysis_partial: false, reanalysis_required: true },
        }]
      : [],
    cached: false,
    analysis_generated_at: new Date().toISOString(),
  };
}

// Any other login gets the same portfolio with a lower score, so comparisons have a clear leader.
function analysisFor(username) {
  if (username === OWNER) return base.analysis;
  return {
    ...base.analysis,
    user: { ...base.analysis.user, username, name: null },
    score: { ...base.analysis.score, overall_score: Math.max(0, (base.analysis.score.overall_score ?? 40) - 20) },
  };
}

const record = (daysAgo, score) => ({
  id: String(daysAgo),
  github_user_id: 1,
  github_username: OWNER,
  analysis_version: "v2",
  analysis_schema_version: "v1",
  captured_at: new Date(Date.now() - daysAgo * 864e5).toISOString(),
  portfolio_score: score,
  category_scores: [{ key: "documentation_consistency", label: "Dokümantasyon", score: score / 2 }],
  passed_checks: ["readme_exists"],
  failed_checks: [],
});

let tasks = [];

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

http
  .createServer(async (request, response) => {
    const origin = request.headers.origin ?? "http://localhost:3100";
    const cors = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
    };
    if (request.method === "OPTIONS") {
      response.writeHead(204, cors);
      return response.end();
    }
    const path = request.url.split("?")[0];
    let raw = "";
    for await (const chunk of request) raw += chunk;
    const body = raw ? JSON.parse(raw) : {};
    const json = (status, value) => {
      response.writeHead(status, { "Content-Type": "application/json", ...cors });
      response.end(JSON.stringify(value));
    };
    const owner = cookies(request).e2e_owner === "1";

    if (path === "/health") return json(200, { status: "ok" });
    if (path === "/api/v1/auth/me") {
      return json(
        200,
        owner
          ? { authenticated: true, user: { github_login: OWNER, display_name: "Test Sahibi", avatar_url: null, github_html_url: `https://github.com/${OWNER}` } }
          : { authenticated: false, user: null },
      );
    }
    if (path === "/api/v1/client-errors") {
      response.writeHead(204, cors);
      return response.end();
    }
    if (path === "/api/v1/analysis") {
      if (body.username === "ghost") return json(404, { detail: { code: "github_user_not_found", message: "GitHub kullanıcısı bulunamadı." } });
      const { analysis, viewer_context, guided_improvements } = resultFor(request);
      return json(200, { ...analysisFor(body.username), viewer_context, guided_improvements: analysis ? guided_improvements : [] });
    }
    if (path === "/api/v1/interpretation" || path === "/api/v1/interpretation/stream") {
      if (body.username === "ghost") return json(404, { detail: { code: "github_user_not_found", message: "GitHub kullanıcısı bulunamadı." } });
      if (path.endsWith("/stream")) {
        response.writeHead(200, { "Content-Type": "application/x-ndjson", ...cors });
        const write = (value) => response.write(`${JSON.stringify(value)}\n`);
        write({ event: "progress", stage: "profile", completed: 0, total: 0 });
        await delay(150);
        for (let done = 0; done <= 8; done += 2) {
          write({ event: "progress", stage: "repositories", completed: done, total: 8 });
          await delay(80);
        }
        write({ event: "result", data: resultFor(request) });
        return response.end();
      }
      return json(200, resultFor(request));
    }
    if (path === "/api/v1/workspace/analysis-history" && owner) {
      const history = [record(0, 61), record(9, 54), record(21, 47)];
      return json(200, {
        latest: history[0],
        previous: history[1],
        comparison: { portfolio_score: 7, category_scores: [], newly_passing_checks: ["license"], newly_failing_checks: [], comparable: true, note: null },
        history,
      });
    }
    if (path === "/api/v1/workspace/action-plan" && owner) {
      if (request.method === "GET") return json(200, { tasks });
      const task = { id: `t${Date.now()}`, title: body.title, description: body.description ?? null, status: "todo", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), completed_at: null };
      tasks = [task, ...tasks];
      return json(201, task);
    }
    const match = path.match(/^\/api\/v1\/workspace\/action-plan\/(.+)$/);
    if (match && owner) {
      if (request.method === "DELETE") {
        tasks = tasks.filter((task) => task.id !== match[1]);
        response.writeHead(204, cors);
        return response.end();
      }
      tasks = tasks.map((task) => (task.id === match[1] ? { ...task, ...body } : task));
      return json(200, tasks.find((task) => task.id === match[1]));
    }
    if (path === "/api/v1/workspace/ai-suggestions" && owner) {
      return json(200, { status: "available", suggestions: [{ title: "CI iş akışı ekle", description: "Testleri çalıştıran bir iş akışı ekleyin.", reason: "Birçok repository'de CI yok.", evidence_refs: ["ci_workflow"] }] });
    }
    return json(owner ? 404 : 401, { detail: owner ? { code: "not_found", message: "yok" } : "Authentication required." });
  })
  .listen(PORT, () => console.log(`mock API on ${PORT}`));
