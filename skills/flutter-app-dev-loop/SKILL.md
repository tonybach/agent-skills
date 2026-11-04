---
name: flutter-app-dev-loop
description: Use when building, testing or checking a Flutter app on an iOS simulator, Android emulator or real phone. Also use when a widget test hangs or reports "A Timer is still pending", when simulator taps miss or screenshots lag, when a debug build will not open from the Home Screen, when Xcode says the signing certificate's private key is not installed, or when two flutter run builds stall. Also covers dart format rewriting whole files, Riverpod "Using ref when a widget is about to or has been unmounted", the keyboard covering fields or MediaQuery.viewInsets reading 0, a SnackBar that never shows, speech_to_text refilling a cleared field, setting up Firebase Crashlytics or Analytics without the Firebase CLI, an app without ads whose build still has advertising ID permissions, removing CocoaPods after Swift Package Manager ("your project still has CocoaPods integration"), and a shared checkout where another session's code does not compile.
---

# Flutter app dev loop

This skill covers building and checking a Flutter app day to day. Other skills cover nearby work:
- `publish-ios-app-store` and `publish-android-play`: store releases.
- `adding-flutter-home-widgets`: widgets.
- `support-iphone-duo`: foldable and resizable layouts.

## 1. Widget tests

- **`pumpAndSettle` hangs** on endless animations (spinners, pulsing mascots, looping Lottie). Use fixed `await tester.pump(const Duration(milliseconds: 300))` steps instead.
- **"A Timer is still pending after the widget tree was disposed"** comes from a provider that loops with `Future.delayed` or `Timer.periodic` (for example a hearts refill). Override that provider in the test with a fixed value. End the test with `await tester.pumpWidget(const SizedBox())`.
- **Database calls hang** (Drift, sqflite, file IO) when they run in the fake-async zone. Put them in `await tester.runAsync(() async { ... })`.
- **Golden test fails:** open the image in `test/**/failures/` before you update the golden. Golden text renders as boxes unless you load fonts (see `adding-flutter-home-widgets`).
- **Time limits:** macOS has no `timeout`. Use `perl -e 'alarm 400; exec @ARGV' flutter test`.
- **Deep flows:** check flows with more than a few taps in widget tests. Use the simulator only for the key screens.

## 2. Driving the simulator or emulator

- Taps sent while a sheet animates, or while a list still scrolls, are lost or hit the wrong row. Wait 1–2 s after a scroll or a transition. Never tap near destructive rows (Delete Account) or external links (Terms, which opens Safari) while content can still move. If you reach a destructive alert by mistake, cancel it.
- A screenshot can show the screen from one step earlier. After each tap that matters, take a new screenshot.
- Panel `text` input can arrive late and be typed twice. Take a screenshot after each text entry.
- If the screen changes when you did not act, the user is probably using the device. Stop and ask.
- **Waiting:** a foreground `sleep N; cmd` is blocked. Use `until <check>; do sleep 2; done`, `run_in_background`, or Monitor. Check the output of a background loop soon after you start it, because a quoting error can make it fail silently.

### Debug screenshot mode (repeatable captures)

Launch arguments are awkward to pass through `flutter run`. Instead, add a debug-only mode that reads `screenshot.txt` from the documents directory. The mode seeds sample data and opens the named screen. Never show screens with real production users (leaderboards, leagues).

```bash
# iOS simulator
echo lesson > "$(xcrun simctl get_app_container <udid> <bundle-id> data)/Documents/screenshot.txt"
# Android (app_flutter = getApplicationDocumentsDirectory)
adb shell "run-as <pkg> sh -c 'echo lesson > app_flutter/screenshot.txt'"
```

### Checking motion

To check an animation or scroll, record a video and make a frame sheet:

```bash
xcrun simctl io <udid> recordVideo --codec h264 /tmp/x.mp4 &   # stop with: pkill -INT -f recordVideo
ffmpeg -i /tmp/x.mp4 -vf "select='gt(scene,0.003)',scale=200:-1,tile=10x3" -frames:v 1 sheet.png
```

### What the simulator cannot test

- Speech recognition: the simulator does not record from the microphone. Piping `say` into it gives nothing. Test speech on a phone.
- `xcrun simctl privacy <udid> grant microphone <bundle>` kills the running app. Grant permissions before launch.

## 3. Real iPhone

- Setup: turn on Developer Mode on the phone, and set a signing team on the Runner target.
- A debug build stops launching from the Home Screen once `flutter run` disconnects. For standalone testing, use `flutter run --release -d <id>`. Release builds still use the StoreKit sandbox.
- If Xcode says "signing certificate … private key is not installed", run `security find-identity -v -p codesigning` first. If this is the only dev Mac, revoking the certificate and making a new one is safe. It does not affect App Store, TestFlight or Xcode Cloud builds.
- Debug builds show a Local Network (Bonjour) prompt, which Flutter adds for the debugger. Release builds do not show it.
- Wi-Fi debugging is unreliable. `xcrun devicectl list devices` shows "unavailable" when the phone is locked or on another network. Use `flutter devices --device-timeout 30` or `flutter run --device-timeout 90`. A USB-C cable is the only stable link.

## 4. Builds and checkouts

- **Two `flutter run` builds on the same `build/ios` stall each other.** Before you start one, run `ps -Ao pid,etime,command | grep "xcodebuild -cloned"`.
- **Hot reload (`r`) does not re-create services** that are already initialized. Use hot restart (`R`) after you change service setup.
- **Another session's uncommitted code does not compile:** build from a detached worktree.
  ```bash
  git worktree add --detach .claude/worktrees/verify origin/main
  cp app/secrets.json .claude/worktrees/verify/app/   # plus other git-ignored configs
  ```
  Use `.claude/worktrees/` instead of the scratchpad, because the terminal tool can refuse a scratchpad working directory.
- **Shared file, shared hunks:** `git add <file>` also stages another session's uncommitted hunks in that file. Use `git add -p` and check `git diff --cached` before you commit.
- **`dart format` rewrote whole files.** The project may use a longer `formatter: page_width` in `analysis_options.yaml`. Read it first. Never format files that another session is editing; format only your own lines.
- A file under a package's `lib/` cannot import a path outside the package. A `bin/` script can.

## 5. Flutter bug patterns

| Symptom | Cause | Fix |
|---|---|---|
| "Bad state: Using "ref" when a widget is about to or has been unmounted is unsafe" | `ref.read` in `dispose` (Riverpod 3) | Cache the service in `initState` and use the cached value in `dispose` |
| `animateTo(maxScrollExtent + 200)` springs back on iOS | Bounce physics | Scroll to the real `maxScrollExtent` in a post-frame callback |
| A cleared text field fills again after send | `speech_to_text` `stop()` delivers a final result | Call `cancel()` on send |
| The keyboard covers controls below a field; `MediaQuery.viewInsets` reads 0 | The outer Scaffold already used the inset | Use a `WidgetsBindingObserver.didChangeMetrics` listener and scroll the controls into view |
| A `SnackBar` never shows | A nested Scaffold catches it | Show the note as an overlay on the widget |
| An LLM feature gets facts about the input text wrong (letter counts, accents, word parts) | A rule in the prompt alone does not work | Compute the data in code and pass it into the prompt |

## 6. Firebase Crashlytics and Analytics without the Firebase CLI

1. Run `gcloud services enable firebase.googleapis.com`. Then call the REST API `POST https://firebase.googleapis.com/v1beta1/projects/<id>:addFirebase`.
2. Register the iOS and Android apps through the same API and download their configs.
3. Keep `google-services.json` and `GoogleService-Info.plist` git-ignored. Store master copies outside the repo (for example `~/.<app>/`), and copy them into each new worktree. Apply the Gradle plugins only if `google-services.json` exists, so the app still builds without it.
4. **Version clash:** `firebase_core` 5.x conflicted with `google_sign_in_ios` (GoogleSignIn 9). Pin `firebase_core: ^4.15` (Firebase iOS SDK 12.x) until the two match.
5. Debug builds turn collection off. To check, use a release build: crash it, open it again, then query `https://firebasecrashlytics.googleapis.com/v1alpha/projects/<number>/apps/<appId>/issues`.
6. zsh trap: never name a loop variable `path`, because zsh ties it to `PATH`.

**Analytics in an app without ads.** Add `firebase_analytics` from the same Firebase line as `firebase_core`. Then:

1. **Start with collection off.** `setAnalyticsCollectionEnabled(!kDebugMode)` runs too late: the SDK collects at launch before Dart calls it. Set `FIREBASE_ANALYTICS_COLLECTION_ENABLED` = NO in `Info.plist` and the `<meta-data>` `firebase_analytics_collection_enabled` = `false` in the manifest. Then turn it on in code for release builds.
2. **iOS advertising ID:** with Swift Package Manager the plugin links `FirebaseAnalytics` (with IDFA support). The environment variable `FIREBASE_ANALYTICS_WITHOUT_ADID=true` removes it, but only for builds that set it, so do not rely on it. Set `GOOGLE_ANALYTICS_IDFA_COLLECTION_ENABLED` = NO and `GOOGLE_ANALYTICS_DEFAULT_ALLOW_AD_PERSONALIZATION_SIGNALS` = NO in `Info.plist`. These keys are enough. Also set `FirebaseAutomaticScreenReportingEnabled` = NO: Flutter has one view controller, so automatic screen views are useless.
3. **Android ad permissions:** the merged manifest gets `com.google.android.gms.permission.AD_ID`, `android.permission.ACCESS_ADSERVICES_AD_ID` and `android.permission.ACCESS_ADSERVICES_ATTRIBUTION`. Remove all three with `tools:node="remove"` (add `xmlns:tools` to `<manifest>`). Add the `<meta-data>` `google_analytics_adid_collection_enabled` and `google_analytics_default_allow_ad_personalization_signals`, both `false`. Check the release APK with `aapt dump permissions`.
4. **Screen views with go_router:** listen to `router.routerDelegate` and log `currentConfiguration.fullPath` (a pattern such as `/story/:id`, so no IDs). For a pushed route, `currentConfiguration.last` is an `ImperativeRouteMatch`: use its `matches.fullPath`. Skip a path that equals the last one.
5. **Parameters:** Firebase takes only strings and numbers, at most 25 per event, names up to 40 characters, string values up to 100. Convert bools to 0 or 1 and drop nulls, or the call fails.
6. **Check a release build:** `adb shell setprop debug.firebase.analytics.app <package>` and `adb shell setprop log.tag.FA-SVC VERBOSE`, start the app, then `adb logcat | grep "Logging event"`. On iOS the log shows `GoogleAppMeasurementIdentitySupport dependency is not currently linked. IDFA will not be accessible`, or `Analytics collection disabled` in debug. Reset with `setprop debug.firebase.analytics.app .none.`.
7. **Install trap:** a debug build on the emulator has a different signature, so `adb install -r` of the release APK fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Piped through `tail -1`, the error is hidden and the old build keeps running. Run `adb uninstall <package>` first and read the full output.
8. Update the store privacy forms: approximate location (from IP), device ID and purchase history gain the purpose analytics.

The Crashlytics dSYM script settings are in the global CLAUDE.md (Xcode Build Settings).

## 7. Removing CocoaPods after Swift Package Manager

Flutter warns: "All plugins found for ios are Swift Packages, but your project still has CocoaPods integration". To fix it:

```bash
cd ios && LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 pod deintegrate   # fails without a UTF-8 locale
rm -rf Podfile Podfile.lock Pods
```

Then remove the `#include? "Pods/Target Support Files/Pods-Runner/..."` lines from `Flutter/Debug.xcconfig` and `Flutter/Release.xcconfig`. Also remove the empty Pods group from the pbxproj. Build both platforms again.
