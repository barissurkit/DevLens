export const MAX_USERNAME_LENGTH = 39;

export const EXAMPLE_USERNAMES: readonly string[] = ["octocat", "torvalds", "gaearon"];

export type UsernameParseResult =
  | { ok: true; username: string }
  | { ok: false; message: string };

// GitHub logins: letters, digits and single hyphens; cannot start or end with a hyphen.
const VALID_USERNAME = /^[a-z\d](?:[a-z\d]|-(?=[a-z\d]))*$/i;
const PROFILE_URL = /^(?:https?:\/\/)?(?:www\.)?github\.com\/([^/?#\s]+)/i;

/** Accepts a plain login, `@login`, or a github.com profile/repository URL. */
export function extractUsername(input: string): string {
  const trimmed = input.trim();
  const fromUrl = PROFILE_URL.exec(trimmed);
  const candidate = fromUrl ? fromUrl[1] : trimmed;
  return candidate.replace(/^@/, "").trim();
}

export function parseGitHubUsername(input: string): UsernameParseResult {
  const username = extractUsername(input);
  if (!username) return { ok: false, message: "Bir GitHub kullanıcı adı girin." };
  if (username.length > MAX_USERNAME_LENGTH) {
    return { ok: false, message: "GitHub kullanıcı adı 39 karakterden uzun olamaz." };
  }
  if (!VALID_USERNAME.test(username)) {
    return {
      ok: false,
      message: "GitHub kullanıcı adı yalnızca harf, rakam ve tek tire içerebilir; tire ile başlayıp bitemez.",
    };
  }
  return { ok: true, username };
}

/**
 * Early feedback while typing: flags only characters that can never be valid, so partial input
 * such as a trailing hyphen ("octo-") is not reported until submit.
 */
export function liveUsernameHint(input: string): string | null {
  const username = extractUsername(input);
  if (!username) return null;
  if (username.length > MAX_USERNAME_LENGTH) return "GitHub kullanıcı adı 39 karakterden uzun olamaz.";
  if (/[^a-z\d-]/i.test(username)) return "Yalnızca harf, rakam ve tire kullanılabilir.";
  if (/--/.test(username)) return "Art arda iki tire kullanılamaz.";
  return null;
}
