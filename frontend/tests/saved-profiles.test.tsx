import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SaveProfileButton } from "../components/save-profile-button";
import { SavedProfiles } from "../components/saved-profiles";
import type { SavedProfile } from "../lib/types";

const api = vi.hoisted(() => ({ getSavedProfiles: vi.fn(), saveProfile: vi.fn(), removeSavedProfile: vi.fn() }));
const mockedUseAuth = vi.hoisted(() => vi.fn());

vi.mock("../lib/api", () => ({
  ...api,
  ApiError: class ApiError extends Error {
    constructor(message: string, readonly status: number, readonly code: string) {
      super(message);
    }
  },
}));
vi.mock("../components/auth-provider", () => ({ useAuth: mockedUseAuth }));

const signedIn = { status: "authenticated", user: { github_login: "me", display_name: "Ben", avatar_url: null, github_html_url: null } };

function profile(username: string, overrides: Partial<SavedProfile> = {}): SavedProfile {
  return { id: `id-${username}`, username, saved_at: "2026-09-20T10:00:00Z", latest_score: null, latest_analyzed_at: null, ...overrides };
}

beforeEach(() => mockedUseAuth.mockReturnValue(signedIn));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SavedProfiles", () => {
  it("lists each profile with its latest score, or says it has not been analysed", async () => {
    api.getSavedProfiles.mockResolvedValue({
      limit: 50,
      profiles: [profile("octocat", { latest_score: 61, latest_analyzed_at: "2026-10-01T10:00:00Z" }), profile("ghost")],
    });
    render(<SavedProfiles />);

    const rows = await screen.findAllByRole("listitem");
    expect(within(rows[0]).getByText("61 / 100")).toBeInTheDocument();
    expect(within(rows[0]).getByText(/Gelişebilir/)).toBeInTheDocument();
    expect(within(rows[0]).getByRole("link", { name: "@octocat" })).toHaveAttribute("href", "/u/octocat");
    expect(within(rows[0]).getByRole("link", { name: "Benimle karşılaştır" })).toHaveAttribute("href", "/karsilastir/me/octocat");
    expect(within(rows[1]).getByText("Skor yok")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Henüz analiz edilmedi")).toBeInTheDocument();
    expect(screen.getByText("2 / 50 profil kayıtlı.")).toBeInTheDocument();
  });

  it("does not offer to compare the person's own profile with itself", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [profile("Me")] });
    render(<SavedProfiles />);

    await screen.findByRole("link", { name: "@Me" });
    expect(screen.queryByRole("link", { name: "Benimle karşılaştır" })).toBeNull();
  });

  it("explains an empty list", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [] });
    render(<SavedProfiles />);

    expect(await screen.findByText(/Henüz kayıtlı profil yok/)).toBeInTheDocument();
  });

  it("adds a profile (a pasted link is reduced to the login) and puts it first", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [profile("old")] });
    api.saveProfile.mockResolvedValue(profile("torvalds"));
    const user = userEvent.setup();
    render(<SavedProfiles />);
    await screen.findByRole("link", { name: "@old" });

    await user.type(screen.getByLabelText("Kaydedilecek GitHub kullanıcı adı"), "https://github.com/torvalds");
    await user.click(screen.getByRole("button", { name: "Profili kaydet" }));

    expect(api.saveProfile).toHaveBeenCalledWith("torvalds");
    const rows = await screen.findAllByRole("listitem");
    expect(within(rows[0]).getByRole("link", { name: "@torvalds" })).toBeInTheDocument();
    expect(screen.getByLabelText("Kaydedilecek GitHub kullanıcı adı")).toHaveValue("");
  });

  it("rejects an invalid name without asking the server, and shows the server's message when it refuses", async () => {
    const { ApiError } = await import("../lib/api");
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [] });
    api.saveProfile.mockRejectedValue(new ApiError("En fazla 50 profil kaydedebilirsin.", 409, "saved_profiles_limit_reached"));
    const user = userEvent.setup();
    render(<SavedProfiles />);
    await screen.findByText(/Henüz kayıtlı profil yok/);

    await user.type(screen.getByLabelText("Kaydedilecek GitHub kullanıcı adı"), "bad name!");
    await user.click(screen.getByRole("button", { name: "Profili kaydet" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(api.saveProfile).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Kaydedilecek GitHub kullanıcı adı"));
    await user.type(screen.getByLabelText("Kaydedilecek GitHub kullanıcı adı"), "octocat");
    await user.click(screen.getByRole("button", { name: "Profili kaydet" }));
    expect(await screen.findByText("En fazla 50 profil kaydedebilirsin.")).toBeInTheDocument();
  });

  it("removes a profile from the list", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [profile("octocat"), profile("ghost")] });
    api.removeSavedProfile.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<SavedProfiles />);
    await screen.findByRole("link", { name: "@octocat" });

    await user.click(screen.getByRole("button", { name: "@octocat profilini kaldır" }));

    expect(api.removeSavedProfile).toHaveBeenCalledWith("id-octocat");
    await waitFor(() => expect(screen.queryByRole("link", { name: "@octocat" })).toBeNull());
    expect(screen.getByRole("link", { name: "@ghost" })).toBeInTheDocument();
  });

  it("shows a load error and can try again", async () => {
    const { ApiError } = await import("../lib/api");
    api.getSavedProfiles.mockRejectedValueOnce(new ApiError("Kayıtlı profillere ulaşılamadı.", 0, "network_error")).mockResolvedValue({ limit: 50, profiles: [profile("octocat")] });
    const user = userEvent.setup();
    render(<SavedProfiles />);

    expect(await screen.findByText("Kayıtlı profillere ulaşılamadı.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yeniden dene" }));

    expect(await screen.findByRole("link", { name: "@octocat" })).toBeInTheDocument();
  });
});

describe("SaveProfileButton", () => {
  it("saves and un-saves the profile of a result page", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [] });
    api.saveProfile.mockResolvedValue(profile("octocat"));
    api.removeSavedProfile.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<SaveProfileButton username="octocat" />);

    const button = await screen.findByRole("button", { name: "Kaydet" });
    expect(button).toHaveAttribute("aria-pressed", "false");
    await user.click(button);
    expect(await screen.findByRole("button", { name: "Kayıtlı" })).toHaveAttribute("aria-pressed", "true");
    expect(api.saveProfile).toHaveBeenCalledWith("octocat");

    await user.click(screen.getByRole("button", { name: "Kayıtlı" }));
    expect(await screen.findByRole("button", { name: "Kaydet" })).toBeInTheDocument();
    expect(api.removeSavedProfile).toHaveBeenCalledWith("id-octocat");
  });

  it("starts as saved when the profile is already in the list, whatever its case", async () => {
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [profile("OctoCat")] });
    render(<SaveProfileButton username="octocat" />);

    expect(await screen.findByRole("button", { name: "Kayıtlı" })).toBeInTheDocument();
  });

  it("is not shown to visitors, on the person's own portfolio, or when saving is unavailable", async () => {
    mockedUseAuth.mockReturnValue({ status: "anonymous", user: null });
    const visitor = render(<SaveProfileButton username="octocat" />);
    expect(visitor.container).toBeEmptyDOMElement();
    expect(api.getSavedProfiles).not.toHaveBeenCalled();
    visitor.unmount();

    mockedUseAuth.mockReturnValue(signedIn);
    const own = render(<SaveProfileButton username="ME" />);
    expect(own.container).toBeEmptyDOMElement();
    expect(api.getSavedProfiles).not.toHaveBeenCalled();
    own.unmount();

    api.getSavedProfiles.mockRejectedValue(new Error("down"));
    const broken = render(<SaveProfileButton username="octocat" />);
    await waitFor(() => expect(api.getSavedProfiles).toHaveBeenCalled());
    await waitFor(() => expect(broken.container).toBeEmptyDOMElement());
  });

  it("shows the server's message when saving is refused", async () => {
    const { ApiError } = await import("../lib/api");
    api.getSavedProfiles.mockResolvedValue({ limit: 50, profiles: [] });
    api.saveProfile.mockRejectedValue(new ApiError("En fazla 50 profil kaydedebilirsin.", 409, "saved_profiles_limit_reached"));
    const user = userEvent.setup();
    render(<SaveProfileButton username="octocat" />);

    await user.click(await screen.findByRole("button", { name: "Kaydet" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("En fazla 50 profil kaydedebilirsin.");
    expect(screen.getByRole("button", { name: "Kaydet" })).toBeInTheDocument();
  });
});
