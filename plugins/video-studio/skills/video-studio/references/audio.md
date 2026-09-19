# Sound

Sound is where amateur edits give themselves away: music that fights the voice, a cut that clicks, one video twice as loud as the next in the feed. All three are measurable, so none of them need to be guessed at.

## Order

Render the video with `--no-loudnorm`, then mix once on the finished audio:

```bash
V=${CLAUDE_SKILL_DIR}/scripts/vs.sh
bash $V synth_audio.py --out edit/audio --duration 70
bash $V mix.py --video edit/video.mp4 --bed edit/audio/music_bed.wav \
  --sfx-dir edit/audio --cues edit/cues.json --mute-until 1.2 --out edit/final.mp4
```

`mix.py` mutes the cold open if there is one, ducks the bed against a measured speech envelope, places the effects, masters in two passes, muxes with `-c:v copy` (the picture is never re-encoded), and prints every level with PASS/FAIL.

## Music

`synth_audio.py` generates an original bed and effects kit — no download, no licensing question, and the user can ship it anywhere. It is deliberately plain; it should register as air under the voice, not as a tune competing with it.

If the user supplies their own track, use it and tell them plainly that music licensing on the platform is their responsibility. Never download music from the internet, even from "free" sites — you cannot verify the license and they carry the risk.

## Targets, and why

| target | value | why |
|---|---|---|
| integrated loudness | −14 LUFS | what Instagram, TikTok and YouTube normalize to; quieter videos sound weak next to everything else |
| true peak | ≤ −1.5 dBTP | AAC encoding adds roughly 0.5 dB, so a WAV mastered at −1.0 clips after upload |
| bed under speech | ≥ 14 LU | below this the music competes with words; the viewer feels tired without knowing why |
| ducking | ~9 dB while speaking | the bed steps back under the voice and returns in gaps |
| effects peak | ≤ −12 dBFS | a whoosh louder than the voice makes the whole edit feel cheap |
| cold open | ≤ speech body +2 dB | an opener that jumps in volume gets muted, and a muted video gets scrolled past |

Measure the **final encoded file**, not the WAV, for loudness and peak. The encoder changes both.

## Effects, placed with intent

Cue file is a list: `[{"file": "whoosh_up.wav", "at": 8.63, "gain_db": -11}]`, times in output seconds.

A sound effect earns its place by marking a change the picture already makes: a whoosh on a hard transition, a soft tick as a label appears, a low thud on a cut into the main video, a riser under a teaser. Effects sprinkled over unchanged picture read as noise. When in doubt, leave it out — subtle is the default for a reason.

## Pops

Every cut boundary gets checked: `vs.sh check_boundaries.py --video edit/final.mp4 --offsets edit/offsets.json --exempt 1.2 8.63`

A click shows up as a transient far above the local level. Boundaries where an effect was placed deliberately are exempt — list them, so the check stays meaningful instead of being waved away.
