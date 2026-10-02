// End-to-end check of the complete SIH26063 lifecycle added in v2, plus smoke + mobile checks for the new pages.
// Login → search → resource → provenance → dataset → expedition → media → AI (cited) → Turn Research Into Outreach →
// public explanation → evidence check → submit → approve → publish (simulated social) → audit log → analytics/impact.
// Usage:  BASE_URL=http://localhost:3000 node e2e/sih-journey.mjs     (optional CHROMIUM_PATH, SHOTS)
import { chromium } from "playwright";
import fs from "node:fs";

const B = process.env.BASE_URL || "http://localhost:3000";
const S = (process.env.SHOTS || "./e2e/shots").replace(/\/$/, "") + "/";
fs.mkdirSync(S, { recursive: true });
const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
p.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
p.on("console", (m) => { if (m.type() === "error" && !/status of 404/.test(m.text())) errs.push(m.text().slice(0, 200)); });
let failed = 0;
const step = async (n, fn) => {
  try { await fn(); console.log("OK  ", n); }
  catch (e) { failed++; console.log("FAIL", n, e.message.split("\n")[0]); await p.screenshot({ path: S + "j-fail-" + n.replace(/\W+/g, "_") + ".png" }).catch(() => {}); }
};
const go = (u) => p.goto(B + u, { waitUntil: "networkidle" });
let contentUrl = "";

await step("01 login (researcher)", async () => {
  await go("/login"); await p.getByRole("button", { name: /Researcher Demo/ }).click(); await p.waitForURL(B + "/");
});
await step("02 search 'Antarctic sea ice' across types", async () => {
  await go("/explore?q=" + encodeURIComponent("Antarctic sea ice"));
  await p.getByText("Antarctic Sea Ice Variability Study").first().waitFor({ timeout: 20000 });
  await p.getByRole("navigation", { name: "Results by resource type" }).getByText(/Datasets/).waitFor();
  await p.screenshot({ path: S + "j02-search.png" });
});
await step("03 open research resource", async () => {
  await p.locator('main a[href="/resources/antarctic-sea-ice-variability-study"]').first().click();
  await p.getByRole("heading", { name: "Antarctic Sea Ice Variability Study", level: 1 }).waitFor();
});
await step("04 view provenance (demo label shown)", async () => {
  await p.getByRole("heading", { name: /Data Provenance/ }).waitFor();
  await p.getByText("Prototype demonstration document").first().waitFor();
  await p.screenshot({ path: S + "j04-provenance.png", fullPage: true });
});
await step("05 open related dataset", async () => {
  await p.locator('main a[href="/datasets/antarctic-sea-ice-observations"]').first().click();
  await p.getByRole("heading", { name: "Antarctic Sea Ice Observations" }).waitFor();
  await p.getByText("Synthetic demonstration").first().waitFor();
  await p.getByText("Variables, units & completeness").waitFor();
});
await step("06 open expedition", async () => {
  await p.locator('main a[href="/expeditions/isea-43"]').first().click();
  await p.getByRole("heading", { name: "Antarctic Expedition 43", level: 1 }).waitFor();
  await p.getByRole("heading", { name: "Knowledge Timeline" }).waitFor();
  await p.locator('ol[aria-label="Knowledge timeline"] a').first().waitFor();
});
await step("07 open media", async () => {
  await p.locator('main a[href^="/media/"]').first().click();
  await p.waitForURL(/\/media\//);
  await p.getByRole("heading", { name: /Data Provenance/ }).waitFor();
});
await step("08 ask AI (cross-modal) and receive cited answer", async () => {
  await go("/assistant?q=" + encodeURIComponent("How has Antarctic sea ice changed and which expeditions studied it?"));
  await p.getByText("Evidence used").waitFor({ timeout: 20000 });
  await p.getByText("Expeditions connected to this evidence").waitFor();
  await p.getByText("Related knowledge").first().waitFor();
  await p.locator('button[aria-label^="Open source 1"]').first().click();
  await p.getByText("Open source record").first().waitFor();
  await p.screenshot({ path: S + "j08-ai.png", fullPage: true });
});
await step("09 Turn Research Into Outreach", async () => {
  await go("/resources/antarctic-sea-ice-variability-study");
  await p.getByRole("button", { name: "Turn Research Into Outreach" }).click();
  await p.waitForURL(/studio\?type=document&slug=antarctic-sea-ice-variability-study/);
  await p.getByText("Antarctic Sea Ice Variability Study").first().waitFor();
});
await step("10 generate public explanation", async () => {
  await p.getByRole("button", { name: /^Public/ }).click();
  await p.getByRole("radio", { name: "General Public" }).waitFor();
  await p.getByRole("button", { name: "Generate draft" }).click();
  await p.waitForURL(/studio\?id=/, { timeout: 20000 });
  contentUrl = p.url();
  await p.getByText("In Plain Language").first().waitFor();
  await p.getByRole("list", { name: "Research-to-outreach workflow" }).waitFor();
});
await step("11 run evidence check", async () => {
  await p.getByRole("button", { name: "Run evidence check" }).click();
  await p.getByText(/Evidence check passed|review warnings|issues found/).waitFor();
  await p.screenshot({ path: S + "j11-evidence.png", fullPage: true });
});
await step("12 submit for review", async () => {
  await p.getByRole("button", { name: "Submit for review" }).click();
  await p.getByText("Waiting for editorial review").waitFor();
});
await step("13 approve (editor)", async () => {
  await p.getByRole("button", { name: /Switch to Editor/ }).click();
  await p.waitForURL(/review\?item=/, { timeout: 15000 });
  await p.getByRole("button", { name: "Approve" }).click();
  const confirm = p.getByRole("dialog").getByRole("button", { name: /Approve/ });
  if (await confirm.count()) await confirm.first().click();
  await p.getByRole("button", { name: "Publish / Disseminate" }).waitFor({ timeout: 15000 });
});
await step("14 publish (website live, LinkedIn simulated)", async () => {
  await p.getByRole("button", { name: "Publish / Disseminate" }).click();
  await p.getByText("Connector ready").first().waitFor();
  await p.getByLabel(/linkedin/i).check();
  await p.getByRole("dialog").getByRole("button", { name: "Publish" }).click();
  await p.getByText(/social channels: prototype simulation/).waitFor();
  const id = contentUrl.split("id=")[1];
  await go("/outreach/" + id);
  await p.getByText("Simulated").first().waitFor();
  await p.getByText("Live").first().waitFor();
});
await step("15 view audit log", async () => {
  await go("/login"); await p.getByRole("button", { name: /Administrator Demo/ }).click(); await p.waitForURL(B + "/");
  await go("/admin/audit?q=");
  await p.getByRole("combobox", { name: "Action" }).selectOption("content_publish");
  await p.getByText("content_publish").nth(1).waitFor();
});
await step("16 view analytics & impact", async () => {
  await go("/admin/analytics"); await p.getByText("Discovery & AI usage").waitFor();
  await go("/impact"); await p.getByText("Prototype Demonstration Metrics").first().waitFor();
  await p.getByText("Search latency (median)").waitFor();
  await p.screenshot({ path: S + "j16-impact.png", fullPage: true });
});

// ---- smoke: every new page renders
const pages = [
  ["activities", "/activities", "Workshops, Outreach & Institutional Events"],
  ["activity-detail", "/activities/sea-ice-teachers-workshop-2025", "About this activity"],
  ["topic", "/topics/sea-ice", "Knowledge Timeline"],
  ["timeline", "/timeline", "Knowledge Timeline"],
  ["impact", "/impact", "Platform Impact Dashboard"],
  ["provenance-admin", "/admin/provenance", "Provenance & Verification Centre"],
  ["activities-admin", "/admin/activities", "Manage Institutional Activities"],
  ["map-layers", "/map", "activities"],
  ["workspace-media", "/workspace", "Image / Video"],
  ["explore-verification", "/explore?verification=Synthetic", "Verification"],
  ["station-provenance", "/stations/maitri", "Official · verified"],
];
for (const [n, u, t] of pages) {
  await step("page " + n, async () => { await go(u); await p.getByText(t).first().waitFor({ timeout: 20000 }); await p.screenshot({ path: S + "jp-" + n + ".png", fullPage: true }); });
}
await step("language switch (Hindi nav, English default restored)", async () => {
  await go("/");
  await p.getByRole("button", { name: /Interface language/ }).click();
  await p.getByRole("menuitemradio", { name: /हिन्दी/ }).click();
  await p.getByRole("navigation", { name: "Main navigation" }).getByText("संस्थागत गतिविधियाँ").waitFor();
  await p.getByRole("button", { name: /Interface language/ }).click();
  await p.getByRole("menuitemradio", { name: /English/ }).click();
  await p.getByRole("navigation", { name: "Main navigation" }).getByText("Institutional Activities").waitFor();
});

// ---- mobile overflow on the new pages
const m = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true });
for (const u of ["/activities", "/activities/sea-ice-teachers-workshop-2025", "/topics/sea-ice", "/timeline", "/impact", "/outreach", "/resources/antarctic-sea-ice-variability-study", "/media/sea-ice-explainer-video", "/explore?q=sea%20ice"]) {
  await step("mobile " + u, async () => {
    await m.goto(B + u, { waitUntil: "networkidle" }); await m.waitForTimeout(500);
    const over = await m.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    await m.screenshot({ path: S + "jm-" + (u.replace(/\W+/g, "_") || "home") + ".png" });
    if (over > 1) throw new Error("horizontal overflow " + over + "px");
  });
}
console.log("CONSOLE/PAGE ERRORS", errs.length, JSON.stringify(errs.slice(0, 10)));
console.log(failed ? `${failed} step(s) failed` : "ALL STEPS PASSED");
await b.close();
process.exit(failed || errs.length ? 1 : 0);
