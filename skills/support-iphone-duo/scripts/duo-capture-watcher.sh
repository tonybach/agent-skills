#!/bin/zsh
# Captures both iPhone Duo displays whenever a UI test asks for it.
#
# XCUIScreen screenshots come back black on the Duo simulator, so the test
# writes <id>.ready into DIR and waits; this script captures both displays
# with simctl, saves <id>-outer.png and <id>-inner.png, then writes <id>.done.
#
# Usage: duo-capture-watcher.sh <device-udid> <dir>   (run in the background)
D=$1
DIR=$2
mkdir -p $DIR

# Display UUIDs change between launches and after display power changes,
# so look them up by native pixel width every time.
#   outer display: 1398 x 2034 px    inner display: 2007 x 2853 px
uuid_for_width() {
  xcrun simctl io $D enumerate 2>/dev/null |
    awk -v w="$1" '/UUID:/{u=$2} /Default width:/{if ($3==w) {print u; exit}}'
}

capture() { # $1 display uuid, $2 output file. simctl can hang, so time out after 8 s.
  perl -e 'alarm 8; exec @ARGV' xcrun simctl io $D screenshot --display=$1 $2 >/dev/null 2>&1
}

while true; do
  for r in $DIR/*.ready(N); do
    id=${r:t:r}
    capture "$(uuid_for_width 1398)" $DIR/$id-outer.png
    capture "$(uuid_for_width 2007)" $DIR/$id-inner.png
    rm -f $r
    touch $DIR/$id.done
  done
  sleep 0.2
done
