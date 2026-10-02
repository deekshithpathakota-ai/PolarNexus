// End-to-end check of the v3 demonstration path:
// Sign-in (premium page, reduced motion, mobile) → search with "why matched" → public-source dataset → AI teacher mode
// with evidence strength → Research Story → visual media search → dataset ingestion (CSV analyse → confirm → explore)
// → campaign planner (scheduling blocked until approval) → content calendar → outreach analytics (DEMO METRICS)
// → admin platform health, plus smoke and 390 px overflow checks for every new page.
// Usage:  BASE_URL=http://localhost:3000 node e2e/v3-journey.mjs     (optional CHROMIUM_PATH, SHOTS)
import { chromium } from "playwright";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const B = process.env.BASE_URL || "http://localhost:3000";
const S = (process.env.SHOTS || "./e2e/shots").replace(/\/$/, "") + "/";
fs.mkdirSync(S, { recursive: true });
const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const errs = [];
const watch = (pg) => {
  pg.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
  pg.on("console", (m) => { if (m.type() === "error" && !/status of 40[134]/.test(m.text())) errs.push(m.text().slice(0, 200)); });
};
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
watch(p);
let failed = 0;
const step = async (n, fn) => {
  try { await fn(); console.log("OK  ", n); }
  catch (e) { failed++; console.log("FAIL", n, e.message.split("\n")[0]); await p.screenshot({ path: S + "v3-fail-" + n.replace(/\W+/g, "_") + ".png" }).catch(() => {}); }
};
const go = (u) => p.goto(B + u, { waitUntil: "networkidle" });

await step("01 premium sign-in renders and logs in (researcher)", async () => {
  await go("/login");
  await p.getByRole("heading", { name: /AI-powered polar science knowledge and outreach/ }).waitFor();
  await p.locator("canvas").first().waitFor();
  await p.screenshot({ path: S + "v3-01-login.png" });
  await p.getByRole("button", { name: /Researcher Demo/ }).click(); await p.waitForURL(B + "/");
});
await step("02 email/password sign-in still works", async () => {
  const c = await b.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: "reduce" });
  const q = await c.newPage(); watch(q);
  await q.goto(B + "/login", { waitUntil: "networkidle" });
  const anim = await q.evaluate(() => getComputedStyle(document.querySelector(".pn-aurora")).animationName);
  if (anim !== "none") throw new Error("aurora still animated under reduced motion: " + anim);
  await q.getByLabel("Email").fill("editor@polarnexus.demo"); await q.getByLabel("Password").fill("polarnexus-demo");
  await q.getByRole("button", { name: "Sign in", exact: true }).click(); await q.waitForURL(B + "/");
  await c.close();
});
await step("03 search explains why results matched", async () => {
  await go("/explore?q=" + encodeURIComponent("Antarctic sea ice"));
  await p.getByText("Why this matched:").first().waitFor();
  await p.getByText("Public source").first().waitFor();
});
await step("04 public-source NSIDC dataset with trust panels", async () => {
  await go("/datasets/nsidc-sea-ice-index-antarctic-september-extent");
  await p.getByText("Public source").first().waitFor();
  await p.getByText("Scientific trust").waitFor();
  await p.getByRole("tab", { name: "Versions" }).click(); await p.getByText(/Imported from S_09_extent_v4.0.csv/).waitFor();
  await p.getByRole("tab", { name: "Metadata" }).click(); await p.getByText("Missing — not recorded").first().waitFor().catch(() => p.getByText("Not recorded").first().waitFor());
  if (await p.getByRole("tab", { name: "Geographic" }).count()) throw new Error("map offered for a dataset without coordinates");
  await p.screenshot({ path: S + "v3-04-dataset.png", fullPage: true });
});
await step("05 AI teacher mode with evidence strength + pipeline", async () => {
  await go("/assistant");
  await p.getByText("Teacher", { exact: true }).click();
  await p.getByLabel("Ask PolarNexus AI").fill("What factors influence Antarctic sea-ice variability?");
  await p.keyboard.press("Enter");
  await p.getByText("Teaching points").first().waitFor({ timeout: 20000 });
  await p.getByText(/repository evidence/).first().waitFor();
  await p.getByText("Every supporting passage comes from prototype demonstration records", { exact: false }).first().waitFor();
  await p.getByText("How this answer was produced").first().click();
  await p.getByText("Citation validation").first().waitFor();
});
await step("06 research story (demo) with explanations, timeline and map", async () => {
  await go("/stories");
  await p.locator("a[href^='/stories/']:not([href='/stories/new'])").first().click();
  await p.getByRole("tab", { name: "Student explanation" }).click();
  await p.getByText("Words to know").first().waitFor().catch(() => {});
  await p.getByText("Timeline").first().waitFor(); await p.getByText("Evidence basis").waitFor();
  await p.screenshot({ path: S + "v3-06-story.png", fullPage: true });
});
await step("07 build a new research story from a dataset", async () => {
  await go("/stories/new?type=dataset&slug=nsidc-sea-ice-index-antarctic-september-extent");
  await p.getByRole("list", { name: "Story chain" }).waitFor();
  await p.getByRole("button", { name: /Create story/ }).click();
  await p.waitForURL(/\/stories\/(?!new)/); await p.getByText("draft").first().waitFor();
});
await step("08 visual media search", async () => {
  await go("/visual-search");
  await p.getByLabel("Describe the image").fill("iceberg near a research vessel");
  await p.getByRole("button", { name: "Search", exact: true }).click();
  await p.getByText(/sim 0\.\d\d|not available|No photograph/).first().waitFor({ timeout: 30000 });
  await p.screenshot({ path: S + "v3-08-visual.png" });
});
await step("09 dataset ingestion: analyse → confirm → explore", async () => {
  const f = path.join(os.tmpdir(), "pn-e2e-buoy.csv");
  fs.writeFileSync(f, "station,date,latitude,longitude,temp_c\nA,2024-01-01,-69.4,76.2,-1.2\nA,2024-01-02,-69.4,76.2,-1.1\nB,2024-01-03,-69.5,76.3,-0.9\n");
  await go("/workspace"); await p.getByText("Dataset (CSV · JSON)").click();
  await p.locator("input[type=file][accept*='.csv']").setInputFiles(f);
  await p.getByRole("button", { name: "Analyse file" }).click();
  await p.getByText("Detected schema").waitFor();
  await p.getByLabel("Unit for temp_c").fill("°C");
  const keep = p.getByRole("button", { name: "Keep both" });
  if (await keep.count()) await keep.click();
  await p.getByRole("button", { name: /Confirm & register dataset/ }).click();
  await p.getByRole("link", { name: "Explore dataset" }).waitFor({ timeout: 30000 });
  await p.getByRole("link", { name: "Explore dataset" }).click();
  await p.getByText("Schema & validation report").waitFor();
  await p.getByText("User uploaded").first().waitFor();
});
await step("10 campaign planner respects review", async () => {
  await go("/campaigns"); await p.getByText("Antarctic Science Week 2026 (demo)").click();
  await p.getByText("Demonstration campaign").waitFor();
  await p.getByRole("tab", { name: "List" }).click();
  await p.getByText("prototype simulation").first().waitFor();
  await p.getByRole("button", { name: /Expedition Story/ }).first().click();
  const sched = p.getByRole("button", { name: "Schedule" });
  if ((await sched.count()) && (await sched.isEnabled())) throw new Error("unapproved content can be scheduled");
  await p.getByText(/must be approved|Submit it for review/).first().waitFor();
  await p.keyboard.press("Escape");
});
await step("11 content calendar", async () => { await go("/calendar"); await p.getByRole("heading", { name: "Content Calendar" }).waitFor(); });
await step("12 outreach analytics labels demo metrics", async () => {
  await go("/outreach-analytics"); await p.getByText("DEMO METRICS").first().waitFor();
  await p.getByLabel("Include demonstration metrics").uncheck(); await p.getByText("LIVE METRICS").first().waitFor();
});
await step("13 admin platform health", async () => {
  await go("/login"); await p.getByRole("button", { name: /Administrator Demo/ }).click(); await p.waitForURL(B + "/");
  await go("/admin"); for (const t of ["Repository health", "AI health", "Data quality"]) await p.getByRole("heading", { name: t }).waitFor();
  await p.screenshot({ path: S + "v3-13-admin.png", fullPage: true });
});

for (const u of ["/stories", "/campaigns", "/calendar", "/visual-search", "/outreach-analytics", "/media", "/media/rv-polarstern-in-sea-ice-mosaic-2020",
  "/resources/indian-antarctic-act-2022", "/datasets/nsidc-sea-ice-index-arctic-september-extent", "/workspace", "/admin", "/login"]) {
  await step("mobile " + u, async () => {
    const m = await b.newPage({ viewport: { width: 390, height: 844 } }); watch(m);
    if (u !== "/login") { await m.goto(B + "/login", { waitUntil: "networkidle" }); await m.getByRole("button", { name: /Administrator Demo/ }).click(); await m.waitForURL(B + "/"); }
    await m.goto(B + u, { waitUntil: "networkidle" }); await m.waitForTimeout(500);
    const over = await m.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    await m.close();
    if (over > 1) throw new Error("horizontal overflow " + over + "px");
  });
}
console.log("CONSOLE/PAGE ERRORS", errs.length, JSON.stringify(errs.slice(0, 10)));
console.log(failed ? `${failed} step(s) failed` : "ALL STEPS PASSED");
await b.close();
process.exit(failed || errs.length ? 1 : 0);
