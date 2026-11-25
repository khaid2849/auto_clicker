package io.github.khaid2849.autoclicker

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.roundToInt

/**
 * Full-screen picker, like the desktop crosshair overlay: the screen dims, a crosshair follows
 * the finger with live X/Y, and lifting the finger picks that spot (in screen coordinates).
 */
@SuppressLint("ViewConstructor")
class PickerView(context: Context, private val onPicked: (Int, Int) -> Unit) : View(context) {

    private val density = resources.displayMetrics.density
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        strokeWidth = 1.5f * density
    }
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = context.getColor(R.color.brand)
        style = Paint.Style.STROKE
        strokeWidth = 3f * density
    }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 16f * density
        setShadowLayer(4f * density, 0f, 0f, Color.BLACK)
    }
    private val hint = context.getString(R.string.picker_hint)

    /** Finger position in view coordinates (for drawing), and in screen coordinates (the result). */
    private var vx = -1f
    private var vy = -1f
    private var sx = 0
    private var sy = 0

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(0x66000000)
        if (vx < 0) {
            text.textAlign = Paint.Align.CENTER
            canvas.drawText(hint, width / 2f, height / 2f, text)
            return
        }
        canvas.drawLine(0f, vy, width.toFloat(), vy, line)
        canvas.drawLine(vx, 0f, vx, height.toFloat(), line)
        canvas.drawCircle(vx, vy, 18f * density, ring)
        // Label above the finger, kept on screen
        val label = "X $sx   Y $sy"
        text.textAlign = Paint.Align.LEFT
        val w = text.measureText(label)
        val lx = (vx + 24 * density).coerceAtMost(width - w - 8 * density).coerceAtLeast(8 * density)
        val ly = (vy - 56 * density).coerceAtLeast(32 * density)
        canvas.drawText(label, lx, ly, text)
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE -> {
                vx = e.x; vy = e.y
                sx = e.rawX.roundToInt(); sy = e.rawY.roundToInt()
                invalidate()
            }
            MotionEvent.ACTION_UP -> onPicked(e.rawX.roundToInt(), e.rawY.roundToInt())
        }
        return true
    }
}
