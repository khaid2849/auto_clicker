package io.github.khaid2849.autoclicker

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Rect
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.TextView
import android.widget.Toast

/**
 * Does the actual work. Android only lets an accessibility service tap on other apps
 * (dispatchGesture), and the same service can draw over them (TYPE_ACCESSIBILITY_OVERLAY)
 * without the extra "display over other apps" permission. So this one class holds:
 * - the floating control panel (pick / start-stop / settings / close),
 * - the target marker,
 * - the full-screen picker,
 * - the timer that sends the taps.
 */
class ClickerService : AccessibilityService() {

    companion object {
        /** The service while it's turned on in Accessibility settings, else null. Same process as the activity. */
        var instance: ClickerService? = null
            private set

        private const val TICK_MS = 250L
        private const val TAP_MS = 40L
        private const val LONG_PRESS_MS = 700L
        private const val DOUBLE_TAP_GAP_MS = 90L
    }

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var wm: WindowManager
    private lateinit var prefs: Prefs

    private var panel: View? = null
    private var panelLp: WindowManager.LayoutParams? = null
    private var marker: View? = null
    private var picker: View? = null

    private var config = ClickConfig()
    var running = false
        private set
    private var count = 0
    private var nextAt = 0L // SystemClock.uptimeMillis() of the next tap
    /** Running, but the scheduled start time hasn't come yet. */
    private var waiting = false
    private var plan = RunPlan(0L, null) // wall-clock start / stop of this run

    private val ticker = object : Runnable {
        override fun run() {
            if (!running) return
            // Wall clock for the schedule: uptimeMillis stops while the phone sleeps
            val wall = System.currentTimeMillis()
            if (plan.stopAt?.let { wall >= it } == true) {
                stop(getString(R.string.time_up_n, count))
                return
            }
            if (waiting) {
                if (wall < plan.startAt) {
                    updateStatus()
                    handler.postDelayed(this, TICK_MS)
                    return
                }
                beginTapping()
            }
            val now = SystemClock.uptimeMillis()
            if (now >= nextAt) {
                if (tap()) count++
                if (config.repeat in 1..count) {
                    stop(getString(R.string.done_n, count))
                    return
                }
                nextAt = now + config.nextIntervalMs()
            }
            updateStatus()
            handler.postDelayed(this, TICK_MS)
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        wm = getSystemService(WindowManager::class.java)
        prefs = Prefs(this)
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        teardown()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        teardown()
        super.onDestroy()
    }

    private fun teardown() {
        stop()
        hidePanel()
        instance = null
    }

    // ---- Floating panel -------------------------------------------------------------------------

    @SuppressLint("InflateParams", "ClickableViewAccessibility")
    fun showPanel() {
        config = prefs.load()
        if (panel != null) {
            updateStatus()
            return
        }
        val v = LayoutInflater.from(this).inflate(R.layout.panel, null)
        v.findViewById<View>(R.id.pick).setOnClickListener { startPick() }
        v.findViewById<View>(R.id.toggle).setOnClickListener { if (running) stop() else start() }
        v.findViewById<View>(R.id.settings).setOnClickListener {
            stop()
            startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
        v.findViewById<View>(R.id.close).setOnClickListener { hidePanel() }

        val lp = overlayParams(WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT, 0)
        lp.x = dp(16)
        lp.y = resources.displayMetrics.heightPixels / 3
        v.setOnTouchListener(DragListener(lp))
        wm.addView(v, lp)
        panel = v
        panelLp = lp
        showMarker()
        updateStatus()
    }

    fun hidePanel() {
        stop()
        cancelPick()
        hideMarker()
        panel?.let { wm.removeView(it) }
        panel = null
        panelLp = null
    }

    private fun updateStatus() {
        val p = panel ?: return
        p.findViewById<TextView>(R.id.toggle).text = getString(if (running) R.string.panel_stop else R.string.panel_start)
        p.findViewById<TextView>(R.id.status).text = when {
            running && waiting ->
                getString(R.string.status_waiting, fmtDuration(plan.startAt - System.currentTimeMillis()))
            running -> getString(R.string.status_running, fmtDuration(nextAt - SystemClock.uptimeMillis()), count)
            config.hasTarget -> getString(R.string.status_ready)
            else -> getString(R.string.status_no_target)
        }
    }

    private inner class DragListener(private val lp: WindowManager.LayoutParams) : View.OnTouchListener {
        private var startX = 0
        private var startY = 0
        private var downX = 0f
        private var downY = 0f

        @SuppressLint("ClickableViewAccessibility")
        override fun onTouch(v: View, e: MotionEvent): Boolean {
            when (e.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    startX = lp.x; startY = lp.y; downX = e.rawX; downY = e.rawY
                }
                MotionEvent.ACTION_MOVE -> {
                    lp.x = startX + (e.rawX - downX).toInt()
                    lp.y = startY + (e.rawY - downY).toInt()
                    wm.updateViewLayout(v, lp)
                }
            }
            return true
        }
    }

    // ---- Target marker --------------------------------------------------------------------------

    @SuppressLint("InflateParams")
    private fun showMarker() {
        hideMarker()
        if (!config.hasTarget) return
        val size = dp(36)
        val v = LayoutInflater.from(this).inflate(R.layout.marker, null)
        val lp = overlayParams(size, size, WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE)
        lp.x = config.x - size / 2
        lp.y = config.y - size / 2
        wm.addView(v, lp)
        marker = v
        // Window coordinates may be offset from screen coordinates (status bar, cutout): correct once laid out.
        v.post {
            if (marker !== v) return@post
            val loc = IntArray(2)
            v.getLocationOnScreen(loc)
            val dx = config.x - (loc[0] + size / 2)
            val dy = config.y - (loc[1] + size / 2)
            if (dx != 0 || dy != 0) {
                lp.x += dx; lp.y += dy
                wm.updateViewLayout(v, lp)
            }
        }
    }

    private fun hideMarker() {
        marker?.let { wm.removeView(it) }
        marker = null
    }

    // ---- Picker ---------------------------------------------------------------------------------

    private fun startPick() {
        stop()
        cancelPick()
        panel?.visibility = View.GONE
        hideMarker()
        val v = PickerView(this) { x, y -> onPicked(x, y) }
        val lp = overlayParams(
            WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        )
        wm.addView(v, lp)
        picker = v
    }

    private fun cancelPick() {
        picker?.let { wm.removeView(it) }
        picker = null
        panel?.visibility = View.VISIBLE
    }

    private fun onPicked(x: Int, y: Int) {
        prefs.saveTarget(x, y)
        config = config.copy(x = x, y = y)
        cancelPick()
        movePanelAwayFrom(x, y)
        showMarker()
        updateStatus()
    }

    /** A tap under the panel would hit the panel, not the app: move the panel to the other half of the screen. */
    private fun movePanelAwayFrom(x: Int, y: Int) {
        val v = panel ?: return
        val lp = panelLp ?: return
        val loc = IntArray(2)
        v.getLocationOnScreen(loc)
        val margin = dp(24)
        val r = Rect(loc[0] - margin, loc[1] - margin, loc[0] + v.width + margin, loc[1] + v.height + margin)
        if (!r.contains(x, y)) return
        val h = resources.displayMetrics.heightPixels
        lp.y = if (y > h / 2) h / 6 else h * 2 / 3
        wm.updateViewLayout(v, lp)
    }

    // ---- Running --------------------------------------------------------------------------------

    fun start() {
        if (running) return
        config = prefs.load()
        if (!config.hasTarget) {
            toast(getString(R.string.status_no_target))
            return
        }
        running = true
        count = 0
        val now = System.currentTimeMillis()
        plan = config.plan(now)
        waiting = plan.startAt > now
        if (!waiting) beginTapping()
        // Also during the wait: if the screen turns off the phone sleeps and the start is late
        setKeepScreenOn(config.keepScreenOn)
        updateStatus()
        val parts = listOfNotNull(
            if (waiting) getString(R.string.plan_start, whenText(plan.startAt, now)) else null,
            plan.stopAt?.let { getString(R.string.plan_stop, whenText(it, now)) },
        )
        if (parts.isNotEmpty()) toast(parts.joinToString(" · "))
        handler.post(ticker)
    }

    /** The start time has come (or ▶ was pressed with "Right away"): the taps begin. */
    private fun beginTapping() {
        waiting = false
        nextAt = SystemClock.uptimeMillis() + if (config.clickNow) 0 else config.nextIntervalMs()
    }

    /** "19:30", "19:30 tomorrow" or "19:30, 30 Nov". */
    private fun whenText(ms: Long, nowMs: Long): String {
        val clock = fmtClock(ms)
        return when (daysAhead(ms, nowMs)) {
            0 -> clock
            1 -> getString(R.string.when_tomorrow, clock)
            else -> getString(R.string.when_date, clock, android.text.format.DateFormat.getMediumDateFormat(this).format(java.util.Date(ms)))
        }
    }

    fun stop(reason: String? = null) {
        if (!running) return
        running = false
        waiting = false
        handler.removeCallbacks(ticker)
        setKeepScreenOn(false)
        updateStatus()
        reason?.let { toast(it) }
    }

    private fun setKeepScreenOn(on: Boolean) {
        val v = panel ?: return
        val lp = panelLp ?: return
        lp.flags = if (on) lp.flags or WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        else lp.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON.inv()
        wm.updateViewLayout(v, lp)
    }

    /** Sends one tap / double tap / long press. Returns false if the system refused it. */
    private fun tap(): Boolean {
        val (x, y) = config.tapPoint()
        val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        val g = GestureDescription.Builder()
        when (config.tapType) {
            TapType.TAP -> g.addStroke(GestureDescription.StrokeDescription(path, 0, TAP_MS))
            TapType.LONG_PRESS -> g.addStroke(GestureDescription.StrokeDescription(path, 0, LONG_PRESS_MS))
            TapType.DOUBLE_TAP -> {
                g.addStroke(GestureDescription.StrokeDescription(path, 0, TAP_MS))
                g.addStroke(GestureDescription.StrokeDescription(path, TAP_MS + DOUBLE_TAP_GAP_MS, TAP_MS))
            }
        }
        return dispatchGesture(g.build(), null, null)
    }

    // ---- Helpers --------------------------------------------------------------------------------

    private fun overlayParams(w: Int, h: Int, extraFlags: Int) = WindowManager.LayoutParams(
        w, h,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or extraFlags,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.START
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
        }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
}
