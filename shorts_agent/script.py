"""Step 1 – write the script (hook -> body -> payoff) with Claude."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .config import Config

SYSTEM = """You are a senior YouTube Shorts scriptwriter.
Rules:
- Total narration 110-150 words (Korean: 220-300 characters) -> about 45 seconds spoken.
- Scene 1 is a HOOK that creates curiosity in the first 2 seconds. No greetings, no intro.
- 5-7 scenes, one idea each, short punchy sentences. Last scene: payoff + a one-line call to action.
- Only state facts you are confident are true. No invented statistics, names or quotes.
  If unsure, speak qualitatively instead.
- `visual_query` is 2-4 ENGLISH words for stock-footage search (concrete, filmable, vertical-friendly).
- `caption_emphasis` lists words from the narration to highlight.
Return ONLY JSON:
{"title": str(<=60 chars, include #Shorts), "description": str, "tags": [str],
 "scenes": [{"narration": str, "visual_query": str, "caption_emphasis": [str]}]}"""


@dataclass
class Scene:
    narration: str
    visual_query: str
    caption_emphasis: list[str] = field(default_factory=list)
    # filled in later
    audio_path: str | None = None
    duration: float = 0.0
    words: list[tuple[str, float, float]] = field(default_factory=list)  # (word, start, end) within scene
    clip_path: str | None = None


@dataclass
class Script:
    title: str
    description: str
    tags: list[str]
    scenes: list[Scene]

    @property
    def text(self) -> str:
        return " ".join(s.narration for s in self.scenes)


def parse_script(raw: str) -> Script:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    data = json.loads(m.group(0))
    scenes = [
        Scene(s["narration"].strip(), s["visual_query"].strip(), list(s.get("caption_emphasis", [])))
        for s in data["scenes"]
        if s.get("narration", "").strip()
    ]
    if not 3 <= len(scenes) <= 10:
        raise ValueError(f"unexpected scene count: {len(scenes)}")
    title = data["title"].strip()
    if "#shorts" not in title.lower():
        title = f"{title[:50]} #Shorts"
    return Script(title, data.get("description", ""), list(data.get("tags", [])), scenes)


def offline_script(topic: str) -> Script:
    """Deterministic placeholder so the pipeline can be exercised without an API key."""
    return Script(
        title=f"{topic[:50]} #Shorts",
        description=f"{topic}\n\n#Shorts",
        tags=["shorts", topic],
        scenes=[
            Scene(f"{topic}, 3초만에 핵심만 알려드립니다.", "city night", [topic]),
            Scene("첫째, 가장 중요한 포인트부터 보세요.", "typing laptop", []),
            Scene("둘째, 작은 습관이 큰 차이를 만듭니다.", "morning routine", []),
            Scene("마지막으로, 오늘 바로 시작해 보세요. 구독하면 다음 편도 받아볼 수 있어요.", "sunrise mountain", []),
        ],
    )


def write_script(topic: str, cfg: Config) -> Script:
    if cfg.offline or not cfg.anthropic_key:
        return offline_script(topic)
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.anthropic_key)
    last_err: Exception | None = None
    for _ in range(3):  # retry on malformed JSON
        msg = client.messages.create(
            model=cfg.claude_model,
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content": f"Language: {cfg.language}\nTopic: {topic}"}],
        )
        try:
            return parse_script(msg.content[0].text)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            last_err = e
    raise RuntimeError(f"script generation failed: {last_err}")
