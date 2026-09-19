# Choosing a transcription provider

Ask the user which provider to use the first time, then remember it in `edit/brief.json`.

## The hard requirement

Every cut edge, caption cue and graphic sync point in this pipeline is derived from **word-level start/end times**. A provider that returns sentence or segment timing cannot drive it: cutting on a segment boundary slices mid-word, and captions land a second late.

So the question to the user is not "which AI do you like" — it is "which of these do you have access to", and the honest answer is that any of the three below works identically downstream.

## Providers

| | word timing | speakers | offline | cost model | limits |
|---|---|---|---|---|---|
| **ElevenLabs** Scribe | yes | yes (diarization) | no | per minute of audio | — |
| **OpenAI** `whisper-1` | yes (`timestamp_granularities:["word"]` + `verbose_json`) | no | no | per minute of audio | 25 MB upload |
| **Gemini** | best effort via JSON schema | no | no | per minute of audio | see the warning below |
| **local** faster-whisper | yes (`word_timestamps=True`) | no | yes | free after model download | slower; accuracy drops hard outside major languages |

`transcribe.py` normalizes all three to the same JSON, so nothing downstream changes.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh transcribe.py clip.mov --provider auto --audio-track 0
```

`auto` picks the first available: ElevenLabs key → OpenAI key → local install.

## Gemini: good words, invented times

Gemini is supported and it transcribes well. Its timing cannot be cut on. This was measured, not assumed — a 63-second Uzbek clip, run through both providers:

| | Gemini 2.5 Flash | ElevenLabs Scribe |
|---|---|---|
| words returned | 142 | 142 |
| text accuracy | near-identical (`bironta`/`birorta`, `man`/`men`) | reference |
| word 8 timing | 3.55–3.90 s | 2.66–2.98 s |
| timing check | **failed** (offset −260 ms, correlation 0.05, times running backwards) | passed |
| `gemini-3-flash-preview` | **failed harder** — correlation 0.00, words timed past the end of the audio | — |

Look at what the numbers describe: every Gemini word starts exactly where the previous one ended. There are no gaps, anywhere — and the clip has 7 seconds of silence in it. The model is spreading words evenly across the duration rather than reporting where they were heard, and by word 8 it has already drifted almost a second.

So use Gemini for what it is good at:

- **Text**: as a second opinion on a hard word, or on a language another provider mangles.
- **Context**: it is the only option here that can describe what is *visually* on screen.

And take the timing from ElevenLabs, OpenAI or local whisper. If Gemini is the only key available, say plainly that captions will drift and cuts will land inside words, and offer the free local provider as the timing source instead.

Read the check the script prints after every transcription:

```
  timing check: words line up with the audio
```

If instead it reports an offset or "this timing is invented", the transcript is fine as *text* but must not drive cuts or captions. Offer to re-run with a provider that documents word timing, or to use the Gemini text with another provider's timing.

Gemini is also the only option here that can describe what is *visually* on screen, which the transcript cannot. That is a genuine use for it even when another provider does the timing.

## Every transcript is checked against the audio

`transcribe.py` cross-correlates where the words claim to be against where sound actually is, and reports a constant offset or a complete mismatch. Measured on a 63-second clip with a known-good transcript:

| transcript | verdict |
|---|---|
| unmodified | passes |
| shifted 300 ms | caught, reported as `+300 ms` |
| shifted 800 ms | caught |
| 6-word `tiny` output | caught: "does not track the audio at any offset" |

A silence-overlap test was tried first and proved useless on dense speech — with few long gaps, a transcript shifted by a whole second still lands nearly every word on top of speech. Correlation catches both the offset and the invented case.

## Local models are not equal across languages

Measured on this machine: the `tiny` model on a 63-second Uzbek clip returned **6 words**
where ElevenLabs returned 142, and what it did return was English-sounding nonsense. The
JSON was structurally perfect and every downstream step accepted it — which is exactly
what makes this dangerous. An edit built on that transcript cuts in the wrong places and
burns invented words into the picture.

`transcribe.py` guards against it: under 40 words per minute of video it warns that the
model likely misheard the language. Treat that warning as a stop sign, not a note.

For anything outside English and the major European languages, use `--model large-v3`
(slower, several GB) or a paid provider. For Uzbek specifically, ElevenLabs was the only
option here that produced a usable transcript.

## Keys

Keys live in `~/.video-studio/.env`, one per line, and the wrapper exports them:

```
ELEVENLABS_API_KEY=...
OPENAI_API_KEY=...
```

Never ask the user to paste a key into the chat — the transcript is stored. Give them the `printf ... > ~/.video-studio/.env` command to run in their own terminal, as `setup.sh` prints it.

## Practical notes

- **Cost happens once per source.** The result is cached at `edit/transcripts/<stem>.json`; re-running reads the cache. Only `--force` re-transcribes, and it should be rare enough to mention when you use it.
- **Pick the mic track.** `--audio-track 0` is the default because iPhone clips carry a second 4-channel spatial track that ffmpeg prefers on its own, and transcribing it gives you room ambience.
- **Long files on OpenAI** are compressed to 16 kHz mono MP3 and, if still over 25 MB, split with the time offset carried across chunks. That stitching is automatic but worth a sanity check on the first long file: the words either side of a chunk boundary should read continuously.
- **Language.** Leave it to auto-detect unless detection is visibly wrong; forcing `--language uz` helps for short or heavily accented clips. Scribe reports a confidence — around 0.5 is normal for Uzbek and does not mean the words are wrong.
- **Accuracy is not uniform.** Proper nouns and technical terms are where ASR fails, and they are exactly what the audience notices. Correct them in a copy of the transcript before burning captions, and show the user your corrections (see `context.md`).
