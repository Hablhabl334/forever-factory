# RUNBOOK — one-time setup (≈15 minutes), then never again

This connects the factory to your YouTube channel with a refresh token
that does not expire (the trick: **publish the OAuth app to
production** with your website in the branding section).

You will need ~15 minutes and a browser. After this, the machine runs
itself daily and you never touch GitHub settings again.

---

## Part 1 — Create the YouTube API project (~10 min)

1. Go to **https://console.cloud.google.com** and sign in with the
   Google account that owns your channel.
2. Top bar → project dropdown → **New project**:
   - Name: `moonberry-factory`
   - Create (wait ~20 s), then select it.
3. **APIs & Services → Library** → search **YouTube Data API v3** →
   **Enable**.
4. **APIs & Services → OAuth consent screen**:
   - User type: **External** → Create
   - App name: `Moonberry Factory`
   - User support email: your Gmail
   - **App home page:** `https://hablhabl334.github.io`
     *(your GitHub Pages site — already live)*
   - **Developer contact:** your Gmail
   - Scopes → **Add or remove scopes** → tick:
     - `.../auth/youtube.upload`
     - `.../auth/youtube.readonly`
   - Save.
   - **Test users → Add users** → add your own Gmail.
5. 🚀 **The forever-token step — PUBLISH THE APP:**
   - On the consent screen page, find **Publishing status** →
     **PUBLISH APP** → confirm.
   - This is what makes the refresh token keep working indefinitely.
     Unpublished (testing) tokens die after 7 days — published ones
     do not.
6. **APIs & Services → Credentials → Create credentials →
   OAuth client ID**:
   - Application type: **Web application**
   - Authorized JavaScript origins:
     `https://hablhabl334.github.io`
   - Authorized redirect URIs:
     `https://hablhabl334.github.io/oauth/callback`
     *(this page is already live on your website — it shows your
     authorization code with a copy button)*
   - Create → **Download JSON** (the little download icon).
   - The JSON contains your `client_id` and `client_secret`.

> NOTE: use **Web application**, not "Desktop app". Google killed the
> old out-of-band (OOB) flow, and the callback page on your website is
> the modern replacement — already deployed for you.

## Part 2 — Get the forever refresh token (~2 min)

Send me the **client_id** and **client_secret** from that JSON and I
will build the connection link for you — or do it yourself:

```bash
cd forever-factory
python tools/auth.py
```

1. Paste `client_id` and `client_secret` when asked.
2. Open the printed link, sign in with the channel's Google account,
   click **Allow**.
3. You land on `hablhabl334.github.io/oauth/callback` — press
   **Copy code** and paste it back.
4. The tool prints your **refresh token** — a long string starting
   with `1//`.

> The Google page may warn "app not verified" — that is normal for
> your own app used only by your own account. Click
> *Advanced → Go to Moonberry Factory* to continue.

## Part 3 — Give the machine its keys (~2 min)

In the GitHub repo: **Settings → Secrets and variables → Actions →
New repository secret** (three times):

| Secret name | Value |
|---|---|
| `YT_CLIENT_ID` | the client_id |
| `YT_CLIENT_SECRET` | the client_secret |
| `YT_REFRESH_TOKEN` | the `1//...` refresh token |

(Or send them to me with push access and I'll set all three myself.)

## Part 4 — First run + verification (~5 min)

1. Repo → **Actions → daily-factory → Run workflow** — first run
   produces a full episode and uploads it (scheduled for the next
   publish slot).
2. **Actions → verify-token → Run workflow** — green = credentials
   healthy.
3. Done. Every day the cycle runs at **19:00 UTC (22:00 Cairo)** —
   two hours before the day's first Short goes public at midnight
   Cairo. Videos appear on the channel at **00:00 / 06:00 / 12:00 /
   18:00 Cairo (the four Shorts)** and **20:00 Cairo (the long)**;
   a late trigger takes the next slot instead of waiting.

## Part 5 — Optional: unlock playlists + channel keywords (1 click)

The original consent covers uploads + reads. Two growth features —
the **bedtime playlist** (the binge loop) and **channel keywords**
(channel-level search index) — need one broader scope. The factory
skips them gracefully (a one-line note in the daily log, uploads
unaffected) until you re-consent:

1. Trigger the **reconsent** workflow (Actions → reconsent → Run
   workflow, no inputs). The run log prints the consent link — the
   machine builds it from its own stored `YT_CLIENT_ID`, so no
   credentials are needed on your computer. Open it, click Allow —
   same flow as Part 2, same callback page.
2. Send me the code from the callback page. I dispatch the same
   workflow in *exchange* mode: it swaps the code for a new refresh
   token where the client credentials live (repo secrets) and
   returns it sealed in a sealed-box only I can open — nothing
   sensitive ever appears in a public log or the repo.
3. From the next cycle on, every long lands in the public
   "Bedtime Stories for Kids to Fall Asleep" playlist automatically.

The consent also grants read-only YouTube Analytics — the future
improve-loop (impressions, CTR, watch time per video, not just views).

---

## Everyday-zero maintenance

- **A day fails** → an Issue is auto-opened in the repo (you get an
  email). The next day retries and completes the interrupted episode.
  You do nothing.
- **Quota near the cap** → the ledger defers uploads to the next day
  automatically. You do nothing.
- **Want more/fewer videos** → edit `channel.yaml` →
  `daily: long_videos:` and `shorts: count:`. One commit.
- **Want different story flavor** → edit the atom banks in
  `src/story_data.py`. One commit.
- **Keep the schedule alive** → nothing to do: the workflow commits
  `data/state.json` every day, which keeps the repo (and the cron
  schedule) permanently active.

---

## Part 6 — The forever clock (external pinger, ~5 min once)

GitHub's own scheduler is *best-effort by design* — it can delay or
skip runs (new repos are starved hardest). The 9 staggered cron slots
+ watchdog already catch most days, but if you want **100%
deterministic daily starts**, put the clock outside GitHub. Free
forever with cron-job.org:

**Step 1 — a minimal-scope token (2 min)**
1. GitHub → click your avatar → **Settings** → Developer settings
   (bottom of the left menu) → **Fine-grained tokens** →
   "Generate new token".
2. Name it `factory-pinger`. Expiration: **No expiration** (or 1 year
   and put a reminder to rotate it). Repository access:
   **Only select repositories** → `forever-factory`.
3. Permissions → **Actions → Read and write**. Nothing else — this
   token can ONLY start workflows, it cannot read secrets, edit
   files, or touch any other repo.
4. Generate, copy the `github_pat_...` value.

**Step 2 — the external clock (3 min)**
1. Create a free account at **cron-job.org** (email + password).
2. Add job, exactly:
   - **URL:** `https://api.github.com/repos/Hablhabl334/forever-factory/actions/workflows/daily-factory.yml/dispatches`
   - **Method:** POST
   - **Headers:** `Authorization: Bearer github_pat_YOUR_TOKEN` and
     `Accept: application/vnd.github+json` and
     `Content-Type: application/json`
   - **Body:** `{"ref":"main"}`
   - **Schedule:** every day at **19:00 UTC** (22:00 Cairo in summer
     — two hours before the first Short of the new day goes public
     at midnight, so the machine finishes producing with headroom).
3. Save. Done — the day now starts on an external clock that never
   starves.

> Already set up for you (2026-09-30): the two live jobs fire at
> **19:00 UTC** (primary) and **19:25 UTC** (backup). If you rebuild
> them by hand, those are the times.

Why this is safe: the dispatch is **gated by default** — if the day
was already produced, a duplicate ping costs one 9-second skipped
run and zero YouTube quota. Even if the token leaked, the worst
case is someone *starting* a workflow that immediately skips.

**Belt and suspenders, the full stack:** external pinger (19:00 UTC)
+ external backup ping (19:25 UTC) → 9 GitHub cron slots (evening
  window + morning recovery) → watchdog heartbeats → auto-Issue if a
  cycle ever fails. Five independent layers; a day can only be missed
  if all of them fail on the same day.

---

## Part 7 — The niche change (2026-10-01, done)

The channel pivoted from kids bedtime stories to **psychology of
love** (tips, breakups, attachment, self-worth). What changed:

- **Content engine**: 24 topics × 40 real psychology concepts,
  combinatorial scripts, same no-repeat ledger as before.
- **Design**: flat webtoon-lite couple illustrations + bold quote
  cards, matching the reference channel's look (black title band on
  Shorts, bold stroked text overlays, #9B59B6 brand purple).
- **Daily output**: **1 long (~9 min) + 4 native vertical Shorts**
  (was 2 longs + 3 cut Shorts).
- **Publish grid (Cairo)**: Shorts at **00:00 / 06:00 / 12:00 / 18:00**
  (every 6 hours), the long at **20:00**. The cycle runs at **22:00
  Cairo**, 2 hours before the first Short.
- **Shorts carry a FIXED title** — `Subscribe for more tips like this`
  — and fixed tags `#psychology #relationship #love
  #relationshipgoals` (the owner's growth strategy).
- **Not made for kids → comments open** (channel defaults; flip in
  Studio → Settings → Community if any video ever shows them off).
- **Channel rebrand**: the first cycle after the change sets the
  channel title to *Psychology of Love* + new keywords + the
  *Love Psychology Tips 💜* playlist.
- The 22 kids videos stay on the channel as history (delete them in
  YouTube Studio if you prefer a clean slate — the machine never
  touches them).

Everything else is the same machine: free voice + PIL art + numpy
music (all layers below), GitHub Actions, memory in git, quota
ledger, self-healing uploads, the external clock.

## Part 8 — The three upgrades (2026-10-01, owner request)

**1. The bank that never repeats (forever, not 1-2-5 years).**
Every concept now has a *variation layer* (`src/content_variants.py`):
3 hooks × 3 example scenes × 3 takeaways per concept, and the
example scenes are **slot-filled** — a fresh cast and setting
(40 names × 16 places × 7 days × 8 times) every time a concept
appears. The no-repeat ledger now records **every Short script
hash** (`short_hashes` in state.json) and the engine drifts until
all 4 daily Shorts are provably new. Measured space: **273
trillion distinct scripts — 0 collisions in a 1000-episode
stress test**; at 5 videos/day that is millions of years. If a
surface ever collides anyway, the drift loop regenerates — the
worst case is a retry, never a repeat.

**2. A voice that sounds human.** Narration is now **neural TTS**
(`edge-tts`, the Edge read-aloud service — free, no key, no
account) with `en-US-AriaNeural`: warm, conversational, calm. A
deterministic ±3% per-sentence pace jitter keeps the delivery
organic. Long videos run at -4% (intimate), Shorts at -2%
(brisk). If the endpoint is ever unreachable, the run falls back
to the vendored offline Piper voice automatically — the channel
never goes silent. Voice settings: `channel.yaml → voice:`.

**3. Calm music that matches the script and the voice.** The bed
is now mood-matched per topic (healing topics get minor-leaning
progressions, attachment suspended warmth, warm topics major
glow) and adds a soft plucked-arpeggio layer over the pads. The
mix normalizes the narration to one loudness standard and the
bed **ducks under each spoken sentence, breathing back in the
pauses** (config: `music.duck_depth`). Nothing to license —
every episode's soundtrack is generated from its seed.

These changed no schedules, no quota math, no upload logic — the
same forever machine, upgraded in place.

## Part 9 — The living couple upgrade (2026-10-02, owner request)

Viewer feedback after the first views: music is perfect, but (1) the
text overlay is far too small, (2) the characters stand completely
still, and (3) the voice is still slightly robotic. Fixed, in order:

**1. Text you can read from across the room.** Long-video captions
went from 44 px to **64 px Archivo Black** with a heavier outline
(render.py ASS style; wrap width tightened to 38 chars so lines stay
balanced). Shorts overlays: hook text **104 → 124 px**, scene/karaoke
text **84 → 104 px**, strokes nearly doubled. Measured: the karaoke
line now covers ~9% of the frame height — TikTok/Shorts standard.

**2. The couple is alive (30 fps).** Every card is now built as
**layers** — a static background plus the two characters as RGBA
**sprites** — and `src/anim.py` composites unique frames at 30 fps:
slow sinusoidal **sway**, breathing **bob**, and natural **blinks**
(2–4 s apart, never in unison, 100–160 ms long). All motions run an
integer number of cycles per loop, so the 2–5 s frame loop is
seamless. Frames are piped to ffmpeg as raw video (no PNG round
trips) and the final clip adds the Ken Burns drift via per-frame
`scale`+`crop` (driven by the filter's own frame counter `n`, so the
drift glides across loop seams). Render cost: ~1 s per second of
video — the daily job budget is unaffected.

**3. Six movement styles, one locked couple.** A style is seeded
**per video** (`sync_breath`, `gentle_sway`, `counter_sway`,
`weight_shift`, `lively`, `calm_bob`) — every day moves differently.
But the couple's appearance is now **locked channel-wide** (one
brunette + one dark-short-hair pair, fixed outfits, fixed iris
colors — `art_engine.LOCKED_COUPLE`): the audience learns their
faces the way they learn a channel's host. Faces also got a seeded
**emotion-intensity pass** per video (sad→crying, happy→inlove,
neutral→thinking/shy…), and the eyes are real now: white sclera +
colored iris + pupil + specular highlight, gaze aimed at the
partner. New expressions: shy, inlove, thinking, crying, hopeful.

**4. A more human voice.** Switched to `en-US-JennyNeural` (the most
conversational of the free neural voices), with per-sentence **pitch
jitter ±3 Hz** in addition to the pace jitter (±4.5%), and
**per-sentence pause jitter** (0.72–1.28×) — humans never breathe
like a metronome. After synthesis a best-effort broadcast polish
(high-pass, presence EQ at 3.2 kHz, gentle 2:1 compression) is
applied with a hard duration check: if the filter chain ever changed
the length by >20 ms, the raw take is kept — caption sync is sacred.
All knobs: `channel.yaml → voice:`.

Schedules, quota math, upload logic, the forever clock: untouched.
Same machine, finally breathing.

---

## Part 10 — The self-healing grid (2026-10-08, owner request)

**The contract**: every day, 4 Shorts go public at 00:00 / 06:00 /
12:00 / 18:00 Cairo and 1 long video at 20:00. Those public times
never move. What may move is when the machine *runs* — the owner
explicitly okayed that.

**The Oct 8 lesson** (why this exists): the Oct 6–7 quota failures
left episode 16 with one short already public and three still owed.
The recovery run booked those three into Oct 8's 00/06/12 slots — and
Oct 8's 18:00 slot stayed **empty**: the only run that could claim it
had to fire before 18:00, and the 20-hour gate window made every
pre-evening slot SKIP. The channel published 3 shorts that day and
nothing in the machine noticed. Three fixes, all pushed together:

1. **The gate watches the grid, not just the clock**
   (`tools/gate.py`). A publish slot that is still in the future,
   still unbooked, and expires *before* the next 22:00 Cairo cycle
   point is a **hole** — no future run can ever claim it. Any
   trigger that sees a hole fires: the morning/midday recovery slots
   and the watchdog beats now actually heal instead of SKIPping.
   Slots closer than ~40 minutes are already lost (the render takes
   that long) — they are not chased.

2. **A cycle books what the grid owes, not a fixed 4**
   (`src/youtube.py: free_slots`, `src/orchestrator.py`). The cycle
   counts every free short slot in the next 24h (holes first — they
   expire soonest) and produces that many shorts, up to 6 per
   episode (`story_engine.N_SHORTS`). A normal evening still books
   exactly 4; a heal day can carry 5–6. `shorts: count: 4` in
   channel.yaml remains the daily *contract* — the healing headroom
   is automatic and temporary.

3. **Partial quota is productive** (`src/orchestrator.py`). The old
   all-or-nothing gate ("need 8050 units or defer everything")
   refused to start a heal run that had 3339 units left — enough for
   the long plus a short. Now a cycle runs whenever the long (1600 +
   50) fits; each upload checks the remaining budget itself and
   defers only what does not fit. The deferred episode stays
   in_progress and the next trigger resumes it into the next free
   slot. A tight day lands 2–3 videos instead of 0.

**Steady state is unchanged**: the evening cycle (22:00 Cairo, plus
the pinger and the backup ring) books tomorrow's full grid, the
morning slots SKIP cheaply, and the 20h window still prevents double
production. The grid-hole rule only fires when the machine actually
owes the channel a slot that nothing else will fill.

**Known cosmetic edge**: at Egypt's DST flip (late October) a slot
booked before the switch publishes at the old instant (one hour off)
once; the next day self-corrects. Not engineered around — the
6-hour cadence never breaks.

---

## Part 11 — The five-year durability audit (2026-10-08)

The machine was stress-tested against the question *"what could
interrupt an unattended 5-year run?"* Six real holes were found and
fixed; everything else checked out. This part is the owner's map of
what was audited, what now protects itself, and the one 5-minute
ritual per year that keeps the human-side links alive.

### What was fixed in this audit

1. **A gate crash could kill the channel silently** (the worst
   finding). Every alert lived *downstream* of the gate job — if the
   gate itself ever failed (runner hiccup, checkout error, a bug,
   missing `python` alias on a future runner), no Issue was filed
   and every slot kept failing quietly. Now: the gate job has its
   own failure alert (timeouts included), and `gate.py` is wrapped
   so ANY internal error defaults to **RUN** — attempt production;
   if that fails, *its* alert fires. A silent skip is the only
   unforgivable verdict. The watchdog got the same treatment (plus
   `issues: write` permission).
2. **Corrupted memory = total amnesia** (fixed). A truncated
   `state.json` used to silently reset to empty — episode numbering
   would restart, the no-repeat banks would vanish, duplicates
   could upload. Now every save keeps a last-known-good
   `state.json.bak` (committed to git, riding with every memory
   commit), and the load ladder is `state.json → .bak → default`,
   with loud `[memory]` lines when recovery engages. One save after
   any double corruption fully repairs both files.
3. **The analytics snapshot was an unbounded growth bomb** (fixed).
   Each daily snapshot stored per-video view counts for EVERY video
   ever uploaded — at 5 videos/day that is ~9,000 videos × 60
   snapshots by year five: a multi-megabyte `state.json` and a
   steadily heavier repo. Persisted detail is now bounded to the
   200 most recent + top 100 all-time (≈300 entries/snapshot,
   forever < 1 MB). Channel totals and the printed growth report
   still use the full numbers.
4. **A dead refresh token was invisible until upload time** (fixed).
   The stats/playlist passes swallow all exceptions — including
   credential rejection. `AuthError` now prints a dedicated
   `[auth] CREDENTIALS REJECTED` banner pointing at the recovery
   steps, while still not blocking the run.
5. **Dependencies were unpinned** (fixed). `numpy>=1.26` etc. silently
   track PyPI's latest — any future major could break every cycle
   overnight. `requirements.txt` is now EXACTLY pinned to the
   versions the machine verified in production (numpy 2.5.3,
   Pillow 12.3.0, PyYAML 6.0.3, piper-tts 1.8.0, edge-tts 7.2.8).
   To upgrade: bump deliberately, run a `--dry-run` dispatch, watch
   one real cycle, then commit. (Frozen pins also keep the pip
   cache key stable — faster runs, forever.)
6. **Failure Issues never closed** (fixed). A failed day opened an
   Issue; the machine healed itself the next cycle; the Issue stayed
   open forever — after years the queue would bury the one issue
   that needs a human. After every successful cycle the machine now
   auto-closes PAST-day failure issues (`tools/close_resolved_issues.py`).

Also verified in this audit (no action needed): the OAuth refresh
token survives indefinitely for a published app in daily use; the
resumable-upload adoption path is duration-gated; quota ledger dates
roll at Pacific midnight like YouTube's real window; the story bank
(273 trillion combinations) cannot collide in any human lifespan;
the playlist only carries longs (~1,825 by year five, under the
5,000-item cap); daily memory commits keep GitHub's scheduler from
ever disabling the repo for inactivity; the memory-push rebase path
drops redundant copies instead of force-pushing stale state; and the
Piper offline voice fallback (the edge-tts backup) was live-tested
against piper-tts 1.8.0 — it works.

### The defense-in-depth map (what breaks → what happens)

| Failure | Detection | Recovery | Human needed |
|---|---|---|---|
| GitHub cron starvation | watchdog beats + 9 slots + external pinger | any live trigger produces | no |
| YouTube daily quota | server reason parsed, defer stamped | auto-resume after Pacific midnight | no |
| Rolling upload limit (burst days) | `uploadLimitExceeded` named in log | 2h back-off, next slot retries | no |
| One failed cycle | auto-Issue (email) + resume window | next slot completes the episode | no |
| Gate/watchdog job crash | **new** own failure alerts | slot retry on fresh runner | no |
| Corrupt state.json | `[memory]` warning lines | `.bak` ladder, self-repairs | no |
| Dead refresh token | `[auth]` banner + failed-run Issue | — | **yes: Part 2–3, ~15 min** |
| cron-job.org account dies | GitHub slots still fire (backup ring) | — | **yes: rebuild Part 6, ~5 min** |
| Action major deprecated (some year) | gate alert fires (runs fail loudly) | — | **yes: bump @v4→@v5, ~1 min** |
| YouTube Data API v3 sunset (unlikely) | uploads fail, Issue filed | — | **yes: migration** |

### The annual 5-minute ritual (put a yearly reminder if you like)

1. **Actions → verify-token → Run workflow** — green = credentials
   healthy. (Do the same after any Google password change.)
2. Log into **cron-job.org** once — an account you never log into is
   an account you cannot notice is dead. Both jobs should show green
   history.
3. Glance at the repo's **open Issues** — with auto-close, anything
   still open genuinely needs a human.
4. Glance at the **Actions usage** — a healthy month is ~1,500–2,500
   minutes (one ~25-min render + cheap gate skips).

That is the whole maintenance contract for a machine designed to
outlive its setup.

### Known cosmetic edges (accepted, not bugs)

- **DST flip days**: a slot booked before Egypt's DST switch
  publishes one hour off, once, then self-corrects (grid cadence
  never breaks). The 00:00 slot on the flip morning is the only
  one ever affected.
- **GitHub cron drift**: scheduled slots can fire minutes early or
  late (observed: ±30 min), and high-load evenings can skip slots
  entirely — the pinger + watchdog + morning recovery exist exactly
  for this; the gate makes every extra fire free.
- **Analytics detail is bounded**: per-video view history is kept
  for the recent 200 + top 100 videos; older videos contribute to
  totals but not per-video rows. Old snapshots age out at 60 days.
