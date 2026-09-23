# FreeBSD port for renasync-gui

A FreeBSD port that installs `renasync-gui` (the GUI addon) so it can be launched
from dmenu. Modeled after your `renasync-freebsd` port; it installs the same way
(pep517 build, autoplist) and adds the runtime deps the GUI needs on top:
`renasync` (imported at runtime) and python tkinter.

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

2. Get the source tarball. Either:

   a. **Offline (repo not published yet)** — create the distfile from this repo and
      drop it in the distfiles dir (named exactly as `DISTFILES`):

      ```
      git archive --format=tar.gz --prefix=renasync-gui/ -o /usr/ports/distfiles/0.0.1.tar.gz HEAD
      ```

      (`make` skips fetching when the distfile already exists, so no network is needed.)

   b. **On-line** — publish the repo (e.g. on Codeberg), tag `v0.0.1`, then update
      `MASTER_SITES`, `WWW` and `DISTFILES`/`DISTVERSION` in the Makefile to your
      account and tag, and let `makesum` fetch it.

3. Update `MAINTAINER` and the `<your-account>` placeholders in the Makefile and
   pkg-descr.

4. Generate real checksums, then build and install:

   ```
   cd /usr/ports/multimedia/renasync-gui
   make makesum
   su    # or run the rest as root
   make install
   ```

   `make install` also pulls and builds `multimedia/renasync`, `py-tkinter`, mpv, etc.

5. Launch from dmenu:

   ```
   renasync-gui
   ```

The console script installed as `/usr/local/bin/renasync-gui` comes from the pyproject
`[project.scripts]` entry point, exactly like `renasync`'s own entry point.