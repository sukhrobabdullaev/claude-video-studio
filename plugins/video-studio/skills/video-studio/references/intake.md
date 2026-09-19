# The interview

Three `AskUserQuestion` calls, four questions each, **in the user's own language**.

Two things make the difference between a useful interview and an annoying one:

**Write every option around their footage.** Not "Choose a hook style" but "Start with the Grafana logs at 0:47 (strongest thing you show), or start on your line 'QA tester kerak emas'". People who don't edit can't picture abstract options; they can absolutely tell you which of two moments is stronger.

**Put the recommendation first and say why.** Someone with no editing background wants a competent default, not a menu. Label it "(Recommended)" and let them accept in one click.

If they answer "you decide" at any point, stop asking, apply the defaults below, and list them compactly.

---

## Round 1 — Where it goes and what it's for

| key | ask about | typical options |
|---|---|---|
| `platform` | where they'll post it | Reels/TikTok/Shorts (tall) · YouTube (wide) · LinkedIn/X · several |
| `length` | how long | tight trim of what exists (~X s) · under 30s · under 60s · longer is fine |
| `goal` | what the viewer should do or feel | learn something · trust them as an expert · click/buy/sign up · entertain |
| `language` | subtitles | burned in, spoken language · plus English second line · separate file · none |

## Round 2 — How it looks

| key | ask about | typical options |
|---|---|---|
| `hook` | the first 2 seconds | teaser of the best visual, then the claim · start on the claim with a title card · a question on screen · straight in |
| `zooms` | framing | reframe each shot to cut dead space · punch in on key moments · slow push on talking head · leave as filmed |
| `graphics` | on-screen labels | labels + boxes pointing at what matters · full: labels, boxes, text reveals, numbers · just one title card · none |
| `caption_style` | subtitle look | small bold, 2 words at a time (recommended for tall video) · large punchy one word · sentence at the bottom · none |

## Round 3 — Sound and finish

| key | ask about | typical options |
|---|---|---|
| `music` | background music | original bed generated here, quiet under the voice · their own track (ask for the file) · none |
| `sfx` | sound effects | subtle whooshes and ticks · punchy hits and risers · none |
| `levels` | loudness | social standard, −14 LUFS · podcast, −16 · broadcast, −23 · match the source |
| `cover` | thumbnail | face + big title · screenshot proof + title · best frame, no text · none |

## Style, asked once

If there is no brand in `edit/project.md` and they haven't mentioned one, ask in plain text: colors, font, and whether a handle or logo should appear. Otherwise propose near-black panels `#0A0A0A` with a single accent `#FF5A00`, Helvetica Bold titles, Menlo Bold for anything code-like — and say they can change it.

## Defaults

- vertical 1080×1920 @30 if the source is vertical, otherwise match the source
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
