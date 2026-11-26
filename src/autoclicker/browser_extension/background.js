// Service worker: keeps the click schedule of each tab and performs the clicks.
//
// State lives in chrome.storage.session (cleared when the browser closes) because an MV3 service
// worker can be stopped at any time. Scheduling uses two layers:
//   - chrome.alarms: wakes the service worker even if it was stopped (30 s minimum when packed);
//   - setTimeout: for short delays while the service worker is awake.
// Both may fire for the same click; fire() checks nextAt so nothing is clicked twice.
import { performClick } from "./inject.js";

const ALARM_PREFIX = "click:";
const SHORT_MS = 25_000;
const timers = new Map();

// Serialize read-modify-write storage operations so they don't overwrite each other
let queue = Promise.resolve();
function locked(fn) {
  const run = queue.then(fn);
  queue = run.catch(() => {});
  return run;
}

async function getJobs() {
  return (await chrome.storage.session.get("jobs")).jobs ?? {};
}

async function setJob(tabId, job) {
  const jobs = await getJobs();
  if (job) jobs[tabId] = job;
  else delete jobs[tabId];
  await chrome.storage.session.set({ jobs });
}

async function setResult(tabId, result) {
  const { results = {} } = await chrome.storage.session.get("results");
  if (result) results[tabId] = result;
  else delete results[tabId];
  await chrome.storage.session.set({ results });
}

function nextDelay(job) {
  const jitter = job.jitterMs ? (Math.random() * 2 - 1) * job.jitterMs : 0;
  return Math.max(1000, job.intervalMs + jitter);
}

// Next time fire() must run: the next click, or the stop time if that comes first
function wakeAt(job) {
  return job.stopAt ? Math.min(job.nextAt, job.stopAt) : job.nextAt;
}

function schedule(job) {
  clearTimeout(timers.get(job.tabId));
  const when = wakeAt(job);
  chrome.alarms.create(ALARM_PREFIX + job.tabId, { when });
  const delay = Math.max(0, when - Date.now());
  if (delay <= SHORT_MS) timers.set(job.tabId, setTimeout(() => fire(job.tabId), delay));
}

async function unschedule(tabId) {
  clearTimeout(timers.get(tabId));
  timers.delete(tabId);
  await chrome.alarms.clear(ALARM_PREFIX + tabId);
}

async function updateBadge(tabId, job) {
  try {
    const amber = job?.lastError || job?.waiting;
    await chrome.action.setBadgeBackgroundColor({ tabId, color: amber ? "#d97706" : "#16a34a" });
    const text = !job ? "" : job.waiting ? "WAIT" : job.count ? String(job.count) : "ON";
    await chrome.action.setBadgeText({ tabId, text });
  } catch {
    // the tab was closed
  }
}

// Call inside locked()
async function finish(tabId, reason, count = 0) {
  await unschedule(tabId);
  await setJob(tabId, null);
  await setResult(tabId, reason ? { reason, count, at: Date.now() } : null);
  await updateBadge(tabId, null);
}

// `when` = { startAt, stopAt } in epoch ms, worked out by the popup (schedule.js); missing = start now, no time limit
function start(tabId, target, cfg, when = {}) {
  return locked(async () => {
    const now = Date.now();
    const startAt = Number(when.startAt) || now;
    const job = {
      tabId,
      target,
      intervalMs: Math.max(1, Number(cfg.interval) || 1) * Number(cfg.unit || 1) * 1000,
      jitterMs: Math.max(0, Number(cfg.jitter) || 0) * 1000,
      repeat: Math.max(0, Math.floor(Number(cfg.repeat) || 0)),
      button: cfg.button || "left",
      clicks: Number(cfg.clicks) === 2 ? 2 : 1,
      count: 0,
      lastError: null,
      clickNow: Boolean(cfg.clickNow),
      startAt,
      stopAt: Number(when.stopAt) || null,
      waiting: startAt > now,
      nextAt: 0,
    };
    job.nextAt = job.waiting ? startAt : now + (job.clickNow ? 0 : nextDelay(job));
    await setJob(tabId, job);
    await setResult(tabId, null);
    await updateBadge(tabId, job);
    schedule(job);
    return { ok: true };
  });
}

function stop(tabId) {
  return locked(async () => {
    const job = (await getJobs())[tabId];
    await finish(tabId, "stopped", job?.count ?? 0);
    return { ok: true };
  });
}

function fire(tabId) {
  return locked(async () => {
    timers.delete(tabId);
    const job = (await getJobs())[tabId];
    if (!job) return;
    if (job.stopAt && Date.now() >= job.stopAt - 250) {
      await finish(tabId, "timeup", job.count);
      return;
    }
    if (Date.now() < job.nextAt - 250) {
      schedule(job); // woken up early or twice
      return;
    }
    if (job.waiting) {
      // The scheduled start time has come
      job.waiting = false;
      if (!job.clickNow) {
        job.nextAt = Date.now() + nextDelay(job);
        await setJob(tabId, job);
        await updateBadge(tabId, job);
        schedule(job);
        return;
      }
    }
    let result;
    try {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId },
        func: performClick,
        args: [job.target, job.button, job.clicks],
      });
      result = res?.result ?? { ok: false, error: "inject_failed" };
    } catch (e) {
      if (/No tab with id/i.test(String(e?.message))) {
        await finish(tabId, null);
        return;
      }
      result = { ok: false, error: "inject_failed" };
    }
    if (result.ok) {
      job.count += 1;
      job.lastError = null;
    } else {
      job.lastError = result.error;
    }
    if (job.repeat && job.count >= job.repeat) {
      await finish(tabId, "done", job.count);
      return;
    }
    job.nextAt = Date.now() + nextDelay(job);
    await setJob(tabId, job);
    await updateBadge(tabId, job);
    schedule(job);
  });
}

async function savePicked(sender, target) {
  const origin = new URL(sender.tab?.url || sender.url).origin;
  const { targets = {} } = await chrome.storage.local.get("targets");
  targets[origin] = target;
  await chrome.storage.local.set({ targets });
  // Reopen the popup so the user can press Start right away (if not allowed, the page shows a hint)
  chrome.action.openPopup?.().catch(() => {});
  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const handlers = {
    start: () => start(msg.tabId, msg.target, msg.config, msg.when),
    stop: () => stop(msg.tabId),
    picked: () => savePicked(sender, msg.target),
  };
  const handler = handlers[msg?.type];
  if (!handler) return false;
  handler().then(sendResponse, (e) => sendResponse({ ok: false, error: String(e?.message || e) }));
  return true; // respond asynchronously
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name.startsWith(ALARM_PREFIX)) fire(Number(alarm.name.slice(ALARM_PREFIX.length)));
});

chrome.tabs.onRemoved.addListener((tabId) => {
  locked(async () => {
    await unschedule(tabId);
    await setJob(tabId, null);
    await setResult(tabId, null);
  });
});

// The service worker just (re)started: resume the schedules of running tabs
locked(async () => {
  for (const job of Object.values(await getJobs())) schedule(job);
});
