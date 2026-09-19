# Video Studio for Claude Code

Drop a raw video into Claude Code and say **"edit this video"**. Claude looks at the footage, interviews you about what you want (hook, zooms, graphics, subtitles, music, loudness, cover) **in your own language**, confirms a plan, edits it, and proves the result with measurements before showing it to you.

Built for people who are not editors. You describe the outcome; Claude makes the technical decisions and reports them afterwards.

## What it does

- **Cuts** on word boundaries — dead air, stumbles, repeats, and false starts removed without ever slicing a word in half
- **Reframes and zooms** to kill dead space in phone footage
- **Subtitles** burned in, in the language actually spoken, with ASR mistakes corrected before rendering
- **Motion graphics** — labels, title cards, and highlight boxes that follow the subject on handheld footage
- **Sound** — an original music bed generated on the spot (no downloads, no licensing risk), ducked under the voice, with effects placed on real transitions
- **Cover / thumbnail** with text that survives the Instagram crop
- **16 quality checks** before delivery: no pops at cuts, loudness on target, captions in sync, personal data on screen flagged

## Requirements

- **macOS**
- **Claude Code** — the desktop app's Code tab or the `claude` CLI. The claude.ai chat cannot run this, because editing needs ffmpeg on your own machine.
- **ffmpeg** and **uv** (`brew install ffmpeg uv`) — the setup step checks and tells you
- An **ElevenLabs** API key with Speech-to-Text permission, for transcribing speech (paid per video)
- Optional: **Node 22+** for richer motion graphics via [HyperFrames](https://github.com/heygen-com/hyperframes). Without it, graphics fall back to a bundled renderer.

The editing engine itself is bundled — there is nothing else to clone.

## Install

```
/plugin marketplace add sukhrobabdullaev/claude-video-studio
/plugin install video-studio@video-studio
```

Restart Claude Code, then say:

> set up video studio

It checks what is missing, asks before installing anything, and gives you a terminal command for the API key so the key never passes through the chat. Setup is done when the check prints `READY`.

Updating later:

```
/plugin marketplace update video-studio
```

### Without GitHub

Copy this folder to the machine, then:

```
/plugin marketplace add /path/to/claude-video-studio
/plugin install video-studio@video-studio
```

### For a whole team

Commit this to a shared project repo's `.claude/settings.json` and Claude Code offers the plugin to everyone who trusts the folder:

```json
{
  "extraKnownMarketplaces": {
    "video-studio": {
      "source": { "source": "github", "repo": "sukhrobabdullaev/claude-video-studio" }
    }
  },
  "enabledPlugins": { "video-studio@video-studio": true }
}
```

For a Claude Team or Enterprise organization, an admin adds the same block under Organization settings → Plugins. Organization-distributed marketplaces must live in a private or internal repository.

## Using it

1. Put the video in a folder.
2. Open Claude Code there, or drag the video into the chat.
3. Say **"edit this video"** — or "make this a reel", "add subtitles", "make this professional".
4. Answer the questions, or say "you decide" and take the defaults.
5. Collect the result from `edit/`.

Everything is written to `<your video folder>/edit/`. Your original file is never modified. To continue an edit later, open Claude Code in the same folder — `edit/project.md` remembers every earlier decision.

## What's inside

```
.claude-plugin/marketplace.json
plugins/video-studio/
  .claude-plugin/plugin.json
  skills/video-studio/
    SKILL.md                    the workflow: look → interview → plan → edit → verify → deliver
    references/
      intake.md                 the interview, and the defaults for "you decide"
      cutting.md                cut rules that prevent silent damage
      graphics.md               HyperFrames and the bundled renderer, alpha handling
      audio.md                  mixing, ducking, loudness targets and why they are what they are
      quality-gates.md          the 16 checks
      troubleshooting.md        environment traps that fail silently
    scripts/
      setup.sh, doctor.sh       install and preflight
      vs.sh                     runs any bundled script with the right environment
      offsets.py                measures the real timeline (frame rounding drifts it)
      captions.py               frame-exact subtitles, no libass needed
      track_box.py              highlight boxes that follow handheld motion
      synth_audio.py            original music bed and sound effects
      mix.py                    ducked mix, mastering, level gates
      check_boundaries.py       audio pop detection
      cover.py                  cover art with crop-safe text
      to_prores.sh              transparent overlays that survive compositing
      vendor/                   bundled editing engine (video-use, MIT)
```

## Credits

The cutting and transcription engine in `scripts/vendor/` is [video-use](https://github.com/browser-use/video-use) by Browser Use, MIT licensed — the license is kept alongside it in `scripts/vendor/LICENSE-video-use`. Motion graphics can use [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen when installed.

## License

Not chosen yet. Until one is added, no reuse rights are granted for the original work in this repository; the bundled video-use files keep their own MIT license.
