# Motion graphics and captions

## Which renderer

**HyperFrames** (if `~/.claude/skills/hyperframes/SKILL.md` exists) authors graphics as HTML/CSS/GSAP compositions and renders them deterministically. Use it for anything with real motion design: kinetic type, staged reveals, charts, UI recreations. Read `/hyperframes` first, scaffold inside the slot directory:

```bash
cd edit/animations/slot_1 && npx --yes hyperframes init . --example blank --non-interactive --skip-skills
npx --yes hyperframes lint . && npx --yes hyperframes check .
npx --yes hyperframes render . --format webm -o render.webm
bash ${CLAUDE_SKILL_DIR}/scripts/to_prores.sh render.webm render.mov
```

When several graphics are needed, build them in parallel sub-agents (one per graphic, each prompt self-contained with exact pixel specs, palette, font paths and a frame-by-frame timeline) — sequential builds waste wall-clock for no benefit. For mechanical variations of one design, a single script that loops is better than several agents: consistency comes free.

**PIL fallback** (always available) is right for label cards, highlight boxes, lower thirds and anything geometric. `track_box.py` is already this.

Run a script you wrote through the same wrapper — the system `python3` has no Pillow, and the wrapper takes a path as readily as a bundled name:

```bash
cd <footage dir>
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh edit/animations/slot_1/make_card.py
# Windows: powershell -File ${CLAUDE_SKILL_DIR}\scripts\vs.ps1 edit\animations\slot_1\make_card.py
```

Inside such a script, take fonts from the platform layer rather than hardcoding a path — the bundled faces exist on every machine, system fonts do not:

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from platform_paths import load_font
title, label = load_font("sans", 72), load_font("mono", 34)
```

A bare name means a bundled script; anything with a slash is your own, and resolves from the current directory — so either `cd` to the footage folder first or pass an absolute path.

Pipe RGBA frames straight into ProRes:

```python
p = subprocess.Popen(["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgba","-s",f"{W}x{H}",
  "-r","30","-i","pipe:0","-c:v","prores_ks","-profile:v","4444","-pix_fmt","yuva444p12le",
  "-an",str(out)], stdin=subprocess.PIPE)
```

## Alpha: the trap that silently ruins a render

Deliver **every** overlay as ProRes 4444 (`yuva444p12le`). ffmpeg's native VP9 decoder ignores WebM alpha and `render.py` does not force `libvpx-vp9`, so a WebM overlay composites as an **opaque black rectangle over the whole frame** — no error, no warning. `to_prores.sh` handles the conversion.

Verify before trusting it: composite one held frame over solid red and confirm red shows outside the graphic.

```bash
ffmpeg -f lavfi -i color=c=red:s=1080x1920:d=3 -i overlay.mov \
  -filter_complex "[0:v][1:v]overlay=enable='between(t,0,3)'" -ss 1.5 -frames:v 1 check.png
```

## Motion that reads as designed

- **Never linear.** `ease_out_cubic` = `1 - (1-t)**3` for reveals; ease-in-out for continuous moves.
- **One new thing at a time.** Two elements appearing together is unreadable — stagger by 0.2–0.4s. This also applies across graphics: two cards appearing at once looks like a bug.
- **Land the payoff on the spoken word.** Start the reveal `reveal_duration` earlier so the finished frame coincides with the word it illustrates.
- **Hold ≥1s** before it disappears; over narration, run at least `narration + 1s`.
- **Typing text:** center on the full string's width, never the partial one, or the text slides sideways as it grows.

## Highlight boxes

`vs.sh track_box.py --video <reframed source> --rect X0 Y0 X1 Y1 --window S E --ref T --out box.mov`

It phase-correlates each frame against the reference and offsets the box, because on handheld footage a static box drifts off its target within half a second. It prints the measured drift and warns when the box leaves the frame — if it does, the target itself has left the frame, so shorten the window rather than letting the box chase it off-screen.

Measure `--rect` off a full-resolution frame at `--ref`, in output-frame pixels.

## Captions

`vs.sh captions.py --edl edit/edl.json --offsets edit/offsets.json --out edit/captions.mov`

Frame-exact by construction, gap-bridged so text doesn't blink between chunks, and independent of libass (which many ffmpeg builds lack). Composite it **last**.

Placement is a platform rule, not taste: the bottom ~25–30% of a vertical frame is covered by the app's own caption, username and buttons. `--bottom-from-edge 595` clears it on a 1920-tall frame.

Before the final render, hand-correct the transcript copy the captions read from — ASR reliably mangles brand and technical names (`kodeksda` → `Codex'da`, `grafinaga` → `Grafana'ga`) — and show the corrected lines to the user. They are the only one who knows what they actually said.
