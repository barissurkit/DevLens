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
