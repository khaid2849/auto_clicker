package io.github.khaid2849.autoclicker

import android.content.Context
import java.util.Locale
import kotlin.math.ceil
import kotlin.math.max
import kotlin.random.Random

enum class IntervalUnit(val seconds: Int) { SECONDS(1), MINUTES(60), HOURS(3600) }

enum class TapType { TAP, DOUBLE_TAP, LONG_PRESS }

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
) {
    val hasTarget get() = x >= 0 && y >= 0

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
        )
    }

    fun save(c: ClickConfig) {
        p.edit()
            .putInt("x", c.x).putInt("y", c.y)
            .putInt("interval", c.interval).putString("unit", c.unit.name)
            .putInt("jitter", c.jitterSec).putInt("repeat", c.repeat)
            .putInt("pos_jitter", c.posJitterPx).putString("tap_type", c.tapType.name)
            .putBoolean("click_now", c.clickNow).putBoolean("keep_screen_on", c.keepScreenOn)
            .apply()
    }

    fun saveTarget(x: Int, y: Int) {
        p.edit().putInt("x", x).putInt("y", y).apply()
    }

    private inline fun <reified E : Enum<E>> enumOr(name: String?, default: E): E =
        enumValues<E>().firstOrNull { it.name == name } ?: default
}
