package io.github.khaid2849.autoclicker

import android.app.Activity
import android.app.AlertDialog
import android.app.TimePickerDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.format.DateFormat
import android.view.View
import android.view.WindowInsets
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView

/** Settings screen. The clicking itself happens in [ClickerService] and its floating panel. */
class MainActivity : Activity() {

    private lateinit var prefs: Prefs

    private lateinit var permissionStatus: TextView
    private lateinit var permissionButton: Button
    private lateinit var interval: EditText
    private lateinit var unit: Spinner
    private lateinit var jitter: EditText
    private lateinit var repeat: EditText
    private lateinit var tapType: Spinner
    private lateinit var posJitter: EditText
    private lateinit var clickNow: CheckBox
    private lateinit var keepScreenOn: CheckBox
    private lateinit var target: TextView
    private lateinit var showPanel: Button
    private lateinit var startMode: Spinner
    private lateinit var startAt: Button
    private lateinit var startIn: EditText
    private lateinit var stopMode: Spinner
    private lateinit var stopAt: Button
    private lateinit var stopAfter: EditText

    // Times of day picked with the clock dialog, minutes since midnight
    private var startAtMin = 0
    private var stopAtMin = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)

        // Android 15+ draws apps edge to edge: keep the content clear of the status/navigation bars and keyboard.
        findViewById<View>(R.id.root).setOnApplyWindowInsetsListener { v, insets ->
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val i = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime())
                v.setPadding(i.left, i.top, i.right, i.bottom)
            } else {
                @Suppress("DEPRECATION")
                v.setPadding(
                    insets.systemWindowInsetLeft, insets.systemWindowInsetTop,
                    insets.systemWindowInsetRight, insets.systemWindowInsetBottom,
                )
            }
            insets
        }

        permissionStatus = findViewById(R.id.permission_status)
        permissionButton = findViewById(R.id.permission_button)
        interval = findViewById(R.id.interval)
        unit = findViewById(R.id.unit)
        jitter = findViewById(R.id.jitter)
        repeat = findViewById(R.id.repeat)
        tapType = findViewById(R.id.tap_type)
        posJitter = findViewById(R.id.pos_jitter)
        clickNow = findViewById(R.id.click_now)
        keepScreenOn = findViewById(R.id.keep_screen_on)
        target = findViewById(R.id.target)
        showPanel = findViewById(R.id.show_panel)
        startMode = findViewById(R.id.start_mode)
        startAt = findViewById(R.id.start_at)
        startIn = findViewById(R.id.start_in)
        stopMode = findViewById(R.id.stop_mode)
        stopAt = findViewById(R.id.stop_at)
        stopAfter = findViewById(R.id.stop_after)

        unit.adapter = adapter(R.array.units)
        tapType.adapter = adapter(R.array.tap_types)
        startMode.adapter = adapter(R.array.start_modes)
        stopMode.adapter = adapter(R.array.stop_modes)
        val showFields = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) = updateScheduleRows()
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        startMode.onItemSelectedListener = showFields
        stopMode.onItemSelectedListener = showFields
        startAt.setOnClickListener {
            pickTime(startAtMin) { startAtMin = it; startAt.text = fmtMinuteOfDay(it) }
        }
        stopAt.setOnClickListener {
            pickTime(stopAtMin) { stopAtMin = it; stopAt.text = fmtMinuteOfDay(it) }
        }

        permissionButton.setOnClickListener { explainPermission() }
        showPanel.setOnClickListener { onShowPanel() }

        fill(prefs.load())
    }

    override fun onResume() {
        super.onResume()
        // The target may have been picked from the floating panel meanwhile
        val c = prefs.load()
        target.text = if (c.hasTarget) getString(R.string.target_at, c.x, c.y) else getString(R.string.target_none)
        val enabled = ClickerService.instance != null
        permissionStatus.setText(if (enabled) R.string.permission_on else R.string.permission_off)
        permissionButton.setText(if (enabled) R.string.permission_manage else R.string.permission_turn_on)
        showPanel.isEnabled = enabled
    }

    override fun onPause() {
        super.onPause()
        prefs.save(read())
    }

    private fun fill(c: ClickConfig) {
        interval.setText(c.interval.toString())
        unit.setSelection(c.unit.ordinal)
        jitter.setText(c.jitterSec.toString())
        repeat.setText(c.repeat.toString())
        tapType.setSelection(c.tapType.ordinal)
        posJitter.setText(c.posJitterPx.toString())
        clickNow.isChecked = c.clickNow
        keepScreenOn.isChecked = c.keepScreenOn
        startMode.setSelection(c.startMode.ordinal)
        stopMode.setSelection(c.stopMode.ordinal)
        startAtMin = c.startAtMin
        stopAtMin = c.stopAtMin
        startAt.text = fmtMinuteOfDay(c.startAtMin)
        stopAt.text = fmtMinuteOfDay(c.stopAtMin)
        startIn.setText(fmtHms(c.startInSec))
        stopAfter.setText(fmtHms(c.stopAfterSec))
        updateScheduleRows()
    }

    /** Show only the time field that goes with each chosen start / stop mode. */
    private fun updateScheduleRows() {
        val start = StartMode.entries[startMode.selectedItemPosition]
        val stop = StopMode.entries[stopMode.selectedItemPosition]
        findViewById<View>(R.id.start_at_row).visibility = if (start == StartMode.AT) View.VISIBLE else View.GONE
        findViewById<View>(R.id.start_in_row).visibility = if (start == StartMode.IN) View.VISIBLE else View.GONE
        findViewById<View>(R.id.stop_at_row).visibility = if (stop == StopMode.AT) View.VISIBLE else View.GONE
        findViewById<View>(R.id.stop_after_row).visibility = if (stop == StopMode.AFTER) View.VISIBLE else View.GONE
        findViewById<View>(R.id.sched_note).visibility = if (start == StartMode.NOW) View.GONE else View.VISIBLE
    }

    private fun pickTime(minuteOfDay: Int, onPicked: (Int) -> Unit) {
        TimePickerDialog(this, { _, h, m -> onPicked(h * 60 + m) },
            minuteOfDay / 60, minuteOfDay % 60, DateFormat.is24HourFormat(this)).show()
    }

    private fun read(): ClickConfig {
        val saved = prefs.load()
        return saved.copy(
            interval = interval.int(saved.interval).coerceIn(1, 99_999),
            unit = IntervalUnit.entries[unit.selectedItemPosition],
            jitterSec = jitter.int(0).coerceIn(0, 3600),
            repeat = repeat.int(0).coerceAtLeast(0),
            tapType = TapType.entries[tapType.selectedItemPosition],
            posJitterPx = posJitter.int(0).coerceIn(0, 200),
            clickNow = clickNow.isChecked,
            keepScreenOn = keepScreenOn.isChecked,
            startMode = StartMode.entries[startMode.selectedItemPosition],
            startAtMin = startAtMin,
            startInSec = parseDuration(startIn.text.toString()) ?: saved.startInSec,
            stopMode = StopMode.entries[stopMode.selectedItemPosition],
            stopAtMin = stopAtMin,
            stopAfterSec = parseDuration(stopAfter.text.toString())?.takeIf { it > 0 } ?: saved.stopAfterSec,
        )
    }

    /** Marks a countdown that can't be read; returns false if any is wrong. */
    private fun durationsValid(): Boolean {
        var ok = true
        val fields = listOf(
            Triple(startIn, StartMode.entries[startMode.selectedItemPosition] == StartMode.IN, 0),
            Triple(stopAfter, StopMode.entries[stopMode.selectedItemPosition] == StopMode.AFTER, 1),
        )
        for ((field, used, min) in fields) {
            val sec = parseDuration(field.text.toString())
            if (used && (sec == null || sec < min)) {
                field.error = getString(R.string.bad_duration)
                if (ok) field.requestFocus()
                ok = false
            } else {
                field.error = null
            }
        }
        return ok
    }

    private fun onShowPanel() {
        val service = ClickerService.instance ?: return explainPermission()
        if (!durationsValid()) return
        prefs.save(read())
        service.showPanel()
        moveTaskToBack(true) // go back to the app the user wants to tap on
    }

    /** Says plainly what the permission is used for before sending the user to system settings. */
    private fun explainPermission() {
        AlertDialog.Builder(this)
            .setTitle(R.string.permission_dialog_title)
            .setMessage(R.string.permission_dialog_message)
            .setPositiveButton(R.string.permission_dialog_open) { _, _ ->
                try {
                    startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                } catch (_: ActivityNotFoundException) {
                    startActivity(Intent(Settings.ACTION_SETTINGS))
                }
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun adapter(arrayRes: Int) =
        ArrayAdapter.createFromResource(this, arrayRes, android.R.layout.simple_spinner_item).apply {
            setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }

    private fun EditText.int(default: Int) = text.toString().trim().toIntOrNull() ?: default
}
