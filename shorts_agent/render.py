"""Step 5 – final master: concat scenes, mix voice + ducked BGM, burn captions, loudness-normalise."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Config
from .script import Scene


def _ff(args: list[str]) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])


def render(scenes: list[Scene], ass: Path, out: Path, workdir: Path, cfg: Config) -> Path:
    # 1) concat the (already uniform) video scenes
    vlist = workdir / "video.txt"
    vlist.write_text("".join(f"file '{Path(s.clip_path).resolve()}'\n" for s in scenes))
    video = workdir / "video_all.mp4"
    _ff(["-f", "concat", "-safe", "0", "-i", str(vlist), "-c", "copy", str(video)])

    # 2) narration track: pad each voice file to its scene length so audio stays in sync
    padded = []
    for i, s in enumerate(scenes):
        p = workdir / f"voice_pad_{i:02d}.wav"
        _ff(["-i", s.audio_path, "-af", f"apad=whole_dur={s.duration:.3f}", "-ar", "44100", "-ac", "2", str(p)])
        padded.append(p)
    alist = workdir / "audio.txt"
    alist.write_text("".join(f"file '{p.resolve()}'\n" for p in padded))
    voice = workdir / "voice_all.wav"
    _ff(["-f", "concat", "-safe", "0", "-i", str(alist), "-c", "copy", str(voice)])

    # 3) final: captions + (optional) BGM ducked under voice + EBU R128 -14 LUFS (YouTube reference)
    sub = f"subtitles={ass.as_posix()}" + (f":fontsdir={cfg.fonts_dir.as_posix()}" if cfg.fonts_dir else "")
    inputs = ["-i", str(video), "-i", str(voice)]
    if cfg.bgm_path and cfg.bgm_path.exists():
        inputs += ["-stream_loop", "-1", "-i", str(cfg.bgm_path)]
        af = ("[1:a]asplit=2[v][sc];[2:a]volume=0.18[b];[b][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[bd];"
              "[v][bd]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    else:
        af = "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    out.parent.mkdir(parents=True, exist_ok=True)
    _ff([*inputs, "-filter_complex", f"[0:v]{sub}[v];{af}", "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", str(cfg.crf), "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-r", str(cfg.fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
         "-t", f"{sum(s.duration for s in scenes):.3f}", str(out)])
    return out
