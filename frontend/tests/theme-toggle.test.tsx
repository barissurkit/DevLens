import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "../components/theme-toggle";
import { THEME_STORAGE_KEY } from "../lib/theme";

const trigger = (label: string) => screen.getByRole("button", { name: `Tema: ${label}` });

describe("ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });
  afterEach(cleanup);

  it("is a single button that shows the system theme at first and keeps the choices hidden", () => {
    render(<ThemeToggle />);

    expect(trigger("Sistem")).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Koyu tema" })).toBeNull();
    expect(document.documentElement).not.toHaveAttribute("data-theme");
  });

  it("opens a list with the three choices and marks the current one", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    await user.click(trigger("Sistem"));

    expect(trigger("Sistem")).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("button", { name: "Sistem teması" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Açık tema" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Koyu tema" })).toHaveAttribute("aria-pressed", "false");
  });

  it("applies and persists an explicit dark theme, closes the list and shows the new theme on the button", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(trigger("Sistem"));

    await user.click(screen.getByRole("button", { name: "Koyu tema" }));

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.queryByRole("button", { name: "Koyu tema" })).toBeNull();
    expect(trigger("Koyu")).toHaveAttribute("aria-expanded", "false");
  });

  it("clears the stored choice when returning to the system theme", async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);
    await user.click(trigger("Sistem"));
    await user.click(screen.getByRole("button", { name: "Açık tema" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");

    await user.click(trigger("Açık"));
    await user.click(screen.getByRole("button", { name: "Sistem teması" }));

    expect(document.documentElement).not.toHaveAttribute("data-theme");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
  });

  it("reads a previously stored choice", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    render(<ThemeToggle />);

    expect(trigger("Açık")).toBeInTheDocument();
  });

  it("closes on Escape and on a press outside, without changing the theme", async () => {
    const user = userEvent.setup();
    render(<><ThemeToggle /><p>başka yer</p></>);

    await user.click(trigger("Sistem"));
    await user.keyboard("{Escape}");
    expect(trigger("Sistem")).toHaveAttribute("aria-expanded", "false");
    expect(trigger("Sistem")).toHaveFocus();

    await user.click(trigger("Sistem"));
    await user.click(screen.getByText("başka yer"));
    expect(trigger("Sistem")).toHaveAttribute("aria-expanded", "false");
    expect(document.documentElement).not.toHaveAttribute("data-theme");
  });
});
