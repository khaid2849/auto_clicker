package io.github.khaid2849.autoclicker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar
import java.util.TimeZone
import kotlin.random.Random

class ClickConfigTest {
    @Test
    fun fmtDuration_matchesDesktop() {
        assertEquals("00:00", fmtDuration(0))
        assertEquals("03:00", fmtDuration(179_200))
        assertEquals("1:02:05", fmtDuration(3_725_000))
        assertEquals("00:00", fmtDuration(-500))
    }

    @Test
    fun defaultIsEveryThreeMinutes() {
        assertEquals(180_000L, ClickConfig().nextIntervalMs())
    }

    @Test
    fun jitterStaysInRange() {
        val c = ClickConfig(interval = 10, unit = IntervalUnit.SECONDS, jitterSec = 3)
        val rnd = Random(42)
        repeat(1000) {
            val ms = c.nextIntervalMs(rnd)
            assertTrue("$ms", ms in 7_000L..13_000L)
        }
    }

    @Test
    fun intervalIsAtLeastOneSecond() {
        val c = ClickConfig(interval = 1, unit = IntervalUnit.SECONDS, jitterSec = 60)
        val rnd = Random(1)
        repeat(1000) { assertTrue(c.nextIntervalMs(rnd) >= 1_000L) }
    }

    @Test
    fun tapPointJitter() {
        assertEquals(100 to 200, ClickConfig(x = 100, y = 200).tapPoint())
        val c = ClickConfig(x = 100, y = 200, posJitterPx = 5)
        val rnd = Random(7)
        repeat(1000) {
            val (x, y) = c.tapPoint(rnd)
            assertTrue(x in 95..105 && y in 195..205)
        }
    }

    @Test
    fun tapPointNeverNegative() {
        val c = ClickConfig(x = 0, y = 0, posJitterPx = 10)
        val rnd = Random(3)
        repeat(1000) {
            val (x, y) = c.tapPoint(rnd)
            assertTrue(x >= 0 && y >= 0)
        }
    }

    // ---- Schedule -------------------------------------------------------------------------------

    private val tz = TimeZone.getTimeZone("Asia/Ho_Chi_Minh")

    /** Wall-clock ms of 2026-11-[day] hh:mm:ss in [tz]. */
    private fun at(day: Int, h: Int, m: Int, s: Int = 0): Long = Calendar.getInstance(tz).apply {
        clear()
        set(2026, Calendar.NOVEMBER, day, h, m, s)
    }.timeInMillis

    private val now = at(26, 18, 0)

    @Test
    fun nextClock_todayOrTomorrow() {
        assertEquals(at(26, 19, 30), nextClockMs(now, 19 * 60 + 30, tz))
        assertEquals(at(27, 19, 30), nextClockMs(at(26, 20, 0), 19 * 60 + 30, tz))
        assertEquals(at(27, 19, 30), nextClockMs(at(26, 19, 30), 19 * 60 + 30, tz))
    }

    @Test
    fun plan_startAtStopAt() {
        val c = ClickConfig(startMode = StartMode.AT, startAtMin = 19 * 60 + 30, stopMode = StopMode.AT, stopAtMin = 21 * 60)
        assertEquals(RunPlan(at(26, 19, 30), at(26, 21, 0)), c.plan(now, tz))
    }

    @Test
    fun plan_stopTimeCountsFromTheStart() {
        val c = ClickConfig(startMode = StartMode.AT, startAtMin = 22 * 60, stopMode = StopMode.AT, stopAtMin = 60)
        assertEquals(at(27, 1, 0), c.plan(now, tz).stopAt)
    }

    @Test
    fun plan_startInStopAfter() {
        val c = ClickConfig(startMode = StartMode.IN, startInSec = 20 * 60, stopMode = StopMode.AFTER, stopAfterSec = 90 * 60)
        assertEquals(RunPlan(at(26, 18, 20), at(26, 19, 50)), c.plan(now, tz))
    }

    @Test
    fun plan_default_isNowWithoutLimit() {
        val p = ClickConfig().plan(now, tz)
        assertEquals(now, p.startAt)
        assertNull(p.stopAt)
    }

    @Test
    fun parseDuration_formats() {
        assertEquals(1200, parseDuration("00:20:00"))
        assertEquals(5400, parseDuration(" 01:30:00 "))
        assertEquals(1200, parseDuration("20:00"))
        assertEquals(45, parseDuration("45"))
        assertNull(parseDuration("1:75:00"))
        assertNull(parseDuration("1::0"))
        assertNull(parseDuration("abc"))
        assertNull(parseDuration(""))
    }

    @Test
    fun formatting() {
        assertEquals("19:30", fmtMinuteOfDay(19 * 60 + 30))
        assertEquals("01:30:00", fmtHms(5400))
        assertEquals("19:30", fmtClock(at(26, 19, 30), tz))
        assertEquals("18:20:05", fmtClock(at(26, 18, 20, 5), tz))
        assertEquals(0, daysAhead(at(26, 23, 59), now, tz))
        assertEquals(1, daysAhead(at(27, 0, 1), now, tz))
    }
}
