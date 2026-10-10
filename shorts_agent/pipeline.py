from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import captions, render, script as script_mod, tts, visuals
from .config import Config


def make_short(topic: str, cfg: Config) -> tuple[Path, script_mod.Script]:
    slug = re.sub(r"[^\w]+", "-", topic).strip("-")[:40] or "short"
    work = cfg.output_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    work.mkdir(parents=True, exist_ok=True)

    print("1/5 script");   sc = script_mod.write_script(topic, cfg)
    print("2/5 voice");    tts.synthesize(sc.scenes, work, cfg)
    total = sum(s.duration for s in sc.scenes)
    if total > cfg.max_seconds:
        raise RuntimeError(f"video would be {total:.0f}s (> {cfg.max_seconds:.0f}s); shorten the script")
    print("3/5 visuals");  visuals.build_visuals(sc.scenes, work, cfg)
    print("4/5 captions"); ass = work / "captions.ass"; ass.write_text(captions.build_ass(sc.scenes, cfg), encoding="utf-8")
    print("5/5 render");   out = render.render(sc.scenes, ass, work / "short.mp4", work, cfg)

    (work / "meta.json").write_text(json.dumps(
        {"title": sc.title, "description": sc.description, "tags": sc.tags, "seconds": round(total, 1),
         "scenes": [{"narration": s.narration, "visual_query": s.visual_query} for s in sc.scenes]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return out, sc
