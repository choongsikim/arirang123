"""Step 4 – word-highlight (karaoke) captions as ASS, sized for the Shorts safe zone."""
from __future__ import annotations

import re

from .config import Config
from .script import Scene

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{font},84,&H0000E5FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,90,90,{mv},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def _ts(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w).lower()


def build_ass(scenes: list[Scene], cfg: Config, max_words: int = 3) -> str:
    # Bottom margin keeps text above YouTube's UI (title/buttons cover ~ the lowest 20-25 %).
    out = [HEADER.format(w=cfg.width, h=cfg.height, font=cfg.font, mv=int(cfg.height * 0.27))]
    offset = 0.0
    for sc in scenes:
        emph = {_norm(e) for e in sc.caption_emphasis}
        for i in range(0, len(sc.words), max_words):
            chunk = sc.words[i : i + max_words]
            start, end = offset + chunk[0][1], offset + chunk[-1][2]
            nxt = sc.words[i + max_words][1] + offset if i + max_words < len(sc.words) else offset + sc.duration
            end = min(max(end + 0.05, start + 0.3), nxt)
            parts = []
            for j, (w, s, e) in enumerate(chunk):
                nxt_s = chunk[j + 1][1] if j + 1 < len(chunk) else chunk[-1][2]
                cs = max(round((nxt_s - s) * 100), 1)
                big = r"{\fs100}" if _norm(w) in emph else ""
                small = r"{\fs84}" if big else ""
                parts.append(rf"{{\kf{cs}}}{big}{w.replace(chr(10), ' ')}{small}")
            out.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,{' '.join(parts)}")
        offset += sc.duration
    return "\n".join(out) + "\n"
