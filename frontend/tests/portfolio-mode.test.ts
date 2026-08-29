import { describe, expect, it } from "vitest";
import { portfolioModeLabel } from "../lib/presentation";

describe("backend-derived portfolio mode labels", () => {
  it("shows the workspace label only for backend-confirmed ownership", () => {
    expect(portfolioModeLabel({ is_owner: true, mode: "my_workspace" })).toBe("Your Portfolio");
  });

  it("falls back to Explore for a backend non-owner result", () => {
    expect(portfolioModeLabel({ is_owner: false, mode: "explore" })).toBe("Viewing public portfolio");
  });
});
