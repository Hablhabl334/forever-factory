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
   evening peak slot).
2. **Actions → verify-token → Run workflow** — green = credentials
   healthy.
3. Done. Every day the factory runs (9 staggered cron slots + a
   watchdog with 5 more chances — see `.github/workflows/`). Videos
   appear on your channel at 19:30 / 21:00 Cairo time (13:00 / 17:30 /
   20:30 for Shorts); a late run publishes immediately instead of
   waiting.

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
   - **Schedule:** every day at **09:05 UTC** (11:05 Cairo in summer
     — just before the first GitHub slot, so it wins the race and
     the GitHub slots become pure backup).
3. Save. Done — the day now starts on an external clock that never
   starves.

Why this is safe: the dispatch is **gated by default** — if the day
was already produced, a duplicate ping costs one 9-second skipped
run and zero YouTube quota. Even if the token leaked, the worst
case is someone *starting* a workflow that immediately skips.

**Belt and suspenders, the full stack:** external pinger (09:05 UTC)
→ 9 GitHub cron slots (09:23–20:31 UTC) → watchdog heartbeats
(5×/day) → auto-Issue if a day is ever missed. Four independent
layers; a day can only be missed if all four fail on the same day.
