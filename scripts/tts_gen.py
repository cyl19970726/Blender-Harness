#!/usr/bin/env python3
"""TTS narration generator for AR magnet narrations (data-driven).

Usage:
  python tts_gen.py <text_file_or_inline> <out.mp3> [voice] [rate] [pitch]

Produces:
  <out.mp3>        — the narration audio
  <out>.cues.json  — phrase-level subtitle cues [{start, end, text}] (seconds),
                     derived from edge-tts WordBoundary timings, split on CJK
                     punctuation so each subtitle line is short + mobile-readable.

Default voice zh-CN-YunxiNeural (lively young male) suits 揭小贤. No API key needed.
"""
import sys, os, json, asyncio, edge_tts

SPLIT = set("。!?！？\n")          # hard sentence breaks → always close a cue
SOFT = set(",，、;；:：")          # soft breaks → close a cue too (short lines)

def load_text(arg):
    if os.path.isfile(arg):
        return open(arg, encoding="utf-8").read().strip()
    return arg

async def main():
    text = load_text(sys.argv[1])
    out = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "zh-CN-YunxiNeural"
    rate = sys.argv[4] if len(sys.argv) > 4 else "-6%"   # slightly slower = clearer
    pitch = sys.argv[5] if len(sys.argv) > 5 else "+0Hz"

    # edge-tts emits SentenceBoundary (and/or WordBoundary). We build cues from
    # whichever fires, splitting long sentences on soft punctuation for mobile.
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    raw = []  # (start, end, text)
    with open(out, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] in ("SentenceBoundary", "WordBoundary"):
                raw.append((ch["offset"] / 1e7,
                            (ch["offset"] + ch["duration"]) / 1e7,
                            ch["text"]))

    def split_long(s, e, t):
        # split a sentence into shorter readable lines on soft punctuation,
        # distributing the time window proportionally by character count.
        parts, buf = [], ""
        for c in t:
            buf += c
            if c in SOFT or c in SPLIT:
                if buf.strip(" ,，、;；:：。!?！？"):
                    parts.append(buf)
                buf = ""
        if buf.strip():
            parts.append(buf)
        if not parts:
            return []
        total = sum(len(p) for p in parts) or 1
        out_cues, acc = [], s
        for p in parts:
            dur = (e - s) * (len(p) / total)
            out_cues.append({"start": round(acc, 2), "end": round(acc + dur, 2),
                             "text": p.strip(" ,，、;；:：")})
            acc += dur
        return out_cues

    cues = []
    for s, e, t in raw:
        for c in split_long(s, e, t):
            if c["text"]:
                cues.append(c)

    cues_path = out.rsplit(".", 1)[0] + ".cues.json"
    json.dump([c for c in cues if c["text"]], open(cues_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    dur = cues[-1]["end"] if cues else 0
    print(f"saved {out} ({os.path.getsize(out)/1024:.0f}KB, ~{dur:.1f}s, voice={voice})")
    print(f"saved {cues_path} ({len(cues)} subtitle cues)")

if __name__ == "__main__":
    asyncio.run(main())
