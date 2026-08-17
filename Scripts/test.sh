#!/bin/sh

set -eu
project_dir=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd)
swift_path=$(/usr/bin/xcrun --find swift)

cd "$project_dir"
/usr/bin/python3 -m compileall -q Hooks Scripts Tests
/usr/bin/python3 -m unittest discover -s Tests -v
"$swift_path" build --scratch-path "${TMPDIR:-/tmp}/nuphy-agent-beacon-swift-build" \
    --product nuphy-capslock-agent-beacon
/usr/bin/plutil -lint AppBundle/AgentBeacon-Info.plist
