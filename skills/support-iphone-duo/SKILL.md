---
name: support-iphone-duo
description: Use when making an iOS app work on iPhone Duo (Apple's foldable iPhone), testing in the iPhone Duo simulator or Xcode Device Hub, adapting a portrait-only SwiftUI iPhone app to resizable windows, wide or short layouts, vertical toolbars, or iOS 27.1 SDK changes, or when Xcode 27.1 builds fail after upgrading.
---

# Supporting iPhone Duo

Learned from adapting a portrait-only SwiftUI journal app (SwiftData, RevenueCat, Firebase, xcodegen) in Oct 2026 and verifying it in the Xcode 27.1 iPhone Duo simulator. Follow the phases in order. The verification phase holds most of the traps.

## Ground rules

- The user must do three things themselves: accept the Xcode license (`sudo xcodebuild -license`), install Xcode 27.1 and the iOS 27.1 runtime, and grant Accessibility permission if you need to drive Device Hub. Never change security settings, and never click macOS permission dialogs. Read a dialog's text and tell the user what it asks.
- Do not claim a pose is verified until you have seen a screenshot of it. Say which poses you could not reach.

## Phase 1: Facts to know

**Requirements:** Apple silicon Mac, macOS 26.6 or later, Xcode 27.1, iOS 27.1 simulator runtime. Xcode 26.x has no Duo device type.

**What the SDK the app is built with does:**

| Built with | On iPhone Duo |
|---|---|
| iOS 26 SDK or earlier | Not resized. Centered with empty space when open; fixed 375 x 667 pt window. |
| iOS 27.0 SDK | Resizes, but avoids the status bar edge. Bars stay horizontal. |
| iOS 27.1 SDK | Edge to edge on both displays. Toolbars and tab bars become a **vertical rail on the trailing edge** when closed and when open in portrait-width layouts. |

**Window sizes (27.1 SDK) and size classes:**

| Pose | Window (pt) | Size class (w / h) |
|---|---|---|
| Closed (outer display) | 466 x 678 | compact / regular |
| Closed, turned | 678 x 466 | compact / compact |
| Open, Book ("Partially Open") | 951 x 669 | regular / regular |
| Open or Book, turned | 669 x 951 | regular / regular |

- Outer display: 1398 x 2034 px. Inner display: 2007 x 2853 px native (shown landscape when open). The status bar sits on the **right edge** of the closed display.
- Folding or unfolding resizes the running app. Re-read sizes on every change; never cache launch-time sizes.
- On the inner display the app should look like its iPad layout.

## Phase 2: Audit the code

Search for and remove each of these:

```bash
grep -rn -E "UIScreen\.main|userInterfaceIdiom|UIDevice\.current\.orientation|statusBarOrientation|interfaceOrientation|UIWindow\(frame|bounds\.(width|height) *==" <AppSources>
```

- `UIScreen.main.bounds` → view/window bounds, `GeometryReader`, or `onGeometryChange`. Scale → `@Environment(\.displayScale)`.
- Idiom or device-size checks → size classes or available space. `horizontalSizeClass == .regular` now runs on iPhone.
- `UIWindow(frame:)` → `UIWindow(windowScene:)`.
- `.scaledToFill()` hero media can crop badly on wide windows.

Then look for layout problems a clean grep will not find:

1. **Portrait-only iPhone apps.** `UISupportedInterfaceOrientations` with only portrait blocks the turned poses. Add `UIInterfaceOrientationLandscapeLeft` and `UIInterfaceOrientationLandscapeRight` (in `project.yml` too if you use xcodegen). This also enables landscape on every iPhone, so check landscape on a normal iPhone before you ship.
2. **Fixed-height pages** (onboarding, paywalls) built from `VStack` + `Spacer()` clip on the 466 pt closed-turned height.
3. **Full-width content** stretches across 951 pt.
4. **Text-only toolbar items.** The 27.1 vertical rail only shows items with a symbol. `Button("Done") { }` needs a symbol.
5. **Horizontal `ScrollView` rows** inside a vertical scroll draw into the safe area and slide under the vertical rail.
6. **Stacked layouts** (for example a calendar above a list) leave no room in compact height.

## Phase 3: Fix patterns

Copy `scripts/AdaptiveLayout.swift` into the app. It has:

- `readableWidth(_:)`: caps width and centers. Use about 480 pt for single-column pages and about 700 pt for lists and editors. Use the same width for a header and the content below it, or they misalign.
- `FillingScrollView`: fills the height like a `VStack` (so `Spacer`s still center the content), and scrolls when the window is too short.
- `PinnedActionPage`: content scrolls above a bottom-pinned action area. Put the primary button **and anything the user decides on** (for example the price) in the pinned area. If the price stays in the scroll area, it ends up half hidden behind the buttons.

Other fixes that worked:

```swift
// Toolbar items: give every item a symbol so it can move into the vertical rail
Button("Done", systemImage: "checkmark") { dismiss() }          // .confirmationAction
Button("Cancel", systemImage: "xmark") { dismiss() }            // .cancellationAction

// Horizontal rows inside a vertical ScrollView: keep them out from under the rail
ScrollView(.horizontal, showsIndicators: false) { ... }
    .clipped()

// Two panes when wide OR short; stacked otherwise
@Environment(\.horizontalSizeClass) private var hSize
@Environment(\.verticalSizeClass) private var vSize
private var sideBySide: Bool { hSize == .regular || vSize == .compact }
// In the side pane, wrap the fixed part (calendar) in a ScrollView so it fits compact height.

// Grids: adaptive columns instead of a fixed count
LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) { ... }

// Medium-only sheets are cramped at 466 pt tall
.presentationDetents([.medium, .large])
```

- Cards with `Color(.systemGray6)` vanish on iPad and Duo form sheets, because the sheet background is the same gray. Use `Color(.tertiarySystemFill)`.
- `ForEach(Calendar.current.veryShortWeekdaySymbols, id: \.self)` drops the repeated "S" and "T". Wide layouts make the missing columns obvious. Use `Array(symbols.enumerated())` with `id: \.offset`.
- Page indicators overlaid at the bottom collide with scrolled content. Put the pinned actions in a `safeAreaInset(edge: .bottom)` with a background, and keep the dots in the inset's bottom padding.

## Phase 4: Build with Xcode 27.1

- **RevenueCat 5.59.0 does not compile** with the Xcode 27.1 Swift compiler: `PaywallColor.swift: error: invalid redeclaration of synthesized memberwise 'init(stringRepresentation:)'`. 5.96.0 works. A `majorVersion: 5.0.0` range does not help, because `Package.resolved` pins the old version, and `xcodebuild -resolvePackageDependencies` reuses the cached checkout.
- To bump a pin, edit `Package.resolved`. Set `version`, and set `revision` to the **commit** hash. For an annotated tag that is the peeled `^{}` line of `git ls-remote <repo> refs/tags/<v> 'refs/tags/<v>^{}'`, not the tag-object hash. Then delete the DerivedData `SourcePackages` and rebuild.
- `ibtoold no longer exists at path ... exiting immediately` / `CompileAssetCatalogVariant failed` means Xcode was replaced mid-build. Rerun after the install finishes.
- `You have not agreed to the Xcode license agreements` blocks `simctl` and builds. The user runs `sudo xcodebuild -license`.

## Phase 5: Verify in the Duo simulator

**Find the simulator:** `xcrun simctl list devices available | grep -i duo` (iOS 27.1 runtime). Boot it with `xcrun simctl boot <udid>`. The simulator UI is **Device Hub** (`/Applications/Xcode.app/Contents/Applications/DeviceHub.app`). There is no separate `Simulator.app` in Xcode 27.

**Screenshots:**
- `xcrun simctl io <udid> screenshot` captures the inner display, which is **black while closed**. List the displays with `xcrun simctl io <udid> enumerate` and capture with `--display=<uuid>`. Pick the display by `Default width` (1398 = outer, 2007 = inner). **The UUIDs change between launches**, so look them up every time.
- A `simctl io ... screenshot` call can hang. Wrap it: `perl -e 'alarm 8; exec @ARGV' xcrun simctl io ...`.
- `XCUIScreen.main.screenshot()` and `XCUIScreen.screens` return **black images** on the Duo simulator. Use the handshake in `scripts/ScreenTourUITests.swift` + `scripts/duo-capture-watcher.sh`: the test writes `<id>.ready`, the host script captures both displays with simctl and writes `<id>.done`.
- Pass `TEST_RUNNER_SHOT_DIR=... TEST_RUNNER_POSE=...` to `xcodebuild test`; the test reads them as `SHOT_DIR` and `POSE`. The simulator shares the host file system, so the test can write marker files to a host path.

**Driving the app:** Use a temporary UI-testing target (the template above) and remove it before you commit. Launch arguments `-key value` override `@AppStorage` / `UserDefaults` for one launch: `["-hasCompletedOnboarding", "NO"]`. To write persistent prefs instead, run `xcrun simctl spawn <udid> defaults write <data-container>/Library/Preferences/<bundle-id> key -type value`. A host-side `defaults write` to that plist is ignored, because the simulator's `cfprefsd` caches values.

**Poses (the hard part):**
- `simctl` has no fold/hinge command. `simctl io screenConfig ... power off` does not fold the device. XCUITest has no fold API, and `XCUIDevice.shared.orientation` **does nothing** on the Duo.
- Only Device Hub can change poses. Its window has buttons **Closed**, **Partially Open** (Book), **Open** and **Rotate Right**. Its menus have **Controls → Rotate Left/Right** and **Device → Orientation**.
- With the user's Accessibility permission, `scripts/devicehub.swift` presses those buttons (`./devicehub press "Open"`). System Events cannot see Device Hub's window (it reports unix id 0), and `NSRunningApplication` reports pid -1, so the script uses the AX API with the pid from `pgrep`.
- **Do not quit Device Hub.** Quitting it shuts down the booted Duo. After a restart, its window's accessibility tree was broken for a while (the window reported itself as the app, recursively), so pose buttons and device menu items were unreachable. It recovered later on its own. If `./devicehub dump` shows no buttons, wait and retry rather than restarting again. Change poses in one Device Hub session where you can, in this order: Closed (default after boot) → Rotate Right → back → Open → Rotate Right → back → Partially Open.
- Device Hub can show several devices. `dump` prints the window title (for example `iPhone Duo – iOS 27.1`). Check that it names the Duo before you press anything.
- Cover at least: closed, closed turned, open, open turned, Book. Book has the same window size as open, but sheets anchor to the leading half.
- The Duo has Touch ID, not Face ID. Biometric lock screens fall back to the passcode prompt until you choose **Device → Touch ID → Enrolled**.
- The Claude Code iOS Simulator panel tool could not load the Xcode 27.1 device set ("Failed to initialize simulator device set"). Fall back to `simctl` and the UI-test handshake.

**When the Duo simulator is unavailable:** iPad simulators in windowed mode (iPadOS 26+) can approximate Duo windows. Drag the bottom-right resize corner to about 466 x 678, 678 x 466 and 951 x 669 pt. This catches clipping, scrolling and width problems, but not the vertical rail or the 27.1 safe areas.

## Review checklist per screenshot

- Nothing hides under the right-edge status bar or the vertical rail (look closely at horizontal scroll rows).
- Primary actions are visible without scrolling in closed turned (466 pt tall).
- No full-width text lines on the inner display; headers align with the content below them.
- Sheets stay readable at medium height and can expand.
- Grids reflow to more columns when wide.
