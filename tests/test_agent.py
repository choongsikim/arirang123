import json
import subprocess

from shorts_agent.captions import build_ass
from shorts_agent.config import Config
from shorts_agent.pipeline import make_short
from shorts_agent.script import Scene, parse_script
from shorts_agent.tts import estimate_words


def test_parse_script_adds_shorts_tag():
    raw = "noise " + json.dumps({"title": "Hi", "description": "d", "tags": ["a"], "scenes": [
        {"narration": f"line {i}", "visual_query": "sea"} for i in range(4)]})
    s = parse_script(raw)
    assert s.title.endswith("#Shorts") and len(s.scenes) == 4


def test_estimate_words_covers_duration():
    w = estimate_words("a bb ccc", 3.0)
    assert abs(w[-1][2] - 3.0) < 1e-6


def test_ass_has_events():
    sc = Scene("one two three four", "x", ["two"])
    sc.duration, sc.words = 2.0, estimate_words(sc.narration, 2.0)
    ass = build_ass([sc], Config())
    assert ass.count("Dialogue:") == 2 and r"\fs100" in ass


def test_end_to_end_offline(tmp_path):
    cfg = Config(output_dir=tmp_path, offline=True)
    out, _ = make_short("테스트 주제", cfg)
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(out)],
        capture_output=True, text=True, check=True).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (v["width"], v["height"]) == (1080, 1920)
    assert any(s["codec_type"] == "audio" for s in info["streams"])
