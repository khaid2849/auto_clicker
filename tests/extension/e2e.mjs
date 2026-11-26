// End-to-end test of the extension in a real (headless) Chrome.
//   npm install --no-save puppeteer-core
//   CHROME_PATH=/path/to/chrome node tests/extension/e2e.mjs
// Needs Chrome for Testing or Chromium: branded Chrome dropped --load-extension in v137.
import puppeteer from "puppeteer-core";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SRC = fileURLToPath(new URL("../../src/autoclicker/browser_extension", import.meta.url));
const EXT = fs.mkdtempSync(path.join(os.tmpdir(), "autoclicker-ext-"));
const SHOTS = process.env.SCREENSHOTS; // optional folder for screenshots
// Test copy: grant all-sites access up front so automation never hits a permission prompt
fs.cpSync(SRC, EXT, { recursive: true });
const manifest = JSON.parse(fs.readFileSync(`${EXT}/manifest.json`, "utf8"));
manifest.host_permissions = ["<all_urls>"];
fs.writeFileSync(`${EXT}/manifest.json`, JSON.stringify(manifest));

const PAGE = `<!doctype html><html><body style="height:3000px;font:16px sans-serif">
<h1>Test page</h1>
<button id="btn" onclick="window.count=(window.count||0)+1;out.textContent=window.count">Click me</button>
<div id="out">0</div>
<div class="card"><span>a</span><button class="go" data-testid="go-btn">Go</button></div>
<a id="lnk" href="#jumped">link</a>
<button id="far" style="position:absolute;top:2500px" onclick="window.farHits=(window.farHits||0)+1">Far</button>
<script>
  btn.addEventListener('dblclick', () => window.dbl = (window.dbl||0)+1);
  btn.addEventListener('contextmenu', (e) => { e.preventDefault(); window.ctx = (window.ctx||0)+1; });
  btn.addEventListener('mousedown', () => window.md = (window.md||0)+1);
</script></body></html>`;
const server = http.createServer((req, res) => { res.setHeader("content-type", "text/html"); res.end(PAGE); });
await new Promise((r) => server.listen(8765, r));
const URL_ = "http://127.0.0.1:8765/";

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
  headless: true,
  args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`, "--no-sandbox", "--window-size=1200,900"],
  defaultViewport: { width: 1200, height: 800 },
});
const swTarget = await browser.waitForTarget((t) => t.type() === "service_worker" && t.url().endsWith("background.js"));
const extId = new URL(swTarget.url()).host;
const sw = await swTarget.worker();
console.log("extension id:", extId);

const page = await browser.newPage();
await page.goto(URL_);
const tabId = (await sw.evaluate(() => chrome.tabs.query({ url: "http://127.0.0.1:8765/*" })))[0].id;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, extra = "") => { results.push(ok); console.log(`${ok ? "✅" : "❌"} ${name} ${extra}`); };

async function openPopup(query = "") {
  const p = await browser.newPage();
  await p.setViewport({ width: 364, height: 760 });
  await p.goto(`chrome-extension://${extId}/popup.html?tab=${tabId}${query}`);
  await p.waitForSelector("#toggle");
  await sleep(300);
  return p;
}
async function setForm(p, values) {
  await p.evaluate((v) => {
    for (const [id, val] of Object.entries(v)) {
      const el = document.getElementById(id);
      if (el.type === "checkbox") el.checked = val; else el.value = String(val);
      el.dispatchEvent(new Event("change"));
    }
  }, values);
}
const session = () => sw.evaluate(() => chrome.storage.session.get(["jobs", "results"]));
const pageVal = (expr) => page.evaluate(expr);

// 1. Pick an element with the picker (through the popup button)
let popup = await openPopup();
await popup.click("#pick");
await sleep(500);
await page.bringToFront();
const box = await (await page.$("#btn")).boundingBox();
await page.mouse.move(box.x + 5, box.y + 5);
await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
await sleep(200);
if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "picker.png") });
await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
await sleep(500);
const { targets } = await sw.evaluate(() => chrome.storage.local.get("targets"));
const picked = targets?.["http://127.0.0.1:8765"];
check("picker saves the target", picked?.selector === "#btn", JSON.stringify(picked));
check("the picking click does not reach the page", (await pageVal(() => window.count || 0)) === 0);
check("picker cleans up its UI", (await pageVal(() => [...document.querySelectorAll("html > div")].filter((d) => d.style.inset).length)) === 0);

// 2. Run 3 times, once per second, with the tab in the background
popup = await openPopup();
await setForm(popup, { interval: 1, unit: 1, repeat: 3, clickNow: true });
await popup.click("#toggle");
await sleep(600);
if (SHOTS) await popup.screenshot({ path: path.join(SHOTS, "popup_running.png"), fullPage: true });
await sleep(2800);
check("clicks 3 times in a background tab, then stops", (await pageVal(() => window.count)) === 3, `count=${await pageVal(() => window.count)}`);
let s = await session();
check("result = done", s.results?.[tabId]?.reason === "done" && !s.jobs?.[tabId], JSON.stringify(s.results));
if (SHOTS) await popup.screenshot({ path: path.join(SHOTS, "popup_done.png"), fullPage: true });
const msg = await popup.$eval("#message", (el) => el.textContent);
check("popup reports completion", /3/.test(msg), msg);

// 3. Element outside the viewport -> scroll to it, then click
const start = (target, config) => popup.evaluate((tabId, target, config) =>
  chrome.runtime.sendMessage({ type: "start", tabId, target, config }), tabId, target, config);
const base = { interval: 1, unit: 1, jitter: 0, repeat: 1, clickNow: true, button: "left", clicks: 1 };
await start({ mode: "element", selector: "#far" }, base);
await sleep(800);
check("clicks an element outside the viewport", (await pageVal(() => window.farHits)) === 1);

// 4. Double click + right click
await pageVal(() => { window.count = 0; window.scrollTo(0, 0); });
await start({ mode: "element", selector: "#btn" }, { ...base, clicks: 2 });
await sleep(800);
check("double click", (await pageVal(() => window.dbl)) === 1 && (await pageVal(() => window.count)) === 2);
await start({ mode: "element", selector: "#btn" }, { ...base, button: "right" });
await sleep(800);
check("right click", (await pageVal(() => window.ctx)) === 1);

// 5. Position mode (viewport coordinates)
await pageVal(() => { window.count = 0; window.scrollTo(0, 0); });
const b2 = await (await page.$("#btn")).boundingBox();
await start({ mode: "point", x: Math.round(b2.x + 10), y: Math.round(b2.y + 8) }, { ...base, repeat: 2 });
await sleep(1800);
check("position mode", (await pageVal(() => window.count)) === 2, `count=${await pageVal(() => window.count)}`);

// 6. Not found -> error shown, keeps running; Stop -> result stopped
await start({ mode: "element", selector: "#khong-co" }, { ...base, repeat: 0 });
await sleep(700);
s = await session();
check("reports not_found", s.jobs?.[tabId]?.lastError === "not_found");
await popup.reload(); await popup.waitForSelector("#toggle"); await sleep(400);
if (SHOTS) await popup.screenshot({ path: path.join(SHOTS, "popup_error.png"), fullPage: true });
await popup.click("#toggle");
await sleep(400);
s = await session();
check("Stop button", !s.jobs?.[tabId] && s.results?.[tabId]?.reason === "stopped");

// 7. Scheduled start/stop: wait 1 s, click every second, stop 2 s after the start
await pageVal(() => { window.count = 0; window.scrollTo(0, 0); });
const t0 = Date.now();
await popup.evaluate((tabId, when) => chrome.runtime.sendMessage({ type: "start", tabId,
  target: { mode: "element", selector: "#btn" },
  config: { interval: 1, unit: 1, jitter: 0, repeat: 0, clickNow: true, button: "left", clicks: 1 }, when }),
  tabId, { startAt: t0 + 1000, stopAt: t0 + 3000 });
await sleep(400);
s = await session();
check("scheduled start waits", s.jobs?.[tabId]?.waiting === true && (await pageVal(() => window.count)) === 0);
await popup.reload(); await popup.waitForSelector("#toggle"); await sleep(300);
const waitText = await popup.$eval("#stateText", (el) => el.textContent);
check("popup shows waiting", /Waiting/.test(waitText), waitText);
if (SHOTS) await popup.screenshot({ path: path.join(SHOTS, "popup_waiting.png"), fullPage: true });
await sleep(1000);
check("starts at the start time", (await pageVal(() => window.count)) >= 1, `count=${await pageVal(() => window.count)}`);
await sleep(2000);
s = await session();
const timedCount = await pageVal(() => window.count);
check("stops at the stop time", !s.jobs?.[tabId] && s.results?.[tabId]?.reason === "timeup" && timedCount >= 2 && timedCount <= 3,
  `count=${timedCount} ${JSON.stringify(s.results?.[tabId])}`);

// 8. Popup form: a bad duration is refused before starting
await popup.evaluate(() => {
  document.getElementById("startMode").value = "in";
  document.getElementById("startMode").dispatchEvent(new Event("change"));
});
await setForm(popup, { startIn: "1:99:00" });
await popup.click("#toggle");
await sleep(300);
s = await session();
const badMsg = await popup.$eval("#message", (el) => el.textContent);
check("bad duration is refused", !s.jobs?.[tabId] && /duration/.test(badMsg), badMsg);
await setForm(popup, { startMode: "now", startIn: "00:20:00" });

// 9. Page reloads mid-run -> keeps clicking
await start({ mode: "element", selector: "#btn" }, { ...base, repeat: 0 });
await sleep(300);
await page.reload();
await sleep(2300);
const afterReload = await pageVal(() => window.count || 0);
check("keeps clicking after a page reload", afterReload >= 1, `count=${afterReload}`);

// 10. Closing the tab clears the schedule
const badge = await sw.evaluate((tabId) => chrome.action.getBadgeText({ tabId }), tabId);
check("badge shows the click count", /^\d+$|ON/.test(badge), `badge=${badge}`);
await page.close();
await sleep(500);
s = await session();
check("closing the tab clears the schedule", !s.jobs?.[tabId]);

// 11. Popup screenshots: light / dark
const shotPage = await browser.newPage();
await shotPage.goto(URL_);
const tab2 = (await sw.evaluate(() => chrome.tabs.query({ url: "http://127.0.0.1:8765/*" })))[0].id;
for (const theme of ["light", "dark"]) {
  await sw.evaluate((theme) => chrome.storage.local.set({ prefs: { theme },
    config: { mode: "element", interval: 3, unit: 60, jitter: 0, repeat: 0, clickNow: false, button: "left", clicks: 1 } }), theme);
  const p = await browser.newPage();
  await p.setViewport({ width: 364, height: 760 });
  await p.goto(`chrome-extension://${extId}/popup.html?tab=${tab2}`);
  await p.waitForSelector("#toggle"); await sleep(300);
  if (SHOTS) await p.screenshot({ path: path.join(SHOTS, `popup_${theme}.png`), fullPage: true });
  await p.close();
}

console.log(`\n${results.filter(Boolean).length}/${results.length} passed`);
await browser.close();
server.close();
process.exit(results.every(Boolean) ? 0 : 1);
