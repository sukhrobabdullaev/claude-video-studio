# Building context before editing

An editor watches the rushes before touching anything. You cannot watch, but you have two things that together tell you more than a single viewing would: **the transcript** (everything that is said, with millisecond timing) and **the footage report** (everything measurable about the picture and sound).

Read both before asking the user anything. Questions asked from a position of knowledge get short useful answers; questions asked blind get "I don't know".

## 1. Run the measurements

```bash
V=${CLAUDE_SKILL_DIR}/scripts/vs.sh
bash $V transcribe.py <video> --provider auto --audio-track 0
bash $V vendor/pack_transcripts.py --edit-dir <dir>/edit
bash $V footage_report.py <video>
```

`footage_report.py` ends with a short "what this means for the edit" list — those lines are written to be acted on, not filed away.

## 2. Derive the context from the transcript

Read `takes_packed.md` and extract, in your head:

- **Topic and claim.** What is this video arguing or showing? Usually in the first two sentences.
- **Structure.** Where does the hook end, where does the demonstration start, where is the payoff, where is the call to action? Note the timestamps — this becomes the edit's skeleton.
- **Proper nouns and jargon.** Product names, tools, companies, technical terms. These are the words ASR gets wrong and the audience notices. List them with the timestamps where they occur.
- **Who speaks.** One person, an interview, a voiceover over screen capture.
- **What is on screen.** The words often say ("mana, ko'ryapsiz" — look, you can see). Cross-check by pulling a full-resolution frame at that moment.
- **Weak spots.** Repeats, false starts, a sentence that trails off, a word you cannot make sense of.

## 3. Look at a few real frames

Pull three or four full-resolution frames — the opening, one from each distinct section — and actually look at them. This is where you catch what neither the transcript nor the report can tell you: what the screen shows, whether the subject is framed badly, and **whether personal data is visible**.

```bash
ffmpeg -v error -ss 20 -i <video> -frames:v 1 -q:v 2 edit/verify/frame_020.jpg
```

Never judge legibility from a filmstrip contact sheet — downscaled thumbnails make readable screen recordings look like mush, and that misjudgement changes the entire plan.

## 4. Say what you understood, in three sentences

Then, and only then, talk to the user. Three sentences covering: what the video is, how it is built, and the two or three problems worth fixing. Concrete, with timestamps, in their language.

> "63 soniyalik vertikal video: 0–8s da siz gapirasiz, qolgani telefon bilan suratga olingan ekran demosi. Umumiy 7.2s jim joy bor, ovoz 15 dB past, oxirida bir jumla takrorlangan. Ekranda mijoz ismi va ichki domenlar ko'rinadi."

This does three jobs at once: it proves you looked, it lets them correct you cheaply, and it surfaces the problems while changing the plan is still free.

## 5. Ask only what the material cannot tell you

The transcript already told you the topic, so do not ask what the video is about. Ask the three things it genuinely cannot know:

1. **Who is this for?** (their followers, a client, a course audience — this drives pace and how much explanation stays in)
2. **What should the viewer do or feel afterwards?** (drives whether a CTA is built and what the hook promises)
3. **Anything that must be spelled a particular way, or must not appear?** (brand name, handle, a client's name, the personal data you just spotted)

Then confirm your list of ASR corrections: *"Men buni shunday tuzatdim: kodeksda → Codex'da, grafinaga → Grafana'ga. To'g'rimi?"* They are the only person who knows what they actually said.

## When something is genuinely unclear

If a word has low confidence and you cannot resolve it from context or from a frame, **ask**. If there is nobody to ask (a background run), leave the word out of the caption rather than burning a guess into the picture, and record it in the notes. A wrong word on screen is worse than a missing one — it is in their voice, permanently, and they did not say it.
