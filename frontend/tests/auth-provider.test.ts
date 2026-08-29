import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthControls } from "../components/auth-controls";
import { AuthProvider } from "../components/auth-provider";
import { getAuthMe, logout } from "../lib/api";

vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {},
  getAuthMe: vi.fn(),
  getAuthStartUrl: vi.fn(() => "http://localhost:8000/api/v1/auth/github"),
  logout: vi.fn(),
}));

const mockedGetAuthMe = vi.mocked(getAuthMe);
const mockedLogout = vi.mocked(logout);

function renderAuthControls() {
  return render(
    createElement(AuthProvider, null, createElement(AuthControls)),
  );
}

describe("frontend authentication state", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    mockedLogout.mockResolvedValue(undefined);
  });

  it("shows a non-blocking loading affordance before /auth/me resolves", () => {
    mockedGetAuthMe.mockReturnValue(new Promise(() => undefined));
    renderAuthControls();

    expect(screen.getByLabelText("Oturum durumu yükleniyor")).toBeInTheDocument();
  });

  it("renders anonymous sign-in and keeps the explore page available", async () => {
    mockedGetAuthMe.mockResolvedValue({ authenticated: false, user: null });
    renderAuthControls();

    const signIn = await screen.findByRole("link", { name: "Sign in with GitHub" });
    expect(signIn).toHaveAttribute("href", "http://localhost:8000/api/v1/auth/github");
    expect(screen.queryByText("Your Portfolio")).not.toBeInTheDocument();
  });

  it("renders the minimum authenticated identity and replaces sign-in", async () => {
    mockedGetAuthMe.mockResolvedValue({
      authenticated: true,
      user: {
        github_login: "example",
        display_name: "Example User",
        avatar_url: null,
        github_html_url: "https://github.com/example",
      },
    });
    renderAuthControls();

    expect(await screen.findByText("Example User")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My Workspace" })).toHaveAttribute(
      "href",
      "/?workspace=1&username=example",
    );
    expect(screen.getByRole("button", { name: "Çıkış yap" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign in with GitHub" })).not.toBeInTheDocument();
  });

  it("revokes the server session before returning to anonymous state", async () => {
    mockedGetAuthMe.mockResolvedValue({
      authenticated: true,
      user: { github_login: "example", display_name: null, avatar_url: null, github_html_url: null },
    });
    renderAuthControls();

    await screen.findByText("@example");
    await userEvent.click(screen.getByRole("button", { name: "Çıkış yap" }));

    await waitFor(() => expect(screen.getByRole("link", { name: "Sign in with GitHub" })).toBeInTheDocument());
    expect(mockedLogout).toHaveBeenCalledOnce();
  });

  it("does not claim logout succeeded when the server request fails", async () => {
    mockedGetAuthMe.mockResolvedValue({
      authenticated: true,
      user: { github_login: "example", display_name: "Example User", avatar_url: null, github_html_url: null },
    });
    mockedLogout.mockRejectedValue(new Error("network"));
    renderAuthControls();

    await screen.findByText("Example User");
    await userEvent.click(screen.getByRole("button", { name: "Çıkış yap" }));

    expect(await screen.findByText("Oturum kapatılamadı.")).toBeInTheDocument();
    expect(screen.getByText("Example User")).toBeInTheDocument();
  });
});
