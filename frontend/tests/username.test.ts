import { describe, expect, it } from "vitest";
import { extractUsername, liveUsernameHint, parseGitHubUsername } from "../lib/username";

describe("extractUsername", () => {
  it.each([
    ["octocat", "octocat"],
    ["  octocat  ", "octocat"],
    ["@octocat", "octocat"],
    ["github.com/octocat", "octocat"],
    ["https://github.com/octocat", "octocat"],
    ["https://www.github.com/octocat/", "octocat"],
    ["http://github.com/octocat/Hello-World", "octocat"],
    ["https://github.com/octocat?tab=repositories", "octocat"],
    ["HTTPS://GitHub.com/Octocat#readme", "Octocat"],
  ])("extracts %s", (input, expected) => {
    expect(extractUsername(input)).toBe(expected);
  });
});

describe("parseGitHubUsername", () => {
  it("accepts valid logins and profile links", () => {
    expect(parseGitHubUsername("octo-cat-1")).toEqual({ ok: true, username: "octo-cat-1" });
    expect(parseGitHubUsername("https://github.com/torvalds")).toEqual({ ok: true, username: "torvalds" });
    expect(parseGitHubUsername("@a")).toEqual({ ok: true, username: "a" });
  });

  it("reports an empty value", () => {
    expect(parseGitHubUsername("   ")).toEqual({ ok: false, message: "Bir GitHub kullanıcı adı girin." });
    expect(parseGitHubUsername("@")).toEqual({ ok: false, message: "Bir GitHub kullanıcı adı girin." });
  });

  it("keeps the existing over-length message", () => {
    expect(parseGitHubUsername("a".repeat(40))).toEqual({
      ok: false,
      message: "GitHub kullanıcı adı 39 karakterden uzun olamaz.",
    });
    expect(parseGitHubUsername("a".repeat(39))).toMatchObject({ ok: true });
  });

  it.each(["-octocat", "octocat-", "octo--cat", "octo cat", "octo_cat", "octocat!", "ünal"])(
    "rejects %s",
    (input) => {
      expect(parseGitHubUsername(input)).toMatchObject({ ok: false });
    },
  );
});

describe("liveUsernameHint", () => {
  it("stays quiet for valid and partially typed input", () => {
    expect(liveUsernameHint("")).toBeNull();
    expect(liveUsernameHint("octo-")).toBeNull();
    expect(liveUsernameHint("https://github.com/octocat")).toBeNull();
  });

  it("flags input that can never become valid", () => {
    expect(liveUsernameHint("octo cat")).toMatch(/harf, rakam ve tire/);
    expect(liveUsernameHint("octo--cat")).toMatch(/iki tire/);
    expect(liveUsernameHint("a".repeat(40))).toMatch(/39 karakter/);
  });
});
