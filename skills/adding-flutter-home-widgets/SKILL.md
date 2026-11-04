---
name: adding-flutter-home-widgets
description: Use when adding a home screen widget to a Flutter app (iOS WidgetKit or Android app widget, usually with the home_widget package), adding an app extension target to a Flutter Xcode project from the terminal, or when a widget shows stale state after midnight, never shows its image, crashes the app in the background, or the build fails with "Multiple commands produce .../.appex" or "Cycle inside Runner".
---

# Adding Flutter home screen widgets

## Overview

A Flutter home screen widget is native code on each platform (SwiftUI WidgetKit extension, Android `AppWidgetProvider`) that reads values the Dart app saves with `home_widget`. Most traps are in the iOS target setup, in value types, and in when Dart draws images for the widget.

## iOS target from the terminal

Use `add_widget_target.rb` in this folder (Ruby `xcodeproj` gem, which CocoaPods installs). Never edit `project.pbxproj` by hand. The script sets what the traps below need. Then build once (`flutter build ios --simulator`) and check that `Runner.app/PlugIns/<Name>.appex` exists.

| Symptom | Cause | Fix |
|---|---|---|
| `Multiple commands produce '.../.appex'` (no name before `.appex`) | `PRODUCT_NAME` empty on the new target | `PRODUCT_NAME = $(TARGET_NAME)` |
| `Cycle inside Runner` | Embed phase after "Thin Binary" | Move "Embed Foundation Extensions" before it |
| Link errors or Pods flags in the extension | Target uses Runner's xcconfig (includes Pods) | Own xcconfig with only `#include? "../Flutter/Generated.xcconfig"` |
| Version mismatch at upload | Hardcoded versions | `$(FLUTTER_BUILD_NAME)` / `$(FLUTTER_BUILD_NUMBER)` |
| Blank widget on iOS 17+, or build error on `containerBackground` | API is iOS 17+, the script targets 15.0 | `if #available(iOS 17.0, *) { view.containerBackground(.fill.tertiary, for: .widget) } else { view.padding() }` |
| Widget reads nothing | App Group missing on one target, or `setAppGroupId` not called first | Same group in both entitlements; call `HomeWidget.setAppGroupId` before any save |
| Upload warns ITMS-91053 (missing API declaration) | `home_widget` writes App Group `UserDefaults` and ships no privacy manifest | Add `PrivacyInfo.xcprivacy` to Runner (`NSPrivacyAccessedAPICategoryUserDefaults`: `CA92.1` and `1C8F.1`) and to the widget extension (`1C8F.1`). Add both to their targets with `xcodeproj`, then check that `Runner.app/PlugIns/<Name>.appex/PrivacyInfo.xcprivacy` exists after a build |

## Values the widget reads

- Save the date of the last activity (`yyyy-MM-dd`, local), never a "done today" boolean. Store every per-day value (a count, a goal) next to the date it belongs to, and show the reset value when that date is not today. Each platform computes "done" and "still alive" from the date, so the widget is right after midnight with the app closed. Keep the rule in one pure Dart function with tests, and mirror it in Swift and Kotlin with a comment that points to it.
- When setup or onboarding finishes, save every value the widget reads, then call `HomeWidget.updateWidget`. If the app saves only in change handlers, values the user left at their defaults are never written, and the widget shows its "Open app to set up" state forever.
- iOS timeline: one entry now and one just after the next midnight, policy `.after(midnight)`.
- Android: compute in `onUpdate`; `updatePeriodMillis="1800000"` redraws at least every 30 minutes.
- Android types: `home_widget` stores a small Dart `int` as an `Int` (`<int>` in `HomeWidgetPreferences.xml`). `getLong` on it throws. Read numbers with `(prefs.all["key"] as? Number)?.toInt()`.
- Android dates: `java.time` needs API 26. Below that, use `Calendar` and `SimpleDateFormat("yyyy-MM-dd", Locale.US)`.

## Drawing a Flutter image for the widget

`HomeWidget.renderFlutterWidget` needs a live screen. Before the first frame it can wait forever, and in the background it crashed the Android raster thread (SIGSEGV in `libflutter.so`).

```dart
final binding = WidgetsBinding.instance;
await binding.waitUntilFirstFrameRasterized.timeout(const Duration(seconds: 10));
final foreground = binding.lifecycleState == null || binding.lifecycleState == AppLifecycleState.resumed;
if (foreground && _drawnFor != key) { /* renderFlutterWidget(...) */ }
```

- Draw only when the image changes (for example the mascot's hat), not on every update.
- Call the widget update last, after notifications and other startup work, so its wait never delays them.
- Wrap it all in `try`/`catch`: a widget must never break the app.
- The call saves the PNG path under the given key. Native code reads that key and loads the file: `UIImage(contentsOfFile:)` with `UserDefaults(suiteName: appGroup)` on iOS, `BitmapFactory.decodeFile` then `setImageViewBitmap` on Android.
- The file is missing until the app opens and draws it: in the widget gallery, on a fresh install, and in the Android picker preview (it uses the layout). Do not hide the image or show an emoji there. Bundle a default PNG in the widget's Asset Catalog and in `res/drawable-nodpi`, fall back to it in code, and set it as `android:src` in the layout.
- Draw the default PNGs from the same painter with a script run by `flutter test` (`RepaintBoundary`, then `toImage` inside `tester.runAsync`). Tests use a blank font, so text draws as boxes. Load the real font with `FontLoader` and `await loader.load()` directly in the test body; inside `tester.runAsync` the load hangs.
- Images that never change can be static assets instead (Asset Catalog and `res/drawable-nodpi`).

## Verify

- iOS simulator: long-press the home screen, then the edit button, then **Add Widget**. The gallery uses `placeholder` or `getSnapshot`; check real data after you add it.
- Android: `adb shell dumpsys appwidget | grep <package>` shows the provider. In the launcher, **Widgets** search does not match a name without its accents (search "Cafe" misses "Café"); search for a word in the widget label. `adb shell run-as <package> cat shared_prefs/HomeWidgetPreferences.xml` and `ls files/home_widget` show the saved values and images.
- `adb uninstall` also removes the placed widget from the Android home screen. Reinstall with `adb install -r` to keep it, or add the widget again after an uninstall.
- iOS: check that the extension bundle holds its images with `xcrun assetutil --info <Runner.app>/PlugIns/<Name>.appex/Assets.car`.
- Send the app to the background, refresh the widget, and check the log for crashes.
