---
name: publish-android-play
description: Use when preparing, uploading, or releasing an Android app on Google Play, setting up Play subscriptions or one-time products (especially with RevenueCat), filling Play Console "Set up your app" / App content forms, or automating Play uploads with fastlane.
---

# Publishing an Android app to Google Play

Learned from shipping two Kotlin/Compose + RevenueCat apps in Oct 2026. Follow the phases in order. Each phase lists what Claude can do, what only the user can do, and the traps that cost time.

## Ground rules

- **Never read, print, type, or store passwords or private keys.** The user types keystore passwords and creates key files. Claude may check a file's *structure* (keys present / `"type": "service_account"`) without printing secret values.
- **Ask before:** accepting any terms of service, downloading files, installing tools, creating store products, changing live RevenueCat offerings, "Save and publish" on store settings, promoting to production, and "Send changes for review". Group small approvals into one table the user can approve at once.
- Release with **drafts**; the user (or an explicit "send it") starts every rollout.
- **Permission-check denials are expected** in auto mode for: creating service accounts/keys (`gcloud iam ...`), creating paid products through the Play API, and `attach-products-to-entitlement`. Do not retry or route around them. Give the user the exact command or console steps, or ask them to allow that one tool, then continue.
- Exception to the password rule: only when the user explicitly asks Claude to create the upload key, generate the password with `openssl rand`, write it only to git-ignored `keystore.properties` (chmod 600), keep a backup outside the repo (e.g. `~/.<app>/`), never print it, and tell the user to back up that folder.
- Record IDs and state in the project's release guide (e.g. `PlayStoreRelease.md`) with a status table, and commit it.

## Phase 0 — Inventory (Claude)

1. Read the project's release guide, `app/build.gradle.kts` (`applicationId`, `versionCode`, `targetSdk` — Play requires the current target API for new apps), `libs.versions.toml` (RevenueCat SDK version), `AndroidManifest.xml`.
2. Ask the user: **Personal or Organization developer account?** Personal accounts created after Nov 13 2023 need a closed test with 12+ testers for 14 days before production. Organization accounts skip it. If Play Console is open in the browser, read it instead of asking: the account home shows "Organization account" or "Personal account" under the developer name.
3. **Entitlement ID check:** grep the app (Android *and* iOS) for `entitlements["..."]` and compare with the RevenueCat entitlement `lookup_key` from `list-entitlements`. A mismatch (code `"lifetime"`, dashboard `"<App> Pro"`) makes paid users look unpaid after a restart and makes Restore find nothing, even though the purchase call "succeeds".
4. If the listing or Data safety will claim data stays on the device, check `android:dataExtractionRules` / `fullBackupContent` exclude app data from cloud backup; Auto Backup uploads to Google Drive by default.
5. The Play app record must exist before any API or fastlane call; only the user can create it (Play Console → Create app). The first AAB can be uploaded in the console (Internal testing → Create release).
6. Check what already exists before creating anything: Play app record, RevenueCat apps, products, entitlements, offerings (`list-apps`, `list-products`, `list-offerings` with `expand`). Earlier sessions often created things already; a 409 "already exists" means look, not retry.

## Phase 1 — Signing and the release bundle

- `keystore.properties` and `*.jks` must be git-ignored. Give the user a `printf` command that writes every non-secret line, then they fill `storePassword`/`keyPassword`.
- **Find the key alias without the password:** `echo "" | keytool -list -keystore app.jks` prints the alias (`Certificate chain length: 0` is fine). A wrong alias shows as `No key with alias 'X' found`. The alias is not secret; Claude may fix that one line with `sed`.
- Lost password and no build uploaded yet → new upload key with `keytool -genkeypair ... -alias upload`. Build already uploaded → Play Console → App integrity → request upload key reset.
- Java: if `java` is missing, use `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`.
- Make release builds **fail on purpose** when signing values are missing or the RevenueCat key is not `goog_` (prevents shipping a Test Store key).
- If other sessions are editing the code, build from a clean `git worktree` at HEAD (copy `keystore.properties`/`.jks` in, delete them after). Rebuild if main moves with changes that should ship.
- **Verify the AAB before upload:**
  - `jarsigner -verify -verbose -certs app-release.aab` → `jar verified`, expected signer.
  - Unzip to a temp dir; `grep -a -o -E "(goog|test)_[A-Za-z0-9]{20,}"` over `*.dex` → only the `goog_` key.
  - `base/manifest/AndroidManifest.xml` contains `com.android.vending.BILLING` if there are purchases.
  - Merged manifest (`app/build/intermediates/merged_manifest/release/...`): note whether `com.google.android.gms.permission.AD_ID` is present — needed for the advertising ID declaration.
- **Smoke-test the R8 release build** before upload: `apksigner sign --ks ~/.android/debug.keystore --ks-pass pass:android --out test.apk app-release-unsigned.apk`, uninstall the debug app (signatures differ), install, and open each screen. Cold-start time: `adb shell am start -W -n <pkg>/.MainActivity` → `TotalTime` (measure 2–3 runs; the first run after install is slow).
- **versionCode may already be taken** by an earlier manual upload ("Version code 1 has already been used"). Check first with `fastlane run google_play_track_version_codes track:internal ...`, then bump `versionCode` and rename `changelogs/<code>.txt`.

## Phase 2 — Store assets (Claude)

- Feature graphic 1024×500: write HTML (app icon, name, tagline, a visual motif), render with
  `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=1024,500 --screenshot=out.png file://.../page.html`. Keep the HTML source in the repo.
- Phone screenshots: launch a debug build on the emulator (`./gradlew :app:installDebug`), drive it with `adb shell input tap/text/swipe`, capture with `adb exec-out screencap -p`. Use the debug premium bypass to reach paid screens; add realistic sample data (entries, lists, history). Play limits the long side to 2× the short side: crop 1080×2400 to 1080×2160 with `sips -c 2160 1080 --cropOffset 120 0`.
- No cropping needed if you set the emulator to exactly 9:16 first: `adb shell wm size 1080x1920`. Clean status bar with SystemUI demo mode: `adb shell settings put global sysui_demo_allowed 1`, then `am broadcast -a com.android.systemui.demo -e command <enter|clock -e hhmm 0941|battery -e level 100 -e plugged false|network -e wifi show -e level 4 -e fully true|notifications -e visible false>`. Afterwards: `wm size reset` and `-e command exit`.
- Emulator traps: a cold boot drops the screen-lock PIN (`adb shell locksettings set-pin 1234` before shooting lock screens; an app may refuse to enable its lock without one). `adb shell input text` can double letters with Gboard. Gboard's floating toolbar covers the left edge and swallows taps/swipes: start swipes at x > 300 or press Back to close the keyboard. Find tap targets with `uiautomator dump` + bounds instead of guessing pixels.
- No Chrome? A short Swift/AppKit script (`NSBitmapImageRep` 1024×500, draw icon + `NSAttributedString`, write PNG) also renders the feature graphic.
- **Remove alpha** (Play wants 24-bit PNG/JPEG): `sips -s format jpeg x.png --out t.jpg && sips -s format png t.jpg --out x.png`; check with `sips -g hasAlpha`.
- Check the icon for stray marks (e.g. an AI-generator watermark in a corner). A watermark also means the **AI asset declaration** in Phase 5 needs "Label assets" for the icon and any graphic that contains it — ask the user.
- Adapting App Store text: fetch the live description with `curl "https://itunes.apple.com/lookup?id=<appStoreId>&country=us"` and replace iOS-only words (iPhone, Face ID/Touch ID, Apple storage, iCloud). Assert none remain before saving.
- Write the listing text (name ≤30, short ≤80, full ≤4000) for every app language; count lengths with Python before saving.

## Phase 3 — In-app products and RevenueCat

**Tools:** RevenueCat MCP via the plugin (`claude plugins marketplace add RevenueCat/ai-toolkit`, `claude plugins install revenuecat`). The user authenticates with `/mcp` **in the same session that will use it** (signing in from another session does not carry over). If a call says "needs you to sign in again", ask for `/mcp` again.

- Quick read-only check of what the SDK will receive: `curl -H "Authorization: Bearer <public appl_/goog_ key>" -H "X-Platform: iOS|android" https://api.revenuecat.com/v1/subscribers/<any_id>/offerings`.
- **Attach new products to the entitlement before swapping them into packages**, or buyers pay and get nothing. Keep legacy products on the entitlement so existing buyers keep access.
- `get-product-store-state` can fail transiently with `store_unauthorized`; run `validate-app-credentials` and retry before blaming keys.
- **Play subscriptions via RevenueCat** (`create-product-store-state-plan` → `plan-...` → poll `get-...` → user approves → `apply-...`):
  - Store identifier is `subscriptionId:basePlanId` (e.g. `app.monthly:monthly`). Ask/decide base plan IDs up front; a probe product with a guessed ID shows `not_found` + empty `base_plans` when the subscription does not exist yet — archive the probe after.
  - Blocker "credentials cannot create or update products" → user grants the service account **Manage store presence** in Play Console.
  - Blocker on `display_name` already used (even by an archived product) → use a distinct name like "Pro Monthly (Play)".
  - `other_regions_config` prices apply only to **future** regions. After apply only the explicit regions are live; tell the user to open each base plan → **Edit prices** to convert to all regions (RevenueCat cannot do Google's currency conversion). Then re-read store state and count priced regions.
- **RevenueCat cannot create or read Play one-time products.** The user creates them in Play Console: Product ID matching iOS, Buy purchase option (e.g. ID `lifetime`), **backwards compatible ON**, multi-quantity OFF, US price then convert, activate. In RevenueCat mark it non-consumable (`is_consumable: false`, needs Android SDK ≥ 7.11).
- RevenueCat **Test Store** keys need a recent Android SDK; on old SDKs the debug paywall spins forever with "Billing is not available". Upgrade the SDK and give the paywall an error + retry state.
- Get the public SDK key with `list-app-public-api-keys` → `revenueCatGoogleApiKey` in `keystore.properties`.
- New Play app in an existing RevenueCat project: `create-app` (`type: play_store`, `play_store.package_name`) → `create-product` (`store_identifier` = the Play product ID, same as iOS; `type: non_consumable` comes back as `one_time`) → `attach-products-to-entitlement` → `attach-products-to-package` (`eligibility_criteria: all`) on the existing `$rc_lifetime` package. Re-read with `get-products-from-entitlement` and `list-packages`. After the user uploads the JSON key, `validate-app-credentials` (`google_play_service_account`) must report all three checks `valid`.
- **Payments profile first.** Play refuses paid products until the user sets up a payments profile (Monetize with Play → Products prompts for it). Symptom on the API side: `pricing:convertRegionPrices` → 403 "The caller does not have permission".
- **Creating the service account** (user runs it, or allows it): reuse the app's Firebase/GCP project.
  ```bash
  gcloud services enable androidpublisher.googleapis.com --project <gcp-project>
  gcloud iam service-accounts create revenuecat-play --project <gcp-project> --display-name "RevenueCat Play access"
  gcloud iam service-accounts keys create ~/.<app>/revenuecat-play-service-account.json --iam-account revenuecat-play@<gcp-project>.iam.gserviceaccount.com
  ```
  Then the user invites that email in Play Console → **Users and permissions** (account level: leave the app via "All apps"; only owners/admins see it) → App permissions → the app → the permissions above → Invite. The user uploads the JSON on the RevenueCat app page (Claude must not paste credentials into forms).

### Play Developer API without fastlane

`play_token.py` (next to this file) mints an access token from the JSON key with openssl only: `T=$(python3 -I play_token.py key.json)`; never echo `$T`. Base URL `https://androidpublisher.googleapis.com/androidpublisher/v3/applications/<pkg>`.
- Read checks that prove access: `GET .../oneTimeProducts` (empty body = no products yet), `GET .../reviews`.
- One-time products use **`oneTimeProducts`**; the old `inappproducts` returns 403 "Please migrate to the new publishing API". Create = `PATCH .../onetimeproducts/<id>?allowMissing=true&regionsVersion.version=2022%2F02&updateMask=listings,purchaseOptions` with `purchaseOptions[].buyOption.legacyCompatible: true`. Read the discovery doc (`https://androidpublisher.googleapis.com/$discovery/rest?version=v3`) for field names.
- Listing edits on a **draft** app: `POST .../edits`, `PUT .../listings/<lang>`, image uploads to `/upload/...` all succeed, but `:validate` and `:commit` returned 403 even with Manage store presence granted. Do not wait for propagation; fill the listing in the console (Phase 5). `:commit?changesNotSentForReview=true` → 400 "Changes are sent for review automatically". Uncommitted edits expire on their own.

## Phase 4 — Upload with fastlane (Google Play Developer API)

- `brew install fastlane` (ask first). Run with `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_HIDE_CHANGELOG=1`.
- **Key file:** RevenueCat keeps its service account key server-side and never returns it. Reuse the same service account but have the user create **another JSON key** for it, saved as git-ignored `play-service-account.json`. Grant it in Play Console: Release to testing tracks, Release to production, Manage store presence. Validate with `validate_play_store_json_key` (lane `check_access`).
- Metadata layout: `fastlane/metadata/android/<locale>/{title,short_description,full_description}.txt`, `changelogs/<versionCode>.txt`, `images/{icon.png,featureGraphic.png,phoneScreenshots/1_x.png...}`. Play locale for Vietnamese is `vi`. Translations reuse default-language graphics.
- Lanes that work:
  ```ruby
  lane :internal do   # AAB + listing + notes in ONE edit
    upload_to_play_store(track: "internal", aab: AAB, release_status: "draft")
  end
  lane :production do
    version_code = File.read("../app/build.gradle.kts")[/versionCode = (\d+)/, 1].to_i
    upload_to_play_store(
      track: "internal", version_code: version_code, track_promote_to: "production",
      track_promote_release_status: "draft",   # default "completed" PUBLISHES IMMEDIATELY
      skip_upload_changelogs: true, skip_upload_aab: true, skip_upload_metadata: true,
      skip_upload_images: true, skip_upload_screenshots: true)
  end
  ```
- Traps: a listing-only upload fails with "Could not find release for version code ''" until a release exists — upload the listing together with the first AAB. Without `version_code`, promote may pick an **older** build still on the track. Verify after every promote with `fastlane run google_play_track_version_codes track:production ...`.

## Phase 5 — Play Console "Set up your app" (browser)

Only the user can sign in. Use the built-in browser; set a 1280×1000 viewport if the pane is small. Do the forms in this **dependency order**:

1. **Privacy policy** URL (curl it first: must return 200).
2. **Sign in details (App access)** — answer **Yes** whenever *any* content is paid; Google's reviewers cannot buy. Give access with a **Play promo code**:
   - Monetize with Play → Promo codes → accept the Promo codes ToS (ask) → One-time product → pick the lifetime purchase option → 1 code → start time **in the future** (a past time fails with "Start and end dates must be in the future") → Create.
   - The code is only in **Download codes** (CSV). The built-in browser cannot download; ask the user to click it, then read `~/Downloads/promotion_codes.csv`.
   - Instructions (English, ≤500 chars): free features, path to the paywall, "choose Redeem code on the Google Play purchase sheet and enter <code>", expiry date.
   - Check "details give full access including paid content". **Turn OFF** "allow Google to use these sign-in details for testing on partner devices" — it can burn a single-use code.
3. **Ads** declaration.
4. **Content rating** (IARC; accept terms only with approval). Answer "online content not in the download" = **Yes** if the app fetches content packs; this can raise Brazil to 14+. Digital purchases = Yes. Save, then Next, then Save on the summary.
5. **Target audience** (locked until Sign in details is done). 18+ for mature themes; leave the optional "block minors" off unless asked.
6. **Data safety** (cannot be *submitted* until Target audience is saved — "Save as draft" before). List only data that leaves the device (e.g. RevenueCat: Purchase history + Device or other IDs; collected, not shared, required, App functionality, not ephemeral, encrypted in transit, no accounts). Leave the optional "users can request deletion" unanswered unless the user decides.
7. **Government apps**, Financial features, Health.
8. **Advertising ID** declaration — not on the dashboard list but **blocks submission** in quick checks. Answer from the merged manifest (`AD_ID` present or not). Do it up front.
9. **Store settings**: category, contact email/website. **"Save and publish" opens a second confirm dialog** — confirm it or nothing saves; re-check the page after.

10. **Store listing** (Grow users → Store presence; first time: Store listings → **Create default store listing** → `/store-listings/default/edit`).
    - Long text: set values with the native setter + `input` event, then check the "N / 30", "N / 80", "N / 4000" counters (typing 4000 chars is slow).
    - **The built-in browser cannot upload files.** Images the user uploads may land only in the **asset library**, not in the slots. Attach per slot: "Add assets" → library panel → hover the row → → arrow → **Add**. The library is newest-first, so add screenshots oldest-first to keep their order. Verify "1 / 1" (icon), "1 / 1" (feature graphic), "N / 8" (screenshots).
    - **Next → Review** has the **AI asset declaration**: "Don't label assets" or "Label assets as created or edited using AI" → select the AI assets → "Label assets and submit". Ask the user; never guess.
    - Translations: the language dropdown → **Manage languages** → tick (e.g. "Vietnamese – vi") → Apply. The new language opens with empty text; fill it, Save as draft → Next → Save. Graphics fall back to the default language.

Other answers that came up: Financial features → tick "My app doesn't provide any financial features" (Next then Save in step 2). Health → "My app does not have any health features" (for example, a journal with mood emojis is not a health app). Content rating → contact email = the public support address, category "All Other App Types". Data safety with RevenueCat follows RevenueCat's own guide (`https://www.revenuecat.com/docs/platform-resources/google-platform-resources/google-plays-data-safety.md`): Financial info → Purchase history, collected, not shared, not ephemeral, required, purposes App functionality + Analytics; no accounts → "My app does not allow users to create an account" and "login with accounts created outside the app" = No.

Console URL map (`/console/u/0/developers/<devId>/app/<appId>/...`): `app-dashboard`, `app-content/overview` (each "Start declaration" opens `app-content/<privacy-policy|testing-credentials|ads-declaration|ad-id-declaration|government-apps|finance|health|target-audience-content|content-rating-overview|data-privacy-security>`), `store-settings`, `store-listings`, `tracks/production`, `publishing`.

After each save Play asks "Go to Publishing overview?" — choose **Not now** and send everything together at the end.

## Phase 6 — Release and review

0. Production → **Countries / regions** tab → tick the header checkbox (all 177) → Save; Publishing overview then also lists "Add rest of world".
1. Production → Create/Edit release → **Add from library** (pick the internal-test build) → release notes use language tags, one block per listing language (`<en-US>…</en-US>\n<vi>…</vi>`; check "Release notes provided for N of N languages") → Next → read every warning (missing native debug symbols is non-blocking) → Save.
   - Error "Your app cannot be published yet. Complete the steps listed on the Dashboard" → open the dashboard: "Set up your app" shows "N of 11 complete" with the open task. A task can look done but not be saved (contact details behind the second confirm dialog) — re-open its page and read the values.
2. Publishing overview → wait for quick checks, fix issues → **Submit N changes for review** → confirm. Status becomes "Changes in review"; reviews take up to ~7 days.
3. Tell the user whether **Managed publishing** is off (goes live on approval) or on (they press Publish).
4. Later updates: bump `versionCode`/`versionName` → `./gradlew bundleRelease` → `fastlane internal` → test with a license tester → `fastlane production` → user rolls out.

## Browser automation notes (Play Console)

- Prefer `find` refs and read state with small JS snippets (checked radios/checkboxes, input values) instead of trusting a click.
- A sticky footer covers the bottom of the page: `scrollIntoView({block:'center'})` the target first. In a scaled pane, screenshot coordinates = CSS px × device ratio (often 2).
- The first click after a scroll sometimes only focuses a radio; re-check and click again.
- Play's help slideshows (e.g. Data safety) block the form: step through to "Start" or press Escape.
- Labels are often detached from inputs; map each radiogroup to its question text before clicking, and verify the full answer list before saving.
- **Narrow pane:** the final Save of multi-step forms (Financial features step 2, Data safety preview) hides behind a `more_vert` overflow button → open it, pick Save. Viewport emulation via `resize_window` gave blank Play Console screenshots; use the desktop preset instead.
- Click coordinates from a JS rect: `x * frameWidth / innerWidth` (the screenshot frame and CSS pixels often differ, e.g. 800 vs 691).
- JS `.click()` works on Play radio inputs (IARC, Data safety). Material checkboxes often ignore it: click the box at its coordinates, then confirm with the next button's `disabled` state or `input.checked`. Screenshots can lag one step behind the DOM; trust JS state.
