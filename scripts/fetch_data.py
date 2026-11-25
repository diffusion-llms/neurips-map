#!/usr/bin/env python3
"""Download the raw NeurIPS 2026 data this site is built from.

Writes into data/raw/ (git-ignored):
  orals-posters.json   official virtual-site feed: sessions, times, rooms, poster numbers, decisions
  export.json          neurips.cc/Downloads export: titles, authors + affiliations, abstracts
                       for posters, tutorials, workshops and invited talks
  events/<kind>_<id>.html   pages for the workshops/tutorials listed in data/events_config.json

Usage:  python3 scripts/fetch_data.py
"""
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BASE = "https://neurips.cc"
UA = "Mozilla/5.0 (compatible; neurips-dd-map/1.0)"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("User-Agent", UA)]


def get(url, data=None, headers=None, timeout=600):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with opener.open(req, timeout=timeout) as r:
        return r.read()


def fetch_feed():
    out = RAW / "orals-posters.json"
    print("feed  ->", out)
    out.write_bytes(get(f"{BASE}/static/virtual/data/neurips-2026-orals-posters.json"))


def fetch_export():
    """POST the Downloads form (needs the CSRF cookie + token from the form page)."""
    out = RAW / "export.json"
    print("export ->", out, "(slow: the server builds the file on request)")
    page = get(f"{BASE}/Downloads/2026").decode("utf-8")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
    form = {
        "csrfmiddlewaretoken": token, "format": "5",  # 5 = json
        "posters": "on", "tutorials": "on", "invited_talks": "on",
        "workshops": "on", "demonstrations": "on", "resource": "0",
        "submitaction": "Download Data",
    }
    body = urllib.parse.urlencode(form).encode()
    out.write_bytes(get(f"{BASE}/Downloads/2026", data=body,
                        headers={"Referer": f"{BASE}/Downloads/2026",
                                 "Content-Type": "application/x-www-form-urlencoded"}))


def fetch_events():
    cfg = json.loads((ROOT / "data" / "events_config.json").read_text())
    (RAW / "events").mkdir(parents=True, exist_ok=True)
    for ev in cfg:
        out = RAW / "events" / f"{ev['kind']}_{ev['id']}.html"
        print("event ->", out)
        out.write_bytes(get(f"{BASE}/virtual/2026/{ev['kind']}/{ev['id']}"))


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    steps = sys.argv[1:] or ["feed", "export", "events"]
    if "feed" in steps:
        fetch_feed()
    if "events" in steps:
        fetch_events()
    if "export" in steps:
        fetch_export()
    print("done")
