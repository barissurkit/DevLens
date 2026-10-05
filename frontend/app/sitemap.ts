import type { MetadataRoute } from "next";
import { SITE_URL, userPath } from "../lib/share";
import { EXAMPLE_USERNAMES } from "../lib/username";

// Analyses are created on demand, so only the landing page, its information pages and the documented examples are listed.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, changeFrequency: "monthly", priority: 1 },
    ...["/nasil-calisir", "/puanlama", "/sss"].map((path) => ({ url: `${SITE_URL}${path}`, changeFrequency: "monthly" as const, priority: 0.6 })),
    ...EXAMPLE_USERNAMES.map((username) => ({ url: `${SITE_URL}${userPath(username)}`, changeFrequency: "weekly" as const, priority: 0.5 })),
  ];
}
