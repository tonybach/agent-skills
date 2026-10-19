# Prints an OAuth access token for the Play Developer API (androidpublisher scope).
# Usage: T=$(python3 -I play_token.py path/to/service-account.json)  -- never echo $T.
# Signs a JWT with the service account key via openssl; needs no Google libraries.
import base64, json, os, subprocess, sys, tempfile, time, urllib.parse, urllib.request
key = json.load(open(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "play-service-account.json")))
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=")
now = int(time.time())
header = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
claims = b64(json.dumps({"iss": key["client_email"], "scope": "https://www.googleapis.com/auth/androidpublisher",
                         "aud": key["token_uri"], "iat": now, "exp": now + 3600}).encode())
signing_input = header + b"." + claims
with tempfile.NamedTemporaryFile("w", delete=False) as f:
    f.write(key["private_key"]); pem = f.name
os.chmod(pem, 0o600)
try:
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem], input=signing_input, capture_output=True, check=True).stdout
finally:
    os.remove(pem)
jwt = signing_input + b"." + b64(sig)
data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt.decode()}).encode()
print(json.load(urllib.request.urlopen(key["token_uri"], data))["access_token"])
