#!/bin/sh

set -eu
project_dir=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd)
exec /usr/bin/python3 "$project_dir/Scripts/uninstall.py" "$@"
