import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalysisErrorState, rateLimitMessage } from "../components/analysis-error-state";
import { ApiError } from "../lib/api";

afterEach(cleanup);

describe("rateLimitMessage", () => {
  it.each([
    [undefined, "Kısa bir süre bekleyip tekrar deneyin."],
    [20, "Yaklaşık 20 saniye bekleyip tekrar deneyebilirsiniz."],
    [59, "Yaklaşık 59 saniye bekleyip tekrar deneyebilirsiniz."],
    [60, "Yaklaşık 1 dakika bekleyip tekrar deneyebilirsiniz."],
    [61, "Yaklaşık 2 dakika bekleyip tekrar deneyebilirsiniz."],
  ])("formats %s seconds", (seconds, expected) => {
    expect(rateLimitMessage(seconds)).toBe(expected);
  });
});

describe("AnalysisErrorState", () => {
  it("explains our own rate limit with the wait time and offers a retry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<AnalysisErrorState error={new ApiError("Çok fazla istek gönderildi.", 429, "rate_limited", 45)} onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Çok fazla istek gönderildi");
    expect(screen.getByRole("alert")).toHaveTextContent("Yaklaşık 45 saniye bekleyip tekrar deneyebilirsiniz.");
    expect(screen.getByRole("alert")).not.toHaveTextContent("Beklenmeyen bir sorun");
    await user.click(screen.getByRole("button", { name: "Tekrar dene" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps the GitHub rate limit distinct from our own", () => {
    render(<AnalysisErrorState error={new ApiError("x", 429, "github_rate_limit")} onRetry={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("GitHub istek sınırına ulaşıldı");
    expect(screen.queryByRole("button", { name: "Tekrar dene" })).not.toBeInTheDocument();
  });

  it("still falls back to the generic message for unknown codes", () => {
    render(<AnalysisErrorState error={new ApiError("x", 500, "something_else")} onRetry={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Beklenmeyen bir sorun oluştu");
  });
});
