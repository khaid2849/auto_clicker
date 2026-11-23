// Service worker: giữ lịch click của từng tab và thực hiện click.
//
// Trạng thái nằm trong chrome.storage.session (mất khi tắt trình duyệt) vì service worker MV3
// có thể bị dừng bất cứ lúc nào. Lịch hẹn dùng hai lớp:
//   - chrome.alarms: đánh thức service worker kể cả khi nó đã ngủ (bản đóng gói tối thiểu 30 giây);
//   - setTimeout: cho khoảng ngắn khi service worker đang thức.
// Hai lớp có thể cùng kích hoạt; fire() kiểm tra nextAt nên không click trùng.
import { performClick } from "./inject.js";

const ALARM_PREFIX = "click:";
const SHORT_MS = 25_000;
const timers = new Map();

// Xếp hàng các thao tác đọc-sửa-ghi storage để không giẫm lên nhau
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

function schedule(job) {
  clearTimeout(timers.get(job.tabId));
  chrome.alarms.create(ALARM_PREFIX + job.tabId, { when: job.nextAt });
  const delay = Math.max(0, job.nextAt - Date.now());
  if (delay <= SHORT_MS) timers.set(job.tabId, setTimeout(() => fire(job.tabId), delay));
}

async function unschedule(tabId) {
  clearTimeout(timers.get(tabId));
  timers.delete(tabId);
  await chrome.alarms.clear(ALARM_PREFIX + tabId);
}

async function updateBadge(tabId, job) {
  try {
    await chrome.action.setBadgeBackgroundColor({ tabId, color: job?.lastError ? "#d97706" : "#16a34a" });
    await chrome.action.setBadgeText({ tabId, text: job ? (job.count ? String(job.count) : "ON") : "" });
  } catch {
    // tab đã đóng
  }
}

// Gọi bên trong locked()
async function finish(tabId, reason, count = 0) {
  await unschedule(tabId);
  await setJob(tabId, null);
  await setResult(tabId, reason ? { reason, count, at: Date.now() } : null);
  await updateBadge(tabId, null);
}

function start(tabId, target, cfg) {
  return locked(async () => {
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
      nextAt: 0,
    };
    job.nextAt = Date.now() + (cfg.clickNow ? 0 : nextDelay(job));
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
    if (Date.now() < job.nextAt - 250) {
      schedule(job); // bị đánh thức sớm hoặc trùng
      return;
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
  // Mở lại popup để người dùng bấm Bắt đầu luôn (không được thì trang đã có thông báo hướng dẫn)
  chrome.action.openPopup?.().catch(() => {});
  return { ok: true };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const handlers = {
    start: () => start(msg.tabId, msg.target, msg.config),
    stop: () => stop(msg.tabId),
    picked: () => savePicked(sender, msg.target),
  };
  const handler = handlers[msg?.type];
  if (!handler) return false;
  handler().then(sendResponse, (e) => sendResponse({ ok: false, error: String(e?.message || e) }));
  return true; // trả lời bất đồng bộ
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

// Service worker vừa (khởi động lại): nối lại lịch của các tab đang chạy
locked(async () => {
  for (const job of Object.values(await getJobs())) schedule(job);
});
