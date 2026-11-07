#!/usr/bin/env python3
"""Ajoute un épisode et régénère feed.xml et index.html.

Usage :
  python3 scripts/publish.py --script episodes/2026-11-07.txt --title "..." \
      --description "..." [--date 2026-11-07] [--voice fr-FR-RemyMultilingualNeural]

Le script texte est converti en MP3 avec edge-tts, puis le flux RSS et la page
d'accueil sont reconstruits à partir de tous les fichiers episodes/*.json.
"""
import argparse, datetime as dt, email.utils, html, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EP = ROOT / "episodes"
BASE_URL = "https://ziryabus.github.io/veille-podcast"
TITLE = "Veille Techno — Ziryab"
DESC = ("Veille quotidienne IA, cloud, cyber, data, méthodes et business IT, "
        "pensée pour un recruteur de DSI et CTO. Un épisode de 5 minutes du lundi "
        "au vendredi, un récap de 15 minutes le samedi.")


def tts(text_file: Path, mp3: Path, voice: str):
    env = dict(os.environ)
    env.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    cmd = ["edge-tts", "--voice", voice, "--rate=+5%", "-f", str(text_file),
           "--write-media", str(mp3)]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        cmd[1:1] = ["--proxy", proxy]
    subprocess.run(cmd, check=True, env=env)


def duration(mp3: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(mp3)], capture_output=True, text=True)
    try:
        return int(float(out.stdout.strip()))
    except ValueError:
        return 0


def build():
    eps = sorted((json.loads(p.read_text()) for p in EP.glob("*.json")),
                 key=lambda e: e["date"], reverse=True)
    items = []
    for e in eps:
        d = dt.datetime.fromisoformat(e["date"]).replace(hour=7, tzinfo=dt.timezone.utc)
        url = f"{BASE_URL}/episodes/{e['file']}"
        items.append(f"""    <item>
      <title>{html.escape(e['title'])}</title>
      <description>{html.escape(e['description'])}</description>
      <pubDate>{email.utils.format_datetime(d)}</pubDate>
      <guid isPermaLink="false">veille-{e['file']}</guid>
      <enclosure url="{url}" length="{e['bytes']}" type="audio/mpeg"/>
      <itunes:duration>{e['seconds']}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(TITLE)}</title>
    <link>{BASE_URL}/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>fr-fr</language>
    <description>{html.escape(DESC)}</description>
    <itunes:author>Veille Techno</itunes:author>
    <itunes:summary>{html.escape(DESC)}</itunes:summary>
    <itunes:image href="{BASE_URL}/cover.jpg"/>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")

    rows = "\n".join(
        f"<li><b>{html.escape(e['title'])}</b><br><small>{html.escape(e['description'])}</small>"
        f"<br><audio controls preload=\"none\" src=\"episodes/{e['file']}\"></audio></li>" for e in eps)
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Veille Techno</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;background:#f8fafc;color:#1e1b4b}}
img{{width:120px;border-radius:12px}}li{{margin:0 0 20px;list-style:none}}ul{{padding:0}}audio{{width:100%;margin-top:6px}}
code{{background:#e0e7ff;padding:2px 6px;border-radius:4px;word-break:break-all}}</style></head><body>
<img src="cover.jpg" alt=""><h1>Veille Techno</h1>
<p>Pour l'écouter dans l'appli Podcasts de l'iPhone : Bibliothèque → ⋯ → « Suivre un podcast par URL » → <code>{BASE_URL}/feed.xml</code></p>
<ul>
{rows}
</ul></body></html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script")
    ap.add_argument("--title")
    ap.add_argument("--description", default="")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--voice", default="fr-FR-RemyMultilingualNeural")
    ap.add_argument("--rebuild-only", action="store_true")
    a = ap.parse_args()
    EP.mkdir(exist_ok=True)
    if not a.rebuild_only:
        if not (a.script and a.title):
            sys.exit("--script et --title sont obligatoires")
        mp3 = EP / f"{a.date}.mp3"
        tts(Path(a.script), mp3, a.voice)
        meta = {"date": a.date, "title": a.title, "description": a.description,
                "file": mp3.name, "bytes": mp3.stat().st_size, "seconds": duration(mp3)}
        (EP / f"{a.date}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        print(f"{BASE_URL}/episodes/{mp3.name}  ({meta['seconds']} s)")
    build()


if __name__ == "__main__":
    main()
