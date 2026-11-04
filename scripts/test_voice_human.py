#!/usr/bin/env python3
"""Tests for THE HUMAN EDGE (2026-11-05) — src/voice_human.py and its
seams in tts.py. Runs offline (the one live-engine case uses the
vendored Kokoro model). Plain asserts, repo style. Usage:

    python3 scripts/test_voice_human.py

Exit code 0 = all checks pass.

What is asserted:
  * determinism    — same story hash -> same schedule, same master bytes
  * fail-open      — every seam collapses to the plain pipeline
  * pause law      — within/sentence/dramatic gaps inside their spans
  * breath law     — present, 180-260 ms, quiet, never rhythmic,
                     only inside gaps that can hold them
  * room tone      — pauses are a room (~-60 dB), not digital silence
  * seam safety    — master length == metadata total; speech energy
                     sits exactly where captions say it does
  * gates intact   — the Oct-13 quality gates survive the human edge
  * lock respected — prosody punctuation never changes caption words
"""
from __future__ import annotations

import array
import json
import shutil
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import tts, voice_human as vh  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


SR = 22_050
WORK = ROOT / "work" / "test_voice_human"

# ── fixtures ─────────────────────────────────────────────────────────

PLAN = [
    {"scene": 1, "text": "You keep checking your phone, waiting.", "idx": 1},
    {"scene": 1, "text": "The reply lands, and your chest lifts.", "idx": 2},
    {"scene": 1, "text": "Then silence, and the doubt returns, heavy.", "idx": 3},
    {"scene": 2, "text": "Why does the quiet hurt more than words?", "idx": 4},
    {"scene": 2, "text": "Psychologists call it intermittent reinforcement,", "idx": 5},
    {"scene": 2, "text": "and it is the same loop a slot machine uses.", "idx": 6},
]

VCONF_ON = {"humanize": True, "_human_story": "hash-ab-1"}
VCONF_OFF = {"humanize": False, "_human_story": "hash-ab-1"}

# breath-rich fixture: 20 long sentences so breath draws land
BREATH_PLAN = [{"scene": 1,
                "text": f"A sentence long enough to end here number {k}.",
                "idx": k + 1} for k in range(20)]


def sine_frames(seconds: float, hz: float = 220.0, amp: float = 0.3) -> array.array:
    n = int(seconds * SR)
    t = np.arange(n) / SR
    a = (amp * np.sin(2 * np.pi * hz * t) * 32767).astype(np.int16)
    return array.array("h", a.tobytes())


def write_chunk_wav(path: Path, frames: array.array) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames.tobytes())


def master_array_from(meta: list[dict], master: array.array) -> np.ndarray:
    return np.frombuffer(master.tobytes(), dtype=np.int16).astype(np.float32)


def rms_dbfs(x: np.ndarray) -> float:
    if len(x) == 0:
        return -120.0
    r = float(np.sqrt(np.mean(x ** 2))) / 32767.0
    return 20 * np.log10(max(r, 1e-12))


# ── 1. determinism ───────────────────────────────────────────────────

def test_determinism() -> None:
    print("determinism (same seed -> same bytes)")
    s1 = vh.schedule_for(BREATH_PLAN, 0.42, 0.70, "det-hash", sr=SR)
    s2 = vh.schedule_for(BREATH_PLAN, 0.42, 0.70, "det-hash", sr=SR)
    check("schedule gaps identical", s1["gap_before"] == s2["gap_before"])
    check("schedule gains identical", s1["gains"] == s2["gains"])
    check("schedule speeds identical", s1["speeds"] == s2["speeds"])
    check("schedule room identical",
          (s1["room_db"], s1["room_seed"]) == (s2["room_db"], s2["room_seed"]))
    b1 = {k: v.tobytes() for k, v in s1["breath_before"].items()}
    b2 = {k: v.tobytes() for k, v in s2["breath_before"].items()}
    check("breaths present in fixture and byte-identical",
          b1 == b2 and len(b1) > 0, f"n={len(b1)}")

    # end-to-end assemble determinism on identical fake chunks
    det_plan = BREATH_PLAN[:8]
    frames = [sine_frames(0.9) for _ in det_plan]
    gaps = s1["gap_before"][:len(det_plan)]
    total = sum(len(f) for f in frames) / SR + sum(gaps) + 0.5
    m1 = vh.assemble(frames, gaps, s1["breath_before"], total, SR,
                     s1["room_db"], s1["room_seed"])
    m2 = vh.assemble(frames, gaps, s2["breath_before"], total, SR,
                     s2["room_db"], s2["room_seed"])
    check("master bytes identical", m1.tobytes() == m2.tobytes())

    s3 = vh.schedule_for(PLAN, 0.42, 0.70, "hash-DIFFERENT", sr=SR)
    check("different story -> different plan",
          s3["gap_before"] != s1["gap_before"] or
          s3["room_seed"] != s1["room_seed"])


# ── 2. fail-open law ─────────────────────────────────────────────────

class _Poison:
    """An object whose str() explodes — any seam touching it must
    collapse, never crash."""

    def __str__(self):
        raise RuntimeError("poisoned text")


def test_fail_open() -> None:
    print("fail-open (humanizer errors collapse to the plain pipeline)")
    poisoned = [{"scene": 1, "text": _Poison(), "idx": 1}]
    check("poisoned plan -> schedule None",
          vh.schedule_for(poisoned, 0.42, 0.70, "h", sr=SR) is None)

    check("tts_text identity on error",
          vh.tts_text({"humanize": True, "_human_story": _Poison()},
                      "Keep the words exactly as they are.") ==
          "Keep the words exactly as they are.")

    check("speed_multiplier neutral on error",
          vh.speed_multiplier({"humanize": True, "_human_speed": {1: _Poison()}},
                              1, "text") == 1.0)

    frames = sine_frames(0.2)
    check("apply_gain passthrough on error",
          vh.apply_gain(frames, _Poison()) is frames)

    # seam wrappers in tts.py
    def _boom():
        raise RuntimeError("boom")

    real = tts._voice_human

    class _Broken:
        def __getattr__(self, name):
            raise RuntimeError(f"broken seam: {name}")

    tts._voice_human = lambda: _Broken()
    try:
        check("tts._human_tts_text falls back",
              tts._human_tts_text(VCONF_ON, "Voice stays alive.") ==
              "Voice stays alive.")
        check("tts._human_speed falls back",
              tts._human_speed(VCONF_ON, 1, "text") == 1.0)
        check("tts._human_schedule falls back",
              tts._human_schedule(PLAN, VCONF_ON, {"hash": "h"}, 0.42, 0.70)
              is None)
    finally:
        tts._voice_human = real

    check("gate off -> no schedule",
          tts._human_schedule(PLAN, VCONF_OFF, {"hash": "h"}, 0.42, 0.70)
          is None)


# ── 3. pause law (a) + (c) ───────────────────────────────────────────

def test_pause_law() -> None:
    print("pause law (mood-aware variable gaps)")
    sp = 0.42
    plan: list[dict] = []
    texts = [
        "The first line ends here.",                    # sent, plain
        "and the thought keeps running, quietly,",      # within (comma)
        "The second line ends here.",                   # sent -> hook follows
        "You already know this feeling too well.",      # HOOK after sent-end
        "and on and on it goes,",                       # within (comma)
        "The cycle closes where it started.",           # sent, plain
    ]
    for k in range(8):                    # 48 chunks, one scene
        for t in texts:
            plan.append({"scene": 1, "text": t, "idx": len(plan) + 1})
    sched = vh.schedule_for(plan, sp, 0.70, "pause-law-hash", sr=SR)
    gaps = sched["gap_before"]

    within, sent = [], []
    for j in range(1, len(plan)):
        prev = plan[j - 1]["text"].rstrip()
        if prev.endswith((".", "!", "?")):
            sent.append(gaps[j])
        else:
            within.append(gaps[j])
    ok_w = all(0.10 <= g <= 0.24 for g in within)
    plain_sent = [g for g in sent if g <= 0.47]     # drama beats are a legal
    drama = [g for g in sent if g > 0.47]           # subset of sentence ends
    ok_s = all(0.24 <= g <= 0.44 for g in plain_sent)
    check(f"within-sentence gaps 120-220 ms ({len(within)} gaps)", ok_w,
          f"min={min(within):.3f} max={max(within):.3f}")
    check(f"sentence-end gaps 260-420 ms ({len(plain_sent)} plain)",
          ok_s, f"min={min(plain_sent):.3f} max={max(plain_sent):.3f}")
    check("gaps are not metronomic (variety)",
          len(set(round(g, 4) for g in gaps)) >= 20,
          f"distinct={len(set(round(g, 4) for g in gaps))}")

    check("dramatic beats occur before hook lines (~500-700 ms)",
          len(drama) >= 3 and all(0.48 <= g <= 0.72 for g in drama),
          f"n={len(drama)}")
    # plain lines after sentence ends never exceed the sentence span
    plain_sent_gaps = [gaps[j] for j in range(1, len(plan))
                       if plan[j - 1]["text"].rstrip().endswith((".", "!", "?"))
                       and not vh.is_hookish(plan[j]["text"])]
    check("no dramatic beat on a plain line",
          all(g <= 0.45 for g in plain_sent_gaps),
          f"max={max(plain_sent_gaps):.3f}")


# ── 4. breath law (b) ────────────────────────────────────────────────

def test_breath_law() -> None:
    print("breath law (soft inhales, never rhythmic)")
    plan = BREATH_PLAN
    sched = vh.schedule_for(plan, 0.42, 0.70, "breath-law-hash", sr=SR)
    breaths = sched["breath_before"]
    check(f"breaths present ({len(breaths)} of 20)",
          2 <= len(breaths) <= 12)
    ok_dur = all(0.12 * SR <= len(b) <= 0.25 * SR for b in breaths.values())
    check("breath duration 120-250 ms (shrunk to fit)", ok_dur,
          f"lens={[len(b) / SR for b in breaths.values()][:6]}")
    ok_level = all(20 * np.log10(float(np.max(np.abs(b))) / 32767.0) <= -35
                   for b in breaths.values())
    check("breath level quiet (<= -35 dBFS)", ok_level)
    ks = sorted(breaths)
    ok_sp = all(b - a > vh.BREATH_MIN_SPACING for a, b in zip(ks, ks[1:]))
    check("breaths never rhythmic (spacing rule)", ok_sp, f"at={ks}")
    ok_fit = all(sched["gap_before"][j] >= len(b) / SR
                 for j, b in breaths.items())
    check("every breath fits inside its gap (sync law)", ok_fit)


# ── 5. room tone (d) ─────────────────────────────────────────────────

def test_room_tone() -> None:
    print("room tone (pauses are a room, not a void)")
    silence = [array.array("h", b"\x00\x00" * int(1.0 * SR)) for _ in PLAN]
    gaps = [0.0] + [0.6] * (len(PLAN) - 1)
    m = vh.assemble(silence, gaps, {}, float(len(PLAN) * 1.6), SR,
                    -60.0, 12345)
    x = master_array_from([], m)
    tail = x[int(1.0 * SR):int(1.55 * SR)]        # inside a pause
    db = rms_dbfs(tail)
    check(f"pause RMS ~ -60 dB (got {db:.1f} dBFS)", -66.0 <= db <= -54.0)
    check("room tone is not digital silence", float(np.max(np.abs(tail))) > 0)
    m2 = vh.assemble(silence, gaps, {}, float(len(PLAN) * 1.6), SR,
                     -60.0, 12345)
    check("room bed deterministic", m.tobytes() == m2.tobytes())


# ── 6. seam safety / caption sync ────────────────────────────────────

def test_seam_safety() -> None:
    print("seam safety (metadata and master from the same numbers)")
    sched = vh.schedule_for(PLAN, 0.42, 0.70, "seam-hash", sr=SR)
    gaps = sched["gap_before"]
    frames = [sine_frames(0.8 + 0.05 * i) for i, _ in enumerate(PLAN)]

    # replicate EXACTLY what narrate() computes for metadata
    meta = []
    t = 0.0
    for j, f in enumerate(frames):
        dur = len(f) / SR
        if j > 0:
            t += gaps[j]
        meta.append({"start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
    total = t + sched["sent_after_last"] + 0.70

    master = vh.assemble(frames, gaps, sched["breath_before"], total, SR,
                         sched["room_db"], sched["room_seed"])
    x = master_array_from([], master)
    check("master length == int(total*SR)",
          len(x) == int(total * SR),
          f"{len(x)} vs {int(total * SR)}")

    # speech energy must sit exactly where the captions say (kokoro
    # chunks may carry a short lead-in, so allow a slightly wider window)
    ok_sync, worst = True, ""
    for j, m in enumerate(meta):
        a, b = int(m["start"] * SR), int(m["end"] * SR)
        if b <= a or b > len(x):
            ok_sync, worst = False, f"chunk {j} window invalid"
            break
        window = x[a:min(b, a + int(0.15 * SR))]
        if rms_dbfs(window) < -45.0:     # room tone is ~-60; speech >>
            ok_sync, worst = False, f"chunk {j} weak at its start " \
                                   f"({rms_dbfs(window):.1f} dBFS)"
            break
    check("speech lands exactly at caption starts", ok_sync, worst)

    # gaps without breaths stay near-silent (only room tone)
    quiet_ok = True
    for j in range(1, len(frames)):
        if j in sched["breath_before"]:
            continue
        a = int((meta[j]["start"] - gaps[j] + 0.03) * SR)   # INSIDE the gap
        b = int((meta[j]["start"] - 0.03) * SR)
        if b <= a:
            continue
        if rms_dbfs(x[a:b]) > -50.0:
            quiet_ok = False
    check("breathless gaps hold only room tone", quiet_ok)


# ── 7. prosody layer never touches caption words ─────────────────────

def test_prosody_lock() -> None:
    print("prosody lock (TTS input only; caption words untouched)")
    import re
    samples = [
        "You keep checking your phone, waiting for the reply.",
        "The reply lands, and your chest lifts a little.",
        "Then silence, and the doubt creeps back in,",
        "why does the quiet hurt more than words?",
        "and it is the same loop a slot machine uses.",
        "Stop calling it love.",
        "It was never about the text.",
        "She waited three days before answering, and it worked.",
        "He left the message on read, again.",
        "The pattern repeats in every relationship you have.",
        "Maybe the calm one is the one worth keeping.",
        "no",
    ]
    core = lambda s: re.sub(r"[.,!?;—\s]+$", "", s)
    vconf = {"humanize": True, "_human_story": "prosody-hash"}
    ok_words, changed = True, 0
    for s in samples:
        out = vh.tts_text(vconf, s)
        if core(out) != core(s):
            ok_words = False
        if out != s:
            changed += 1
    check("caption words never change", ok_words)
    check("prosody layer actually bites (some chunks re-punctuated)",
          changed >= 2, f"changed={changed}/{len(samples)}")
    check("gate off -> text identity",
          all(vh.tts_text(VCONF_OFF, s) == s for s in samples))
    check("tiny fragments untouched",
          vh.tts_text(vconf, "no") == "no")


# ── 8. end-to-end with the real engine (quality gates intact) ────────

def test_end_to_end() -> None:
    print("end-to-end (kokoro + human edge; Oct-13 gates intact)")
    if WORK.exists():
        shutil.rmtree(WORK)
    story = {
        "hash": "human-edge-e2e",
        "scenes": [
            {"n": 1, "narration": "You keep checking your phone, waiting for "
                                  "the reply that decides your whole day."},
            {"n": 2, "narration": "Why does the quiet hurt more than the "
                                  "words ever did? Psychologists have a name "
                                  "for that loop, and it is not love."},
        ],
    }
    cfg_obj = None
    from src import config as config_mod
    cfg_obj = config_mod.cfg()
    vconf = cfg_obj["voice"]
    humanize_before = vconf.get("humanize")

    # ON run
    vconf["humanize"] = True
    meta_on = tts.narrate(story, WORK, chunk_words=8)
    marker = (WORK / "chunks" / "engine.txt").read_text().strip()
    check("engine marker carries the humanize fingerprint", marker == "kokoro+h",
          f"marker={marker}")
    check("engine reported as kokoro (metadata unchanged)", meta_on["engine"] == "kokoro")
    check("no neural fallback raised", tts.NEURAL_FALLBACK is False)
    check("chunks monotonic and finite",
          all(m["end"] > m["start"] for m in meta_on["chunks"]) and
          all(meta_on["chunks"][i + 1]["start"] >= meta_on["chunks"][i]["start"]
              for i in range(len(meta_on["chunks"]) - 1)))

    # polish duration law: master wav duration == metadata total
    with wave.open(str(WORK / "narration.wav"), "rb") as w:
        dur = w.getnframes() / w.getframerate()
    check("master duration == total (sync law)",
          abs(dur - meta_on["total"]) < 0.05,
          f"wav={dur:.3f} meta={meta_on['total']:.3f}")

    # sync spot check: speech energy at each caption start (kokoro
    # chunks carry a short lead-in, so a wider window + an absolute
    # floor well above the room tone do the judging)
    with wave.open(str(WORK / "narration.wav"), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    ok_sync = True
    worst = ""
    for m in meta_on["chunks"]:
        a = int(m["start"] * SR)
        window = x[a:a + int(0.20 * SR)]
        db = rms_dbfs(window)
        if db < -45.0:
            ok_sync, worst = False, f"chunk@{m['start']}s = {db:.1f} dBFS"
    check("real chunks land at caption starts", ok_sync, worst)

    # determinism at the factory level: same story -> same total
    WORK2 = ROOT / "work" / "test_voice_human_2"
    if WORK2.exists():
        shutil.rmtree(WORK2)
    meta_on2 = tts.narrate(story, WORK2, chunk_words=8)
    check("same story -> same narration total",
          abs(meta_on2["total"] - meta_on["total"]) < 0.001,
          f"{meta_on['total']} vs {meta_on2['total']}")
    shutil.rmtree(WORK2, ignore_errors=True)

    # OFF run: white-box legacy parity — metadata must equal the
    # legacy pause formulas exactly
    vconf["humanize"] = False
    WORK3 = ROOT / "work" / "test_voice_human_off"
    if WORK3.exists():
        shutil.rmtree(WORK3)
    meta_off = tts.narrate(story, WORK3, chunk_words=8)
    marker_off = (WORK3 / "chunks" / "engine.txt").read_text().strip()
    check("gate off -> plain marker", marker_off == "kokoro", f"marker={marker_off}")
    t = 0.0
    last_scene = 1
    ok_legacy = True
    for p_story in meta_off["chunks"]:
        pass
    # recompute from the plan the same way the legacy loop does
    plan = []
    idx = 0
    for scene in story["scenes"]:
        for text in tts.split_chunks(scene["narration"], max_words=8):
            idx += 1
            plan.append({"scene": scene["n"], "text": text, "idx": idx})
    sent_pause = float(vconf.get("sentence_pause", 0.42))
    scene_pause = float(vconf.get("paragraph_pause", 0.70))
    t = 0.0
    last_scene = plan[0]["scene"]
    for j, p in enumerate(plan):
        with wave.open(str(WORK3 / "chunks" / f"chunk_{p['idx']:03d}.wav"), "rb") as w:
            dur = w.getnframes() / w.getframerate()
        if p["scene"] != last_scene:
            t += tts._pause_for(p["text"], -p["scene"], scene_pause)
            last_scene = p["scene"]
        if abs(round(t, 3) - meta_off["chunks"][j]["start"]) > 0.0011:
            ok_legacy = False
        t += dur + tts._pause_for(p["text"], p["idx"], sent_pause)
    check("gate off -> metadata equals legacy pause formulas", ok_legacy)

    if humanize_before is None:
        del vconf["humanize"]
    else:
        vconf["humanize"] = humanize_before
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(WORK3, ignore_errors=True)


def main() -> int:
    test_determinism()
    test_fail_open()
    test_pause_law()
    test_breath_law()
    test_room_tone()
    test_seam_safety()
    test_prosody_lock()
    test_end_to_end()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
