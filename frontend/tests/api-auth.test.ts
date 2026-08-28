import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAuthMe, getAuthStartUrl, logout } from "../lib/api";

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
});
