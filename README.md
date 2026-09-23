# renasync-gui

A lightweight GUI addon for [Renasync](https://codeberg.org/xordev/renasync). It keeps the
terminal hidden while you chat and watch: a small dialog picks a server, room and name
(saved connections are remembered), then the room window opens with the chat, the online
users and a shared playlist. mpv still opens in its own window as usual.

This addon does **not** bundle renasync itself. Renasync is installed separately (package
manager, upstream zipapp, or pip) and is imported at runtime.

## Requirements

* python 3.10 or higher, with tkinter
* libmpv (client)
* renasync, installed separately so `import renasync` works

## Installation (Linux)

From inside this repository:

```
pip install .
```

Which provides a `renasync-gui` command. Alternatively, run it without installing:

```
python3 -m renasync_gui
```

### Building the zipapp

To build a single-file executable (run `./renasync-gui`):

```
./build-linux.sh
```

This produces `./renasync-gui` in the repository root. Since renasync is a separate
install, the addon zipapp stays small.

## Getting Started

Run the GUI:

```
renasync-gui
```

Enter a server, room and name, then join. The GUI shows the chat and the online users; the
player opens as usual in its own window. Use `Load file...` to play a local file or URL.

The playlist (bottom right) is shared with the room:

* `Add URLs...` — paste one or more URLs and add them to the queue
* `Del` / `Clear` — remove the selected entry or the whole queue
* double-click an entry to play it
* `Auto next` — advance the queue when media ends

The config file (saved connections) lives at `~/.config/renasync/config.json` on Linux or
`%APPDATA%\renasync\config.json` on Windows.

## Windows

Build a standalone `renasync-gui.exe` plus a `Renasync-Setup-<version>.exe` installer
(adds Start Menu and desktop shortcuts) with `build-windows.ps1` on a Windows machine with
Python installed:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-windows.ps1
```

The script fetches the libmpv runtime dll (`mpv-2.dll`) automatically, installs
PyInstaller and Inno Setup (via winget/choco) when missing, and names the installer after
the nearest git tag (defaults to `0.0.1` when not in a git checkout). It pulls renasync
from Codeberg and bundles it with the addon into the exe, so the result is
self-contained. Pass `-NoInstaller` to build just the exe.

Tag a release with `v*` and push it to your hosting forge to build and attach both files
automatically (see `.github/workflows/windows.yml`).

## License

0BSD