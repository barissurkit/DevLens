import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { analyzePortfolioWithInterpretation } from "../lib/api";
import type { AnalysisProgress } from "../lib/types";

const analysis = { user: {}, selection: {}, repository_analysis: {}, aggregation: {}, intelligence: {}, score: {} };
const resultBody = {
  analysis,
  interpretation: { status: "unavailable", reason: "not_configured" },
  viewer_context: { is_owner: false, mode: "explore" },
  guided_improvements: [],
  analysis_generated_at: "2026-09-30T01:00:00Z",
  cached: false,
};

function ndjson(events: unknown[], chunkSize = 40): Response {
  const bytes = new TextEncoder().encode(events.map((event) => JSON.stringify(event)).join("\n") + "\n");
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let offset = 0; offset < bytes.length; offset += chunkSize) {
        controller.enqueue(bytes.slice(offset, offset + chunkSize));
      }
      controller.close();
    },
  });
  return new Response(stream, { status: 200, headers: { "Content-Type": "application/x-ndjson" } });
}

describe("streaming analysis", () => {
  beforeEach(() => vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000"));
  afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });

  it("reports progress in order and returns the final result, even when lines span chunks", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([
      { event: "progress", stage: "profile", completed: 0, total: 0 },
      { event: "progress", stage: "repositories", completed: 0, total: 3 },
      { event: "progress", stage: "repositories", completed: 3, total: 3 },
      { event: "progress", stage: "interpretation", completed: 0, total: 0 },
      { event: "result", data: resultBody },
    ]));
    const progress: AnalysisProgress[] = [];

    const result = await analyzePortfolioWithInterpretation("alice", { onProgress: (item) => progress.push(item) });

    expect(progress.map((item) => [item.stage, item.completed, item.total])).toEqual([
      ["profile", 0, 0],
      ["repositories", 0, 3],
      ["repositories", 3, 3],
      ["interpretation", 0, 0],
    ]);
    expect(result).toMatchObject({ cached: false, analysis_generated_at: "2026-09-30T01:00:00Z" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/v1/interpretation/stream");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ username: "alice" });
  });

  it("sends refresh only when requested", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([{ event: "result", data: resultBody }]));

    await analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined, refresh: true });

    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ username: "alice", refresh: true });
  });

  it("sends retry_interpretation only when an AI retry is requested", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => ndjson([{ event: "result", data: resultBody }]));

    await analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined, retryInterpretation: true });
    await analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined, refresh: true, retryInterpretation: true });
    await analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined });

    const bodies = fetchMock.mock.calls.map((call) => JSON.parse(String(call[1]?.body)));
    expect(bodies).toEqual([
      { username: "alice", retry_interpretation: true },
      { username: "alice", refresh: true, retry_interpretation: true },
      { username: "alice" },
    ]);
  });

  it("also sends the flags on the plain endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(resultBody), { status: 200 }));

    await analyzePortfolioWithInterpretation("alice", { retryInterpretation: true });

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/v1/interpretation");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ username: "alice", retry_interpretation: true });
  });

  it("maps a streamed error event to an ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([
      { event: "progress", stage: "profile", completed: 0, total: 0 },
      { event: "error", status: 404, detail: { code: "github_user_not_found", message: "GitHub kullanıcısı bulunamadı." } },
    ]));

    await expect(analyzePortfolioWithInterpretation("ghost", { onProgress: () => undefined })).rejects.toMatchObject({
      status: 404,
      code: "github_user_not_found",
      message: "GitHub kullanıcısı bulunamadı.",
    });
  });

  it("rejects an invalid streamed result instead of rendering it", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([{ event: "result", data: { nope: true } }]));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toMatchObject({
      code: "malformed_response",
    });
  });

  it("reports a dropped connection when the stream ends without a result", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([{ event: "progress", stage: "profile", completed: 0, total: 0 }]));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toMatchObject({
      code: "network_error",
    });
  });

  it("ignores unknown progress stages and unknown events", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ndjson([
      { event: "progress", stage: "teleport", completed: 1, total: 1 },
      { event: "heartbeat" },
      { event: "result", data: resultBody },
    ]));
    const onProgress = vi.fn();

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress })).resolves.toMatchObject({ cached: false });
    expect(onProgress).not.toHaveBeenCalled();
  });

  it("uses the regular JSON error contract for failures before streaming starts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ detail: { code: "rate_limited", message: "Çok fazla istek." } }),
      { status: 429 },
    ));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toMatchObject({
      status: 429,
      code: "rate_limited",
    });
  });

  it("carries the Retry-After hint of a rate limit response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(
      JSON.stringify({ detail: { code: "rate_limited", message: "Çok fazla istek." } }),
      { status: 429, headers: { "Retry-After": "42" } },
    ));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toMatchObject({
      code: "rate_limited",
      retryAfterSeconds: 42,
    });
  });

  it("ignores a missing or invalid Retry-After header", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: "rate_limited", message: "x" } }), { status: 429, headers: { "Retry-After": "soon" } }));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toMatchObject({
      code: "rate_limited",
      retryAfterSeconds: undefined,
    });
  });

  it("falls back to the plain endpoint when the streaming endpoint does not exist", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("Not Found", { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(resultBody), { status: 200 }));
    const onProgress = vi.fn();

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress })).resolves.toMatchObject({ cached: false });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "http://localhost:8000/api/v1/interpretation/stream",
      "http://localhost:8000/api/v1/interpretation",
    ]);
    expect(onProgress).not.toHaveBeenCalled();
  });

  it("falls back to the plain endpoint when the response is not an event stream", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response("<html></html>", { status: 200, headers: { "Content-Type": "text/html" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify(resultBody), { status: 200 }));

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).resolves.toMatchObject({ cached: false });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not stream at all when no progress listener is given", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(resultBody), { status: 200 }));

    await analyzePortfolioWithInterpretation("alice");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/v1/interpretation");
  });

  it("propagates aborts instead of falling back", async () => {
    const abort = Object.assign(new Error("aborted"), { name: "AbortError" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockRejectedValue(abort);

    await expect(analyzePortfolioWithInterpretation("alice", { onProgress: () => undefined })).rejects.toBe(abort);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
