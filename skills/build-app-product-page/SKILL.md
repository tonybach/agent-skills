---
name: build-app-product-page
description: Use when creating or updating a product or marketing web page for an iOS or Android app, its privacy policy or terms of use pages, or the website, support and privacy URLs in its store listings; when refreshing the page's screenshots; or when a page, policy or store listing may no longer match what the shipped app does (new release, new SDK, subscriptions, pricing change, new owner, dark mode, new devices).
---

# Building an app product page

An app's site is usually three static pages: the product page, a privacy policy and terms of use. The stores link to them, the app's Settings links to them, and reviewers read them. Every claim, screenshot, price and URL must match the version people can download today.

**Ground rule:** these pages are public, and the policy is a legal text. Show the user any change to the privacy policy or terms before you push it. Note mismatches you find, even when they are outside the task.

## 1. Site structure and URLs

- One folder per app, served by GitHub Pages from `docs/`: `docs/index.html`, `docs/privacy/index.html`, `docs/terms/index.html`. The folders give clean URLs (`/privacy`, not `privacy.html`).
- A project site lives under `/<Repo>/`, and the path is case sensitive. If the owner's user site has a custom domain, project sites get it too (`<domain>/<Repo>/`); do not add a `CNAME` to the app repo. Root links (`/styles.css`, `/privacy`, a logo with `href="/"`) go to the owner's main site. Use relative links (`href="privacy"`, from a subpage `href="../"`) or the full `/<Repo>/...` path.
- Use one URL scheme everywhere: `<site>/<Repo>/` for the website and support URL, `<site>/<Repo>/privacy/` for the policy, `<site>/<Repo>/terms/` for terms. The app's Settings (a Privacy Policy row, a Terms row when there are subscriptions, a Contact mailto), the paywall (privacy and terms links), the store listings and the pages must use the same strings. The site can stay in one language; localize the store listing.
- Put one contact email on every page (a mailto in the footer) and use the same address in Settings and the store listings.
- Add `docs/sitemap.xml` listing the product, privacy and terms pages by their final URLs (with the trailing slash; `curl -sI` shows the redirect). Set each `<lastmod>` from the file's last commit: `git log -1 --format=%cs -- docs/privacy/index.html`. When you change a page in any way, even only the app name, update its `<lastmod>` in the same commit. Make sure no page has a leftover `noindex` meta tag.
- Search engines read `robots.txt` only at the domain root, so it lives in the owner's main site repo. It lists one `Sitemap:` line per sitemap (the main site's and each app's). Add a line there when you create a new app site. Leave files with personal data (a resume, for example) out of sitemaps. Submitting sitemaps in Google Search Console needs the user's sign-in.

## 2. The product page

- **Hero:** name, one-line promise, the official store badge, one or two screenshots. Use Apple's badge (`https://developer.apple.com/assets/elements/badges/download-on-the-app-store.svg` or a local copy), never a hand-made button. Use the white badge, or `filter: invert(1)`, on a dark theme.
- **Store link:** the numeric app ID exists in App Store Connect (App Information, Apple ID) before launch. Link `https://apps.apple.com/app/id<appId>`; it works once the app is live. Do not guess a slug URL or show a "coming soon" badge. Update every badge on the page, hero and footer. Add a Google Play badge only when the Play listing is live (a 404 on `play.google.com/store/apps/details?id=<pkg>` means it is not).
- **Features:** one card per shipped feature. Keep the card count a multiple of every column count the grid uses (3 and 2 columns: 6 or 12); with fewer real features, change the column count instead of padding. Leave out unreleased features; never write "coming soon".
- **Pricing:** what is free (from the code: limits such as `freeEntryLimit`, `isPremium` gates), what the paid tier unlocks, the plan types, and "The App Store shows the price in your local currency" under a base price. Say "free to start", not "free", when there is a paid tier.
- **Privacy:** say what leaves the device, plainly. "Anonymous crash reports, which never include what you write" is true; "zero telemetry" is not, once a crash reporter ships.
- **Head:** `<title>`, `meta description`, `og:title`, `og:description`, `og:url`, `og:type`, `og:image` (an absolute URL, for example the app icon), `twitter:card` (`summary`), `twitter:title`, `twitter:description`, `twitter:image`. Favicon and `apple-touch-icon` from the app icon, not an emoji, on every page. A `theme-color` per color scheme. A `<link rel="canonical">` to the page's own URL.
- **Structured data:** a `<script type="application/ld+json">` block with `"@type": "MobileApplication"`: `name` (the store name), `description` (the same text as the meta description), `url`, `image` (the icon, absolute), `installUrl` (the store link), `operatingSystem` (from the lookup's `minimumOsVersion`), `applicationCategory` (a schema value such as `LifestyleApplication`, from the store genre) and `offers` (`price` and `priceCurrency` from the lookup). Leave out `aggregateRating` unless something keeps it current; star ratings in search need it, but a stale count is wrong. Update the block when the store name, category or price changes.

**Layout traps:**
- Do not fit the hero to the viewport with `overflow: hidden` or `max-height: 70vh`; it crops on phones. Use `min-height: 100vh; min-height: 100dvh` and let the page scroll.
- Screenshots: `max-width` instead of a fixed `width`, `height: auto`, `object-fit: contain`, and `width`/`height` attributes on the `<img>`.
- Support `prefers-reduced-motion` if the page animates.

## 3. Legal pages

- Style them like the product page (same fonts and colors), with a link back to it and the same footer and favicon.
- Name the legal owner the same way in the policy ("owned and operated by ..."), the terms, the page copyright, the app's copyright string and the store listing. Change all of them together.
- Update "Last updated" on every edit, and check the year.
- **Privacy policy:** one section per service that receives data (purchases, crash reports, sync, content downloads): what it sends, why, and how long it is kept. Recheck it whenever the app adds or removes an SDK.
- **Terms of use:** apps with auto-renewing subscriptions must link to terms of use from the paywall, Settings and the listing (App Store Guideline 3.1.2). Apple's standard license agreement (EULA) is enough; a custom page is a choice. Free and one-time paid apps can rely on Apple's standard EULA. A custom page should cover billing at confirmation, auto-renewal unless cancelled 24 hours before the period ends, the renewal charge window, how to cancel on each platform, upgrades and downgrades, refunds through the store, and lifetime purchases and restore.

## 4. Keep everything consistent

These must say the same thing: the product page, the privacy policy, the store description, the App Store privacy label, the app's privacy manifest (`PrivacyInfo.xcprivacy`) and the Google Play data safety form.

- Find the truth first. Live version, description, price and languages: `curl "https://itunes.apple.com/lookup?id=<appId>&country=us"`. Shipped features: commits up to the live version's tag; a version in review is not live yet. Data that leaves the device: the app's entry point and package list. Who owns an open release: the repo's release notes file (for example `RELEASE.md`).
- The store **description** belongs to a version and can change only while a version is editable. If it is in review, or another session owns the release, update the repo's listing files for the next version and tell the user.
- The App Store **privacy label** has no public API. Ask the user to sign in to App Store Connect and check it with you. On Play, a purchase processor is a service provider: "collected", not "shared". Declare crash logs once a crash reporter ships.
- Every store locale needs its own `privacyPolicyUrl` (App Info) and `supportUrl` and `marketingUrl` (version localization). When you add a locale, set all three and read the listing back; a missing one blocks review. Play needs a website, a contact email and a privacy policy URL; check that the form fields saved.

## 5. Screenshots

- Capture from a current build of the released code with Debug-only sample data, opened by launch arguments where the app has them, so the run needs no taps and can be repeated. Set a clean status bar: `xcrun simctl status_bar <udid> override --time "9:41" --batteryState charged --batteryLevel 100`.
- If the page has dark styles (`prefers-color-scheme`), capture every screenshot in light and dark from the same data (`xcrun simctl ui <udid> appearance dark`) and serve them with `<picture><source srcset="x-dark.png" media="(prefers-color-scheme: dark)"><img src="x.png" alt="..."></picture>`. Replace the light image too, so both show the same data. Check that the dark file really differs (compare hashes).
- Use a simulator only you use. If the project's screenshot simulator is booted, another session may need it: create a temporary one and delete it afterwards.
- App Group settings need `xcrun simctl spawn <udid> defaults write <group container>/Library/Preferences/<group id> key -bool YES`; launch arguments do not reach them. Take proof screenshots with `xcrun simctl io <udid> screenshot`; a simulator panel's screenshot can be stale.
- Keep the old pixel size so the layout does not move. Simple UI compresses well as a 256-color PNG (Pillow `quantize(256, dither=NONE)`); compare a crop first. Delete images the page no longer uses.
- Store screenshots can share the pipeline: capture at the largest required size (iPhone 6.9": 1320 x 2868), frame them with a script that keeps captions per locale, check line breaks in every localized language, and dry-run uploads. For foldables, follow the `support-iphone-duo` skill.

## 6. Verify before you push

- Serve the folder under the same path prefix (`/<Repo>/`) on a local server, and follow every link: badges, legal pages, logo, mailto.
- Parse the JSON-LD with `json.loads` (or `JSON.parse` in the page) and the sitemap as XML.
- Emulate light and dark. For each image, check `img.currentSrc` and `naturalWidth` with script, not only by eye; scroll-reveal animations make page screenshots look blank.
- Check a 375 px width for horizontal scroll and cropping.
- Work in a git worktree, change the page, policy and listing files in the same commit, rebase on the default branch, then push.
- After GitHub Pages deploys, run `curl -sI` on every URL and expect `200` over HTTPS before you enter new URLs in App Store Connect or Play Console.

## Common mistakes

| Mistake | Fix |
|---|---|
| Root-relative links on a project site | Relative links or `/<Repo>/` |
| Copy describes `main`, not the live version | Compare with the store lookup |
| SDK added, policy and page not updated | Recheck data flows every release |
| Store text changed on a version in review | Change the listing files; apply to the next version |
| New store locale without a privacy URL | Set all three URLs per locale, read back |
| Light screenshot on the dark theme, or a "dark" copy of the light file | Pairs from the same data; compare hashes |
| Hero locked to the viewport | `min-height`, let it scroll |
| Page changed, sitemap `<lastmod>` not | Update it in the same commit |
| `robots.txt` added to an app repo | It only works at the domain root |
| Shared simulator reseeded or switched to dark | Temporary simulator |
