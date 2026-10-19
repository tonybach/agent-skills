#!/usr/bin/env python3
"""App Store Connect API helper. No dependencies: signs the ES256 JWT with openssl.

Env: ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_PATH (path to AuthKey_XXX.p8; never print it).

  python3 asc.py --bundle-id com.example.App status
  python3 asc.py --bundle-id com.example.App builds
  python3 asc.py --bundle-id com.example.App create-version 1.0.1
  python3 asc.py --bundle-id com.example.App apply metadata/vi.json [--dry-run]
  python3 asc.py --bundle-id com.example.App submit 1.0.1 1 [--no-encryption]

Only `status` and `builds` are read-only. Ask the user before the others.
Metadata JSON: {"locale": "vi", "name", "subtitle", "privacyPolicyUrl",
                "description", "keywords", "promotionalText", "whatsNew", "supportUrl", "marketingUrl"}
(any subset; empty values are skipped).
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.appstoreconnect.apple.com/v1"
EDITABLE_VERSION_STATES = {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED",
                           "METADATA_REJECTED", "INVALID_BINARY"}
LIVE_STATES = {"READY_FOR_DISTRIBUTION", "READY_FOR_SALE", "ACCEPTED"}
APP_INFO_FIELDS = ("name", "subtitle", "privacyPolicyUrl")
VERSION_FIELDS = ("description", "keywords", "promotionalText", "whatsNew", "supportUrl", "marketingUrl")


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def der_to_raw(sig):
    """Convert an openssl DER ECDSA signature to the 64-byte r||s form JWT needs."""
    assert sig[0] == 0x30
    i = 3 if sig[1] & 0x80 else 2
    out = b""
    for _ in range(2):
        assert sig[i] == 0x02
        n = sig[i + 1]
        out += sig[i + 2:i + 2 + n].lstrip(b"\x00").rjust(32, b"\x00")
        i += 2 + n
    return out


def token():
    now = int(time.time())
    header = b64(json.dumps({"alg": "ES256", "kid": os.environ["ASC_KEY_ID"], "typ": "JWT"}).encode())
    claims = b64(json.dumps({"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 15 * 60,
                             "aud": "appstoreconnect-v1"}).encode())
    signing_input = header + b"." + claims
    key = os.path.expanduser(os.environ["ASC_KEY_PATH"])
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key], input=signing_input,
                         capture_output=True, check=True).stdout
    return (signing_input + b"." + b64(der_to_raw(sig))).decode()


def call(method, path, body=None):
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        if "REQUIRED_AGREEMENTS_MISSING_OR_EXPIRED" in detail:
            sys.exit("403: the Account Holder must accept the new agreement in App Store Connect > Business.")
        sys.exit(f"{method} {url} -> {e.code}\n{detail}")


def app_id(bundle_id):
    data = call("GET", f"/apps?filter[bundleId]={bundle_id}")["data"]
    if not data:
        sys.exit(f"No app with bundle id {bundle_id}")
    return data[0]["id"]


def versions(app):
    return call("GET", f"/apps/{app}/appStoreVersions?filter[platform]=IOS&limit=20")["data"]


def editable_version(app):
    return next((v for v in versions(app) if v["attributes"]["appStoreState"] in EDITABLE_VERSION_STATES), None)


def editable_app_info(app):
    infos = call("GET", f"/apps/{app}/appInfos")["data"]
    return next((i for i in infos if i["attributes"].get("appStoreState") not in LIVE_STATES), None)


def builds(app, limit=10):
    r = call("GET", f"/builds?filter[app]={app}&sort=-uploadedDate&limit={limit}&include=preReleaseVersion")
    pre = {i["id"]: i["attributes"]["version"] for i in r.get("included", [])}
    out = []
    for b in r["data"]:
        a = b["attributes"]
        pv = b["relationships"]["preReleaseVersion"]["data"]
        out.append({"id": b["id"], "marketing": pre.get(pv["id"]) if pv else None, "build": a["version"],
                    "state": a["processingState"], "uploaded": a["uploadedDate"],
                    "encryption": a.get("usesNonExemptEncryption")})
    return out


def cmd_status(app):
    for info in call("GET", f"/apps/{app}/appInfos")["data"]:
        print(f"\nAppInfo {info['id']} state={info['attributes'].get('appStoreState')}")
        for loc in call("GET", f"/appInfos/{info['id']}/appInfoLocalizations")["data"]:
            a = loc["attributes"]
            print(f"  [{a['locale']}] " + json.dumps({k: a.get(k) for k in APP_INFO_FIELDS}, ensure_ascii=False))
    for v in versions(app):
        a = v["attributes"]
        print(f"\nVersion {a['versionString']} id={v['id']} state={a['appStoreState']} release={a.get('releaseType')}")
        for loc in call("GET", f"/appStoreVersions/{v['id']}/appStoreVersionLocalizations")["data"]:
            la = loc["attributes"]
            short = {k: (la.get(k)[:80] + "…" if k == "description" and la.get(k) else la.get(k)) for k in VERSION_FIELDS}
            print(f"  [{la['locale']}] " + json.dumps(short, ensure_ascii=False, indent=2))


def cmd_builds(app):
    for b in builds(app):
        print(f"{b['id']} {b['marketing']} ({b['build']}) {b['state']} {b['uploaded']} "
              f"usesNonExemptEncryption={b['encryption']}")


def cmd_create_version(app, version_string):
    existing = editable_version(app)
    if existing:
        sys.exit(f"Editable version already exists: {existing['attributes']['versionString']}")
    v = call("POST", "/appStoreVersions", {"data": {
        "type": "appStoreVersions", "attributes": {"platform": "IOS", "versionString": version_string},
        "relationships": {"app": {"data": {"type": "apps", "id": app}}}}})["data"]
    print(f"Created version {version_string}: {v['id']} state={v['attributes']['appStoreState']}")


def upsert(list_path, kind, parent_rel, parent_type, parent_id, locale, attrs, dry_run):
    existing = [l for l in call("GET", list_path)["data"] if l["attributes"]["locale"] == locale]
    if dry_run:
        print(f"[dry-run] {'update' if existing else 'create'} {kind} {locale}: "
              + json.dumps(attrs, ensure_ascii=False, indent=2))
    elif existing:
        call("PATCH", f"/{kind}/{existing[0]['id']}", {"data": {"type": kind, "id": existing[0]["id"], "attributes": attrs}})
        print(f"Updated {kind} {locale}")
    else:
        call("POST", f"/{kind}", {"data": {"type": kind, "attributes": {"locale": locale, **attrs},
              "relationships": {parent_rel: {"data": {"type": parent_type, "id": parent_id}}}}})
        print(f"Created {kind} {locale}")


def cmd_apply(app, path, dry_run):
    meta = json.load(open(path))
    locale = meta["locale"]
    limits = {"name": 30, "subtitle": 30, "keywords": 100, "promotionalText": 170, "description": 4000, "whatsNew": 4000}
    too_long = [f"{k} {len(meta[k])}/{n}" for k, n in limits.items() if meta.get(k) and len(meta[k]) > n]
    if too_long:
        sys.exit("Too long: " + ", ".join(too_long))
    info_attrs = {k: meta[k] for k in APP_INFO_FIELDS if meta.get(k)}
    if info_attrs:
        info = editable_app_info(app)
        if info is None:
            print("No editable AppInfo: name/subtitle change only with a new version. Skipping them.")
        else:
            upsert(f"/appInfos/{info['id']}/appInfoLocalizations", "appInfoLocalizations",
                   "appInfo", "appInfos", info["id"], locale, info_attrs, dry_run)
    version_attrs = {k: meta[k] for k in VERSION_FIELDS if meta.get(k)}
    if version_attrs:
        version = editable_version(app)
        if version is None:
            sys.exit("No editable App Store version. Run create-version first.")
        print(f"Using version {version['attributes']['versionString']} ({version['id']})")
        upsert(f"/appStoreVersions/{version['id']}/appStoreVersionLocalizations", "appStoreVersionLocalizations",
               "appStoreVersion", "appStoreVersions", version["id"], locale, version_attrs, dry_run)


def cmd_submit(app, version_string, build_number, no_encryption):
    version = editable_version(app)
    if not version or version["attributes"]["versionString"] != version_string:
        sys.exit(f"No editable version {version_string}")
    build = next((b for b in builds(app, 20)
                  if b["marketing"] == version_string and b["build"] == build_number), None)
    if build is None:
        sys.exit(f"Build {version_string} ({build_number}) not found. Upload it first.")
    if build["state"] != "VALID":
        sys.exit(f"Build is {build['state']}; wait until it is VALID.")
    if build["encryption"] is None:
        if not no_encryption:
            sys.exit("Export compliance unanswered. Re-run with --no-encryption if the app uses only "
                     "HTTPS/Apple crypto, or answer it in App Store Connect.")
        call("PATCH", f"/builds/{build['id']}", {"data": {"type": "builds", "id": build["id"],
             "attributes": {"usesNonExemptEncryption": False}}})
        print("Export compliance: usesNonExemptEncryption=false")
    call("PATCH", f"/appStoreVersions/{version['id']}/relationships/build",
         {"data": {"type": "builds", "id": build["id"]}})
    print(f"Attached build {version_string} ({build_number})")
    sub = call("POST", "/reviewSubmissions", {"data": {"type": "reviewSubmissions", "attributes": {"platform": "IOS"},
               "relationships": {"app": {"data": {"type": "apps", "id": app}}}}})["data"]
    call("POST", "/reviewSubmissionItems", {"data": {"type": "reviewSubmissionItems", "relationships": {
        "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": sub["id"]}},
        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version["id"]}}}}})
    call("PATCH", f"/reviewSubmissions/{sub['id']}", {"data": {"type": "reviewSubmissions", "id": sub["id"],
         "attributes": {"submitted": True}}})
    v = call("GET", f"/appStoreVersions/{version['id']}")["data"]["attributes"]
    print(f"Submitted: version {version_string} is {v['appStoreState']}, releaseType={v.get('releaseType')}")


def main():
    args = sys.argv[1:]
    bundle_id = os.environ.get("ASC_BUNDLE_ID")
    if "--bundle-id" in args:
        i = args.index("--bundle-id")
        bundle_id = args[i + 1]
        del args[i:i + 2]
    flags = {a for a in args if a.startswith("--")}
    args = [a for a in args if not a.startswith("--")]
    if not args or not bundle_id:
        sys.exit(__doc__)
    app = app_id(bundle_id)
    cmd = args[0]
    if cmd == "status":
        cmd_status(app)
    elif cmd == "builds":
        cmd_builds(app)
    elif cmd == "create-version" and len(args) == 2:
        cmd_create_version(app, args[1])
    elif cmd == "apply" and len(args) == 2:
        cmd_apply(app, args[1], "--dry-run" in flags)
    elif cmd == "submit" and len(args) == 3:
        cmd_submit(app, args[1], args[2], "--no-encryption" in flags)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
