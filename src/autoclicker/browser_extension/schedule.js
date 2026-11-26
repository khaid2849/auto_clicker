// When a run starts and stops: right away, at a time of day ("19:30") or after a countdown ("00:20:00").
// Same rules as the desktop app (src/autoclicker/schedule.py). Times are epoch milliseconds.
import { t } from "./i18n.js";

export const START_MODES = ["now", "at", "in"]; // right away / at a time of day / after a countdown
export const STOP_MODES = ["none", "at", "after"]; // no time limit / at a time of day / after running for

/** "19:30" -> [19, 30]; anything else -> null. */
export function parseClock(text) {
  const m = /^\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*$/.exec(text ?? "");
  if (!m) return null;
  const [h, min] = [Number(m[1]), Number(m[2])];
  return h < 24 && min < 60 ? [h, min] : null;
}

/** "01:30:00" -> 5400, "20:00" (mm:ss) -> 1200, "45" -> 45; anything else -> null. */
export function parseDuration(text) {
  const parts = String(text ?? "").trim().split(":");
  if (parts.length > 3 || parts.some((p) => !/^\d+$/.test(p))) return null;
  const nums = parts.map(Number);
  if (nums.slice(1).some((n) => n >= 60)) return null; // minutes / seconds after the first part
  return nums.reduce((total, n) => total * 60 + n, 0);
}

/** First moment strictly after `afterMs` when the local clock shows hour:minute. */
export function nextClock(afterMs, hour, minute) {
  const d = new Date(afterMs);
  d.setHours(hour, minute, 0, 0);
  if (d.getTime() <= afterMs) d.setDate(d.getDate() + 1); // setDate keeps the clock time across DST changes
  return d.getTime();
}

/**
 * Returns { startAt, stopAt } in ms (stopAt null = no time limit), or { error } naming the bad field.
 * The stop time counts from the start: "start at 22:00, stop at 01:00" stops the night after, and
 * "stop after 01:30:00" means 1 h 30 of clicking, not counting the wait before it.
 */
export function plan(nowMs, cfg) {
  let startAt = nowMs;
  if (cfg.startMode === "at") {
    const c = parseClock(cfg.startAt);
    if (!c) return { error: "startAt" };
    startAt = nextClock(nowMs, ...c);
  } else if (cfg.startMode === "in") {
    const sec = parseDuration(cfg.startIn);
    if (sec === null) return { error: "startIn" };
    startAt = nowMs + sec * 1000;
  }
  let stopAt = null;
  if (cfg.stopMode === "at") {
    const c = parseClock(cfg.stopAt);
    if (!c) return { error: "stopAt" };
    stopAt = nextClock(startAt, ...c);
  } else if (cfg.stopMode === "after") {
    const sec = parseDuration(cfg.stopAfter);
    if (!sec) return { error: "stopAfter" };
    stopAt = startAt + sec * 1000;
  }
  return { startAt, stopAt };
}

/** "19:30", "19:30 tomorrow" or "19:30 Mon 30 Nov"; seconds only when they aren't :00. */
export function fmtWhen(ms, nowMs = Date.now()) {
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  const clock = `${pad(d.getHours())}:${pad(d.getMinutes())}${d.getSeconds() ? `:${pad(d.getSeconds())}` : ""}`;
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((day(d) - day(new Date(nowMs))) / 86_400_000);
  if (days === 0) return clock;
  if (days === 1) return t("when_tomorrow", { t: clock });
  return t("when_date", { t: clock, date: d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) });
}
