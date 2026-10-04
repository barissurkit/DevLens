import { expect, test, type Page } from "@playwright/test";
import { THEME_STORAGE_KEY } from "../lib/theme";

const OWNER = "barissurkit";

/** The sheet is 210 x 297 mm; the flowing content may only use the area between the header and the footer. */
async function layoutProblems(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const px = (mm: number) => (mm * 96) / 25.4;
    const problems: string[] = [];
    document.querySelectorAll<HTMLElement>(".report-sheet").forEach((sheet, sheetIndex) => {
      const box = sheet.getBoundingClientRect();
      if (Math.abs(box.width - px(210)) > 2 || Math.abs(box.height - px(297)) > 2) problems.push(`sheet ${sheetIndex + 1} is not A4 (${Math.round(box.width)}x${Math.round(box.height)})`);
      const flow = sheet.querySelector<HTMLElement>(".report-flow");
      if (!flow) return;
      const top = box.top + px(21);
      const bottom = box.top + px(21) + Math.floor(px(258));
      const right = box.left + px(210 - 16);
      // Every element of the flowing content (not only the blocks) has to stay inside the content area.
      flow.querySelectorAll<HTMLElement>("*").forEach((element) => {
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;
        if (rect.bottom > bottom + 1) problems.push(`sheet ${sheetIndex + 1}: <${element.tagName.toLowerCase()}> ends ${Math.round(rect.bottom - bottom)}px below the content area`);
        if (rect.top < top - 1) problems.push(`sheet ${sheetIndex + 1}: <${element.tagName.toLowerCase()}> starts above the content area`);
        if (rect.right > right + 1) problems.push(`sheet ${sheetIndex + 1}: <${element.tagName.toLowerCase()}> sticks out on the right`);
      });
    });
    return problems;
  });
}

async function openReport(page: Page, login: string, mode: "ozet" | "detay") {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(`/u/${login}/rapor?tur=${mode}`);
  await expect(page.locator(".report-root[data-report-pages]")).toBeAttached({ timeout: 30_000 });
}

const pageCount = async (page: Page) => Number(await page.locator(".report-root").getAttribute("data-report-pages"));

test.describe("report: the menu on the result page", () => {
  test("the print button opens a bar with the two reports and closes again", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    const button = page.getByRole("button", { name: /Yazdır \/ PDF/ });
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute("aria-expanded", "false");

    await button.click();

    await expect(button).toHaveAttribute("aria-expanded", "true");
    const bar = page.getByRole("group", { name: "Rapor türü" });
    await expect(bar).toBeVisible();
    // The bar must not squeeze the profile name next to the buttons (font metrics differ between machines, so the
    // limit is generous: the name has hundreds of pixels when nothing is wrong and collapses to zero when it is).
    const nameBox = await page.getByRole("heading", { level: 2, name: /portföyü$/ }).boundingBox();
    expect(nameBox!.width).toBeGreaterThan(250);
    await expect(bar.getByRole("link", { name: /Özet rapor/ })).toHaveAttribute("href", `/u/${OWNER}/rapor?tur=ozet`);
    await expect(bar.getByRole("link", { name: /Ayrıntılı rapor/ })).toHaveAttribute("href", `/u/${OWNER}/rapor?tur=detay`);

    await page.keyboard.press("Escape");
    await expect(bar).toBeHidden();
    await expect(button).toBeFocused();

    await button.click();
    await expect(bar).toBeVisible();
    await page.getByRole("heading", { level: 2, name: /portföyü$/ }).click();
    await expect(bar).toBeHidden();
  });

  test("choosing a report opens it", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    await page.getByRole("button", { name: /Yazdır \/ PDF/ }).click();
    await page.getByRole("link", { name: /Ayrıntılı rapor/ }).click();

    await expect(page).toHaveURL(new RegExp(`/u/${OWNER}/rapor\\?tur=detay$`));
    await expect(page.locator(".report-sheet").first()).toBeVisible();
  });
});

test.describe("report: content", () => {
  test.skip(({ isMobile }) => isMobile, "Sheet geometry is checked at desktop width");

  test("the summary has a cover and numbered pages, without repository details or AI", async ({ page }) => {
    await openReport(page, OWNER, "ozet");
    const pages = await pageCount(page);

    expect(pages).toBeGreaterThanOrEqual(2);
    expect(pages).toBeLessThanOrEqual(4);
    const cover = page.locator(".report-sheet").first();
    await expect(cover).toContainText("Portföy Analiz Raporu");
    await expect(cover).toContainText("Özet rapor");
    await expect(cover).toContainText(`@${OWNER}`);
    await expect(cover).toContainText("Oluşturulma:");

    const footers = await page.locator(".report-page-footer").allInnerTexts();
    expect(footers.map((text) => text.match(/Sayfa \d+ \/ \d+/)?.[0])).toEqual(Array.from({ length: pages - 1 }, (_, index) => `Sayfa ${index + 2} / ${pages}`));

    const text = await page.locator(".report-sheets").innerText();
    for (const expected of ["Genel değerlendirme", "Puanlama boyutları", "Öncelikli iyileştirmeler", "Analiz kapsamı", "Notlar ve sınırlar"]) expect(text).toContain(expected);
    expect(text).not.toContain("Repository ayrıntıları");
    expect(text).not.toContain("Puanlama yöntemi");
    expect(text).not.toMatch(/AI Yorumu|Gemini|AI Önerilen/);
    expect(await layoutProblems(page)).toEqual([]);
  });

  test("the detailed report adds every repository and the scoring method", async ({ page }) => {
    await openReport(page, OWNER, "ozet");
    const summaryPages = await pageCount(page);
    await openReport(page, OWNER, "detay");

    expect(await pageCount(page)).toBeGreaterThan(summaryPages);
    const text = await page.locator(".report-sheets").innerText();
    expect(text).toContain("Repository ayrıntıları");
    expect(text).toContain("Puanlama yöntemi");
    // Repository names of the recorded portfolio.
    for (const name of ["DevLens", "ai-search-engine", "impostra", "customer-churn-analysis"]) expect(text).toContain(name);
    expect(await layoutProblems(page)).toEqual([]);
    expect(await page.locator(".report-root").getAttribute("data-report-oversized")).toBe("0");
  });

  test("a portfolio without analyzed repositories still gives a tidy report", async ({ page }) => {
    for (const mode of ["ozet", "detay"] as const) {
      await openReport(page, "bos", mode);

      await expect(page.locator(".report-sheet").first()).toContainText("—");
      await expect(page.locator(".report-sheets")).toContainText("en az iki repository");
      expect(await layoutProblems(page)).toEqual([]);
    }
  });

  test("thirty repositories flow over many pages without any card being cut, and long sections are labelled", async ({ page }) => {
    await openReport(page, "buyuk", "detay");

    expect(await pageCount(page)).toBeGreaterThanOrEqual(10);
    expect(await layoutProblems(page)).toEqual([]);
    expect(await page.locator(".report-root").getAttribute("data-report-oversized")).toBe("0");
    // Every repository card appears exactly once.
    const names = await page.locator("[data-report-block] p.truncate").allInnerTexts();
    expect(names).toHaveLength(30);
    expect(new Set(names).size).toBe(30);
    // The repository list runs over several pages, so later pages carry a "continued" label.
    const labels = await page.locator(".report-continued").allInnerTexts();
    expect(labels.length).toBeGreaterThan(0);
    expect(labels.every((label) => label.includes("(devamı)"))).toBe(true);
    expect(labels.some((label) => label.includes("Repository ayrıntıları"))).toBe(true);
  });

  test("very long names, descriptions and notes wrap inside the page", async ({ page }) => {
    for (const mode of ["ozet", "detay"] as const) {
      await openReport(page, "uzun", mode);

      expect(await layoutProblems(page)).toEqual([]);
      expect(await page.locator(".report-root").getAttribute("data-report-oversized")).toBe("0");
    }
  });

  test("the printed PDF has exactly one page per sheet", async ({ page }) => {
    for (const [login, mode] of [[OWNER, "ozet"], [OWNER, "detay"], ["buyuk", "detay"]] as const) {
      await openReport(page, login, mode);
      const sheets = await pageCount(page);
      await page.emulateMedia({ media: "print" });

      const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });

      const counts = [...pdf.toString("latin1").matchAll(/\/Type\s*\/Pages[^>]*?\/Count\s+(\d+)/g)].map((match) => Number(match[1]));
      expect(Math.max(...counts), `${login} ${mode}`).toBe(sheets);
      await page.emulateMedia({ media: "screen" });
    }
  });
});

test.describe("report: page", () => {
  test("the toolbar switches between the two reports and goes back to the result", async ({ page }) => {
    await page.goto(`/u/${OWNER}/rapor?tur=ozet`);
    await expect(page.getByRole("link", { name: /Özet rapor/ })).toHaveAttribute("aria-current", "page");

    await page.getByRole("link", { name: "Ayrıntılı rapor" }).click();
    await expect(page).toHaveURL(/tur=detay$/);
    await expect(page.getByRole("link", { name: "Ayrıntılı rapor" })).toHaveAttribute("aria-current", "page");

    await page.getByRole("link", { name: /Sonuca dön/ }).click();
    await expect(page).toHaveURL(new RegExp(`/u/${OWNER}$`));
  });

  test("an unknown user gets a message instead of a report", async ({ page }) => {
    await page.goto("/u/ghost/rapor");

    await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)')).toContainText("GitHub kullanıcısı bulunamadı");
    await expect(page.locator(".report-sheet")).toHaveCount(0);
  });

  test("on a phone the sheets are scaled to the screen width", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Phone only");
    await page.goto(`/u/${OWNER}/rapor?tur=ozet`);
    await expect(page.locator(".report-sheet").first()).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await expect(page.getByRole("button", { name: /Yazdır \/ PDF olarak kaydet/ })).toBeVisible();
  });

  test("the report is always light, even when the dark theme is chosen", async ({ page }) => {
    await page.addInitScript((key) => window.localStorage.setItem(key, "dark"), THEME_STORAGE_KEY);
    await page.goto(`/u/${OWNER}`);
    await expect.poll(() => page.evaluate(() => document.documentElement.getAttribute("data-theme"))).toBe("dark");
    await page.goto(`/u/${OWNER}/rapor?tur=ozet`);
    await expect(page.locator(".report-sheet").first()).toBeVisible();

    const colors = await page.evaluate(() => {
      const sheet = document.querySelector(".report-sheet") as HTMLElement;
      return { background: getComputedStyle(sheet).backgroundColor, theme: document.documentElement.getAttribute("data-theme") };
    });
    expect(colors.background).toBe("rgb(255, 255, 255)");
    expect(colors.theme).toBe("light");
  });
});
