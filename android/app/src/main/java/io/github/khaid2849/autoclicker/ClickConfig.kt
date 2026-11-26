package io.github.khaid2849.autoclicker

import android.content.Context
import java.util.Calendar
import java.util.Locale
import java.util.TimeZone
import kotlin.math.ceil
import kotlin.math.max
import kotlin.random.Random

enum class IntervalUnit(val seconds: Int) { SECONDS(1), MINUTES(60), HOURS(3600) }

enum class TapType { TAP, DOUBLE_TAP, LONG_PRESS }

/** When a run begins: right away, at a time of day, or after a countdown. */
enum class StartMode { NOW, AT, IN }

/** When a run ends (besides the tap limit): never, at a time of day, or after running for a while. */
enum class StopMode { NONE, AT, AFTER }

/** Wall-clock times (System.currentTimeMillis) of one run. stopAt = null: no time limit. */
data class RunPlan(val startAt: Long, val stopAt: Long?)

/** Everything the user sets up. Same options and defaults as the desktop app. */
data class ClickConfig(
    /** Target in screen pixels; -1 = not picked yet. */
    val x: Int = -1,
    val y: Int = -1,
    val interval: Int = 3,
    val unit: IntervalUnit = IntervalUnit.MINUTES,
    /** Random extra time, ± seconds. */
    val jitterSec: Int = 0,
    /** Stop after this many taps; 0 = never. */
    val repeat: Int = 0,
    /** Random offset of the tap position, ± pixels. */
    val posJitterPx: Int = 0,
    val tapType: TapType = TapType.TAP,
    val clickNow: Boolean = false,
    val keepScreenOn: Boolean = true,
    val startMode: StartMode = StartMode.NOW,
    /** Minute of the day, 19:30 = 1170. */
    val startAtMin: Int = 19 * 60 + 30,
    val startInSec: Int = 20 * 60,
    val stopMode: StopMode = StopMode.NONE,
    val stopAtMin: Int = 21 * 60,
    val stopAfterSec: Int = 90 * 60,
) {
    val hasTarget get() = x >= 0 && y >= 0

    /**
     * Start and stop times for a run that's started at [nowMs]. Same rules as the desktop app: the
     * stop time counts from the start, so "start at 22:00, stop at 01:00" stops the night after, and
     * "stop after 01:30:00" means 1 h 30 of tapping, not counting the wait before it.
     */
    fun plan(nowMs: Long, tz: TimeZone = TimeZone.getDefault()): RunPlan {
        val start = when (startMode) {
            StartMode.NOW -> nowMs
            StartMode.AT -> nextClockMs(nowMs, startAtMin, tz)
            StartMode.IN -> nowMs + startInSec.coerceAtLeast(0) * 1000L
        }
        val stop = when (stopMode) {
            StopMode.NONE -> null
            StopMode.AT -> nextClockMs(start, stopAtMin, tz)
            StopMode.AFTER -> start + stopAfterSec.coerceAtLeast(1) * 1000L
        }
        return RunPlan(start, stop)
    }

    /** Time until the next tap: interval ± jitter, never under 1 second. */
    fun nextIntervalMs(random: Random = Random.Default): Long {
        val base = interval.toDouble() * unit.seconds
        val j = jitterSec.toDouble()
        val sec = if (j > 0) base + random.nextDouble(-j, j) else base
        return (max(1.0, sec) * 1000).toLong()
    }

    /** The target, moved by up to ±posJitterPx in each direction. */
    fun tapPoint(random: Random = Random.Default): Pair<Int, Int> {
        val j = posJitterPx
        if (j <= 0) return x to y
        return (x + random.nextInt(-j, j + 1)).coerceAtLeast(0) to (y + random.nextInt(-j, j + 1)).coerceAtLeast(0)
    }
}

/** 179_200 -> "03:00", 3_725_000 -> "1:02:05". */
fun fmtDuration(ms: Long): String {
    val sec = max(0L, ceil(ms / 1000.0).toLong())
    val h = sec / 3600
    val m = sec % 3600 / 60
    val s = sec % 60
    return if (h > 0) String.format(Locale.ROOT, "%d:%02d:%02d", h, m, s)
    else String.format(Locale.ROOT, "%02d:%02d", m, s)
}

/** First moment strictly after [afterMs] when the local clock shows [minuteOfDay] (19:30 asked at 20:00 -> tomorrow). */
fun nextClockMs(afterMs: Long, minuteOfDay: Int, tz: TimeZone = TimeZone.getDefault()): Long {
    val c = Calendar.getInstance(tz)
    c.timeInMillis = afterMs
    c.set(Calendar.HOUR_OF_DAY, minuteOfDay / 60)
    c.set(Calendar.MINUTE, minuteOfDay % 60)
    c.set(Calendar.SECOND, 0)
    c.set(Calendar.MILLISECOND, 0)
    if (c.timeInMillis <= afterMs) c.add(Calendar.DAY_OF_MONTH, 1) // keeps the clock time across DST changes
    return c.timeInMillis
}

/** Calendar days from [nowMs] to [ms]: 0 = today, 1 = tomorrow. */
fun daysAhead(ms: Long, nowMs: Long, tz: TimeZone = TimeZone.getDefault()): Int {
    fun dayStart(t: Long) = Calendar.getInstance(tz).apply {
        timeInMillis = t
        set(Calendar.HOUR_OF_DAY, 12) // noon: the day count stays right across a DST change
        set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
    }.timeInMillis
    return Math.round((dayStart(ms) - dayStart(nowMs)) / 86_400_000.0).toInt()
}

/** "19:30" (or "19:30:15" when the seconds aren't :00) for a wall-clock time. */
fun fmtClock(ms: Long, tz: TimeZone = TimeZone.getDefault()): String {
    val c = Calendar.getInstance(tz).apply { timeInMillis = ms }
    val (h, m, s) = Triple(c.get(Calendar.HOUR_OF_DAY), c.get(Calendar.MINUTE), c.get(Calendar.SECOND))
    return if (s != 0) String.format(Locale.ROOT, "%02d:%02d:%02d", h, m, s)
    else String.format(Locale.ROOT, "%02d:%02d", h, m)
}

/** 1170 -> "19:30". */
fun fmtMinuteOfDay(min: Int): String = String.format(Locale.ROOT, "%02d:%02d", min / 60, min % 60)

/** 5400 -> "01:30:00". */
fun fmtHms(sec: Int): String = String.format(Locale.ROOT, "%02d:%02d:%02d", sec / 3600, sec % 3600 / 60, sec % 60)

/** "01:30:00" -> 5400, "20:00" (mm:ss) -> 1200, "45" -> 45; anything else -> null. */
fun parseDuration(text: String): Int? {
    val parts = text.trim().split(":")
    if (parts.size > 3 || parts.any { p -> p.isEmpty() || !p.all { it.isDigit() } || p.length > 5 }) return null
    val nums = parts.map { it.toInt() }
    if (nums.drop(1).any { it >= 60 }) return null
    return nums.fold(0) { total, n -> total * 60 + n }
}

/** Saves the settings between runs. */
class Prefs(context: Context) {
    private val p = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    fun load(): ClickConfig {
        val d = ClickConfig()
        return ClickConfig(
            x = p.getInt("x", d.x),
            y = p.getInt("y", d.y),
            interval = p.getInt("interval", d.interval),
            unit = enumOr(p.getString("unit", null), d.unit),
            jitterSec = p.getInt("jitter", d.jitterSec),
            repeat = p.getInt("repeat", d.repeat),
            posJitterPx = p.getInt("pos_jitter", d.posJitterPx),
            tapType = enumOr(p.getString("tap_type", null), d.tapType),
            clickNow = p.getBoolean("click_now", d.clickNow),
            keepScreenOn = p.getBoolean("keep_screen_on", d.keepScreenOn),
            startMode = enumOr(p.getString("start_mode", null), d.startMode),
            startAtMin = p.getInt("start_at", d.startAtMin).coerceIn(0, 24 * 60 - 1),
            startInSec = p.getInt("start_in", d.startInSec).coerceAtLeast(0),
            stopMode = enumOr(p.getString("stop_mode", null), d.stopMode),
            stopAtMin = p.getInt("stop_at", d.stopAtMin).coerceIn(0, 24 * 60 - 1),
            stopAfterSec = p.getInt("stop_after", d.stopAfterSec).coerceAtLeast(1),
        )
    }

    fun save(c: ClickConfig) {
        p.edit()
            .putInt("x", c.x).putInt("y", c.y)
            .putInt("interval", c.interval).putString("unit", c.unit.name)
            .putInt("jitter", c.jitterSec).putInt("repeat", c.repeat)
            .putInt("pos_jitter", c.posJitterPx).putString("tap_type", c.tapType.name)
            .putBoolean("click_now", c.clickNow).putBoolean("keep_screen_on", c.keepScreenOn)
            .putString("start_mode", c.startMode.name).putInt("start_at", c.startAtMin).putInt("start_in", c.startInSec)
            .putString("stop_mode", c.stopMode.name).putInt("stop_at", c.stopAtMin).putInt("stop_after", c.stopAfterSec)
            .apply()
    }

    fun saveTarget(x: Int, y: Int) {
        p.edit().putInt("x", x).putInt("y", y).apply()
    }

    private inline fun <reified E : Enum<E>> enumOr(name: String?, default: E): E =
        enumValues<E>().firstOrNull { it.name == name } ?: default
}
