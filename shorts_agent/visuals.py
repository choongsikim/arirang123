"""Step 3 – one background clip per scene (Pexels portrait stock, or generated fallback)."""
from __future__ import annotations

import colorsys
import hashlib
import subprocess
from pathlib import Path

import requests

from .config import Config
from .script import Scene

PEXELS = "https://api.pexels.com/videos/search"


def _pick_file(video: dict) -> dict | None:
    files = [f for f in video["video_files"] if f.get("file_type") == "video/mp4" and f["height"] > f["width"]]
    if not files:
        return None
    # Prefer >= 1080 wide (sharp after 9:16 crop), otherwise the largest available.
    good = [f for f in files if f["width"] >= 1080]
    return min(good, key=lambda f: f["width"]) if good else max(files, key=lambda f: f["width"])


def fetch_stock(query: str, cfg: Config, cache: Path, used: set[int], min_len: float) -> Path | None:
    r = requests.get(
        PEXELS,
        headers={"Authorization": cfg.pexels_key},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15},
        timeout=20,
    )
    r.raise_for_status()
    for v in r.json().get("videos", []):
        if v["id"] in used or v.get("duration", 0) < min(min_len, 4):
            continue
        f = _pick_file(v)
        if not f:
            continue
        dst = cache / f"pexels_{v['id']}.mp4"
        if not dst.exists():
            with requests.get(f["link"], stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(dst, "wb") as fh:
                    for chunk in resp.iter_content(1 << 16):
                        fh.write(chunk)
        used.add(v["id"])
        return dst
    return None


def generated_background(query: str, out: Path, seconds: float, cfg: Config) -> None:
    """Gradient + slow Ken-Burns zoom. Used when no stock footage is available."""
    from PIL import Image

    h = int(hashlib.md5(query.encode()).hexdigest()[:4], 16) / 0xFFFF
    top = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.55, 0.55))
    bot = tuple(int(c * 255) for c in colorsys.hsv_to_rgb((h + 0.12) % 1, 0.70, 0.18))
    w, ht = cfg.width * 2, cfg.height * 2  # 2x source avoids zoompan jitter
    img = Image.new("RGB", (1, ht))
    for y in range(ht):
        t = y / (ht - 1)
        img.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    png = out.with_suffix(".png")
    img.resize((w, ht)).save(png)
    frames = int(seconds * cfg.fps) + 1
    vf = (f"zoompan=z='1+0.0004*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}"
          f":s={cfg.width}x{cfg.height}:fps={cfg.fps}")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-vf", vf, "-t", f"{seconds:.2f}",
                    "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(out)],
                   check=True, capture_output=True)


def fit_clip(src: Path, out: Path, seconds: float, cfg: Config) -> None:
    """Cover-crop to 1080x1920, loop if too short, cut to exactly `seconds`, slight zoom for motion polish."""
    vf = (f"scale={cfg.width}:{cfg.height}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={cfg.width}:{cfg.height},fps={cfg.fps},setsar=1,format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.2f}", "-an",
                    "-vf", vf, "-c:v", "libx264", "-crf", "14", "-preset", "fast", str(out)],
                   check=True, capture_output=True)


def build_visuals(scenes: list[Scene], workdir: Path, cfg: Config) -> None:
    cache = cfg.output_dir / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    used: set[int] = set()
    for i, sc in enumerate(scenes):
        out = workdir / f"scene_{i:02d}.mp4"
        src = None
        if cfg.pexels_key and not cfg.offline:
            try:
                src = fetch_stock(sc.visual_query, cfg, cache, used, sc.duration)
            except requests.RequestException as e:
                print(f"  [warn] stock fetch failed for '{sc.visual_query}': {e}")
        if src:
            fit_clip(src, out, sc.duration, cfg)
        else:
            generated_background(sc.visual_query, out, sc.duration, cfg)
        sc.clip_path = str(out)
