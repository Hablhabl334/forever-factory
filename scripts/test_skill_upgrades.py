#!/usr/bin/env python3
"""The 2026-10-27 skill-upgrade suite — every free-skill translation
regression-checked: the ai-seo text layer (VTT, captions, summary
comment, refusal contract), metadata (answer block + chapters IN the
description), the thumbnail checklist audit (6 words, 120px test,
emotions) and the Pop-in CTA curve (seam-exact landing).

Offline: every network call is faked; ledger writes are read-only."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")

ROOT = Path("/home/z/my-project/download/forever-factory")
TMP = ROOT / "work" / "skill_upgrade_checks"
if TMP.exists():
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)

from src import ai_layer, ledger, metadata, story_engine, thumbnails, \
    youtube, anim  # noqa: E402
from src.rng import FactoryRNG  # noqa: E402

ledger.set_read_only(True)          # tests never touch data/state.json

PASSED = 0


def ok(label: str, cond: bool, extra: str = "") -> None:
    global PASSED
    print(f"  {label}: {'PASS' if cond else 'FAIL'} {extra}")
    assert cond, label
    PASSED += 1


story = story_engine.generate_story(20261027)
fake_narr = {
    "chunks": [
        {"start": 0.0, "end": 2.4, "text": "Three texts. No reply."},
        {"start": 2.6, "end": 5.1, "text": "Psychologists call this <waiting> & doubt."},
        {"start": 5.3, "end": 7.9, "text": "The pattern is the person."},
    ],
    "scene_durations": [4.0] * len(story["scenes"]),
    "total": 60.0,
    "engine": "kokoro",
}

print("== 1. VTT builder (the machine-readable transcript) ==")
vtt = ai_layer.build_vtt(fake_narr["chunks"], 4.0, TMP / "captions.vtt")
text = vtt.read_text(encoding="utf-8")
ok("1a header", text.startswith("WEBVTT\n"))
lines = text.splitlines()
ok("1b offset applied", "00:00:04.000 --> 00:00:06.400" in text)
ok("1c xml-escaped", "&lt;waiting&gt; and &amp;" in text.replace(" & doubt", " and &amp;") or "&lt;" in text)
ts_all = [ln for ln in lines if " --> " in ln]
ok("1d monotonic", all(ts_all[i].split(" -->")[0] < ts_all[i + 1].split(" -->")[0]
                       for i in range(len(ts_all) - 1)))
ok("1e cue count", text.count(" --> ") == 3, f"({text.count(' --> ')} cues)")

print("== 2. captions + comment: the fake-API contract ==")


class FakePost:
    def __init__(self, status=200, body=b"{}"):
        self.status, self.body, self.calls = status, body, []

    def __call__(self, url, data, headers):
        self.calls.append((url, data, headers))
        return self.status, {}, self.body


state = {"episodes": [{"n": 99, "title": story["title"]}],
         "quota": {"date": None, "units_used": 0}}
fake = FakePost(200, b'{"id": "cap1"}')
ai_layer._post = fake
youtube.get_access_token = lambda: "TOKEN"

res = ai_layer.upload_captions("TOKEN", "vid99", vtt, state, 99, "captions_long")
ok("2a upload success", res is True)
ok("2b quota spent 50", state["quota"]["units_used"] == 50,
   f"({state['quota']['units_used']})")
ok("2c flag set", "captions_long" in state["episodes"][0]["text_layer"])
ok("2d multipart + vtt bytes",
   b"--fact0ry-text-layer-7f3a9c" in fake.calls[0][1]
   and b"WEBVTT" in fake.calls[0][1]
   and b'"videoId": "vid99"' in fake.calls[0][1])
ok("2e upload URL", "/upload/youtube/v3/captions" in fake.calls[0][0])

# idempotent: a resume must never re-post
n_before = len(fake.calls)
res = ai_layer.upload_captions("TOKEN", "vid99", vtt, state, 99, "captions_long")
ok("2f idempotent skip", res is True and len(fake.calls) == n_before)

res = ai_layer.post_summary_comment(
    "TOKEN", "vid99", metadata.summary_comment(story), state, 99)
ok("2g comment success", res is True)
ok("2h comment quota", state["quota"]["units_used"] == 100)
ok("2i comment endpoint", "commentThreads" in fake.calls[-1][0]
   and b"textOriginal" in fake.calls[-1][1])
ok("2j total 100 units", state["quota"]["units_used"] == 100,
   f"({state['quota']['units_used']} — the 2x50/day contract)")

# structural refusal: remembered forever, never retried
state2 = {"episodes": [{"n": 98}], "quota": {"date": None, "units_used": 0}}
refused = FakePost(400, b'{"error": {"errors": [{"reason": "captionForbidden"}]}}')
ai_layer._post = refused
res = ai_layer.upload_captions("TOKEN", "vid98", vtt, state2, 98, "captions_long")
ok("2k refusal returns False", res is False)
ok("2l refusal remembered", "captions" in state2["text_layer_refused"])
res = ai_layer.upload_captions("TOKEN", "vid98", vtt, state2, 98, "captions_long")
ok("2m never retried", res is False and len(refused.calls) == 1)
res = ai_layer.post_summary_comment("TOKEN", "vid98", "x", state2, 98)
ok("2n independent per surface", res is False and len(refused.calls) == 2
   and "summary_comment" in state2["text_layer_refused"])

# transient failure: NOT remembered — next cycle retries
state3 = {"episodes": [{"n": 97}], "quota": {"date": None, "units_used": 0}}
flaky = FakePost(503, b"backend error")
ai_layer._post = flaky
res = ai_layer.upload_captions("TOKEN", "vid97", vtt, state3, 97, "captions_long")
ok("2o transient skips", res is False and "text_layer_refused" not in state3)
ai_layer._post = FakePost(200, b"{}")
res = ai_layer.upload_captions("TOKEN", "vid97", vtt, state3, 97, "captions_long")
ok("2p transient retries next cycle", res is True)

# quota-low: bonus surface never spends the upload budget
state4 = {"episodes": [{"n": 96}],
          "quota": {"date": ledger._quota_today(), "units_used": 9970}}
lowfake = FakePost(200, b"{}")
ai_layer._post = lowfake
res = ai_layer.upload_captions("TOKEN", "vid96", vtt, state4, 96, "captions_long")
ok("2q quota-low skip", res is False and len(lowfake.calls) == 0)

print("== 3. attach_text_layer: the orchestrator entry point ==")
state5 = {"episodes": [{"n": 95}], "quota": {"date": None, "units_used": 0}}
good = FakePost(200, b"{}")
ai_layer._post = good
out = ai_layer.attach_text_layer(story, 95, "vid95", fake_narr, [],
                                 state5, TMP)
ok("3a both shipped", out.get("captions_long") == "ok"
   and out.get("comment") == "ok")
out2 = ai_layer.attach_text_layer(story, 95, "vid95", fake_narr, [],
                                  state5, TMP)
ok("3b resume = already", out2.get("captions_long") == "already"
   and out2.get("comment") == "already"
   and len(good.calls) == 2)          # nothing re-posted
ok("3c no long id = no-op",
   ai_layer.attach_text_layer(story, 94, None, fake_narr, [],
                              {"episodes": [], "quota": {"date": None,
                                                         "units_used": 0}},
                              TMP) == {})

# shorts captions (opt-in): narration.json per short work dir
orig_conf = ai_layer._conf
ai_layer._conf = lambda: {"captions": True, "captions_shorts": True,
                          "summary_comment": True}
state6 = {"episodes": [{"n": 93}], "quota": {"date": None, "units_used": 0}}
sfake = FakePost(200, b"{}")
ai_layer._post = sfake
n1 = story["shorts"][0]["n"]
swd = TMP / f"short_{n1:02d}"
swd.mkdir(parents=True, exist_ok=True)
(swd / "narration.json").write_text(json.dumps(fake_narr), encoding="utf-8")
out3 = ai_layer.attach_text_layer(story, 93, "vid93", fake_narr,
                                  ["sA", "sB"], state6, TMP)
ok("3d shorts caption flag", "captions_short_0" in state6["episodes"][0]
   ["text_layer"], f"({out3})")
ai_layer._conf = orig_conf

print("== 4. metadata: answer block + chapters IN the description ==")
meta = metadata.long_metadata(story, fake_narr)
desc = meta["description"]
answer = metadata._answer_block(story, len(story["atoms"]["concepts"]))
aw = len(answer.split())
ok("4a answer 30-80 words", 30 <= aw <= 80, f"({aw} words)")
ok("4b answer is liftable prose",
   answer.startswith("In plain words:") and answer.rstrip().endswith("tonight."))
ok("4c answer in description", answer in desc)
ok("4d chapters in description",
   "Chapters:\n0:00 " in desc and f"Tip 1: {story['atoms']['concepts'][0]}" in desc)
ok("4e every chapter line present",
   all(ln in desc for ln in meta["chapters"]))
ok("4f keyword head intact (first 150 chars)",
   desc.startswith("Psychology of love explained in plain words"))
ok("4g desc under 4900", len(desc) <= 4900, f"({len(desc)})")
ok("4h tags unchanged cap", len(meta["tags"]) <= 20)
ok("4i determinism", metadata.long_metadata(story, fake_narr)
   ["description"] == desc)

com = metadata.summary_comment(story)
ok("4j summary comment shape",
   com.startswith(f"Today's {len(story['atoms']['concepts'])} lessons")
   and "1. " in com and story.get("question", "1.") in com and "💜" in com)

print("== 5. thumbnails: 6-word cap, emotions, the checklist audit ==")
long_story = dict(story, title="Why the slowest reply often means "
                               "the deepest feeling actually")
ok("5a long title -> N lessons",
   thumbnails._pick_promise(long_story).split() == [
       str(len(story["atoms"]["concepts"])), "psychology", "lessons"])
short_story = dict(story, title="Chemistry vs Compatibility")
ok("5b short title kept", thumbnails._pick_promise(short_story)
   == "Chemistry vs Compatibility")

emos = set()
for s in (101, 202, 303, 404):
    a, b = thumbnails._thumb_emotions(s)
    emos.add(a)
ok("5c emotions from the approved set",
   emos <= {"inlove", "happy", "hopeful", "shy"}, f"({sorted(emos)})")
ok("5d pair mood unified", all(
    thumbnails._thumb_emotions(s)[0] == thumbnails._thumb_emotions(s)[1]
    for s in range(20)))

thumb = TMP / "thumb.png"
thumbnails.make_thumbnail(story, thumb, story["seed"])
rep = thumbnails.audit_thumbnail(story, thumb)
ok("5e audit passes", rep["ok"], f"({rep})")
ok("5f 120px measured", rep["px120_var"] > 100, f"(var {rep['px120_var']})")
ok("5g promise <= 6 words", rep["words"] <= 6, f"({rep['words']} words)")
ok("5h png under 2MB", rep["png_kb"] < 2048, f"({rep['png_kb']}KB)")
# fail-open contract: a broken PNG is a WARNING, not an exception
bad = TMP / "bad.png"
bad.write_bytes(b"not a png")
rep2 = thumbnails.audit_thumbnail(story, bad)
ok("5i audit fails gracefully", rep2["ok"] is False and rep2["fails"])

print("== 6. Pop-in CTA curve (seam-exact landing) ==")
s0, s1 = anim.pop_scale(0.0), anim.pop_scale(1.0)
ok("6a starts at feed-thumbnail scale", abs(s0 - 1.055) < 1e-12)
ok("6b lands EXACTLY on 1.0", s1 == 1.0)
curve = [anim.pop_scale(i / 100.0) for i in range(101)]
ok("6c one undershoot exists", min(curve) < 0.999 and min(curve) > 0.985,
   f"(min {min(curve):.4f})")
ok("6d never above the start", max(curve) <= 1.055 + 1e-12)
ok("6e legacy ease-out unchanged",
   abs(anim.pop_scale(0.5, pop=False) - (1.055 - 0.055 * 0.875)) < 1e-12)
tail = curve[75:]
ok("6f perceptually settled by 3/4 (subpixel micro-settle only)",
   max(tail) - min(tail) < 0.002 and curve[-1] == 1.0,
   f"(tail spread {max(tail) - min(tail):.5f} — 'perceptual duration': "
   f"feels finished, micro-settles underneath)")

# the real render path: a CTA-style card through render_clip_art with
# pop=True — the intro must exist as a _intro_dip_pop.mp4 clip of
# exactly the intro length (the seam contract lives in the filenames)
from src import art_engine, render  # noqa: E402
scene = next(s for s in story["scenes"]
             if s.get("image", {}).get("kind") == "couple_scene")
layers = art_engine.build_scene_layers(scene, story["seed"] + scene["n"] * 13)
cta_clip = TMP / "cta_card.mp4"
render.render_clip_art(layers, story["seed"], cta_clip, 4.0, "zoom_in",
                       card_idx=7, accent=True, pop=True)
intro_pop = TMP / "cta_card_intro_dip_pop.mp4"
ok("6g pop intro rendered + cached under its own name", intro_pop.exists())
info = render.probe(intro_pop)
ok("6h pop intro is the 0.30s entrance",
   0.25 < float(info["format"]["duration"]) < 0.40,
   f"({float(info['format']['duration']):.2f}s)")
ok("6i the loop + final clip still render (seam contract intact)",
   cta_clip.exists() and len(list(TMP.glob("cta_card_loop*_rig.mp4"))) == 1,
   f"(final {cta_clip.stat().st_size/1e6:.2f}MB)")

print("== 7. upload snippet: the inert chapters key never sent ==")
recorded = {}


def fake_upload(token, filepath, variant, status, state=None, **kw):
    recorded.update(variant)
    return "vidNEW"


youtube.get_access_token = lambda: "TOKEN"
youtube._find_video_by_title = lambda *a, **k: None
youtube._upload_video = fake_upload
meta_in = {"title": "Test: the chapters key", "description": "d",
           "tags": ["a"], "chapters": ["0:00 x", "0:04 y"]}
f = TMP / "fake.mp4"
f.write_bytes(b"\0" * 1024)
st = {"episodes": [], "stats": {},
      "quota": {"date": None, "units_used": 0}}
vid = youtube.upload_video(f, meta_in, None, 92, "long", st)
ok("7a upload returned", vid == "vidNEW")
ok("7b chapters stripped from snippet", "chapters" not in recorded)
ok("7c real snippet keys intact",
   recorded.get("title") == "Test: the chapters key"
   and recorded.get("categoryId") == "24")

print(f"\nALL {PASSED} CHECKS PASS — the free-skill upgrades are "
      f"regression-locked.")
