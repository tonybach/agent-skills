---
name: build-app-product-page
description: Use when creating or updating a product or marketing web page for an iOS or Android app, refreshing its screenshots, or when a page, privacy policy, or store listing may no longer match what the shipped app does (new release, new SDK, pricing change, dark mode, new devices).
---

# Building an app product page

A product page makes promises about a shipped app. Every claim, screenshot and price on it must match the version people can download today, and must agree with the privacy policy and the store listing.

## 1. Find the truth before you write

| Question | Source of truth |
|---|---|
| Which version is live, in which languages, at what price | The store, not `main`: `curl "https://itunes.apple.com/lookup?id=<appId>&country=us"` gives `version`, `description`, `releaseNotes`, `formattedPrice`, `languageCodesISO2A`. For Play, a 404 on `play.google.com/store/apps/details?id=<pkg>` means not live: show no Play badge and do not say "on Android". |
| Which features shipped | Commits up to the live version's tag or submission. A version in review is not live: describe the live one, and update the page again after approval. Leave out anything newer. Never write "coming soon". |
| Free limits, what the paid tier unlocks, plan types | The code (`freeEntryLimit`, `isPremium` gates), not old copy. |
| What data leaves the device | The app entry point and package list: crash reporting, analytics, purchase SDKs, sync. |
| Who owns an open release | The repo's release notes file (for example `RELEASE.md`). Read it first. |

## 2. Keep four places consistent

The page, the privacy policy (find it from the page's footer link, often `docs/privacy/`), the store description and the store privacy label must say the same thing. If the app uses a crash reporter (Firebase Crashlytics, Sentry), no text may say "zero telemetry", "no exceptions" or "the only third-party service is X". Name each SDK in the policy with what it sends and how long it is kept, and say plainly on the page: "Anonymous crash reports, which never include what you write."

- The store **description** belongs to a version and can change only while a version is editable. If a version is in review or another session owns the release, update the repo's listing files for the next version and tell the user. Promotional text and the privacy policy URL can change any time.
- There is no public API for the App Store **privacy label**. Ask the user to sign in to App Store Connect and check it with you.
- Also update `<meta name="description">` and `og:description`.

## 3. Screenshots

- Capture from a **current build** of the released code, with sample (seed) data, the status bar set to 9:41, and a full battery: `xcrun simctl status_bar <udid> override --time "9:41" ...`
- If the page has dark styles (`prefers-color-scheme`), capture **every** screenshot in light and dark from the **same data and screen**, then switch with `xcrun simctl ui <udid> appearance dark`. Serve them with `<picture><source srcset="x-dark.png" media="(prefers-color-scheme: dark)"><img src="x.png" alt="..."></picture>`. Replace the light image too, so both show the same data.
- Use a simulator only you use. If the project's screenshot simulator is booted, another session may be using it: create a temporary one and delete it afterwards.
- Settings in an App Group need `xcrun simctl spawn <udid> defaults write <group container>/Library/Preferences/<group id> key -bool YES`; launch arguments do not reach them.
- Take proof screenshots with `xcrun simctl io <udid> screenshot`. A simulator panel's screenshot can be stale, so taps look like they failed.
- Keep the old pixel size so the layout does not move. Simple UI compresses well as a 256-color PNG (`Image.quantize(256, dither=NONE)`); compare a crop before you commit.
- For foldables and resizable windows, follow the `support-iphone-duo` skill.

## 4. Page details that break

- A GitHub Pages project site lives under `/<Repo>/`. `href="/"` goes to the owner's main site.
- Keep the number of feature cards a multiple of every column count the grid uses (3 and 2 columns: 6 or 12).
- Prices: show the base price and say the store shows local currency.

## 5. Verify

- Serve the folder under the same path prefix (`/<Repo>/`) on a local server.
- Emulate light and dark. For every image, check `img.currentSrc` and `naturalWidth` with script, not only by eye. Scroll-reveal animations make screenshots of the page look blank.
- Check a 375 px width for horizontal scroll.
- Work in a git worktree, rebase on `origin/main`, then push.

## Common mistakes

| Mistake | Fix |
|---|---|
| Copy describes `main`, not the live version | Compare with the store lookup |
| Light screenshot on the dark theme | Light and dark pair from the same data |
| Privacy text written once, SDK added later | Recheck SDKs on every release |
| Store text changed on a version in review | Change the listing files; apply to the next version |
| Shared simulator reseeded or switched to dark | Temporary simulator |
