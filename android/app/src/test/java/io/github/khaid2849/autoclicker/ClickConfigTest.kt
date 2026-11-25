package io.github.khaid2849.autoclicker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
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
}
