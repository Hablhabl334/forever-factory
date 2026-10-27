# SKILLS.md — the free-skill library, mapped to this factory

Every skill the agent environment can load lives in
`/home/z/my-project/skills/`. The owner's standing rule decides what
enters that library: **free and readable only** — a skill that needs an
API key, a paid quota, or a logged-in belt CLI is skipped at install
time (the 7 skipped on 2026-10-27: ai-avatar-video, ai-video-generation,
python-executor, agent-tools, google-agents-cli-workflow,
anti-detect-browser, browser-mcp-agent).

This file maps each installed skill to WHERE the factory uses it — so
any future session (agent or human) knows the doctrine is already in
the code and where to look.

## The factory-doctrine skills (translated into code)

### ai-seo — *the text layer*  →  `src/ai_layer.py`, `src/metadata.py`
Doctrine: **models don't watch the video; they read the text around
it** — transcript, captions, chapters, description, comments
(`references/youtube-ai-citations.md`). In the code:

* the narration ships as a machine-readable English **caption track**
  (`captions.insert`, 50 units) — exact words, exact timings
* the long gets a channel **summary comment**
  (`commentThreads.insert`, 50 units) — the numbered lesson list plus
  the open-loop question; owner may pin each in Studio (the API can't)
* the description carries a **40-60 word liftable answer block**, and
  the **chapter timestamps are IN the description** (fixed 2026-10-27:
  they had been computed since day 1 and silently dropped at upload)
* refusal contract: one structural 400/403 is remembered in
  `state["text_layer_refused"]` and never retried; transient failures
  retry next cycle; zero quota is ever wasted on a failed call

### youtube-thumbnail-design — *the click*  →  `src/thumbnails.py`
The skill's paid image-API examples are ignored (free-only rule); its
design rules are 100% free knowledge and now enforced in code:

* **max 6 words** of promise text — cut words, never shrink
* **seeded expression variety** on the LOCKED couple (warm positives,
  `inlove` double-weighted; the faces vary, the brand does not)
* **the automated checklist**: spec size, the measured **120px squint
  test** (text-band separability on the real feed-size downscale),
  the 8% mobile text floor, contrast delta, <2MB — logged every
  cycle, **fail-open** (a deterministic render would repeat any
  failure forever; the audit is a regression gate, not a day-killer)

### marketing-psychology — *the copy principles*  →  `src/metadata.py`,
`src/content_variants.py`, comment/description structure
The models that already shaped this channel's voice, now named:

* **Zeigarnik effect / open loops** — every description and comment
  leads with the question; scripts close on the comment prompt
* **Peak-End rule** — the CTA card gets the Pop-in landing (see
  animation-vocabulary); the last beat of every Short answers
* **Mere exposure** — the owner's fixed-Short-title funnel IS the
  consistency play; never "improve" it without the owner
* **Reciprocity** — one real free lesson a day, no gate, no bait
* **No fabricated social proof, ever** — no invented counts; the
  channel's honesty is the moat (also YouTube policy)
* When the muse (OpenRouter layer) wakes: its prompt templates should
  apply loss-aversion framing, specificity and curiosity-gap structure
  from this skill's library

### marketing-ideas — *the angle bank*  →  `tools/trend_intel.py`,
`tools/compete.py`, the Sunday benchmark ring
The SaaS idea list is channel-translated: the weekly benchmark IS the
"competitor" play; the topic queue IS programmatic ideation; the
trend-intel title-formula taxonomy (NUMBER_LIST / HOW_TO / VS /
WARNING / STORY / YEAR_SPECIFIC) is the free replacement for paid
trend tools. When stuck for growth moves, re-read this skill's
139-idea index and translate each idea into "what would this mean for
a daily love-psychology channel with zero budget?"

### animation-vocabulary — *the motion glossary*  →  `src/anim.py`
Named patterns the factory already speaks, so future motion work has
exact words: **ease-out** landings (every card), **Pop in** (the CTA
settle, `pop_scale()`), the **dip cut** (term reveal), the breathing
camera **drift**. The glossary is the design review vocabulary: any
new motion must have a NAME from this list and a reason ("Pop in —
appears with a slight overshoot, like it bounces into place") before
it gets code.

### claude-handoff — *the memory contract*  →  `/home/z/my-project/worklog.md`
No `claude --bg` here; the local adapter (installed with the skill)
says it plainly: **worklog.md IS the handoff.** Every session reads
the tail first, appends a dated section last, with Task ID, work log,
stage summary. This is how the factory survives context resets.

### subagent-driven-development — *parallel feature work*
For factory work that can be split (e.g. "audit tts.py AND
music.py"): write the task brief, dispatch, collect reports, re-read
the diff yourself. The factory's determinism rule makes subagent work
safe: tests catch what review misses. Use for read-only exploration
and well-scoped edits; never for the daily pipeline (it must stay a
single deterministic process).

### code-review — *the pre-push ritual*
Run before every push that touches `src/`: diff against the change's
stated intent (this repo has no CONTRIBUTING beyond its docstrings —
the docstrings ARE the standards; the blueprints in README/RUNBOOK
are the spec). The 2026-10-27 skill-upgrade commit was reviewed this
way: every edit re-read, every test green before push.

### agent-browser & playwright-cli — *zero-quota web verification*
`tools/channel_check.py` and the morning report use YouTube oEmbed
(free, no API). For anything deeper — verifying a public page, the
channel front, a comment's visibility — use agent-browser
(`agent-browser` binary, v0.39+) or `npx playwright` (1.57 installed)
instead of API quota. Browser automation on youtube.com must stay
read-only (no automated watching/liking — ToS and honesty).

### browser-fingerprint-audit — *the honesty fence*
Installed and useful for auditing OUR OWN scraping posture. Standing
decision: this factory does NOT use anti-detect browsers against
YouTube — the Data API is the contract, oEmbed is the free probe, and
the two anti-detect skills that arrived in the same batch were
SKIPPED per the free-only rule (closed-source, license phone-home).
If a free data path ever needs a real browser, audit its fingerprint
first with `npx liarjs --offline`.

## The pre-existing factory skills (already integrated)

* **scraping-youtube-trending-videos** +
  **tracking-youtube-trending-topics-by-niche** → `tools/trend_intel.py`
  (translated 2026-10-26: yt-dlp flat search + OAuth enrichment on the
  factory's own free path; scoring verbatim from the playbooks)
* **youtube-analytics** → the daily analytics snapshot + the Sunday
  benchmark (`tools/compete.py`)
* **research / web-search / watch-video / scraping family** → the
  agent's general web tooling; used for niche studies, not in the
  daily loop

## The API-gated twins (dormant until an owner decision)

* **LLM / VLM / TTS / image-generation / video-generation** (z-ai SDK
  skills) — platform-managed, usable in-session but BUDGETED: any
  factory-facing use must fit the daily quota plan or be owner-approved.
  The muse (`src/muse.py`) will use OpenRouter's free meta-router
  when its key lands as a GitHub secret — free-tier models only.
* **hyperframes** — the motion doctrine source for v4 (`motion.md`:
  "arrive slow, land still"); its render pipeline is NOT used (the
  factory renders its own), but its craft rules are the reference.

## Batch-2: the 19 skills of 2026-10-27 (translated same-day)

Installed under the owner's free-only filter (13 of the 32 requested
were skipped at install time — API keys, paid quotas, logins). The 19
that made it, mapped:

### Translated into factory code

* **hook-writer-sms** — *the 9-pattern hook library* →
  `src/hook_patterns.py` (merged into the variant pools by
  `content_variants.py`)
  Doctrine: hooks that stop the scroll follow nine named patterns
  (contrarian, question, statistic, empathy, before/after, negation,
  open loop, list preview, bold claim). The pools were strong but
  mono-pattern — one NEW pattern-labeled hook per concept (40) is
  appended so the seeded draw rotates PATTERNS, not just phrasings.
  Rules enforced by `scripts/test_batch2_skills.py`: 8-30 words,
  never leaks the concept's term, never duplicates the legacy pool,
  ≥7 distinct patterns, no pattern owns a third of the pool.

* **short-form-video** — *the retention contract* → confirmed the v2
  arc's shape, then extended it
  The skill's spine (hook → tension hold → payoff → loop; "open a
  loop in the first ~3s, close it last") was already the v2 script
  arc (opener → hook → micro → facts → LATE reveal → takeaway →
  question → CTA). What it added: the LONG video was missing the
  "tension hold" — see BRIDGES under script-writer below.

* **script-writer** — *curiosity bridges for the long* →
  `content_variants.py` BRIDGES pool + `story_engine._build`
  Doctrine: mid-video sag is where watch-time dies; serialized
  segments beat standalone ones. Every concept segment except the
  last now ENDS on a spoken one-breath tease of the next pattern
  (12-line pool, drawn without replacement per episode). Bridges
  draw from a SIDE rng stream (seed+777_777) so the main draw
  sequence stays byte-identical to pre-bridge episodes. Rollback:
  `channel.yaml: story.bridges: false`.

* **youtube-seo** — *the Shorts text layer* → `src/metadata.py`
  short_metadata
  Doctrine: title/description/thumbnail are one system; keyword in
  the first chars; descriptions carry the search terms. The Short
  TITLE and TAGS are owner-locked, so the doctrine lands on the only
  free surface — the description now carries the concept's TERM (the
  phrase a searcher types), the hook line, and the niche keywords,
  with the engagement question still on the visible fold.

* **youtube-transcript + baoyu-youtube-transcript + yt-dlp +
  youtube-downloader** — *transcripts are free* →
  `tools/transcript_probe.py`
  Doctrine: a video's transcript is public, free, and the most
  honest performance data — what winners SAY, not what titles claim.
  The probe fetches any video's English auto-sub track via yt-dlp
  (zero quota, read-only), reports the first-15-seconds spoken hook,
  pace, and the repeated-phrase layer, and saves the full text to
  `data/probe/` for phrase-level steal-list study. Manual/weekly,
  next to `compete.py` — never in the daily loop.

### Reference doctrine (no factory code — the row is the memory)

* **video-marketing** — the strategy layer above the daily loop;
  its hook/structure guidance is already embedded in the v2 arc and
  the pattern library. Re-read when planning format experiments.
* **video-spec-builder** — the spec-first discipline for any NEW
  format: write the retention contract (hook budget, interrupt
  cadence, loop seam) as a spec BEFORE code, like BLUEPRINT does.
* **web-video-presentation** — presentation/lecture craft (pacing,
  signposting); the long video's chapter + bridge structure is its
  channel-native translation.
* **influencer-marketing** — collab/outreach doctrine; dormant until
  the channel is large enough that outreach is worth owner time.
* **creator-ugc-marketing** — community/UGC doctrine; the comment
  questions ARE the channel-native UGC play (the audience writes the
  relatability layer). Escalation needs an owner decision.
* **tech-podcast-youtube-channel** — a different niche's full
  playbook; kept as a structural reference (cadence, batching,
  packaging) — its content advice does not transfer.
* **youtube-automation** — the claude-office automation playbook;
  the factory already IS its channel-specific implementation.
* **app-preview-video** — app-store preview craft; not applicable to
  this channel (kept in the library only because it is free).
* **markitdown** — agent-side file conversion utility (PDF/DOCX →
  text); useful in future research sessions, never in the loop.
* **autocli** — agent-side CLI launcher; its `curl|sh` install is
  the official vendor pattern (security-scanned clean), unused.

## Standing rule for future installs

Before adding any skill to `/home/z/my-project/skills/`:
1. Is it free — no API key, no paid quota, no login?
2. Is it readable — a playbook/KL script the agent can load?
3. If it touches the factory: does this file get a row above?
Four "no"s = don't install; a "yes" = clone the source repo to
`/home/z/my-project/repos/` and write the map row in the same change.
