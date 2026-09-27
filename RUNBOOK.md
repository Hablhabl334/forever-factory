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
3. Done. Every day at 10:00 UTC the factory runs. Videos appear on
   your channel at 19:30 / 21:00 Cairo time (13:00 / 17:30 / 20:30
   for Shorts).

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
