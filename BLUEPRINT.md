# 🏭 THE FOREVER FACTORY BLUEPRINT
### From zero to a self-running YouTube channel — the complete replication guide

> **What this is**: the full record of how this machine was built — every
> step, every decision, every fix from beginning to today — plus the exact
> recipe to clone the whole setup for a **new channel**. You change the
> *category/niche*; everything else (auto-upload, GitHub automation, the
> external clock, the self-healing schedule) stays identical.
>
> **Machine status at packaging time (2026-10-12)**: running clean.
> 16 days active, 72 videos published, 3 consecutive 100%-green days,
> 0 open failure issues, all regression suites passing. Zero dollars
> spent, zero paid APIs, zero servers.

---

## Part 0 — What is in this package

```
forever-factory/
├── BLUEPRINT.md          ← you are here (also in the repo)
├── README.md             the machine's own manual (current niche)
├── RUNBOOK.md            the full history — Parts 1-11, click-by-click
├── channel.yaml          the channel's DNA — THE config file
├── main.py               the daily entrypoint
├── src/                  the whole content/render/upload engine
├── tools/                gate, OAuth helper, issue cleanup, checks
├── scripts/              the 3 regression test suites
├── assets/               fonts + the offline Piper voice (63 MB)
├── .github/workflows/    the 5 automation workflows
├── data/state.json       the factory memory (this channel's history)
├── data/state.json.bak   last-known-good memory copy
├── factory.log           the latest cycle's log (growth report inside)
└── extras/
    └── oauth-callback.html  the GitHub Pages OAuth callback page
                              (deploy this on your new pages site)
```

**The machine in one paragraph**: every day at 19:00 UTC an external
clock (cron-job.org) pings a GitHub Actions workflow. A 15-second
gate job checks the factory's memory and decides SKIP (today is done)
or RUN. A run invents a brand-new script from a generative grammar
(273 trillion combinations, zero repeats ever), paints original
illustrations, narrates with a free neural voice, composes an original
soundtrack, renders 1 long video + 4 vertical Shorts with ffmpeg,
uploads them to YouTube with `publishAt` scheduling (grid: 00:00 /
06:00 / 12:00 / 18:00 / 20:00 Cairo), commits its memory back to git,
and files a GitHub Issue if anything failed. Fourteen daily trigger
chances, one production, self-healing everything. Cost: $0/month.

---

## Part 1 — The complete story (beginning → now)

This is the timeline of how the machine came to be. Each entry is a
decision that still shapes the machine — read it once and you will
understand why every layer exists. (Full details live in RUNBOOK.md
Parts 1–11.)

| When | What happened | Why it still matters |
|---|---|---|
| Sep 2026 | **The origin**: an AI bedtime-story channel guide (research → create → improve loop, $3,000/month planning target — a plan, not a promise) | The whole design goal: a channel that runs *daily* without a human |
| Sep 25 | **Build A — "perpetual machine" v0**: 4 videos published via z-ai APIs | Proved the concept, then hit the wall: paid/API-dependent designs rot. Lesson learned: **no paid APIs** |
| Sep 26 | **Build B — the Forever Factory design**: generative grammar (no story bank), Piper TTS (offline), procedural PIL art, numpy music, all state in git | The architecture that survived: everything offline except YouTube upload + GitHub itself |
| Sep 27 | **Sandbox lost everything** (twice) — the machine was rebuilt from the shared chat log each time | Why all state lives in **git** (GitHub), never on one machine. The repo IS the machine |
| Sep 28 | **The OAuth forever-token trick**: Google Cloud OAuth app **published to production** with the GitHub Pages site in branding → refresh token never expires | The single most important setup step (Part 4 below). Unpublished "testing" tokens die in 7 days |
| Sep 29 | **GitHub cron starvation discovered**: on-the-hour crons got dropped 3 days straight | Why all 9 cron slots are off-the-hour (11, 23, 41, 13, 19, 31, 37 past) |
| Sep 30 | **The external clock**: cron-job.org pinger at 19:00 + 19:25 UTC with a minimal-scope fine-grained PAT | GitHub can starve any internal schedule; an external ping makes the start deterministic |
| Oct 1 | **The niche change**: kids bedtime stories → **psychology of love** (24 topics × 40 concepts), new visual design, 1 long + 4 native Shorts, fixed Shorts title as subscription funnel | Proof the machine is niche-portable — the exact path you will repeat for your next channel |
| Oct 1 | **Three upgrades**: variation layer (273-trillion no-repeat space, every short hash ledgered), neural voice (edge-tts, free), mood-matched music with voice ducking | The content quality layer — all free, all offline-capable |
| Oct 2 | **The living couple upgrade**: 30 fps animation (sway/bob/blink), channel-locked character pair, human voice jitter (pace + pitch + pause), broadcast polish | Viewer feedback drove quality: text readable from across the room, characters that breathe |
| Oct 3 | **The double-production race fixed**: dispatch + delayed cron both rendered the same day — checkout now reads `ref:main` (fresh state), concurrency group queues duplicates | Why every checkout pins `ref: main`, never the event SHA |
| Oct 6–7 | **Quota + rolling upload limits hit**: honest deferral system built (real reason named in logs, 2h back-off, partial-quota production) | The machine survives YouTube's limits by *deferring honestly*, not by failing blindly |
| Oct 8 | **The self-healing grid**: gate watches the publish grid (not just the clock) — an unbooked slot that expires before the next cycle is a HOLE that triggers a heal run; cycles book what the grid owes (up to 6 shorts) | The Oct 8 18:00 hole taught the machine to heal itself — 4 shorts + 1 long every day, guaranteed |
| Oct 8 | **The five-year durability audit**: 6 silent-death holes found and fixed — gate-crash alerting, `.bak` memory ladder, bounded analytics, `[auth] CREDENTIALS REJECTED` banner, exactly-pinned dependencies, auto-closing failure issues | The machine is now contracted for years: every failure is loud, every alert self-heals, nothing grows unbounded |
| Oct 13 | **The voice incident**: the neural TTS endpoint refused the runner's IP range; the offline fallback counted as SUCCESS — two robotic days shipped silently. Fixed: edge-tts range-pinned (>=7.3.1,<8), patient multi-voice probe, voice-degraded cycles FAIL before upload so backup slots retry on fresh runner IPs, and a "Voice degraded" Issue fires the moment quality drops | The blueprint's loudest lesson: **availability is not quality**. A fallback that silently succeeds is worse than a failure — make every quality regression as loud as an outage |
| Oct 16 | **The viral upgrade**: the voice went fully LOCAL — Kokoro-82M vendored in the repo (~120 MB, MIT, CPU ~2x realtime, no API/network at all, af_heart); hooks engineered for the algorithm (every Short opens with a 2-6 word pattern interrupt + closes with a comment-bait question; longs + descriptions carry it too); shorts pacing tightened (9-word karaoke cards, ~2.5 s rhythm, word band recalibrated to the measured 150 wpm) | Three growth levers with one theme: **own the whole stack**. The voice can never go dark; the first two seconds and the comment section — the two signals the Shorts feed actually ranks on — are now scripted, offline, forever |
| Oct 9–12 | **Clean operation**: 3+ consecutive 100%-green days, all cycles producing 4 shorts + 1 long, auto-closing old issues, memory committing nightly | The proof state — this is what "working" looks like in the Actions tab |

**The five design laws** (everything above collapses into these):

1. **No paid APIs. No accounts that can bill you. No servers.** The
   only external dependencies are YouTube Data API v3 (free quota),
   GitHub Actions (free for public repos), and one external ping.
2. **The repo is the machine.** All memory lives in git. Any computer
   (or none) can die; clone the repo and the machine continues.
3. **Every failure is loud.** Any crash opens a GitHub Issue (email).
   Any silence is treated as a bug (that was audit finding #1).
4. **Every trigger is cheap.** 14 daily chances to run, one production;
   duplicate triggers cost a 15-second gate SKIP and zero quota.
5. **Nothing grows forever.** Memory bounded, analytics bounded,
   issues auto-close, dependencies pinned. A machine that grows is a
   machine that dies.

---

## Part 2 — Replication: the 13 steps (new channel, new niche)

> Budget: **~60–90 minutes** of clicking (plus 1–2 evenings if your new
> niche needs a fresh concept bank — see Step 7). Money: **$0**.
> Keep this open next to RUNBOOK.md Parts 1–6 (they have screenshots
> of the Google Cloud pages).

### Step 1 — Create the new YouTube channel (~5 min)

1. Sign into YouTube with the Google account that will own the new
   channel (or create a **Brand Account** — recommended: keeps your
   personal account separate and lets you add managers later).
2. Create the channel: profile photo, channel name, handle.
3. **Verify the channel now** → `https://youtube.com/verify` (any
   phone number). This unlocks custom thumbnails — without it, every
   `thumbnails.set` call fails with 403 (the machine survives it and
   retries on later cycles, but verifying now saves days of plain
   auto-thumbnails).
4. Leave settings default for now — the machine sets title,
   description and keywords itself on the first cycle (channel
   branding pass).

### Step 2 — Create the GitHub repo and push this code (~10 min)

1. New public repo on GitHub (e.g. `yourname/forever-factory`).
   **Public matters**: free unlimited Actions minutes. (Private repos
   get 2,000 min/month — a ~25-min daily render = ~750 min/month, it
   fits, but public is the comfortable forever choice. Public is safe:
   **no secrets live in the repo**, only in GitHub Secrets.)
2. Push this package's `forever-factory/` folder as the initial commit:
   ```bash
   cd forever-factory
   rm -rf .git            # if you cloned with history — start YOUR history
   git init
   git add -A
   git commit -m "the forever factory, first light"
   git remote add origin https://github.com/YOURNAME/forever-factory.git
   git push -u origin main
   ```
   (Push from the ZIP's folder — it contains no `.git`, so skip the
   `rm -rf .git` line.)

### Step 3 — The OAuth callback page on GitHub Pages (~5 min)

Google needs a real HTTPS redirect page for the OAuth flow (the old
"desktop app" flow is dead). You already own the page — deploy it:

1. Create a second repo named `yourname.github.io` (a GitHub Pages
   site). Enable Pages: Settings → Pages → Deploy from branch → main.
2. Put `extras/oauth-callback.html` in it as
   `oauth/callback/index.html`. Edit the page title if you like
   (cosmetic only — the logic is generic: it reads the `code=` from
   the URL and shows it with a copy button).
3. Your redirect URI is now
   `https://yourname.github.io/oauth/callback` — write it down, you
   need it in Step 4. Test it in a browser (it should render the
   dark "Factory connection" page, even with no code).

### Step 4 — The Google Cloud OAuth app, WITH the forever trick (~10 min)

> This is RUNBOOK Part 1 verbatim. The **PUBLISH APP** step at the end
> is what makes your refresh token live forever — do not skip it.

1. `https://console.cloud.google.com` → sign in with the account that
   owns the channel → **New project** (name it anything, e.g.
   `factory-<niche>`).
2. **APIs & Services → Library → YouTube Data API v3 → Enable.**
3. **APIs & Services → OAuth consent screen**:
   - User type: **External** → Create
   - App name: anything (e.g. `Factory`)
   - User support email: your Gmail
   - **App home page**: `https://yourname.github.io`
   - Developer contact: your Gmail
   - Scopes → Add or remove scopes → tick
     `.../auth/youtube.upload` and `.../auth/youtube.readonly`
   - Test users → add your own Gmail
4. 🚀 **PUBLISH THE APP**: consent screen → Publishing status →
   **PUBLISH APP** → confirm. *(Testing status = tokens die after 7
   days. Published = the refresh token survives indefinitely for your
   own account's daily use.)*
5. **Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**
   - Authorized JavaScript origins: `https://yourname.github.io`
   - Authorized redirect URIs:
     `https://yourname.github.io/oauth/callback`
   - Create → **Download JSON** → keep it, it holds `client_id` +
     `client_secret`.

### Step 5 — Get the forever refresh token (~3 min)

Run the helper **on any computer with Python 3** (no other setup):

```bash
cd forever-factory
python3 tools/auth.py
```

1. Paste `client_id` and `client_secret` when asked.
2. Open the printed link → sign in with the channel's Google account →
   **Allow**. (A "app not verified" warning is normal for your own
   app — Advanced → Go to your app.)
3. You land on your callback page → **Copy code** → paste it back.
4. It prints the **refresh token** (`1//...`).

### Step 6 — Give the machine its keys (~3 min)

GitHub repo → **Settings → Secrets and variables → Actions → New
repository secret**, three times:

| Secret name | Value |
|---|---|
| `YT_CLIENT_ID` | the client_id |
| `YT_CLIENT_SECRET` | the client_secret |
| `YT_REFRESH_TOKEN` | the `1//...` refresh token |

### Step 7 — The niche swap: point the machine at your new category

This is the **only creative work** in the whole replication. Three
layers, in order of importance:

**(a) The content bank — `src/content_data.py`** (the real work).
The current niche (love psychology) is 24 topics × 40 concepts, each
concept being a short structured explanation (mechanism, plain words,
relatable example, healthy takeaway). To change category:

- Replace `TOPICS` with ~24 umbrellas of YOUR niche (each: a long
  title phrase, a shorts band label, an opener hook, 8 concept keys).
- Replace `CONCEPTS` with ~40 real concepts in your field
  (knowledge work: this is a day of focused writing — or a session
  with any AI assistant — but **you must fact-check every concept**;
  this channel's trust comes from real psychology, not invented
  facts).
- Update `SERIES_NAME` and `CTA_LINE`.

**(b) The channel DNA — `channel.yaml`** (~10 min). Change:
`display_name`, `handle`, `niche`, `audience`, `promise`,
`description`, the `discovery:` block (playlist title/description,
channel keywords, channel description), and the shorts `fixed_title`
+ `fixed_tags`. Keep **everything else identical** — schedule,
quota, voice, render, counts (unless you deliberately want changes).

**(c) The visual layer — `src/art_engine.py`** (honest scope note).
The current art draws a **channel-locked couple** (two characters the
audience learns to recognize) + bold quote cards. For niches in the
same visual genre (relationships, advice, psychology, motivation,
life-tips), this works as-is or with palette/prop tweaks. For a
visually different niche (e.g. fitness, cooking, tech), the card/text
system works but the characters need a redesign — budget an evening
or ask your AI assistant for a redraw of the sprite builders in
`art_engine.py` + `src/anim.py` keeps working with any sprites.

> **Speed cheat**: for a first new channel, you can launch with the
> visual layer untouched (quote cards alone carry fine) and redesign
> characters later — the machine rebrands visuals only going forward,
> old videos stay as history.

### Step 8 — Reset the factory memory (fresh start) (~2 min)

The packaged `data/state.json` carries THIS channel's history
(episode numbers, used script hashes, analytics). For a new channel,
give it a clean mind — delete the memory and its backup:

```bash
rm data/state.json data/state.json.bak
```

The machine rebuilds a fresh memory on the first run (episode 1,
empty no-repeat ledgers — full 273-trillion space ahead). Don't worry
about the `.gitignore`-less delete: the first cycle re-creates both
files and commits them.

*(Optional — cross-channel no-repeat: keep the old file instead and
the new channel will also avoid the ~50 scripts your first channel
already used. Rarely worth the confusion; deleting is cleaner.)*

### Step 9 — First run: dry, then real (~5 min + ~25 min)

1. Repo → **Actions → daily-factory → Run workflow** → tick
   **dry_run** → Run. Watch the job: it produces a full episode and
   prints the upload plan without touching YouTube. First run takes
   ~20–30 min (pip install + one render).
2. If green: **Actions → daily-factory → Run workflow** (no tick).
   This is the real first episode — it uploads and schedules the
   whole first grid.
3. **Actions → verify-token → Run workflow** → green = credentials
   healthy.
4. Check YouTube Studio: videos appear as scheduled (00:00 / 06:00 /
   12:00 / 18:00 / 20:00 Cairo), channel title/keywords get set by
   the branding pass on the first cycle, the playlist appears.

### Step 10 — The external clock (cron-job.org) (~5 min)

> RUNBOOK Part 6 verbatim. This is what makes the day start
> deterministic — GitHub's internal cron is best-effort only.

1. GitHub → avatar → Settings → Developer settings → **Fine-grained
   tokens** → Generate new token:
   - Name `factory-pinger`, expiration **No expiration**
   - Repository access: **Only select repositories** → your
     forever-factory repo
   - Permissions: **Actions → Read and write** ONLY (the token can
     merely start workflows — it cannot read secrets or edit files)
2. Create a free **cron-job.org** account, add the job:
   - URL: `https://api.github.com/repos/YOURNAME/forever-factory/actions/workflows/daily-factory.yml/dispatches`
   - Method: POST
   - Headers: `Authorization: Bearer github_pat_YOUR_TOKEN`,
     `Accept: application/vnd.github+json`,
     `Content-Type: application/json`
   - Body: `{"ref":"main"}`
   - Schedule: every day at **19:00 UTC**
3. (Optional but recommended — the backup ping): duplicate the job at
   **19:25 UTC**.
4. Save. Next day: a workflow_dispatch run appears at 19:00 UTC —
   that's your clock, live.

### Step 11 — The reconsent: playlists + channel keywords (1 click)

The base consent (upload + readonly) is enough to run. The **playlist
binge-loop** and **channel keywords** need the broader scope set
(already coded in `tools/auth.py`):

1. **Actions → reconsent → Run workflow** (no inputs) — the run log
   prints a consent link (built from the repo's own
   `YT_CLIENT_ID`).
2. Open it, Allow, copy the code from the callback page.
3. **Actions → reconsent → Run workflow** again, paste the code into
   the `code` input → the workflow exchanges it and updates the
   `YT_REFRESH_TOKEN` secret itself. From the next cycle, every long
   video lands in the public playlist automatically.

### Step 12 — Enable + verify the whole defense stack (~5 min)

1. **Actions tab**: all 5 workflows should be enabled (they come with
   the repo — check each is not accidentally disabled).
2. Repo → Settings → Actions → General → **Workflow permissions** →
   *Read and write permissions* (the memory commit needs it) — the
   workflows also declare `permissions:` inline, but flip this if a
   memory commit ever fails with a push error.
3. Next morning check: Actions shows yesterday's production run +
   several cheap SKIPs (green), cron-job.org shows 2 green pings,
   no open Issues. That's the machine breathing.

### Step 13 — The final checklist (tick every line)

- [ ] Channel created + **verified** (youtube.com/verify)
- [ ] Repo public, code pushed, Actions tab shows the 5 workflows
- [ ] Pages site live, `https://yourname.github.io/oauth/callback`
      renders the connection page
- [ ] OAuth app **PUBLISHED** (not testing!) — consent screen shows
      "In production"
- [ ] 3 secrets set (client id / client secret / refresh token)
- [ ] Niche swapped (content_data.py + channel.yaml + optionally art)
- [ ] Memory reset (`rm data/state.json*`)
- [ ] Dry run green
- [ ] First real run green — videos scheduled on the grid
- [ ] verify-token green
- [ ] cron-job.org pinger live (2 jobs: 19:00 + 19:25 UTC)
- [ ] reconsent done → playlist + channel keywords active
- [ ] Day 2 arrived on its own (a green 19:00 UTC dispatch run)

**Done. From here the machine runs itself. You are now a channel
owner whose daily job is watching one dashboard — and even that is
optional: failures email you.**

---

## Part 3 — The change-map: what changes vs. what stays identical

| Component | New channel? | Action |
|---|---|---|
| YouTube channel + verification | ✅ new | Step 1 |
| GitHub repo (this code) | ✅ new repo | Step 2 — code identical |
| OAuth callback page (GitHub Pages) | ✅ new site | Step 3 — same page file |
| Google Cloud project + OAuth app | ✅ new app | Step 4 — **PUBLISH it** |
| Refresh token + 3 repo secrets | ✅ new values | Steps 5–6 — same names |
| `src/content_data.py` (topic/concept bank) | ✅ **new niche** | Step 7a — the real work |
| `channel.yaml` branding fields | ✅ new values | Step 7b — everything else identical |
| `src/art_engine.py` visuals | ⚠️ maybe | Step 7c — same genre = as-is |
| Factory memory (`data/state.json`) | ✅ reset | Step 8 |
| Publish grid (00/06/12/18 + 20:00 Cairo) | ❌ identical | owner's hard contract |
| Daily output (1 long + 4 Shorts, ≤6 heal) | ❌ identical | — |
| Voice (JennyNeural + Piper fallback) | ❌ identical | — |
| Music, render, captions, thumbnails | ❌ identical | — |
| All 5 workflows + gate + watchdog | ❌ identical | — |
| Quota math + defer/heal logic | ❌ identical | — |
| cron-job.org pinger config | 🔁 new URL + PAT | Step 10 — same times |
| RUNBOOK knowledge | ❌ identical | your manual, forever |

---

## Part 4 — How the machine works (reference card)

### The daily cycle (a RUN verdict)

```
19:00 UTC  cron-job.org pings GitHub (workflow_dispatch)
   └─ gate job (~15 s, zero quota): read state.json →
        today already produced? → SKIP (costs nothing)
        grid hole expiring before next cycle? → RUN (heal)
        20h window open + evening? → RUN (produce)
   └─ build job (~25 min):
        1. ledger.load() — state.json → .bak → fresh (never dies)
        2. growth report — per-video views, day-over-day deltas
        3. story_engine — pick topic + concepts, drift until
           every script hash is provably new (273-trillion space)
        4. safety gate — regenerate on any risky word
        5. tts — edge-tts neural voice (jittered pace/pitch/pause),
           broadcast polish; Piper offline if the endpoint is down
        6. music — mood-matched pads + arpeggio, ducks under speech
        7. art + anim — locked couple sprites, sway/bob/blink 30 fps
        8. render — ffmpeg long (1080p, captions) + 4 Shorts (9:16)
        9. youtube.py — OAuth refresh, resumable upload, publishAt
           grid booking, per-upload quota check + honest defers
       10. ledger.save() — atomic write + .bak refresh
       11. git commit memory (+ factory.log) → push (rebase-safe)
       12. close past-day failure issues (best-effort)
   └─ any failure → GitHub Issue → email to you
```

### The schedule defense stack (why the day cannot be missed)

1. **External pinger** — cron-job.org, 19:00 UTC (outside GitHub
   entirely; GitHub cannot starve it)
2. **External backup ping** — 19:25 UTC
3. **9 GitHub cron slots** — 19:11, 19:23, 19:41, 20:13, 21:19,
   22:31, 23:37 + morning 05:23 + midday 12:29 UTC (all off-the-hour)
4. **Watchdog** — 19:49–23:49 hourly + 05/08/11/14:23 beats, each
   dispatches the factory if the day isn't produced
5. **Gate** — makes every duplicate trigger free (SKIP = 15 s, no
   quota) and every hole loud (grid-hole detection)

A day can only be missed if all 14+ chances fail on the same day —
and then an Issue tells you about it anyway.

### The memory (state.json)

- `episodes[]` — every episode: title, seed, hash, video IDs, status
- `story_hashes` / `short_hashes` — the no-repeat ledgers
- `slots` — the Cairo publish grid (what's booked, what's owed)
- `quota` — units used today (rolls at Pacific midnight, like
  YouTube's real window)
- `analytics` — growth snapshots, bounded (recent 200 + top 100)
- `.bak` twin — last known good, committed with every memory push;
  load ladder: `state.json → .bak → fresh`

---

## Part 5 — Zero-maintenance contract (what you'll ever do)

### Never (the machine handles it)

Quota exhaustion (defers, resumes after Pacific midnight) · rolling
upload limits (2h back-off) · a failed cycle (next slot resumes the
episode from the same seed) · transient API errors (retried) ·
duplicate triggers (gate SKIPs) · grid holes (heal run books them) ·
old failure issues (auto-closed) · memory corruption (.bak ladder) ·
voice endpoint down (Piper fallback) · repo inactivity (daily commits
keep the scheduler alive).

### The annual 5-minute ritual (set a yearly reminder)

1. **Actions → verify-token → Run workflow** — green = credentials
   healthy (also do this after any Google password change).
2. Log into **cron-job.org** once — both jobs should show green
   history.
3. Glance at **open Issues** — anything still open needs a human.
4. Glance at **Actions usage** — healthy month ≈ 1,500–2,500 min.

### The only things that can ever need a human (with fixes)

| Failure | Symptom | Fix |
|---|---|---|
| Refresh token revoked (Google password change etc.) | `[auth] CREDENTIALS REJECTED` in factory.log + failed runs | Steps 5–6 again (~10 min) |
| cron-job.org account dead | no more 19:00 dispatch runs (GitHub slots still cover) | Step 10 again (~5 min) |
| GitHub changes an action major (some year) | gate alert, all runs fail loudly | bump `actions/checkout@v4` → `@v5` etc. (~1 min) |
| YouTube Data API v3 sunset (unlikely, years away) | uploads fail | migration project |

### Known cosmetic edges (accepted, not bugs)

- **DST flip days** (Egypt, late Oct / late Apr): one slot can
  publish an hour off, once; the grid self-corrects the next day.
- **GitHub cron drift**: scheduled slots fire ±30 min or skip under
  load — that's exactly why the pinger + watchdog exist.
- **Bounded analytics detail**: videos beyond recent-200 + top-100
  contribute to totals but not per-video rows; snapshots age out at
  60 days.

---

## Part 6 — Exact settings snapshot (as running today, 2026-10-12)

The reference in case you ever want to diff "what did the working
machine look like".

| Setting | Value |
|---|---|
| Channel | Psychology of Love (`@PsychologyOfLove`), category_id 24 |
| Niche | love-psychology — 24 topics × 40 concepts |
| Daily output | 1 long (~9 min) + 4 Shorts (45–90 s), heal capacity 6 |
| Publish grid (Cairo) | Shorts 00:00 / 06:00 / 12:00 / 18:00 · long 20:00 |
| Cycle time | 19:00 UTC (22:00 Cairo) + 13 backup triggers |
| Voice | PRIMARY: Kokoro-82M local (vendored `assets/voice_kokoro/`, af_heart, speed 0.96, jitter 4.5) · BACKUP: edge-tts `en-US-JennyNeural` · LAST RESORT: Piper `en_US-lessac-medium` (loud, retried) |
| Music | numpy synth, −23 dB bed, 0.55 duck depth, mood-matched |
| Video | 1080p30, CRF 21 veryfast, Ken Burns overscan 1.25 |
| Shorts | 1080×1920, fixed title "Subscribe for more tips like this" |
| Quota budget | 10,000 units/day, 1,600/video, ledger per Pacific day |
| YouTube flags | madeForKids false · synthetic media disclosure ON · public |
| Secrets | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| External clock | cron-job.org × 2 (19:00 + 19:25 UTC) + `factory-pinger` fine-grained PAT (Actions R/W only) |
| Workflows | daily-factory (gate+build), watchdog, verify-token, reconsent, channel-check |
| Deps | numpy 2.5.3 · Pillow 12.3.0 · PyYAML 6.0.3 · piper-tts 1.8.0 (exact pins) · edge-tts >=7.3.1,<8 (living range — Microsoft rotates the TTS token scheme; the range self-heals) |
| Content space | 273,301,428,924,195,840 distinct scripts, hash-ledgered |
| Combination claim | "the factory never repeats" — mathematically for millions of years |
| Cost | $0.00/month — free API quota + free public-repo Actions |

---

## Part 7 — Quick troubleshooting

| Symptom | Meaning | First move |
|---|---|---|
| Run says `SKIP ... last cycle 0.xh ago` | normal — the day is done | nothing |
| `SKIP ... 20h window` | normal — evening cycle already ran | nothing |
| `RUN ... grid hole` | a slot needs healing | watch it produce |
| `uploads deferred (quotaDailyLimitExceeded)` | quota spent | auto-resumes next Pacific day |
| `uploads deferred (uploadLimitExceeded)` | rolling upload limit (burst) | auto-resumes ~2h |
| `[auth] CREDENTIALS REJECTED` | dead refresh token | Steps 5–6 of Part 2 |
| `[memory] ... recovered from .bak` | state.json got corrupted (it self-healed) | run `verify-token`; if fine, ignore |
| Thumbnails "403 forbidden" | channel not phone-verified | `youtube.com/verify` once |
| No 19:00 UTC dispatch run | cron-job.org job failed | log into cron-job.org, check job |
| Everything failing at the gate | repo/checkout/action problem | read the gate-failure Issue, check Actions status page |
| `gh: command not found` in alerts | cosmetic (alert text only) | ignore — alert still files via API path in next cycle |
| `VOICE-ALERT` + "Voice degraded" Issue | neural TTS refused the runner IP (self-retried on fresh runners first) | usually self-heals next slot; if more than a day, RUNBOOK Part 12 |
| `VoiceQualityError ... aborting BEFORE upload` | the voice-degraded retry ring working as designed | nothing — the next slot re-attempts automatically |
| Videos sound robotic | the day exhausted `max_voice_retries` and shipped the offline voice | RUNBOOK Part 12 (a dry-run dispatch confirms recovery) |

**The golden rule**: when anything looks wrong, read
`factory.log` (committed every cycle) — the machine explains itself.
And RUNBOOK.md is the deep manual; this file is the map.

---

*Packaged 2026-10-12 by the machine's builder. The factory never
repeats; neither does the gratitude — thank you for building it with
me. ♥*

