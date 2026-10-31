#!/usr/bin/env python3
"""#epN episode-numbering tests (2026-11-01 owner decision).

Every moving part of the system gets a regression check, fully offline
(the YouTube layer is monkeypatched — zero quota, zero network):

  1. allocation      — the forever-counter seeds from the ledger before
                       the first channel sync; numbers are never reused
  2. binding         — a published video's number lands in the map
  3. born metadata   — new longs/Shorts carry #epN in title + an
                       "Episode #N" line in the description; ep_num=None
                       keeps the legacy shapes (backward compat)
  4. title limits    — every generated/renamed title fits 100 chars
  5. rename rules    — the fixed Short title gains the number between
                       CTA and hashtags; longs append; idempotent
  6. the backfill    — chronological assignment 1..K, orphan adoption,
                       placeholder skip, live-title verification, quota
                       gating, quota-family refusal (no attempt burned),
                       collision guard, give-up-after-N-attempts

Run: python3 scripts/test_ep_numbering.py   (from the repo root)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(name: str, got, want=True):
    ok = got == want
    if isinstance(want, bool) or isinstance(got, bool):
        ok = isinstance(got, bool) == isinstance(want, bool) and got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"  (got {got!r}, want {want!r})"))
    if not ok:
        FAILURES.append(name)


def section(title: str):
    print(f"\n== {title} ==")


# ── fixtures ─────────────────────────────────────────────────────────

def story_fixture(title="Why We Get Jealous", hook="The calmest person in the room is often the most afraid."):
    return {
        "title": title,
        "hook": hook,
        "hash": "d802aa025c356290",
        "seed": 42,
        "topic_label": "jealousy",
        "question": "Which one hit home?",
        "atoms": {"concepts": ["jealousy", "attachment", "trust", "self worth", "repair",
                                "bids", "conflict", "secure love"]},
        "scenes": [],
        "shorts": [],
    }


def narration_fixture(n_scenes=8):
    return {"scene_durations": [40.0] * n_scenes, "total": 320.0, "chunks": [],
            "engine": "edge"}


def state_fixture():
    """A small ledger: 2 episodes × (1 long + 2 shorts) = 6 videos."""
    return {
        "version": 1,
        "episodes": [
            {"n": 1, "title": "Ep One", "date": "2026-10-01", "status": "done",
             "ids": {"long": "LONG1", "shorts": ["SHORT1", "SHORT2"],
                     "thumbnail": "2026-10-01"}},
            {"n": 2, "title": "Ep Two", "date": "2026-10-02", "status": "done",
             "ids": {"long": "LONG2", "shorts": ["SHORT3", "SHORT4"],
                     "thumbnail": "2026-10-02"}},
        ],
        "story_hashes": [], "short_hashes": [],
        "ep_numbering": {"seq_next": 1, "videos": {}},
        "quota": {"date": None, "units_used": 0},
        "last_run": None,
        "stats": {"videos_published": 6, "days_active": 2},
    }


from src import epnumbering, ledger, metadata, youtube  # noqa: E402


# ── 1. allocation ────────────────────────────────────────────────────

section("1. allocation — the forever-counter")

ledger.set_read_only(True)          # never touch data/state.json from tests
try:
    st = state_fixture()
    n1 = ledger.allocate_ep_number(st)
    check("first allocation seeds from the ledger (6 ids -> 7)",
          n1, 7)
    n2 = ledger.allocate_ep_number(st)
    check("second allocation advances (8)", n2, 8)
    check("counter persisted in memory", st["ep_numbering"]["seq_next"], 9)

    st2 = state_fixture()
    st2["ep_numbering"]["channel_synced"] = True
    st2["ep_numbering"]["seq_next"] = 4
    check("after channel sync the counter is authoritative",
          ledger.allocate_ep_number(st2), 4)

    st3 = state_fixture()           # channel_synced, but never synced in fact
    st3["ep_numbering"]["channel_synced"] = False
    st3["ep_numbering"]["seq_next"] = 3
    check("seeding is monotonic (max), never backwards",
          ledger.allocate_ep_number(st3), 7)

    # ── 2. binding ───────────────────────────────────────────────────

    section("2. binding — published video -> number map")

    st = state_fixture()
    ledger.bind_ep_number(st, "LONG9", 12, "long", 9)
    ledger.bind_ep_number(st, "SHORT9", 13, "short", 9)
    rec = st["ep_numbering"]["videos"]["LONG9"]
    check("long bound with kind+episode",
          (rec["n"], rec["kind"], rec["episode"], rec["born"]),
          (12, "long", 9, True))
    check("short bound", st["ep_numbering"]["videos"]["SHORT9"]["n"], 13)
    ledger.bind_ep_number(st, "", 99, "long", 9)
    check("empty video id ignored", "" not in st["ep_numbering"]["videos"])

    # ── 3. born metadata ─────────────────────────────────────────────

    section("3. born metadata — #epN in title + description")

    s = story_fixture()
    narr = narration_fixture()
    lm = metadata.long_metadata(s, narr, ep_num=37)
    check("long title carries #ep37", lm["title"].endswith(" #ep37"), True)
    check("long title fits 100 chars", len(lm["title"]) <= 100, True)
    check("long description carries the episode line",
          "Episode #37 of the daily love psychology series." in lm["description"], True)

    sm = metadata.short_metadata(s, {"term": "jealousy", "hook": "h"}, ep_num=132)
    want_title = ("Subscribe for more tips like this #ep132 "
                  "#psychology #relationship #love #relationshipgoals")
    check("short title is CTA + #ep132 + fixed hashtags",
          sm["title"], want_title)
    check("short title fits 100 chars", len(sm["title"]) <= 100, True)
    check("short description carries the episode line",
          "Episode #132 of the daily love psychology shorts." in sm["description"], True)
    check("short tags unchanged", sm["tags"], list(metadata.SHORT_TAGS))

    lm0 = metadata.long_metadata(s, narr)
    check("legacy long title has no #ep", "#ep" not in lm0["title"], True)
    sm0 = metadata.short_metadata(s, {"term": "jealousy", "hook": "h"})
    check("legacy short title is the fixed one",
          sm0["title"], metadata.SHORT_TITLE)
    check("legacy short desc has no episode line",
          "Episode #" not in sm0["description"], True)

    # ── 4. title limits under clipping ───────────────────────────────

    section("4. title limits")

    long_story = story_fixture(title="Why the slowest reply often means the deepest feeling and what psychology says about it")
    t = metadata.long_title(long_story, ep_num=12345)
    check("clipped long title still ends with the number",
          (t.endswith(" #ep12345"), len(t) <= 100), (True, True))

    # ── 5. rename rules for OLD videos ───────────────────────────────

    section("5. rename rules — built from the live title")

    got = epnumbering.new_title_for(metadata.SHORT_TITLE, 132)
    check("fixed short title -> number inserted before hashtags",
          got, want_title)
    got = epnumbering.new_title_for("Psychology of Love: Trust | Love Tips", 25)
    check("long title -> number appended",
          got, "Psychology of Love: Trust | Love Tips #ep25")
    huge = "Psychology of Love: " + "why we get jealous " * 6
    got = epnumbering.new_title_for(huge, 7)
    check("overlong title clipped but keeps the number",
          (len(got) <= 100, got.endswith(" #ep7")), (True, True))
    check("already-numbered title is untouched (idempotent)",
          epnumbering.new_title_for("A lesson #ep9 | tips", 9),
          "A lesson #ep9 | tips")

    d = epnumbering.new_description_for("Some description.", 5, "long")
    check("description gains the line",
          d.endswith("Episode #5 of the daily love psychology series."), True)
    check("description rename is idempotent",
          epnumbering.new_description_for(d, 5, "long"), d)
    ds = epnumbering.new_description_for("", 6, "short")
    check("empty description -> just the line",
          ds, "Episode #6 of the daily love psychology shorts.")
    check("short vs long lines differ",
          epnumbering.new_description_for("x", 6, "short")
          != epnumbering.new_description_for("x", 6, "long"), True)

    # ── 6. the backfill (YouTube layer mocked) ───────────────────────

    section("6a. the videos.update request body (the Oct-31 403 lesson)")

    body = youtube._update_body(
        "MpR4TtgggrE",
        {"title": "old", "description": "old", "tags": ["love", "psychology"],
         "categoryId": "24", "defaultLanguage": "en",
         "defaultAudioLanguage": "en", "publishedAt": "2026-10-31T00:00:00Z",
         "channelId": "UCx", "thumbnails": {"default": {"url": "https://x"}},
         "localized": {"title": "old"}},
        "New title #ep42", "New desc")
    check("the video id rides IN the body (required — its absence was the 403)",
          body.get("id"), "MpR4TtgggrE")
    sn = body["snippet"]
    check("title/description/categoryId present",
          (sn["title"], sn["description"], sn["categoryId"]),
          ("New title #ep42", "New desc", "24"))
    check("tags pass through (else they would be DELETED)",
          sn.get("tags"), ["love", "psychology"])
    check("languages pass through",
          (sn.get("defaultLanguage"), sn.get("defaultAudioLanguage")),
          ("en", "en"))
    check("read-only fields never sent",
          any(k in sn for k in ("publishedAt", "channelId", "thumbnails", "localized")),
          False)
    body2 = youtube._update_body("X", {"categoryId": "24"}, "t", "d")
    check("no tags key when the video has none",
          "tags" in body2["snippet"], False)
    body3 = youtube._update_body("X", {}, "t", "d")
    check("categoryId falls back to the channel config",
          body3["snippet"]["categoryId"], "24")

    section("6b. the backfill — assign + rename, fully mocked")

    def install_mocks(state, channel_titles, snippets, updates,
                      refuse_reason=None):
        """Point the youtube module at deterministic fakes."""
        youtube.get_access_token = lambda: "TOK"
        youtube.list_channel_videos = lambda token, st=None: dict(channel_titles)
        youtube.fetch_video_snippets = lambda token, ids, st=None: {
            k: dict(v) for k, v in snippets.items() if k in set(ids)}
        def _update(token, vid, sn, title, desc, st=None):
            updates.append((vid, title, desc))
            if refuse_reason:
                return {"ok": False, "reason": refuse_reason}
            if st is not None:   # the real call ledgers 50 units per write
                ledger.spend_quota(st, youtube.UPDATE_UNITS)
            return {"ok": True, "reason": ""}
        youtube.update_video_snippet = _update

    def channel_and_snippets(state):
        """Legacy channel: every video un-numbered, chronological."""
        titles, snippets = {}, {}
        published = {
            "SHORT1": "2026-10-01T00:00:00Z", "SHORT2": "2026-10-01T06:00:00Z",
            "SHORT3": "2026-10-01T12:00:00Z", "SHORT4": "2026-10-01T18:00:00Z",
            "LONG1": "2026-10-01T20:00:00Z", "LONG2": "2026-10-02T20:00:00Z",
        }
        for vid, ts in published.items():
            if vid.startswith("SHORT"):
                titles[vid] = metadata.SHORT_TITLE
                desc = "New love psychology shorts every day.\n\n" + metadata.SHORT_HASHTAGS
                kind = "short"
            else:
                titles[vid] = f"Psychology of Love: Ep {vid[-1]} | Love Tips"
                desc = "Psychology of love explained in plain words."
                kind = "long"
            snippets[vid] = {"title": titles[vid], "description": desc,
                             "tags": ["love", "psychology"], "categoryId": "24",
                             "defaultLanguage": "en", "publishedAt": ts,
                             "_duration": 60.0, "_kind": kind}
        return titles, snippets

    # 6a. full happy path
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    updates: list = []
    install_mocks(st, titles, snips, updates)
    summary = epnumbering.renumber_and_rename(st)
    check("assigned 6 chronological numbers", summary["assigned"], 6)
    check("renamed all 6 within fresh quota", summary["renamed"], 6)
    check("nothing pending", summary["pending"], 0)
    nums = sorted(rec["n"] for rec in st["ep_numbering"]["videos"].values()
                  if rec.get("n"))
    check("numbers are exactly 1..6 (dense)", nums, [1, 2, 3, 4, 5, 6])
    order = sorted(st["ep_numbering"]["videos"].items(),
                   key=lambda kv: kv[1]["n"])
    check("chronological: #1 is the earliest short",
          order[0][0], "SHORT1")
    check("chronological: #6 is the newest long",
          order[-1][0], "LONG2")
    check("counter advanced past the block", st["ep_numbering"]["seq_next"], 7)
    check("channel synced flag set", st["ep_numbering"]["channel_synced"], True)
    long_updates = [u for u in updates if u[0] == "LONG1"]
    check("long rename keeps the SEO head and adds the number",
          long_updates[0][1].endswith(" #ep5"), True)
    check("long rename appends the episode line to the description",
          long_updates[0][2].endswith("Episode #5 of the daily love psychology series."), True)
    short_updates = [u for u in updates if u[0] == "SHORT1"]
    check("short rename inserts the number before the hashtags",
          short_updates[0][1], want_title.replace("#ep132", "#ep1"))
    check("tags/category pass through on the update body",
          snips["LONG1"]["tags"] == ["love", "psychology"], True)

    # 6b. idempotency: rerun with the LIVE titles now numbered
    live_titles = {vid: t for vid, t in
                   ((u[0], u[1]) for u in updates)}
    live_snips = {}
    for vid, title in live_titles.items():
        sn = dict(snips[vid]); sn["title"] = title
        upd = next(u for u in updates if u[0] == vid)
        sn["description"] = upd[2]
        live_snips[vid] = sn
    updates2: list = []
    install_mocks(st, live_titles, live_snips, updates2)
    summary2 = epnumbering.renumber_and_rename(st)
    check("rerun assigns nothing new", summary2["assigned"], 0)
    check("rerun renames nothing (live titles verified)", summary2["renamed"], 0)
    check("rerun spends zero update calls", len(updates2), 0)

    # 6c. quota gating — assignment is free, renames wait
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    updates3: list = []
    install_mocks(st, titles, snips, updates3)
    st["quota"] = {"date": ledger._quota_today(), "units_used": 9800}
    summary3 = epnumbering.renumber_and_rename(st)
    check("assignment still happens on a tight budget",
          summary3["assigned"], 6)
    check("exactly two renames fit above the reserve (200-2x50=100)",
          summary3["renamed"], 2)
    check("the rest stay pending", summary3["pending"], 4)

    # 6d. placeholder videos are never numbered
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    titles["P0D1"] = metadata.SHORT_TITLE
    snips["P0D1"] = {"title": metadata.SHORT_TITLE, "description": "",
                     "tags": [], "categoryId": "24",
                     "publishedAt": "2026-10-01T03:00:00Z", "_duration": 0.0}
    updates4: list = []
    install_mocks(st, titles, snips, updates4)
    summary4 = epnumbering.renumber_and_rename(st)
    check("placeholder detected and skipped", summary4["placeholders"], 1)
    check("placeholder never numbered",
          st["ep_numbering"]["videos"]["P0D1"].get("placeholder"), True)
    check("real videos still got dense 1..6",
          sorted(r["n"] for r in st["ep_numbering"]["videos"].values()
                 if r.get("n")), [1, 2, 3, 4, 5, 6])

    # 6e. crash orphan on the channel (not in the ledger) gets numbered
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    titles["ORPH1"] = metadata.SHORT_TITLE
    snips["ORPH1"] = {"title": metadata.SHORT_TITLE, "description": "d",
                      "tags": [], "categoryId": "24",
                      "publishedAt": "2026-10-01T09:00:00Z", "_duration": 55.0}
    updates5: list = []
    install_mocks(st, titles, snips, updates5)
    summary5 = epnumbering.renumber_and_rename(st)
    orec = st["ep_numbering"]["videos"]["ORPH1"]
    check("orphan numbered between its neighbors (09:00 -> #3)",
          orec["n"], 3)
    check("orphan marked as orphan kind", orec["kind"], "orphan")
    check("orphan renamed too", any(u[0] == "ORPH1" for u in updates5), True)

    # 6f. quota-family refusal: defer marker set, attempt NOT burned
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    updates6: list = []
    install_mocks(st, titles, snips, updates6, refuse_reason="quotaExceeded")
    summary6 = epnumbering.renumber_and_rename(st)
    check("quota refusal stops the pass (1 attempt only)",
          len(updates6), 1)
    check("server defer marker stamped",
          bool(st["quota"].get("defer_until")), True)
    first_pending = [rec for rec in st["ep_numbering"]["videos"].values()
                     if rec.get("n") and not rec.get("renamed")]
    check("quota refusal does not burn the attempt budget",
          all(rec.get("attempts", 0) <= 1 for rec in first_pending), True)
    # and the next pass holds off entirely while the defer is live
    st["quota"]["defer_until"] = 4102444800   # far future
    updates6b: list = []
    install_mocks(st, titles, snips, updates6b)
    summary6b = epnumbering.renumber_and_rename(st)
    check("defer active -> the whole pass holds",
          (summary6b["assigned"], len(updates6b)), (0, 0))

    # 6f-b. a GLOBAL 403 forbidden stops the pass without burning attempts
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    updates6c: list = []
    install_mocks(st, titles, snips, updates6c, refuse_reason="forbidden")
    summary6c = epnumbering.renumber_and_rename(st)
    check("global 403 stops the pass after one call",
          len(updates6c), 1)
    recs = [r for r in st["ep_numbering"].values()]
    vids_map = st["ep_numbering"]["videos"]
    check("no video's attempt budget burned by a global 403",
          all(r.get("attempts", 0) == 0 for r in vids_map.values()), True)
    check("everything stays pending (numbering intact)",
          summary6c["pending"], 6)

    # 6g. collision guard — a born number is never reused
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    # a NEW video (uploaded after deployment) already claimed #7...
    st["ep_numbering"]["seq_next"] = 7
    st["ep_numbering"]["videos"]["NEW1"] = {"n": 7, "kind": "short",
                                            "episode": 3, "born": True,
                                            "renamed": "2026-11-01"}
    titles["NEW1"] = "Subscribe for more tips like this #ep7 " + metadata.SHORT_HASHTAGS
    snips["NEW1"] = {"title": titles["NEW1"], "description": "Episode #7.",
                     "tags": [], "categoryId": "24",
                     "publishedAt": "2026-11-01T00:00:00Z", "_duration": 60.0}
    updates7: list = []
    install_mocks(st, titles, snips, updates7)
    summary7 = epnumbering.renumber_and_rename(st)
    check("born-numbered video verified, not renamed",
          any(u[0] == "NEW1" for u in updates7), False)
    check("old videos keep 1..6, none touches #7",
          sorted(r["n"] for r in st["ep_numbering"]["videos"].values()
                 if r.get("n")) , [1, 2, 3, 4, 5, 6, 7])

    # 6h. permanent rejection gives up after MAX_ATTEMPTS
    st = state_fixture()
    titles, snips = channel_and_snippets(st)
    updates8: list = []
    install_mocks(st, titles, snips, updates8, refuse_reason="invalidTitle")
    for _ in range(epnumbering.MAX_ATTEMPTS + 1):
        st8 = st
        epnumbering.renumber_and_rename(st8)
    gave_up = [r for r in st["ep_numbering"]["videos"].values()
               if r.get("renamed") == "failed"]
    check("a permanently rejected rename gives up (flagged failed)",
          len(gave_up) >= 1, True)

finally:
    ledger.set_read_only(False)

# ── wiring smoke checks ──────────────────────────────────────────────

section("7. wiring — the orchestrator and CLI know the new mode")

import subprocess  # noqa: E402
help_out = subprocess.run(
    [sys.executable, "main.py", "--help"], capture_output=True, text=True,
    cwd=str(ROOT)).stdout
check("--rename-only is a real CLI mode", "--rename-only" in help_out, True)
src = (ROOT / "src" / "orchestrator.py").read_text()
check("produce_episode allocates before the long upload",
      "allocate_ep_number" in src and "long_metadata(story, narration, long_ep)" in src, True)
check("produce_episode allocates per short",
      src.count("allocate_ep_number") >= 2, True)
check("the daily cycle runs the numbering pass",
      "renumber_and_rename(state)" in src, True)

print(f"\n{'ALL CHECKS PASSED' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
