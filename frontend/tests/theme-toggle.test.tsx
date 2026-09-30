import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "../components/theme-toggle";
import { THEME_STORAGE_KEY } from "../lib/theme";

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });
  afterEach(cleanup);

  it("starts on the system theme without forcing a data-theme attribute", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "Sistem teması" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement).not.toHaveAttribute("data-theme");
  });

  it("applies and persists an explicit dark theme", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Koyu tema" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Koyu tema" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Sistem teması" })).toHaveAttribute("aria-pressed", "false");
  });

  it("clears the stored choice when returning to the system theme", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(screen.getByRole("button", { name: "Açık tema" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    await user.click(screen.getByRole("button", { name: "Sistem teması" }));
    expect(document.documentElement).not.toHaveAttribute("data-theme");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it("reads a previously stored choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: "Açık tema" })).toHaveAttribute("aria-pressed", "true");
  });
});
