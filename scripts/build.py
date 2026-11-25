#!/usr/bin/env python3
"""Build the discrete-diffusion map of NeurIPS 2026.

Inputs
  data/raw/orals-posters.json   (scripts/fetch_data.py)
  data/raw/export.json          (scripts/fetch_data.py)
  data/raw/events/*.html        (scripts/fetch_data.py)
  data/classification.json      per-paper relevance, category, tags and TL;DR
  data/overrides.json           hand corrections applied on top of the classification
  data/events_config.json       which workshops / tutorials to feature, and where they run
  site/template.html            the page (an HTML fragment with a /*__DATA__*/ slot)

Outputs
  data/papers.json              the merged, included papers (handy for other tools)
  docs/index.html               standalone page for GitHub Pages
  build/artifact.html           the same page as a fragment (for hosts that add their own <head>)

Usage:  python3 scripts/build.py
"""
import html
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
# Denoising-grid mark from the tutorial site (d-llms.com/neurips26), used as the favicon.
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='6' fill='%230b1020'/%3E%3Cg fill='%235b53ff'%3E"
           "%3Crect x='5' y='5' width='6' height='6' rx='1.4' opacity='.35'/%3E%3Crect x='13' y='5' width='6' height='6' rx='1.4' opacity='.9'/%3E"
           "%3Crect x='21' y='5' width='6' height='6' rx='1.4' opacity='.5'/%3E%3C/g%3E%3Cg fill='%2312b3a6'%3E"
           "%3Crect x='5' y='13' width='6' height='6' rx='1.4' opacity='.85'/%3E%3Crect x='13' y='13' width='6' height='6' rx='1.4' opacity='.45'/%3E"
           "%3Crect x='21' y='13' width='6' height='6' rx='1.4' opacity='.95'/%3E%3C/g%3E%3Cg fill='%235b53ff'%3E"
           "%3Crect x='5' y='21' width='6' height='6' rx='1.4' opacity='.55'/%3E%3Crect x='13' y='21' width='6' height='6' rx='1.4' opacity='.95'/%3E"
           "%3Crect x='21' y='21' width='6' height='6' rx='1.4' opacity='.3'/%3E%3C/g%3E%3C/svg%3E")

VENUE_TZ = {"Sydney": "Australia/Sydney", "Atlanta": "America/New_York", "Paris": "Europe/Paris"}
AEDT = timezone(timedelta(hours=11))  # every event page prints Sydney time in December


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def to_utc(iso):
    if not iso:
        return None
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def venue_of(session):
    s = session or ""
    for v in VENUE_TZ:
        if s.startswith(v):
            return v
    if s.startswith("Orals"):  # unprefixed oral sessions are the main (Sydney) programme
        return "Sydney"
    return None


def track_of(src):
    src = src or ""
    if "Evaluations_and_Datasets" in src:
        return "Evaluations & Datasets"
    if "Position_Paper" in src:
        return "Position"
    if "journal-track" in src:
        return "Journal (" + re.search(r"Posters_(\w+)\.xlsx", src).group(1) + ")"
    if "bridging-the-future" in src:
        return "Bridging the Future"
    return "Main"


def decision_of(d, has_oral):
    d = (d or "").lower()
    if has_oral or "oral" in d:
        return "oral"
    if "spotlight" in d:
        return "spotlight"
    return "poster"


# ---------------------------------------------------------------- papers
def build_papers():
    feed = load(RAW / "orals-posters.json")["results"]
    export = load(RAW / "export.json")
    cls = load(ROOT / "data" / "classification.json")
    over_path = ROOT / "data" / "overrides.json"
    overrides = load(over_path) if over_path.exists() else {}
    for pid, o in overrides.items():
        if pid.startswith("_"):
            continue
        cls[pid] = {**cls.get(pid, {"rel": "exclude", "cat": None, "tags": [], "tldr": ""}), **o}

    by_id = {str(x["id"]): x for x in feed}
    abstracts = {}
    for x in export:
        m = re.search(r"/(\d+)$", x["virtualsite_url"])
        if m:
            abstracts[m.group(1)] = clean(x.get("abstract"))
    orals = {}
    for x in feed:
        if x["eventtype"] == "Oral":
            for rid in x["related_events_ids"]:
                orals[str(rid)] = x

    papers = []
    for pid, c in cls.items():
        if c.get("rel") not in ("core", "related"):
            continue
        p = by_id.get(pid)
        if p is None:
            print("  ! not in feed, skipped:", pid)
            continue
        o = orals.get(pid)
        code = p.get("url") or ""
        if code and ("openreview.net" in code or "neurips.cc" in code):
            code = ""
        rec = {
            "id": pid,
            "t": clean(p["name"]),
            "au": [[clean(a["fullname"]), clean(a.get("institution") or "")] for a in p["authors"]],
            "abs": abstracts.get(pid, ""),
            "rel": c["rel"],
            "cat": c.get("cat") or "training",
            "tags": c.get("tags") or [],
            "tldr": c.get("tldr") or "",
            "dec": decision_of(p.get("decision"), o is not None),
            "v": venue_of(p.get("session")),
            "ps": clean(p.get("session")),
            "s": to_utc(p.get("starttime")),
            "e": to_utc(p.get("endtime")),
            "room": clean(p.get("room_name")),
            "pos": clean(p.get("poster_position")),
            "track": track_of(p.get("sourceurl")),
            "topic": clean(p.get("topic")),
            "or": p.get("paper_url") or "",
            "code": code,
        }
        if o:
            rec["oral"] = {"ses": clean(o["session"]), "s": to_utc(o["starttime"]),
                           "e": to_utc(o["endtime"]), "room": clean(o["room_name"]),
                           "v": venue_of(o["session"]) or rec["v"]}
        papers.append(rec)
    papers.sort(key=lambda r: (r["s"] or "9", r["t"].lower()))
    return papers


# ---------------------------------------------------------------- poster/oral sessions per venue
def build_sessions():
    feed = load(RAW / "orals-posters.json")["results"]
    ses = {}
    for x in feed:
        name = clean(x.get("session"))
        if not name or not x.get("starttime"):
            continue
        kind = "oral" if x["eventtype"] == "Oral" else "poster"
        k = (name, kind)
        s, e = to_utc(x["starttime"]), to_utc(x["endtime"])
        if k not in ses:
            ses[k] = {"name": name, "kind": kind, "v": venue_of(name), "s": s, "e": e,
                      "room": clean(x.get("room_name")) if kind == "oral" else "", "n": 0}
        cur = ses[k]
        cur["s"], cur["e"] = min(cur["s"], s), max(cur["e"], e)
        cur["n"] += 1
    return sorted(ses.values(), key=lambda r: (r["s"], r["name"]))


# ---------------------------------------------------------------- workshops & tutorials
def parse_event(path, cfg, export_by_id):
    h = path.read_text(encoding="utf-8")
    pills = [clean(re.sub(r"<[^>]+>", " ", m)) for m in re.findall(r'<span class="meta-pill">(.*?)</span>', h, re.S)]
    when = next(p for p in pills if "AEDT" in p)
    room = next((p for p in pills if p != when), "")
    m = re.match(r"\w+, (\w+ \d+, \d{4}) • (\d+:\d+ [AP]M) – (\d+:\d+ [AP]M) AEDT", when)
    day, t0, t1 = m.groups()
    start = datetime.strptime(f"{day} {t0}", "%b %d, %Y %I:%M %p").replace(tzinfo=AEDT)
    end = datetime.strptime(f"{day} {t1}", "%b %d, %Y %I:%M %p").replace(tzinfo=AEDT)
    if end <= start:
        end += timedelta(days=1)
    title = clean(re.search(r'<h1 class="event-title">(.*?)</h1>', h, re.S).group(1))
    org_m = re.search(r'<div class="event-organizers">(.*?)</div>', h, re.S)
    organizers = []
    for n in clean(org_m.group(1)).split("⋅") if org_m else []:
        n = n.strip()
        if n and n not in organizers:
            organizers.append(n)
    project = re.search(r'class="action-btn project" href="([^"]+)"', h)
    openrev = re.search(r'href="(https://openreview\.net/forum\?id=[^"]+)"', h)
    ex = export_by_id.get(str(cfg["id"]), {})
    if not organizers and ex.get("speakers/authors"):
        organizers = [clean(a) for a in re.split(r",\s*(?![^()]*\))", ex["speakers/authors"])]
    return {
        "id": str(cfg["id"]), "kind": cfg["kind"], "rel": cfg["rel"], "v": cfg["venue"],
        "t": title, "s": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "e": end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "room": room, "org": organizers, "abs": clean(ex.get("abstract")),
        "web": cfg.get("web") or (project.group(1) if project else ""), "or": openrev.group(1) if openrev else "",
        "url": f"https://neurips.cc/virtual/2026/{cfg['kind']}/{cfg['id']}",
        "note": cfg.get("note", ""),
    }


def build_events():
    export = load(RAW / "export.json")
    by_id = {}
    for x in export:
        m = re.search(r"/(\d+)$", x["virtualsite_url"])
        if m:
            by_id[m.group(1)] = x
    out = []
    for cfg in load(ROOT / "data" / "events_config.json"):
        out.append(parse_event(RAW / "events" / f"{cfg['kind']}_{cfg['id']}.html", cfg, by_id))
    return sorted(out, key=lambda r: r["s"])


def main():
    papers = build_papers()
    events = build_events()
    sessions = build_sessions()
    meta = load(ROOT / "data" / "site_meta.json")
    meta["built"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta["totalAccepted"] = sum(1 for x in load(RAW / "orals-posters.json")["results"] if x["eventtype"] == "Poster")

    (ROOT / "data" / "papers.json").write_text(json.dumps(papers, ensure_ascii=False, indent=1), encoding="utf-8")
    blob = json.dumps({"meta": meta, "papers": papers, "events": events, "sessions": sessions},
                      ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    tpl = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
    fragment = tpl.replace("/*__DATA__*/null", blob)
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "artifact.html").write_text(fragment, encoding="utf-8")
    page = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<meta name=\"theme-color\" content=\"#0b1020\">\n"
            f"<link rel=\"icon\" href=\"{FAVICON}\">\n"
            "<style>html{color-scheme:dark;background:#0b1020}body{margin:0}"
            "img{max-width:100%}[hidden]{display:none!important}</style>\n</head>\n<body>\n"
            + fragment + "\n</body>\n</html>\n")
    (ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("")

    c = Counter(p["rel"] for p in papers)
    print(f"papers: {len(papers)} ({c['core']} core, {c['related']} related) | events: {len(events)} | "
          f"sessions: {len(sessions)} | page: {len(page)/1e6:.2f} MB")


if __name__ == "__main__":
    main()
