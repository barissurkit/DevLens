import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { analyzePortfolioWithInterpretation, createActionPlanTask, deleteActionPlanTask, getActionPlan, getAuthMe, getAuthStartUrl, logout, updateActionPlanTask } from "../lib/api";

describe("authentication API helpers", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("uses credentials for anonymous and authenticated /auth/me bootstrap", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ authenticated: false, user: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        authenticated: true,
        user: { github_login: "example", display_name: null, avatar_url: null, github_html_url: null },
      }), { status: 200 }));

    await expect(getAuthMe()).resolves.toMatchObject({ authenticated: false, user: null });
    await expect(getAuthMe()).resolves.toMatchObject({ authenticated: true });
    expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8000/api/v1/auth/me", { credentials: "include" });
  });

  it("keeps login as browser navigation and sends credentialed POST logout", async () => {
    expect(getAuthStartUrl()).toBe("http://localhost:8000/api/v1/auth/github");
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));

    await expect(logout()).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
    });
  });

  it("does not persist authentication data in browser storage", () => {
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("uses credentialed JSON requests for private Action Plan CRUD", async () => {
    const task = { id: "task-1", title: "Task" };
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ tasks: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(task), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(task), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await getActionPlan();
    await createActionPlanTask({ title: "Task" });
    await updateActionPlanTask("task-1", { status: "done" });
    await deleteActionPlanTask("task-1");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8000/api/v1/workspace/action-plan", { credentials: "include" });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8000/api/v1/workspace/action-plan", expect.objectContaining({ method: "POST", credentials: "include", headers: { "Content-Type": "application/json" } }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "http://localhost:8000/api/v1/workspace/action-plan/task-1", expect.objectContaining({ method: "PATCH", credentials: "include" }));
    expect(fetchMock).toHaveBeenNthCalledWith(4, "http://localhost:8000/api/v1/workspace/action-plan/task-1", expect.objectContaining({ method: "DELETE", credentials: "include", headers: { "Content-Type": "application/json" } }));
    expect(fetchMock.mock.calls[3][1]).not.toHaveProperty("body");
  });

  it("includes the HttpOnly session cookie on public analysis without adding an auth header", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));

    await expect(analyzePortfolioWithInterpretation("example")).rejects.toMatchObject({ code: "malformed_response" });
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/interpretation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username: "example" }),
    });
  });
});
