# agent-skills

Reusable skills for coding agents (Claude Code and other tools that read `SKILL.md` files), learned from shipping real apps. Each skill records the steps, traps, and fixes that cost time the first time.

## Skills

| Skill | Use it when |
|-------|-------------|
| [publish-android-play](skills/publish-android-play/SKILL.md) | Preparing, uploading, or releasing an Android app on Google Play: signing, store assets, Play Console forms, one-time products and subscriptions with RevenueCat, fastlane or the Play Developer API. |
| [publish-ios-app-store](skills/publish-ios-app-store/SKILL.md) | Localizing, uploading, or submitting an iOS app: String Catalogs, App Store Connect API listings and versions, localized App Store screenshots (capture, captioned framing, upload), xcodebuild archive and upload, Xcode Cloud tag builds and failed-run diagnosis (signing, missing App ID capabilities, archive-only workflows), review submission. |
| [support-iphone-duo](skills/support-iphone-duo/SKILL.md) | Adapting an iOS app to iPhone Duo: resizable layouts for every fold pose, the iOS 27.1 vertical toolbar, Xcode 27.1 build fixes, and scripted testing of the app and its widgets in the Duo simulator and Device Hub. |

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
