# 🌙 Moonberry Tales — the Forever Factory

**One YouTube channel. One machine. Runs itself daily, forever.**

Every day, on GitHub's servers, for free, the factory:

1. **Invents a brand-new bedtime story from zero** — no story bank, no
   repeats: a generative grammar recombines into
   **4,970,310,669,434,880 (≈5 quadrillion) unique stories**. At 2 per
   day, the first possible repeat is ~6.8 **trillion** years away, and
   a no-repeat ledger guarantees it.
2. **Paints fresh storybook art** for every scene (pure Python/PIL —
   no image API, nothing to break).
3. **Narrates it** with an offline neural voice (Piper, vendored in
   this repo) at a calm 130 wpm bedtime pace.
4. **Composes an original ambient soundtrack** (numpy synth — zero
   copyright risk, zero licenses).
5. **Renders a ~13-minute 1080p video** — Ken Burns motion, exact
   word-synced captions, title card, end card (ffmpeg, resumable).
6. **Cuts 3 vertical Shorts** from it (blurred-background letterbox,
   readable captions, title overlays).
7. **Generates the thumbnail + all metadata** — honest title,
   parent-focused description, chapters, tags.
8. **Uploads everything once, scheduled to publish at peak bedtime
   slots** (Cairo time): long videos 19:30 / 21:00, Shorts 13:00 /
   17:30 / 20:30.
9. **Remembers everything** in `data/state.json` (committed daily by
   the workflow) — the schedule can never be disabled, the factory
   never repeats a story, and quota is tracked (8,100 of 10,000 daily
   units by design).

If a day fails: the failure auto-opens a GitHub Issue (email alert),
and the next day's run **resumes the interrupted episode from the same
seed** — stories are pure functions of their seed, so nothing is ever
half-lost.

## The only services it ever touches

| Service | Credential | Where |
|---|---|---|
| YouTube Data API v3 | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | GitHub repo secrets |
| GitHub Actions | the repo itself | free forever on a public repo |

No Gemini. No OpenAI. No paid APIs. No accounts. No servers. Nothing
that can version-rot or rate-limit the machine into silence.

## One-time setup (~15 minutes)

Follow **[RUNBOOK.md](RUNBOOK.md)** — the exact click-by-click for the
Google OAuth app (including the publish-the-app step that makes the
refresh token last forever) and the three GitHub secrets.

## Run it

The schedule runs itself daily at 10:00 UTC (uploads land in the Cairo
evening peaks). Manual runs:

- **Actions → daily-factory → Run workflow** — full cycle now
  (tick *dry_run* to preview without uploading)
- **Actions → verify-token → Run workflow** — check YouTube credentials
- Locally: `python main.py --dry-run`

## Made for Kids — by design

Bedtime stories for children are child-directed content, so every
upload sets **`madeForKids: true`** and the honest **AI-assistance
disclosure** (`containsSyntheticMedia`). Stories pass an automated
safety gate (brand names, scary words, adult themes) before any art or
audio is generated — the gate regenerates a fresh story rather than
publishing a risky draft. Every story is 100% original: the grammar
atom bank contains no copyrighted characters, franchises, or existing
tales.

**Comments are off — and that is the right state, not a limitation.**
YouTube itself disables comments on every made-for-kids video (COPPA
rule), so there is no "kids flag + comments on" combination to choose.
Enabling them would mean declaring this content *not* made for kids —
false for bedtime stories aimed at 5–8-year-olds, and a real
FTC-mislabeling and channel-termination risk. It would also buy
nothing: sleep content is played at lights-out by parents; its growth
engines are average view duration, nightly repeat views, and playlist
adds, while comment sections on bedtime videos stay empty. Likes,
subscribes, and playlist adds all still work — those are the signals
to watch in YouTube Studio.

Custom thumbnails are phone-verification-gated by YouTube: until the
channel is verified (`youtube.com/verify`) `thumbnails.set` fails with
403. The factory treats that as non-fatal and retries every daily
cycle until it succeeds once per video (deterministic rebuild from the
episode seed, 50 quota units per attempt, flagged in the ledger so a
video is never touched twice).

## Repo layout

```
channel.yaml              the channel's DNA (name, pace, slots, counts)
main.py                   the daily entrypoint
src/story_data.py         the atom bank (12 grammar dimensions)
src/story_engine.py       generative grammar + safety gate + ledger
src/characters.py         24 procedural storybook animals (PIL)
src/art_engine.py         layered scene painter (12 palettes, 14 scene types)
src/tts.py                Piper narration with exact per-sentence captions
src/music.py              seeded ambient soundtrack (numpy)
src/render.py             resumable ffmpeg renderer (Ken Burns + captions)
src/shorts.py             9:16 auto-cut Shorts (blurred letterbox)
src/thumbnails.py         auto thumbnails
src/metadata.py           titles, descriptions, chapters, tags
src/youtube.py            OAuth + resumable upload + quota + scheduling
src/ledger.py             the factory memory (state.json)
src/orchestrator.py       the daily conductor (idempotent, resumable)
tools/auth.py             one-time OAuth helper → forever refresh token
assets/voice/             Piper voice model (vendored, 63 MB)
assets/fonts/             Baloo 2 (OFL) captions font
.github/workflows/        daily-factory.yml + verify-token.yml
data/state.json           the memory (committed every day)
```

## Tuning

Everything lives in **`channel.yaml`** — channel name, story words,
voice pace, publish slots, daily counts, quota budget, colors. Change
the numbers; the machine adapts. The niche and grammar live in
`src/story_data.py`.
