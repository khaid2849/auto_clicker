import { LANGUAGES, defaultLanguage, translator } from "./i18n.js";
import { startPicker } from "./inject.js";

const $ = (id) => document.getElementById(id);
const DEFAULT_CONFIG = { mode: "element", interval: 3, unit: 60, jitter: 0, repeat: 0, clickNow: false, button: "left", clicks: 1 };
const THEMES = ["system", "light", "dark"];
const STORE_HOSTS = ["chromewebstore.google.com", "microsoftedge.microsoft.com"];

let t = translator("en");
let prefs = { lang: "en", theme: "system" };
let tab = null;
let origin = null;
let target = null; // mục tiêu đã chọn cho trang (theo origin)
let job = null; // lịch click đang chạy trên tab này (từ service worker)
let result = null; // kết quả lần chạy gần nhất
let flash = null; // thông báo tạm thời { text, until }

function isScriptable(url) {
  try {
    const u = new URL(url);
    if (!["http:", "https:", "file:"].includes(u.protocol)) return false;
    if (STORE_HOSTS.includes(u.hostname)) return false;
    return !(u.hostname === "chrome.google.com" && u.pathname.startsWith("/webstore"));
  } catch {
    return false;
  }
}

function sitePattern(url) {
  const u = new URL(url);
  return u.protocol === "file:" ? "file:///*" : `${u.protocol}//${u.hostname}/*`;
}

function fmt(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${String(m).padStart(2, "0")}:${s}`;
}

// ───────────── Form ─────────────
function readForm() {
  return {
    mode: document.querySelector("input[name=mode]:checked").value,
    interval: Math.max(1, Number($("interval").value) || 1),
    unit: Number($("unit").value),
    jitter: Math.max(0, Number($("jitter").value) || 0),
    repeat: Math.max(0, Math.floor(Number($("repeat").value) || 0)),
    clickNow: $("clickNow").checked,
    button: $("button").value,
    clicks: Number($("clicks").value),
  };
}

function writeForm(cfg) {
  document.querySelector(`input[name=mode][value="${cfg.mode}"]`).checked = true;
  $("interval").value = cfg.interval;
  $("unit").value = String(cfg.unit);
  $("jitter").value = cfg.jitter;
  $("repeat").value = cfg.repeat;
  $("clickNow").checked = cfg.clickNow;
  $("button").value = cfg.button;
  $("clicks").value = String(cfg.clicks);
}

// ───────────── Hiển thị ─────────────
function applyPrefs() {
  t = translator(prefs.lang);
  document.documentElement.lang = prefs.lang;
  if (prefs.theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = prefs.theme;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  $("lang").title = t("language");
  $("theme").title = t("theme");
  $("theme").replaceChildren(...THEMES.map((mode) => new Option(t(`theme_${mode}`), mode, false, mode === prefs.theme)));
  $("lang").value = prefs.lang;
  renderTarget();
  renderStatus();
}

function renderTarget() {
  const box = $("targetInfo");
  if (!target) {
    box.innerHTML = `<span class="muted"></span>`;
    box.firstChild.textContent = t("no_target");
    return;
  }
  if (readForm().mode === "point") {
    box.textContent = t("point_label", { x: target.x, y: target.y });
  } else {
    box.innerHTML = `<div></div><div class="muted"></div>`;
    box.children[0].textContent = target.label;
    box.children[1].textContent = target.selector;
  }
}

function renderStatus() {
  const running = Boolean(job);
  $("dot").classList.toggle("on", running);
  $("stateText").textContent = t(running ? "running" : "stopped");
  $("count").textContent = t("clicks", { n: job?.count ?? result?.count ?? 0 });
  $("countdown").textContent = running ? fmt(job.nextAt - Date.now()) : "--:--";
  $("toggle").textContent = t(running ? "stop" : "start");
  $("toggle").classList.toggle("running", running);
  document.querySelectorAll(".settings input, .settings select, .settings button")
    .forEach((el) => (el.disabled = running));

  let text = "";
  let isError = false;
  if (flash && Date.now() < flash.until) {
    ({ text } = flash);
    isError = true;
  } else if (job?.lastError) {
    text = t(`err_${job.lastError}`);
    isError = true;
  } else if (!job && result) {
    text = t(result.reason === "done" ? "done" : "stopped_after", { n: result.count });
  }
  showMessage(text, isError);
}

function showFlash(text) {
  flash = { text, until: Date.now() + 4000 };
  renderStatus();
}

function showMessage(text, isError = false) {
  $("message").textContent = text;
  $("message").hidden = !text;
  $("message").classList.toggle("error", isError);
}

async function refreshJob() {
  const { jobs = {}, results = {} } = await chrome.storage.session.get(["jobs", "results"]);
  job = jobs[tab.id] ?? null;
  result = results[tab.id] ?? null;
  renderStatus();
}

// ───────────── Hành động ─────────────
// Các hàm gọi API cần "user gesture" (permissions.request) phải gọi ngay, không await trước đó.
function onPick() {
  chrome.scripting
    .executeScript({ target: { tabId: tab.id }, func: startPicker, args: [{ hint: t("picker_hint"), done: t("picker_done") }] })
    .then(() => window.close(), () => showFlash(t("err_pick_failed")));
}

function onToggle() {
  if (job) {
    chrome.runtime.sendMessage({ type: "stop", tabId: tab.id });
    return;
  }
  if (!target) {
    showFlash(t("err_no_target"));
    return;
  }
  const config = readForm();
  // Xin quyền cố định cho trang này để vẫn click được sau khi trang tải lại
  // (không cấp thì vẫn chạy nhờ activeTab, tới khi trang chuyển hoặc tải lại)
  chrome.permissions.request({ origins: [sitePattern(tab.url)] }).catch(() => {});
  chrome.storage.local.set({ config });
  chrome.runtime.sendMessage({ type: "start", tabId: tab.id, target: { ...target, mode: config.mode }, config });
}

function savePrefs() {
  chrome.storage.local.set({ prefs });
  applyPrefs();
}

// ───────────── Khởi động ─────────────
async function init() {
  // ?tab=<id> chỉ dùng khi test/gỡ lỗi popup trong một tab riêng
  const forced = Number(new URLSearchParams(location.search).get("tab"));
  tab = forced ? await chrome.tabs.get(forced) : (await chrome.tabs.query({ active: true, currentWindow: true }))[0];

  const stored = await chrome.storage.local.get(["config", "prefs", "targets"]);
  prefs = { lang: defaultLanguage(), theme: "system", ...stored.prefs };
  $("lang").replaceChildren(...Object.entries(LANGUAGES).map(([code, name]) => new Option(name, code)));
  writeForm({ ...DEFAULT_CONFIG, ...stored.config });

  const allowed = tab && isScriptable(tab.url);
  $("restricted").hidden = allowed;
  $("main").classList.toggle("disabled", !allowed);
  if (allowed) {
    origin = new URL(tab.url).origin;
    target = stored.targets?.[origin] ?? null;
  }
  applyPrefs();
  if (tab) await refreshJob();

  $("lang").addEventListener("change", () => { prefs.lang = $("lang").value; savePrefs(); });
  $("theme").addEventListener("change", () => { prefs.theme = $("theme").value; savePrefs(); });
  document.querySelectorAll(".settings input, .settings select").forEach((el) =>
    el.addEventListener("change", () => {
      chrome.storage.local.set({ config: readForm() });
      renderTarget();
    }));
  $("pick").addEventListener("click", onPick);
  $("toggle").addEventListener("click", onToggle);

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "session" && (changes.jobs || changes.results) && tab) refreshJob();
    if (area === "local" && changes.targets && origin) {
      target = changes.targets.newValue?.[origin] ?? null;
      renderTarget();
    }
  });
  setInterval(renderStatus, 250);
}

init();
