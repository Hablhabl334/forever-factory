# 💜 Psychology of Love — the Forever Factory

**One YouTube channel. One machine. Runs itself daily, forever.**

Every day, on GitHub's servers, for free, the factory:

1. **Invents a brand-new psychology-of-love lesson from zero** — no
   content bank, no repeats: 24 topics × 40 real concepts, a
   variation layer (3 hooks × 3 example scenes × 3 takeaways) and
   slot-filled example casts recombine into **273,301,428,924,195,840
   distinct scripts (≈273 trillion)**. At 5 videos/day the first
   possible repeat is millions of years away — and a no-repeat ledger
   (story + short hashes) guarantees it.
2. **Paints fresh couple illustrations and quote cards** for every
   scene (pure Python/PIL — no image API, nothing to break), with a
   channel-locked couple the audience learns to recognize.
3. **Narrates it** with a free neural voice (`en-US-JennyNeural` via
   edge-tts — no key, no account) with per-sentence pace/pitch/pause
   jitter so it sounds human; if the endpoint is ever down, the
   vendored offline Piper voice takes over automatically.
4. **Composes an original mood-matched soundtrack** (numpy synth —
   zero copyright risk, zero licenses) that ducks under every spoken
   sentence.
5. **Renders a ~9-minute 1080p long video** — animated couple (sway,
   bob, blinks at 30 fps), Ken Burns motion, word-synced captions —
   plus **4 native vertical Shorts** (69–74 s, bold overlay text,
   blurred letterbox), with ffmpeg.
6. **Generates the thumbnail + all metadata** — search-first titles
   and keyword-loaded descriptions for longs, a fixed
   subscription-funnel title on Shorts, chapters parsed INTO the
   description, tags — plus the AI-SEO text layer: the narration
   uploads as a machine-readable caption track and a channel summary
   comment seeds every long (models don't watch videos, they read
   the text around them).
7. **Uploads everything once, scheduled to publish at the fixed grid
   (Africa/Cairo)**: Shorts at **00:00 / 06:00 / 12:00 / 18:00**, the
   long at **20:00**. Public times never move; when the machine runs
   is flexible.
8. **Remembers everything** in `data/state.json` (committed daily by
   the workflow, with a last-known-good `.bak`) — the schedule can
   never be disabled, the factory never repeats a script, and quota
   is tracked per Pacific day.

If a day fails: the failure auto-opens a GitHub Issue (email alert),
the next run **resumes the interrupted episode from the same seed**
(stories are pure functions of their seed, so nothing is ever
half-lost), and past-day failure issues auto-close once the machine
has healed itself.

## The only services it ever touches

| Service | Credential | Where |
|---|---|---|
| YouTube Data API v3 | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | GitHub repo secrets |
| GitHub Actions | the repo itself | free forever on a public repo |

No Gemini. No OpenAI. No paid APIs. No servers. Nothing that can
version-rot or rate-limit the machine into silence. The one external
clock (cron-job.org) just pings GitHub with a minimal-scope token.

## One-time setup (~20 minutes)

Follow **[RUNBOOK.md](RUNBOOK.md)** — the exact click-by-click for
the Google OAuth app (including the publish-the-app step that makes
the refresh token last forever), the three GitHub secrets, and the
external pinger. **[BLUEPRINT.md](BLUEPRINT.md)** is the complete
replication guide — every step from zero to this machine, written so
you can clone the whole setup for a new channel/niche.

## How the schedule defends itself

**9 staggered cron slots** (off-the-hour — GitHub starves on-the-hour
crons) **+ a watchdog** workflow with extra heartbeats that dispatches
the factory whenever the day hasn't been produced yet **+ an external
pinger** (cron-job.org, 19:00 + 19:25 UTC) that no GitHub starvation
can touch. Every extra trigger is caught by a cheap gate job (~15 s,
zero quota) that skips the run if today's work is done — so ~14 daily
chances, one production. The gate also watches the publish **grid**:
an unbooked future slot that expires before the next cycle is a hole
that triggers a heal run (up to 6 shorts/day capacity).

- **Actions → daily-factory → Run workflow** — full cycle now
  (tick *dry_run* to preview without uploading — side-effect-free)
- **Actions → verify-token → Run workflow** — check YouTube credentials
- **Actions → channel-check → Run workflow** — channel settings report
- **Actions → reconsent → Run workflow** — regenerate OAuth consent
- Locally: `python main.py --dry-run`

## How it gets found (the discovery layer)

- **Search-first long titles**: the phrase people actually type leads
  the title, rotated across long-tail frames.
- **Keyword-loaded descriptions** (first 150 chars carry the terms),
  real chapters, the binge line, the AI disclosure, hashtags.
- **The "Love Psychology Tips 💜" playlist** — every long lands in the
  public binge-loop playlist automatically.
- **Channel keywords** — set once via the API at rebrand time.
- **A daily growth report** — view counts for recent + top videos with
  day-over-day deltas, printed into `factory.log` and stored in the
  factory memory (bounded: recent 200 + top 100, so it never grows
  unbounded). This is the *research* half of the research → create →
  improve loop.

## Content policy — by design

General-audience relationship content: `madeForKids: false`, comments
open, honest **AI-assistance disclosure** (`containsSyntheticMedia`)
on every upload. Every script passes the same safety gate before any
art or audio is generated. All content is 100% original — the grammar
atom banks contain no copyrighted characters, franchises, or existing
works.

Custom thumbnails are phone-verification-gated by YouTube: until the
channel is verified (`youtube.com/verify`) `thumbnails.set` fails with
403; the factory treats that as non-fatal and retries on later cycles
(deterministic rebuild from the episode seed, flagged in the ledger so
a video is never touched twice).

## Repo layout

```
channel.yaml              the channel's DNA (name, niche, slots, counts)
main.py                   the daily entrypoint
src/content_data.py       the atom bank (topics, concepts, vocab)
src/content_variants.py   the variation layer (hooks/scenes/takeaways)
src/story_engine.py       generative grammar + safety gate + no-repeat ledger
src/art_engine.py         the locked couple + layered scene painter
src/anim.py               30 fps sprite animation (sway/bob/blink)
src/tts.py                edge-tts narration + Piper offline fallback
src/music.py              mood-matched seeded soundtrack (numpy)
src/render.py             resumable ffmpeg renderer (Ken Burns + captions)
src/shorts.py             native 9:16 Shorts (bold overlays)
src/thumbnails.py         auto thumbnails
src/metadata.py           titles, descriptions, chapters, tags
src/discovery.py          growth report, playlist, channel branding
src/youtube.py            OAuth + resumable upload + quota + grid booking
src/ledger.py             the factory memory (state.json + .bak ladder)
src/orchestrator.py       the daily conductor (idempotent, resumable)
tools/gate.py             the SKIP/RUN verdict (grid-aware, bulletproof)
tools/auth.py             one-time OAuth helper → forever refresh token
tools/close_resolved_issues.py   failure-issue auto-cleanup
assets/voice/             Piper voice model (vendored, offline fallback)
assets/fonts/             Baloo 2 / Archivo Black / Anton / Literata
.github/workflows/        daily-factory, watchdog, verify-token,
                          reconsent, channel-check
data/state.json           the memory (committed every day)
scripts/                  regression suites (durability, grid-heal, oct8)
```

## Tuning

Everything lives in **`channel.yaml`** — channel name, niche, voice
pace, publish slots, daily counts, quota budget, colors. Change the
numbers; the machine adapts. The niche content lives in
`src/content_data.py` + `src/content_variants.py`.

**For a brand-new channel**: read **[BLUEPRINT.md](BLUEPRINT.md)** —
the complete step-by-step replication guide (new OAuth app, new
secrets, memory reset, niche swap).
