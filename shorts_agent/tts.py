"""Step 2 – narration audio + word timings (drives captions and scene length)."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

from .config import Config
from .script import Scene


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(out.strip())


async def _edge(scene: Scene, out: Path, cfg: Config) -> None:
    import edge_tts

    comm = edge_tts.Communicate(scene.narration, cfg.voice, rate=cfg.voice_rate, boundary="WordBoundary")
    words: list[tuple[str, float, float]] = []
    with open(out, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7  # 100-ns ticks -> s
                words.append((ch["text"], s, s + ch["duration"] / 1e7))
    scene.words = words


def estimate_words(text: str, total: float) -> list[tuple[str, float, float]]:
    """Spread words over `total` seconds proportional to length (fallback timing)."""
    toks = text.split()
    weights = [max(len(re.sub(r"\W", "", t)), 1) for t in toks]
    t, acc = total / sum(weights), 0.0
    out = []
    for tok, w in zip(toks, weights):
        out.append((tok, acc, acc + w * t))
        acc += w * t
    return out


def synthesize(scenes: list[Scene], workdir: Path, cfg: Config) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    for i, sc in enumerate(scenes):
        out = workdir / f"voice_{i:02d}.mp3"
        if cfg.offline:
            dur = max(1.5, len(sc.narration) / 7.0)
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", f"{dur:.2f}",
                  "-c:a", "libmp3lame", str(out)])
        else:
            asyncio.run(_edge(sc, out, cfg))
        sc.audio_path = str(out)
        sc.duration = probe_duration(out) + 0.25  # small breath between scenes
        if not sc.words:
            sc.words = estimate_words(sc.narration, sc.duration - 0.25)
