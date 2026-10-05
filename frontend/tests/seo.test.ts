import { describe, expect, it } from "vitest";
import robots from "../app/robots";
import sitemap from "../app/sitemap";
import { SITE_URL } from "../lib/share";
import { EXAMPLE_USERNAMES } from "../lib/username";

describe("search engine files", () => {
  it("allows crawling and points at the sitemap", () => {
    expect(robots()).toEqual({ rules: [{ userAgent: "*", allow: "/" }], sitemap: `${SITE_URL}/sitemap.xml` });
  });

  it("lists the landing page, its information pages and the example results only", () => {
    const urls = sitemap().map((entry) => entry.url);
    expect(urls).toEqual([
      SITE_URL,
      `${SITE_URL}/nasil-calisir`,
      `${SITE_URL}/puanlama`,
      `${SITE_URL}/sss`,
      ...EXAMPLE_USERNAMES.map((name) => `${SITE_URL}/u/${name}`),
    ]);
  });
});
