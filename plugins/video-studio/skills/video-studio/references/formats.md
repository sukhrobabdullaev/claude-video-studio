# Format, aspect ratio and delivery

Ask this explicitly. Do not infer the target from the source: people shoot vertically and publish to YouTube, or shoot wide and want a reel. Getting it wrong means re-rendering everything, because captions, graphics and safe zones are all sized to the frame.

State the source's own shape when you ask — "sizning videongiz vertikal (1080×1920), shu holda qoldiraylikmi yoki YouTube uchun 16:9 qilaylikmi?" — so the cheap option is obvious.

## Targets

| shape | pixels | where | notes |
|---|---|---|---|
| 9:16 | 1080×1920 | Reels, TikTok, Shorts | the app covers the bottom ~25–30% with its own UI |
| 16:9 | 1920×1080 | YouTube, web, presentations | the only shape where small on-screen text stays readable |
| 1:1 | 1080×1080 | feed posts | safe fallback when the destination is unknown |
| 4:5 | 1080×1350 | Instagram feed | tallest shape the feed will not crop |

Frame rate: **keep the source rate** for screen recordings, gameplay and anything with fast motion — halving 60 fps throws away the smoothness that made it worth recording. Use 30 for talking heads, where it halves the render time and nobody can tell. Never *raise* the rate; interpolated frames look worse than honest ones.

A phone filming a screen is both at once, and the answer is 30: the camera is already the limiting factor, the screen's own refresh is lost to the lens regardless, and the handheld motion at 60 costs double the render for smoothness the footage never had. Keep 60 only when the screen content itself moves fast enough to smear — scrolling code, a game, a fast cursor drag.

Encoding: H.264 High, `yuv420p`, CRF 18–20 for a master, `+faststart` so it starts playing before it finishes downloading. Platforms re-encode to 3–5 Mbps anyway, so a clean master matters more than a small file.

## Safe zones

Captions and graphics must survive the platform's own interface. The rule that matters is distance from the bottom edge:

| shape | caption baseline above bottom | why |
|---|---|---|
| 9:16 | ~595 px of 1920 (31%) | clears the caption, username and the right-hand button column |
| 4:5 | ~250 px of 1350 (19%) | feed UI is shallower |
| 1:1 | ~200 px of 1080 (19%) | same |
| 16:9 | ~120 px of 1080 (11%) | player controls only, and they auto-hide |

Keep the top ~12% clear on 9:16 as well — that is where the app puts its own labels.

## Converting between shapes

| source → target | what to do |
|---|---|
| vertical → 9:16 | nothing; reframe only to remove dead space |
| horizontal → 9:16 | crop to the subject, and **track it** — a static centre crop loses the speaker the moment they move. `track_box.py`'s motion estimate can drive the crop path. Alternative when the whole frame matters (a screen recording): fit the full width and fill the space above and below with a blurred copy or a solid brand panel |
| vertical → 16:9 | same problem inverted: pillarbox with a blurred backdrop, or build a two-panel layout (speaker on one side, screen on the other) |
| any → 1:1 or 4:5 | centre crop is usually fine; check the subject's head is not cut |

When a conversion would crop out something the video depends on — the side of a screen showing a log panel, for instance — say so and offer the padded layout instead. Silently cropping away the point of the video is the worst outcome here.

## Reframing mechanics

The EDL has no per-range filter, so render a full-length reframed intermediate per treatment and reference it as another source (see `cutting.md`). Compute every crop in **displayed** coordinates: phone footage is stored rotated, and `footage_report.py` prints both the stored and displayed size for exactly this reason.
