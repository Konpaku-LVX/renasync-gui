#!/bin/sh
# Build the renasync-gui addon as a standalone zipapp.
#
# This packages only the addon. Renasync itself is NOT bundled: it must be
# installed separately (package manager, upstream zipapp, or pip) and is
# imported at runtime. Requires python 3.10+ with tkinter, plus libmpv.

set -e
cd "$(dirname "$0")"

find src -name '__pycache__' -type d -exec rm -rf {} +

python3 -m zipapp -o renasync-gui -p '/usr/bin/env python3' -m renasync_gui:main -c src
chmod +x renasync-gui

echo "Built ./renasync-gui"