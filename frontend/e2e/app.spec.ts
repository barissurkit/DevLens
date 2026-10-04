import { expect, test, type Page } from "@playwright/test";

const OWNER = "barissurkit";

async function signInAs(page: Page, options: { aiOff?: boolean } = {}) {
  const cookies = [{ name: "e2e_owner", value: "1", domain: "localhost", path: "/" }];
  if (options.aiOff) cookies.push({ name: "e2e_ai", value: "off", domain: "localhost", path: "/" });
  await page.context().addCookies(cookies);
}

// Next.js adds its own role="alert" route announcer; ignore it when looking for the page's alerts.
const pageAlert = (page: Page) => page.locator('[role="alert"]:not(#__next-route-announcer__)');

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test.describe("landing page", () => {
  test("explains the product and has working section links", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText("GitHub portföyündeki kanıtları daha net gör.");
    await expect(page.getByRole("heading", { name: "Nasıl çalışır?" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Şeffaf puanlama" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sık sorulan sorular" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test("answers a question inside the FAQ", async ({ page }) => {
    await page.goto("/");
    const question = page.getByText("AI skoru değiştirir mi?");
    await question.scrollIntoViewIfNeeded();
    await question.click();

    await expect(page.getByText("AI yanıt vermediğinde bile skor ve bulgular eksiksiz görünür.")).toBeVisible();
  });

  test("shows a notice after a failed GitHub sign-in and cleans the address", async ({ page }) => {
    await page.goto("/?auth_error=authentication_failed");

    await expect(pageAlert(page)).toContainText("GitHub ile giriş tamamlanamadı");
    await expect(page).toHaveURL(/\/$/);
    await page.getByRole("button", { name: "Kapat" }).click();
    await expect(pageAlert(page)).toHaveCount(0);
  });

  test("serves the 404 page for unknown routes", async ({ page }) => {
    const response = await page.goto("/bu-sayfa-yok");

    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Aradığın sayfa bulunamadı" })).toBeVisible();
  });
});

test.describe("analysis", () => {
  test("searching with a profile link opens the shareable result", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("GitHub kullanıcı adı").fill(`https://github.com/${OWNER}`);
    await page.getByRole("button", { name: "Analiz et" }).click();

    await expect(page.getByRole("heading", { level: 2, name: /portföyü$/ })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/u/${OWNER}$`));
    await expect(page).toHaveTitle(`@${OWNER} portföy analizi | DevLens`);
    await expect(page.getByRole("tab", { name: /Genel Bakış/ })).toHaveAttribute("aria-selected", "true");
    await expectNoHorizontalOverflow(page);
  });

  test("a shared link loads the result directly and shows the AI interpretation", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    await expect(page.getByRole("tab", { name: /AI Yorumu/ })).toBeVisible();

    await page.getByRole("tab", { name: /AI Yorumu/ }).click();

    await expect(page.getByText("Portföy düzenli bir temel sunuyor")).toBeVisible();
  });

  test("tabs can be used with the keyboard", async ({ page, isMobile }) => {
    test.skip(isMobile, "Keyboard navigation is a desktop concern");
    await page.goto(`/u/${OWNER}`);
    const first = page.getByRole("tab", { name: /Genel Bakış/ });
    await first.focus();

    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: /Repository'ler/ })).toBeFocused();
    await expect(page.getByRole("tab", { name: /Repository'ler/ })).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: /Aksiyonlar/ })).toHaveAttribute("aria-selected", "true");
  });

  test("an unknown GitHub user gets a clear error and the page is marked noindex", async ({ page }) => {
    await page.goto("/u/ghost");

    await expect(pageAlert(page)).toContainText("GitHub kullanıcısı bulunamadı");
    await expect(page.locator('meta[name="robots"][content="noindex"]')).toHaveCount(1);
  });

  test("the slash key jumps to the search field", async ({ page, isMobile }) => {
    test.skip(isMobile, "There is no physical keyboard on a phone");
    await page.goto("/");
    await page.keyboard.press("/");

    await expect(page.getByLabel("GitHub kullanıcı adı")).toBeFocused();
  });

  test("a visitor sees the actions tab locked and a sign-in link", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    await page.getByRole("tab", { name: /Aksiyonlar/ }).click();

    await expect(page.getByRole("heading", { name: "Aksiyonların kilidini aç" })).toBeVisible();
    await expect(page.getByRole("link", { name: "GitHub ile giriş yap" }).first()).toHaveAttribute("href", /\/api\/v1\/auth\/github$/);
  });

  test("unavailable AI is flagged on its tab and can be retried", async ({ page }) => {
    await signInAs(page, { aiOff: true });
    await page.goto(`/u/${OWNER}`);

    await expect(page.getByRole("tab", { name: /AI Yorumu/ })).toContainText("(şu anda kullanılamıyor)");
    await page.getByRole("tab", { name: /AI Yorumu/ }).click();
    await expect(page.getByRole("button", { name: "AI yorumunu yeniden dene" })).toBeVisible();
  });
});

test.describe("signed-in owner", () => {
  test.beforeEach(async ({ page }) => signInAs(page));

  test("sees their workspace: progress history, AI suggestions and the action plan", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    await expect(page.getByText("Senin portföyün")).toBeVisible();
    await page.getByRole("tab", { name: /Aksiyonlar/ }).click();

    await expect(page.getByRole("heading", { name: "İlerleme" })).toBeVisible();
    await expect(page.getByText("Yeni karşılanan kriterler: Lisans dosyası")).toBeVisible();
    await expect(page.getByRole("img", { name: /Skor geçmişi/ })).toBeVisible();

    await page.getByRole("button", { name: "Öneri oluştur" }).click();
    await expect(page.getByText("CI iş akışı ekle")).toBeVisible();
    await expect(page.getByText("Temel kanıt: CI iş akışı")).toBeVisible();
  });

  test("adds, advances and removes an action plan task", async ({ page }) => {
    await page.goto(`/u/${OWNER}`);
    await page.getByRole("tab", { name: /Aksiyonlar/ }).click();

    await page.getByPlaceholder("ör. README kullanım bölümünü geliştir").fill("README kullanımını genişlet");
    await page.getByRole("button", { name: "Görev ekle" }).click();
    await expect(page.getByLabel("Görev başlığı").first()).toHaveValue("README kullanımını genişlet");

    await page.getByLabel("Görev durumu").first().selectOption("done");
    await expect(page.getByLabel("Görev durumu").first()).toHaveValue("done");

    await page.getByRole("button", { name: "Sil" }).first().click();
    await expect(page.getByLabel("Görev başlığı")).toHaveCount(0);
  });
});
