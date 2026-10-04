import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorReporter } from "../components/error-reporter";
import { reportClientError, resetClientErrorBudget } from "../lib/report-error";

describe("client error reporting", () => {
  let fetchMock: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/");
    resetClientErrorBudget();
    window.history.replaceState(null, "", "/u/octocat?token=abc");
    fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("posts a bounded report that carries the path but not the query string", () => {
    reportClientError("render", Object.assign(new Error("x".repeat(900)), { stack: "s".repeat(3000) }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.example.com/api/v1/client-errors");
    const body = JSON.parse(String(init.body));
    expect(body).toMatchObject({ kind: "render", path: "/u/octocat" });
    expect(body.message).toHaveLength(500);
    expect(body.stack).toHaveLength(2000);
    expect(String(init.body)).not.toContain("token=abc");
  });

  it("sends at most five reports per page view", () => {
    for (let index = 0; index < 8; index += 1) reportClientError("script", new Error(`e${index}`));
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("does nothing without an API address and never throws when the network fails", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    reportClientError("script", new Error("a"));
    expect(fetchMock).not.toHaveBeenCalled();

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com");
    fetchMock.mockRejectedValue(new Error("offline"));
    expect(() => reportClientError("script", new Error("b"))).not.toThrow();
  });

  it("reports uncaught errors and unhandled rejections once mounted", () => {
    render(<ErrorReporter />);

    window.dispatchEvent(new ErrorEvent("error", { error: new Error("boom"), message: "boom" }));
    const rejection = new Event("unhandledrejection") as Event & { reason: unknown };
    rejection.reason = new Error("nope");
    window.dispatchEvent(rejection);

    const kinds = fetchMock.mock.calls.map((call: unknown[]) => JSON.parse(String((call[1] as RequestInit).body)).kind);
    expect(kinds).toEqual(["script", "promise"]);
  });
});
