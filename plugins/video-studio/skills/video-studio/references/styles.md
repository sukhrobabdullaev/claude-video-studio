# Editing styles

Style is the one creative decision the user can make confidently without knowing any editing vocabulary, because they know how they want to come across. Ask it as a feeling — "tezkor va zarbdormi, yoki bosiq va ishonchlimi?" — and map the answer to one of these four.

Copy the chosen preset into `edit/brief.json` so every later step reads the same numbers instead of re-deciding.

## The four

| | **Professional** | **Creative** | **Documentary** | **Educational** |
|---|---|---|---|---|
| feels like | calm authority | fast, punchy | observed, unhurried | patient, clear |
| avg shot length | 3–5 s | 1.5–2.5 s | 6–10 s | 4–8 s |
| pauses trimmed to | 150 ms | 80 ms | 250 ms | 200 ms |
| graphics | labels on key beats | frequent, kinetic | minimal, lower thirds only | labels + callouts on detail |
| transitions | hard cuts | whip/flash on existing motion | hard cuts, rare dissolve | hard cuts + punch-ins |
| music under voice | −15 LU | −12 LU, cut to the beat | −18 LU or none | −16 LU |
| captions | 72 px, 2 words | 84 px, 1–2 words | 64 px, sentence | 72 px, 2–3 words |
| grade | neutral + slight contrast | saturated, punchy | natural, untouched | neutral, safe for screen content |
| sound effects | one per section change | frequent | none | subtle, on reveals |

## Reading the material, not just the answer

The footage argues for a style too, and when it disagrees with the user's answer, say so once and let them decide:

- **Heavy camera motion** (`footage_report.py` median above ~60 px/s) fights long shots — the eye tires. Documentary pacing on shaky handheld looks like a mistake rather than a choice.
- **Dense screen content** argues against Creative: labels and flashes cover the thing the viewer is supposed to read.
- **A quiet, careful delivery** cut to 1.5-second shots feels frantic and wrong; the pacing should follow the speech, not the trend.
- **Long unbroken explanation** is where Educational earns its keep: punch in on the detail being described rather than cutting away from it.

## Applying a style

The numbers above are starting values, not a contract. Two rules keep a style coherent once you start deviating:

**Pace comes from the speech, not the clock.** A 2-second target shot length does not mean cutting every 2 seconds; it means choosing the tighter option at each natural boundary. Cutting mid-thought to hit a number is how edits start feeling mechanical.

**Density is a budget.** Creative allows frequent graphics, but two things still never reveal at once — stagger them 0.2–0.4 s. The budget buys more moments, not more simultaneous noise.

## brief.json

```json
{
  "style": "professional",
  "pace": {"avg_shot_s": [3, 5], "gap_trim_ms": 150},
  "graphics": {"density": "key-beats", "transitions": "hard-cut"},
  "music": {"under_speech_lu": 15},
  "captions": {"size_max": 72, "words_per_chunk": 2},
  "grade": "neutral-contrast",
  "sfx": "section-changes"
}
```
