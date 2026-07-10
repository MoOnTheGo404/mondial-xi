import { test, expect, type Page } from "@playwright/test";

// Collect console errors on every page we visit; fail on unexpected ones.
function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

const noCritical = (errors: string[]) =>
  errors.filter(
    (e) =>
      !e.includes("favicon") && // benign missing favicon in dev
      !e.includes("Download the React DevTools"),
  );

test("home page shows system status, fixtures and championship odds", async ({
  page,
}) => {
  const errors = watchConsole(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    /who lifts the trophy/i,
  );
  await expect(page.getByText("matches", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /championship probabilities/i }),
  ).toBeVisible({ timeout: 20_000 });
  // real data cutoff stamp visible
  await expect(page.getByText(/data cutoff/i).first()).toBeVisible();
  expect(noCritical(errors)).toEqual([]);
});

test("browse fixtures → open match center → prediction present", async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto("/fixtures");
  await expect(page.getByRole("heading", { name: /fixtures/i })).toBeVisible();
  const link = page.getByRole("link", { name: /match center/i }).first();
  await link.click();
  await expect(page).toHaveURL(/\/match\//);
  await expect(page.getByRole("heading", { name: /^forecast$/i })).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText(/model 20/)).toBeVisible(); // model version stamp
  await expect(
    page.getByRole("heading", { name: "Scorelines", exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/data quality [A-D]/i).first()).toBeVisible();
  expect(noCritical(errors)).toEqual([]);
});

test("match lab: remove a player, forecast shifts, restore resets, URL is shareable", async ({
  page,
}) => {
  test.slow();
  await page.goto("/lab?home=norway&away=england&neutral=true");
  await expect(page.getByRole("heading", { name: /match lab/i })).toBeVisible();

  // wait for baseline forecast
  await expect(page.getByRole("heading", { name: /^forecast$/i })).toBeVisible({
    timeout: 25_000,
  });
  const baseline = await page
    .locator("dt, .font-mono", { hasText: "" })
    .first()
    .textContent();
  expect(baseline).not.toBeNull();

  // mark Haaland out
  const haalandRow = page.locator("li", { hasText: "Erling Haaland" }).first();
  await haalandRow.getByRole("button", { name: "Out" }).click();

  // scenario banner appears + URL captures assumption
  await expect(page.getByText(/scenario-adjusted forecast/i)).toBeVisible({
    timeout: 25_000,
  });
  await expect(page).toHaveURL(/hs=norway%2Ferling-haaland%3Aout|hs=norway\/erling-haaland:out/);
  await expect(
    page.getByText(/Erling Haaland marked unavailable \(user scenario\)/i),
  ).toBeVisible();

  // reset restores the provider baseline
  await page.getByRole("button", { name: /reset assumptions/i }).click();
  await expect(page.getByText(/scenario-adjusted forecast/i)).toBeHidden({
    timeout: 25_000,
  });
});

test("scenario URL reload reproduces the scenario", async ({ page }) => {
  await page.goto("/lab?home=norway&away=england&neutral=true&hs=norway%2Ferling-haaland%3Aout");
  await expect(page.getByText(/scenario-adjusted forecast/i)).toBeVisible({
    timeout: 25_000,
  });
  const outBtn = page
    .locator("li", { hasText: "Erling Haaland" })
    .first()
    .getByRole("button", { name: "Out" });
  await expect(outBtn).toHaveAttribute("aria-pressed", "true");
});

test("scenario compare shows side-by-side deltas", async ({ page }) => {
  test.slow();
  await page.goto(
    "/compare?home=argentina&away=france&neutral=true&bh=argentina%2Flionel-messi%3Aout",
  );
  await expect(page.getByRole("heading", { name: /scenario compare/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /what changed/i })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/lionel-messi newly assumed/i)).toBeVisible();
  // delta shown in percentage points
  await expect(page.getByText(/pp$/).first()).toBeVisible();
});

test("tournament simulator: run, lock an upset, probabilities change", async ({
  page,
}) => {
  test.slow();
  const errors = watchConsole(page);
  await page.goto("/simulator");
  await expect(
    page.getByRole("heading", { name: /advancement probabilities/i }),
  ).toBeVisible({ timeout: 30_000 });

  // France row shows a championship probability
  const franceRow = page.locator("tr", { hasText: "France" }).first();
  await expect(franceRow).toBeVisible();
  const before = await franceRow.locator("td").last().textContent();

  // in the knockout bracket, pick Morocco to beat France in the QF
  await page.getByRole("heading", { name: /knockout bracket/i }).scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: /lock morocco to win/i }).click();
  await expect(page.getByRole("button", { name: /clear 1 lock/i })).toBeVisible();
  await page.getByRole("button", { name: /re-run/i }).click();

  await expect(async () => {
    const after = await page
      .locator("tr", { hasText: "France" })
      .first()
      .locator("td")
      .last()
      .textContent();
    expect(after).toBe("—"); // France cannot win after a locked QF exit
  }).toPass({ timeout: 30_000 });
  expect(before).not.toBe("—");
  expect(noCritical(errors)).toEqual([]);
});

test("team explorer → team profile with Elo chart and history", async ({ page }) => {
  await page.goto("/teams");
  const brazil = page.getByRole("link", { name: /brazil/i }).first();
  await brazil.waitFor({ state: "visible" });
  await brazil.click();
  await expect(page).toHaveURL(/\/team\/brazil/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: /elo history/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /record by venue/i })).toBeVisible();
  // venue filter works
  await page.getByRole("button", { name: "neutral" }).click();
  await expect(page.getByText(/neutral/i).first()).toBeVisible();
});

test("player explorer → profile with honest availability", async ({ page }) => {
  await page.goto("/players?");
  await page.getByPlaceholder("Search players…").fill("Haaland");
  await page.getByRole("link", { name: /haaland/i }).first().click();
  await expect(page).toHaveURL(/\/player\/norway/);
  await expect(page.getByText(/estimated impact/i)).toBeVisible();
  await expect(page.getByText("unknown").first()).toBeVisible(); // availability
  await expect(page.getByText(/not an overall player-quality rating/i)).toBeVisible();
});

test("prediction archive separates sealed forecasts from backtests", async ({ page }) => {
  await page.goto("/archive");
  await expect(
    page.getByRole("heading", { name: /graded forecasts/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /historical backtest/i }),
  ).toBeVisible();
  await expect(page.getByText(/sealed as a content-hashed snapshot/i).first()).toBeVisible();
  await expect(page.getByText(/hash [0-9a-f]+/i).first()).toBeVisible();
});

test("performance page loads artifact-driven metrics", async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto("/performance");
  await expect(page.getByRole("heading", { name: /chronological protocol/i })).toBeVisible();
  await expect(page.getByText("UNTOUCHED TEST", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /model comparison/i })).toBeVisible();
  await expect(page.getByText("champion").first()).toBeVisible();
  expect(noCritical(errors)).toEqual([]);
});

test("keyboard navigation: skip link and focusable nav", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /skip to content/i })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /mondial xi home/i })).toBeFocused();
});

test("mobile navigation works @mobile", async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto("/");
  await page.getByRole("button", { name: /menu/i }).click();
  await page.getByRole("navigation", { name: /primary mobile/i }).getByRole("link", { name: /simulator/i }).click();
  await expect(page).toHaveURL(/\/simulator/);
  await expect(
    page.getByRole("heading", { name: /world cup 2026 simulator/i }),
  ).toBeVisible();
  expect(noCritical(errors)).toEqual([]);
});

test("2030 outlook: assumptions visible, qualification + title odds render", async ({
  page,
}) => {
  test.slow();
  await page.goto("/simulator/2030");
  await expect(page.getByText(/outlook — assumptions apply/i)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /championship probabilities \(2030 outlook\)/i }),
  ).toBeVisible({ timeout: 60_000 });
  await expect(
    page.getByRole("heading", { name: /qualification probabilities/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /assumptions behind this outlook/i }),
  ).toBeVisible();
  // hosts marked auto
  await expect(page.getByText("auto").first()).toBeVisible();
});
