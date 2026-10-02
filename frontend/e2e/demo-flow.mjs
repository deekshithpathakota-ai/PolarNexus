// End-to-end check of the SIH26063 showcase flow plus a smoke test of every page.
// Usage:  BASE_URL=http://localhost:3000 node e2e/demo-flow.mjs
// Optional: CHROMIUM_PATH=/path/to/chrome  SHOTS=./e2e/shots
import { chromium } from "playwright";
import fs from "node:fs";

const B = process.env.BASE_URL || "http://localhost:3000";
const S = (process.env.SHOTS || "./e2e/shots").replace(/\/$/, "") + "/";
fs.mkdirSync(S, { recursive: true });
const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
p.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
p.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource: the server responded with a status of 404/.test(m.text())) errs.push(m.text().slice(0, 200)); });
let failed = 0;
const step = async (n, fn) => {
  try { await fn(); console.log("OK  ", n); }
  catch (e) { failed++; console.log("FAIL", n, e.message.split("\n")[0]); await p.screenshot({ path: S + "fail-" + n.replace(/\W+/g, "_") + ".png" }).catch(() => {}); }
};

await step("1 home", async () => { await p.goto(B + "/", { waitUntil: "networkidle" }); await p.getByText("Explore India").first().waitFor(); });
await step("2 search", async () => {
  const i = p.getByRole("combobox").first();
  await i.fill("Antarctic sea ice"); await i.press("Enter");
  await p.waitForURL(/explore\?q=/);
  await p.getByText("Antarctic Sea Ice Variability Study").first().waitFor({ timeout: 20000 });
  await p.screenshot({ path: S + "02-explore.png" });
});
await step("2b filter = Dataset", async () => {
  await p.getByLabel("Dataset").first().click(); await p.waitForURL(/type=Dataset/); await p.waitForTimeout(1500);
  if (!(await p.locator('main a[href^="/datasets/"]').count())) throw new Error("no dataset results");
  const docs = await p.locator('main a[href^="/resources/"]').count();
  if (docs) throw new Error("filter leaked documents " + docs);
});
await step("3 open resource", async () => {
  await p.goto(B + "/resources/antarctic-sea-ice-variability-study", { waitUntil: "networkidle" });
  await p.getByRole("heading", { name: "Antarctic Sea Ice Variability Study" }).waitFor();
  await p.screenshot({ path: S + "03-resource.png", fullPage: true });
});
await step("4-6 ask AI + citations", async () => {
  await p.getByRole("button", { name: /Ask .* AI/ }).first().click();
  await p.getByPlaceholder(/Ask about this document/).fill("Explain the key factors discussed in this resource.");
  await p.getByRole("button", { name: "Ask", exact: true }).click();
  await p.getByText("Evidence used").waitFor({ timeout: 20000 });
  await p.getByText("Strong repository evidence").first().waitFor();
  await p.locator('button[aria-label^="Open source 1"]').first().click();
  await p.getByText("Open source record").first().waitFor();
  await p.screenshot({ path: S + "04-answer.png", fullPage: true });
});
await step("insufficient evidence", async () => {
  await p.goto(B + "/assistant?q=" + encodeURIComponent("Who won the cricket world cup in 2011?"), { waitUntil: "networkidle" });
  await p.getByText("Insufficient repository evidence").first().waitFor({ timeout: 20000 });
});
await step("summary", async () => {
  await p.goto(B + "/resources/antarctic-sea-ice-variability-study?tab=summaries", { waitUntil: "networkidle" });
  await p.getByRole("button", { name: "Key Findings" }).click(); await p.getByText("Sections used").waitFor();
});
await step("login researcher", async () => { await p.goto(B + "/login", { waitUntil: "networkidle" }); await p.getByRole("button", { name: /Researcher Demo/ }).click(); await p.waitForURL(B + "/"); });
await step("7-9 generate student draft", async () => {
  await p.goto(B + "/studio?type=document&slug=antarctic-sea-ice-variability-study", { waitUntil: "networkidle" });
  await p.getByText("Antarctic Sea Ice Variability Study").first().waitFor();
  await p.getByRole("button", { name: /^Student/ }).click();
  await p.getByRole("button", { name: "Generate draft" }).click();
  await p.waitForURL(/studio\?id=/, { timeout: 20000 });
  await p.getByText("What is this about?").waitFor();
  await p.getByRole("tab", { name: "Evidence check" }).click();
  await p.getByText(/Evidence check passed|review warnings|issues found/).waitFor();
  await p.screenshot({ path: S + "05-studio.png", fullPage: true });
});
await step("10 submit for review", async () => { await p.getByRole("button", { name: "Submit for review" }).click(); await p.getByText("Waiting for editorial review").waitFor(); });
await step("11 editor opens review", async () => {
  await p.getByRole("button", { name: /Switch to Editor/ }).click();
  await p.waitForURL(/review\?item=/, { timeout: 15000 });
  await p.getByRole("button", { name: "Approve" }).waitFor({ timeout: 15000 });
  await p.screenshot({ path: S + "06-review.png", fullPage: true });
});
await step("12 approve", async () => { await p.getByRole("button", { name: "Approve" }).click(); await p.getByRole("button", { name: "Publish / Disseminate" }).waitFor(); });
await step("13 publish", async () => {
  await p.getByRole("button", { name: "Publish / Disseminate" }).click();
  await p.getByLabel(/linkedin/i).check();
  await p.getByRole("dialog").getByRole("button", { name: "Publish" }).click();
  await p.getByText(/Published to website, linkedin/).waitFor();
});
await step("outreach feed", async () => { await p.goto(B + "/outreach", { waitUntil: "networkidle" }); await p.getByText("For Students: Antarctic Sea Ice Variability Study").first().waitFor(); });
await step("admin analytics", async () => {
  await p.goto(B + "/login"); await p.getByRole("button", { name: /Administrator Demo/ }).click(); await p.waitForURL(B + "/");
  await p.goto(B + "/admin", { waitUntil: "networkidle" }); await p.getByText("Usage trends").waitFor(); await p.waitForTimeout(800);
  await p.screenshot({ path: S + "07-admin.png", fullPage: true });
});
const pages = [
  ["explore", "/explore", "Explore Polar Knowledge"], ["documents", "/documents", "Documents"], ["datasets", "/datasets", "Datasets"],
  ["dataset-detail", "/datasets/antarctic-sea-ice-observations", "Antarctic Sea Ice Observations"], ["media", "/media", "Photographs"],
  ["media-detail", "/media/aurora-australis-over-bharati", "Aurora australis"], ["expeditions", "/expeditions", "Expedition Explorer"],
  ["expedition-detail", "/expeditions/isea-43", "Antarctic Expedition 43"], ["stations", "/stations", "Research Stations"],
  ["station-detail", "/stations/maitri", "Station facts"], ["map", "/map", "Polar Map"], ["learn", "/learn", "Learn Polar Science"],
  ["researcher", "/researchers/ananya-rao", "Dr. Ananya Rao"], ["assistant", "/assistant", "How answers are made"],
  ["workspace", "/workspace", "Upload a document"], ["repository", "/admin/repository", "Repository Management"],
  ["users", "/admin/users", "Users & Roles"], ["analytics", "/admin/analytics", "Discovery & AI usage"], ["audit", "/admin/audit", "Audit Logs"],
  ["health", "/admin/health", "System Health"], ["my-knowledge", "/my-knowledge", "My Knowledge"], ["review", "/review", "Review Center"],
  ["studio", "/studio", "Content Studio"], ["resource-404", "/resources/does-not-exist", "Not found"], ["page-404", "/nonexistent-page", "Resource Not Found"],
];
for (const [n, u, t] of pages) {
  await step("page " + n, async () => {
    await p.goto(B + u, { waitUntil: "networkidle" }); await p.getByText(t).first().waitFor({ timeout: 20000 }); await p.waitForTimeout(400);
    await p.screenshot({ path: S + "p-" + n + ".png", fullPage: true });
  });
}
// mobile overflow check
const m = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
for (const u of ["/", "/explore?q=sea%20ice", "/resources/antarctic-sea-ice-variability-study", "/datasets/antarctic-sea-ice-observations", "/map", "/assistant", "/expeditions", "/stations/maitri", "/learn", "/outreach"]) {
  await step("mobile " + u, async () => {
    await m.goto(B + u, { waitUntil: "networkidle" }); await m.waitForTimeout(600);
    const over = await m.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    await m.screenshot({ path: S + "m-" + (u.replace(/\W+/g, "_") || "home") + ".png", fullPage: false });
    if (over > 1) throw new Error("horizontal overflow " + over + "px");
  });
}
console.log("CONSOLE/PAGE ERRORS", errs.length, JSON.stringify(errs.slice(0, 10)));
console.log(failed ? `${failed} step(s) failed` : "ALL STEPS PASSED");
await b.close();
process.exit(failed ? 1 : 0);
