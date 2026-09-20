---
name: video-studio
description: Edit raw video footage into a finished, professional-quality video — reading the material first, then deciding format, style, subtitles, music, sound levels and cover with the user, then cutting and quality-checking it. Use this whenever someone has a video file (.mov .mp4 .m4v .mkv) or a folder of takes and wants it edited, cut, trimmed, captioned, subtitled, turned into a reel / short / TikTok / YouTube video, given music or motion graphics, or simply "made professional" — even if they only say "here's my video, fix it", drag a clip in, or ask for a thumbnail or cover for it. Also use it to continue an edit that already has an edit/project.md.
---

# Video Studio

Turn raw footage into a finished video, working with someone who may know nothing about editing.

They know how they want to come across; they do not know what a LUFS is. So ask about outcomes in their words, make the technical calls yourself, and prove the result with numbers at the end.

## Three rules that shape everything

**Speak their language.** Ask and answer in whatever language they write in. Subtitles follow the language spoken *in the video*, which is often a different one.

**Teach as you go.** One sentence per step saying what you are doing and why — "avval materialni o'lchayman, chunki tebranish qanchaligi kadr uzunligini hal qiladi". By the third video they will understand their own footage. Never a lecture: one sentence, then work.

**Look before you ask.** A question asked blind gets "I don't know". A question asked after reading the transcript — quoting their own line, with a timestamp — gets a real answer in one click.

## Setup

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/doctor.sh          # macOS, Linux
powershell -File ${CLAUDE_SKILL_DIR}\scripts\doctor.ps1   # Windows
```

`FAIL` → run `setup.sh` / `setup.ps1`, follow what it prints, check again.

Every bundled script runs through the wrapper, which finds the Python environment and loads any API keys:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh <script> [args]
```

**On Windows, `vs.ps1` replaces `vs.sh` everywhere in this skill** — `powershell -File ${CLAUDE_SKILL_DIR}\scripts\vs.ps1 <script> [args]`. The scripts themselves are identical on all three platforms; only the two wrappers differ. Anything platform-specific (where the environment lives, how ffmpeg is installed, which fonts are used) is resolved in `scripts/platform_paths.py`, so nothing else branches on the operating system.

Fonts are bundled (Inter Bold, JetBrains Mono Bold, both OFL), so a caption renders the same on every machine and Uzbek `o'` / `g'` are guaranteed present.

To prove the whole chain works on this machine — every script, no API calls, about six seconds — run the smoke test. It builds its own clip, so it needs no footage and spends no credits:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh selftest.py
```

Anything other than `14/14 passed` is a broken install; the failing line names the script.

`references/troubleshooting.md` lists the environment traps. They fail silently, and the scripts already work around them.

## The engine

`scripts/vendor/` bundles the **video-use** helpers (MIT, Browser Use). Motion graphics use **HyperFrames** when installed, otherwise the bundled renderer (`references/graphics.md`).

## Workflow

Work in this order. Each step exists because the next one needs its answer.

### 0. Resume

`<footage_dir>/edit/project.md` exists → summarize the last session in one sentence, ask whether to continue or start over.

### 1. Context — read the material

*Why: you cannot plan an edit for footage you have not seen, and every later question depends on knowing what is in it.*

Follow `references/context.md`:

- Ask which transcription service they have a key for — ElevenLabs, OpenAI, Gemini, or none at all (there is a free offline option). `references/stt.md` has the comparison; the edit is identical whichever they pick. Store the choice in `brief.json`, say once that transcription costs money per video, and never re-transcribe a cached source.
- Read the timing check that `transcribe.py` prints. If it reports an offset or invented timing, stop and fix that before planning anything — every cut and caption is built on those numbers.
- `vs.sh transcribe.py`, `vs.sh vendor/pack_transcripts.py`, `vs.sh footage_report.py`.
- Read the transcript for topic, structure, proper nouns and weak spots. Pull three or four **full-resolution** frames and look at them.
- Tell them in three sentences what you found, including any personal data visible on screen.
- Ask only the three things the material cannot reveal: who it is for, what the viewer should do afterwards, and anything that must be spelled exactly or must not appear.

### 2. Format — decide the frame

*Why: captions, graphics and crops are all sized to the frame, so changing it later means rendering everything twice.*

`references/formats.md`. Ask the aspect ratio explicitly, naming the source's own shape so the cheap option is obvious. Settle frame rate at the same time (keep the source rate for screen recordings and fast motion; 30 for talking heads). If the conversion would crop away something the video depends on, say so and offer a padded layout instead.

### 3. Style — decide how it should feel

*Why: this is the one creative decision they can make confidently, and it sets pace, graphics density, music level and caption size all at once.*

`references/styles.md`. Ask it as a feeling, map it to Professional / Creative / Documentary / Educational, and copy the preset into `brief.json`. If the footage argues against their choice — heavy shake with documentary pacing, dense screen text with a Creative graphics budget — say so once, then follow their call.

### 4. Details

*Why: the remaining choices are cheap to ask now and expensive to change after rendering.*

`references/intake.md` covers what is left: hook, zooms, graphics level, caption style, music, sound effects, loudness target, cover. Anyone who says "you decide" gets the defaults — list them compactly so nothing is a surprise, then move on. An unsure person answering "I don't know" three times is telling you to decide for them.

### 5. Plan, and wait

Four to eight plain sentences: structure, what gets cut, what appears on screen and when, captions, music, length. Wait for a yes.

### 6. Edit

1. **Cut** — `references/cutting.md`. Word-boundary edges, audited in code.
2. **Reframe** — full-length intermediates, referenced as extra sources.
3. **Measure the timeline** — `vs.sh offsets.py`. Per-cut frame rounding drifts it; everything after this is timed against the measured offsets.
4. **Graphics** — `references/graphics.md`. Staggered reveals.
5. **Subtitles** — `vs.sh captions.py`, after showing your ASR corrections.
6. **Sound** — `references/audio.md`. `vs.sh synth_audio.py`, then `vs.sh mix.py`.
7. **Cover** — `vs.sh cover.py` if asked.

### 7. Prove it

`references/quality-gates.md` on the rendered file. Fix, re-render, re-check, at most three rounds, then report what still fails.

The cut that sounds fine to you may click at 12.3 s and run captions 200 ms late. Measure.

### 8. Deliver

- `SendUserFile` the video and cover. Over 30 MB shows only in the desktop app — say so.
- Report in plain language, with the measured numbers as evidence.
- Raise what is theirs to decide: personal data on screen, borderline taste calls, music licensing for a supplied track.
- Append to `edit/project.md`: decisions, reasoning, measurements, what is outstanding.

## Boundaries

- Outputs go in `<footage_dir>/edit/`. Never write inside the skill directory; it may be read-only.
- Never upload, publish or post the video. Hand over the file.
- Never download music or stock footage. Use `synth_audio.py` or a file they provide.
- Flag, rather than quietly ship, footage showing someone else's personal data or a person who plainly did not agree to be filmed.
