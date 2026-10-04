import { parseGitHubUsername } from "./username";

export const SITE_URL = "https://devlens.barissurkit.com";

/** Path of the shareable result page for a GitHub login. */
export function userPath(username: string): string {
  return `/u/${encodeURIComponent(username)}`;
}

/** The login from a `/u/[username]` route segment, or null when it is not a valid GitHub login. */
export function usernameFromRouteParam(raw: string): string | null {
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return null;
  }
  // Only a bare login is a valid segment; links or @names belong to the search field, not the URL.
  if (decoded !== decoded.trim() || decoded.startsWith("@") || /[/?#\s]/.test(decoded)) return null;
  const parsed = parseGitHubUsername(decoded);
  return parsed.ok ? parsed.username : null;
}

export interface UserPageMetadata {
  title: string;
  description: string;
  path: string;
}

export function userPageMetadata(username: string): UserPageMetadata {
  return {
    title: `@${username} portföy analizi | DevLens`,
    description: `@${username} için herkese açık GitHub kanıtlarına dayalı deterministik portföy skoru, repository bulguları ve gelişim alanları.`,
    path: userPath(username),
  };
}

/** Copies text with the async Clipboard API, falling back to a hidden textarea when it is unavailable or denied. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fall through: the API is missing (insecure context) or the permission was denied.
  }
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.setAttribute("aria-hidden", "true");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  try {
    field.select();
    return typeof document.execCommand === "function" && document.execCommand("copy");
  } catch {
    return false;
  } finally {
    field.remove();
  }
}

/** URL of the score badge image served by the API for a GitHub login, or null when the API is not configured. */
export function badgeImageUrl(username: string): string | null {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!baseUrl) return null;
  return `${baseUrl.replace(/\/+$/, "")}/api/v1/badge/${encodeURIComponent(username)}.svg`;
}

/** Markdown for a README: the badge, linking to the shareable result page. */
export function badgeMarkdown(username: string, siteUrl: string): string | null {
  const image = badgeImageUrl(username);
  return image ? `[![DevLens portföy skoru](${image})](${siteUrl}${userPath(username)})` : null;
}
