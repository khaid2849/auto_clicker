// Unit tests for the extension's start/stop schedule:  node --test tests/extension/schedule.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { fmtWhen, nextClock, parseClock, parseDuration, plan } from "../../src/autoclicker/browser_extension/schedule.js";

const at = (d, h, m, s = 0) => new Date(2026, 10, d, h, m, s).getTime(); // local time, November 2026
const NOW = at(26, 18, 0);

test("parseClock", () => {
  assert.deepEqual(parseClock("19:30"), [19, 30]);
  assert.deepEqual(parseClock("7:05"), [7, 5]);
  assert.equal(parseClock("24:00"), null);
  assert.equal(parseClock("19h30"), null);
  assert.equal(parseClock(""), null);
});

test("parseDuration", () => {
  assert.equal(parseDuration("00:20:00"), 1200);
  assert.equal(parseDuration("01:30:00"), 5400);
  assert.equal(parseDuration("25:00:00"), 90000); // more than a day is fine
  assert.equal(parseDuration("20:00"), 1200); // mm:ss
  assert.equal(parseDuration("45"), 45);
  assert.equal(parseDuration("1:75:00"), null);
  assert.equal(parseDuration("abc"), null);
  assert.equal(parseDuration(""), null);
});

test("nextClock: today or tomorrow", () => {
  assert.equal(nextClock(NOW, 19, 30), at(26, 19, 30));
  assert.equal(nextClock(at(26, 20, 0), 19, 30), at(27, 19, 30));
  assert.equal(nextClock(at(26, 19, 30), 19, 30), at(27, 19, 30));
});

test("plan: start at 19:30, stop at 21:00", () => {
  assert.deepEqual(plan(NOW, { startMode: "at", startAt: "19:30", stopMode: "at", stopAt: "21:00" }),
    { startAt: at(26, 19, 30), stopAt: at(26, 21, 0) });
});

test("plan: the stop time counts from the start", () => {
  assert.equal(plan(NOW, { startMode: "at", startAt: "22:00", stopMode: "at", stopAt: "01:00" }).stopAt, at(27, 1, 0));
});

test("plan: start in 00:20:00, stop after 01:30:00", () => {
  assert.deepEqual(plan(NOW, { startMode: "in", startIn: "00:20:00", stopMode: "after", stopAfter: "01:30:00" }),
    { startAt: at(26, 18, 20), stopAt: at(26, 19, 50) });
});

test("plan: no schedule, and bad input", () => {
  assert.deepEqual(plan(NOW, { startMode: "now", stopMode: "none" }), { startAt: NOW, stopAt: null });
  assert.deepEqual(plan(NOW, { startMode: "at", startAt: "x" }), { error: "startAt" });
  assert.deepEqual(plan(NOW, { startMode: "now", stopMode: "after", stopAfter: "0" }), { error: "stopAfter" });
});

test("fmtWhen", () => {
  assert.equal(fmtWhen(at(26, 19, 30), NOW), "19:30");
  assert.equal(fmtWhen(at(26, 18, 20, 5), NOW), "18:20:05");
  assert.equal(fmtWhen(at(27, 1, 0), NOW), "01:00 tomorrow");
});
