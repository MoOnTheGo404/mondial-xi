import { test } from "@playwright/test";
import fs from "node:fs";

/**
 * Visual QA: capture every major page at desktop/tablet/mobile widths into
 * docs/screenshots. Run via `make screenshots` (requires API+web running).
 */

const OUT = "../../docs/screenshots";

const PAGES: { name: string; path: string; settle?: number }[] = [
  { name: "home", path: "/", settle: 6000 },
  { name: "fixtures", path: "/fixtures" },
  { name: "match-center", path: "__FIRST_MATCH__", settle: 4000 },
  { name: "match-lab", path: "/lab?home=norway&away=england&neutral=true&hs=norway%2Ferling-haaland%3Aout", settle: 6000 },
  { name: "compare", path: "/compare?home=argentina&away=france&neutral=true&bh=argentina%2Flionel-messi%3Aout", settle: 8000 },
  { name: "simulator", path: "/simulator", settle: 8000 },
  { name: "simulator-2030", path: "/simulator/2030", settle: 12000 },
  { name: "teams", path: "/teams" },
  { name: "team-profile", path: "/team/brazil", settle: 4000 },
  { name: "players", path: "/players" },
  { name: "player-profile", path: "/player/norway/erling-haaland", settle: 4000 },
  { name: "archive", path: "/archive" },
  { name: "performance", path: "/performance", settle: 4000 },
  { name: "methodology", path: "/methodology" },
];

const VIEWPORTS = [
  { tag: "desktop", width: 1440, height: 900 },
  { tag: "tablet", width: 834, height: 1112 },
  { tag: "mobile", width: 390, height: 844 },
];

test.describe.configure({ mode: "serial" });

for (const vp of VIEWPORTS) {
  test(`screenshots @ ${vp.tag}`, async ({ page, request }) => {
    test.setTimeout(300_000);
    fs.mkdirSync(OUT, { recursive: true });
    await page.setViewportSize({ width: vp.width, height: vp.height });

    const fixtures = await (
      await request.get("http://localhost:8000/api/v1/fixtures?status=upcoming&limit=1")
    ).json();
    const matchPath = `/match/${fixtures.fixtures[0].match_id}`;

    for (const p of PAGES) {
      const path = p.path === "__FIRST_MATCH__" ? matchPath : p.path;
      await page.goto(path, { waitUntil: "networkidle" });
      if (p.settle) await page.waitForTimeout(p.settle);
      await page.screenshot({
        path: `${OUT}/${p.name}-${vp.tag}.png`,
        fullPage: vp.tag === "desktop",
      });
    }
  });
}
