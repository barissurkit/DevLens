import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BadgeButton } from "../components/badge-button";
import { badgeImageUrl, badgeMarkdown } from "../lib/share";

describe("badge links", () => {
  beforeEach(() => vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/"));
  afterEach(() => vi.unstubAllEnvs());

  it("points at the API badge image", () => {
    expect(badgeImageUrl("octo-cat")).toBe("https://api.example.com/api/v1/badge/octo-cat.svg");
  });

  it("builds README markdown that links back to the result page", () => {
    expect(badgeMarkdown("octocat", "https://devlens.example")).toBe(
      "[![DevLens portföy skoru](https://api.example.com/api/v1/badge/octocat.svg)](https://devlens.example/u/octocat)",
    );
  });

  it("has nothing to offer when the API is not configured", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(badgeImageUrl("octocat")).toBeNull();
    expect(badgeMarkdown("octocat", "https://devlens.example")).toBeNull();
  });
});

describe("BadgeButton", () => {
  beforeEach(() => vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com"));
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("copies the markdown and confirms it", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    render(<BadgeButton username="octocat" />);

    fireEvent.click(screen.getByRole("button", { name: /README rozeti/ }));

    await waitFor(() => expect(screen.getByRole("button")).toHaveTextContent("Rozet kodu kopyalandı"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("https://api.example.com/api/v1/badge/octocat.svg"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining(`${window.location.origin}/u/octocat`));
  });

  it("renders nothing without an API address", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    await act(async () => { render(<BadgeButton username="octocat" />); });
    expect(screen.queryByRole("button")).toBeNull();
  });
});
