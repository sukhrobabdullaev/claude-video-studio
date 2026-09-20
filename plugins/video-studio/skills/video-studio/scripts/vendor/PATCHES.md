# Local changes to the vendored video-use helpers

These files come from https://github.com/browser-use/video-use (MIT). They are kept as
close to upstream as possible so they can be re-synced; every deliberate difference is
listed here.

## render.py — concat list uses forward slashes

`concat_segments()` wrote each segment as `file '<absolute path>'`. Inside the concat
demuxer's `file` directive a backslash is an escape character, so on Windows every
path was mangled and ffmpeg failed with "No such file or directory". Found by the
Windows job of this repository's selftest workflow.

The paths are now written with forward slashes, which ffmpeg accepts on every
platform, so the change is a no-op on macOS and Linux.
