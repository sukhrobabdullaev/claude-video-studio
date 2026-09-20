# Environment traps

Every entry here cost a real debugging session. They share a shape: the command exits 0, the output looks plausible, and the damage only shows up on screen or in the numbers.

## ffmpeg has no `subtitles` filter

Current Homebrew ffmpeg ships without libass, so `subtitles`, `drawtext` and `ass` do not exist and `render.py --build-subtitles` fails with a confusing parse error. Check:

```bash
ffmpeg -hide_banner -filters | grep -E ' subtitles | drawtext '
```

Nothing to fix — `captions.py` rasterizes captions with PIL and composites them as a normal overlay. Do not send the user off to rebuild ffmpeg, and never download a third-party ffmpeg binary to work around it.

## WebM alpha silently becomes an opaque black box

ffmpeg's native VP9 decoder cannot see WebM's alpha plane, and `ffprobe` reports `yuv420p` even when the alpha is really there. Composite it and a black rectangle covers the whole frame — no error.

Convert every overlay to ProRes 4444 (`to_prores.sh`) and verify over solid red. If you must read a WebM's alpha directly, force the decoder: `ffmpeg -c:v libvpx-vp9 -i in.webm ...`.

## iPhone clips have two audio tracks

The second track is 4-channel spatial audio, and ffmpeg's default stream selection prefers it because it has more channels — so a default transcription hears the room, not the speaker. Always pass `--audio-track 0` unless `ffprobe` shows the mic is elsewhere.

## Rotation

Phone video is often stored 1920×1080 with `rotation=-90` and displays as 1080×1920. Read rotation from `stream_side_data` and swap the dimensions before computing any crop, overlay position or rect.

## The output timeline drifts

Each extracted segment's duration rounds to whole frames, so after ~15 cuts the timeline sits ~0.2s later than the EDL says. Graphics timed on nominal EDL math land late, and captions drift out of sync near the end.

Run `offsets.py` after a base render and map every source time through the measured offsets:

```
output_time = source_time − range.src_start + measured.out_start
```

## Paths inside the EDL

`render.py` resolves `overlays[].file` and `subtitles` relative to the **edit directory**. Writing `edit/animations/x.mov` produces `edit/edit/animations/x.mov` and a failed render. Write `animations/x.mov`.

## Stale clips in the clips directory

Re-rendering an EDL whose ranges changed leaves clips from the previous run under different names, so a naive `glob("seg_*.mp4")` picks up too many. `offsets.py` takes the newest N by modification time and orders them by index — keep that behaviour if you rewrite it.

## Caption tracks built with the concat demuxer drift

Each concat entry's duration quantizes to a frame, and the error accumulates — 0.2s over 150 entries, worse once gaps are bridged. Emit every frame explicitly instead (`captions.py` does). Expect drift ≤ 1 frame and check the number it prints.

## Loudness changes when you encode

A mix mastered to −1.5 dBTP as WAV measures around −1.0 dBTP after AAC. Aim the master lower and verify on the final MP4, which is what the platform actually receives.

## Thumbnails lie about legibility

A 10-frame filmstrip makes readable screen recordings look like mush. Before deciding that footage is unusable, unreadable or badly framed, extract a full-resolution frame and look at that.


## `overlay=...:eof_action=pass` silently drops a still overlay

A single-frame PNG ends after frame 1. With `eof_action=pass` the overlay filter then
passes the main video straight through and the graphic never appears again — no error,
no warning. A render can come back with a working title card and zero subtitles.

Use `repeatlast=1` for stills, or hold the graphic in a full-length ProRes track (what
`captions.py` and `track_box.py` produce), which never EOFs early.


## `render.py` re-extracts every segment on a second pass

It does not reuse `clips_graded/` even when nothing about the cut changed, so a
second render of a 60-second clip pays the full extract-and-concat again — around a
minute wasted, on a workflow that is deliberately two passes (measure offsets, then
composite).

When only overlays or audio changed, skip the re-extract: keep the `base.mp4` from the
first pass and run the composite step's own ffmpeg command against it. Write the
overlays into `edl.json` anyway, so a plain `render.py edl.json` still reproduces the
result from scratch later.


## `render.py -o base.mp4` dies with exit 234

`render.py` concatenates its segments into `base.mp4` inside the edit directory. Ask it
to *write* `base.mp4` and the final copy step runs ffmpeg with the same file as input
and output, which fails with exit 234 and a traceback that points at ffmpeg rather than
at the name collision.

Name the output anything else — `final.mp4`, `preview.mp4`, `video_pro.mp4`. The same
applies to `base_draft.mp4` and `base_preview.mp4` in draft and preview modes.
