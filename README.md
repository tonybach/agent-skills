# agent-skills

Reusable skills for coding agents (Claude Code and other tools that read `SKILL.md` files), learned from shipping real apps. Each skill records the steps, traps, and fixes that cost time the first time.

## Skills

| Skill | Use it when |
|-------|-------------|
| [adding-flutter-home-widgets](skills/adding-flutter-home-widgets/SKILL.md) | Adding a home screen widget to a Flutter app on iOS and Android with `home_widget`: a script that adds the WidgetKit extension target from the terminal, the build errors it avoids, values that stay right after midnight, drawing Flutter images for the widget without crashes, Android layout limits, and telling users the widget exists. |
| [build-app-product-page](skills/build-app-product-page/SKILL.md) | Building or updating an app's website on GitHub Pages: product page, privacy policy and terms of use, the URLs in the app and store listings, link previews, structured data and sitemaps, light and dark screenshots, and keeping it all in line with the live release and the SDKs the app ships, plus pre-launch pages and accessibility checks. |
| [flutter-app-dev-loop](skills/flutter-app-dev-loop/SKILL.md) | Building, testing and checking a Flutter app day to day on simulators, emulators and real phones: widget test traps, unreliable simulator taps, a debug screenshot mode, real-iPhone setup, common Flutter bug patterns, Crashlytics and Analytics without the Firebase CLI (with ad IDs off), and removing CocoaPods after Swift Package Manager. |
| [port-ios-app-to-android](skills/port-ios-app-to-android/SKILL.md) | Porting a native SwiftUI app to Android with Kotlin and Jetpack Compose: choosing the stack, parity tests against the Swift logic, matching iOS colors, and the Compose and Android traps (taps through overlays, untestable reminders, cancelled saves, R8 failures). |
| [publish-android-play](skills/publish-android-play/SKILL.md) | Preparing, uploading, or releasing an Android app on Google Play: signing, store assets, Play Console forms, one-time products and subscriptions with RevenueCat, fastlane or the Play Developer API. |
| [publish-ios-app-store](skills/publish-ios-app-store/SKILL.md) | Localizing, uploading, or submitting an iOS app: String Catalogs, App Store Connect API listings and versions, localized App Store screenshots (capture, captioned framing, upload), xcodebuild archive and upload, Xcode Cloud tag builds and failed-run diagnosis (signing, missing App ID capabilities, archive-only workflows), pre-submission App Review checks (third-party AI consent, Sign in with Apple token revoke on account deletion, user-generated content, paywall price), first-release fields (categories, age rating, price, review contact), creating subscriptions and in-app purchases through the API, App Privacy answers, sandbox purchase testing, iPad screenshot sets, review submission including the first in-app purchases and subscriptions. |
| [support-iphone-duo](skills/support-iphone-duo/SKILL.md) | Adapting an iOS app (SwiftUI or Flutter) to iPhone Duo: resizable layouts for every fold pose, the iOS 27.1 vertical toolbar, Xcode 27.1 build fixes, and scripted testing of the app and its widgets in the Duo simulator and Device Hub. |

## Install

### Claude Code (plugin marketplace)

```bash
claude plugin marketplace add tonybach/agent-skills
claude plugin install agent-skills@tonybach-skills
```

Update later with `claude plugin update agent-skills`.

### Copy a single skill

```bash
git clone https://github.com/tonybach/agent-skills.git
cp -R agent-skills/skills/adding-flutter-home-widgets ~/.claude/skills/
cp -R agent-skills/skills/build-app-product-page ~/.claude/skills/
cp -R agent-skills/skills/flutter-app-dev-loop ~/.claude/skills/
cp -R agent-skills/skills/port-ios-app-to-android ~/.claude/skills/
cp -R agent-skills/skills/publish-android-play ~/.claude/skills/
cp -R agent-skills/skills/publish-ios-app-store ~/.claude/skills/
cp -R agent-skills/skills/support-iphone-duo ~/.claude/skills/
```

Other agents that support skills can use `~/.agents/skills/` instead.

### Cloud sessions

Add the marketplace in the cloud environment's setup script, or commit a `.claude/settings.json` to your project:

```json
{
  "extraKnownMarketplaces": {
    "tonybach-skills": { "source": { "source": "github", "repo": "tonybach/agent-skills" } }
  },
  "enabledPlugins": { "agent-skills@tonybach-skills": true }
}
```

## Layout

```
.claude-plugin/   plugin and marketplace manifests
skills/<name>/    SKILL.md plus any helper scripts
```

## Contributing

Issues and pull requests are welcome. A good skill is specific: real error messages, exact commands, and the order that works. Keep secrets, account IDs, and personal paths out of skills.

## License

MIT
