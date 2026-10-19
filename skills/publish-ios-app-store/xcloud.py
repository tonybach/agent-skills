#!/usr/bin/env python3
"""Xcode Cloud helper on the App Store Connect API (reuses asc.py for auth).
Env: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_PATH (never print the key).

  python3 xcloud.py --bundle-id com.example.App show                 # product, workflows, repo
  python3 xcloud.py --bundle-id com.example.App runs [N]             # last N build runs + actions + builds
  python3 xcloud.py --bundle-id com.example.App xcode                # Xcode versions and IDs
  python3 xcloud.py --bundle-id com.example.App tag-release WORKFLOW_ID --scheme App --xcode "Xcode 27.1" [--name "TestFlight Release"] [--apply]
  python3 xcloud.py --bundle-id com.example.App start WORKFLOW_ID --tag v1.0.2

`show`, `runs` and `xcode` are read-only. `tag-release` prints the change unless --apply is given.
`start` starts a build. Ask the user before --apply or start.

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


def cmd_start(workflow_id, tag):
    wf = asc.call("GET", f"/ciWorkflows/{workflow_id}/repository")["data"]
    refs = asc.call("GET", f"/scmRepositories/{wf['id']}/gitReferences?limit=200")["data"]
    ref = next((r for r in refs if r["attributes"].get("name") == tag and r["attributes"].get("kind") == "TAG"), None)
    if not ref:
        sys.exit(f"tag {tag} not found in the repository (push it first)")
    body = {"data": {"type": "ciBuildRuns", "relationships": {
        "workflow": {"data": {"type": "ciWorkflows", "id": workflow_id}},
        "sourceBranchOrTag": {"data": {"type": "scmGitReferences", "id": ref["id"]}}}}}
    r = asc.call("POST", "/ciBuildRuns", body)["data"]
    print("started run", r["id"], "#", r["attributes"].get("number"))


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
    p = sub.add_parser("start"); p.add_argument("workflow_id"); p.add_argument("--tag", required=True)
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
        cmd_start(a.workflow_id, a.tag)


if __name__ == "__main__":
    main()
