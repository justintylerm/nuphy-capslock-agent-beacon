#!/bin/sh

set -eu

project_dir=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")/.." && pwd)
app_dir="$project_dir/dist/NuPhy CapsLock Agent Beacon.app"
contents_dir="$app_dir/Contents"
executable_dir="$contents_dir/MacOS"
swift_path=$(/usr/bin/xcrun --find swift)

cd "$project_dir"
"$swift_path" build -c release --product nuphy-capslock-agent-beacon

if [ -e "$app_dir" ]; then
    /bin/rm -rf -- "$app_dir"
fi
/bin/mkdir -p "$executable_dir"
/bin/cp "$project_dir/AppBundle/AgentBeacon-Info.plist" "$contents_dir/Info.plist"
/bin/cp "$project_dir/.build/release/nuphy-capslock-agent-beacon" \
    "$executable_dir/nuphy-capslock-agent-beacon"

/usr/bin/codesign --force --sign - \
    --identifier io.github.justintylerm.nuphy-capslock-agent-beacon \
    "$app_dir"

/usr/bin/codesign --verify --strict --verbose=2 "$app_dir"
printf '%s\n' "$app_dir"
