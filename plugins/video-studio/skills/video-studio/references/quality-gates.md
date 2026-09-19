# Quality gates

Run on the **rendered deliverable**, not on sources or intermediates. Report each gate as PASS / FAIL with the measured number.

| # | gate | how | pass |
|---|---|---|---|
| 1 | Spec | `ffprobe` width, height, fps, pix_fmt, audio codec/channels | matches `brief.json` output; yuv420p; AAC 48k stereo |
| 2 | Duration | `ffprobe` vs sum of measured offsets | within ±1 frame of expected (plus any overlay tail) |
| 3 | No cut inside a word | programmatic audit of every EDL range edge against transcript words | 0 edges strictly inside a word (muted cold-open ranges exempt, documented) |
| 4 | No audio pops | `vs.sh check_boundaries.py` | every boundary transient ratio ≤ 6, except boundaries with an intentional SFX hit (listed) |
| 5 | Integrated loudness | `vs.sh mix.py` output or `loudnorm print_format=summary` on the final file | target ±0.5 LU |
| 6 | True peak | same | ≤ target (e.g. −1.5 dBTP). AAC encoding can add ~0.5 dB — measure the final file, not the WAV |
| 7 | Music balance | `vs.sh mix.py` stems | bed ≥ 14 LU under speech |
| 8 | SFX headroom | `vs.sh mix.py` | SFX bus peak ≤ −12 dBFS |
| 9 | Cold open not hot | RMS of cold open vs speech body | cold open ≤ speech body +2 dB |
| 10 | Caption sync | `vs.sh captions.py` prints drift | caption track drift ≤ 1 frame |
| 11 | Captions visible | extract frames at 3+ cue midpoints incl. every overlay window | caption present, not occluded, inside safe margins |
| 12 | Overlay alpha | composite each overlay over solid red at a hold frame | red visible outside the graphic |
| 13 | Graphics land | view a frame at each graphic's hold moment | on target (highlights on their UI element), text unclipped, no two reveals simultaneous |
| 14 | ASR corrections | read the cue list | brand/tech names spelled correctly; no duplicated words at cut points |
| 15 | PII | view frames across every screen section | no names/addresses/emails/keys on screen, or each one reported with timestamp |
| 16 | Cover crops | `vs.sh cover.py` safe-band check + view the 4:5 crop | type fully inside 4:5 center band |

Max 3 fix/re-render passes. If a gate still fails, ship nothing silently — report the failing gate, the number, and the options.


## Input-side checks (before editing, from `footage_report.py`)

These never block an edit. They decide what the edit has to compensate for, and they
belong in the plan you show the user — a problem named up front is a craft decision,
the same problem found afterwards is a complaint.

| measure | when it matters | what it changes |
|---|---|---|
| camera motion (median px/s) | above ~60 | shorter shots; overlays must be motion-tracked, never static |
| blur score | high / rising | do not punch in — zooming soft footage makes it softer |
| highlight clipping % | above ~5 | do not lift exposure; the bright area is already gone |
| average luma | below ~60 | gentle lift only; grading hard raises noise |
| noise floor (dB) | above ~−50 | keep music quieter than the preset default |
| integrated LUFS | below ~−20 | the source needs normalizing, say so before they hear it |
| silence total | above ~5 s | this is where runtime comes from without losing content |
| scene changes | any | natural section boundaries — cut on them rather than through them |
