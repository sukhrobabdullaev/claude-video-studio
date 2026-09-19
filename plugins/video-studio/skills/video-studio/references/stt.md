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
| **local** faster-whisper | yes (`word_timestamps=True`) | no | yes | free after model download | slower; accuracy drops hard outside major languages |

`transcribe.py` normalizes all three to the same JSON, so nothing downstream changes.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/vs.sh transcribe.py clip.mov --provider auto --audio-track 0
```

`auto` picks the first available: ElevenLabs key → OpenAI key → local install.

## Why Gemini is not in the list

Gemini reads video and audio well, but its audio documentation specifies segment timestamps in `MM:SS` — one-second granularity, with no word-level guarantee. At one-second resolution a cut lands up to half a word early or late, so it cannot be the timing source here.

If the user asks for Gemini specifically, explain this in one sentence and offer it for a different job: describing what is *visually* on screen. That is a real gap (the transcript only covers what is said), and it needs a `GEMINI_API_KEY`.

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
