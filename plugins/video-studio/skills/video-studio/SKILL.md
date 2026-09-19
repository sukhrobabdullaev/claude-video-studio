---
name: video-studio
description: Edit raw video footage into a finished, professional-quality video — interviewing the user first about hook, zooms, motion graphics, subtitles, music, sound levels and cover, then cutting, captioning, scoring and quality-checking it. Use this whenever someone has a video file (.mov .mp4 .m4v .mkv) or a folder of takes and wants it edited, cut, trimmed, captioned, subtitled, sped up, turned into a reel / short / TikTok / YouTube video, given music or motion graphics, or simply "made professional" — even if they only say "here's my video, fix it", drag a clip in, or ask for a thumbnail or cover for it. Also use it to continue an edit that already has an edit/project.md.
---

# Video Studio

Turn raw footage into a finished video, for someone who may know nothing about editing.

The person you are working with is usually **not an editor**. They know what they want the video to feel like, not what a LUFS or a J-cut is. Your job is to ask about outcomes in their own words, make the technical decisions yourself, and show your work in numbers only when it proves the result is good.

## Two rules that shape everything

**Speak their language.** Answer and ask questions in whatever language the user writes to you in — Uzbek, Russian, English, anything. Subtitles follow the language spoken *in the video*, which is often different. Never make someone read English questions to edit their own Uzbek video.

**No jargon without a plain-language anchor.** "LUFS" alone is useless; "−14 LUFS, the loudness Instagram expects" is fine. If you would need a diagram to explain a term, you probably shouldn't be asking about it at all — decide it yourself and report it afterwards.

## Setup

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/doctor.sh
```

Any `FAIL` → run `bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh`, follow what it prints, then check again. Never start editing on a broken toolchain; you will waste the user's time and their transcription credits.

Run every bundled script through the wrapper, which loads the Python environment and the API key:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh <script> [args]     # e.g. vendor/render.py, captions.py
```

`references/troubleshooting.md` explains the environment traps (they are real, they bite silently, and the scripts already work around them).

## The engine

`scripts/vendor/` bundles the **video-use** helpers (MIT, Browser Use — see `scripts/vendor/LICENSE-video-use`): transcription, transcript packing, timeline views, cutting, grading and rendering. `references/cutting.md` documents how to drive them and the production rules that must not be broken.

Motion graphics come from **HyperFrames** when it is installed (`/hyperframes` skills), otherwise from the bundled Python renderer. `references/graphics.md` covers both.

## Workflow

### 1. Resume or start

If `<footage_dir>/edit/project.md` exists, summarize the last session in one sentence and ask whether to continue or start fresh. That file is the memory of every earlier decision — read it before changing anything.

### 2. Look at the footage first

Never ask a single question before you have seen what you are working with — generic questions produce generic videos, and you cannot propose a hook if you don't know what the person says in the first ten seconds.

- `ffprobe` each file: resolution **after rotation**, fps, duration, and every audio track.
- Transcribe (`vendor/transcribe.py`), pack (`vendor/pack_transcripts.py`), and read the result.
- Look at a few **full-resolution frames**, not only filmstrip thumbnails — thumbnails make perfectly readable screen recordings look unreadable, and that mistake changes the whole edit plan.
- Note: stumbles, repeats, filler, dead air totals, and any name/address/key visible on screen.

Transcription costs the user real money per video. Say so once, before the first one, and never re-transcribe a source you have already transcribed.

Then tell them what you found, in a few plain sentences: how long it is, how much of it is actual talking, what the shape of it is, and what problems you spotted.

### 3. Interview (the part that must never be skipped)

Follow `references/intake.md`: three rounds of four questions, in the user's language, each option written around *their* footage and quoting *their* words with timestamps.

If they say "you decide", "sen hal qil", "just make it good" — use the defaults in that file, list them in one short block so nothing is a surprise, and move on. Confirming beats interrogating: an unsure person answers "I don't know" to every question, and that is a signal to decide for them, not to ask again.

### 4. Plan, then wait

Describe the edit in 4–8 plain sentences: structure, what gets cut, what appears on screen and when, subtitle style, music, length. Wait for a yes. Editing before the plan is approved wastes an hour of rendering on the wrong video.

### 5. Edit

Order matters; each step feeds the next:

1. **Cut** — `references/cutting.md`. Word-boundary cuts, audited programmatically.
2. **Reframe / zoom** — full-length reframed intermediates, referenced as extra sources.
3. **Measure the real timeline** — `vs.sh offsets.py`. Frame rounding drifts the timeline; everything after this step is timed against the measured offsets, never the nominal EDL.
4. **Graphics** — `references/graphics.md`. Staggered reveals, never two at once.
5. **Subtitles** — `vs.sh captions.py`. Hand-correct names and technical terms first, and show the corrected lines before the final render.
6. **Sound** — `references/audio.md`. `vs.sh synth_audio.py` then `vs.sh mix.py`.
7. **Cover** — `vs.sh cover.py`, if they asked for one.

### 6. Prove it is good before showing it

Run the gates in `references/quality-gates.md` on the rendered file. Fix, re-render, re-check — at most three rounds, then report what still fails instead of looping.

This is what separates a professional result from a plausible one: the cut that sounds fine to you may have a click at 12.3s and a caption 200ms late. Measure, don't assume.

### 7. Deliver

- Send the video and cover with `SendUserFile`. Files over 30 MB show only in the desktop app — say so when it applies.
- Report in plain language what you did, plus the measured numbers as evidence.
- Raise anything that is the user's call: personal data visible on screen, borderline taste decisions, music licensing if they supplied a track.
- Append a session entry to `<footage_dir>/edit/project.md`: what was decided, why, what was measured, what is left. The next session — maybe months later — starts by reading it.

## Boundaries

- All outputs go in `<footage_dir>/edit/`. Never write inside the skill directory; it may be read-only.
- Never upload, publish or post the video anywhere. Hand the file to the user.
- Never download music or stock footage from the internet. Use `synth_audio.py`, or a file the user provides.
- If a person appears in the footage who plainly did not consent to being filmed, or the video shows someone else's personal data, flag it before delivery rather than quietly shipping it.
