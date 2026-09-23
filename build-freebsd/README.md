# FreeBSD port for renasync-gui

A FreeBSD port that installs `renasync-gui` (the GUI addon) so it can be launched
from dmenu. Modeled after your `renasync-freebsd` port; it installs the same way
(pep517 build, autoplist) and adds the runtime deps the GUI needs on top:
`renasync` (imported at runtime) and python tkinter. The distfile comes from
GitHub (`USE_GITHUB`), the tarball is fetched with `MASTER_SITES=GH`.

The port lives in `renasync-gui/`. `distinfo` currently holds placeholder
checksums — generate the real ones on your FreeBSD box before building.

## On your FreeBSD box

1. Copy the port into your ports overlay so it keeps its category
   (`multimedia`, matching the reference):

   ```
   mkdir -p /usr/ports/multimedia/renasync-gui
   cp renasync-gui/Makefile renasync-gui/pkg-descr renasync-gui/distinfo /usr/ports/multimedia/renasync-gui/
   ```

   The `renasync` port (multimedia/renasync) is pulled in via `RUN_DEPENDS`;
   make sure it is also available in your overlay/installed.

2. Publish the repo and tag `v0.0.1` on GitHub first (the port fetches
   tag `GH_TAGNAME=v0.0.1`, `<GH_ACCOUNT>-<GH_PROJECT>-<GH_TAGNAME>` ->
   `Konpaku-LVX-renasync-gui-v0.0.1`).

3. Generate real checksums, then build and install:

   ```
   cd /usr/ports/multimedia/renasync-gui
   make makesum      # downloads the tarball from GitHub and writes distinfo
   su                # or run the rest as root
   make install
   ```

   `make install` also pulls and builds `multimedia/renasync`, `py-tkinter`, mpv, etc.

4. Launch from dmenu:

   ```
   renasync-gui
   ```

## Offline alternative

If you want to avoid the network at `makesum` time, download GitHub's own
tarball into the distfiles dir under the exact name `make` expects, then run
`make makesum` (it skips fetching when the distfile already exists):

```
curl -L -o /usr/ports/distfiles/Konpaku-LVX-renasync-gui-0.0.1-v0.0.1_GH0.tar.gz \
  https://codeload.github.com/Konpaku-LVX/renasync-gui/tar.gz/refs/tags/v0.0.1
cd /usr/ports/multimedia/renasync-gui
make makesum
```

Do **not** hand-craft that tarball with `git archive`: the distfile must be
byte-identical to GitHub's codeload output, whose checksums are what the
`GH0` distname pins down.

## Notes

- `MAINTAINER` is set to the GitHub account handle; switch it to a real
  address before submitting this port anywhere.
- The console script installed as `/usr/local/bin/renasync-gui` comes from the
  pyproject `[project.scripts]` entry point, exactly like `renasync`'s own.