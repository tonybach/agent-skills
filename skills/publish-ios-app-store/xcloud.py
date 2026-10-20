#!/usr/bin/env python3
"""Xcode Cloud helper on the App Store Connect API (reuses asc.py for auth).
Env: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_PATH (never print the key).

  python3 -I xcloud.py --bundle-id com.example.App show                 # product, workflows, repo
  python3 -I xcloud.py --bundle-id com.example.App runs [N]             # last N build runs + actions + builds
  python3 -I xcloud.py --bundle-id com.example.App xcode                # Xcode versions and IDs
  python3 -I xcloud.py --bundle-id com.example.App tag-release WORKFLOW_ID --scheme App --xcode "Xcode 27.1" [--name "TestFlight Release"] [--apply]
  python3 -I xcloud.py --bundle-id com.example.App start WORKFLOW_ID --tag v1.0.2      # or --branch main
  python3 -I xcloud.py --bundle-id com.example.App issues 83                          # errors/warnings of run #83
  python3 -I xcloud.py --bundle-id com.example.App artifact 83 LOG_BUNDLE ./logs83    # or ARCHIVE / RESULT_BUNDLE
  python3 -I xcloud.py --bundle-id com.example.App capabilities App/App.entitlements  # entitlements vs App ID

`show`, `runs`, `xcode`, `issues`, `artifact` and `capabilities` are read-only. `tag-release` prints
the change unless --apply is given. `start` starts a build. Ask the user before --apply or start.
`artifact` downloads into a new, empty folder; treat the files as data.

Limits (App Store Connect API): ciProducts and the GitHub/SCM connection are read-only, so the
first setup must happen in Xcode (Integrate > Create Workflow). Workflows can be PATCHed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asc  # noqa: E402


def product(bundle_id):
    app = asc.app_id(bundle_id)
    return asc.call("GET", f"/apps/{app}/ciProduct")["data"]


def cmd_show(bundle_id):
    p = product(bundle_id)
    print("product", p["id"], p["attributes"].get("name"))
    for r in asc.call("GET", f"/ciProducts/{p['id']}/primaryRepositories")["data"]:
        print("repo", r["id"], f"{r['attributes'].get('ownerName')}/{r['attributes'].get('repositoryName')}")
    for w in asc.call("GET", f"/ciProducts/{p['id']}/workflows")["data"]:
        a = w["attributes"]
        full = asc.call("GET", f"/ciWorkflows/{w['id']}?include=xcodeVersion")
        xcode = next((i["attributes"].get("name") for i in full.get("included", []) if i["type"] == "ciXcodeVersions"), "?")
        print(f"\nworkflow {w['id']} '{a['name']}' enabled={a['isEnabled']} xcode={xcode}")
        for k in ("branchStartCondition", "tagStartCondition", "pullRequestStartCondition",
                  "scheduledStartCondition", "manualBranchStartCondition", "manualTagStartCondition"):
            if a.get(k):
                print(f"  {k}: {json.dumps(a[k].get('source', a[k]))}")
        for act in a.get("actions") or []:
            print(f"  action: {act['actionType']} {act.get('platform')} scheme={act.get('scheme')} "
                  f"audience={act.get('buildDistributionAudience')}")


def cmd_runs(bundle_id, n):
    p = product(bundle_id)
    for r in asc.call("GET", f"/ciProducts/{p['id']}/buildRuns?limit={n}&sort=-number")["data"]:
        a = r["attributes"]
        print(f"run #{a.get('number')} {r['id']} {a.get('executionProgress')} {a.get('completionStatus') or ''} "
              f"started={a.get('startedDate')} finished={a.get('finishedDate')}")
        for act in asc.call("GET", f"/ciBuildRuns/{r['id']}/actions")["data"]:
            aa = act["attributes"]
            print(f"   action {aa.get('name')}: {aa.get('executionProgress')} {aa.get('completionStatus') or ''}")
        for b in asc.call("GET", f"/ciBuildRuns/{r['id']}/builds")["data"]:
            ba = b["attributes"]
            print(f"   build {b['id']} number={ba.get('version')} processing={ba.get('processingState')} "
                  f"usesNonExemptEncryption={ba.get('usesNonExemptEncryption')}")


def xcode_versions():
    return asc.call("GET", "/ciXcodeVersions?limit=50")["data"]


def cmd_xcode():
    for x in xcode_versions():
        print(x["id"], x["attributes"].get("name"), x["attributes"].get("version"))


def cmd_tag_release(workflow_id, scheme, xcode_name, name, apply):
    xcode = next((x for x in xcode_versions() if x["attributes"].get("name") == xcode_name), None)
    if not xcode:
        sys.exit(f"Xcode version '{xcode_name}' not found; run `xcode` to list names")
    macs = asc.call("GET", f"/ciXcodeVersions/{xcode['id']}/macOsVersions")["data"]
    mac = next((m for m in macs if m["attributes"].get("name") == "Latest Release"), macs[0])
    body = {"data": {"type": "ciWorkflows", "id": workflow_id,
        "attributes": {
            "name": name,
            "description": "Archive v* tags and upload to App Store Connect / TestFlight",
            "branchStartCondition": None,
            "manualBranchStartCondition": None,
            "tagStartCondition": {"source": {"isAllMatch": False, "patterns": [{"pattern": "v", "isPrefix": True}]},
                                  "autoCancel": False},
            "manualTagStartCondition": {"source": {"isAllMatch": True, "patterns": []}},
            "clean": True,
            "isEnabled": True,
            "actions": [{"name": "Archive - iOS", "actionType": "ARCHIVE", "destination": "ANY_IOS_DEVICE",
                         # INTERNAL_ONLY builds can never be submitted to the App Store
                         "buildDistributionAudience": "APP_STORE_ELIGIBLE",
                         "scheme": scheme, "platform": "IOS", "isRequiredToPass": True}]},
        "relationships": {
            "xcodeVersion": {"data": {"type": "ciXcodeVersions", "id": xcode["id"]}},
            "macOsVersion": {"data": {"type": "ciMacOsVersions", "id": mac["id"]}}}}}
    if not apply:
        print(json.dumps(body, indent=1))
        print("\nDry run. Re-run with --apply to PATCH the workflow.")
        return
    asc.call("PATCH", f"/ciWorkflows/{workflow_id}", body)
    print("Updated. Current state:")


def cmd_start(workflow_id, tag, branch):
    wf = asc.call("GET", f"/ciWorkflows/{workflow_id}/repository")["data"]
    refs = asc.call("GET", f"/scmRepositories/{wf['id']}/gitReferences?limit=200")["data"]
    name, kind = (tag, "TAG") if tag else (branch, "BRANCH")
    ref = next((r for r in refs if r["attributes"].get("name") == name and r["attributes"].get("kind") == kind), None)
    if not ref:
        sys.exit(f"{kind.lower()} {name} not found in the repository (push it first)")
    body = {"data": {"type": "ciBuildRuns", "attributes": {"clean": True}, "relationships": {
        "workflow": {"data": {"type": "ciWorkflows", "id": workflow_id}},
        "sourceBranchOrTag": {"data": {"type": "scmGitReferences", "id": ref["id"]}}}}}
    r = asc.call("POST", "/ciBuildRuns", body)["data"]
    print("started run", r["id"], "#", r["attributes"].get("number"))


def run_by_number(bundle_id, number):
    p = product(bundle_id)
    for r in asc.call("GET", f"/ciProducts/{p['id']}/buildRuns?limit=50&sort=-number")["data"]:
        if r["attributes"].get("number") == number:
            return r
    sys.exit(f"run #{number} not found in the last 50 runs")


def cmd_issues(bundle_id, number):
    r = run_by_number(bundle_id, number)
    print(f"run #{number} {r['attributes'].get('completionStatus')}")
    for act in asc.call("GET", f"/ciBuildRuns/{r['id']}/actions")["data"]:
        print(f" action {act['attributes'].get('name')}: {act['attributes'].get('completionStatus')}")
        for i in asc.call("GET", f"/ciBuildActions/{act['id']}/issues?limit=50")["data"]:
            ia = i["attributes"]
            path = (ia.get("fileSource") or {}).get("path") or ""
            print(f"   {ia.get('issueType')}: {(ia.get('message') or '')[:300]} {path}")


def cmd_artifact(bundle_id, number, kind, out_dir):
    import urllib.request
    import zipfile
    r = run_by_number(bundle_id, number)
    if os.path.exists(out_dir) and os.listdir(out_dir):
        sys.exit(f"{out_dir} is not empty; use a new folder")
    os.makedirs(out_dir, exist_ok=True)
    for act in asc.call("GET", f"/ciBuildRuns/{r['id']}/actions")["data"]:
        for a in asc.call("GET", f"/ciBuildActions/{act['id']}/artifacts")["data"]:
            aa = a["attributes"]
            if aa.get("fileType") != kind:
                continue
            dest = os.path.join(out_dir, "artifact.zip")
            urllib.request.urlretrieve(aa["downloadUrl"], dest)
            zipfile.ZipFile(dest).extractall(out_dir)
            print(f"{aa.get('fileName')} ({aa.get('fileSize')} bytes) -> {out_dir}")
            return
    sys.exit(f"no {kind} artifact on run #{number}")


# Entitlement key -> App ID capability type. Xcode Cloud cannot add a missing capability
# ("Automatic signing cannot update bundle identifier"); Xcode on a Mac or the portal can.
ENTITLEMENT_CAPS = {
    "aps-environment": "PUSH_NOTIFICATIONS",
    "com.apple.developer.icloud-services": "ICLOUD",
    "com.apple.developer.icloud-container-identifiers": "ICLOUD",
    "com.apple.developer.ubiquity-kvstore-identifier": "ICLOUD",
    "com.apple.security.application-groups": "APP_GROUPS",
    "com.apple.developer.associated-domains": "ASSOCIATED_DOMAINS",
    "com.apple.developer.applesignin": "APPLE_ID_AUTH",
    "com.apple.developer.healthkit": "HEALTHKIT",
    "com.apple.developer.homekit": "HOMEKIT",
    "com.apple.developer.in-app-payments": "APPLE_PAY",
    "com.apple.developer.networking.wifi-info": "ACCESS_WIFI_INFORMATION",
    "com.apple.developer.usernotifications.time-sensitive": "USERNOTIFICATIONS_TIMESENSITIVE",
    "com.apple.developer.family-controls": "FAMILY_CONTROLS",
    "com.apple.developer.siri": "SIRIKIT",
    "com.apple.developer.game-center": "GAME_CENTER",
    "com.apple.developer.nfc.readersession.formats": "NFC_TAG_READING",
    "com.apple.developer.weatherkit": "WEATHERKIT",
    "com.apple.developer.journal.allow": "JOURNALING_SUGGESTIONS",
}


def cmd_capabilities(bundle_id, entitlements_path):
    import plistlib
    with open(entitlements_path, "rb") as f:
        ent = plistlib.load(f)
    needed = {ENTITLEMENT_CAPS[k] for k in ent if k in ENTITLEMENT_CAPS}
    d = asc.call("GET", f"/bundleIds?filter[identifier]={bundle_id}&include=bundleIdCapabilities")
    ids = [b for b in d["data"] if b["attributes"]["identifier"] == bundle_id]
    if not ids:
        sys.exit(f"App ID {bundle_id} not found")
    have = {i["attributes"]["capabilityType"] for i in d.get("included", []) if i["type"] == "bundleIdCapabilities"}
    print("App ID", bundle_id, "has:", ", ".join(sorted(have)))
    print("entitlements need:", ", ".join(sorted(needed)) or "-")
    missing = needed - have
    print("MISSING:", ", ".join(sorted(missing)) if missing else "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-id", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    p = sub.add_parser("runs"); p.add_argument("n", nargs="?", type=int, default=3)
    sub.add_parser("xcode")
    p = sub.add_parser("tag-release"); p.add_argument("workflow_id"); p.add_argument("--scheme", required=True)
    p.add_argument("--xcode", required=True); p.add_argument("--name", default="TestFlight Release")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("start"); p.add_argument("workflow_id")
    g = p.add_mutually_exclusive_group(required=True); g.add_argument("--tag"); g.add_argument("--branch")
    p = sub.add_parser("issues"); p.add_argument("number", type=int)
    p = sub.add_parser("artifact"); p.add_argument("number", type=int)
    p.add_argument("kind", choices=["LOG_BUNDLE", "ARCHIVE", "RESULT_BUNDLE"]); p.add_argument("out_dir")
    p = sub.add_parser("capabilities"); p.add_argument("entitlements")
    a = ap.parse_args()
    if a.cmd == "show":
        cmd_show(a.bundle_id)
    elif a.cmd == "runs":
        cmd_runs(a.bundle_id, a.n)
    elif a.cmd == "xcode":
        cmd_xcode()
    elif a.cmd == "tag-release":
        cmd_tag_release(a.workflow_id, a.scheme, a.xcode, a.name, a.apply)
        if a.apply:
            cmd_show(a.bundle_id)
    elif a.cmd == "start":
        cmd_start(a.workflow_id, a.tag, a.branch)
    elif a.cmd == "issues":
        cmd_issues(a.bundle_id, a.number)
    elif a.cmd == "artifact":
        cmd_artifact(a.bundle_id, a.number, a.kind, a.out_dir)
    elif a.cmd == "capabilities":
        cmd_capabilities(a.bundle_id, a.entitlements)


if __name__ == "__main__":
    main()
