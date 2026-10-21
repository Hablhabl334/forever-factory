#!/usr/bin/env python3
"""Viral-upgrade regression suite (2026-10-16).

Covers the three upgrades shipped together:
  1. VOICE   — Kokoro-82M as the primary LOCAL engine (vendored in
               assets/voice_kokoro/), engine ladder kokoro -> edge ->
               piper; kokoro never sets NEURAL_FALLBACK; the quality
               gate treats kokoro as full quality.
  2. HOOKS   — every Short script opens with a pattern interrupt
               (OPENERS) and closes with an engagement question
               (COMMENT_QUESTIONS) before the CTA; openers are unique
               within an episode; the long's outro + descriptions
               carry the question.
  3. PACING  — shorts narrate with 9-word caption chunks (faster card
               rhythm) and the word band is recalibrated for the
               local voice's ~150-wpm pace (125-205 words -> 50-82 s,
               inside the owner's 45 s floor / 90 s cap).

Audio-touching checks are conditional on the vendored model being
present so the suite stays green on machines without the 120 MB of
weights.
"""
from __future__ import annotations

import re
import sys
import types
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import tts as tts_mod
from src.content_data import CTA_LINE, CONCEPTS
from src.content_variants import COMMENT_QUESTIONS, OPENERS
from src.story_engine import generate_story

PASS = FAIL = 0


def check(name: str, got, want=True) -> None:
    global PASS, FAIL
    ok = (got == want) if isinstance(want, bool) else (got == want)
    if ok:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}: got {got!r}, want {want!r}")


# ── 1. the pools ─────────────────────────────────────────────────────
print("== viral pools ==")
check("OPENERS: 25+ interrupt lines", len(OPENERS) >= 25)
check("OPENERS: every opener is 2-7 words",
      all(2 <= len(o.split()) <= 7 for o in OPENERS))
check("QUESTIONS: 10+ engagement closers", len(COMMENT_QUESTIONS) >= 10)
check("QUESTIONS: every one asks for interaction",
      all(re.search(r"comment|below|tell|tag|heart|same|count", q, re.I)
          for q in COMMENT_QUESTIONS))
banned = re.compile(
    r"diagnos|disorder|medicin|guaranteed|manipulat|narcissist|"
    r"sociopath|mental illness|therapy session|toxic person|"
    r"you are broken|\bcures?\b", re.I)
check("OPENERS pass the safety audit", not banned.search(" ".join(OPENERS)))
check("QUESTIONS pass the safety audit",
      not banned.search(" ".join(COMMENT_QUESTIONS)))

# ── 2. script structure ─────────────────────────────────────────────
print("== shorts script structure ==")
STORY = generate_story(20261016)
for i, sh in enumerate(STORY["shorts"][:4], start=1):
    check(f"short {i} opens with an OPENERS line",
          any(sh["script"].startswith(o) for o in OPENERS))
    check(f"short {i} ends with the CTA",
          sh["script"].rstrip().endswith(CTA_LINE))
    q = sh["script"].rstrip().rsplit(CTA_LINE, 1)[0]
    # 2026-10-21 fix: {term}-bearing templates must be REPLACED before
    # the substring check — the raw template can never appear in a script
    check(f"short {i} carries an engagement question before the CTA",
          any(question.replace("{term}", CONCEPTS[sh["concept"]]["term"]) == q
              or question.replace("{term}", CONCEPTS[sh["concept"]]["term"]) in q
              for question in COMMENT_QUESTIONS))
    check(f"short {i} word band 125-205",
          125 <= sh["words"] <= 205, True)

openers_used = [sh["script"].split(".")[0] for sh in STORY["shorts"][:4]]
check("openers unique within the episode", len(set(openers_used)) == 4)

check("episode carries a question", bool(STORY.get("question")))
outro = STORY["scenes"][-1]["narration"]
check("long outro speaks the question", STORY["question"] in outro)

# ── 3. metadata surfaces the question ───────────────────────────────
print("== metadata ==")
from src.metadata import short_metadata, long_metadata
sm = short_metadata(STORY, STORY["shorts"][0])
check("short description opens with the question",
      sm["description"].startswith(STORY["question"]))
check("short title untouched (owner rule)",
      sm["title"] == "Subscribe for more tips like this #psychology "
      "#relationship #love #relationshipgoals")
fake_narr = {"scene_durations": [6.0] * len(STORY["scenes"])}
lm = long_metadata(STORY, fake_narr)
check("long description contains the question",
      STORY["question"] in lm["description"])

# ── 4. engine ladder + kokoro helpers ───────────────────────────────
print("== engine ladder ==")
from src.config import cfg
vconf = dict(cfg()["voice"])

m, v = tts_mod.kokoro_model_paths(vconf)
check("kokoro model path is the vendored file",
      m.name == "kokoro-v1.0.int8.onnx"
      and m.parent.name == "voice_kokoro")
check("kokoro voices path is the vendored file", v.name == "voices-v1.0.bin")
check("vendored files actually present (this repo)", tts_mod.kokoro_available(vconf))

# speed mapping: edge-style -3% -> 0.97, shorts -1% -> 0.99, clamp 0.5-2
check("speed map: None -> config base", round(
    tts_mod._kokoro_speed_for({"kokoro_speed": 0.96}, None), 4) == 0.96)
check("speed map: -3% -> 0.97", round(
    tts_mod._kokoro_speed_for({}, "-3%"), 4) == 0.97)
check("speed map: -1% -> 0.99", round(
    tts_mod._kokoro_speed_for({}, "-1%"), 4) == 0.99)
check("speed map: -25% clamps at 0.75", round(
    tts_mod._kokoro_speed_for({}, "-25%"), 4) == 0.75)
check("speed map: +400% clamps at 2.0", round(
    tts_mod._kokoro_speed_for({}, "+400%"), 2) == 2.0)

# narrate() prefers kokoro when the files exist (offline machine:
# engine 'edge' config bypasses it, 'auto' uses it)
print("== engine selection (unit, no synthesis) ==")
_here = Path(ROOT / "work" / "_ladder_probe")
_here.mkdir(parents=True, exist_ok=True)
_real_edge_pick = tts_mod._edge_pick_voice
_real_kokoro_probe = tts_mod._kokoro_probe
_real_kokoro_synth = tts_mod._kokoro_synth_all
_real_edge_synth = tts_mod._edge_synth_all
tts_mod._EDGE_DECISION = None
try:
    # a) auto + kokoro present + probe succeeds -> kokoro
    tts_mod._kokoro_probe = lambda v: True
    calls = {"edge": 0}
    def _fake_pick(v, c):
        calls["edge"] += 1
        return "en-US-JennyNeural"
    tts_mod._edge_pick_voice = _fake_pick
    story_t = {"hash": "ladder-a", "scenes": [
        {"n": 1, "narration": "Hello there friend of mine."}]}
    # fake the actual synthesis: piper path would need the model;
    # monkeypatch _kokoro_synth_all to write silence chunks
    import array as _arr
    def _fake_kokoro(items, cd, vconf, rate_pct=None):
        for idx, _ in items:
            tts_mod.write_wav(cd / f"chunk_{idx:03d}.wav",
                              _arr.array("h", [100] * 4410))
    tts_mod._kokoro_synth_all = _fake_kokoro
    import shutil
    wt = _here / "a"; shutil.rmtree(wt, ignore_errors=True)
    meta = tts_mod.narrate(story_t, wt)
    check("auto + local model -> engine kokoro", meta.get("engine"), "kokoro")
    check("edge picker never called", calls["edge"], 0)
    check("kokoro engine never flags degradation",
          tts_mod.NEURAL_FALLBACK, False)

    # b) kokoro probe fails -> falls to the edge ladder
    tts_mod._kokoro_probe = lambda v: False
    tts_mod._EDGE_DECISION = "en-US-JennyNeural"
    def _fake_edge(items, cd, vconf):
        for idx, _ in items:
            tts_mod.write_wav(cd / f"chunk_{idx:03d}.wav",
                              _arr.array("h", [100] * 4410))
    tts_mod._edge_synth_all = _fake_edge
    wt = _here / "b"; shutil.rmtree(wt, ignore_errors=True)
    meta = tts_mod.narrate({"hash": "ladder-b", "scenes": [
        {"n": 1, "narration": "Hello there friend of mine."}]}, wt)
    check("kokoro broken -> engine edge", meta.get("engine"), "edge")
    check("edge fallback stays silent on the flag",
          tts_mod.NEURAL_FALLBACK, False)
finally:
    tts_mod._edge_pick_voice = _real_edge_pick
    tts_mod._EDGE_DECISION = None
    # restore every engine monkeypatch — later sections (and the live
    # smoke below) must see the REAL implementations
    for name, orig in (("_kokoro_probe", _real_kokoro_probe),
                       ("_kokoro_synth_all", _real_kokoro_synth),
                       ("_edge_synth_all", _real_edge_synth)):
        setattr(tts_mod, name, orig)
    import shutil
    shutil.rmtree(_here, ignore_errors=True)

# ── 5. chunk width ──────────────────────────────────────────────────
print("== pacing ==")
chunks = tts_mod.split_chunks(
    "The person who chases and the person who retreats always find "
    "each other, and that is not chemistry, it is a circuit.",
    max_words=9)
check("shorts chunk width: every chunk <= 9 words",
      all(len(c.split()) <= 9 for c in chunks))
check("shorts chunk width: splits long sentences",
      len(chunks) >= 3)

# ── 6. LIVE kokoro smoke (only when the model is present) ───────────
print("== live kokoro smoke ==")
if tts_mod.kokoro_available(vconf):
    try:
        import time
        from src import tts as T
        w = ROOT / "work" / "_viral_smoke"
        import shutil as sh
        sh.rmtree(w, ignore_errors=True)
        t0 = time.time()
        # 2026-10-21: ~80 words (~32 s of audio) — a 4 s smoke could not
        # amortize the model load, so the factor measured cold-start
        # overhead, not steady-state throughput (the property that
        # matters for the daily render window)
        n = T.narrate({"hash": "smoke-kokoro", "scenes": [
            {"n": 1, "narration": "Read this twice. If they only reply "
             "when you are about to give up, that is not bad luck. "
             "Monday you text, Thursday they answer, warm and perfect, "
             "then a week of nothing. The uncertainty itself becomes "
             "the hook, because a maybe demands constant attention. "
             "That is why an inconsistent person can feel more intense "
             "than a consistent one. Consistency is the real green "
             "flag, and calm is a nervous system finally resting."}]},
            w, sent_pause=0.26, scene_pause=0.30, rate_pct="-1%",
            chunk_words=9)
        check("live smoke: engine kokoro", n["engine"], "kokoro")
        check("live smoke: narration has duration", n["total"] > 3.0)
        with wave.open(str(w / "narration.wav")) as f:
            check("live smoke: master wav at 22050 Hz",
                  f.getframerate(), 22050)
            check("live smoke: master wav mono", f.getnchannels(), 1)
        check("live smoke: realtime factor >= 1.0x",
              (n["total"] / max(time.time() - t0, 0.01)) >= 1.0)
        sh.rmtree(w, ignore_errors=True)
    except Exception as exc:  # model present but engine broken -> LOUD
        check(f"live smoke raised unexpectedly: {exc}", False)
else:
    print("  (vendored kokoro model absent — live smoke skipped)")

# ── 7. determinism + no-repeat still hold ───────────────────────────
print("== determinism ==")
s2 = generate_story(20261016)
check("same seed -> same episode hash", s2["hash"], STORY["hash"])
check("same seed -> same shorts hashes",
      s2["short_hashes"][:4], STORY["short_hashes"][:4])
h1 = {sh["shash"] for sh in STORY["shorts"]}
check("episode shorts never repeat a script", len(h1), len(STORY["shorts"]))

print()
if FAIL:
    print(f"✗ {FAIL} test(s) failed")
    sys.exit(1)
print(f"✓ all viral-upgrade tests passed ({PASS} checks)")
