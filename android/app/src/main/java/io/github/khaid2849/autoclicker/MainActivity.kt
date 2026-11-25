package io.github.khaid2849.autoclicker

import android.app.Activity
import android.app.AlertDialog
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.view.WindowInsets
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

        unit.adapter = adapter(R.array.units)
        tapType.adapter = adapter(R.array.tap_types)

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
        )
    }

    private fun onShowPanel() {
        val service = ClickerService.instance ?: return explainPermission()
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
