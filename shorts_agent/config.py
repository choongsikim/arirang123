from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """All knobs in one place; every value can be overridden by env var."""

    output_dir: Path = field(default_factory=lambda: Path(os.getenv("SHORTS_OUT", "output")))
    language: str = os.getenv("SHORTS_LANG", "ko")
    voice: str = os.getenv("SHORTS_VOICE", "ko-KR-SunHiNeural")
    voice_rate: str = os.getenv("SHORTS_RATE", "+8%")
    claude_model: str = os.getenv("SHORTS_CLAUDE_MODEL", "claude-sonnet-5-5")
    pexels_key: str | None = os.getenv("PEXELS_API_KEY")
    anthropic_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    bgm_path: Path | None = Path(p) if (p := os.getenv("SHORTS_BGM")) else None
    font: str = os.getenv("SHORTS_FONT", "Noto Sans CJK KR")
    fonts_dir: Path | None = Path(p) if (p := os.getenv("SHORTS_FONTS_DIR")) else None
    # Output spec: YouTube Shorts = vertical 9:16, <= 180 s.
    width: int = 1080
    height: int = 1920
    fps: int = 30
    crf: int = 18  # visually near-lossless; YouTube re-encodes anyway
    max_seconds: float = 58.0
    offline: bool = False  # no network: synthetic visuals + silent timing audio

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
