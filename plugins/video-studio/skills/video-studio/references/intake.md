# The interview

Three `AskUserQuestion` calls, up to four questions each, **in the user's own language**.

Format and style are settled before this point in their own steps, so what is left here is one round of scope, one of on-screen choices, and one of sound and finish. Drop any question the user has already answered in their request — re-asking something they just told you reads as not listening.

Two things make the difference between a useful interview and an annoying one:

**Write every option around their footage.** Not "Choose a hook style" but "Start with the Grafana logs at 0:47 (strongest thing you show), or start on your line 'QA tester kerak emas'". People who don't edit can't picture abstract options; they can absolutely tell you which of two moments is stronger.

**Put the recommendation first and say why.** Someone with no editing background wants a competent default, not a menu. Label it "(Recommended)" and let them accept in one click.

If they answer "you decide" at any point, stop asking, apply the defaults below, and list them compactly.

---

Format (aspect ratio, frame rate) is settled in its own step — see `formats.md`. Style
(pace, graphics density, music level) likewise — see `styles.md`. Both are asked before
this point, because the answers here depend on them.

## Round 1 — Scope

| key | ask about | typical options |
|---|---|---|
| `length` | how long | tight trim of what exists (~X s) · under 30s · under 60s · longer is fine |
| `hook` | the first 2 seconds | teaser of the best visual, then the claim · start on the claim with a title card · a question on screen · straight in |
| `zooms` | framing | reframe each shot to cut dead space · punch in on key moments · slow push on talking head · leave as filmed |
| `language` | subtitles | burned in, spoken language · plus English second line · separate file · none |

## Round 2 — On screen

| key | ask about | typical options |
|---|---|---|
| `graphics` | on-screen labels | labels + boxes pointing at what matters · full: labels, boxes, text reveals, numbers · just one title card · none |
| `caption_style` | subtitle look | the style preset's default (recommended) · larger and punchier · sentence at the bottom · none |
| `cover` | thumbnail | face + big title · screenshot proof + title · best frame, no text · none |
| `brand` | colors, font, handle | reuse what's in project.md · brand colors they name · the default dark + orange · no branding |

## Round 3 — Sound and finish

| key | ask about | typical options |
|---|---|---|
| `music` | background music | original bed generated here, quiet under the voice · their own track (ask for the file) · none |
| `sfx` | sound effects | subtle whooshes and ticks · punchy hits and risers · none |
| `levels` | loudness | social standard, −14 LUFS · podcast, −16 · broadcast, −23 · match the source |

## Style, asked once

If there is no brand in `edit/project.md` and they haven't mentioned one, ask in plain text: colors, font, and whether a handle or logo should appear. Otherwise propose near-black panels `#0A0A0A` with a single accent `#FF5A00`, Helvetica Bold titles, Menlo Bold for anything code-like — and say they can change it.

## Defaults

- format: keep the source's shape; 30 fps for talking heads, source rate for screen recordings
- style: Professional preset (`styles.md`)
- tight trim: dead air down to ~150ms, stumbles and repeats removed, all content kept
- subtitles burned in, spoken language, ASR errors hand-corrected
- hook: open on the claim with a title card; add a 1–2s teaser only if a genuinely strong visual exists later
- reframe each shot to remove dead space
- labels on each beat + motion-tracked boxes on what the viewer should look at
- captions: 72px cap, 7px outline, bottom edge 595px above the frame bottom (clear of the app's own buttons)
- music: generated bed, 15 LU under the voice, ducking 9 dB when they speak
- sound effects: subtle
- −14 LUFS, true peak ≤ −1.5 dBTP
- cover: face frame + title

## Record it

Save answers to `edit/brief.json` so a later session can pick up the same choices:

```json
{
  "language_of_user": "uz",
  "platform": "reels-9x16",
  "output": {"width": 1080, "height": 1920, "fps": 30},
  "length": "tight-trim",
  "goal": "learn-technique",
  "captions": {"mode": "burned", "language": "uz", "size_max": 72, "stroke": 7, "bottom_from_edge": 595},
  "hook": "claim-plus-card",
  "zooms": "static-reframe",
  "graphics": "labels-and-boxes",
  "music": {"source": "synth", "under_speech_lu": 15, "duck_db": 9},
  "sfx": "subtle",
  "levels": {"lufs": -14, "true_peak": -1.5},
  "cover": "face-title",
  "brand": {"panel": "#0A0A0A", "accent": "#FF5A00", "title_font": "Helvetica Bold", "mono_font": "Menlo Bold"}
}
```
