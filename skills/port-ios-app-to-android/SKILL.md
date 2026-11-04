---
name: port-ios-app-to-android
description: Use when porting a native SwiftUI iOS app to Android, choosing between Kotlin + Jetpack Compose, Flutter or Kotlin Multiplatform for that port, matching iOS look and behavior in Compose, or when a ported Android app has taps falling through overlays, reminders that never fire in tests, onboarding that repeats after restart, faint status bar icons, or an R8 "Missing classes" failure in the release build.
---

# Port an iOS app to Android

Related skills: `publish-android-play` (signing, Play Console, release).

## 1. Choose the stack

For a pure-Swift app, a native Kotlin + Jetpack Compose port is the best choice. Flutter or KMP would share no code with the existing Swift app, so you would rewrite everything anyway, and you would get a non-native feel on both platforms. Keep the same data model, feature set and product IDs. Map each SwiftUI screen to one Compose screen.

## 2. Port the logic with parity tests

- Port pure logic (dates, streaks, counts, merge rules, limits) first, as plain Kotlin with no Android imports.
- Write JUnit tests for the edge cases: day boundaries, time zones, empty data, limits.
- Run the original Swift code on the same inputs (a small Swift test or a script) and compare the outputs. Fix the Kotlin until both agree.
- Run `./gradlew testDebugUnitTest` before you start on the UI.

## 3. Match the look

- Sample real iOS system colors from a simulator screenshot (a small AppKit or Pillow script that reads pixels). Do not use hand-written hex values: iOS purple, for example, renders more magenta than the published values.
- Map SF Symbols to Material Symbols one by one. Keep a table in the repo.
- Set the status bar icon color for each screen. On a light lock screen or a light background, the icons were faint white. Use `WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = true` (or `enableEdgeToEdge` with a light `SystemBarStyle`).

## 4. Compose traps

- **Taps fall through overlays.** Taps on empty parts of a full-screen Compose layer (an editor, a lock screen, a sheet) reached the screen below. Every full-screen layer must consume pointer input, for example `Modifier.pointerInput(Unit) { detectTapGestures { } }` or a clickable background with no indication.
- **Saves cancelled on navigation.** Onboarding showed again after every restart. `rememberCoroutineScope().launch { save() }` ran on a screen that navigation popped right away, which cancelled the DataStore write. Await the save before you navigate, or save in a ViewModel or application scope.
- **Smoke test:** finish onboarding, force-stop the app (`adb shell am force-stop <pkg>`), open it again. Onboarding must not show.

## 5. Reminders and notifications

- On Android 16, `adb shell am broadcast -n <pkg>/.ReminderReceiver` does not reach a non-exported receiver. You cannot test reminders by broadcast.
- Instead, set a reminder 2 minutes ahead and wait. Inexact alarms can fire a few minutes late.
- Grant the permission first on the emulator: `adb shell pm grant <pkg> android.permission.POST_NOTIFICATIONS`.
- To check WorkManager jobs, `dumpsys jobscheduler` may show nothing. Read `no_backup/androidx.work.workdb` through `adb shell run-as <pkg>`.

## 6. Localization

- Port each `Localizable.strings` / String Catalog language to `res/values-<lang>/strings.xml`.
- For per-app language in system settings, add `res/xml/locales_config.xml` and `android:localeConfig="@xml/locales_config"` in the manifest. Keep the list in sync with the `values-*` folders.

## 7. Build and release traps

- **Gradle wrapper timeout:** the first wrapper download timed out. Set `networkTimeout=120000` in `gradle/wrapper/gradle-wrapper.properties`.
- **R8 and review-ktx:** with `com.google.android.play:review-ktx`, `bundleRelease` failed in R8 with "Missing classes detected while running R8" (class `com.google.android.gms.common.annotation.NoNullnessRewrite`). The debug build did not show it. Add this rule to `proguard-rules.pro`:
  ```
  -dontwarn com.google.android.gms.common.annotation.NoNullnessRewrite
  ```
  Run `./gradlew bundleRelease` after you add any dependency, before you commit.
- Use a separate emulator for each app (see `publish-android-play`), and set `ANDROID_SERIAL` so another session cannot take your device.

## 8. Parity checklist before release

- [ ] Every iOS screen and setting exists on Android, or the difference is written down.
- [ ] Logic parity tests pass.
- [ ] Purchases use the same entitlement and product meaning (RevenueCat entitlement IDs match).
- [ ] Onboarding, lock and reminders survive force-stop and process death.
- [ ] Every language from iOS is present, with `locales_config.xml`.
- [ ] `bundleRelease` builds, and an R8 release build runs the main flows.
