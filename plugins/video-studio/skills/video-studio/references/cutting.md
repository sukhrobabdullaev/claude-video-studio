# Cutting

The bundled engine (`scripts/vendor/`, from video-use, MIT) reads the video as text: a word-level transcript is the editing surface, and pictures are pulled only at decision points. That is why an hour of footage can be edited without watching it — but it also means the transcript's timestamps are the only thing standing between you and a cut in the middle of a word.

## Pipeline

```bash
V=${CLAUDE_SKILL_DIR}/scripts/vs.sh
bash $V vendor/transcribe.py <video> --audio-track 0      # word-level, cached
bash $V vendor/pack_transcripts.py --edit-dir <dir>/edit  # -> takes_packed.md
bash $V vendor/timeline_view.py <video> <start> <end>     # filmstrip + waveform PNG
bash $V vendor/render.py <edl.json> -o out.mp4 --fps 30 --no-subtitles --no-loudnorm
bash $V offsets.py --edl <edl.json>                       # measured output timeline
```

`--audio-track 0` matters: iPhone clips carry a second 4-channel spatial track, and ffmpeg otherwise picks the track with the most channels — you would transcribe room ambience instead of the voice.

Use `--no-loudnorm` whenever music will be mixed in later, so loudness is set once on the finished mix rather than twice.

## Rules that cause silent damage when broken

These are not style preferences. Each one has a failure that is invisible until someone watches the result.

1. **Never cut inside a word.** Snap every edge to a word boundary from the transcript, then audit it in code — a 50ms overlap shows up as a stuttered syllable and a duplicated caption word. Audit, don't eyeball:

```python
inside = [w for w in words if w["start"] < edge < w["end"]]
```

2. **Pad every edge 30–200ms.** Scribe timestamps drift 50–100ms; padding absorbs it.
3. **30ms audio fades at every segment boundary** — otherwise every cut clicks.
4. **Extract per segment, then concat losslessly.** A single filtergraph re-encodes everything twice once overlays exist.
5. **Subtitles composite last**, after every overlay, or graphics cover them.
6. **Overlay timing uses `setpts=PTS-STARTPTS+T/TB`**, or you see the middle of an animation instead of its start.
7. **Caption times use measured output offsets**, not nominal EDL durations.
8. **Never re-transcribe a cached source.** It costs money and changes nothing.

## Where cuts belong

Silences ≥400ms are the cleanest cut targets; 150–400ms works if a timeline view confirms it; below 150ms you are inside a phrase. Keep laughs and reactions — the laugh *is* the beat. Give speaker changes 400–600ms of air.

Cut stumbles out through the gap around them: find the silence before and after the fumbled word, and make the two edges land in those gaps. If a word is unintelligible even to you, ask the user what they said rather than guessing at a subtitle.

## Zooms and reframes

The EDL has no per-range filter, so render a full-length reframed intermediate and treat it as another source:

```bash
ffmpeg -i src.mov -map 0:v:0 -map 0:a:0 \
  -vf "crop=810:1440:135:90,scale=1080:1920:flags=lanczos" \
  -c:v libx264 -preset fast -crf 16 -pix_fmt yuv420p -c:a copy edit/punch/demo.mp4
```

Copy the transcript to `transcripts/<source-key>.json` for each new source key, because captions resolve transcripts by source key. Keep the same duration and timebase so the EDL's times stay valid against either source.

A cut that switches sources mid-motion (a whip pan, a hand crossing frame) hides itself completely; the same cut on a still frame is a visible jump. Use the motion the footage already has.
