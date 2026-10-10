import argparse

from .config import Config
from .pipeline import make_short


def main() -> None:
    p = argparse.ArgumentParser(prog="shorts_agent", description="Auto-generate a YouTube Short")
    p.add_argument("topic")
    p.add_argument("--offline", action="store_true", help="no network/API: placeholder script, silent audio, gradient visuals")
    p.add_argument("--upload", action="store_true")
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    a = p.parse_args()
    cfg = Config(offline=a.offline)
    out, script = make_short(a.topic, cfg)
    print(f"\nDone: {out}\nTitle: {script.title}")
    if a.upload:
        from .upload import upload
        print("Uploaded:", upload(out, script, a.privacy))


main()
