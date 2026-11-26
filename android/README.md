# Auto Clicker for Android

A native Kotlin app (no extra libraries) with the same options as the desktop app.
Needs Android 7.0 or newer.

## How it works

| File | What it does |
|---|---|
| `ClickerService.kt` | An **accessibility service**: the only way Android lets an app tap on other apps (`dispatchGesture`). It also draws the floating panel, the target marker and the picker over other apps (`TYPE_ACCESSIBILITY_OVERLAY`, so no "display over other apps" permission is needed) and runs the timer. |
| `PickerView.kt` | Full-screen crosshair with live X/Y. Lifting the finger picks the spot. |
| `MainActivity.kt` | Settings screen and the permission explanation. |
| `ClickConfig.kt` | Settings, timing maths (`nextIntervalMs`, `tapPoint`, `fmtDuration`), the start/stop schedule (`plan`, `nextClockMs`, `parseDuration`) and saving. Plain Kotlin with unit tests. |

Differences from the desktop app: taps instead of mouse buttons (tap, double tap, long press). There's no cursor to put back.
The emergency stop is the ■ button on the floating panel.

## Build

Use Android Studio (open this `android/` folder), or from the command line with JDK 17, the Android SDK and Gradle 8.14:

```bash
cd android
gradle testDebugUnitTest assembleDebug     # -> app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Run `gradle wrapper` once to add `./gradlew`, so you no longer need Gradle installed.

## Signing releases

APKs signed with different keys can't update each other, so release builds need one fixed key:

```bash
keytool -genkeypair -v -keystore release.jks -alias autoclicker -keyalg RSA -keysize 4096 -validity 10000
base64 -w0 release.jks   # paste the output into the ANDROID_KEYSTORE_BASE64 secret
```

In GitHub → Settings → Secrets and variables → Actions, add `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`,
`ANDROID_KEY_ALIAS` and `ANDROID_KEY_PASSWORD`. **Keep `release.jks` safe and out of git.** If you lose it, you can't publish updates.
Without the secrets, CI still builds an APK, but it's signed with a throwaway debug key.

## Google Play

Play has strict rules for apps that use the Accessibility API for something other than helping people with disabilities.
Expect a review declaration and a possible rejection. Releases are published as an APK on GitHub instead.
