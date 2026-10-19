#!/bin/sh
# Template: copy to <repo>/ci_scripts/ci_post_clone.sh, chmod +x, and set PROJECT below.
# Xcode Cloud runs this after cloning the repo.
#
# For tag builds (tag v1.0.2 -> version 1.0.2), set the app version from the
# tag so a release only needs:  git tag v1.0.2 && git push origin v1.0.2
# Xcode Cloud sets the build number itself.
set -eu

TAG="${CI_TAG:-}"
if [ -z "$TAG" ]; then
  echo "Not a tag build; keeping MARKETING_VERSION from the project."
  exit 0
fi

VERSION="${TAG#refs/tags/}"
VERSION="${VERSION#v}"
if ! echo "$VERSION" | grep -Eq '^[0-9]+(\.[0-9]+){1,2}$'; then
  echo "error: tag '$TAG' is not like v1.2 or v1.2.3" >&2
  exit 1
fi

PROJECT="App.xcodeproj"   # your project file, relative to the repo root
PBXPROJ="${CI_PRIMARY_REPOSITORY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}/$PROJECT/project.pbxproj"
sed -i '' -E "s/MARKETING_VERSION = [^;]+;/MARKETING_VERSION = $VERSION;/g" "$PBXPROJ"
echo "Set MARKETING_VERSION to $VERSION:"
grep -n "MARKETING_VERSION" "$PBXPROJ"
