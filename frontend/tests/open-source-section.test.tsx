import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OpenSourceSection } from "../components/open-source-section";
import type { OpenSourceContributions } from "../lib/types";

const mockedGet = vi.hoisted(() => vi.fn());
vi.mock("../lib/api", () => ({
  getOpenSourceContributions: mockedGet,
  ApiError: class ApiError extends Error {
    constructor(message: string, readonly status: number, readonly code: string) {
      super(message);
    }
  },
}));

const data: OpenSourceContributions = {
  username: "alice",
  total_merged: 3,
  repository_count: 2,
  is_truncated: false,
  contributions: [
    { repository: "big/framework", html_url: "https://github.com/big/framework", stars: 90000, merged_count: 2, latest_title: "Fix a crash", latest_url: "https://github.com/big/framework/pull/2", latest_merged_at: "2026-09-20T10:00:00Z" },
    { repository: "small/lib", html_url: "https://github.com/small/lib", stars: null, merged_count: 1, latest_title: "Add option", latest_url: "https://github.com/small/lib/pull/3", latest_merged_at: null },
  ],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OpenSourceSection", () => {
  it("does not ask GitHub until the tab is active, then asks once", async () => {
    mockedGet.mockResolvedValue(data);
    const { rerender } = render(<OpenSourceSection username="alice" active={false} />);

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(mockedGet).not.toHaveBeenCalled();

    rerender(<OpenSourceSection username="alice" active />);
    expect(await screen.findByRole("link", { name: "big/framework" })).toBeInTheDocument();
    rerender(<OpenSourceSection username="alice" active={false} />);
    rerender(<OpenSourceSection username="alice" active />);

    expect(mockedGet).toHaveBeenCalledTimes(1);
    expect(mockedGet).toHaveBeenCalledWith("alice");
  });

  it("shows the totals, each repository with its stars and latest pull request, and says the score ignores it", async () => {
    mockedGet.mockResolvedValue(data);
    render(<OpenSourceSection username="alice" active />);

    expect(await screen.findByText("90.000")).toBeInTheDocument();
    expect(screen.getByText(/skora katılmaz/)).toBeInTheDocument();
    expect(screen.getByText("Birleştirilen pull request").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("Katkı yapılan repository").nextSibling).toHaveTextContent("2");
    expect(screen.getByRole("link", { name: "Fix a crash" })).toHaveAttribute("href", "https://github.com/big/framework/pull/2");
    expect(screen.getByText("2 birleşen PR")).toBeInTheDocument();
    // A repository whose stars are unknown simply has no star count.
    const row = screen.getByRole("link", { name: "small/lib" }).closest("li") as HTMLElement;
    expect(row).not.toHaveTextContent("★");
  });

  it("marks a truncated search with a plus sign and a note", async () => {
    mockedGet.mockResolvedValue({ ...data, is_truncated: true });
    render(<OpenSourceSection username="alice" active />);

    expect(await screen.findByText("3+")).toBeInTheDocument();
    expect(screen.getByText(/daha eskileri varsa burada yer almıyor/)).toBeInTheDocument();
  });

  it("says so when there are no contributions", async () => {
    mockedGet.mockResolvedValue({ ...data, total_merged: 0, repository_count: 0, contributions: [] });
    render(<OpenSourceSection username="alice" active />);

    expect(await screen.findByText(/birleştirilmiş bir pull request bulunamadı/)).toBeInTheDocument();
  });

  it("shows the error and can try again", async () => {
    const { ApiError } = await import("../lib/api");
    mockedGet.mockRejectedValueOnce(new ApiError("GitHub'a geçici olarak erişilemiyor.", 503, "github_unavailable")).mockResolvedValue(data);
    const user = userEvent.setup();
    render(<OpenSourceSection username="alice" active />);

    expect(await screen.findByRole("alert")).toHaveTextContent("GitHub'a geçici olarak erişilemiyor.");
    await user.click(screen.getByRole("button", { name: "Yeniden dene" }));

    await waitFor(() => expect(screen.getByRole("link", { name: "big/framework" })).toBeInTheDocument());
    expect(mockedGet).toHaveBeenCalledTimes(2);
  });
});
