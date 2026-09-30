import { describe, expect, it, vi } from "vitest";

describe("/version", () => {
  it("reports the build commit and time without caching", async () => {
    vi.stubEnv("BUILD_COMMIT", "abc1234");
    vi.stubEnv("BUILD_TIME", "2026-09-30T12:00:00.000Z");
    const { GET } = await import("../app/version/route");

    const response = GET();

    expect(await response.json()).toEqual({ commit: "abc1234", builtAt: "2026-09-30T12:00:00.000Z" });
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    vi.unstubAllEnvs();
  });
});
