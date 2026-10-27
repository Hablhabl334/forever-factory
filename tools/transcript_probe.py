#!/usr/bin/env python3
"""transcript_probe — free competitor transcript study (batch-2 skills,
2026-10-27).

The youtube-transcript / baoyu-youtube-transcript / yt-dlp skills all
teach the same free doctrine: a video's transcript is public, free,
and the most honest performance data that exists — what winners SAY,
not what their titles claim. This tool extends the Sunday benchmark's
title-level steal list down to the PHRASE level:

    python3 tools/transcript_probe.py <url-or-id> [url-or-id ...]

For each video (read-only, zero API quota — yt-dlp fetches the
auto-generated English subtitle track the same way the trend-intel
discovery path works):

  * THE FIRST 15 SECONDS — the spoken hook block, verbatim (what
    actually opens the video, where retention is decided)
  * pace — words, est. spoken minutes at 150 wpm, words-per-sentence
  * the repeated phrase layer — top 2-4-word content phrases by
    frequency (the vocabulary the video is REALLY about)
  * full plain text saved to data/probe/<id>.txt for the agent to
    read in-session with any transcript skill

Never in the daily loop (manual/weekly, next to compete.py). Never
automated watching or engagement — read-only is the honesty fence.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

# the same stopword fence trend_intel uses, extended for subtitles
_STOP = frozenset("""
the a an and or but is are was were be been being you your yours it its
to of in on at for with that this these those not no yes they them their
he she his her we us our i me my mine as from by so than then there here
what when where which who whom why how all any both each few more most
other some such only own same too very can will just don should now
like really ever never always gonna wanna got get gotcha oh um uh
things thing way ways one two three first second next last make makes
made say says said know knows going want wants lot bit yeah okay
""".split())


def _probe_dir() -> Path:
    d = Path("data/probe")
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_transcript(video: str) -> tuple[str, str]:
    """yt-dlp auto-sub fetch — returns (video_id, plain_text).

    Uses --write-auto-subs --skip-download (no video bytes, no API
    quota). Falls back to any en.* track YouTube generated.
    """
    vid = video.rstrip("/").split("=")[-1].split("/")[-1][-11:]
    if not re.fullmatch(r"[\w-]{11}", vid):
        sys.exit(f"cannot parse a video id out of: {video!r}")
    with tempfile.TemporaryDirectory(prefix="probe-") as td:
        out_tmpl = str(Path(td) / "%(id)s")
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", "en.*",
            "--sub-format", "vtt",
            "-o", out_tmpl,
            "--no-warnings",
            f"https://www.youtube.com/watch?v={vid}",
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True,
                           timeout=240, check=True)
        except FileNotFoundError:
            sys.exit("yt-dlp not installed (pip install yt-dlp)")
        except subprocess.CalledProcessError as e:
            sys.exit(f"yt-dlp failed for {vid}: {e.stderr[:300]}")
        except subprocess.TimeoutExpired:
            sys.exit(f"yt-dlp timed out for {vid}")
        vtt = next(Path(td).glob(f"{vid}*.vtt"), None)
        if vtt is None:
            sys.exit(f"no English auto-sub track available for {vid}")
        return vid, parse_vtt(vtt.read_text(encoding="utf-8",
                                            errors="replace"))


def parse_vtt(raw: str) -> str:
    """VTT -> plain sentences. Handles timestamps, cue settings, the
    rolling-duplicate lines auto-subs produce, inline tags and HTML
    entities."""
    lines: list[str] = []
    prev = ""
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s == "WEBVTT" or s.startswith(("Kind:", "Language:",
                                                   "NOTE", "STYLE")):
            continue
        if "-->" in s:                    # cue timing line
            continue
        if re.fullmatch(r"[\d:.]+", s):   # stray timestamp
            continue
        clean = (s.replace("<c>", "").replace("</c>", "")
                 .replace("&nbsp;", " ").replace("&amp;", "&")
                 .replace("&#39;", "'").replace("&quot;", '"'))
        clean = re.sub(r"</?[^>]+>", "", clean).strip()
        if not clean or clean == prev:    # auto-sub rollup duplicate
            prev = clean
            continue
        prev = clean
        lines.append(clean)
    text = " ".join(lines)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def top_phrases(text: str, n: int = 8) -> list[tuple[str, int]]:
    """Top repeated 2-4-word content phrases (the vocabulary layer)."""
    words = [w for w in re.findall(r"[a-z']{2,}", text.lower())
             if w not in _STOP]
    counts: Counter[str] = Counter()
    for size in (2, 3, 4):
        for i in range(len(words) - size + 1):
            counts[" ".join(words[i:i + size])] += 1
    # a 3-gram that only ever appears inside ONE repeated 4-gram is the
    # same fact; keep the longest repeated forms
    out = [(p, c) for p, c in counts.most_common() if c >= 3]
    pruned: list[tuple[str, int]] = []
    for p, c in out:
        if any(p in q and c == qc for q, qc in pruned):
            continue
        pruned.append((p, c))
        if len(pruned) >= n:
            break
    return pruned


def hook_block(text: str, seconds: int = 15) -> list[str]:
    """The first ~15 seconds of speech (~38 words at 150 wpm)."""
    target = max(3, int(seconds / 60 * 150))
    sents = sentences(text)
    out: list[str] = []
    n = 0
    for s in sents:
        out.append(s)
        n += len(s.split())
        if n >= target:
            break
    return out


def report(video: str) -> None:
    vid, text = fetch_transcript(video)
    sents = sentences(text)
    words = len(text.split())
    wps = words / max(1, len(sents))
    print(f"\n═══ {vid} ═══")
    print(f"words {words:,} | ~{words / 150:.1f} min spoken | "
          f"{len(sents)} sentences | {wps:.1f} words/sentence")
    print("\n— the first 15 seconds (spoken hook) —")
    for s in hook_block(text):
        print(f"  {s}")
    print("\n— the repeated-phrase layer —")
    phrases = top_phrases(text)
    if phrases:
        for p, c in phrases:
            print(f"  {c:>3}x  {p}")
    else:
        print("  (no phrase repeated 3+ times)")
    out = _probe_dir() / f"{vid}.txt"
    out.write_text(text, encoding="utf-8")
    print(f"\nfull transcript: {out}")


def main(argv: list[str]) -> None:
    args = [a for a in argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(1)
    for v in args:
        report(v)


if __name__ == "__main__":
    main(sys.argv)
